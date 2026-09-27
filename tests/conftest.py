"""Fixtures for the IESO regression tests.

The production model is an 8760-hour model. These tests shorten the horizon
so that each case can be checked by hand. The horizon is passed to each solve
as per-run configuration (RunConfig.hours) through the public API -- the same
path the command line takes -- so nothing global is patched and no part of the
model is restructured for the sake of testing.
"""

import os
import sys

import pytest


from ieso import api
from ieso import fcn as u
from ieso.errors import IesoError

# The horizon of the test in progress: this harness's own state, reset by the
# fixture below after every test. solve() passes it to the model per run.
HOURS = u.HOURS_PER_YEAR


@pytest.fixture
def horizon(monkeypatch):
    """Shorten the year for this test's solves. Returns a setter so a test can
    choose its own length; the setter returns the length."""

    def _set(hours):
        monkeypatch.setattr(sys.modules[__name__], 'HOURS', hours)
        return hours

    return _set


def demand_e(total, profile='', var_cost_ns=1000.0, l_ns=(0, 1e9)):
    return {
        'iden': 'electricity', 'profile': profile, 'total': total,
        'supply_sources': [], 'var_cost_ns': var_cost_ns, 'l_ns': list(l_ns),
        'output_ns': [], 'shadow_prices': {}, 'kpis': {},
    }


def demand_x(iden, total, supply_sources, profile='', var_cost_ns=1000.0, l_ns=(0, 1e9)):
    return {
        'iden': iden, 'profile': profile, 'total': total,
        'supply_sources': list(supply_sources), 'var_cost_ns': var_cost_ns,
        'l_ns': list(l_ns), 'output_ns': [], 'shadow_prices': {}, 'kpis': {},
    }


def generator(iden, fix=0.0, var=0.0, emis=0.0, cf=1.0, c_prod=-1,
              profile='', kind='elec', l_prod=(0, 1e6), turbine=(), cond=0.0):
    return {
        'iden': iden, 'profile': profile, 'capacity_factor': cf, 'type': kind,
        'fix_cost_prod': fix, 'var_cost_prod': var, 'var_emis_prod': emis,
        'l_prod': list(l_prod), 'c_prod': c_prod, 'e_prod': [], 'h_prod': [],
        'turbine_t_p': list(turbine), 'condenser_p': cond, 'a': 0, 'b': 0,
    }


def flex(iden, fix=0.0, hours=4, rte=0.85, c_strg=-1, l_strg=(0, 1e6),
         soc_ini=0.5, soc_min=0.0, soc_max=1.0, **extra):
    f = {
        'iden': iden, 'fix_cost_strg': fix, 'hours_of_storage': hours,
        'round_trip_efficiency': rte, 'l_strg': list(l_strg), 'c_strg': c_strg,
        'e_strg': [], 'soc_ini': soc_ini, 'soc_min': soc_min, 'soc_max': soc_max,
        'e_char': [], 'e_disc': [],
    }
    f.update(extra)
    return f


def p2x(iden, elec_use, fix_prod=0.0, var_prod=0.0, fix_strg=0.0, cf=1.0,
        kind='elec', ther_use=0.0, sources=(), temperature=0,
        c_prod=-1, c_strg=-1, l_prod=(0, 1e6), l_strg=(0, 1e6), soc_ini=0.5):
    return {
        'iden': iden, 'profile': '', 'capacity_factor': cf, 'type': kind,
        'temperature': temperature, 'supply_sources': list(sources),
        'fix_cost_strg': fix_strg, 'l_strg': list(l_strg), 'c_strg': c_strg,
        'x_strg': [], 'fix_cost_prod': fix_prod, 'var_cost_prod': var_prod,
        'pow_use_elec_prod': elec_use, 'pow_use_ther_prod': ther_use,
        'l_prod': list(l_prod), 'c_prod': c_prod, 'x_prod': [],
        'soc_ini': soc_ini, 'x_supp': [], 'shadow_prices': {},
    }


