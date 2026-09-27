#!/usr/bin/env python3
"""Install an IES Optimiser wheel into a fresh environment and test it in isolation.

    python tools/test_installed_wheel.py WHEEL_OR_DIR --bundle DIR --report DIR [--constraints FILE]

Run it with the Python to be tested. It:

1. creates a new virtual environment in a temporary directory, outside any
   checkout;
2. installs the wheel with binary-only dependencies from the package index
   (pip --only-binary=:all:, so no dependency is built from source), plus
   pytest and jsonschema; --constraints pins versions (the reference
   environment's);
3. records what was installed and how ies_optimiser was found;
4. runs the installed-artifact tests (BUNDLE/tests_installed) from the
   bundle directory, with PATH reduced to the environment's own scripts (and
   System32 on Windows), no PYTHONPATH, python -P, and IES_OPTIMISER_ISOLATED=1, so the
   tests can assert that no checkout, Git or compiler is reachable;
5. inspects the installed thermodynamics executable (tools/inspect_native.py;
   with --local-build, as a host-built, non-distributable wheel).

BUNDLE is a directory holding tests_installed/, tests/fixtures/, examples/,
README.md, docs/ and tools/ -- the test bundle CI uploads; in a checkout, the checkout
itself will do, since the tests import nothing from it. Exit status 0 when
every step passes. REPORT receives pip-list.json, installation.json,
junit.xml, pytest.log and native.json.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def scripts(venv):
    return os.path.join(venv, 'Scripts' if os.name == 'nt' else 'bin')


def python(venv):
    return os.path.join(scripts(venv), 'python.exe' if os.name == 'nt' else 'python')


def wheel_path(target):
    if os.path.isdir(target):
        wheels = sorted(os.path.join(target, n) for n in os.listdir(target) if n.endswith('.whl'))
        if len(wheels) != 1:
            raise SystemExit('expected one wheel in ' + target + ', found ' + str(wheels))
        return wheels[0]
    return target


def isolated_env(venv):
    keep = ('HOME', 'USERPROFILE', 'TEMP', 'TMP', 'TMPDIR', 'SYSTEMROOT', 'SystemRoot', 'WINDIR', 'LANG', 'LC_ALL',
            'COMSPEC', 'PATHEXT', 'APPDATA', 'LOCALAPPDATA')
    env = {k: v for k, v in os.environ.items() if k in keep}
    path = [scripts(venv)]
    if os.name == 'nt':
        path.append(os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32'))
    env['PATH'] = os.pathsep.join(path)
    env['IES_OPTIMISER_ISOLATED'] = '1'
    env['PYTHONUTF8'] = '1'
    return env


def step(title, cmd, **kw):
    print('::group::' + title if os.environ.get('GITHUB_ACTIONS') else '== ' + title, flush=True)
    out = subprocess.run(cmd, **kw)
    if os.environ.get('GITHUB_ACTIONS'):
        print('::endgroup::', flush=True)
    return out


def check_installed(venv, bundle, report, root, local_build=False):
    """Steps 3-5 for an environment in which ies_optimiser is installed: record how ies_optimiser
    is found, run the installed-artifact tests in isolation, inspect the
    executable. Returns the list of failures. Also used by
    tools/verify_index_install.py."""
    failures = []
    py = python(venv)
    probe = ('import json, sys, ies_optimiser; from ies_optimiser import _install, fcn; '
             'print(json.dumps({"python": sys.version, "executable": sys.executable, "ies_optimiser": ies_optimiser.__version__, '
             '"installation": _install.installation(), "thermo": fcn.Thermo_bin, "sys_path": sys.path}))')
    found = subprocess.run([py, '-I', '-c', probe], capture_output=True, text=True, cwd=root, env=isolated_env(venv))
    if found.returncode != 0:
        print(found.stderr)
        failures.append('import in isolation')
    else:
        with open(os.path.join(report, 'installation.json'), 'w', encoding='utf-8') as f:
            f.write(found.stdout)
        info = json.loads(found.stdout)
        print(json.dumps(info['installation']), flush=True)
        if info['installation']['kind'] != 'wheel':
            failures.append('ies_optimiser is not the installed wheel: ' + info['installation']['kind'])

    pytest = [py, '-P', '-m', 'pytest', 'tests_installed', '-p', 'no:cacheprovider', '-q', '-rs',
              '--junitxml', os.path.join(report, 'junit.xml')]
    with open(os.path.join(report, 'pytest.log'), 'w', encoding='utf-8') as log:
        run = step('installed-artifact tests', pytest, cwd=bundle, env=isolated_env(venv), stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, text=True)
        log.write(run.stdout)
    print(run.stdout[-6000:], flush=True)
    if run.returncode != 0:
        failures.append('installed-artifact tests')

    # The inspection needs its parsers and native tools (otool); it runs after
    # the isolated tests, with the ordinary PATH.
    subprocess.run([py, '-m', 'pip', 'install', '-q', '--only-binary=:all:', 'pyelftools', 'pefile', 'auditwheel'],
                   check=True)
    inspect = [py, os.path.join(bundle, 'tools', 'inspect_native.py'), '--installed',
               '--report', os.path.join(report, 'native.json')] + (['--local-build'] if local_build else [])
    native = step('native executable', inspect, cwd=root)
    if native.returncode != 0:
        failures.append('native executable inspection')

    return failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('wheel')
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--constraints')
    ap.add_argument('--local-build', action='store_true',
                    help='the wheel was built on this host from the sdist (inspect_native.py --local-build)')
    args = ap.parse_args(argv)
    wheel = os.path.abspath(wheel_path(args.wheel))
    bundle = os.path.abspath(args.bundle)
    report = os.path.abspath(args.report)
    os.makedirs(report, exist_ok=True)
    root = tempfile.mkdtemp(prefix='ies-optimiser-installed-')
    venv = os.path.join(root, 'venv')
    failures = []

    subprocess.run([sys.executable, '-m', 'venv', venv], check=True)
    py = python(venv)
    subprocess.run([py, '-m', 'pip', 'install', '-q', '--upgrade', 'pip'], check=True)
    install = [py, '-m', 'pip', 'install', '--only-binary=:all:', wheel, 'pytest', 'jsonschema']
    if args.constraints:
        install += ['--constraint', os.path.abspath(args.constraints)]
    if step('install ' + os.path.basename(wheel), install).returncode != 0:
        print('FAIL: installation', flush=True)
        return 1
    listing = subprocess.run([py, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True, check=True)
    with open(os.path.join(report, 'pip-list.json'), 'w', encoding='utf-8') as f:
        f.write(listing.stdout)

    failures += check_installed(venv, bundle, report, root, args.local_build)

    shutil.rmtree(root, ignore_errors=True)
    for f in failures:
        print('FAIL: ' + f)
    print('PASS' if not failures else 'FAILED', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
