"""Demand shadow prices against finite differences of the objective.

The unmet-demand variable is bounded above by the hour's demand. Raising
demand in an hour therefore moves two things: the balance row, and -- where
the shortfall sits at that bound -- the bound itself. The balance-row dual
(demand_match) holds every bound fixed, so where the shortfall bound binds it
is not the marginal value of demand. demand_marginal adds the shortfall
variable's reduced cost there.

What demand_marginal is: a subgradient of the objective as a function of the
hour's demand. Away from breakpoints that is the derivative, and the finite
differences below measure it exactly. At a breakpoint it lies between the left
and right derivatives and need not equal either -- the last two tests pin that
down, including a zero-demand case where it reports 0 against a right
derivative of 100.

Reproduced before the correction: one hour, generation at 100 $/MWh, primary
shortage at 10 $/MWh, a process needing 1 MWh. Primary demand is shed while
generation supplies the process; raising demand by 0.001 MWh costs $0.01, i.e.
10 $/MWh, but the only reported price was 100 $/MWh.

The first five cases are away from breakpoints, so the finite difference is
exact there.
"""

import pytest

from conftest import demand_x, generator, p2x, solve, system

DELTA = 1e-3


def objective(build, demand, **kw):
    ok, s = solve(build(demand, **kw))
    assert ok
    return s['solver']['_objective'], s


def fd(build, demand, hour, which='e'):
    base, s = objective(build, demand)
    bumped = list(demand)
    bumped[hour] += DELTA
    up, _ = objective(build, bumped)
    return (up - base) / DELTA, s


def electricity(demand, e_ns_cost=10.0, l_ns=(0, 1e9), availability=''):
    """demand: hourly electricity demand. A 3 MW generator at 100 $/MWh, and a
    process needing 1 MWh an hour whose product is dear to leave unmet."""
    cf = 1.0 if availability == '' else sum(availability) / len(availability)
    return system(generators=[generator('g', var=100.0, l_prod=(0, 3), c_prod=3,
                                        profile=availability, cf=cf)],
                  p2xs=[p2x('p', elec_use=1.0, c_prod=1, c_strg=0)],
                  e_total=sum(demand),
                  xs=[demand_x('water', float(len(demand)), ['p'], var_cost_ns=1e4)],
                  e_kwargs={'profile': list(demand), 'var_cost_ns': e_ns_cost, 'l_ns': l_ns})


def product(demand, x_ns_cost=5.0):
    """demand: hourly water demand, produced at 0.5 MWh/unit from 100 $/MWh
    electricity (50 $/unit) but left unmet at only 5 $/unit."""
    return system(generators=[generator('g', var=100.0)],
                  p2xs=[p2x('p', elec_use=0.5, c_prod=10, c_strg=0)],
                  e_total=1.0,
                  xs=[demand_x('water', sum(demand), ['p'], profile=list(demand), var_cost_ns=x_ns_cost)])


def test_binding_shortfall_bound_marginal_is_the_penalty(horizon):
    horizon(1)
    slope, s = fd(electricity, [1.0], 0)
    sp = s['demand']['e']['shadow_prices']
    assert slope == pytest.approx(10.0, rel=1e-6)
    assert sp['demand_marginal'][0] == pytest.approx(slope, rel=1e-6)
    assert sp['demand_match'][0] == pytest.approx(100.0)       # the row dual, still reported as such


def test_unbound_shortfall_marginal_equals_the_row_dual(horizon):
    """Shortfall dearer than generation: demand is served, no bound binds."""
    horizon(1)
    build = lambda d: electricity(d, e_ns_cost=1000.0)
    slope, s = fd(build, [1.0], 0)
    sp = s['demand']['e']['shadow_prices']
    assert slope == pytest.approx(100.0, rel=1e-6)
    assert sp['demand_marginal'][0] == pytest.approx(slope, rel=1e-6)
    assert sp['demand_match'][0] == pytest.approx(slope, rel=1e-6)


