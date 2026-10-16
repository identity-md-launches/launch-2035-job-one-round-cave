#!/usr/bin/env python3
"""Deterministic offline batch-budget and refusal checks."""
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from zipbatch import Rejected, plan


class BatchTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch, prefix='zipbatch-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = self.make('a.zip', [('docs/a', b'abcd'), ('empty/', b'')])
        self.b = self.make('b.zip', [('docs/b', b'xyz')])

    def make(self, name, members):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as writer:
            for member, payload in members:
                writer.writestr(member, payload)
        return dict(archive=path, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def test_exact_shared_limits(self):
        r = plan([self.a, self.b], batch_entries=3, batch_nodes=7, batch_bytes=7)
        self.assertEqual(r['totals'], dict(archives=2, entries=3,
                                         nodes_including_roots=7, uncompressed_bytes=7))
        self.assertTrue(r['all_payloads_checked'])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['a.zip', 'b.zip'])

    def test_aggregate_bytes(self):
        with self.assertRaises(Rejected):
            plan([self.a, self.b], batch_bytes=6)

    def test_aggregate_nodes(self):
        with self.assertRaises(Rejected):
            plan([self.a, self.b], batch_nodes=6)

    def test_aggregate_entries(self):
        with self.assertRaises(Rejected):
            plan([self.a, self.b], batch_entries=2)

    def test_implicit_parents(self):
        deep = self.make('deep.zip', [('a/b/c/d', b'')])
        self.assertEqual(plan([deep], batch_nodes=5)['totals']['nodes_including_roots'], 5)
        with self.assertRaises(Rejected):
            plan([deep], batch_nodes=4)

    def test_empty_archives_consume_roots(self):
        empty = self.make('empty.zip', [])
        r = plan([empty, empty], batch_nodes=2)
        self.assertEqual(r['totals']['nodes_including_roots'], 2)
        self.assertEqual(r['totals']['entries'], 0)
        with self.assertRaises(Rejected):
            plan([empty, empty], batch_nodes=1)

    def test_empty_after_exhausted_bytes_and_entries(self):
        empty = self.make('empty.zip', [])
        r = plan([self.b, empty], batch_entries=1, batch_bytes=3)
        self.assertEqual(r['totals']['uncompressed_bytes'], 3)

    def test_zero_byte_entry_after_exhausted_bytes(self):
        emptyfile = self.make('zero.zip', [('z', b'')])
        self.assertEqual(plan([self.b, emptyfile], batch_bytes=3)['totals']['entries'], 2)

    def test_one_byte_after_exhausted_bytes(self):
        one = self.make('one.zip', [('z', b'x')])
        with self.assertRaises(Rejected):
            plan([self.b, one], batch_bytes=3)

    def test_repeated_archive_counted_twice(self):
        r = plan([self.b, self.b])
        self.assertEqual(r['totals']['uncompressed_bytes'], 6)
        self.assertEqual(r['totals']['nodes_including_roots'], 6)

    def test_wrong_approval(self):
        with self.assertRaisesRegex(Rejected, 'SHA-256'):
            plan([self.a, dict(self.b, sha256='0' * 64)])

    def test_uppercase_approval(self):
        self.assertTrue(plan([dict(self.a, sha256=self.a['sha256'].upper())])['ok'])

    def test_declarations_validated_before_io(self):
        with patch('zipbatch.inspect_archive') as inspect:
            with self.assertRaises(Rejected):
                plan([self.a, dict(self.b, unexpected=True)])
            inspect.assert_not_called()

    def test_invalid_specs(self):
        for value in [[], {}, 'x', [None], [dict(self.a, sha256=None)],
                      [dict(self.a, sha256='ab')], [dict(self.a, archive=3)]]:
            with self.subTest(value=value), self.assertRaises(Rejected):
                plan(value)

    def test_archive_count_limit(self):
        with patch('zipbatch.inspect_archive') as inspect:
            with self.assertRaises(Rejected):
                plan([self.a, self.b], batch_archives=1)
            inspect.assert_not_called()

    def test_invalid_limits(self):
        names = ['batch_archives', 'batch_entries', 'batch_nodes', 'batch_bytes',
                 'entries', 'directory_bytes', 'archive_bytes', 'nodes',
                 'file_bytes', 'total_bytes', 'ratio']
        for name in names:
            for bad in [0, -1, True, 1.5, '3']:
                with self.subTest(name=name, bad=bad), self.assertRaises(Rejected):
                    plan([self.a], **{name: bad})

    def test_invalid_seconds(self):
        for value in [0, -1, True, float('nan'), float('inf'), '1', 10**1000]:
            with self.subTest(value=str(value)), self.assertRaises(Rejected):
                plan([self.a], seconds=value)

    def test_invalid_callback(self):
        with self.assertRaises(Rejected):
            plan([self.a], cancelled=True)

    def test_cancel_before_io(self):
        with patch('zipbatch.inspect_archive') as inspect:
            with self.assertRaisesRegex(Rejected, 'cancelled'):
                plan([self.a], cancelled=lambda: True)
            inspect.assert_not_called()

    def test_cancel_after_first_archive(self):
        from zipbatch import inspect_archive
        done = []
        def inspect(*args, **kw):
            result = inspect_archive(*args, **kw)
            done.append(True)
            return result
        with patch('zipbatch.inspect_archive', side_effect=inspect):
            with self.assertRaisesRegex(Rejected, 'cancelled'):
                plan([self.a, self.b], cancelled=lambda: bool(done))
        self.assertEqual(len(done), 1)

    def test_shared_deadline_without_sleep(self):
        from zipbatch import inspect_archive
        clock = [100.0]
        def inspect(*args, **kw):
            result = inspect_archive(*args, **kw)
            clock[0] += 2
            return result
        with patch('zipbatch.time.monotonic', side_effect=lambda: clock[0]):
            with patch('zipbatch.inspect_archive', side_effect=inspect) as inspector:
                with self.assertRaisesRegex(Rejected, 'time budget'):
                    plan([self.a, self.b], seconds=1)
                self.assertEqual(inspector.call_count, 1)

    def test_inherited_archive_budgets(self):
        for opts in [dict(archive_bytes=10), dict(file_bytes=2),
                     dict(total_bytes=2), dict(directory_bytes=10), dict(entries=1)]:
            with self.subTest(opts=opts), self.assertRaises(Rejected):
                plan([self.a], **opts)

    def test_unsafe_member(self):
        unsafe = self.make('bad.zip', [('../escape', b'x')])
        with self.assertRaisesRegex(Rejected, 'unsafe'):
            plan([self.a, unsafe])

    def test_symlink_member(self):
        link = zipfile.ZipInfo('link')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        unsafe = self.make('link.zip', [(link, b'target')])
        with self.assertRaisesRegex(Rejected, 'link or special'):
            plan([unsafe])

    def test_symlink_source(self):
        link = self.root / 'alias.zip'
        link.symlink_to('a.zip')
        with self.assertRaisesRegex(Rejected, 'symlink'):
            plan([dict(self.a, archive=link)])

    def test_outside_workspace(self):
        with self.assertRaisesRegex(Rejected, 'workspace'):
            plan([dict(self.a, archive=Path.cwd().parent / 'unused.zip')])

    def test_corrupt_payload(self):
        bad = self.make('corrupt.zip', [('file', b'abcd')])
        data = bytearray(bad['archive'].read_bytes())
        size, extra = struct.unpack_from('<HH', data, 26)
        data[30 + size + extra] ^= 1
        bad['archive'].write_bytes(data)
        bad['sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(zipfile.BadZipFile):
            plan([bad])

    def cli(self, *extra):
        return subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('zipbatch.py')),
                               '--archive', str(self.a['archive']), '--sha256', self.a['sha256'],
                               *extra], capture_output=True, text=True)

    def test_cli_success(self):
        run = self.cli()
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        self.assertEqual(json.loads(run.stdout)['totals']['entries'], 2)

    def test_cli_refusal(self):
        run = self.cli('--batch-bytes', '3')
        self.assertEqual(run.returncode, 2)
        self.assertFalse(json.loads(run.stdout)['ok'])

    def test_cli_unpaired_approval(self):
        run = self.cli('--archive', str(self.b['archive']))
        self.assertEqual(run.returncode, 2)
        self.assertIn('one --sha256', run.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
