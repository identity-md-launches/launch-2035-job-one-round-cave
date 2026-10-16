#!/usr/bin/env python3
"""Offline replay of historical public data under aggregate extraction budgets."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from zipbatch import Rejected, local_path, plan


def main():
    source = local_path(Path(__file__).resolve().parents[1] / 'safezip/imd-openapi.json')
    payload = source.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == 'be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a'
    scratch = local_path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix='zipbatch-demo-') as directory:
        root = Path(directory)
        specs = []
        # Two workers could each receive the same capture in a separate tree.
        # Packaging and the two output copies are illustrative, data is genuine.
        for label in ['research', 'review']:
            archive = root / (label + '.zip')
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
                member = zipfile.ZipInfo('docs/imd/openapi.json', (2026, 10, 16, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                writer.writestr(member, payload)
            specs.append(dict(archive=archive, sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
        report = plan(specs, batch_bytes=2 * len(payload), batch_nodes=8,
                      batch_entries=2, seconds=10)
        assert report['totals']['uncompressed_bytes'] == 46264
        assert report['totals']['nodes_including_roots'] == 8
        # Each archive fits this limit alone; together they must be refused.
        for spec in specs:
            assert plan([spec], batch_bytes=len(payload))['ok']
        try:
            plan(specs, batch_bytes=len(payload))
        except Rejected as error:
            refusal = str(error)
        else:
            raise AssertionError('combined over-budget extraction was accepted')
        assert sorted(p.name for p in root.iterdir()) == ['research.zip', 'review.zip']
        print(json.dumps({'ok': True, 'network_used': False,
                          'historical_public_source': 'https://api.imd.fun/openapi.json',
                          'capture_bytes': len(payload), 'plan': report,
                          'each_fits_alone_but_batch_refused': refusal,
                          'nothing_extracted': True}, indent=2))


if __name__ == '__main__':
    main()
