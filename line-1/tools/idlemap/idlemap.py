#!/usr/bin/env python3
"""Explain idle capacity and ready-task waits in a checked full offline plan."""
import argparse
from decimal import Decimal
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    'idlemap_check', Path(__file__).resolve().parents[1] / 'plancheck' / 'plancheck.py')
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def exact(value):
    """Finite decimal rendering; inputs and sums come only from decimal values."""
    value = Fraction(value)
    sign = '-' if value < 0 else ''
    whole, rest = divmod(abs(value.numerator), value.denominator)
    digits = []
    while rest:
        digit, rest = divmod(rest * 10, value.denominator)
        digits.append(str(digit))
    return sign + str(whole) + ('.' + ''.join(digits) if digits else '')


def analyze(data, plan, workers, budget=None):
    validation = check.check(data, plan, workers, budget)
    if not validation['valid']:
        return {'analyzed': False, 'check': validation}
    graph = check.graph(data)
    slots = {r['task']: (r['worker'], check.number(r['start'], 'start'),
                          check.number(r['finish'], 'finish'))
             for r in plan['schedule']}
    ready = {name: max((slots[d][2] for d in deps), default=Fraction(0))
             for name, (_, deps) in graph.items()}
    finish = max(row[2] for row in slots.values())
    # Readiness changes occur only at predecessor finishes, already in events.
    events = sorted({Fraction(0)} | {t for _, s, e in slots.values() for t in (s, e)})
    timeline = []
    spare_wait = dict.fromkeys(slots, Fraction(0))
    busy_wait = dict.fromkeys(slots, Fraction(0))
    idle_area = Fraction(0)
    opportunity_area = Fraction(0)
    for start, end in zip(events, events[1:]):
        running = sum(s <= start < e for _, s, e in slots.values())
        queued = sorted(n for n, (_, s, _) in slots.items() if ready[n] <= start < s)
        idle = workers - running
        duration = end - start
        idle_area += idle * duration
        opportunity_area += min(idle, len(queued)) * duration
        for name in queued:
            (spare_wait if idle else busy_wait)[name] += duration
        timeline.append({'start': exact(start), 'finish': exact(end),
                         'running': running, 'idle_workers': idle,
                         'ready_waiting': len(queued)})
    per_worker = []
    for worker in range(1, workers + 1):
        busy = sum((e-s for w, s, e in slots.values() if w == worker), Fraction(0))
        per_worker.append({'worker': worker, 'busy_minutes': exact(busy),
                           'idle_minutes': exact(finish-busy)})
    busy_total = sum((duration for duration, _ in graph.values()), Fraction(0))
    assert busy_total + idle_area == workers * finish
    return {'analyzed': True, 'check': validation, 'units': 'minutes',
            'horizon': {'start': '0', 'finish': exact(finish)},
            'busy_worker_minutes': exact(busy_total),
            'idle_worker_minutes': exact(idle_area),
            'ready_spare_worker_minutes': exact(opportunity_area),
            'peak_running': max(row['running'] for row in timeline),
            'workers': per_worker, 'timeline': timeline,
            'tasks': [{'task': name, 'ready_at': exact(ready[name]),
                       'start': exact(slots[name][1]),
                       'ready_wait_minutes': exact(slots[name][1]-ready[name]),
                       'wait_with_spare_capacity': exact(spare_wait[name]),
                       'wait_with_all_workers_busy': exact(busy_wait[name])}
                      for name in sorted(slots)],
            'scope': 'observed intervals at supplied estimates, from zero to plan finish; '
                     'spare capacity assumes interchangeable workers; waiting may be intentional; '
                     'no execution, rescheduling, optimality or achievable speedup claim'}


def demo():
    tasks = {'tasks': [{'id': 'build', 'minutes': 4},
                       {'id': 'fixtures', 'minutes': 2},
                       {'id': 'check', 'minutes': 1, 'after': ['build', 'fixtures']}]}
    plan = {'workers': 2, 'finish': 7, 'schedule': [
        {'task': 'build', 'worker': 1, 'start': 0, 'finish': 4},
        {'task': 'fixtures', 'worker': 1, 'start': 4, 'finish': 6},
        {'task': 'check', 'worker': 1, 'start': 6, 'finish': 7}]}
    return tasks, plan, 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--tasks')
    parser.add_argument('--plan')
    parser.add_argument('--workers', type=int)
    parser.add_argument('--budget', type=Decimal)
    args = parser.parse_args()
    try:
        if args.demo:
            if any(x is not None for x in (args.tasks, args.plan, args.workers, args.budget)):
                raise ValueError('--demo cannot be combined with other options')
            result = analyze(*demo())
        else:
            if any(x is None for x in (args.tasks, args.plan, args.workers)):
                raise ValueError('--tasks, --plan and --workers are required')
            result = analyze(check.read_json(args.tasks), check.read_json(args.plan),
                             args.workers, args.budget)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['analyzed'] else 2
    except (ValueError, OSError, RecursionError, OverflowError) as exc:
        print('idlemap: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
