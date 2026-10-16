#!/usr/bin/env python3
"""Compare a hypothetical destination migration in saved public API bytes."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import api_bundle


def demo():
    capture = Path(__file__).with_name('imd-openapi.json').read_bytes()
    old = json.loads(capture)
    new = copy.deepcopy(old)
    new['paths']['/requests/quote']['post']['servers'] = [{'url': 'https://example.invalid/migrated'}]
    scratch = Path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='server-bundle-', dir=scratch) as directory:
        paths, hashes = [], []
        for label, document in [('old', old), ('new', new)]:
            path = Path(directory) / (label + '.zip')
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(zipfile.ZipInfo('openapi.json'), json.dumps(document))
            paths.append(path)
            hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        unchanged = api_bundle.compare(paths[0], paths[0], old_sha256=hashes[0],
                                       new_sha256=hashes[0], servers=True)
        changed = api_bundle.compare(*paths, old_sha256=hashes[0], new_sha256=hashes[1],
                                     servers=True, seconds=10)
        assert unchanged['findings'] == []
        assert changed['status'] == 'breaking'
        assert any(row['code'] == 'server_destination_removed' for row in changed['findings'])
        return {'baseline_source': 'https://api.imd.fun/openapi.json',
                'baseline_sha256': hashlib.sha256(capture).hexdigest(),
                'trial': 'Hypothetical destination migration of one captured operation.',
                'network_used': False, 'files_extracted': 0,
                'unchanged_status': unchanged['status'], 'changed': changed}


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))
