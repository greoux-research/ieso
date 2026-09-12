"""Cost and emission allocation across commodities, and the guard on it."""

import numpy as np
import pytest

from ieso_modules import fcn as u
from ieso_modules import pos_dmd
from conftest import flex, generator, p2x, demand_x, solve, system


@pytest.fixture
def fixed_thermo(monkeypatch):
    """Pin the cogeneration coefficients so the allocation is tested alone."""
    monkeypatch.setattr(u, 'thermo', lambda *args: (0.25, 1.5, False))
    return 0.25, 1.5


def thermal_case(hours):
    """One MED-like process drawing heat from two eligible suppliers.

    'cheap' dispatches; 'costly' is priced out and never produces heat. The
    defect summed the process's whole heat requirement once per eligible
    supplier, so it counted heat that was never generated.
    """
    return system(
        generators=[
            generator('cheap', var=10.0, kind='elec + ther', turbine=(290, 70), cond=0.05),
            generator('costly', var=900.0, kind='elec + ther', turbine=(564, 152), cond=0.05),
        ],
        p2xs=[p2x('med', elec_use=0.0015, ther_use=0.05, kind='elec + ther',
                  sources=('cheap', 'costly'), temperature=80)],
        e_total=100.0 * hours,
        xs=[demand_x('water', 50.0 * hours, ['med'])],
    )


def test_allocation_shares_sum_to_one(horizon, fixed_thermo):
    hours = horizon(24)
    ok, s = solve(thermal_case(hours))
    assert ok
    assert s['system']['allocated_share_total'] == pytest.approx(1.0, abs=1e-9)


def test_heat_attributed_is_heat_dispatched(horizon, fixed_thermo):
    """Water carries its own electricity plus the heat actually generated."""
    hours = horizon(24)
    a, _ = fixed_thermo
    ok, s = solve(thermal_case(hours))
    assert ok

    med = s['p2x'][0]
    dispatched = sum(sum(g['h_prod']) for g in s['generator'] if g['h_prod'])
    expected = sum(med['x_prod']) * med['pow_use_elec_prod'] + dispatched * a

    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    attributed = water['accounts']['allocation_share'] * s['system']['output']
    assert attributed == pytest.approx(expected, rel=1e-9)


def test_idle_supplier_is_not_charged_for_heat(horizon, fixed_thermo):
    """Listing a second supplier that never runs must not change the answer."""
    hours = horizon(24)

    _, both = solve(thermal_case(hours))

    one = thermal_case(hours)
    one['generator'] = [g for g in one['generator'] if g['iden'] == 'cheap']
    one['p2x'][0]['supply_sources'] = ['cheap']
    _, single = solve(one)

    def share(s):
        return [d for d in s['demand']['x'] if d['iden'] == 'water'][0]['accounts']['allocation_share']

    assert share(both) == pytest.approx(share(single), rel=1e-9)


def test_emissions_follow_the_same_corrected_share(horizon, fixed_thermo):
    hours = horizon(24)
    ok, s = solve(thermal_case(hours))
    assert ok
    for d in [s['demand']['e']] + [x for x in s['demand']['x'] if x['total'] > 0]:
        assert d['accounts']['emissions'] == pytest.approx(
            d['accounts']['allocation_share'] * s['system']['emis'], rel=1e-9)


def test_the_guard_fires_when_shares_do_not_sum_to_one(horizon, monkeypatch, capsys):
    """The threshold was 1e+9, which no residual could ever exceed."""
    hours = horizon(24)
    monkeypatch.setattr(u, 'Verbose', True)

    real = pos_dmd.g_figs
    monkeypatch.setattr(pos_dmd, 'g_figs', lambda s: tuple(
        [real(s)[0] * 0.5] + list(real(s)[1:])))          # halve total output

    solve(system(generators=[generator('gas', var=10.0)], e_total=100.0 * hours))
    assert 'allocation shares do not sum to one' in capsys.readouterr().out
