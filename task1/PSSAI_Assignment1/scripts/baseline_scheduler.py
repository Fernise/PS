import json
import sys
from pathlib import Path


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def resource_capacity_at(resource, time):
    for period in resource["AvailabilityPeriods"]:
        if period["Start"] <= time < period["End"]:
            return period["Capacity"]
    return 0


def has_enough_resources(instance, scheduled_jobs, job, start_time):
    if not instance["Resources"]:
        return True

    job_by_id = {j["Id"]: j for j in instance["Jobs"]}
    end_time = start_time + job["ProcessingTime"]

    for t in range(start_time, end_time):
        for required in job["RequiredResources"]:
            resource_id = required["ResourceId"]
            needed = required["Capacity"]

            resource = next(r for r in instance["Resources"] if r["Id"] == resource_id)
            available = resource_capacity_at(resource, t)

            used = 0
            for scheduled in scheduled_jobs:
                scheduled_job = job_by_id[scheduled["JobId"]]
                scheduled_start = scheduled["StartTime"]
                scheduled_end = scheduled_start + scheduled_job["ProcessingTime"]

                if scheduled_start <= t < scheduled_end:
                    for req in scheduled_job["RequiredResources"]:
                        if req["ResourceId"] == resource_id:
                            used += req["Capacity"]

            if used + needed > available:
                return False

    return True


def build_baseline_solution(instance):
    jobs = sorted(instance["Jobs"], key=lambda j: j["Id"])
    job_by_id = {j["Id"]: j for j in jobs}

    resource_ends = [
        period["End"]
        for resource in instance["Resources"]
        for period in resource["AvailabilityPeriods"]
    ]

    if resource_ends:
        max_resource_end = max(resource_ends)
    else:
        max_resource_end = 0

    max_horizon = max_resource_end + sum(j["ProcessingTime"] for j in jobs) + 100000

    scheduled = {}
    solution_jobs = []

    while len(scheduled) < len(jobs):
        progress = False

        for job in jobs:
            job_id = job["Id"]

            if job_id in scheduled:
                continue

            if not all(p in scheduled for p in job["PrecedenceJobIds"]):
                continue

            best_candidate = None

            for machine_id in job["EligibleMachineIds"]:
                start_time = 0

                # Precedence constraints
                for p in job["PrecedenceJobIds"]:
                    pred = job_by_id[p]
                    pred_start = scheduled[p]["StartTime"]
                    pred_end = pred_start + pred["ProcessingTime"]
                    start_time = max(start_time, pred_end)

                # Machine setup constraints
                previous_jobs_on_machine = [
                    s for s in solution_jobs if s["MachineId"] == machine_id
                ]

                if not previous_jobs_on_machine:
                    start_time = max(start_time, job["InitialSetupTime"])
                else:
                    last = max(
                        previous_jobs_on_machine,
                        key=lambda x: x["StartTime"] + job_by_id[x["JobId"]]["ProcessingTime"],
                    )
                    last_job = job_by_id[last["JobId"]]
                    last_end = last["StartTime"] + last_job["ProcessingTime"]
                    setup_time = job["JobSetupTimes"][last["JobId"] - 1]
                    start_time = max(start_time, last_end + setup_time)

                # Resource constraints
                while start_time <= max_horizon and not has_enough_resources(
                    instance, solution_jobs, job, start_time
                ):
                    start_time += 1

                if start_time > max_horizon:
                    continue

                candidate = {
                    "JobId": job_id,
                    "StartTime": start_time,
                    "MachineId": machine_id,
                }

                if best_candidate is None or candidate["StartTime"] < best_candidate["StartTime"]:
                    best_candidate = candidate

            if best_candidate is None:
                continue

            scheduled[job_id] = best_candidate
            solution_jobs.append(best_candidate)
            progress = True

        if not progress:
            raise RuntimeError("Could not schedule all jobs with this greedy baseline.")

    return {"Jobs": sorted(solution_jobs, key=lambda x: x["JobId"])}


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 baseline_scheduler.py <instance.json> <output.solution.json>")
        sys.exit(1)

    instance_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    instance = load_json(instance_path)
    solution = build_baseline_solution(instance)
    save_json(solution, output_path)

    print(f"Solution written to {output_path}")


if __name__ == "__main__":
    main()