def system(generators=(), flexes=(), p2xs=(), e_total=0.0, xs=(), e_kwargs=None):
    xs = list(xs)
    idens = {x['iden'] for x in xs}
    for name in ('heat', 'hydrogen', 'water'):
        if name not in idens:
            xs.append(demand_x(name, 0, []))
    return {
        'demand': {'e': demand_e(e_total, **(e_kwargs or {})), 'x': xs},
        'p2x': list(p2xs), 'generator': list(generators), 'flex': list(flexes),
        'solver': {'stat_succ': -1, 'stat_time': 0, 'stat_capa': 0,
                   'stat_outp': 0, 'stat_cons': 0},
    }


def solve(s, opts=None, config=None):
    """Solve through the public API, as the command line does. Returns
    (optimal, result document); the document carries the solver objective as
    solver._objective for reconciliation tests. The input is not modified."""
    result = api.solve(s, options=opts, config=config if config is not None else u.RunConfig(hours=HOURS))
    document = result.document
    document['solver']['_objective'] = result.objective
    return result.optimal, document


def solved_document(hours=4):
    """A complete, genuinely solved result in the shape ieso.py writes.

    Every reported block is present: an electric and a cogeneration unit, an
    inflow-fed store, a thermally coupled process, both caps, provenance. Used
    by the comparator tests, which need a real result to mutate.
    """
    import json

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(u, 'thermo', lambda *args, **kwargs: (0.25, 1.5, False))
        s = system(
            generators=[generator('gas', fix=1.0, var=30.0, emis=400.0),
                        generator('chp', fix=2.0, var=20.0, emis=300.0, kind='elec + ther',
                                  turbine=(564, 152), cond=0.05),
                        generator('solr', fix=0.5, var=0.0, profile=[0.0, 1.0, 1.0, 0.2] * (hours // 4),
                                  cf=0.4)],
            flexes=[flex('dam', fix=0.1, c_strg=20, hours=4, rte=1.0, soc_ini=0.5,
                         inflow_total=8.0 * hours, inflow_profile='', charge_allowed=False),
                    flex('bstr', fix=0.2, rte=0.81, hours=2)],
            p2xs=[p2x('med', elec_use=0.01, ther_use=0.5, kind='elec + ther',
                      sources=('chp',), temperature=80, fix_prod=1.0, fix_strg=0.1)],
            e_total=20.0 * hours,
            xs=[demand_x('water', 4.0 * hours, ['med'])])
        opts = {'carbon-constraint': 250.0, 'non-served-power-constraint': 0.05}
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), 'case.json')
        with open(path, 'w') as f:
            json.dump(s, f)
        result = api.solve(s, options=opts, config=u.RunConfig(hours=hours), source=path)
        assert result.optimal
        s = result.document
        s['solver']['stat_time'] = 0.1
    return json.loads(json.dumps(s))


def refused(monkeypatch, capsys, s, opts=None):
    """Solve a configuration that must be refused; return the refusal's text.

    Refusals are exceptions (InputError, ThermoError), never an exit, so the
    caller keeps running. monkeypatch and capsys are accepted for the existing
    call sites and unused."""
    with pytest.raises(IesoError) as info:
        solve(s, opts)
    return str(info.value)


@pytest.fixture
def fixed_thermo(monkeypatch):
    """Pin the cogeneration coefficients so a test does not depend on sim.bin."""
    monkeypatch.setattr(u, 'thermo', lambda *args, **kwargs: (0.25, 1.5, False))
    return 0.25, 1.5


@pytest.fixture(scope='session')
def sim_bin(tmp_path_factory):
    """The thermodynamics executable, compiled from the sources under test.

    Built fresh so the tests exercise the current C++ rather than whatever
    binary happens to be lying in thermo/. Skips only when no C++ compiler is
    available, and says so.
    """
    import shutil
    import subprocess

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compiler = shutil.which('g++') or shutil.which('c++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('no C++ compiler: thermodynamics integration tests not run')
    out = tmp_path_factory.mktemp('thermo') / 'sim.bin'
    sources = [os.path.join(root, 'thermo', n) for n in ('iesoH2O.cpp', 'Cogen.cpp', 'sim.cpp')]
    build = subprocess.run([compiler, '-O2', '-o', str(out)] + sources + ['-lm'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert build.returncode == 0, build.stdout
    return str(out)
