"""The input contract: what IES Optimiser accepts, what it refuses, and why.

An input outside the model's domain used to be absorbed silently: an
efficiency of 4 created energy, a negative capacity factor built nothing and
reported success, a process soc_ini of 1.5 forced its store to zero. Each of
these is refused now, before the problem is built, with the entity and field
named. Legitimate inputs that look unusual -- negative emissions, zero costs,
zero shortage penalties -- are accepted and are tested as such.
"""

import copy
import json
import os
import subprocess
import sys

import pytest

from ies_optimiser import fcn as u
from conftest import demand_x, flex, generator, p2x, refused, solve, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAN = float('nan')
INF = float('inf')


def base():
    """A small, valid system exercising every entity type."""
    return system(
        generators=[generator('g', fix=1.0, var=10.0, emis=100.0)],
        flexes=[flex('b', fix=1.0, rte=0.81, hours=2)],
        p2xs=[p2x('p', elec_use=0.5, fix_prod=1.0, fix_strg=0.1)],
        e_total=24.0,
        xs=[demand_x('water', 12.0, ['p'])])


def at(s, path):
    node = s
    for part in path[:-1]:
        node = node[part]
    return node, path[-1]


INVALID = [
    # storage
    (('flex', 0, 'round_trip_efficiency'), 4.0, 'round_trip_efficiency'),
    (('flex', 0, 'round_trip_efficiency'), 0.0, 'round_trip_efficiency'),
    (('flex', 0, 'round_trip_efficiency'), -0.5, 'round_trip_efficiency'),
    (('flex', 0, 'round_trip_efficiency'), NAN, 'round_trip_efficiency'),
    (('flex', 0, 'hours_of_storage'), 0.0, 'hours_of_storage'),
    (('flex', 0, 'hours_of_storage'), -2.0, 'hours_of_storage'),
    (('flex', 0, 'soc_ini'), 1.5, 'soc_ini'),
    (('flex', 0, 'soc_min'), 0.7, 'soc_ini'),          # soc_ini 0.5 now below the band
    (('flex', 0, 'inflow_total'), -5.0, 'inflow_total'),
    (('flex', 0, 'charge_allowed'), 'no', 'charge_allowed'),
    (('flex', 0, 'c_strg'), -2, 'c_strg'),
    (('flex', 0, 'l_strg'), [5, 1], 'l_strg'),
    # processes
    (('p2x', 0, 'soc_ini'), 1.5, 'soc_ini'),
    (('p2x', 0, 'soc_ini'), -0.1, 'soc_ini'),
    (('p2x', 0, 'pow_use_elec_prod'), -1.0, 'pow_use_elec_prod'),
    (('p2x', 0, 'pow_use_ther_prod'), -1.0, 'pow_use_ther_prod'),
    (('p2x', 0, 'pow_use_ther_prod'), 0.05, 'pow_use_ther_prod'),   # heat use on an electric process
    (('p2x', 0, 'capacity_factor'), 1.2, 'capacity_factor'),
    (('p2x', 0, 'type'), 'elec+ther', 'type'),
    (('p2x', 0, 'c_prod'), NAN, 'c_prod'),
    (('p2x', 0, 'l_prod'), [0], 'l_prod'),
    (('p2x', 0, 'var_cost_prod'), INF, 'var_cost_prod'),
    # generators
    (('generator', 0, 'capacity_factor'), -0.5, 'capacity_factor'),
    (('generator', 0, 'capacity_factor'), 1.5, 'capacity_factor'),
    (('generator', 0, 'capacity_factor'), NAN, 'capacity_factor'),
    (('generator', 0, 'type'), 'nuclear', 'type'),
    (('generator', 0, 'c_prod'), -2, 'c_prod'),
    (('generator', 0, 'c_prod'), True, 'c_prod'),
    (('generator', 0, 'l_prod'), [-1, 5], 'l_prod'),
    (('generator', 0, 'l_prod'), [0, INF], 'l_prod'),
    (('generator', 0, 'fix_cost_prod'), NAN, 'fix_cost_prod'),
    (('generator', 0, 'var_emis_prod'), NAN, 'var_emis_prod'),
    # demands
    (('demand', 'e', 'total'), -5.0, 'total'),
    (('demand', 'e', 'total'), NAN, 'total'),
    (('demand', 'x', 0, 'total'), -1.0, 'total'),
    (('demand', 'x', 0, 'supply_sources'), 'p', 'supply_sources'),
]


