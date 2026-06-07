"""
Experiment runner for Assignment 2.

It runs several random seeds for each instance and each parameter setting.
For every setting it reports:

    average cost, best cost, and standard deviation over the runs
"""

import argparse
import csv
import glob
from pathlib import Path

from metaheuristic_solver import simulated_annealing
from schedule_utils import (
    average,
    load_json,
    save_json,
    standard_deviation,
    validate_with_official_script,
)


PARAMETER_SETTINGS = {
    "short": {
        "iterations_factor": 0.5,
        "start_temperature": 250.0,
        "cooling_rate": 0.9990,
    },
    "default": {
        "iterations_factor": 1.0,
        "start_temperature": 500.0,
        "cooling_rate": 0.9995,
    },
    "hot": {
        "iterations_factor": 1.0,
        "start_temperature": 1000.0,
        "cooling_rate": 0.9997,
    },
}


def expand_instance_patterns(patterns):
    """Convert command line paths or glob patterns into a sorted file list."""
    instance_paths = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            instance_paths.extend(matches)
        else:
            instance_paths.append(pattern)

    return sorted(
        {
            str(Path(path))
            for path in instance_paths
            if Path(path).is_file() and str(path).endswith(".json")
        }
    )


def write_csv(path, rows):
    """Write all run and summary rows to a CSV file."""
    fieldnames = [
        "row_type",
        "setting",
        "instance",
        "run",
        "seed",
        "iterations",
        "cost",
        "tardiness",
        "makespan",
        "runtime",
        "feasible",
        "average_cost",
        "best_cost",
        "std_cost",
    ]

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run PMS metaheuristic experiments.")
    parser.add_argument("--instances", nargs="+", required=True, help="Instance files or glob patterns.")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--settings", default="short,default,hot")
    parser.add_argument("--seed-base", type=int, default=1)
    parser.add_argument("--output-csv", default="results_assignment2.csv")
    parser.add_argument("--solutions-dir", default="results")
    parser.add_argument("--skip-validation", action="store_true")
    return parser.parse_args()


def main():
    args = parse_arguments()
    instance_paths = expand_instance_patterns(args.instances)
    selected_settings = [name.strip() for name in args.settings.split(",") if name.strip()]

    for setting in selected_settings:
        if setting not in PARAMETER_SETTINGS:
            raise ValueError(f"Unknown parameter setting: {setting}")

    if not instance_paths:
        raise SystemExit("No instance files found.")

    rows = []
    for instance_path in instance_paths:
        instance = load_json(instance_path)
        instance_name = Path(instance_path).stem

        for setting_name in selected_settings:
            setting = PARAMETER_SETTINGS[setting_name]
            iterations = max(1, int(args.iterations * setting["iterations_factor"]))
            costs = []

            for run_number in range(1, args.runs + 1):
                seed = args.seed_base + run_number - 1

                result = simulated_annealing(
                    instance=instance,
                    seed=seed,
                    iterations=iterations,
                    time_limit=args.time_limit,
                    start_temperature=setting["start_temperature"],
                    cooling_rate=setting["cooling_rate"],
                )

                solution_path = (
                    Path(args.solutions_dir)
                    / setting_name
                    / f"{instance_name}_seed{seed}.solution.json"
                )
                save_json(result["solution"], solution_path)

                feasible = True
                if not args.skip_validation:
                    feasible, _ = validate_with_official_script(instance_path, solution_path)

                metrics = result["metrics"]
                costs.append(metrics["cost"])

                rows.append(
                    {
                        "row_type": "run",
                        "setting": setting_name,
                        "instance": instance_name,
                        "run": run_number,
                        "seed": seed,
                        "iterations": iterations,
                        "cost": metrics["cost"],
                        "tardiness": metrics["tardiness"],
                        "makespan": metrics["makespan"],
                        "runtime": f"{result['runtime']:.3f}",
                        "feasible": feasible,
                    }
                )

                print(
                    f"{instance_name}, {setting_name}, run {run_number}/{args.runs}: "
                    f"cost={metrics['cost']}, feasible={feasible}"
                )

            rows.append(
                {
                    "row_type": "summary",
                    "setting": setting_name,
                    "instance": instance_name,
                    "iterations": iterations,
                    "average_cost": f"{average(costs):.3f}",
                    "best_cost": min(costs),
                    "std_cost": f"{standard_deviation(costs):.3f}",
                }
            )

    write_csv(args.output_csv, rows)
    print(f"CSV written to: {args.output_csv}")


if __name__ == "__main__":
    main()
