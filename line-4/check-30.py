"""Workspace-only round verification plus one optional public description GET."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path.cwd()
rows = []
for tool in ('servercheck', 'oauthcheck'):
    command = [sys.executable, '-B', 'line-4/tools/' + tool + '/selftest.py']
    run = subprocess.run(command, text=True, capture_output=True, timeout=60)
    rows.append({'command': command, 'exit': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
    if run.returncode:
        raise RuntimeError(run.stderr)
spec = importlib.util.spec_from_file_location('round30_server', ROOT/'line-4/tools/servercheck/servercheck.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
capture = ROOT/'line-4/tools/apidelta/imd-openapi.json'
old, digest = module.api.load(capture)
baseline = module.compare(old, old)
assert baseline['findings'] == []
result = {'tests': rows, 'baseline_sha256': digest, 'baseline_self_compare': baseline, 'demo': module.demo()}
if '--live' in sys.argv:
    url = 'https://api.imd.fun/openapi.json'
    request = urllib.request.Request(url, headers={'User-Agent': 'Pepeolithic-ServerCheck/30.0', 'Accept': 'application/json'})
    # Explicitly disable implicit proxy/environment discovery.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(module.api.MAX_BYTES + 1)
        if len(raw) > min(module.api.MAX_BYTES, 100000):
            raise ValueError('live capture exceeds deliverable budget')
        path = ROOT/'line-4/live-openapi-30.json'
        path.write_bytes(raw)
        current, current_digest = module.api.load(path)
        live = module.compare(old, current)
        live.update(source=url, current_sha256=current_digest, baseline_sha256=digest)
        result['live'] = live
    except (OSError, ValueError) as exc:
        result['live'] = {'source': url, 'unavailable': str(exc)}
(ROOT/'line-4/check-results-30.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'test_suites_passed': len(rows), 'baseline_operations': baseline['operations_compared'],
                  'demo_counts': result['demo']['counts'], 'live': result.get('live')}, indent=2))