@pytest.mark.parametrize('path, value, field', INVALID,
                         ids=['.'.join(map(str, p)) + '=' + repr(v) for p, v, _ in INVALID])
def test_out_of_domain_input_is_refused(horizon, monkeypatch, capsys, path, value, field):
    horizon(24)
    s = base()
    node, key = at(s, path)
    node[key] = value
    out = refused(monkeypatch, capsys, s)
    assert field in out


def test_an_efficiency_above_one_no_longer_creates_energy(horizon, monkeypatch, capsys):
    """Reproduced before the correction: a cyclic battery with efficiency 4
    met demand without any generator or inflow."""
    horizon(4)
    s = system(flexes=[flex('b', rte=4.0, l_strg=(10, 10))], e_total=4.0)
    assert 'round_trip_efficiency' in refused(monkeypatch, capsys, s)


def test_missing_required_field_is_named(horizon, monkeypatch, capsys):
    horizon(24)
    s = base()
    del s['generator'][0]['var_cost_prod']
    out = refused(monkeypatch, capsys, s)
    assert 'var_cost_prod' in out and "'g'" in out


# --- what remains legitimate ---------------------------------------------------

def test_negative_emissions_and_zero_costs_are_accepted(horizon):
    hours = horizon(4)
    s = system(generators=[generator('dac', fix=0.0, var=0.0, emis=-50.0)],
               e_total=float(hours), e_kwargs={'var_cost_ns': 0.0})
    ok, s = solve(s, {'carbon-constraint': -10.0})
    assert ok


def test_negative_economic_costs_are_a_documented_domain_choice(horizon):
    """Validation does not forbid negative costs: a subsidised unit is a
    legitimate linear input, bounded by its capacity. See the IO docs."""
    hours = horizon(4)
    s = system(generators=[generator('sub', var=-5.0, l_prod=(0, 3))], e_total=float(hours))
    ok, s = solve(s)
    assert ok
    assert s['generator'][0]['c_prod'] == pytest.approx(3.0)


def test_absent_output_arrays_are_created(horizon):
    hours = horizon(4)
    s = system(generators=[generator('g', var=1.0)], e_total=float(hours))
    for k in ('e_prod', 'h_prod'):
        del s['generator'][0][k]
    del s['demand']['e']['output_ns']
    ok, s = solve(s)
    assert ok and len(s['generator'][0]['e_prod']) == hours


def test_a_result_fed_back_as_input_is_refused_clearly(horizon, monkeypatch, capsys):
    """Solver variables used to be appended after the old numbers, and the run
    then crashed. Output arrays that already hold values are refused."""
    horizon(24)
    ok, first = solve(base())
    assert ok
    again = json.loads(json.dumps(first))
    out = refused(monkeypatch, capsys, again)
    assert 'already holds' in out


# --- the command line ---------------------------------------------------------

def cli_input(tmp_path, name='case.json'):
    s = system(generators=[generator('coal', fix=1.0, var=10.0, emis=1000.0),
                           generator('bio-ccs', fix=1.0, var=50.0, emis=-100.0)],
               e_total=8760.0)
    p = tmp_path / name
    p.write_text(json.dumps(s))
    return p


def run_cli(path, *args, cwd=ROOT):
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'ies_optimiser.py'), str(path)] + list(args),
                         cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, timeout=300)
    return out.returncode, out.stdout


@pytest.mark.parametrize('args, reason', [
    (['carbon-contraint=0'], 'unknown option'),
    (['carbon-constraint', '0'], 'name=value'),
    (['carbon-constraint'], 'name=value'),
    (['carbon-constraint='], 'not a number'),
    (['=50'], 'unknown option'),
    (['carbon-constraint=abc'], 'not a number'),
    (['carbon-constraint=nan'], 'finite'),
    (['carbon-constraint=inf'], 'finite'),
    (['non-served-power-constraint=-inf'], 'finite'),
    (['non-served-power-constraint=1.5'], 'non-served-power-constraint'),
    (['non-served-power-constraint=-0.1'], 'non-served-power-constraint'),
    (['carbon-constraint=1', 'carbon-constraint=2'], 'more than once'),
])
def test_invalid_options_fail_before_solving(tmp_path, args, reason):
    p = cli_input(tmp_path)
    code, out = run_cli(p, *args)
    assert code != 0
    assert reason in out
    assert not list(tmp_path.glob('*.ies-optimiser*.json'))          # nothing written


