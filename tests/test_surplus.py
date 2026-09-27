"""Surplus, unallocated output, and reconciliation to the system totals.

The demand balances are inequalities, so output may exceed what final demand
takes. The accounting used to assume every unit of output belonged to a final
demand; where it did not, part of the system cost and emissions was allocated
to nobody and silently disappeared from the commodity accounts. Surplus is now
reported, and whatever is not allocated is reported as unallocated, so that

    allocated + unallocated = system total

for output, cost and emissions alike. Expected values are worked by hand.
"""

import numpy as np
import pytest

from ieso import fcn as u
from conftest import demand_x, flex, generator, p2x, solve, system

REL = 1e-9


def reconciles(s):
    sy = s['system']
    assert sy['accounting_ok'] is True, {k: v for k, v in sy['checks'].items() if not v['ok']}
    assert sy['allocated']['cost'] + sy['unallocated']['cost'] == pytest.approx(sy['cost'], rel=REL, abs=1e-9)
    assert sy['allocated']['emis'] + sy['unallocated']['emis'] == pytest.approx(sy['emis'], rel=REL, abs=1e-9)
    if sy['allocation_defined']:
        assert sy['allocated']['output'] + sy['unallocated']['output'] == pytest.approx(sy['output'], rel=REL, abs=1e-9)
        commodities = [s['demand']['e']] + [d for d in s['demand']['x'] if d['total'] > 0]
        assert sum(d['accounts']['resource_cost'] for d in commodities if d['total'] > 0) == \
            pytest.approx(sy['allocated']['cost'], rel=REL, abs=1e-9)


def test_no_surplus_leaves_nothing_unallocated(horizon):
    hours = horizon(4)
    s = system(generators=[generator('gas', fix=2.0, var=10.0, emis=300.0)],
               e_total=10.0 * hours)
    ok, s = solve(s)
    assert ok
    reconciles(s)
    sy = s['system']
    assert sy['unallocated']['output'] == pytest.approx(0.0, abs=1e-9)
    assert sy['allocated_share_total'] == pytest.approx(1.0)
    assert s['demand']['e']['surplus'] == pytest.approx([0.0] * hours, abs=1e-9)


def test_negative_emissions_surplus_reconciles_every_dollar_and_kilogram(horizon):
    """1 MWh demanded, a 10 $/MWh unit emitting -1 kg/MWh, carbon target -2
    kg/MWh of demand. Generation 2 MWh, cost $20, emissions -2 kg; half of it
    serves demand and half is surplus. Before, $10 and -1 kg vanished."""
    horizon(1)
    s = system(generators=[generator('dac', var=10.0, emis=-1.0)], e_total=1.0)
    ok, s = solve(s, {'carbon-constraint': -2.0})
    assert ok
    assert s['generator'][0]['e_prod'] == pytest.approx([2.0])
    sy = s['system']
    assert sy['cost'] == pytest.approx(20.0)
    assert sy['emis'] == pytest.approx(-2.0)
    e = s['demand']['e']
    assert e['surplus'] == pytest.approx([1.0])
    assert e['accounts']['resource_cost'] == pytest.approx(10.0)
    assert e['accounts']['emissions'] == pytest.approx(-1.0)
    assert sy['unallocated']['cost'] == pytest.approx(10.0)
    assert sy['unallocated']['emis'] == pytest.approx(-1.0)
    assert sy['unallocated']['electricity_surplus'] == pytest.approx(1.0)
    assert sy['surplus']['electricity'] == pytest.approx(1.0)
    assert e['kpis']['reli'] == pytest.approx(1.0)
    reconciles(s)


