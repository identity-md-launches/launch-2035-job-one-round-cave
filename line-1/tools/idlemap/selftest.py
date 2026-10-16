#!/usr/bin/env python3
"""Behavioral tests, including an independent integer-minute timeline oracle."""
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).with_name('idlemap.py')
spec = importlib.util.spec_from_file_location('idlemap_under_test', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class IdlemapTests(unittest.TestCase):
    def test_demo(self):
        r = m.analyze(*m.demo())
        self.assertEqual(r['busy_worker_minutes'], '7')
        self.assertEqual(r['idle_worker_minutes'], '7')
        self.assertEqual(r['ready_spare_worker_minutes'], '4')
        fixtures = next(t for t in r['tasks'] if t['task'] == 'fixtures')
        self.assertEqual(fixtures['ready_wait_minutes'], '4')
        self.assertEqual(fixtures['wait_with_spare_capacity'], '4')

    def test_busy_wait_and_dependency_wait(self):
        tasks, plan, _ = m.demo()
        plan['workers'] = 1
        r = m.analyze(tasks, plan, 1)
        fixtures = next(t for t in r['tasks'] if t['task'] == 'fixtures')
        check = next(t for t in r['tasks'] if t['task'] == 'check')
        self.assertEqual(fixtures['wait_with_all_workers_busy'], '4')
        self.assertEqual(check['ready_at'], '6')
        self.assertEqual(check['ready_wait_minutes'], '0')
        self.assertEqual(r['idle_worker_minutes'], '0')

    def test_leading_and_trailing_worker_idle(self):
        tasks = {'tasks': [{'id': 'a', 'minutes': 2}]}
        plan = {'workers': 3, 'finish': 5, 'schedule': [
            {'task': 'a', 'worker': 2, 'start': 3, 'finish': 5}]}
        r = m.analyze(tasks, plan, 3)
        self.assertEqual([w['idle_minutes'] for w in r['workers']], ['5', '3', '5'])
        self.assertEqual(r['idle_worker_minutes'], '13')
        self.assertEqual(r['ready_spare_worker_minutes'], '3')

    def test_decimal_and_touching_endpoints(self):
        tasks = {'tasks': [{'id': 'a', 'minutes': Decimal('0.1')},
                           {'id': 'b', 'minutes': Decimal('0.2'), 'after': ['a']}]}
        plan = {'workers': 2, 'finish': Decimal('0.3'), 'schedule': [
            {'task': 'a', 'worker': 1, 'start': 0, 'finish': Decimal('0.1')},
            {'task': 'b', 'worker': 1, 'start': Decimal('0.1'), 'finish': Decimal('0.3')}]}
        r = m.analyze(tasks, plan, 2)
        self.assertEqual(r['idle_worker_minutes'], '0.3')
        self.assertEqual(r['busy_worker_minutes'], '0.3')
        self.assertEqual(r['peak_running'], 1)
        self.assertTrue(all(t['ready_wait_minutes'] == '0' for t in r['tasks']))

    def test_invalid_plan_returns_only_check(self):
        tasks, plan, workers = m.demo()
        plan['schedule'][0]['finish'] = 5
        r = m.analyze(tasks, plan, workers)
        self.assertFalse(r['analyzed'])
        self.assertNotIn('timeline', r)
        self.assertFalse(m.analyze(*m.demo(), budget=6)['analyzed'])

    def test_malformed_graph(self):
        tasks, plan, workers = m.demo()
        tasks['tasks'][0]['after'] = ['check']
        with self.assertRaises(ValueError):
            m.analyze(tasks, plan, workers)

    def test_order_independent(self):
        tasks, plan, workers = m.demo()
        expected = m.analyze(tasks, plan, workers)
        tasks['tasks'].reverse()
        plan['schedule'].reverse()
        self.assertEqual(m.analyze(tasks, plan, workers), expected)

    def test_grid_oracle(self):
        rng = random.Random(3001)
        for trial in range(120):
            count = rng.randint(1, 12)
            workers = rng.randint(1, 4)
            tasks, rows, ends = [], [], {}
            free = [0] * workers
            for i in range(count):
                name = str(i)
                deps = [str(j) for j in range(i) if rng.random() < .22]
                length = rng.randint(1, 4)
                w = rng.randrange(workers)
                start = max([free[w]] + [ends[d] for d in deps]) + rng.randint(0, 2)
                ends[name] = start + length
                free[w] = ends[name]
                tasks.append({'id': name, 'minutes': length, 'after': deps})
                rows.append({'task': name, 'worker': w+1, 'start': start, 'finish': ends[name]})
            finish = max(ends.values())
            r = m.analyze({'tasks': tasks}, {'workers': workers, 'finish': finish,
                                          'schedule': rows}, workers)
            idle = opportunity = peak = 0
            spare = {str(i): 0 for i in range(count)}
            full = dict(spare)
            for minute in range(finish):
                active = [row for row in rows if row['start'] <= minute < row['finish']]
                queued = [row['task'] for row in rows
                          if row['start'] > minute and all(ends[d] <= minute
                              for d in tasks[int(row['task'])]['after'])]
                idle += workers - len(active)
                opportunity += min(workers-len(active), len(queued))
                peak = max(peak, len(active))
                for name in queued:
                    (spare if len(active) < workers else full)[name] += 1
            self.assertEqual(r['idle_worker_minutes'], str(idle), trial)
            self.assertEqual(r['ready_spare_worker_minutes'], str(opportunity), trial)
            self.assertEqual(r['peak_running'], peak, trial)
            for row in r['tasks']:
                self.assertEqual(row['wait_with_spare_capacity'], str(spare[row['task']]))
                self.assertEqual(row['wait_with_all_workers_busy'], str(full[row['task']]))

    def test_cli(self):
        for args, code in [(['--demo'], 0), ([], 1),
                           (['--demo', '--workers', '2'], 1),
                           (['--tasks', 'line-1/tools/plancheck/tasks.json',
                             '--plan', 'line-1/tools/plancheck/plan.json',
                             '--workers', '2', '--budget', '0'], 2)]:
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), *args],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stderr)
            if code == 0:
                self.assertTrue(json.loads(result.stdout)['analyzed'])


if __name__ == '__main__':
    unittest.main()
