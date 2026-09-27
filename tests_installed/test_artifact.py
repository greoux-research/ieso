"""The installed artifact: what it is, what it contains, how it behaves.

Run against the ies_optimiser package installed in this Python. With IES_OPTIMISER_ISOLATED=1
the environment itself is checked too: an installed wheel, no checkout, no
Git, no compiler.
"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from importlib import metadata

import pytest

import ies_optimiser
from ies_optimiser import _install, fcn, schemas

from conftest import ISOLATED, console

PACKAGE = os.path.dirname(os.path.abspath(ies_optimiser.__file__))


def run(args, cwd, **kw):
    return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          timeout=kw.pop('timeout', 600), **kw)


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def snapshot(folder):
    return sorted((os.path.relpath(os.path.join(d, n), folder), os.stat(os.path.join(d, n)).st_mtime_ns)
                  for d, _, names in os.walk(folder) for n in names if '__pycache__' not in d)


# --- what is installed ---------------------------------------------------------------------

@pytest.mark.skipif(not ISOLATED, reason='IES_OPTIMISER_ISOLATED is not set')
def test_the_installed_wheel_is_what_runs():
    install = _install.installation()
    assert install['kind'] == 'wheel' and install['checkout'] is None, install
    direct = metadata.distribution('ies-optimiser').read_text('direct_url.json')
    assert direct is None or not json.loads(direct).get('dir_info', {}).get('editable'), direct
    assert 'site-packages' in PACKAGE.replace('\\', '/').lower()
    assert 'PYTHONPATH' not in os.environ
    assert not any(os.path.isfile(os.path.join(p or os.curdir, 'ies_optimiser', '__init__.py')) and
                   os.path.abspath(os.path.join(p or os.curdir, 'ies_optimiser')) != PACKAGE for p in sys.path), sys.path


@pytest.mark.skipif(not ISOLATED, reason='IES_OPTIMISER_ISOLATED is not set')
def test_no_git_compiler_or_build_tool_is_reachable():
    tools = ['git', 'gcc', 'g++', 'cc', 'c++', 'clang', 'clang++', 'cl', 'cmake', 'ninja', 'make']
    assert [t for t in tools if shutil.which(t)] == []


def test_version_and_metadata_agree():
    assert ies_optimiser.__version__ == metadata.version('ies-optimiser')
    requires = metadata.requires('ies-optimiser') or []
    assert {r.split('>')[0].split('<')[0].split('=')[0].split(';')[0].strip() for r in requires
            if 'extra ==' not in r} == {'numpy', 'ortools', 'pydantic'}


def test_resources_are_installed():
    assert os.path.isfile(os.path.join(PACKAGE, 'py.typed'))
    for kind in ('input', 'result'):
        path = schemas.path(kind)
        assert os.path.dirname(path) == os.path.join(PACKAGE, 'data')
        with open(path, encoding='utf-8') as f:
            assert f.read() == schemas.generate(kind)          # shipped == generated from installed models
    exe = fcn.Thermo_bin
    assert os.path.dirname(exe) == os.path.join(PACKAGE, '_bin')
    assert os.path.basename(exe) == ('ies-optimiser-thermo.exe' if sys.platform == 'win32' else 'ies-optimiser-thermo')
    assert os.path.isfile(exe) and os.access(exe, os.X_OK)


def test_import_has_no_side_effects(tmp_path):
    probe = """
import builtins, subprocess, sys
sys.argv = ['host.py', '--unrelated', 'case.json']
def refuse(what):
    def f(*a, **k):
        raise AssertionError('import performed ' + what)
    return f
subprocess.Popen.__init__ = refuse('a subprocess launch')
real_open = builtins.open
def guarded(file, mode='r', *a, **k):
    if any(c in mode for c in 'wax+'):
        raise AssertionError('import opened a file for writing: ' + str(file))
    return real_open(file, mode, *a, **k)
