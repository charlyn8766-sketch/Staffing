
import time
import pulp

def solve_schedule(
    W,
    D=range(1,8),
    T=range(1,16),
    MinHw=None,
    MaxHw=None,
    Demand=None,
    Max_Deviation=2.5,
    weekend_15h_only=True,
    require_min_staff=True,
    solver_time_limit=None
):
    """
    Returns: (status, objective, schedule, under_over)
      - status: str
      - objective: float
      - schedule: list[(worker, day, slot)]
      - under_over: dict[(day,slot)] -> (under, over, staffed, demand)
    """
    W = list(W); D = list(D); T = list(T)
    if MinHw is None or MaxHw is None:
        raise ValueError("MinHw and MaxHw must be provided.")
    if Demand is None:
        Demand = {d: [1.0 for _ in T] for d in D}
    else:
        for d in D:
            if d not in Demand:
                raise ValueError(f"Demand missing day={d}")
            if len(Demand[d]) != len(T):
                raise ValueError(f"Demand[day={d}] length should be {len(T)}, got {len(Demand[d])}")

    # Build shift set S with inclusive length (e-s+1)
    S = [(s, e) for s in T for e in T if 4 <= (e - s + 1) <= 8 and s <= e]

    model = pulp.LpProblem("Shift_Scheduling", pulp.LpMinimize)

    x = pulp.LpVariable.dicts("x", (W, D, T), cat="Binary")
    y = pulp.LpVariable.dicts("y", (W, D), cat="Binary")
    z = pulp.LpVariable.dicts("z", (W, range(1,7)), cat="Binary")
    b = pulp.LpVariable.dicts("b", (W, D, S), cat="Binary")
    under = pulp.LpVariable.dicts("under", (D, T), lowBound=0)
    over  = pulp.LpVariable.dicts("over",  (D, T), lowBound=0)

    # Objective
    model += pulp.lpSum(under[d][t] + over[d][t] for d in D for t in T)

    # Link b, x, y
    for w in W:
        for d in D:
            model += pulp.lpSum(b[w][d][s_e] for s_e in S) <= 1
            for t in T:
                model += x[w][d][t] == pulp.lpSum(b[w][d][s_e] for s_e in S if s_e[0] <= t <= s_e[1])
            model += y[w][d] == pulp.lpSum(b[w][d][s_e] for s_e in S)

    # Weekly hours bounds
    for w in W:
        model += pulp.lpSum(x[w][d][t] for d in D for t in T) >= MinHw[w]
        model += pulp.lpSum(x[w][d][t] for d in D for t in T) <= MaxHw[w]

    # Exactly one pair of consecutive rest days
    for w in W:
        model += pulp.lpSum(z[w][d] for d in range(1,7)) == 1
        for d in range(1,7):
            model += z[w][d] <= 1 - y[w][d]
            model += z[w][d] <= 1 - y[w][d+1]

    # 12h rest: late then early
    for w in W:
        for d in range(1,7):
            for t in [13,14,15]:
                early = t - 12  # 1..3
                if early in T:
                    model += x[w][d][t] + x[w][d+1][early] <= 1

    # Max 2 closing shifts per worker (slot 15 as "closing" here)
    for w in W:
        if 15 in T:
            model += pulp.lpSum(x[w][d][15] for d in D) <= 2

    # Demand balance & per-slot rules
    for d in D:
        for idx, t in enumerate(T):
            model += (pulp.lpSum(x[w][d][t] for w in W) + under[d][t] - over[d][t] == Demand[d][idx])
            model += under[d][t] + over[d][t] <= Max_Deviation
            if require_min_staff:
                model += pulp.lpSum(x[w][d][t] for w in W) >= 1

    # Weekend-only for 15h contracts
    if weekend_15h_only:
        for w in W:
            if abs(MinHw[w] - 15) < 1e-6:
                for d in D:
                    if d not in [5,6,7]:
                        model += y[w][d] == 0

    # Solve (no random seed, no time limit control here to mirror your previous app)
    cmd = pulp.PULP_CBC_CMD(msg=True)
    start = time.time()
    model.solve(cmd)
    end = time.time()

    status = pulp.LpStatus[model.status]
    objective = pulp.value(model.objective)

    # Extract solution
    schedule = []
    for w in W:
        for d in D:
            for t in T:
                if pulp.value(x[w][d][t]) > 1e-6:
                    schedule.append((w, d, t))

    # Per-slot metrics
    under_over = {}
    for d in D:
        for idx, t in enumerate(T):
            staffed = sum(1 for w in W if pulp.value(x[w][d][t]) > 0.5)
            under_v = pulp.value(under[d][t])
            over_v = pulp.value(over[d][t])
            demand_v = Demand[d][idx]
            under_over[(d,t)] = (under_v, over_v, staffed, demand_v)

    return status, objective, schedule, under_over
