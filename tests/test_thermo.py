"""The thermodynamics executable, how IES Optimiser finds it, and what provenance says.

These run the compiled C++ (built fresh by the sim_bin fixture), not mocked
coefficients. The supported extraction domain is the open interval between
the saturation temperature at the condenser pressure and the saturation
temperature at the turbine inlet pressure: outside it the extraction pressure
does not lie between the two, and the expansion helper would compute a
compression and return plausible-looking coefficients for an impossible plant.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys

import pytest

from ies_optimiser import fcn as u
from ies_optimiser.errors import ThermoError
from conftest import demand_x, generator, p2x, solve, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NUCLEAR = (290, 70, 0.05)
FOSSIL = (564, 152, 0.05)


def sim(binary, *args, timeout=30):
    out = subprocess.run([binary] + [str(a) for a in args], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, timeout=timeout)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def limits(binary, turbine_t, turbine_p, condenser_p):
    code, out, err = sim(binary, '--limits', turbine_t, turbine_p, condenser_p)
    assert code == 0, err
    low, high = (float(v) for v in out.split())
    return low, high


# --- the executable itself ----------------------------------------------------

@pytest.mark.parametrize('plant, expected', [
    (NUCLEAR, (0.124272, 1.97657)),        # reproduces the archived MED coefficients
    (FOSSIL, (0.123277, 1.57164)),
])
def test_representative_plants(sim_bin, plant, expected):
    code, out, _ = sim(sim_bin, *plant, 80)
    assert code == 0
    a, b = (float(v) for v in out.split())
    assert (a, b) == pytest.approx(expected, rel=1e-5)


def test_limits_are_the_saturation_temperatures(sim_bin):
    low, high = limits(sim_bin, *NUCLEAR)
    # steam tables: Tsat(0.05 bar) = 32.88 C, Tsat(70 bar) = 285.83 C
    assert low == pytest.approx(32.88, abs=0.05)
    assert high == pytest.approx(285.83, abs=0.05)


def test_extraction_above_the_inlet_saturation_is_refused(sim_bin):
    """Astra's counterexample: 300 C extraction on a 70 bar turbine needs an
    extraction pressure above the inlet pressure. It returned 0.620405 1.69702."""
    code, out, err = sim(sim_bin, *NUCLEAR, 300)
    assert code != 0
    assert out == ''
    assert 'extraction temperature' in err


@pytest.mark.parametrize('where', ['low', 'high'])
def test_boundaries_are_excluded(sim_bin, where):
    """At the lower limit extraction is at condenser pressure and the heat is
    free (a = 0); at the upper limit it is at the inlet. Both are refused."""
    low, high = limits(sim_bin, *NUCLEAR)
    at = low if where == 'low' else high
    code, _, err = sim(sim_bin, *NUCLEAR, repr(at))
    assert code != 0 and 'extraction temperature' in err


@pytest.mark.parametrize('where', ['low', 'high'])
def test_just_inside_the_boundaries_is_accepted(sim_bin, where):
    low, high = limits(sim_bin, *NUCLEAR)
    t = low + 1.0 if where == 'low' else high - 1.0
    code, out, _ = sim(sim_bin, *NUCLEAR, t)
    assert code == 0
    a, b = (float(v) for v in out.split())
    assert 0 < a < 1 and b > 0 and a * b < 1


@pytest.mark.parametrize('args, reason', [
    ((290, 70, 0.05, 20), 'extraction temperature'),        # below condenser saturation
    ((280, 70, 0.05, 80), 'superheated'),                   # inlet below saturation at 70 bar
    ((290, 70, 80, 150), 'condenser pressure'),             # condenser above inlet
    ((290, 70, 0, 80), 'condenser pressure'),
    ((290, 70, 0.05, 'nan'), 'finite'),
    ((290, 'inf', 0.05, 80), 'finite'),
    ((290, 70, 0.05, 'abc'), 'number'),
    ((290, 70, 0.05), 'usage'),
])
def test_invalid_inputs_are_refused(sim_bin, args, reason):
    code, out, err = sim(sim_bin, *args)
    assert code != 0
    assert out == ''
    assert reason in err.lower()


# --- the Python boundary --------------------------------------------------------

def fake(tmp_path, body, name='sim.bin'):
    p = tmp_path / name
    p.write_text('#!/bin/sh\n' + body + '\n')
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def test_python_uses_the_compiled_binary(sim_bin):
    a, b, err = u.thermo(*NUCLEAR, 80, binary=sim_bin)
    assert err is False
    assert (a, b) == pytest.approx((0.124272, 1.97657), rel=1e-5)


@pytest.mark.parametrize('body, reason', [
    ('echo "0.2 1.5"; exit 3', 'status 3'),
    ('echo "abc def"', 'malformed'),
    ('echo "0.2 1.5 7"', 'malformed'),
    ('echo "nan 1.5"', 'finite'),
    ('echo "1.5 1.5"', 'admissible'),
    ('echo "0.2 -1"', 'admissible'),
    ('echo "0.9 1.5"', 'admissible'),          # a*b >= 1: heat would exceed the fuel
    ('sleep 5; echo "0.2 1.5"', 'timed out'),
])
def test_failures_at_the_python_boundary(tmp_path, body, reason):
    a, b, err = u.thermo(*NUCLEAR, 80, binary=fake(tmp_path, body), timeout=1)
    assert err and reason in err


def test_a_missing_binary_is_reported(tmp_path):
    _, _, err = u.thermo(*NUCLEAR, 80, binary=str(tmp_path / 'absent.bin'))
    assert err and 'not found' in err and 'reinstall' in err


def test_a_failed_calculation_stops_the_run_and_names_the_units(horizon, sim_bin):
    """Previously a coupled unit whose coefficients failed was not silently
    downgraded -- but an invalid temperature slipped through as positive
    coefficients. Now the run is refused with a ThermoError naming the
    generator, the process and the reason; the caller keeps running."""
    hours = horizon(4)
    s = system(generators=[generator('nucl', var=10.0, kind='elec + ther',
                                     turbine=(290, 70), cond=0.05)],
               p2xs=[p2x('med', elec_use=0.001, ther_use=0.05, kind='elec + ther',
                         sources=('nucl',), temperature=300)],
               e_total=10.0 * hours, xs=[demand_x('water', 5.0 * hours, ['med'])])
    with pytest.raises(ThermoError) as info:
        solve(s, config=u.RunConfig(hours=hours, thermo_bin=sim_bin))
    e = info.value
    assert (e.generator, e.process) == ('nucl', 'med')
    assert 'extraction temperature' in e.reason and 'extraction temperature' in str(e)


def test_thermal_case_solves_with_the_real_binary(horizon, sim_bin):
    hours = horizon(24)
    s = system(generators=[generator('nucl', fix=1.0, var=10.0, kind='elec + ther',
                                     turbine=(290, 70), cond=0.05)],
               p2xs=[p2x('med', elec_use=0.0015, ther_use=0.05, kind='elec + ther',
                         sources=('nucl',), temperature=80, fix_prod=1.0)],
               e_total=100.0 * hours, xs=[demand_x('water', 50.0 * hours, ['med'])])
    ok, s = solve(s, config=u.RunConfig(hours=hours, thermo_bin=sim_bin))
    assert ok
    assert s['provenance']['thermo_binary'] == sim_bin
    g = s['generator'][0]
    assert (g['a'], g['b']) == pytest.approx((0.124272, 1.97657), rel=1e-5)
    assert sum(g['h_prod']) == pytest.approx(0.05 * 50.0 * hours, rel=1e-9)
    assert s['system']['accounting_ok'] is True


# --- one binary: the one executed is the one hashed -------------------------------

def test_executed_and_hashed_binary_are_the_same_file(tmp_path, sim_bin, monkeypatch, horizon):
    """Run from a directory holding a different thermo/sim.bin. The configured
    binary must be the one run, and the one a result's provenance records."""
    decoy_dir = tmp_path / 'thermo'
    decoy_dir.mkdir()
    fake(decoy_dir, 'echo "0.5 1.0"')
    monkeypatch.chdir(tmp_path)
    a, b, err = u.thermo(*NUCLEAR, 80, binary=sim_bin)
    assert err is False and a == pytest.approx(0.124272, rel=1e-5)
    state = u.source_state(sim_bin)
    assert state['thermo_binary'] == sim_bin
    assert state['source_files_sha256']['thermo/sim.bin'] == u.file_digest(sim_bin)
    # and through a solve: the executable configured is executed and hashed
    hours = horizon(4)
    s = system(generators=[generator('nucl', var=10.0, kind='elec + ther', turbine=(290, 70), cond=0.05)],
               p2xs=[p2x('med', elec_use=0.001, ther_use=0.05, kind='elec + ther',
                         sources=('nucl',), temperature=80)],
               e_total=10.0 * hours, xs=[demand_x('water', 5.0 * hours, ['med'])])
    ok, doc = solve(s, config=u.RunConfig(hours=hours, thermo_bin=sim_bin))
    assert ok and doc['generator'][0]['a'] == pytest.approx(0.124272, rel=1e-5)
    assert doc['provenance']['thermo_binary'] == sim_bin
    assert doc['provenance']['source_files_sha256']['thermo/sim.bin'] == u.file_digest(sim_bin)


