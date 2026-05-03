int: n_jobs;
int: n_machines;

set of int: JOBS = 1..n_jobs;
set of int: MACHINES = 1..n_machines;

array[JOBS] of int: processing_time;
array[JOBS] of int: due_time;

int: horizon = sum(j in JOBS)(processing_time[j]) + 1000;

array[JOBS] of var MACHINES: machine;
array[JOBS] of var 0..horizon: start_time;
array[JOBS] of var 0..horizon: end_time;

array[JOBS, JOBS] of int: precedence;

array[JOBS, MACHINES] of int: eligible;

array[JOBS] of int: initial_setup;
array[JOBS, JOBS] of int: setup_time;

constraint forall(p, j in JOBS where precedence[p, j] = 1)(
    end_time[p] <= start_time[j]
);

constraint forall(j in JOBS)(
    eligible[j, machine[j]] = 1
);

constraint forall(j in JOBS)(
    end_time[j] = start_time[j] + processing_time[j]
);

% Initial setup: every job must start after its initial setup time
constraint forall(j in JOBS)(
    start_time[j] >= initial_setup[j]
);

% Setup time between two consecutive jobs on the same machine
constraint forall(j1, j2 in JOBS where j1 != j2)(
    machine[j1] = machine[j2] /\ end_time[j1] <= start_time[j2] ->
    start_time[j2] >= end_time[j1] + setup_time[j2, j1]
);

% No overlap on same machine
constraint forall(j1, j2 in JOBS where j1 < j2)(
    machine[j1] = machine[j2] ->
    (end_time[j1] <= start_time[j2] \/ end_time[j2] <= start_time[j1])
);

% Objective: tardiness + makespan
var int: makespan = max(j in JOBS)(end_time[j]);

var int: total_tardiness =
    sum(j in JOBS)(max(0, end_time[j] - due_time[j]));

solve minimize total_tardiness + makespan;