def test_zero_cost_surplus_may_differ_between_optima_but_always_reconciles(horizon):
    """A zero-cost unit may overproduce at no cost, so the reported surplus
    depends on which optimal vertex the solver returns. Nothing about the
    surplus itself is asserted -- only that it is reported as the residual it
    is, and that the accounts reconcile whatever it turns out to be."""
    hours = horizon(3)
    shape = [1.0, 0.2, 0.2]
    s = system(generators=[generator('solr', fix=1.0, var=0.0, profile=shape, cf=0.8),
                           generator('gas', fix=1.0, var=50.0)],
               e_total=float(hours))
    ok, s = solve(s)
    assert ok
    gen = np.sum([g['e_prod'] for g in s['generator']], axis=0)
    residual = gen + np.array(s['demand']['e']['output_ns']) - 1.0
    assert s['demand']['e']['surplus'] == pytest.approx(residual.tolist(), abs=1e-9)
    assert s['system']['surplus']['electricity'] == pytest.approx(residual.sum(), abs=1e-9)
    reconciles(s)


def test_product_surplus_is_reported_and_stays_in_the_commodity(horizon):
    """A process paid to produce (var cost -10 $/unit, against 0.5 MWh x 10
    $/MWh of electricity) makes all it can: 3 per hour against 1 demanded. The 2 undelivered units are product surplus. Their
    electricity is still an input to the water chain, so it remains in the
    water share rather than being counted a second time as unallocated."""
    hours = horizon(2)
    s = system(generators=[generator('g', var=10.0)],
               p2xs=[p2x('p', elec_use=0.5, var_prod=-10.0, l_prod=(0, 3), c_prod=3)],
               e_total=2.0, xs=[demand_x('water', 2.0, ['p'])])
    ok, s = solve(s)
    assert ok
    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    assert sum(s['p2x'][0]['x_prod']) == pytest.approx(6.0)
    assert sum(water['surplus']) == pytest.approx(4.0)
    assert water['accounts']['surplus'] == pytest.approx(4.0)
    assert s['system']['surplus']['products']['water'] == pytest.approx(4.0)
    # electricity 2 MWh, water 6 x 0.5 = 3 MWh: 5 MWh output, all allocated
    assert water['accounts']['allocation_share'] == pytest.approx(3 / 5)
    assert s['system']['unallocated']['output'] == pytest.approx(0.0, abs=1e-9)
    reconciles(s)


def test_unused_heat_is_reported_and_unallocated(horizon, fixed_thermo):
    """A unit paid to run (var cost -1 $/MWh) runs at its limit whatever is
    demanded. Between electricity and heat the split is not unique -- both earn
    the same per electricity-equivalent MWh -- but the total is: the whole
    10 MWh of electricity-equivalent capacity, of which only the process's
    heat and electricity are allocated. Everything else, electricity surplus or
    unused heat, is unallocated."""
    a, b = fixed_thermo
    hours = horizon(2)
    s = system(generators=[generator('chp', var=-1.0, kind='elec + ther', c_prod=10,
                                     turbine=(564, 152), cond=0.05)],
               p2xs=[p2x('med', elec_use=0.1, ther_use=1.0, kind='elec + ther',
                         sources=('chp',), temperature=80, c_prod=1, c_strg=0)],
               e_total=0.0, xs=[demand_x('water', 2.0, ['med'])])
    ok, s = solve(s)
    assert ok
    g = s['generator'][0]
    med = s['p2x'][0]
    e, h = np.array(g['e_prod']), np.array(g['h_prod'])
    assert (e + a * h) == pytest.approx([10.0, 10.0])
    heat_residual = h - 1.0 * np.array(med['x_prod'])
    assert med['heat_surplus'] == pytest.approx(heat_residual.tolist(), abs=1e-9)
    assert s['system']['surplus']['heat'] == pytest.approx(heat_residual.sum(), abs=1e-9)
    # allocated to water: 1 unit/h x (0.1 MWh + 1 MWh heat x a) over 2 h
    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    assert water['accounts']['allocated_output'] == pytest.approx(2 * (0.1 + a * 1.0))
    sy = s['system']
    assert sy['unallocated']['output'] == pytest.approx(20.0 - 2 * (0.1 + a))
    assert sy['unallocated']['electricity_surplus'] + sy['unallocated']['unused_heat'] == \
        pytest.approx(sy['unallocated']['output'])
    reconciles(s)


