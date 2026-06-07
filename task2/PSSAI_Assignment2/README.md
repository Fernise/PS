# PSSAI Assignment 2 - Topic A: Parallel Machine Scheduling

This folder contains my Assignment 2 implementation for Topic A.

The method is a self-implemented **Simulated Annealing** metaheuristic in Python. The program does not use MiniZinc or CP. It always builds schedules with all hard constraints:

- machine eligibility
- no overlapping jobs on the same machine
- precedence constraints
- initial and sequence-dependent setup times
- resource capacity constraints

The objective is:

```text
total tardiness + makespan
```

The results are heuristic "best found" values, not proven optimal values.

## Files

- `metaheuristic_solver.py`: solve one instance
- `schedule_utils.py`: decoder, objective calculation, resource checks, validator call
- `run_experiments.py`: run 5 seeds and compare parameter settings
- `instances/`: benchmark instances copied for this assignment
- `scripts/solution_validator.py`: validator from the course material
- `results/`: generated solution files
- `results_assignment2.csv`: experiment table
- `slides/assignment2_slides.md`: presentation outline

## Algorithm

The implementation follows the local search questions from the lecture slides.

### What is a solution?

The search representation has two parts:

1. a priority list of jobs
2. a machine assignment for each job

The decoder converts this representation into real start times. It only schedules jobs whose predecessors are already finished. For each selected job it searches the earliest feasible start time on the assigned machine.

When checking a start time, the decoder verifies:

- the machine is eligible
- the machine is free
- the required setup time is respected
- all predecessors are finished
- enough resource capacity exists during the whole processing time

### What is the cost of a solution?

The cost is the objective from the assignment:

```text
cost = total tardiness + makespan
```

### What are the neighbours of a solution?

The Simulated Annealing neighbourhood uses three simple moves:

- swap two jobs in the priority list
- remove one job and insert it in another position
- assign one job to another eligible machine

### How is the initial solution generated?

The initial solution is built with a greedy constructive heuristic. At each step it considers only jobs whose predecessors have already been scheduled, and then chooses a feasible placement with a low immediate cost.

### How are worse neighbours accepted?

If a neighbour has lower cost, it is accepted. If it has higher cost, it can still be accepted with the Simulated Annealing probability:

```text
exp(-(new_cost - current_cost) / temperature)
```

The temperature is multiplied by the cooling rate after each iteration.

## Run One Instance

```bash
python3 metaheuristic_solver.py \
  --instance instances/PSSAI_PMS_j10_m3_r1_5.json \
  --output results/PSSAI_PMS_j10_m3_r1_5.solution.json \
  --seed 1 \
  --iterations 10000
```

## Run Experiments

Five runs for the small benchmark instances:

```bash
python3 run_experiments.py \
  --instances "instances/PSSAI_PMS_j10_*.json" \
  --runs 5 \
  --iterations 10000 \
  --output-csv results_assignment2.csv
```

All benchmark instances:

```bash
python3 run_experiments.py \
  --instances "instances/PSSAI_PMS_*.json" \
  --runs 5 \
  --iterations 10000 \
  --time-limit 300 \
  --output-csv results_assignment2.csv
```

The CSV contains one row per run and one summary row per instance and parameter setting. The summary reports:

- average cost
- best cost
- standard deviation

## Parameter Settings

The experiment script compares:

- `short`: fewer iterations and lower temperature
- `default`: baseline setting
- `hot`: higher temperature and slower cooling

## Manual Validation

```bash
python3 scripts/solution_validator.py \
  instances/PSSAI_PMS_j10_m3_r1_5.json \
  results/PSSAI_PMS_j10_m3_r1_5.solution.json
```

## Lessons Learned

- The most important part is not the random search itself, but the decoder that keeps every final schedule feasible.
- Resource capacities cannot be ignored because they are hard constraints.
- Simulated Annealing is easy to explain and works reasonably well for this assignment because it can escape some local optima.
- Larger instances need more runtime, because every neighbour must be decoded and checked.
