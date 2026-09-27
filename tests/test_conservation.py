"""Conservation: unmet demand is bounded by demand, and product is delivered once.

The demand balances are inequalities, so every quantity entering them must be
physical. An unbounded shortfall variable is not: on the electricity balance it
offsets process consumption, so "shedding" demand that never existed can power
a process. On a product balance it lets unmet demand exceed demand, and served
demand go negative. Every expected value below is worked out by hand.
"""

import pytest

from ies_optimiser import fcn as u
from conftest import demand_x, generator, p2x, refused, solve, system

TOL = 1e-7


def test_shortfall_cannot_power_a_process(horizon):
    """2 MWh of demand over two hours, a process wanting 20 MWh, no generator.

    Before the correction the solver reported 22 MWh unmet against 2 MWh of
    demand, produced all 20 units, and recorded served demand of -20 MWh.
    """
    horizon(2)
    # Electricity shortage is priced below the product's, so fictitious shedding
    # (22 x 100) undercuts leaving the product unmet (20 x 1000 + 2 x 100).
    s = system(p2xs=[p2x('p', elec_use=1.0)], e_total=2.0,
               xs=[demand_x('hydrogen', 20.0, ['p'], var_cost_ns=1000.0)],
               e_kwargs={'var_cost_ns': 100.0})
    ok, s = solve(s)
    assert ok
    e = s['demand']['e']
    assert e['output_ns'] == pytest.approx([1.0, 1.0])          # all of it, and no more
    assert sum(s['p2x'][0]['x_prod']) == pytest.approx(0.0)     # nothing to power it with
    assert e['accounts']['served_demand'] == pytest.approx(0.0)
    h2 = [d for d in s['demand']['x'] if d['iden'] == 'hydrogen'][0]
    assert sum(h2['output_ns']) == pytest.approx(20.0)


def test_shortfall_is_not_chosen_over_generation_as_a_power_source(horizon):
    """A generator costs 500 $/MWh and a shortfall only 100 $/MWh. Shedding
    fictitious demand used to be the cheaper 'source' for the process."""
    horizon(1)
    s = system(generators=[generator('g', var=500.0)], p2xs=[p2x('p', elec_use=1.0)],
               e_total=2.0, xs=[demand_x('hydrogen', 20.0, ['p'], var_cost_ns=1000.0)],
               e_kwargs={'var_cost_ns': 100.0})
    ok, s = solve(s)
    assert ok
    e = s['demand']['e']
    g = s['generator'][0]['e_prod'][0]
    x = s['p2x'][0]['x_prod'][0]
    assert e['output_ns'][0] <= 2.0 + TOL
    # physical supply covers the process, whatever the dispatch
    assert g + TOL >= x * 1.0
    # 20 units at 500 + 2 MWh shed at 100 = 10200 beats 20000 of product penalty
    assert x == pytest.approx(20.0)
    assert g == pytest.approx(20.0)
    assert e['output_ns'][0] == pytest.approx(2.0)


def test_lower_bound_above_hourly_demand_is_refused(horizon, monkeypatch, capsys):
    """2 units over two hours with l_ns = [2, 10]: at least 2 unmet each hour
    against 1 demanded. The old code reported 4 unmet and -2 served."""
    horizon(2)
    s = system(generators=[generator('g', var=1.0)], p2xs=[p2x('p', elec_use=1.0)],
               e_total=1.0, xs=[demand_x('water', 2.0, ['p'], l_ns=(2, 10))])
    out = refused(monkeypatch, capsys, s)
    assert 'water' in out and 'l_ns' in out and 'hour 0' in out


def test_electricity_lower_bound_above_demand_is_refused(horizon, monkeypatch, capsys):
    horizon(3)
    s = system(generators=[generator('g', var=1.0)], e_total=3.0,
               e_kwargs={'l_ns': (1.5, 10)})
    out = refused(monkeypatch, capsys, s)
    assert 'demand.e' in out and 'l_ns' in out and 'hour 0' in out


@pytest.mark.parametrize('which', ['e', 'x'])
def test_zero_penalty_is_valid_but_bounded(horizon, which):
    """A zero penalty makes unmet demand free. It must still not exceed demand."""
    horizon(2)
    if which == 'e':
        s = system(generators=[generator('g', var=1.0)], e_total=2.0,
                   e_kwargs={'var_cost_ns': 0.0, 'l_ns': (0, 10)})
        ok, s = solve(s)
        d = s['demand']['e']
    else:
        s = system(generators=[generator('g', var=1.0)], p2xs=[p2x('p', elec_use=1.0)],
                   e_total=2.0, xs=[demand_x('water', 2.0, ['p'], var_cost_ns=0.0, l_ns=(0, 10))])
        ok, s = solve(s)
        d = [x for x in s['demand']['x'] if x['iden'] == 'water'][0]
    assert ok
    assert all(-TOL <= v <= 1.0 + TOL for v in d['output_ns'])
    assert d['accounts']['served_demand'] >= -TOL
    assert 0.0 <= d['kpis']['reli'] <= 1.0


@pytest.mark.parametrize('which', ['e', 'x'])
def test_negative_penalty_is_refused(horizon, monkeypatch, capsys, which):
    horizon(2)
    if which == 'e':
        s = system(generators=[generator('g', var=1.0)], e_total=2.0,
                   e_kwargs={'var_cost_ns': -1.0})
    else:
        s = system(generators=[generator('g', var=1.0)], p2xs=[p2x('p', elec_use=1.0)],
                   e_total=2.0, xs=[demand_x('water', 2.0, ['p'], var_cost_ns=-1.0)])
    out = refused(monkeypatch, capsys, s)
    assert 'var_cost_ns' in out