def test_the_default_binary_is_the_packaged_one():
    """Resolved through the package's resources: never the repository's
    thermo/sim.bin (the Step 1 reference build), never the working directory."""
    from ies_optimiser import _install
    assert os.path.isabs(u.Thermo_bin)
    assert u.Thermo_bin == _install.packaged_thermo()
    assert os.path.basename(u.Thermo_bin) == ('ies-optimiser-thermo.exe' if sys.platform == 'win32' else 'ies-optimiser-thermo')
    assert os.path.dirname(u.Thermo_bin).endswith(os.path.join('ies_optimiser', '_bin'))
    assert u.Thermo_bin != os.path.join(ROOT, 'thermo', 'sim.bin')
    assert u.RunConfig().thermo_bin == u.Thermo_bin          # the default a run uses


@pytest.mark.skipif(not os.path.isfile(u.Thermo_bin), reason='IES Optimiser installed without its executable')
def test_cli_from_another_directory_uses_the_packaged_binary(tmp_path):
    """End to end: decoys in the working directory are ignored."""
    for decoy in (tmp_path / 'thermo', tmp_path / 'ies_optimiser' / '_bin'):
        decoy.mkdir(parents=True)
        fake(decoy, 'echo "0.5 1.0"')
        fake(decoy, 'echo "0.5 1.0"', name='ies-optimiser-thermo')
    from conftest import system as mk
    s = mk(generators=[generator('nucl', fix=1.0, var=10.0, kind='elec + ther',
                                 turbine=(290, 70), cond=0.05)],
           p2xs=[p2x('med', elec_use=0.0015, ther_use=0.05, kind='elec + ther',
                     sources=('nucl',), temperature=80, fix_prod=1.0)],
           e_total=8760.0 * 100, xs=[demand_x('water', 8760.0 * 50, ['med'])])
    (tmp_path / 'case.json').write_text(json.dumps(s))
    out = subprocess.run([sys.executable, '-m', 'ies_optimiser', 'case.json'],
                         cwd=str(tmp_path), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, timeout=600)
    assert out.returncode == 0, out.stdout
    doc = json.loads((tmp_path / 'case.ies-optimiser.json').read_text())
    assert doc['generator'][0]['a'] == pytest.approx(0.124272, rel=1e-5)
    assert doc['provenance']['thermo_binary'] == u.Thermo_bin
    assert doc['provenance']['thermo_binary_origin'] == 'packaged'
    assert doc['provenance']['source_files_sha256']['thermo/sim.bin'] == u.file_digest(u.Thermo_bin)