def test_valid_combined_options(tmp_path):
    p = cli_input(tmp_path)
    code, out = run_cli(p, 'carbon-constraint=-5', 'non-served-power-constraint=0.05')
    assert code == 0, out
    written = tmp_path / 'case.ies-optimiser.carbon-constraint_-5.0.non-served-power-constraint_0.05.json'
    doc = json.loads(written.read_text())
    assert doc['provenance']['options'] == {'carbon-constraint': -5.0,
                                            'non-served-power-constraint': 0.05}
    # a negative carbon target is honoured, not discarded
    assert doc['system']['emis'] <= -5.0 * 8760.0 + 1e-6


def test_parse_options_directly():
    assert u.parse_options([]) == {}
    assert u.parse_options(['carbon-constraint=50']) == {'carbon-constraint': 50.0}
    assert list(u.parse_options(['non-served-power-constraint=0', 'carbon-constraint=1'])) == \
        ['non-served-power-constraint', 'carbon-constraint']        # order kept for the file name


# --- defaults are applied, not only accepted -------------------------------------
#
# A field the contract says may be omitted must lead to a working run, not merely
# pass validation: an accepted default that was never stored made the equation
# or reporting modules fail later on the missing key. An explicit null is not an
# omission and is refused.

OPTIONAL = [
    ('generator', 0, 'profile'),
    ('generator', 0, 'turbine_t_p'),
    ('generator', 0, 'condenser_p'),
    ('generator', 0, 'a'),
    ('generator', 0, 'b'),
    ('generator', 0, 'e_prod'),
    ('generator', 0, 'h_prod'),
    ('flex', 0, 'soc_min'),
    ('flex', 0, 'soc_max'),
    ('flex', 0, 'inflow_total'),
    ('flex', 0, 'charge_allowed'),
    ('flex', 0, 'e_char'),
    ('p2x', 0, 'profile'),
    ('p2x', 0, 'temperature'),
    ('p2x', 0, 'supply_sources'),
    ('p2x', 0, 'shadow_prices'),
    ('demand', 'e', 'profile'),
    ('demand', 'e', 'supply_sources'),
    ('demand', 'e', 'shadow_prices'),
    ('demand', 'e', 'kpis'),
    ('demand', 'x', 0, 'profile'),
]


@pytest.mark.parametrize('path', OPTIONAL, ids=['.'.join(map(str, p)) for p in OPTIONAL])
def test_an_omitted_optional_field_still_runs_and_reconciles(horizon, path):
    horizon(24)
    s = base()
    node, key = at(s, path)
    node.pop(key, None)                  # some are already absent from base()
    ok, s = solve(s)
    assert ok
    assert s['system']['accounting_ok'] is True
    json.dumps(s, allow_nan=False)


def test_defaults_are_written_into_the_model_input(horizon):
    horizon(24)
    s = base()
    for k in ('soc_min', 'soc_max'):
        del s['flex'][0][k]
    del s['generator'][0]['profile']
    ok, s = solve(s)
    assert ok
    f = s['flex'][0]
    assert (f['soc_min'], f['soc_max'], f['inflow_total'], f['charge_allowed']) == (0.0, 1.0, 0.0, True)
    assert s['generator'][0]['profile'] == ''
    assert (s['generator'][0]['a'], s['generator'][0]['b']) == (0, 0)


@pytest.mark.parametrize('path', [
    ('flex', 0, 'soc_min'), ('flex', 0, 'soc_max'), ('flex', 0, 'inflow_total'),
    ('flex', 0, 'charge_allowed'), ('generator', 0, 'profile'), ('generator', 0, 'condenser_p'),
    ('generator', 0, 'turbine_t_p'), ('p2x', 0, 'profile'), ('p2x', 0, 'supply_sources'),
    ('demand', 'e', 'profile'), ('demand', 'e', 'l_ns'), ('generator', 0, 'fix_cost_prod'),
    ('flex', 0, 'e_char'),
], ids=lambda p: '.'.join(map(str, p)))
def test_an_explicit_null_is_refused(horizon, monkeypatch, capsys, path):
    horizon(24)
    s = base()
    node, key = at(s, path)
    node[key] = None
    out = refused(monkeypatch, capsys, s)
    assert path[-1] in out
