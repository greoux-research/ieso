"""Fixtures for the IESO regression tests.

The production model is an 8760-hour model. These tests shorten the horizon by
patching ``fcn.Y2H`` so that each case can be checked by hand, and drive the
same sequence of module calls that ``ieso.py`` performs, so no part of the
model is restructured for the sake of testing.
"""

import os
import sys

import pytest
from ortools.linear_solver import pywraplp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ieso_modules import chk, eqs_dmd_e, eqs_dmd_x, eqs_flx, eqs_gen, eqs_p2x_1, eqs_p2x_2
from ieso_modules import fcn as u
from ieso_modules import obj, opt, pos


@pytest.fixture
def horizon(monkeypatch):
    """Shorten the year. Returns a setter so a test can choose its own length."""

    def _set(hours):
        monkeypatch.setattr(u, 'Y2H', hours)
        return hours

    return _set


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(u, 'Verbose', False)


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


def solve(s, opts=None):
    """Build and solve exactly as ieso.py does. Returns (success, s)."""
    opts = dict(opts or {})
    stat = {'time': 0, 'capa': 0, 'outp': 0, 'cons': 0}
    glop = pywraplp.Solver.CreateSolver('GLOP')
    objective = glop.Objective()
    objective.SetMinimization()

    chk.define(glop, s, opts, stat)
    eqs_p2x_1.define(glop, s, opts, stat)
    eqs_gen.define(glop, s, opts, stat)
    eqs_p2x_2.define(glop, s, opts, stat)
    eqs_flx.define(glop, s, opts, stat)
    emis_con, nspo_con = eqs_dmd_e.define(glop, s, opts, stat)
    eqs_dmd_x.define(glop, s, opts, stat)
    obj.define(objective, s)

    success = opt.run(glop, s, opts, stat)
    if success:
        pos.process(glop, s, opts, stat, emis_con, nspo_con)
    s['solver']['stat_succ'] = 1 if success else 0
    s['solver']['_objective'] = objective.Value() if success else None
    return success, s
