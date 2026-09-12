"""Configurations the formulation cannot represent are refused, not solved."""

import pytest

from ieso_modules import fcn as u
from conftest import demand_x, flex, generator, p2x, solve, system


@pytest.fixture(autouse=True)
def fixed_thermo(monkeypatch):
    monkeypatch.setattr(u, 'thermo', lambda *args: (0.25, 1.5, False))


def chp(iden):
    return generator(iden, var=10.0, kind='elec + ther', turbine=(564, 152), cond=0.05)


def med(iden, sources, temperature=80):
    return p2x(iden, elec_use=0.001, ther_use=0.05, kind='elec + ther',
               sources=sources, temperature=temperature)


def test_one_process_may_draw_on_several_generators(horizon):
    """The bundled MED case: three eligible suppliers, one consumer."""
    hours = horizon(24)
    s = system(generators=[chp('a'), chp('b'), chp('c')],
               p2xs=[med('med', ('a', 'b', 'c'))],
               e_total=100.0 * hours,
               xs=[demand_x('water', 50.0 * hours, ['med'])])
    ok, _ = solve(s)
    assert ok


def test_independent_thermal_groups_are_supported(horizon):
    hours = horizon(24)
    s = system(generators=[chp('a'), chp('b')],
               p2xs=[med('med1', ('a',)), med('med2', ('b',))],
               e_total=100.0 * hours,
               xs=[demand_x('water', 50.0 * hours, ['med1', 'med2'])])
    ok, _ = solve(s)
    assert ok


def test_heat_shared_between_two_processes_is_refused(horizon, monkeypatch, capsys):
    """Each process carries its own balance against the same h_prod variables,
    so one generator's heat would satisfy both and be spent twice."""
    hours = horizon(24)
    monkeypatch.setattr(u, 'Verbose', True)
    s = system(generators=[chp('a')],
               p2xs=[med('med1', ('a',)), med('med2', ('a',))],
               e_total=100.0 * hours,
               xs=[demand_x('water', 50.0 * hours, ['med1', 'med2'])])
    with pytest.raises(SystemExit):
        solve(s)
    out = capsys.readouterr().out
    assert 'heat is shared between processes' in out
    assert 'med1' in out and 'med2' in out


def test_processes_at_different_temperatures_cannot_share_a_generator(horizon):
    """Coefficients come from whichever process is seen first, so the second
    would silently inherit the first one's extraction conditions."""
    hours = horizon(24)
    s = system(generators=[chp('a')],
               p2xs=[med('low', ('a',), temperature=80),
                     med('high', ('a',), temperature=250)],
               e_total=100.0 * hours,
               xs=[demand_x('water', 50.0 * hours, ['low', 'high'])])
    with pytest.raises(SystemExit):
        solve(s)


@pytest.mark.parametrize('mutate, reason', [
    (lambda s: s['p2x'][0].update(supply_sources=[]), 'at least one heat supply source'),
    (lambda s: s['p2x'][0].update(supply_sources=['ghost']), 'unknown heat supply source'),
    (lambda s: s['generator'].append(generator('plain', var=1.0)) or
               s['p2x'][0].update(supply_sources=['plain']), 'not a cogeneration unit'),
    (lambda s: s['generator'][0].update(turbine_t_p=[]), 'turbine_t_p'),
])
def test_invalid_heat_supply_is_refused(horizon, monkeypatch, capsys, mutate, reason):
    hours = horizon(24)
    monkeypatch.setattr(u, 'Verbose', True)
    s = system(generators=[chp('a')], p2xs=[med('med', ('a',))],
               e_total=100.0 * hours,
               xs=[demand_x('water', 50.0 * hours, ['med'])])
    mutate(s)
    with pytest.raises(SystemExit):
        solve(s)
    assert reason in capsys.readouterr().out


def test_demand_naming_an_unknown_process_is_refused(horizon, monkeypatch, capsys):
    hours = horizon(24)
    monkeypatch.setattr(u, 'Verbose', True)
    s = system(generators=[generator('gas', var=10.0)],
               p2xs=[p2x('ro', elec_use=0.0045)],
               e_total=100.0 * hours,
               xs=[demand_x('water', 50.0 * hours, ['desal'])])
    with pytest.raises(SystemExit):
        solve(s)
    assert 'unknown supply source' in capsys.readouterr().out


def test_duplicate_identifiers_are_refused(horizon, monkeypatch, capsys):
    hours = horizon(24)
    monkeypatch.setattr(u, 'Verbose', True)
    s = system(generators=[generator('gas', var=10.0), generator('gas', var=20.0)],
               e_total=100.0 * hours)
    with pytest.raises(SystemExit):
        solve(s)
    assert 'duplicate generator identifier' in capsys.readouterr().out