def test_shortfall_capped_by_l_ns_does_not_move_with_demand(horizon):
    """l_ns[1] = 0.5 < demand: the binding bound is the configured one, which
    demand does not move, so the extra MWh must be generated at 100."""
    horizon(1)
    build = lambda d: electricity(d, l_ns=(0, 0.5))
    slope, s = fd(build, [1.0], 0)
    sp = s['demand']['e']['shadow_prices']
    assert slope == pytest.approx(100.0, rel=1e-6)
    assert sp['demand_marginal'][0] == pytest.approx(slope, rel=1e-6)


def test_product_shortfall_bound(horizon):
    horizon(1)
    slope, s = fd(product, [2.0], 0)
    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    assert slope == pytest.approx(5.0, rel=1e-6)
    assert water['shadow_prices']['demand_marginal'][0] == pytest.approx(slope, rel=1e-6)


def test_each_hour_against_its_own_finite_difference(horizon):
    """Three hours, shortage at 1000 $/MWh. Hours 0 and 2 are served at 100.
    In hour 1 only 1 MW is available and the process takes it, so primary
    demand is shed entirely: the shortfall sits at its demand bound. The row
    dual there is the product's 1e4 $/unit; the marginal cost of demand is the
    1000 $/MWh shortage penalty."""
    horizon(3)
    avail = [1.0, 1.0 / 3.0, 1.0]
    build = lambda d: electricity(d, e_ns_cost=1000.0, availability=avail)
    demand = [1.0, 4.0, 1.5]
    _, s = objective(build, demand)
    sp = s['demand']['e']['shadow_prices']
    expected = [100.0, 1000.0, 100.0]
    for hour in range(3):
        slope, _ = fd(build, demand, hour)
        assert slope == pytest.approx(expected[hour], rel=1e-6), hour
        assert sp['demand_marginal'][hour] == pytest.approx(slope, rel=1e-6), hour
    assert sp['demand_match'][1] == pytest.approx(1e4)


# --- breakpoints: between the one-sided derivatives, not necessarily either -----

def single(demand):
    """One hour: a 1 MW unit at 100 $/MWh, shortage at 1000 $/MWh."""
    return system(generators=[generator('g', var=100.0, c_prod=1)], e_total=sum(demand),
                  e_kwargs={'profile': list(demand) if sum(demand) > 0 else '', 'var_cost_ns': 1000.0})


def one_sided(build, demand, hour):
    base, s = objective(build, demand)
    up = list(demand); up[hour] += DELTA
    right = (objective(build, up)[0] - base) / DELTA
    left = None
    if demand[hour] >= DELTA:
        down = list(demand); down[hour] -= DELTA
        left = (base - objective(build, down)[0]) / DELTA
    return left, right, s


def test_zero_demand_is_a_breakpoint(horizon):
    """Reproduced in review: at zero demand the reported value is 0 while the
    first MWh costs 100. Both are consistent with the documented meaning -- a
    subgradient, and demand cannot fall below zero -- but the value is not the
    derivative for an increase, and the documentation no longer claims it is."""
    horizon(1)
    left, right, s = one_sided(single, [0.0], 0)
    marginal = s['demand']['e']['shadow_prices']['demand_marginal'][0]
    assert left is None
    assert right == pytest.approx(100.0, rel=1e-6)
    assert marginal <= right + 1e-6


def test_capacity_breakpoint_lies_between_the_one_sided_derivatives(horizon):
    """Demand exactly at the unit's 1 MW: the last MWh costs 100, the next 1000."""
    horizon(1)
    left, right, s = one_sided(single, [1.0], 0)
    marginal = s['demand']['e']['shadow_prices']['demand_marginal'][0]
    assert left == pytest.approx(100.0, rel=1e-6)
    assert right == pytest.approx(1000.0, rel=1e-6)
    assert left - 1e-6 <= marginal <= right + 1e-6
