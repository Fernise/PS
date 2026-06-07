# Assignment 2 Slides - Topic A PMS

## 1. Problem and Goal

- Parallel Machine Scheduling
- We have jobs, machines, precedences, setup times and resources
- Goal: assign every job to a machine and a start time
- Objective: minimize total tardiness + makespan
- All constraints from Topic A are treated as hard constraints

## 2. Algorithm Description

- I use Simulated Annealing
- It is a single-solution local search method
- It starts from one current solution
- It generates one neighbour at a time
- It accepts better solutions
- It sometimes accepts worse solutions to escape local optima
- The temperature decreases during the search

## 3. Representation and Decoder

- Representation:
  - priority list of jobs
  - selected machine for each job
- The decoder converts this representation into real start times
- It schedules only jobs whose predecessors are finished
- It checks machine eligibility, setup times, precedences and resources
- The final solution is checked with the official validator

## 4. Neighbourhood and Acceptance

- Neighbourhood moves:
  - swap two jobs in the priority list
  - remove and reinsert one job
  - change one job to another eligible machine
- Better neighbours are accepted
- Worse neighbours can be accepted with probability depending on:
  - cost difference
  - current temperature

## 5. Parameter Variants

- `short`: 5000 iterations, temperature 250, cooling 0.9990
- `default`: 10000 iterations, temperature 500, cooling 0.9995
- `hot`: 10000 iterations, temperature 1000, cooling 0.9997
- Each variant is run 5 times with different random seeds
- Results are best found values, not optimality proofs

## 6. Benchmark Results

Results are reported as average, best and standard deviation over 5 runs.

| Instance | Best setting | Average | Best | Std |
|---|---:|---:|---:|---:|
| j10_m3_r0_1 | default/hot | 2697.0 | 2697 | 0.0 |
| j10_m3_r0_2 | short/default/hot | 6050.0 | 6050 | 0.0 |
| j10_m3_r1_5 | short/default/hot | 3380.0 | 3380 | 0.0 |
| j10_m3_r2_3 | short/default/hot | 4009.0 | 4009 | 0.0 |
| j10_m4_r1_4 | short/default/hot | 14602.0 | 14602 | 0.0 |

Full run data is stored in `results_assignment2.csv`.

## 7. Conclusions and Lessons Learned

- The decoder is the key part of the implementation
- Resource constraints cannot be ignored
- Simulated Annealing gives feasible best-found solutions
- It does not prove optimality
- More iterations can improve results, but also increase runtime

## 8. How to Run

Solve one instance:

```bash
python3 metaheuristic_solver.py --instance instances/PSSAI_PMS_j10_m3_r1_5.json --output results/PSSAI_PMS_j10_m3_r1_5.solution.json --seed 1 --iterations 10000
```

Run experiments:

```bash
python3 run_experiments.py --instances "instances/PSSAI_PMS_j10_*.json" --runs 5 --iterations 10000
```