def test_reservoir_spill_is_reported_separately_from_output(horizon):
    """40 MWh of inflow, discharge limited to 1 MWh/h by c_strg/hours = 5/5, a
    cyclic store. 4 MWh are generated and 36 MWh must be spilled. Spill never
    became output, so it carries no share of anything."""
    hours = horizon(4)
    s = system(flexes=[flex('dam', c_strg=5, hours=5, rte=1.0, soc_ini=0.5,
                            inflow_total=40.0, inflow_profile='', charge_allowed=False)],
               e_total=float(hours))
    ok, s = solve(s)
    assert ok
    assert s['system']['surplus']['spill'] == pytest.approx(36.0)
    assert s['system']['output'] == pytest.approx(4.0)
    assert s['demand']['e']['accounts']['allocation_share'] == pytest.approx(1.0)
    reconciles(s)


def test_nothing_generated_all_demand_unmet(horizon):
    """A unit that must be built (l_prod lower bound) but is too dear to run:
    its fixed cost is real and allocated to nobody; there is no output to
    share it by. Reliability is 0 -- known exactly -- not the -1 placeholder."""
    hours = horizon(2)
    s = system(generators=[generator('dear', fix=5.0, var=1e6, l_prod=(1, 10))],
               e_total=2.0, e_kwargs={'var_cost_ns': 10.0})
    ok, s = solve(s)
    assert ok
    e = s['demand']['e']
    assert e['kpis']['reli'] == pytest.approx(0.0)
    assert e['accounts']['allocation_share'] is None
    assert e['accounts']['resource_cost'] is None
    sy = s['system']
    assert sy['allocation_defined'] is False
    assert sy['cost'] == pytest.approx(5.0)
    assert sy['allocated']['cost'] == 0.0
    assert sy['unallocated']['cost'] == pytest.approx(5.0)
    assert sy['unallocated']['share'] is None
    reconciles(s)


def test_zero_demand_everywhere(horizon):
    horizon(2)
    ok, s = solve(system(generators=[generator('g', var=1.0)], e_total=0.0))
    assert ok
    e = s['demand']['e']
    assert e['kpis'] == {'cost': -1, 'emis': -1, 'reli': -1}      # not applicable
    assert s['system']['allocation_defined'] is False
    reconciles(s)


def test_fixed_and_optimised_capacity_reconcile_with_the_objective(horizon):
    hours = horizon(6)
    s = system(generators=[generator('pinned', fix=100.0, var=5.0, c_prod=4),
                           generator('sized', fix=10.0, var=40.0)],
               flexes=[flex('b', fix=3.0, c_strg=8, hours=2)],
               e_total=6.0 * hours, e_kwargs={'var_cost_ns': 30.0})
    ok, s = solve(s)
    assert ok
    check = s['system']['checks']['objective_reconciliation']
    assert check['ok'] is True
    fixed = 4 * 100.0 + 8 * 3.0
    penalty = s['demand']['e']['accounts']['shortage_penalty']
    assert s['system']['cost'] + penalty == pytest.approx(s['solver']['_objective'] + fixed, rel=REL)
    reconciles(s)


def test_accounting_failures_are_machine_readable(horizon, monkeypatch):
    """A failed check is recorded in the result, not only printed."""
    hours = horizon(2)
    monkeypatch.setattr(u, 'Recon_rtol', -1.0)       # make every reconciliation impossible
    monkeypatch.setattr(u, 'Recon_atol', -1.0)
    ok, s = solve(system(generators=[generator('g', var=1.0)], e_total=2.0))
    assert ok
    assert s['system']['accounting_ok'] is False
    failed = [k for k, v in s['system']['checks'].items() if not v['ok']]
    assert 'cost_reconciliation' in failed
