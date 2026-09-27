#!/usr/bin/env python3
"""Check that a release tag names exactly the version in the source, and that
the version is new.

    python tools/release_check.py --tag v2026.9.0rc1 [--require-on-main] [--github-output FILE]

Checks:
* the tag is 'v' + the version in pyproject.toml, which is a valid PEP 440
  version already in normal form (so the tag, the wheels' file names and the
  index agree character for character);
* with --require-on-main, the checked-out commit is on origin/main (so only a
  reviewed commit can be released; needs the full history);
* neither PyPI nor TestPyPI already has the version (versions are never
  reused); a version present on TestPyPI only is reported, since TestPyPI's
  project is independent and may hold rehearsals.

Writes version=..., prerelease=true|false to --github-output. Exit status 0
when every check passes.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# PEP 440 public versions IES Optimiser uses: YYYY.M.PATCH, optionally aN/bN/rcN (normal form).
VERSION = re.compile(r'^(\d{4})\.(\d{1,2})\.(\d+)((a|b|rc)(\d+))?$')
INDEXES = {'pypi': 'https://pypi.org/pypi/ies-optimiser/json', 'testpypi': 'https://test.pypi.org/pypi/ies-optimiser/json'}


def published(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ies-optimiser-release-check'}),
                                    timeout=30) as r:
            return set(json.load(r)['releases'])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return set()                     # no project (which does not mean the name can be registered)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tag', required=True)
    ap.add_argument('--require-on-main', action='store_true')
    ap.add_argument('--github-output')
    args = ap.parse_args(argv)
    problems = []

    with open(os.path.join(ROOT, 'pyproject.toml'), 'rb') as f:
        version = tomllib.load(f)['project']['version']
    m = VERSION.match(version)
    if not m:
        problems.append('pyproject.toml version ' + repr(version) + ' is not YYYY.M.PATCH[aN|bN|rcN] in normal form')
    elif not 1 <= int(m.group(2)) <= 12:
        problems.append('month ' + m.group(2) + ' in ' + version + ' is not a month')
    if args.tag != 'v' + version:
        problems.append('tag ' + args.tag + ' does not name the source version (expected v' + version + ')')
    prerelease = bool(m and m.group(4))
    print('version ' + version + (' (prerelease)' if prerelease else ' (final)'))

    if args.require_on_main:
        head = subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        on_main = subprocess.run(['git', '-C', ROOT, 'merge-base', '--is-ancestor', 'HEAD', 'origin/main']).returncode == 0
        print('commit ' + head + (' is' if on_main else ' is NOT') + ' on origin/main')
        if not on_main:
            problems.append('the tagged commit ' + head + ' is not on origin/main')

    for name, url in INDEXES.items():
        releases = published(url)
        print(name + ': ' + (', '.join(sorted(releases)) if releases else 'no releases visible'))
        if version in releases:
            problems.append(version + ' already exists on ' + name + '; versions are never reused')

    if args.github_output:
        with open(args.github_output, 'a', encoding='utf-8') as f:
            f.write('version=' + version + '\nprerelease=' + ('true' if prerelease else 'false') + '\n')
    for p in problems:
        print('FAIL ' + p)
    print('PASS' if not problems else 'FAILED')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
