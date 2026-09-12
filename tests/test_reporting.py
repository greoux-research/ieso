"""Reported quantities: cost accounts, cap duals, and process heat prices."""

import math

import numpy as np
import pytest

from ieso_modules import fcn as u
from conftest import demand_x, flex, generator, p2x, solve, system


# --- cost accounts ---------------------------------------------------------

def test_accounts_reconcile_with_the_legacy_cost_kpi(horizon):
    """cost == (resource cost + shortage penalty) / demand, as before."""
    hours = horizon(24)
    ok, s = solve(system(generators=[generator('gas', var=10.0)], e_total=100.0 * hours))
    assert ok
    d = s['demand']['e']
    acc = d['accounts']
    assert d['kpis']['cost'] == pytest.approx(
        (acc['resource_cost'] + acc['shortage_penalty']) / acc['demand'], rel=1e-12)


def test_shortage_penalty_is_separated_from_resource_cost(horizon):
    """A penalty on unserved demand is not money spent on supply."""
    hours = horizon(24)
    s = system(generators=[generator('gas', var=1.0, l_prod=(0, 50))],
               e_total=100.0 * hours, e_kwargs={'var_cost_ns': 5.0})
    ok, s = solve(s)
    assert ok
    acc = s['demand']['e']['accounts']
    assert acc['unmet_demand'] > 0
    assert acc['shortage_penalty'] == pytest.approx(acc['unmet_demand'] * 5.0)
    assert acc['resource_cost'] == pytest.approx(s['system']['cost'], rel=1e-9)
    assert acc['resource_cost_per_demand'] < acc['resource_cost_per_served']


def test_served_and_unmet_split_the_demand(horizon):
    hours = horizon(24)
    s = system(generators=[generator('gas', var=1.0, l_prod=(0, 50))],
               e_total=100.0 * hours, e_kwargs={'var_cost_ns': 5.0})
    ok, s = solve(s)
    acc = s['demand']['e']['accounts']
    assert acc['served_demand'] + acc['unmet_demand'] == pytest.approx(acc['demand'])
    assert s['demand']['e']['kpis']['reli'] == pytest.approx(
        acc['served_demand'] / acc['demand'])


def test_per_served_is_undefined_rather_than_infinite(horizon):
    """Nothing delivered means no cost per unit delivered, not a division."""
    hours = horizon(24)
    s = system(generators=[generator('gas', var=100.0, l_prod=(0, 0))],
               e_total=100.0 * hours, e_kwargs={'var_cost_ns': 5.0})
    ok, s = solve(s)
    assert ok
    acc = s['demand']['e']['accounts']
    assert acc['served_demand'] == pytest.approx(0.0)
    assert acc['resource_cost_per_served'] is None


# --- cap duals -------------------------------------------------------------

def test_slack_reliability_cap_reports_no_marginal_value(horizon):
    """The row rested on its redundant lower bound and reported a large dual."""
    hours = horizon(24)
    s = system(generators=[generator('gas', var=10.0)], e_total=100.0 * hours,
               e_kwargs={'var_cost_ns': 10000.0})
    ok, s = solve(s, {'non-served-power-constraint': 0.5})
    assert ok
    sp = s['demand']['e']['shadow_prices']
    detail = sp['reliability_cap_detail']
    assert detail['activity'] == pytest.approx(0.0)
    assert detail['slack'] > 0
    assert detail['binding'] is False
    assert sp['reliability_cap'] == 0.0


def test_binding_reliability_cap_reports_its_dual(horizon):
    hours = horizon(24)
    s = system(generators=[generator('gas', var=100.0)], e_total=100.0 * hours,
               e_kwargs={'var_cost_ns': 5.0})
    ok, s = solve(s, {'non-served-power-constraint': 0.25})
    assert ok
    detail = s['demand']['e']['shadow_prices']['reliability_cap_detail']
    assert detail['activity'] == pytest.approx(detail['cap'], rel=1e-9)
    assert detail['binding'] is True


def test_carbon_cap_detail_reports_the_activity(horizon):
    hours = horizon(24)
    s = system(generators=[generator('coal', var=10.0, emis=800.0),
                           generator('wind', fix=1.0, var=0.0)],
               e_total=100.0 * hours)
    ok, s = solve(s, {'carbon-constraint': 100.0})
    assert ok
    detail = s['demand']['e']['shadow_prices']['carbon_cap_detail']
    assert detail['activity'] == pytest.approx(s['system']['emis'], rel=1e-9)
    assert detail['cap'] == pytest.approx(100.0 * 100.0 * hours)