def test_an_explicit_binary_is_recorded_as_an_override(horizon, sim_bin):
    hours = horizon(4)
    s = system(generators=[generator('nucl', fix=1.0, var=10.0, kind='elec + ther', turbine=(290, 70), cond=0.05)],
               p2xs=[p2x('med', elec_use=0.0015, ther_use=0.05, kind='elec + ther', sources=('nucl',),
                         temperature=80, fix_prod=1.0)],
               e_total=100.0 * hours, xs=[demand_x('water', 50.0 * hours, ['med'])])
    ok, doc = solve(s, config=u.RunConfig(hours=hours, thermo_bin=sim_bin))
    assert ok and doc['provenance']['thermo_binary'] == sim_bin
    assert doc['provenance']['thermo_binary_origin'] == 'override'


# --- Git provenance ---------------------------------------------------------------

def test_own_checkout_is_identified_as_such():
    state = u.source_state()
    if state['git_scope'] is None:
        pytest.skip('not running from a Git checkout')
    assert state['git_scope'] == 'ies_optimiser'
    assert len(state['git_revision']) == 40
    assert state['enclosing_git'] is None


def _copy_package(dest):
    from ies_optimiser import _install
    shutil.copytree(_install.PACKAGE_DIR, str(dest), ignore=shutil.ignore_patterns('__pycache__', '_bin'))


