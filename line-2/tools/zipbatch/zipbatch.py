#!/usr/bin/env python3
"""Plan separate ZIP extractions against one aggregate budget; never extract."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import time
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'zipgate'))
from zipgate import Rejected, local_path, positive, process as inspect_archive


def plan(archives, *, batch_archives=32, batch_entries=1000,
         batch_nodes=32000, batch_bytes=67108864, entries=1000,
         directory_bytes=2097152, archive_bytes=33554432, nodes=32000,
         file_bytes=16777216, total_bytes=67108864, ratio=200,
         seconds=None, cancelled=None):
    """Validate every payload, then budget separate complete extraction trees.

    Each item is exactly {'archive': workspace_path, 'sha256': reviewed_digest}.
    Output roots each count as one node, even for empty ZIPs. Repeated archives
    count repeatedly. No extraction, output allocation or saved-report trust.
    """
    options = dict(entries=entries, directory_bytes=directory_bytes,
                   archive_bytes=archive_bytes, nodes=nodes,
                   file_bytes=file_bytes, total_bytes=total_bytes, ratio=ratio)
    for name, value in dict(options, batch_archives=batch_archives,
                            batch_entries=batch_entries, batch_nodes=batch_nodes,
                            batch_bytes=batch_bytes).items():
        positive(name, value)
    if (not isinstance(archives, (list, tuple)) or not archives
            or len(archives) > batch_archives):
        raise Rejected('archives must be a nonempty bounded list/tuple')
    if seconds is not None:
        try:
            valid = (not isinstance(seconds, bool) and isinstance(seconds, (int, float))
                     and math.isfinite(seconds) and seconds > 0)
        except OverflowError:
            valid = False
        if not valid:
            raise Rejected('seconds must be a finite positive number')
    if cancelled is not None and not callable(cancelled):
        raise Rejected('cancelled must be callable')
    started = time.monotonic()

    def checkpoint():
        if cancelled is not None and cancelled():
            raise Rejected('batch cancelled')
        if seconds is not None and time.monotonic() - started >= seconds:
            raise Rejected('batch time budget exceeded')
        return False

    # Validate every declaration before inspecting any archive.
    specs = []
    for item in archives:
        checkpoint()
        if not isinstance(item, dict) or set(item) != {'archive', 'sha256'}:
            raise Rejected('each archive needs exactly archive and sha256')
        if not isinstance(item['archive'], (str, Path)):
            raise Rejected('archive must be a workspace path')
        if not isinstance(item['sha256'], str) or re.fullmatch(
                r'[0-9a-fA-F]{64}', item['sha256']) is None:
            raise Rejected('each archive needs an approved 64-hex SHA-256')
        specs.append((local_path(item['archive']), item['sha256']))
    used_entries = used_nodes = used_bytes = 0
    reports = []
    for source, digest in specs:
        checkpoint()
        if used_nodes >= batch_nodes:
            raise Rejected('batch node limit exceeded by extraction root')
        # Tighten inherited pre-parser and payload limits to remaining budget.
        # A zero remainder uses one as the parser cap, then exact accounting
        # below distinguishes a truly empty archive from a one-entry overrun.
        remaining = dict(options)
        remaining['entries'] = min(entries, max(1, batch_entries - used_entries))
        remaining['nodes'] = min(nodes, max(1, batch_nodes - used_nodes - 1))
        remaining['total_bytes'] = min(total_bytes, max(1, batch_bytes - used_bytes))
        checked = inspect_archive(source, expected_sha256=digest,
                                  cancelled=checkpoint, **remaining)
        paths = set()
        for entry in checked['entries']:
            checkpoint()
            parts = entry['path'].split('/')
            for depth in range(1, len(parts) + 1):
                paths.add('/'.join(parts[:depth]))
                if used_nodes + 1 + len(paths) > batch_nodes:
                    raise Rejected('batch node limit exceeded')
        count = len(checked['entries'])
        size = checked['total_bytes']
        used_entries += count
        used_nodes += 1 + len(paths)
        used_bytes += size
        if used_entries > batch_entries:
            raise Rejected('batch entry limit exceeded')
        if used_bytes > batch_bytes:
            raise Rejected('batch byte limit exceeded')
        reports.append({'archive': str(source.relative_to(Path.cwd().resolve())),
                        'archive_sha256': checked['archive_sha256'],
                        'entries': count, 'nodes_including_root': 1 + len(paths),
                        'uncompressed_bytes': size,
                        'preflight': checked['preflight']})
    checkpoint()
    return {'ok': True, 'mode': 'batch-plan', 'all_payloads_checked': True,
            'separate_output_roots': True, 'archives': reports,
            'totals': {'archives': len(reports), 'entries': used_entries,
                       'nodes_including_roots': used_nodes,
                       'uncompressed_bytes': used_bytes},
            'batch_limits': {'archives': batch_archives, 'entries': batch_entries,
                             'nodes_including_roots': batch_nodes,
                             'uncompressed_bytes': batch_bytes}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='append', required=True,
                        help='workspace ZIP path; repeat in approval order')
    parser.add_argument('--sha256', action='append', required=True,
                        help='reviewed digest; nth digest approves nth archive')
    for name, default in [('batch-archives', 32), ('batch-entries', 1000),
                          ('batch-nodes', 32000), ('batch-bytes', 67108864),
                          ('entries', 1000), ('directory-bytes', 2097152),
                          ('archive-bytes', 33554432), ('nodes', 32000),
                          ('file-bytes', 16777216), ('total-bytes', 67108864),
                          ('ratio', 200)]:
        parser.add_argument('--' + name, type=int, default=default)
    parser.add_argument('--seconds', type=float)
    args = vars(parser.parse_args())
    paths, hashes = args.pop('archive'), args.pop('sha256')
    if len(paths) != len(hashes):
        parser.error('one --sha256 is required for each --archive')
    specs = [dict(archive=path, sha256=digest) for path, digest in zip(paths, hashes)]
    try:
        report = plan(specs, **args)
    except (ValueError, OSError, zipfile.BadZipFile, NotImplementedError,
            RuntimeError, EOFError, zlib.error) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