# --- process heat duals ----------------------------------------------------

def test_thermal_process_reports_a_heat_price(horizon, monkeypatch):
    hours = horizon(24)
    monkeypatch.setattr(u, 'thermo', lambda *args: (0.25, 1.5, False))
    s = system(
        generators=[generator('gas', var=10.0, kind='elec + ther', turbine=(564, 152), cond=0.05)],
        p2xs=[p2x('med', elec_use=0.0015, ther_use=0.05, kind='elec + ther',
                  sources=('gas',), temperature=80)],
        e_total=100.0 * hours, xs=[demand_x('water', 50.0 * hours, ['med'])])
    ok, s = solve(s)
    assert ok
    duals = s['p2x'][0]['shadow_prices']['demand_match']
    assert len(duals) == hours
    assert any(abs(v) > 0 for v in duals)


def test_electric_process_reports_no_heat_price(horizon):
    """Reverse osmosis has no heat balance; the series must stay empty."""
    hours = horizon(24)
    s = system(generators=[generator('gas', var=10.0)],
               p2xs=[p2x('ro', elec_use=0.0045)],
               e_total=100.0 * hours, xs=[demand_x('water', 50.0 * hours, ['ro'])])
    ok, s = solve(s)
    assert ok
    assert s['p2x'][0]['shadow_prices']['demand_match'] == []


# --- storage balance -------------------------------------------------------

def balance_residual(f, hours, inflow=None):
    r = math.sqrt(f['round_trip_efficiency'])
    worst = 0.0
    for i in range(hours):
        prev = f['soc_ini'] * f['c_strg'] if i == 0 else f['e_strg'][i - 1]
        expected = prev + f['e_char'][i] * r - f['e_disc'][i] / r
        if inflow is not None:
            expected += inflow[i] - f['e_spil'][i]
        worst = max(worst, abs(f['e_strg'][i] - expected))
    return worst


def test_battery_satisfies_the_storage_balance(horizon):
    hours = horizon(24)
    shape = [0.0] * 12 + [1.0] * 12
    s = system(generators=[generator('solar', fix=1.0, profile=shape, cf=0.5)],
               flexes=[flex('bstr', fix=0.1)], e_total=100.0 * hours)
    ok, s = solve(s)
    assert ok
    assert balance_residual(s['flex'][0], hours) < 1e-6


def test_reservoir_with_inflow_satisfies_the_storage_balance(horizon):
    """Discharge over charge equals round-trip efficiency only without inflow."""
    hours = horizon(24)
    s = system(
        generators=[generator('gas', var=50.0)],
        flexes=[flex('hdam', fix=0.1, inflow_total=200.0, inflow_profile='',
                     charge_allowed=False)],
        e_total=100.0 * hours)
    ok, s = solve(s)
    assert ok
    f = s['flex'][0]
    inflow = u.dm_h('', 200.0)
    assert balance_residual(f, hours, inflow) < 1e-6
    assert sum(f['e_char']) == pytest.approx(0.0)      # a dam cannot be pumped
    assert sum(f['e_disc']) > 0                        # but it does generate


def test_a_net_negative_emissions_target_is_representable(horizon):
    """The carbon row is a cap, so it needs no lower bound.

    The redundant lower bound of zero did more than obscure the dual: it
    asserted that system emissions could not be negative, which makes any
    net-negative target infeasible by construction in a system containing a
    removal technology.
    """
    hours = horizon(24)
    s = system(
        generators=[generator('gas', var=10.0, emis=400.0),
                    generator('beccs', var=40.0, emis=-500.0)],
        e_total=100.0 * hours)
    ok, s = solve(s, {'carbon-constraint': -100.0})
    assert ok
    assert s['system']['emis'] < 0
    assert s['system']['emis'] <= -100.0 * 100.0 * hours + 1e-6


def test_carbon_cap_dual_is_reported_when_binding(horizon):
    hours = horizon(24)
    s = system(generators=[generator('coal', var=5.0, emis=900.0),
                           generator('gas', var=40.0, emis=400.0)],
               e_total=100.0 * hours)
    ok, s = solve(s, {'carbon-constraint': 500.0})
    assert ok
    sp = s['demand']['e']['shadow_prices']
    assert sp['carbon_cap_detail']['binding'] is True
    assert sp['carbon_cap'] > 0
