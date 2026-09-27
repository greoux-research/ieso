#!/usr/bin/env python3
"""Verify an IES Optimiser release as installed from a package index.

    python tools/verify_index_install.py --index testpypi|pypi --version V \\
        --sha256sums FILE --bundle DIR --report DIR

Run it with the Python to be tested, outside any checkout. In a fresh
virtual environment it:

1. installs ies-optimiser==V alone (no dependencies) from the chosen index --
   TestPyPI or PyPI, and nothing else -- as a binary wheel, and checks from
   pip's installation report that the file came from that index's file host
   and that its SHA-256 is one of the release's recorded hashes (SHA256SUMS
   from the build that was tested);
2. installs ies-optimiser's own dependencies, as its metadata declares them, from
   production PyPI only (a separate, explicit step: no combined or fallback
   index), plus pytest and jsonschema, all as wheels;
3. runs the installed-artifact tests and the native inspection
   (tools/test_installed_wheel.py, check_installed) with PATH reduced to the
   environment;
4. with --index pypi, also installs the unversioned 'ies-optimiser' into a second fresh
   environment -- what 'pip install ies-optimiser' does -- and checks it selects V.

REPORT receives the pip reports, the installed listing and the test reports.
--index-url and --file-host override the index (a local rehearsal index).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # this tool's own directory, for its sibling
import test_installed_wheel as t                                    # noqa: E402

INDEXES = {
    'testpypi': ('https://test.pypi.org/simple/', 'test-files.pythonhosted.org'),
    'pypi': ('https://pypi.org/simple/', 'files.pythonhosted.org'),
}
PYPI = 'https://pypi.org/simple/'


def pip(py, *args, **kw):
    return subprocess.run([py, '-m', 'pip'] + list(args), **kw)


def install_from_index(py, spec, index_url, report_file, attempts):
    # A new release can take a few minutes to appear on an index's mirrors.
    for attempt in range(attempts):
        out = pip(py, 'install', '--no-deps', '--only-binary=:all:', '--no-cache-dir', '--index-url', index_url,
                  '--report', report_file, spec)
        if out.returncode == 0:
            return True
        if attempt + 1 < attempts:
            print('not installable yet; retrying in 30 s', flush=True)
            time.sleep(30)
    return False


def check_origin(report_file, version, host, hashes):
    with open(report_file, encoding='utf-8') as f:
        items = json.load(f)['install']
    problems = []
    if len(items) != 1:
        return ['expected one installed item, got ' + str(len(items))]
    item = items[0]
    meta, info = item['metadata'], item['download_info']
    url = info['url']
    digest = info.get('archive_info', {}).get('hashes', {}).get('sha256') or \
        info.get('archive_info', {}).get('hash', '').replace('sha256=', '')
    print('installed ' + meta['name'] + ' ' + meta['version'] + ' from ' + url, flush=True)
    if re.sub(r'[-_.]+', '-', meta['name']).lower() != 'ies-optimiser' or meta['version'] != version:
        problems.append('installed ' + meta['name'] + ' ' + meta['version'] + ', expected ies-optimiser ' + version)
    if host and urlparse(url).hostname != host:
        problems.append('downloaded from ' + str(urlparse(url).hostname) + ', expected ' + host)
    if not url.endswith('.whl'):
        problems.append('not a wheel: ' + url)
    name = os.path.basename(urlparse(url).path)
    if hashes.get(name) != digest:
        problems.append(name + ': sha256 ' + str(digest) + ' is not the tested artifact\'s ' + str(hashes.get(name)))
    return problems


def dependencies(py):
    code = ('import importlib.metadata as m; '
            'print("\\n".join(r for r in (m.requires("ies-optimiser") or []) if "extra ==" not in r))')
    out = subprocess.run([py, '-c', code], capture_output=True, text=True, check=True)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def read_sums(path):
    hashes = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                digest, name = line.split(None, 1)
                hashes[os.path.basename(name.strip().lstrip('*'))] = digest
    return hashes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--index', choices=sorted(INDEXES), required=True)
    ap.add_argument('--version', required=True)
    ap.add_argument('--sha256sums', required=True)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--index-url', help='override the index (rehearsal)')
    ap.add_argument('--file-host', help='override the expected file host ("" to skip)')
    ap.add_argument('--attempts', type=int, default=20)
    args = ap.parse_args(argv)
    index_url, host = INDEXES[args.index]
    index_url = args.index_url or index_url
    host = host if args.file_host is None else args.file_host
    hashes = read_sums(args.sha256sums)
    bundle, report = os.path.abspath(args.bundle), os.path.abspath(args.report)
    os.makedirs(report, exist_ok=True)
    root = tempfile.mkdtemp(prefix='ies-optimiser-index-')
    failures = []

    venv = os.path.join(root, 'venv')
    subprocess.run([sys.executable, '-m', 'venv', venv], check=True)
    py = t.python(venv)
    pip(py, 'install', '-q', '--upgrade', 'pip', check=True)
    first = os.path.join(report, 'pip-report-ies-optimiser.json')
    if not install_from_index(py, 'ies-optimiser==' + args.version, index_url, first, args.attempts):
        print('FAIL: ies-optimiser==' + args.version + ' could not be installed from ' + index_url)
        return 1
    failures += check_origin(first, args.version, host, hashes)
    deps = dependencies(py)
    print('dependencies from PyPI: ' + ', '.join(deps), flush=True)
    if pip(py, 'install', '--only-binary=:all:', '--index-url', PYPI, '--report',
           os.path.join(report, 'pip-report-dependencies.json'), *deps, 'pytest', 'jsonschema').returncode != 0:
        failures.append('dependencies from PyPI')
    if pip(py, 'check').returncode != 0:
        failures.append('pip check')
    with open(os.path.join(report, 'pip-list.json'), 'w', encoding='utf-8') as f:
        f.write(pip(py, 'list', '--format=json', capture_output=True, text=True, check=True).stdout)
    if not failures:
        failures += t.check_installed(venv, bundle, report, root)

    if args.index == 'pypi':
        # What the documented 'pip install ies-optimiser' does, in a second environment.
        plain = os.path.join(root, 'plain')
        subprocess.run([sys.executable, '-m', 'venv', plain], check=True)
        ppy = t.python(plain)
        pip(ppy, 'install', '-q', '--upgrade', 'pip', check=True)
        unversioned = os.path.join(report, 'pip-report-unversioned.json')
        if pip(ppy, 'install', '--no-cache-dir', '--only-binary=:all:', '--report', unversioned, 'ies-optimiser').returncode:
            failures.append('pip install ies-optimiser')
        else:
            with open(unversioned, encoding='utf-8') as f:
                got = {re.sub(r'[-_.]+', '-', i['metadata']['name']).lower(): i['metadata']['version'] for i in json.load(f)['install']}
            print('pip install ies-optimiser selected ' + str(got.get('ies-optimiser')), flush=True)
            if got.get('ies-optimiser') != args.version:
                failures.append('pip install ies-optimiser selected ' + str(got.get('ies-optimiser')) + ', not ' + args.version)
            out = subprocess.run([os.path.join(t.scripts(plain), 'ies-optimiser'), '--version'], capture_output=True,
                                 text=True, env=t.isolated_env(plain), cwd=root)
            if out.stdout.strip() != 'ies-optimiser ' + args.version:
                failures.append('ies-optimiser --version printed ' + repr(out.stdout.strip()))

    shutil.rmtree(root, ignore_errors=True)
    for f in failures:
        print('FAIL: ' + f)
    print('PASS' if not failures else 'FAILED', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
