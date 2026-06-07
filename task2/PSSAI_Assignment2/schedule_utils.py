"""
Helper functions for Assignment 2.

The important idea in this file is the decoder:

    priority list + machine choices  ->  real feasible schedule

The metaheuristic is allowed to change the priority list and the machine choices.
After each change, the decoder builds actual start times while checking all hard
constraints from Topic A.
"""

import json
import math
import subprocess
import sys
from bisect import bisect_left
from pathlib import Path


VERY_LARGE_NUMBER = 10**18


def load_json(path):
    """Read a JSON file."""
    with open(path, "r") as file:
        return json.load(file)


def save_json(data, path):
    """Write a JSON file and create the output folder if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as file:
        json.dump(data, file, indent=2)


def calculate_objective(instance, solution):
    """
    Calculate the objective required in Topic A:

        total tardiness + makespan
    """
    jobs_by_id = {job["Id"]: job for job in instance["Jobs"]}
    start_by_job = {entry["JobId"]: entry["StartTime"] for entry in solution["Jobs"]}

    tardiness = 0
    makespan = 0
    for job_id, job in jobs_by_id.items():
        end_time = start_by_job[job_id] + job["ProcessingTime"]
        tardiness += max(0, end_time - job["DueTime"])
        makespan = max(makespan, end_time)

    return {
        "tardiness": int(tardiness),
        "makespan": int(makespan),
        "cost": int(tardiness + makespan),
    }


def topological_order(instance):
    """
    Return one precedence-feasible order of the jobs.

    This is useful for making an initial priority list. The decoder also checks
    precedence dynamically, so later neighbour moves do not have to keep the list
    topological.
    """
    jobs = sorted(instance["Jobs"], key=lambda job: job["Id"])
    predecessors_left = {job["Id"]: len(job["PrecedenceJobIds"]) for job in jobs}
    successors = {job["Id"]: [] for job in jobs}

    for job in jobs:
        for predecessor in job["PrecedenceJobIds"]:
            successors[predecessor].append(job["Id"])

    ready = sorted([job_id for job_id, count in predecessors_left.items() if count == 0])
    order = []

    while ready:
        job_id = ready.pop(0)
        order.append(job_id)

        for successor in successors[job_id]:
            predecessors_left[successor] -= 1
            if predecessors_left[successor] == 0:
                ready.append(successor)
        ready.sort()

    if len(order) != len(jobs):
        raise ValueError("The instance contains a cycle in the precedence graph.")

    return order


class ScheduleBuilder:
    """
    Incrementally builds a schedule.

    Resource usage is stored as intervals. When a new job is tested, the code only
    checks intervals where resource capacity or already used capacity can change.
    This is still simple to explain, but much faster than checking every time point.
    """

    def __init__(self, instance):
        self.instance = instance
        self.jobs_by_id = {job["Id"]: job for job in instance["Jobs"]}
        self.resources_by_id = {res["Id"]: res for res in instance["Resources"]}

        self.machine_available_at = {machine["Id"]: 0 for machine in instance["Machines"]}
        self.last_job_on_machine = {machine["Id"]: None for machine in instance["Machines"]}
        self.scheduled_jobs = []
        self.scheduled_by_id = {}
        self.resource_intervals = {res["Id"]: [] for res in instance["Resources"]}
        self.resource_period_boundaries = self._make_resource_period_boundaries()

        self.max_horizon = self._estimate_safe_horizon()

    def _make_resource_period_boundaries(self):
        """Store resource period start/end times for faster resource checks."""
        boundaries = {}
        for resource in self.instance["Resources"]:
            points = set()
            for period in resource["AvailabilityPeriods"]:
                points.add(period["Start"])
                points.add(period["End"])
            boundaries[resource["Id"]] = sorted(points)
        return boundaries

    def _estimate_safe_horizon(self):
        """
        A large upper bound used to avoid infinite loops when searching start times.
        """
        total_processing = sum(job["ProcessingTime"] for job in self.instance["Jobs"])
        largest_setup = 0
        for job in self.instance["Jobs"]:
            largest_setup = max(largest_setup, job["InitialSetupTime"])
            largest_setup = max(largest_setup, max(job["JobSetupTimes"], default=0))

        last_resource_time = 0
        for resource in self.instance["Resources"]:
            for period in resource["AvailabilityPeriods"]:
                last_resource_time = max(last_resource_time, period["End"])

        return last_resource_time + total_processing + largest_setup * len(self.instance["Jobs"]) + 10000

    def _resource_capacity_at(self, resource_id, time):
        """Return available capacity of one resource at one time point."""
        resource = self.resources_by_id[resource_id]
        for period in resource["AvailabilityPeriods"]:
            if period["Start"] <= time < period["End"]:
                return period["Capacity"]
        return 0

    def _used_resource_capacity_between(self, resource_id, start, end):
        """Return capacity already used during one interval [start, end)."""
        used = 0
        for interval_start, interval_end, capacity in self.resource_intervals[resource_id]:
            if interval_start < end and start < interval_end:
                used += capacity

        return used

    def _resource_boundaries_inside(self, resource_id, start, end):
        """Resource availability changes only at these boundaries."""
        boundaries = self.resource_period_boundaries.get(resource_id, [])
        position = bisect_left(boundaries, start)
        result = []
        while position < len(boundaries) and boundaries[position] < end:
            if boundaries[position] > start:
                result.append(boundaries[position])
            position += 1
        return result

    def _resource_check(self, job, start_time):
        """
        Check the resource hard constraint for the whole processing interval.

        To make this faster, I do not check every integer time point. Instead I split
        the interval only where something can change: resource availability periods or
        already scheduled jobs starting/ending.
        """
        end_time = start_time + job["ProcessingTime"]
        next_start_time = start_time + 1

        for requirement in job["RequiredResources"]:
            resource_id = requirement["ResourceId"]
            needed = requirement["Capacity"]

            points = {start_time, end_time}
            points.update(self._resource_boundaries_inside(resource_id, start_time, end_time))

            for interval_start, interval_end, _ in self.resource_intervals[resource_id]:
                if interval_start < end_time and start_time < interval_end:
                    points.add(max(start_time, interval_start))
                    points.add(min(end_time, interval_end))

            sorted_points = sorted(points)
            for left, right in zip(sorted_points, sorted_points[1:]):
                if left >= right:
                    continue

                available = self._resource_capacity_at(resource_id, left)
                already_used = self._used_resource_capacity_between(resource_id, left, right)

                if already_used + needed > available:
                    # If the job cannot start here, jumping to the end of the
                    # conflicting segment is usually better than increasing by 1.
                    return False, max(next_start_time, right)

        return True, start_time

    def _earliest_time_after_precedence(self, job):
        """Earliest start time allowed by precedence constraints."""
        earliest = 0
        for predecessor_id in job["PrecedenceJobIds"]:
            predecessor = self.jobs_by_id[predecessor_id]
            predecessor_start = self.scheduled_by_id[predecessor_id]["StartTime"]
            predecessor_end = predecessor_start + predecessor["ProcessingTime"]
            earliest = max(earliest, predecessor_end)
        return earliest

    def _earliest_time_after_machine_setup(self, job, machine_id):
        """Earliest start time allowed by machine availability and setup time."""
        previous_job_id = self.last_job_on_machine[machine_id]

        if previous_job_id is None:
            return job["InitialSetupTime"]

        setup_time = job["JobSetupTimes"][previous_job_id - 1]
        return self.machine_available_at[machine_id] + setup_time

    def find_earliest_start(self, job, machine_id):
        """Find earliest feasible start on one machine."""
        start_time = max(
            self._earliest_time_after_precedence(job),
            self._earliest_time_after_machine_setup(job, machine_id),
        )

        while start_time <= self.max_horizon:
            resources_ok, next_start_time = self._resource_check(job, start_time)
            if resources_ok:
                return start_time
            start_time = next_start_time

        return None

    def add_job(self, job, machine_id, start_time):
        """Add one scheduled job to the partial schedule."""
        entry = {
            "JobId": int(job["Id"]),
            "StartTime": int(start_time),
            "MachineId": int(machine_id),
        }

        self.scheduled_jobs.append(entry)
        self.scheduled_by_id[job["Id"]] = entry
        self.last_job_on_machine[machine_id] = job["Id"]
        self.machine_available_at[machine_id] = start_time + job["ProcessingTime"]

        end_time = start_time + job["ProcessingTime"]
        for requirement in job["RequiredResources"]:
            self.resource_intervals[requirement["ResourceId"]].append(
                (start_time, end_time, requirement["Capacity"])
            )


def decode_solution(instance, priority_order, machine_assignment):
    """
    Build a feasible schedule from a priority list and machine assignments.

    The priority list is only used to decide which currently available job should be
    scheduled next. A job is "available" only when all predecessors have already been
    scheduled, so precedence is always respected.
    """
    jobs_by_id = {job["Id"]: job for job in instance["Jobs"]}
    rank = {job_id: position for position, job_id in enumerate(priority_order)}

    predecessors_left = {job["Id"]: set(job["PrecedenceJobIds"]) for job in instance["Jobs"]}
    successors = {job["Id"]: [] for job in instance["Jobs"]}
    for job in instance["Jobs"]:
        for predecessor in job["PrecedenceJobIds"]:
            successors[predecessor].append(job["Id"])

    ready_jobs = [job_id for job_id, preds in predecessors_left.items() if not preds]
    builder = ScheduleBuilder(instance)

    while ready_jobs:
        ready_jobs.sort(key=lambda job_id: (rank.get(job_id, VERY_LARGE_NUMBER), job_id))
        job_id = ready_jobs.pop(0)
        job = jobs_by_id[job_id]

        assigned_machine = machine_assignment.get(job_id, job["EligibleMachineIds"][0])
        if assigned_machine not in job["EligibleMachineIds"]:
            assigned_machine = job["EligibleMachineIds"][0]

        # Repair idea: first try the machine selected by the metaheuristic. If this
        # cannot place the job, try the other eligible machines and choose the
        # earliest feasible placement.
        machines_to_try = [assigned_machine] + [
            machine_id
            for machine_id in job["EligibleMachineIds"]
            if machine_id != assigned_machine
        ]

        best_start = None
        best_machine = None
        for machine_id in machines_to_try:
            candidate_start = builder.find_earliest_start(job, machine_id)
            if candidate_start is None:
                continue
            if best_start is None or candidate_start < best_start:
                best_start = candidate_start
                best_machine = machine_id

        if best_start is None:
            raise RuntimeError(f"No feasible start time found for job {job_id}.")

        builder.add_job(job, best_machine, best_start)

        for successor in successors[job_id]:
            predecessors_left[successor].remove(job_id)
            if not predecessors_left[successor]:
                ready_jobs.append(successor)

    if len(builder.scheduled_jobs) != len(instance["Jobs"]):
        raise RuntimeError("The decoder did not schedule all jobs.")

    return {"Jobs": sorted(builder.scheduled_jobs, key=lambda item: item["JobId"])}


def validate_with_official_script(instance_path, solution_path):
    """Run the provided validator and return (feasible, full_output)."""
    validator = Path(__file__).resolve().parent / "scripts" / "solution_validator.py"
    command = [sys.executable, str(validator), str(instance_path), str(solution_path)]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = (completed.stdout or "") + (completed.stderr or "")
    feasible = completed.returncode == 0 and "Solution is feasible" in output
    return feasible, output


def average(values):
    return sum(values) / len(values)


def standard_deviation(values):
    """Sample standard deviation, as usually reported for repeated experiments."""
    if len(values) <= 1:
        return 0.0
    avg = average(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)
