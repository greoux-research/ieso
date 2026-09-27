"""The package as installed (Step 5): entry points, resources, version, and
the compatibility launcher.

These run against whatever ies_optimiser is installed in the test interpreter -- an
editable install of this checkout in development, or a wheel.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

import ies_optimiser
from ies_optimiser import _install, fcn, schemas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(args, cwd):
    return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          timeout=120)


def console():
    found = shutil.which('ies-optimiser', path=os.path.dirname(sys.executable))
    if found is None:
        pytest.skip('no ies-optimiser console script beside ' + sys.executable)
    return found


def test_the_public_api_is_explicit():
    for name in ies_optimiser.__all__:
        assert hasattr(ies_optimiser, name), name
    assert ies_optimiser.solve is ies_optimiser.api.solve and ies_optimiser.RunConfig is fcn.RunConfig
    assert ies_optimiser.InputError is ies_optimiser.errors.InputError


def test_one_version_from_the_distribution_metadata():
    from importlib import metadata
    assert ies_optimiser.__version__ == metadata.version('ies-optimiser') == _install.version()
    try:
        import tomllib
    except ImportError:                               # Python < 3.11
        return
    pyproject = os.path.join(ROOT, 'pyproject.toml')
    if _install.checkout_root() == ROOT and os.path.isfile(pyproject):
        with open(pyproject, 'rb') as f:
            assert tomllib.load(f)['project']['version'] == ies_optimiser.__version__


def test_resources_are_inside_the_package():
    package = os.path.dirname(os.path.abspath(ies_optimiser.__file__))
    assert os.path.isfile(os.path.join(package, 'py.typed'))
    for kind in ('input', 'result'):
        assert os.path.dirname(schemas.path(kind)) == os.path.join(package, 'data')
        with open(schemas.path(kind), encoding='utf-8') as f:
            assert json.load(f)['x-ies-optimiser-format']['kind'] == kind
    assert os.path.isfile(fcn.Thermo_bin) and os.access(fcn.Thermo_bin, os.X_OK)


@pytest.mark.parametrize('how', ['module', 'console'])
def test_help_and_version(tmp_path, how):
    cmd = [sys.executable, '-m', 'ies_optimiser'] if how == 'module' else [console()]
    out = run(cmd + ['--help'], tmp_path)
    assert out.returncode == 0 and 'ies-optimiser validate INPUT.json' in out.stdout and 'Exit status' in out.stdout
    out = run(cmd + ['--version'], tmp_path)
    assert out.returncode == 0 and out.stdout.strip() == 'ies-optimiser ' + ies_optimiser.__version__
    out = run(cmd + ['validate', '--help'], tmp_path)
    assert out.returncode == 0 and 'schema input|result' in out.stdout
    out = run(cmd, tmp_path)
    assert out.returncode == 1
    assert list(tmp_path.iterdir()) == []


def test_console_and_module_give_the_same_schema(tmp_path):
    a = run([console(), 'schema', 'result'], tmp_path)
    b = run([sys.executable, '-m', 'ies_optimiser', 'schema', 'result'], tmp_path)
    assert a.returncode == b.returncode == 0 and a.stdout == b.stdout


# --- the compatibility launcher (python ies_optimiser.py ...) ------------------------------------

LAUNCHER = os.path.join(ROOT, 'ies_optimiser.py')
needs_checkout = pytest.mark.skipif(not os.path.isfile(LAUNCHER), reason='not a source checkout')


@needs_checkout
def test_the_launcher_runs_the_installed_package_from_anywhere(tmp_path):
    out = run([sys.executable, LAUNCHER, '--version'], tmp_path)
    assert out.returncode == 0 and out.stdout.strip() == 'ies-optimiser ' + ies_optimiser.__version__
    out = run([sys.executable, LAUNCHER, '--version'], ROOT)                 # from the checkout itself
    assert out.returncode == 0 and out.stdout.strip() == 'ies-optimiser ' + ies_optimiser.__version__


@needs_checkout
def test_the_launcher_refuses_to_pose_as_the_package():
    spec = importlib.util.spec_from_file_location('ies_optimiser', LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    with pytest.raises(ImportError, match='launcher, not the ies_optimiser package'):
        spec.loader.exec_module(module)


@needs_checkout
def test_the_launcher_does_not_import_itself(tmp_path):
    """Run as a script, its directory (the checkout root, holding ies_optimiser.py) is
    sys.path[0]; the package imported must still be the package."""
    code = [sys.executable, LAUNCHER, 'schema', 'input']
    out = run(code, ROOT)
    assert out.returncode == 0, out.stderr
    with open(schemas.path('input'), encoding='utf-8') as f:
        assert out.stdout == f.read()