builtins.open = guarded
from ortools.linear_solver import pywraplp
pywraplp.Solver.CreateSolver = staticmethod(refuse('a solver creation'))
import ies_optimiser, ies_optimiser.api, ies_optimiser.cli, ies_optimiser.models, ies_optimiser.results, ies_optimiser.schemas, ies_optimiser.__main__
sys.stdout.write('IMPORTED')
"""
    out = run([sys.executable, '-B', '-c', probe], tmp_path)
    assert out.returncode == 0, out.stderr
    assert out.stdout == 'IMPORTED' and out.stderr == ''
    assert list(tmp_path.iterdir()) == []


# --- entry points ----------------------------------------------------------------------------

@pytest.mark.parametrize('how', ['console', 'module'])
def test_entry_points(tmp_path, how):
    cmd = [console()] if how == 'console' else [sys.executable, '-m', 'ies_optimiser']
    out = run(cmd + ['--help'], tmp_path)
    assert out.returncode == 0 and 'ies-optimiser validate INPUT.json' in out.stdout
    out = run(cmd + ['--version'], tmp_path)
    assert out.returncode == 0 and out.stdout.strip() == 'ies-optimiser ' + ies_optimiser.__version__
    out = run(cmd + ['schema', 'input'], tmp_path)
    assert out.returncode == 0 and json.loads(out.stdout)['x-ies-optimiser-format'] == {'kind': 'input', 'version': 1}
    assert run(cmd, tmp_path).returncode == 1
    assert list(tmp_path.iterdir()) == []


# --- validation ------------------------------------------------------------------------------

def test_validation_is_structured_and_json_is_clean(tmp_path, examples_copy):
    with open(examples_copy / 'electricity-storage' / 'case.json', encoding='utf-8') as f:
        case = json.load(f)
    case['generator'][0]['capacity_factor'] = 2
    case['flex'][0]['colour'] = 'blue'
    bad = tmp_path / 'bad case.json'
    bad.write_text(json.dumps(case), encoding='utf-8')
    out = run([console(), 'validate', str(bad), '--json'], tmp_path)
    assert out.returncode == 1
    doc = json.loads(out.stdout)                                # stdout is exactly one JSON document
    assert doc['valid'] is False and doc['stages']['structure'] == 'failed'
    got = {(d['code'], d['path'], d['layer']) for d in doc['diagnostics']}
    assert got == {('value.out_of_range', '/generator/0/capacity_factor', 'structure'),
                   ('field.unknown', '/flex/0/colour', 'structure')}
    out = run([console(), 'validate', str(examples_copy / 'power-to-x-thermal' / 'case.json'), '--json'], tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    doc = json.loads(out.stdout)
    assert doc['valid'] and doc['stages']['thermodynamics'] == 'passed'


def test_examples_satisfy_the_input_schema(examples_copy):
    jsonschema = pytest.importorskip('jsonschema')
    with open(schemas.path('input'), encoding='utf-8') as f:
        validator = jsonschema.Draft202012Validator(json.load(f))
    for name in ('electricity-storage', 'power-to-x-thermal'):
        with open(examples_copy / name / 'case.json', encoding='utf-8') as f:
            validator.validate(json.load(f))


# --- profiles, legacy mode, outputs ------------------------------------------------------------

def test_cli_solve_from_an_unrelated_directory_with_spaces(tmp_path, examples_copy):
    """Profiles resolve against the input's own directory; a decoy in the
    working directory is never read; the only file written is the result,
    beside the input; the installed package is left untouched."""
    case_dir = examples_copy / 'electricity-storage'
    elsewhere = tmp_path / 'unrelated working dir'
    elsewhere.mkdir()
    (elsewhere / 'solar.csv').write_text('not a profile\n')
    (elsewhere / 'demand.csv').write_text('not a profile\n')
    before_case, before_package = snapshot(str(case_dir)), snapshot(PACKAGE)
    out = run([console(), str(case_dir / 'case.json')], elsewhere)
    assert out.returncode == 0, out.stderr
    written = sorted(set(os.listdir(case_dir)) - {p for p, _ in before_case})
    assert written == ['case.ies-optimiser.json']
    assert sorted(os.listdir(elsewhere)) == ['demand.csv', 'solar.csv']
    assert snapshot(PACKAGE) == before_package
    with open(case_dir / 'case.ies-optimiser.json', encoding='utf-8') as f:
        doc = json.load(f)
    os.remove(case_dir / 'case.ies-optimiser.json')
    pv = doc['provenance']
    assert doc['solver']['stat_status'] == 'optimal' and doc['system']['accounting_ok'] is True
    assert pv['profile_resolution'] == {'mode': 'input-directory', 'base': str(case_dir)}
    for declared in ('solar.csv', 'demand.csv'):
        entry = pv['profile_files'][declared]
        assert entry['resolved'] == str(case_dir / declared)
        assert entry['sha256'] == sha256(case_dir / declared)


def test_legacy_mode_is_explicit(tmp_path, examples_copy):
    """An unversioned input with paths relative to another directory needs
    --profile-base; without it the profile is refused, naming where it looked."""
    with open(examples_copy / 'electricity-storage' / 'case.json', encoding='utf-8') as f:
        case = json.load(f)
    del case['format_version']
    case['demand']['e']['profile'] = 'electricity-storage/demand.csv'
    case['generator'][0]['profile'] = 'electricity-storage/solar.csv'
    case['solver'] = {'stat_succ': -1}                          # a legacy placeholder
    legacy = tmp_path / 'legacy.json'
    legacy.write_text(json.dumps(case), encoding='utf-8')
    out = run([console(), 'validate', str(legacy), '--json'], tmp_path)
    assert out.returncode == 1
    d = json.loads(out.stdout)['diagnostics'][0]
    assert d['code'] == 'profile.not_found' and str(tmp_path) in d['message']
    out = run([console(), 'validate', str(legacy), '--profile-base', str(examples_copy), '--json'], tmp_path)
    assert out.returncode == 0, out.stdout
    doc = json.loads(out.stdout)
    assert doc['format'] == 'legacy' and doc['profile_resolution'] == {'mode': 'explicit', 'base': str(examples_copy)}
    assert '/solver' in doc['removed_fields']


# --- the API ------------------------------------------------------------------------------------

def test_api_solves_are_immutable_and_independent(solved, examples_copy, expected):
    """Solving the same input object twice gives the same answer and leaves the object as it was."""
    sc = expected['scenarios'][0]
    path = str(examples_copy / sc['case'])
    with open(path, encoding='utf-8') as f:
        case = json.load(f)
    before = copy.deepcopy(case)
    again = ies_optimiser.solve(case, options=sc['options'], source=path)
    assert case == before
    first = solved[sc['name']]
    assert again.objective == first.objective
    a, b = copy.deepcopy(first.document), copy.deepcopy(again.document)
    for d in (a, b):
        d['solver'].pop('stat_time')
        d['provenance'].pop('run_utc')
    assert a == b


def test_provenance_identifies_the_installed_code_and_executable(solved):
    doc = solved['power-to-x-thermal'].document
    pv = doc['provenance']
    assert pv['ies_optimiser_version'] == ies_optimiser.__version__
    assert pv['installation']['package_dir'] == PACKAGE
    if ISOLATED:
        assert pv['installation']['kind'] == 'wheel'
        assert (pv['git_scope'], pv['git_revision'], pv['enclosing_git']) == (None, None, None)
    assert pv['thermo_binary'] == fcn.Thermo_bin and pv['thermo_binary_origin'] == 'packaged'
    assert pv['source_files_sha256']['thermo/sim.bin'] == sha256(fcn.Thermo_bin)
    assert pv['source_files_sha256']['ies_optimiser/fcn.py'] == sha256(os.path.join(PACKAGE, 'fcn.py'))
    assert pv['result_format_version'] == 1 and pv['input_format'] == 'canonical'
    assert pv['source_matches_case'] is True and len(pv['case_sha256']) == 64
    gen = next(g for g in doc['generator'] if g['iden'] == 'nuclear')
    assert gen['type'] == 'elec + ther' and 0 < gen['a'] < 1 and gen['b'] > 0


def test_results_satisfy_the_result_schema(solved):
    jsonschema = pytest.importorskip('jsonschema')
    with open(schemas.path('result'), encoding='utf-8') as f:
        validator = jsonschema.Draft202012Validator(json.load(f))
    for result in solved.values():
        validator.validate(result.document)