def test_zero_demand_hours_admit_no_shortfall(horizon):
    """Where nothing is demanded nothing can be unmet, whatever l_ns says."""
    horizon(4)
    s = system(e_total=2.0, e_kwargs={'profile': [0.0, 1.0, 0.0, 1.0], 'l_ns': (0, 1e9)})
    ok, s = solve(s)
    assert ok
    assert s['demand']['e']['output_ns'] == pytest.approx([0.0, 1.0, 0.0, 1.0])
    assert s['demand']['e']['kpis']['reli'] == pytest.approx(0.0)


def test_lower_bound_in_a_zero_demand_hour_is_refused(horizon, monkeypatch, capsys):
    horizon(4)
    s = system(generators=[generator('g', var=1.0)], e_total=2.0,
               e_kwargs={'profile': [1.0, 0.0, 1.0, 1.0], 'l_ns': (0.1, 10)})
    out = refused(monkeypatch, capsys, s)
    assert 'hour 1' in out


def test_a_valid_lower_bound_is_respected(horizon):
    """l_ns = [0.25, 10] with 1 per hour demanded: at least 0.25 unmet each hour,
    although generation is cheap."""
    hours = horizon(4)
    s = system(generators=[generator('g', var=1.0)], e_total=float(hours),
               e_kwargs={'l_ns': (0.25, 10), 'var_cost_ns': 1000.0})
    ok, s = solve(s)
    assert ok
    e = s['demand']['e']
    assert e['output_ns'] == pytest.approx([0.25] * hours)
    assert e['accounts']['served_demand'] == pytest.approx(0.75 * hours)
    assert e['kpis']['reli'] == pytest.approx(0.75)


@pytest.mark.parametrize('l_ns, why', [
    ((-1, 10), 'negative'),
    ((5, 1), 'exceeds'),
    ((0,), 'two'),
    ((0, float('nan')), 'finite'),
])
def test_malformed_shortfall_bounds_are_refused(horizon, monkeypatch, capsys, l_ns, why):
    horizon(2)
    s = system(generators=[generator('g', var=1.0)], e_total=2.0, e_kwargs={'l_ns': l_ns})
    out = refused(monkeypatch, capsys, s)
    assert 'l_ns' in out and why in out


# --- product supply is delivered once ----------------------------------------

def test_one_process_cannot_serve_two_demands(horizon, monkeypatch, capsys):
    """x_supp entered every balance naming the process, so 2 units produced
    satisfied two demands of 2 units each, and the shares summed above one."""
    horizon(1)
    s = system(generators=[generator('g', var=1.0)], p2xs=[p2x('p', elec_use=1.0)],
               e_total=1.0,
               xs=[demand_x('water', 2.0, ['p']), demand_x('hydrogen', 2.0, ['p'])])
    out = refused(monkeypatch, capsys, s)
    assert "'p'" in out and 'water' in out and 'hydrogen' in out


def test_duplicate_demand_identifiers_are_refused(horizon, monkeypatch, capsys):
    """Allocation quantities were keyed by identifier, so the second entry
    overwrote the first and the shares summed to 1.33."""
    horizon(1)
    s = system(generators=[generator('g', var=1.0)],
               p2xs=[p2x('p1', elec_use=1.0), p2x('p2', elec_use=1.0)], e_total=2.0,
               xs=[demand_x('water', 1.0, ['p1']), demand_x('water', 3.0, ['p2'])])
    out = refused(monkeypatch, capsys, s)
    assert 'duplicate demand identifier' in out and 'water' in out


def test_independent_product_groups_are_supported(horizon):
    horizon(1)
    s = system(generators=[generator('g', var=1.0)],
               p2xs=[p2x('p1', elec_use=1.0), p2x('p2', elec_use=2.0)], e_total=2.0,
               xs=[demand_x('water', 1.0, ['p1']), demand_x('hydrogen', 3.0, ['p2'])])
    ok, s = solve(s)
    assert ok
    shares = {d['iden']: d['accounts']['allocation_share']
              for d in [s['demand']['e']] + s['demand']['x'] if 'accounts' in d}
    # 2 MWh electricity, 1 MWh into water, 6 MWh into hydrogen: 9 MWh in all
    assert shares == pytest.approx({'electricity': 2 / 9, 'water': 1 / 9, 'hydrogen': 6 / 9})


def test_several_processes_may_supply_one_demand(horizon):
    horizon(2)
    s = system(generators=[generator('g', var=1.0)],
               p2xs=[p2x('p1', elec_use=1.0, l_prod=(0, 1), fix_prod=1.0),
                     p2x('p2', elec_use=2.0, fix_prod=1.0)],
               e_total=2.0, xs=[demand_x('water', 4.0, ['p1', 'p2'])])
    ok, s = solve(s)
    assert ok
    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    assert sum(water['output_ns']) == pytest.approx(0.0)
    supplied = sum(sum(p['x_supp']) for p in s['p2x'])
    assert supplied == pytest.approx(4.0)


def test_an_inactive_reference_does_not_affect_accounting(horizon):
    """A demand with total 0 may name a process that an active demand also
    names; it builds no balance and receives no share."""
    horizon(1)
    s = system(generators=[generator('g', var=1.0)], p2xs=[p2x('p', elec_use=1.0)],
               e_total=1.0,
               xs=[demand_x('hydrogen', 0.0, ['p']), demand_x('water', 3.0, ['p'])])
    ok, s = solve(s)
    assert ok
    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    assert water['accounts']['allocation_share'] == pytest.approx(0.75)
    assert s['system']['allocated_share_total'] == pytest.approx(1.0)
