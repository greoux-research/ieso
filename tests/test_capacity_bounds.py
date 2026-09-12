"""Capacity bounds govern what is built, not how it is operated.

l_prod and l_strg bound installed capacity. They were also applied to the
hourly variables, so a minimum capacity became a minimum output, inventory,
charge and discharge in every hour, an energy bound was applied to power
variables, and product delivery inherited the production plant's bound.
"""

import numpy as np
import pytest

from ieso_modules import fcn as u
from conftest import demand_x, flex, generator, p2x, solve, system


def test_minimum_capacity_does_not_force_output(horizon):
    hours = horizon(24)
    s = system(
        generators=[
            generator('must_build', fix=1.0, var=1000.0, l_prod=(50, 100)),
            generator('cheap', fix=1.0, var=1.0),
        ],
        e_total=10.0 * hours)
    ok, s = solve(s)
    assert ok

    built = [g for g in s['generator'] if g['iden'] == 'must_build'][0]
    assert built['c_prod'] >= 50.0                      # the minimum is still installed
    assert sum(built['e_prod']) == pytest.approx(0.0)   # but it need not run


def test_minimum_storage_capacity_does_not_force_inventory_or_cycling(horizon):
    hours = horizon(24)
    s = system(
        generators=[generator('cheap', fix=1.0, var=1.0)],
        flexes=[flex('bstr', fix=1.0, l_strg=(10, 100), soc_ini=0.0)],
        e_total=10.0 * hours)
    ok, s = solve(s)
    assert ok

    f = s['flex'][0]
    assert f['c_strg'] >= 10.0
    assert sum(f['e_char']) == pytest.approx(0.0)
    assert sum(f['e_disc']) == pytest.approx(0.0)
    assert min(f['e_strg']) == pytest.approx(0.0)       # the store may sit empty


def test_charge_and_discharge_are_limited_by_duration_not_energy_bounds(horizon):
    """Power is bounded by c_strg / hours_of_storage, an MW quantity."""
    hours = horizon(24)
    shape = [1.0] * 12 + [0.0] * 12          # surplus first: the store begins empty
    s = system(
        generators=[generator('solar', fix=1.0, var=0.0, profile=shape, cf=0.5),
                    generator('peaker', fix=1.0, var=500.0)],
        flexes=[flex('bstr', fix=1.0, hours=4, l_strg=(0, 1e6), soc_ini=0.0)],
        e_total=100.0 * hours)
    ok, s = solve(s)
    assert ok

    f = s['flex'][0]
    limit = f['c_strg'] / 4
    assert max(f['e_char']) <= limit + 1e-6
    assert max(f['e_disc']) <= limit + 1e-6
    assert max(f['e_disc']) > 0


def test_delivery_may_exceed_the_production_rate_from_storage(horizon):
    """A store exists so delivery need not track production."""
    hours = horizon(24)
    spike = [0.0] * (hours - 1) + [1.0]
    s = system(
        generators=[generator('cheap', fix=1.0, var=1.0)],
        p2xs=[p2x('ro', elec_use=0.001, fix_prod=1.0, fix_strg=0.01,
                  l_prod=(0, 15), l_strg=(0, 1e6), soc_ini=0.0)],
        e_total=10.0 * hours,
        xs=[demand_x('water', 240.0, ['ro'], profile=spike)])
    ok, s = solve(s)
    assert ok

    ro = s['p2x'][0]
    water = [d for d in s['demand']['x'] if d['iden'] == 'water'][0]
    assert sum(water['output_ns']) == pytest.approx(0.0)     # fully served
    assert ro['c_prod'] <= 15.0 + 1e-9                       # capacity honours its bound
    assert max(ro['x_supp']) == pytest.approx(240.0)         # delivery far exceeds it
    assert max(ro['x_supp']) > ro['c_prod']


def test_output_is_held_to_nameplate_when_the_profile_exceeds_one(horizon):
    """capacity_factor above the profile's own mean/max scales it past one."""
    hours = horizon(24)
    shape = [1.0] * 12 + [0.5] * 12                   # mean/max = 0.75
    assert max(u.cf_h(shape, 0.9)) == pytest.approx(1.2)

    s = system(generators=[generator('vre', fix=1.0, var=0.0, profile=shape,
                                     cf=0.9, c_prod=100)],
               e_total=1000.0 * hours)
    ok, s = solve(s)
    assert ok

    g = s['generator'][0]
    assert max(g['e_prod']) == pytest.approx(100.0)   # not 120
    assert max(g['e_prod']) <= g['c_prod'] + 1e-9


def test_cogeneration_nameplate_uses_the_electrical_capacity(horizon, monkeypatch):
    """e + a*h <= c_prod and h <= b*c_prod. Never h <= c_prod: b exceeds one."""
    hours = horizon(24)
    a, b = 0.25, 1.5
    monkeypatch.setattr(u, 'thermo', lambda *args: (a, b, False))

    shape = [1.0] * 12 + [0.5] * 12
    s = system(
        generators=[generator('chp', fix=1.0, var=1.0, kind='elec + ther',
                              profile=shape, cf=0.9, c_prod=100,
                              turbine=(564, 152), cond=0.05)],
        p2xs=[p2x('med', elec_use=0.001, ther_use=1.0, kind='elec + ther',
                  sources=('chp',), temperature=80, fix_prod=1.0, fix_strg=0.01)],
        e_total=10.0 * hours,
        xs=[demand_x('water', 3000.0, ['med'])])
    ok, s = solve(s)
    assert ok

    g = s['generator'][0]
    for e, h in zip(g['e_prod'], g['h_prod']):
        assert e + a * h <= g['c_prod'] + 1e-6
        assert h <= b * g['c_prod'] + 1e-6
    assert max(g['h_prod']) > g['c_prod']             # heat legitimately exceeds it
