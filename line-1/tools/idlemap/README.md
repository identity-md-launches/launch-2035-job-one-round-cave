# Idlemap — explain unused capacity in a proposed work plan

Run from the repository root, offline, with Python 3.10+:

```sh
python3 -B line-1/tools/idlemap/idlemap.py --demo
```

The demonstration has two available workers but puts build (4 minutes),
fixtures (2), and their dependent check (1) on worker 1. Observed finish: 7;
busy capacity: 7 worker-minutes; idle capacity: 7 worker-minutes. Fixtures
waits ready for 4 minutes while a worker is idle. Idlemap explains that
opportunity without changing the plan or running task labels.

Analyze your own full plan:

```sh
python3 -B line-1/tools/idlemap/idlemap.py --tasks line-1/tools/plancheck/tasks.json --plan line-1/tools/plancheck/plan.json --workers 2 --budget 10
```

Task JSON: `{"tasks":[{"id":"build","minutes":4,"after":[]}]}`.
Plan JSON: `{"workers":1,"finish":4,"schedule":[{"task":"build","worker":1,"start":0,"finish":4}]}`.
The external worker count and optional budget are authoritative. The unchanged
sibling `../plancheck/plancheck.py` checks dependencies, durations, capacity,
completeness and deadline before any analysis. Keep that folder with Idlemap.
Standard library only; no install, network, credentials or environment reads.
Explicit input files must resolve inside the current workspace, be ordinary
files, and contain at most 100,000 bytes each. Inherited limits: 500 tasks,
64 workers, bounded finite decimal numbers, no duplicate JSON keys.

Output uses exact decimal **strings** for times and capacity areas:

- `timeline`: half-open intervals `[start, finish)`, with running, idle and
  ready-but-unstarted task counts. Completions take effect at the boundary.
- `idle_worker_minutes`: integral of idle workers from zero through plan finish,
  including initial and per-worker trailing gaps. Busy plus idle equals workers
  times finish. The optional deadline only validates; it does not extend this horizon.
- `ready_spare_worker_minutes`: integral of the smaller of idle-worker count and
  ready-waiting task count. This avoids double-counting one spare worker when
  several tasks wait. It is a diagnostic of this timeline, not recoverable time.
- Per-task readiness is the latest **scheduled** predecessor finish (zero for
  roots). Its ready wait is split between intervals with all workers busy and
  intervals with at least one spare worker. Per-task waits can overlap; do not
  sum them to obtain unused worker capacity.
- Per-worker busy/idle totals and peak concurrency include unused workers.

Assumptions: continuous availability, interchangeable workers, nonpreemptive
tasks, one worker per task, supplied durations, full schedules starting from
zero. Intentional waiting can improve a schedule; an idle interval alone is
not a flaw. No claim of optimality, achievable speedup, real effort, resource
eligibility or execution is made. Progress/replan segments are refused.
Malformed inputs exit 1; well-formed infeasible plans exit 2 with validation
diagnostics only; analyzed schedules exit 0.

Checks:

```sh
python3 -B line-1/tools/idlemap/selftest.py
```

Nine tests cover decimal endpoints, initial/trailing idle, dependency waiting,
fully occupied waiting, invalid inputs, input order, CLI exits, and 120 seeded
valid DAG schedules checked by an independent minute-by-minute oracle.
