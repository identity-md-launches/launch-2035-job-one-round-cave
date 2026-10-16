#!/usr/bin/env python3
"""Independent finite-set and regression checks; no network."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import servercheck as s


def doc(servers=None):
    result = {'openapi': '3.1.0', 'info': {'title': 'Test', 'version': '1'},
              'paths': {'/a~b/c': {'get': {'responses': {}}}}}
    if servers is not None:
        result['servers'] = servers
    return result


def codes(a, b):
    return {f['code'] for f in s.compare(a, b)['findings']}


def template(values=('one', 'two'), default='one'):
    var = {'default': default}
    if values is not None:
        var['enum'] = list(values)
    return {'url': 'https://{region}.example.invalid/v1', 'variables': {'region': var}}


class Checks(unittest.TestCase):
    def test_capture_demo(self):
        self.assertTrue(any(f['code'] == 'server_destination_removed' for f in s.demo()['findings']))
        capture = s.oauth.scheme.auth.depend.unique.const.multiple.bound.BASE.with_name('imd-openapi.json')
        a, _ = s.api.load(capture)
        self.assertEqual(s.compare(a, a)['findings'], [])

    def test_root_default_and_empty(self):
        a = doc()
        b = doc([])
        self.assertNotIn('server_destination_removed', codes(a, b))
        self.assertEqual(s.model(s.effective(s.api.Document(a), a['paths']['/a~b/c'], 'get'))[0], {'/'})

    def test_removed_added_and_duplicate(self):
        a = doc([{'url': '/v1'}, {'url': '/v2'}])
        b = doc([{'url': '/v2'}])
        self.assertIn('server_destination_removed', codes(a, b))
        self.assertNotIn('server_destination_removed', codes(b, a))
        c = doc([{'url': '/v2'}, {'url': '/v1'}, {'url': '/v1'}])
        self.assertNotIn('server_destination_removed', codes(a, c))

    def test_overrides(self):
        a = doc([{'url': '/root'}])
        a['paths']['/a~b/c']['servers'] = [{'url': '/path'}]
        a['paths']['/a~b/c']['get']['servers'] = [{'url': '/operation'}]
        b = copy.deepcopy(a)
        b['servers'] = [{'url': '/new-root'}]
        b['paths']['/a~b/c']['servers'] = [{'url': '/new-path'}]
        self.assertNotIn('server_destination_removed', codes(a, b))
        del b['paths']['/a~b/c']['get']['servers']
        self.assertIn('server_destination_removed', codes(a, b))

    def test_finite_independent_oracle(self):
        # 49 domain pairs, each compared against explicit literal destination sets.
        subsets = [v for n in range(1, 4) for v in itertools.combinations(('one', 'two', 'three'), n)]
        for old in subsets:
            for new in subsets:
                with self.subTest(old=old, new=new):
                    a = doc([template(old, old[0])])
                    b = doc([template(new, new[0])])
                    expected = bool(set(old) - set(new))
                    self.assertEqual('server_destination_removed' in codes(a, b), expected)
                    literal = doc([{'url': 'https://' + v + '.example.invalid/v1'} for v in new])
                    self.assertEqual('server_destination_removed' in codes(a, literal), expected)

    def test_repeated_variable_correlated(self):
        a = {'url': '/{x}/{x}', 'variables': {'x': {'default': 'a', 'enum': ['a', 'b']}}}
        self.assertEqual(s.model([a])[0], {'/a/a', '/b/b'})

    def test_two_variables_and_substitution_not_recursive(self):
        a = {'url': '/{x}/{y}', 'variables': {'x': {'default': 'a', 'enum': ['a', 'b']},
                                           'y': {'default': 'c', 'enum': ['c', 'd']}}}
        self.assertEqual(s.model([a])[0], {'/a/c', '/a/d', '/b/c', '/b/d'})
        a['variables']['x']['enum'] = ['a', '{y}']
        with self.assertRaises(s.api.Invalid):
            s.model([a])

    def test_unbounded_is_unresolved(self):
        a = doc([template()])
        b = doc([template(None)])
        self.assertIn('server_destination_unresolved', codes(a, b))
        self.assertNotIn('server_destination_removed', codes(a, b))
        self.assertIn('server_template_coverage_unresolved', codes(b, a))
        c = copy.deepcopy(b)
        c['servers'][0]['variables']['region']['description'] = 'Only annotation'
        self.assertNotIn('server_template_coverage_unresolved', codes(b, c))
        self.assertNotIn('server_template_coverage_unresolved', codes(b, b))

    def test_defaults_and_literal_equality(self):
        a = doc([template()])
        b = doc([template(default='two')])
        self.assertIn('server_defaults_changed', codes(a, b))
        self.assertNotIn('server_destination_removed', codes(a, b))
        self.assertIn('server_destination_removed', codes(doc([{'url': '/v1'}]), doc([{'url': '/v1/'}])))

    def test_invalid_identical_effective_declarations(self):
        entries = [None, {}, {'url': ''}, {'url': 'has space'}, {'url': '/{x}'},
                   {'url': '/{x'}, {'url': '/' ,'variables': []}, {'$ref': '#/server'},
                   template([], 'one'), template(('two',), 'one'),
                   {'url': '/{x}', 'variables': {'x': {'default': 1}}}]
        for entry in entries:
            with self.subTest(entry=entry), self.assertRaises(s.api.Invalid):
                a = doc([entry])
                s.compare(a, a)
        for layer in ('path', 'operation'):
            a = doc()
            item = a['paths']['/a~b/c']
            (item if layer == 'path' else item['get'])['servers'] = []
            with self.assertRaises(s.api.Invalid):
                s.compare(a, a)

    def test_unused_invalid_declarations_ignored(self):
        a = doc([None])
        a['paths']['/a~b/c']['servers'] = [{'url': '/valid'}]
        self.assertEqual(s.compare(a, a)['findings'], [])

    def test_expansion_limits_and_work_budget(self):
        var = {'default': '0', 'enum': [str(n) for n in range(17)]}
        a = doc([{'url': '/{x}/{y}', 'variables': {'x': var, 'y': var}}])
        with self.assertRaises(s.api.Invalid):
            s.compare(a, a)
        a = doc([{'url': '/'}] * 65)
        with self.assertRaises(s.api.Invalid):
            s.compare(a, a)
        limit = s.MAX_WORK
        s.MAX_WORK = 0
        try:
            with self.assertRaises(s.api.Invalid):
                s.compare(doc(), doc())
        finally:
            s.MAX_WORK = limit

    def test_character_limits(self):
        a = {'url': '/{x}/{y}/{z}', 'variables': {n: {'default': 'v' * 4096}
                                                for n in ('x', 'y', 'z')}}
        with self.assertRaises(s.api.Invalid):
            s.model([a])
        limit = s.MAX_CHARACTERS
        s.MAX_CHARACTERS = 1
        try:
            with self.assertRaises(s.api.Invalid):
                s.compare(doc([{'url': '/long'}]), doc())
        finally:
            s.MAX_CHARACTERS = limit

    def test_inherited_retained_deterministic_nonmutation(self):
        a = doc()
        a['paths']['/a~b/c']['get']['requestBody'] = {'content': {'application/json': {
            'schema': {'type': 'string', 'maxLength': 20}}}}
        b = copy.deepcopy(a)
        b['paths']['/a~b/c']['get']['requestBody']['content']['application/json']['schema']['maxLength'] = 10
        original = copy.deepcopy((a, b))
        before = s.oauth.compare(a, b)['findings']
        after = s.compare(a, b)
        self.assertTrue(all(f in after['findings'] for f in before))
        self.assertTrue(any(f['code'] == 'size_bound_incompatible' for f in after['findings']))
        self.assertEqual(after, s.compare(a, b))
        self.assertEqual((a, b), original)
        change = s.compare(doc(), doc([{'url': '/v2'}]))
        self.assertTrue(any(f['location'] == '/paths/~1a~0b~1c/get/servers' for f in change['findings']))

    def test_cli_exits(self):
        root = Path('test/scratch')
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            a, b = Path(tmp)/'a.json', Path(tmp)/'b.json'
            old = doc([template()])
            a.write_text(json.dumps(old))
            for new, exit_code in ((old, 0), (doc([{'url': '/other'}]), 1),
                                   (doc([template(default='two')]), 3), (doc([None]), 2)):
                b.write_text(json.dumps(new))
                run = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('servercheck.py')),
                                      'compare', str(a), str(b)], capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, exit_code, run.stderr)
                if exit_code != 2:
                    self.assertEqual(len(json.loads(run.stdout)['old_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
