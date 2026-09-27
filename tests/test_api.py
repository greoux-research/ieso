"""The Python API's contracts: import safety, no mutation, isolation, explicit
failures, serialisable results, and equivalence with the command line."""

import copy
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from ies_optimiser import api, cli
from ies_optimiser import fcn as u
from ies_optimiser.errors import InputError, ThermoError
from conftest import demand_x, flex, generator, p2x, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPARE = os.path.join(ROOT, 'tools', 'compare_outputs.py')


def small(hours, profile_array=False):
    """A case exercising every entity type; optionally a NumPy profile."""
    shape = np.linspace(1.0, 2.0, hours) if profile_array else ''
    return system(
        generators=[generator('gas', fix=1.0, var=30.0, emis=400.0),
                    generator('solr', fix=0.5, var=0.0, profile=shape, cf=0.3)],
        flexes=[flex('bstr', fix=0.2, rte=0.81, hours=2)],
        p2xs=[p2x('ro', elec_use=0.5, fix_prod=1.0, fix_strg=0.1)],
        e_total=10.0 * hours, xs=[demand_x('water', 2.0 * hours, ['ro'])])


def same(a, b):
    """Deep equality that also requires identical types (arrays stay arrays)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray):
        return a.dtype == b.dtype and np.array_equal(a, b)
    return a == b


def plain_json(node, path='$'):
    """Assert a document holds only plain JSON types -- no solver objects."""
    if isinstance(node, dict):
        for k, v in node.items():
            assert isinstance(k, str), path
            plain_json(v, path + '.' + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            plain_json(v, f'{path}[{i}]')
    else:
        assert node is None or type(node) in (str, int, float, bool), (path, type(node))


# --- import safety ------------------------------------------------------------------

def test_import_is_safe_even_with_unrelated_command_line_arguments(tmp_path):
    """Importing the package, its API and its command line reads no input,
    launches no process, creates no solver, writes no file, prints nothing and
    does not exit -- whatever sys.argv holds."""
    probe = f"""
import builtins, subprocess, sys
sys.argv = ['host.py', '--unrelated', 'case.json', 'carbon-constraint=1']
def refuse(what):
    def f(*a, **k):
        raise AssertionError('import performed ' + what)
    return f
subprocess.Popen.__init__ = refuse('a subprocess launch')
real_open = builtins.open
def guarded_open(file, mode='r', *a, **k):
    if any(c in mode for c in 'wax+'):
        raise AssertionError('import opened a file for writing: ' + str(file))
    return real_open(file, mode, *a, **k)
