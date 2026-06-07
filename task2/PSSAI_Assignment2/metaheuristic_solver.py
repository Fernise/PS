"""
Assignment 2

We use Simulated Annealing:

1. Start with a greedy feasible solution.
2. Make a small random change.
3. Decode the changed representation into a feasible schedule.
4. Accept improvements, and sometimes also accept worse solutions to escape local optima.

The final result is always decoded and validated as a real schedule.
"""

import argparse
import math
import random
import time
from pathlib import Path

from schedule_utils import (
    ScheduleBuilder,
    calculate_objective,
    decode_solution,
    load_json,
    save_json,
    validate_with_official_script,
)


def make_greedy_initial_solution(instance, random_generator):
    """
    Construct a feasible initial solution.

    At each step, only jobs with all predecessors already scheduled are considered.
    Among them, I prefer jobs with earlier due dates. For the selected job, all eligible
    machines are tested and the machine with the earliest completion is chosen.
    """
    jobs_by_id = {job["Id"]: job for job in instance["Jobs"]}
    predecessors_left = {job["Id"]: set(job["PrecedenceJobIds"]) for job in instance["Jobs"]}
    successors = {job["Id"]: [] for job in instance["Jobs"]}

    for job in instance["Jobs"]:
        for predecessor in job["PrecedenceJobIds"]:
            successors[predecessor].append(job["Id"])

    ready_jobs = [job_id for job_id, preds in predecessors_left.items() if not preds]
    builder = ScheduleBuilder(instance)

    priority_order = []
    machine_assignment = {}

    while ready_jobs:
        best_job_id = None
        best_machine = None
        best_start = None
        best_score = None

        # Try all currently available jobs. This is a little slower, but it avoids
        # choosing a job that looks good locally while another ready job has a much
        # more urgent feasible placement.
        for candidate_job_id in ready_jobs:
            candidate_job = jobs_by_id[candidate_job_id]

            for machine_id in candidate_job["EligibleMachineIds"]:
                start_time = builder.find_earliest_start(candidate_job, machine_id)
                if start_time is None:
                    continue

                end_time = start_time + candidate_job["ProcessingTime"]
                tardiness = max(0, end_time - candidate_job["DueTime"])
                score = (
                    tardiness + end_time,
                    candidate_job["DueTime"],
                    candidate_job["ProcessingTime"],
                    random_generator.random(),
                )

                if best_score is None or score < best_score:
                    best_score = score
                    best_job_id = candidate_job_id
                    best_machine = machine_id
                    best_start = start_time

        if best_job_id is None:
            raise RuntimeError("Could not schedule any ready job in the greedy heuristic.")

        job_id = best_job_id
        job = jobs_by_id[job_id]
        ready_jobs.remove(job_id)

        builder.add_job(job, best_machine, best_start)
        priority_order.append(job_id)
        machine_assignment[job_id] = best_machine

        for successor in successors[job_id]:
            predecessors_left[successor].remove(job_id)
            if not predecessors_left[successor]:
                ready_jobs.append(successor)

    return priority_order, machine_assignment


def make_neighbour(instance, priority_order, machine_assignment, random_generator):
    """
    Create a neighbouring solution representation.

    The decoder will repair precedence by scheduling only ready jobs, therefore the
    priority list itself is allowed to be non-topological.
    """
    new_order = list(priority_order)
    new_assignment = dict(machine_assignment)

    move_type = random_generator.choice(["swap", "insert", "machine"])

    if move_type == "swap" and len(new_order) >= 2:
        first, second = random_generator.sample(range(len(new_order)), 2)
        new_order[first], new_order[second] = new_order[second], new_order[first]

    elif move_type == "insert" and len(new_order) >= 2:
        old_position, new_position = random_generator.sample(range(len(new_order)), 2)
        job_id = new_order.pop(old_position)
        new_order.insert(new_position, job_id)

    else:
        jobs_with_choice = [
            job for job in instance["Jobs"] if len(job["EligibleMachineIds"]) > 1
        ]
        if jobs_with_choice:
            job = random_generator.choice(jobs_with_choice)
            current_machine = new_assignment[job["Id"]]
            possible_machines = [
                machine_id
                for machine_id in job["EligibleMachineIds"]
                if machine_id != current_machine
            ]
            new_assignment[job["Id"]] = random_generator.choice(possible_machines)

    return new_order, new_assignment


