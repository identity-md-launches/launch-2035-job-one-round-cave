#!/usr/bin/env python3
"""Check the delivered shared folder in isolation, with no line folders present."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent.parent
    assert Path.cwd().resolve() == root
    scratch = root / 'test/scratch/shared30'
    shutil.copytree(root / 'shared/api_bundle', scratch / 'shared/api_bundle', dirs_exist_ok=True)
    results = []
    for script in ['selftest.py', 'demo.py', 'server_demo.py']:
        command = [sys.executable, '-B', 'shared/api_bundle/' + script]
        run = subprocess.run(command, cwd=scratch, capture_output=True, text=True, timeout=60)
        match = re.search(r'Ran (\d+) tests?', run.stderr)
        results.append({'script': script, 'exit': run.returncode, 'passed': run.returncode == 0,
                        'tests': int(match.group(1)) if match else 0,
                        'stdout_sha256': hashlib.sha256(run.stdout.encode()).hexdigest(),
                        'stderr_sha256': hashlib.sha256(run.stderr.encode()).hexdigest(),
                        'error': run.stderr[:1000] if run.returncode else ''})
    report = {'isolated_copy': True, 'results': results}
    (root / 'gathering/shared-check-results-30.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if all(row['passed'] for row in results) else 1


if __name__ == '__main__':
    sys.exit(main())