builtins.open = guarded_open
from ortools.linear_solver import pywraplp
pywraplp.Solver.CreateSolver = staticmethod(refuse('a solver creation'))
import ies_optimiser, ies_optimiser.api, ies_optimiser.cli, ies_optimiser.__main__
sys.stdout.write('IMPORTED')
"""
    out = subprocess.run([sys.executable, '-B', '-c', probe], cwd=str(tmp_path),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout == 'IMPORTED'
    assert out.stderr == ''
    assert list(tmp_path.iterdir()) == []


# --- no mutation of the caller's data ------------------------------------------------

@pytest.mark.parametrize('profile_array', [False, True])
def test_a_successful_solve_leaves_its_input_unchanged(profile_array):
    case = small(6, profile_array)
    del case['flex'][0]['soc_min']                     # an optional field the model would default
    before = copy.deepcopy(case)
    result = api.solve(case, config=u.RunConfig(hours=6))
    assert result.optimal
    assert same(case, before)                          # nested lists, dicts and arrays untouched
    assert 'soc_min' not in case['flex'][0]            # the default was applied to a private copy
    assert result.document['flex'][0]['soc_min'] == 0.0


def test_an_infeasible_solve_leaves_its_input_unchanged():
    case = system(generators=[generator('gas', var=10.0, l_prod=(0, 0))], e_total=24.0,
                  e_kwargs={'l_ns': (0, 0)})
    before = copy.deepcopy(case)
    result = api.solve(case, config=u.RunConfig(hours=24))
    assert result.optimal is False and result.status == 'infeasible'
    assert same(case, before)


def test_a_refused_input_is_left_unchanged():
    case = small(6)
    case['demand']['e']['l_ns'] = [11.0, 20.0]         # hourly demand is 10 MWh: a lower bound of 11 is refused
    before = copy.deepcopy(case)
    with pytest.raises(InputError):
        api.solve(case, config=u.RunConfig(hours=6))
    assert same(case, before)


# --- isolation between runs ------------------------------------------------------------

def comparable(doc):
    d = copy.deepcopy(doc)
    d['solver'].pop('stat_time')
    d['provenance'].pop('run_utc')
    return d


def test_repeated_solves_are_independent():
    """Configuration, options and solver state do not carry from one solve to
    the next: B solved after A equals B solved first."""
    b_first = api.solve(small(4), config=u.RunConfig(hours=4)).document
    a = api.solve(small(24), options={'carbon-constraint': 100.0}, config=u.RunConfig(hours=24))
    b_after = api.solve(small(4), config=u.RunConfig(hours=4)).document
    assert len(a.document['generator'][0]['e_prod']) == 24
    assert 'carbon_cap_detail' in a.document['demand']['e']['shadow_prices']
    assert len(b_after['generator'][0]['e_prod']) == 4
    assert 'carbon_cap_detail' not in b_after['demand']['e']['shadow_prices']
    assert comparable(b_after) == comparable(b_first)
    assert u.RunConfig().hours == 8760                  # defaults untouched


# --- explicit, catchable failures -------------------------------------------------------

def test_input_errors_carry_context_and_do_not_end_the_caller():
    case = small(6)
    case['demand']['e']['l_ns'] = [3.0, 10.0]           # valid wherever there is demand...
    case['demand']['e']['profile'] = [1.0, 0.0, 1.0, 1.0, 1.0, 1.0]   # ...but hour 1 has none
    with pytest.raises(InputError) as info:
        api.solve(case, config=u.RunConfig(hours=6))
    e = info.value
    assert (e.entity, e.field, e.hour) == ('demand.e', 'l_ns', 1)
    # the caller carries on: a valid solve still works
    assert api.solve(small(6), config=u.RunConfig(hours=6)).optimal


def test_option_errors_name_the_option():
    with pytest.raises(InputError) as info:
        api.solve(small(4), options={'carbon-contraint': 0.0}, config=u.RunConfig(hours=4))
    assert info.value.field == 'carbon-contraint' and 'unknown option' in str(info.value)
    with pytest.raises(InputError):
        api.solve(small(4), options={'non-served-power-constraint': 1.5}, config=u.RunConfig(hours=4))
    with pytest.raises(InputError):
        api.solve(small(4), options={'carbon-constraint': float('nan')}, config=u.RunConfig(hours=4))


def test_thermodynamics_failures_are_their_own_exception(tmp_path):
    bad = tmp_path / 'sim.bin'
    bad.write_text('#!/bin/sh\necho "error" >&2\nexit 3\n')
    bad.chmod(0o755)
    case = system(generators=[generator('chp', var=10.0, kind='elec + ther', turbine=(564, 152), cond=0.05)],
                  p2xs=[p2x('med', elec_use=0.001, ther_use=0.05, kind='elec + ther',
                            sources=('chp',), temperature=80)],
                  e_total=40.0, xs=[demand_x('water', 20.0, ['med'])])
    with pytest.raises(ThermoError) as info:
        api.solve(case, config=u.RunConfig(hours=4, thermo_bin=str(bad)))
    assert (info.value.generator, info.value.process) == ('chp', 'med')
    assert 'status 3' in info.value.reason
    assert not isinstance(info.value, InputError)


def test_a_missing_input_file_is_an_input_error(tmp_path):
    with pytest.raises(InputError) as info:
        api.load_input(tmp_path / 'absent.json')
    assert info.value.entity.endswith('absent.json')


# --- results ------------------------------------------------------------------------

def test_results_are_plain_serialisable_json():
    case = small(6, profile_array=True)
    result = api.solve(case, options={'carbon-constraint': 300.0, 'non-served-power-constraint': 0.1},
                       config=u.RunConfig(hours=6))
    assert result.optimal and result.accounting_ok is True
    plain_json(result.document)
    json.dumps(result.document, allow_nan=False)
    assert result.document['provenance']['input'] == '<in-memory>'
    assert len(result.document['provenance']['input_sha256']) == 64


def test_an_unsuccessful_result_is_marked_and_serialisable():
    case = system(generators=[generator('gas', var=10.0, l_prod=(0, 0))], e_total=24.0,
                  e_kwargs={'l_ns': (0, 0)})
    result = api.solve(case, config=u.RunConfig(hours=24))
    assert (result.optimal, result.accounting_ok, result.objective) == (False, None, None)
    d = result.document
    plain_json(d)
    assert d['solver']['stat_succ'] == 0 and d['solver']['stat_status'] == 'infeasible'
    assert 'system' not in d                           # no accounts presented for a failed solve
    assert d['provenance']['source_sha256']            # but it is still traceable


# --- the command line -----------------------------------------------------------------

def full_year_case(tmp_path, name='case.json'):
    s = system(generators=[generator('gas', fix=1.0, var=30.0, emis=400.0),
                           generator('dac', fix=1.0, var=80.0, emis=-100.0)],
               flexes=[flex('bstr', fix=0.2, rte=0.81, hours=2)],
               e_total=8760.0 * 10)
    path = tmp_path / name
    path.write_text(json.dumps(s))
    return path


def test_cli_and_api_give_the_same_mathematical_result(tmp_path):
    path = full_year_case(tmp_path)
    opts = ['carbon-constraint=20', 'non-served-power-constraint=0.05']
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'ies_optimiser.py'), str(path)] + opts, cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
    assert out.returncode == 0, out.stdout
    cli_file = tmp_path / 'case.ies-optimiser.carbon-constraint_20.0.non-served-power-constraint_0.05.json'
    result = api.solve(api.load_input(path), options={'carbon-constraint': 20.0,
                                                      'non-served-power-constraint': 0.05}, source=path)
    api_file = tmp_path / 'api.json'
    api.write_result(result, api_file)
    cmp = subprocess.run([sys.executable, COMPARE, str(api_file), str(cli_file)],
                         stdout=subprocess.PIPE, text=True)
    assert cmp.returncode == 0, cmp.stdout
    # the same input, recorded the same way
    cli_doc = json.loads(cli_file.read_text())
    assert result.document['provenance']['input_sha256'] == cli_doc['provenance']['input_sha256']


def test_cli_exit_codes_in_process(tmp_path, monkeypatch):
    """0 success, 1 refused input or options (nothing written), 3 accounting
    failure (result written). main() returns the status; it does not exit."""
    path = full_year_case(tmp_path)
    assert cli.main([]) == 1
    assert cli.main([str(path), 'carbon-contraint=1']) == 1
    assert not list(tmp_path.glob('*.ies-optimiser*.json'))
    assert cli.main([str(path)]) == 0
    assert (tmp_path / 'case.ies-optimiser.json').is_file()
    monkeypatch.setattr(u, 'Recon_rtol', -1.0)          # make every reconciliation fail
    monkeypatch.setattr(u, 'Recon_atol', -1.0)
    (tmp_path / 'case.ies-optimiser.json').unlink()
    assert cli.main([str(path)]) == 3
    assert json.loads((tmp_path / 'case.ies-optimiser.json').read_text())['system']['accounting_ok'] is False


def test_cli_launcher_without_arguments_exits_one():
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'ies_optimiser.py')], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    assert out.returncode == 1
    assert "'ies-optimiser input.json'" in out.stdout


# --- per-run settings are checked, not trusted -----------------------------------------

@pytest.mark.parametrize('field, value', [
    ('hours', 0), ('hours', -24), ('hours', True), ('hours', 24.0), ('hours', '24'),
    ('storage_closes_the_year', 'false'), ('storage_closes_the_year', 0), ('storage_closes_the_year', None),
    ('thermo_timeout', 0), ('thermo_timeout', -1.0), ('thermo_timeout', float('nan')), ('thermo_timeout', float('inf')),
    ('thermo_timeout', True), ('thermo_timeout', '30'),
    ('thermo_bin', None), ('thermo_bin', 3), ('thermo_bin', b'/bin/x'), ('thermo_bin', ''),
    ('profile_base', 7), ('profile_base', b'/tmp'), ('profile_base', ''),
])
def test_malformed_run_settings_are_refused_with_diagnostics(field, value):
    """A string 'false' used to switch storage closure ON (it is truthy), and
    hours=0 raised ZeroDivisionError inside validate()."""
    with pytest.raises(InputError) as info:
        u.RunConfig(**{field: value})
    d = info.value.diagnostics[0]
    assert (d.code, d.layer, d.field, d.entity) == ('config.invalid', 'configuration', field, 'RunConfig')


def test_path_like_settings_are_normalised(tmp_path):
    import pathlib
    cfg = u.RunConfig(hours=4, profile_base=pathlib.Path(tmp_path), thermo_bin=pathlib.Path(u.Thermo_bin))
    assert cfg.profile_base == str(tmp_path) and cfg.thermo_bin == u.Thermo_bin
    assert cfg.storage_closes_the_year is True and u.RunConfig().thermo_bin == u.Thermo_bin
    assert api.validate(small(4), config=cfg).valid


# --- provenance identifies the case actually solved -------------------------------------

def test_provenance_identifies_the_case_solved_not_only_its_source(tmp_path):
    """A case edited in memory and solved with source= naming the original file
    used to carry only the file's hash."""
    case = small(4)
    path = tmp_path / 'case.json'
    path.write_text(json.dumps(case))
    edited = copy.deepcopy(case)
    edited['demand']['e']['total'] *= 2
    config = u.RunConfig(hours=4)
    as_file = api.solve(case, source=path, config=config).document['provenance']
    as_edited = api.solve(edited, source=path, config=config).document['provenance']
    from_path = api.solve(str(path), config=config).document['provenance']
    in_memory = api.solve(edited, config=config).document['provenance']
    assert as_file['source_matches_case'] is True and from_path['source_matches_case'] is True
    assert as_edited['source_matches_case'] is False
    assert as_edited['input_sha256'] == as_file['input_sha256'] == u.file_digest(str(path))   # the file named
    assert as_edited['case_sha256'] != as_file['case_sha256'] == from_path['case_sha256']     # the case solved
    assert in_memory['source_matches_case'] is None and in_memory['case_sha256'] == as_edited['case_sha256']
    canonical = api.solve(api.to_canonical(case), config=config).document['provenance']
    assert canonical['case_sha256'] == as_file['case_sha256']            # a legacy case and its canonical form