def simulated_annealing(
    instance,
    seed,
    iterations,
    time_limit,
    start_temperature,
    cooling_rate,
):
    """Run the simulated annealing search."""
    random_generator = random.Random(seed)
    start_clock = time.perf_counter()

    current_order, current_assignment = make_greedy_initial_solution(
        instance, random_generator
    )
    current_solution = decode_solution(instance, current_order, current_assignment)
    current_metrics = calculate_objective(instance, current_solution)

    best_order = list(current_order)
    best_assignment = dict(current_assignment)
    best_solution = current_solution
    best_metrics = current_metrics

    temperature = start_temperature
    accepted_moves = 0

    for _ in range(iterations):
        if time_limit is not None and time.perf_counter() - start_clock >= time_limit:
            break

        neighbour_order, neighbour_assignment = make_neighbour(
            instance, current_order, current_assignment, random_generator
        )
        try:
            neighbour_solution = decode_solution(instance, neighbour_order, neighbour_assignment)
        except RuntimeError:
            # Some priority orders are too bad to repair for the resource calendar.
            # In that case I simply reject the neighbour and continue the search.
            continue
        neighbour_metrics = calculate_objective(instance, neighbour_solution)

        difference = neighbour_metrics["cost"] - current_metrics["cost"]

        accept = False
        if difference <= 0:
            accept = True
        else:
            probability = math.exp(-difference / max(temperature, 0.000001))
            accept = random_generator.random() < probability

        if accept:
            current_order = neighbour_order
            current_assignment = neighbour_assignment
            current_solution = neighbour_solution
            current_metrics = neighbour_metrics
            accepted_moves += 1

            if current_metrics["cost"] < best_metrics["cost"]:
                best_order = list(current_order)
                best_assignment = dict(current_assignment)
                best_solution = current_solution
                best_metrics = current_metrics

        temperature *= cooling_rate

    return {
        "solution": best_solution,
        "metrics": best_metrics,
        "runtime": time.perf_counter() - start_clock,
        "accepted_moves": accepted_moves,
        "priority_order": best_order,
        "machine_assignment": best_assignment,
    }


def parse_arguments():
    parser = argparse.ArgumentParser(description="Simulated annealing PMS solver.")
    parser.add_argument("--instance", required=True, help="Path to the instance JSON file.")
    parser.add_argument("--output", required=True, help="Path to the output solution JSON file.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--time-limit", type=float, default=None, help="Optional time limit in seconds.")
    parser.add_argument("--start-temperature", type=float, default=500.0)
    parser.add_argument("--cooling-rate", type=float, default=0.9995)
    parser.add_argument("--skip-validation", action="store_true")
    return parser.parse_args()


def main():
    args = parse_arguments()

    instance_path = Path(args.instance)
    output_path = Path(args.output)
    instance = load_json(instance_path)

    result = simulated_annealing(
        instance=instance,
        seed=args.seed,
        iterations=args.iterations,
        time_limit=args.time_limit,
        start_temperature=args.start_temperature,
        cooling_rate=args.cooling_rate,
    )

    save_json(result["solution"], output_path)

    feasible = True
    if not args.skip_validation:
        feasible, validator_output = validate_with_official_script(instance_path, output_path)
        if not feasible:
            print(validator_output)

    metrics = result["metrics"]
    print(f"Solution written to: {output_path}")
    print(f"Seed: {args.seed}")
    print(f"Runtime: {result['runtime']:.3f} seconds")
    print(f"Tardiness: {metrics['tardiness']}")
    print(f"Makespan: {metrics['makespan']}")
    print(f"Cost: {metrics['cost']}")
    print(f"Feasible according to validator: {feasible}")


if __name__ == "__main__":
    main()
