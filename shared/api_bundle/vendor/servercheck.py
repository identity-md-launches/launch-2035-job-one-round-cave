#!/usr/bin/env python3
"""Bounded, offline checks for effective OpenAPI server destinations."""
import argparse
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import re
import sys

PREVIOUS = Path(__file__).resolve().with_name('oauthcheck.py')
spec = importlib.util.spec_from_file_location('servercheck_oauth', PREVIOUS)
oauth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oauth)
api = oauth.api
MAX_SERVERS = 64
MAX_EXPANSIONS = 256
MAX_WORK = 100000
MAX_CHARACTERS = 2 * 1024 * 1024
TOKEN = re.compile(r'\{([^{}]+)\}')


def effective(document, item, method):
    """An explicit narrower layer wins; empty narrower arrays are refused."""
    for layer in (item[method], item):
        if 'servers' in layer:
            api.require(isinstance(layer['servers'], list) and layer['servers'],
                        'empty or invalid path/operation servers is unsupported; omit to inherit')
            return layer['servers']
    raw = document.obj.get('servers', [])
    api.require(isinstance(raw, list), 'root servers must be an array')
    return raw or [{'url': '/'}]


def model(raw):
    api.require(isinstance(raw, list) and 0 < len(raw) <= MAX_SERVERS,
                'effective servers must have 1..64 entries')
    finite, symbolic, defaults = set(), set(), set()
    work = 0
    characters = 0
    for entry in raw:
        api.require(isinstance(entry, dict) and '$ref' not in entry, 'server must be an inline object')
        url = entry.get('url')
        api.require(isinstance(url, str) and 0 < len(url) <= 4096 and
                    not any(c.isspace() or ord(c) < 32 for c in url),
                    'server URL must be a nonempty reference of at most 4096 characters without whitespace')
        names = sorted(set(TOKEN.findall(url)))
        api.require(not any(c in TOKEN.sub('', url) for c in '{}'), 'malformed server URL template')
        variables = entry.get('variables', {})
        api.require(isinstance(variables, dict) and len(variables) <= 32 and len(names) <= 32,
                    'server variables must be an object of at most 32 entries')
        api.require(set(names) <= variables.keys(), 'undeclared server URL variable')
        choices, signature, selected = [], [], {}
        unlimited = False
        for name in names:
            var = variables[name]
            api.require(isinstance(var, dict) and isinstance(var.get('default'), str),
                        'server variable requires a string default')
            default = var['default']
            # Restrict substitution strings to keep literal expansion bounded and unambiguous.
            def valid(v):
                return isinstance(v, str) and len(v) <= 4096 and not any(
                    c.isspace() or ord(c) < 32 or c in '{}' for c in v)
            api.require(valid(default), 'unsupported server variable default')
            selected[name] = default
            values = var.get('enum')
            if 'enum' in var:
                api.require(isinstance(values, list) and 0 < len(values) <= MAX_EXPANSIONS and
                            all(valid(v) for v in values) and default in values,
                            'server enum must contain 1..256 strings including its default')
                values = tuple(sorted(set(values)))
            else:
                unlimited = True
                values = None
            choices.append(values)
            signature.append((name, values))
        render = lambda values: TOKEN.sub(lambda m: values[m.group(1)], url)
        default_url = render(selected)
        api.require(len(default_url) <= 8192, 'default server reference exceeds 8192 characters')
        defaults.add(default_url)
        if unlimited:
            symbolic.add((url, tuple(signature)))
            work += 1
        else:
            count = 1
            for values in choices:
                count *= len(values)
            api.require(count <= MAX_EXPANSIONS, 'server expansion exceeds 256 combinations')
            work += count
            for values in itertools.product(*choices):
                expanded = render(dict(zip(names, values)))
                api.require(len(expanded) <= 8192, 'expanded server reference exceeds 8192 characters')
                characters += len(expanded)
                api.require(characters <= MAX_CHARACTERS, 'server expansions exceed 2 Mi characters')
                finite.add(expanded)
    return finite, symbolic, defaults, work, characters


class Analyzer(oauth.Analyzer):
    def __init__(self, old, new):
        super().__init__(old, new)
        self.server_work = 0
        self.server_cache = {}
        self.server_characters = 0

    def destinations(self, doc, item, method):
        raw = effective(doc, item, method)
        key = api.canonical(raw)
        if key not in self.server_cache:
            result = model(raw)
            self.server_work += result[3]
            api.require(self.server_work <= MAX_WORK, 'server expansion work exceeds 100000')
            self.server_characters += result[4]
            api.require(self.server_characters <= 4 * MAX_CHARACTERS,
                        'cached server expansions exceed 8 Mi characters')
            self.server_cache[key] = result
        return self.server_cache[key]

    def operation(self, path, method, old_item, new_item):
        super().operation(path, method, old_item, new_item)
        before = self.destinations(self.old, old_item, method)
        after = self.destinations(self.new, new_item, method)
        loc = api.pointer('/paths', path) + '/' + method + '/servers'
        missing = before[0] - after[0]
        if missing:
            self.emit('review' if after[1] else 'breaking',
                      'server_destination_unresolved' if after[1] else 'server_destination_removed', loc,
                      str(len(missing)) + ' old literal/finite server URL references are not retained '
                      'by the new finite declarations. ' +
                      ('New unbounded templates require manual coverage review.' if after[1] else
                       'Existing clients selecting these destinations may fail; no endpoint was contacted.'))
        if not before[1] <= after[1]:
            self.emit('review', 'server_template_coverage_unresolved', loc,
                      'An old unbounded server template lacks an identical new URL/variable-domain declaration; '
                      'coverage is unresolved, not proved incompatible.')
        if before[2] != after[2]:
            self.emit('review', 'server_defaults_changed', loc,
                      'Effective default-substituted server references changed; review client selection behavior.')


def compare(old, new):
    analyzer = Analyzer(old, new)
    result = analyzer.run()
    result['extension'] = 'servercheck-v1 (includes oauthcheck and earlier line 4 analyzers)'
    result['server_expansion_work'] = analyzer.server_work
    return result


def demo():
    capture = oauth.scheme.auth.depend.unique.const.multiple.bound.BASE.with_name('imd-openapi.json')
    old, digest = api.load(capture)
    new = copy.deepcopy(old)
    # Clearly hypothetical migration of one real captured operation; never fetched.
    path = sorted(new['paths'])[0]
    method = sorted(set(new['paths'][path]) & api.METHODS)[0]
    new['paths'][path][method]['servers'] = [{'url': 'https://example.invalid/migrated'}]
    result = compare(old, new)
    api.require(any(f['code'] == 'server_destination_removed' for f in result['findings']),
                'demo failed to detect hypothetical destination removal')
    result.update(capture_sha256=digest, baseline_source='https://api.imd.fun/openapi.json',
                  demo='Hypothetical operation server migration of the saved public description; no endpoint contacted.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    diff = commands.add_parser('compare')
    diff.add_argument('old')
    diff.add_argument('new')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            result = demo()
        else:
            old, oh = api.load(args.old)
            new, nh = api.load(args.new)
            result = compare(old, new)
            result.update(old_sha256=oh, new_sha256=nh)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if args.command == 'demo' else {
            'breaking': 1, 'review_required': 3, 'no_detected_breakage': 0}[result['status']]
    except (api.Invalid, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print('servercheck: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