def _state_of(package_parent):
    # A subprocess importing the copy, not the installed package: a test-only
    # path entry, in a process of its own.
    # An editable install's import hook sits at the front of sys.meta_path and
    # would take precedence over sys.path, so this process removes it.
    code = ('import json, sys; '
            'sys.meta_path[:] = [f for f in sys.meta_path if not type(f).__module__.startswith("_editable")]; '
            'sys.path.insert(0, sys.argv[1]); '
            'from ies_optimiser import fcn; print(json.dumps(fcn.source_state()))')
    out = subprocess.run([sys.executable, '-c', code, str(package_parent)], stdout=subprocess.PIPE,
                         text=True, check=True)
    state = json.loads(out.stdout)
    assert state['installation']['package_dir'] == os.path.join(str(package_parent), 'ies_optimiser'), state
    return state


def _commit(repo):
    git = ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'commit.gpgsign=false']
    subprocess.run(git + ['init', '-q', str(repo)], check=True)
    subprocess.run(git + ['-C', str(repo), 'add', '-A'], check=True)
    subprocess.run(git + ['-C', str(repo), 'commit', '-q', '-m', 'host'], check=True)


@pytest.mark.skipif(shutil.which('git') is None, reason='git not available')
def test_an_enclosing_repository_is_not_reported_as_the_ies_optimiser_revision(tmp_path):
    """An IES Optimiser checkout vendored inside another project: 'git rev-parse HEAD'
    walks upward and would report the host project's commit as IES Optimiser's."""
    host = tmp_path / 'host'
    checkout = host / 'vendor' / 'ies_optimiser'
    _copy_package(checkout / 'src' / 'ies_optimiser')
    shutil.copy(os.path.join(ROOT, 'pyproject.toml'), str(checkout / 'pyproject.toml'))
    _commit(host)
    state = _state_of(checkout / 'src')
    assert state['installation']['kind'] == 'source'
    assert state['git_scope'] == 'enclosing'
    assert state['git_revision'] is None and state['git_dirty'] is None
    assert os.path.realpath(state['enclosing_git']['toplevel']) == os.path.realpath(str(host))
    assert len(state['enclosing_git']['revision']) == 40


@pytest.mark.skipif(shutil.which('git') is None, reason='git not available')
def test_an_installed_package_consults_no_repository(tmp_path):
    """A package that is not a checkout (as installed from a wheel, here inside
    an unrelated repository, like a virtual environment kept in a project):
    Git is not consulted at all."""
    host = tmp_path / 'project'
    site = host / 'venv' / 'site-packages'
    _copy_package(site / 'ies_optimiser')
    _commit(host)
    state = _state_of(site)
    assert state['installation']['kind'] == 'unknown'          # a copy, not a recorded distribution
    assert (state['git_scope'], state['git_revision'], state['git_dirty'], state['enclosing_git']) == \
        (None, None, None, None)
    assert state['source_files_sha256']['ies_optimiser/fcn.py'] == u.file_digest(str(site / 'ies_optimiser' / 'fcn.py'))


# --- output path ------------------------------------------------------------------

@pytest.mark.parametrize('src, opts, expected', [
    ('case.json', {}, 'case.ies-optimiser.json'),
    ('case.json', {'carbon-constraint': 50.0, 'non-served-power-constraint': 0.05},
     'case.ies-optimiser.carbon-constraint_50.0.non-served-power-constraint_0.05.json'),
    (os.path.join('runs.json', 'case.json'), {}, os.path.join('runs.json', 'case.ies-optimiser.json')),
    (os.path.join('a.json.d', 'my.json.case.json'), {},
     os.path.join('a.json.d', 'my.json.case.ies-optimiser.json')),
    ('case', {}, 'case.ies-optimiser.json'),
])
def test_output_path_is_suffix_aware(src, opts, expected):
    assert u.output_path(src, opts) == expected


def test_cli_writes_beside_the_input_in_a_directory_named_json(tmp_path):
    d = tmp_path / 'scenarios.json'
    d.mkdir()
    s = system(generators=[generator('g', fix=1.0, var=1.0)], e_total=8760.0)
    (d / 'case.json').write_text(json.dumps(s))
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'ies_optimiser.py'), str(d / 'case.json')],
                         cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, timeout=300)
    assert out.returncode == 0, out.stdout
    assert (d / 'case.ies-optimiser.json').is_file()
