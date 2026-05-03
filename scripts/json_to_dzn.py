import json
import sys


def write_list(name, values):
    return f"{name} = [{', '.join(map(str, values))}];\n"


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 json_to_dzn.py <instance.json> <output.dzn>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    jobs = sorted(data["Jobs"], key=lambda j: j["Id"])
    machines = sorted(data["Machines"], key=lambda m: m["Id"])
    resources = sorted(data["Resources"], key=lambda r: r["Id"])

    n_jobs = len(jobs)
    n_machines = len(machines)
    n_resources = len(resources)

    horizon = sum(j["ProcessingTime"] for j in jobs) + 1000

    processing = [j["ProcessingTime"] for j in jobs]
    due = [j["DueTime"] for j in jobs]
    initial_setup = [j["InitialSetupTime"] for j in jobs]

    eligible = []
    for j in jobs:
        for m in machines:
            eligible.append(1 if m["Id"] in j["EligibleMachineIds"] else 0)

    precedence = []
    for p in jobs:
        for j in jobs:
            precedence.append(1 if p["Id"] in j["PrecedenceJobIds"] else 0)

    setup = []
    for j in jobs:
        setup.extend(j["JobSetupTimes"])

    resource_req = []
    for j in jobs:
        reqs = {r["ResourceId"]: r["Capacity"] for r in j["RequiredResources"]}
        for r in resources:
            resource_req.append(reqs.get(r["Id"], 0))

    capacity = []
    for r in resources:
        for t in range(horizon + 1):
            cap = 0
            for p in r["AvailabilityPeriods"]:
                if p["Start"] <= t < p["End"]:
                    cap = p["Capacity"]
                    break
            capacity.append(cap)

    with open(sys.argv[2], "w") as f:
        f.write(f"n_jobs = {n_jobs};\n")
        f.write(f"n_machines = {n_machines};\n")
        f.write(f"n_resources = {n_resources};\n")
        f.write(f"horizon = {horizon};\n\n")

        f.write(write_list("processing_time", processing))
        f.write(write_list("due_time", due))
        f.write(write_list("initial_setup", initial_setup))

        f.write("\n")
        f.write(f"eligible = array2d(JOBS, MACHINES, [{', '.join(map(str, eligible))}]);\n")
        f.write(f"precedence = array2d(JOBS, JOBS, [{', '.join(map(str, precedence))}]);\n")
        f.write(f"setup_time = array2d(JOBS, JOBS, [{', '.join(map(str, setup))}]);\n")


        f.write(f"resource_req = array2d(JOBS, RESOURCES, [{', '.join(map(str, resource_req))}]);\n")
        f.write(f"capacity = array2d(RESOURCES, 0..horizon, [{', '.join(map(str, capacity))}]);\n")


if __name__ == "__main__":
    main()