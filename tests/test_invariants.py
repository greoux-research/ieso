"""Invariants on generated systems.

Small systems are generated from recorded seeds -- random costs, emission
factors (negative included), profiles with zero hours, fixed and optimised
capacities, batteries, inflow-fed stores, electric and thermally coupled
processes, shortfall lower bounds, carbon and reliability caps -- and every
solution is checked against invariants recomputed here from the input and the
reported series alone. Nothing below calls the post-processing code under test
to obtain an expected value.

The checks do not assert a particular dispatch: several optima may exist. They
assert what every optimum must satisfy.
"""

import copy
import json
import math
import os
import subprocess
import sys

import numpy as np
import pytest

from ies_optimiser import fcn as u
from conftest import demand_x, flex, generator, p2x, solve, system

SEEDS = list(range(24))           # recorded: each seed reproduces its case exactly
HOURS = 24
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def shape(rng, hours, zeros=False):
    p = rng.uniform(0.05, 1.0, hours)
    if zeros:
        p[rng.rand(hours) < 0.25] = 0.0
        p[0] = max(p[0], 0.5)         # never all zero
    return p.tolist()


def make_case(seed, hours=HOURS):
    """A feasible system: a zero-emission backstop with ample capacity keeps any
    carbon or reliability cap satisfiable."""
    rng = np.random.RandomState(seed)
    gens = [generator('backstop', fix=1.0, var=300.0, emis=0.0, l_prod=(0, 1e4))]
    for k in range(rng.randint(1, 4)):
        fixed = rng.rand() < 0.3
        gens.append(generator(
            f'g{k}', fix=float(rng.uniform(0, 40)),
            var=float(0.0 if rng.rand() < 0.3 else rng.uniform(-5, 120)),
            emis=float(rng.uniform(-300, 900)),
            cf=float(rng.uniform(0.2, 1.0)),
            profile=shape(rng, hours, zeros=rng.rand() < 0.3) if rng.rand() < 0.6 else '',
            c_prod=float(rng.uniform(0, 40)) if fixed else -1,
            l_prod=(0, float(rng.uniform(20, 200)))))
    flexes = []
    if rng.rand() < 0.7:
        lo = float(rng.uniform(0, 0.3))
        hi = float(rng.uniform(0.7, 1.0))
        flexes.append(flex('bat', fix=float(rng.uniform(0, 5)), hours=float(rng.randint(1, 7)),
                           rte=float(rng.uniform(0.5, 1.0)), soc_min=lo, soc_max=hi,
                           soc_ini=float(rng.uniform(lo, hi))))
    if rng.rand() < 0.4:
        flexes.append(flex('dam', fix=0.0, c_strg=float(rng.uniform(5, 50)),
                           hours=float(rng.uniform(2, 20)), rte=1.0, soc_ini=0.5,
                           inflow_total=float(rng.uniform(5, 200)),
                           inflow_profile=shape(rng, hours), charge_allowed=False))
    p2xs, xs = [], []
    thermal = rng.rand() < 0.5
    if rng.rand() < 0.6:
        p2xs.append(p2x('ro', elec_use=float(rng.uniform(0.01, 1.0)), fix_prod=float(rng.uniform(0, 5)),
                        var_prod=float(rng.uniform(-1, 3)), fix_strg=float(rng.uniform(0, 0.5)),
                        cf=float(rng.uniform(0.5, 1.0)), soc_ini=float(rng.uniform(0, 1))))
        total = float(rng.uniform(5, 60))
        prof = shape(rng, hours)
        dm_min = min(np.array(prof) / sum(prof) * total)
        xs.append(demand_x('water', total, ['ro'], profile=prof,
                           var_cost_ns=float(rng.choice([0.0, rng.uniform(10, 2000)])),
                           l_ns=(float(rng.uniform(0, 0.3) * dm_min), 1e9)))
    if thermal:
        gens.append(generator('chp', fix=float(rng.uniform(1, 30)), var=float(rng.uniform(-2, 60)),
                              emis=float(rng.uniform(0, 500)), kind='elec + ther',
                              turbine=(564, 152), cond=0.05, l_prod=(0, 100)))
        p2xs.append(p2x('med', elec_use=float(rng.uniform(0.001, 0.05)),
                        ther_use=float(rng.uniform(0.1, 1.0)), kind='elec + ther',
                        sources=('chp',), temperature=80, fix_prod=float(rng.uniform(0, 3)),
                        fix_strg=float(rng.uniform(0, 0.2)), soc_ini=1.0))
        xs.append(demand_x('heat', float(rng.uniform(5, 40)), ['med'],
                           var_cost_ns=float(rng.uniform(50, 1500))))
    e_prof = shape(rng, hours, zeros=rng.rand() < 0.3)
    e_total = float(rng.uniform(50, 400))
    e_lb = 0.0 if min(e_prof) == 0 else float(rng.uniform(0, 0.2)) * min(e_prof) / sum(e_prof) * e_total
    s = system(generators=gens, flexes=flexes, p2xs=p2xs, e_total=e_total, xs=xs,
               e_kwargs={'profile': e_prof, 'var_cost_ns': float(rng.choice([0.0, rng.uniform(50, 3000)])),
                         'l_ns': (e_lb, 1e9)})
    opts = {}
    if rng.rand() < 0.5:
        opts['carbon-constraint'] = float(rng.uniform(-100, 300))
        if opts['carbon-constraint'] < 0:
            # a net-negative target needs a removal technology to be feasible
            s['generator'].append(generator('removal', fix=1.0, var=200.0, emis=-600.0, l_prod=(0, 1e4)))
    if rng.rand() < 0.5:
        opts['non-served-power-constraint'] = float(rng.uniform(0, 0.3))
    a = float(rng.uniform(0.05, 0.5))
    b = float(rng.uniform(0.5, min(2.0, 0.95 / a)))          # admissible: a * b < 1
    return s, opts, (a, b)


# --- independent reconstructions ------------------------------------------------

def demand_series(d, hours):
    total = d['total']
    p = d['profile']
    if isinstance(p, str) and p == '':
        return np.full(hours, total / hours)
    p = np.asarray(p, float)
    return total * p / p.sum()


def availability_series(item, hours):
    p = item['profile']
    cf = item['capacity_factor']
    if isinstance(p, str) and p == '':
        return np.full(hours, cf)
    p = np.asarray(p, float)
    n = p / p.max()
    return n * cf / n.mean()


def verify(spec, s, opts, coeffs):
    H = len(s['demand']['e']['output_ns'])
    tol = lambda scale: 1e-6 + 1e-7 * max(1.0, scale)
    doc = json.dumps(s, allow_nan=False)            # no NaN or infinity anywhere
    assert doc

    gens = {g['iden']: g for g in s['generator']}
    specs = {g['iden']: g for g in spec['generator']}
    arr = lambda xs: np.asarray(xs, float)

    # --- generators: capacity bounds, availability, nameplate, cogeneration
    for name, g in gens.items():
        sp = specs[name]
        c = g['c_prod']
        if sp['c_prod'] == -1:
            assert sp['l_prod'][0] - 1e-9 <= c <= sp['l_prod'][1] + 1e-9
        else:
            assert c == sp['c_prod']
        cf = availability_series(sp, H)
        e = arr(g['e_prod'])
        assert np.all(e >= -tol(c))
        if g['type'] == 'elec + ther':
            a, b = coeffs
            h = arr(g['h_prod'])
            assert (g['a'], g['b']) == pytest.approx((a, b))
            assert np.all(h >= -tol(c))
            assert np.all(e + a * h <= cf * c + tol(c))
            assert np.all(h <= b * cf * c + tol(c))
            assert np.all(e + a * h <= c + tol(c))
            assert np.all(h <= b * c + tol(c))
        else:
            assert np.all(e <= cf * c + tol(c))
            assert np.all(e <= c + tol(c))

    # --- storage: bounds, duration limit, transitions, closure
    inflow_total = 0.0
    for f, fs in zip(s['flex'], spec['flex']):
        c = f['c_strg']
        if fs['c_strg'] == -1:
            assert fs['l_strg'][0] - 1e-9 <= c <= fs['l_strg'][1] + 1e-9
        ch, dc, st = arr(f['e_char']), arr(f['e_disc']), arr(f['e_strg'])
        r = math.sqrt(fs['round_trip_efficiency'])
        infl = demand_series({'total': fs.get('inflow_total', 0.0), 'profile': fs.get('inflow_profile', '')}, H) \
            if fs.get('inflow_total', 0) > 0 else np.zeros(H)
        spil = arr(f['e_spil']) if fs.get('inflow_total', 0) > 0 else np.zeros(H)
        inflow_total += infl.sum()
        assert np.all(ch >= -tol(c)) and np.all(dc >= -tol(c)) and np.all(spil >= -tol(c))
        assert np.all(ch <= c / fs['hours_of_storage'] + tol(c))
        assert np.all(dc <= c / fs['hours_of_storage'] + tol(c))
        if not fs.get('charge_allowed', True):
            assert np.all(np.abs(ch) <= tol(c))
        assert np.all(st >= fs['soc_min'] * c - tol(c)) and np.all(st <= fs['soc_max'] * c + tol(c))
        prev = np.concatenate([[fs['soc_ini'] * c], st[:-1]])
        assert np.abs(st - (prev + infl - spil + r * ch - dc / r)).max() <= tol(max(c, infl.max()))
        assert abs(st[-1] - fs['soc_ini'] * c) <= tol(c)

    # --- processes: availability, inventory transitions and closure
    for p, ps in zip(s['p2x'], spec['p2x']):
        c, cs = p['c_prod'], p['c_strg']
        xp, xs_, xst = arr(p['x_prod']), arr(p['x_supp']), arr(p['x_strg'])
        assert np.all(xp >= -tol(c)) and np.all(xs_ >= -tol(c)) and np.all(xst >= -tol(cs))
        assert np.all(xp <= availability_series(ps, H) * c + tol(c))
        assert np.all(xst <= cs + tol(cs))
        prev = np.concatenate([[ps['soc_ini'] * cs], xst[:-1]])
        assert np.abs(xst - (prev + xp - xs_)).max() <= tol(max(cs, xs_.max()))
        assert abs(xst[-1] - ps['soc_ini'] * cs) <= tol(cs)

    # --- electricity: shortfall bounds, balance, reported surplus
    e, es = s['demand']['e'], spec['demand']['e']
    dm = demand_series(es, H)
    ns = arr(e['output_ns'])
    assert np.all(ns >= es['l_ns'][0] - tol(dm.max()))
    assert np.all(ns <= dm + tol(dm.max()))
    gen = np.sum([arr(g['e_prod']) for g in s['generator']], axis=0)
    net = np.sum([arr(f['e_disc']) - arr(f['e_char']) for f in s['flex']], axis=0) if s['flex'] else 0
    use = np.sum([p['pow_use_elec_prod'] * arr(p['x_prod']) for p in s['p2x']], axis=0) if s['p2x'] else 0
    S_e = gen + net - use + ns - dm
    assert S_e.min() >= -tol(max(dm.max(), gen.max()))
    assert arr(e['surplus']) == pytest.approx(S_e, abs=tol(dm.max()))
    assert e['kpis']['reli'] == pytest.approx(1 - ns.sum() / es['total'])

    # the marginal cost of demand departs from the balance-row dual only where the
    # shortfall sits at a bound that demand itself sets, and only downwards
    match = arr(e['shadow_prices']['demand_match'])
    marginal = arr(e['shadow_prices']['demand_marginal'])
    free = (ns < dm - tol(dm.max())) | (dm >= es['l_ns'][1])
    assert marginal[free] == pytest.approx(match[free], abs=1e-6)
    assert np.all(marginal <= match + 1e-6)

    # --- heat balance
    for p in s['p2x']:
        if p['type'] == 'elec + ther':
            h = np.sum([arr(gens[g]['h_prod']) for g in p['supply_sources']], axis=0)
            S_h = h - p['pow_use_ther_prod'] * arr(p['x_prod'])
            assert S_h.min() >= -tol(h.max())
            assert arr(p['heat_surplus']) == pytest.approx(S_h, abs=tol(h.max()))

    # --- products
    procs = {p['iden']: p for p in s['p2x']}
    for d, ds in zip(s['demand']['x'], spec['demand']['x']):
        if d['total'] <= 0:
            continue
        dmx = demand_series(ds, H)
        nsx = arr(d['output_ns'])
        assert np.all(nsx >= ds['l_ns'][0] - tol(dmx.max()))
        assert np.all(nsx <= dmx + tol(dmx.max()))
        sup = np.sum([arr(procs[n]['x_supp']) for n in d['supply_sources']], axis=0)
        S_x = sup + nsx - dmx
        assert S_x.min() >= -tol(dmx.max())
        assert arr(d['surplus']) == pytest.approx(S_x, abs=tol(dmx.max()))
        assert d['kpis']['reli'] == pytest.approx(1 - nsx.sum() / ds['total'])

    # --- caps
    emis = sum(g['var_emis_prod'] * (arr(g['e_prod']).sum()
                                     + (g['a'] * arr(g['h_prod']).sum() if g['type'] == 'elec + ther' else 0))
               for g in s['generator'])
    if 'carbon-constraint' in opts:
        cap = opts['carbon-constraint'] * es['total']
        assert emis <= cap + tol(max(abs(cap), abs(emis)))
    if 'non-served-power-constraint' in opts:
        assert ns.sum() <= opts['non-served-power-constraint'] * es['total'] + tol(es['total'])

    # --- cost, emissions and their reconciliation
    cost = 0.0
    fixed = 0.0
    for g, gs in zip(s['generator'], spec['generator']):
        cost += g['c_prod'] * g['fix_cost_prod'] + g['var_cost_prod'] * arr(g['e_prod']).sum()
        if g['type'] == 'elec + ther':
            cost += g['var_cost_prod'] * g['a'] * arr(g['h_prod']).sum()
        fixed += 0 if gs['c_prod'] == -1 else g['c_prod'] * g['fix_cost_prod']
    for f, fs in zip(s['flex'], spec['flex']):
        cost += f['c_strg'] * f['fix_cost_strg']
        fixed += 0 if fs['c_strg'] == -1 else f['c_strg'] * f['fix_cost_strg']
    for p, ps in zip(s['p2x'], spec['p2x']):
        cost += p['c_prod'] * p['fix_cost_prod'] + p['c_strg'] * p['fix_cost_strg'] \
            + p['var_cost_prod'] * arr(p['x_prod']).sum()
        fixed += (0 if ps['c_prod'] == -1 else p['c_prod'] * p['fix_cost_prod']) \
            + (0 if ps['c_strg'] == -1 else p['c_strg'] * p['fix_cost_strg'])
    sy = s['system']
    rel = 1e-9
    assert sy['cost'] == pytest.approx(cost, rel=rel, abs=1e-6)
    assert sy['emis'] == pytest.approx(emis, rel=rel, abs=1e-6)
    penalties = e['var_cost_ns'] * ns.sum() + sum(
        d['var_cost_ns'] * arr(d['output_ns']).sum() for d in s['demand']['x'] if d['total'] > 0)
    assert cost + penalties == pytest.approx(s['solver']['_objective'] + fixed, rel=1e-8, abs=1e-6)
    assert sy['allocated']['cost'] + sy['unallocated']['cost'] == pytest.approx(cost, rel=rel, abs=1e-6)
    assert sy['allocated']['emis'] + sy['unallocated']['emis'] == pytest.approx(emis, rel=rel, abs=1e-6)

    # --- allocation, recomputed under the documented convention
    out = gen.sum() + (net.sum() if s['flex'] else 0) + sum(
        g['a'] * arr(g['h_prod']).sum() for g in s['generator'] if g['type'] == 'elec + ther')
    assert sy['output'] == pytest.approx(out, rel=rel, abs=1e-6)
    if sy['allocation_defined']:
        expect = {'electricity': es['total'] - ns.sum()}
        for d in s['demand']['x']:
            if d['total'] > 0:
                q = 0.0
                for n in d['supply_sources']:
                    p = procs[n]
                    xp = arr(p['x_prod'])
                    q += p['pow_use_elec_prod'] * xp.sum()
                    if p['type'] == 'elec + ther':
                        (g,) = p['supply_sources']        # one supplier in these cases
                        q += gens[g]['a'] * p['pow_use_ther_prod'] * xp.sum()
                expect[d['iden']] = q
        for d in [e] + [d for d in s['demand']['x'] if d['total'] > 0]:
            assert d['accounts']['allocation_share'] == pytest.approx(expect[d['iden']] / out, rel=1e-7, abs=1e-9)
            assert d['accounts']['resource_cost'] == pytest.approx(expect[d['iden']] / out * cost, rel=1e-7, abs=1e-6)
        assert sy['unallocated']['output'] == pytest.approx(out - sum(expect.values()), rel=1e-7, abs=1e-6)
    else:
        assert out <= 1e-6
        assert sy['unallocated']['cost'] == pytest.approx(cost)

    assert sy['accounting_ok'] is True, {k: v for k, v in sy['checks'].items() if not v['ok']}


@pytest.mark.parametrize('seed', SEEDS)
def test_generated_system_satisfies_every_invariant(horizon, monkeypatch, seed):
    horizon(HOURS)
    spec, opts, coeffs = make_case(seed)
    monkeypatch.setattr(u, 'thermo', lambda *args, **kwargs: (coeffs[0], coeffs[1], False))
    ok, s = solve(copy.deepcopy(spec), opts)
    assert ok, f'seed {seed}: {s["solver"]}'
    verify(spec, s, opts, coeffs)


@pytest.mark.parametrize('seed', SEEDS)
def test_demand_marginal_is_a_subgradient(horizon, monkeypatch, seed):
    """For a convex piecewise-linear objective, any subgradient s at d satisfies
    (f(d) - f(d - h)) / h <= s <= (f(d + h) - f(d)) / h for every step h > 0,
    breakpoint or not. Checked on one hour per case, with the carbon budget and
    reliability cap held at their absolute values while demand moves."""
    horizon(HOURS)
    spec, opts, coeffs = make_case(seed)
    monkeypatch.setattr(u, 'thermo', lambda *args, **kwargs: (coeffs[0], coeffs[1], False))
    rng = np.random.RandomState(1000 + seed)
    hour = int(rng.randint(HOURS))
    e = spec['demand']['e']
    dm = demand_series(e, HOURS)
    step = 1e-3 * max(1.0, dm.max())

    def solved(delta):
        s = copy.deepcopy(spec)
        d = dm.copy()
        d[hour] += delta
        s['demand']['e']['profile'] = d.tolist()
        s['demand']['e']['total'] = float(d.sum())
        o = {k: v * e['total'] / d.sum() for k, v in opts.items()}     # same absolute caps
        ok, r = solve(s, o)
        assert ok
        return r

    base = solved(0.0)
    f0 = base['solver']['_objective']
    marginal = base['demand']['e']['shadow_prices']['demand_marginal'][hour]
    right = (solved(step)['solver']['_objective'] - f0) / step
    tol = 1e-6 * max(1.0, abs(right), abs(marginal))
    assert marginal <= right + tol, (seed, hour, marginal, right)
    if dm[hour] - step >= e['l_ns'][0]:
        left = (f0 - solved(-step)['solver']['_objective']) / step
        assert left - tol <= marginal, (seed, hour, left, marginal)


def test_generated_thermal_system_with_the_real_binary(horizon, sim_bin):
    """The same invariants, with coefficients from the compiled executable."""
    horizon(HOURS)
    for seed in SEEDS:
        spec, opts, _ = make_case(seed)
        if any(p['type'] == 'elec + ther' for p in spec['p2x']):
            break
    a, b, err = u.thermo(564, 152, 0.05, 80, binary=sim_bin)
    assert err is False
    ok, s = solve(copy.deepcopy(spec), opts, config=u.RunConfig(hours=HOURS, thermo_bin=sim_bin))
    assert ok
    verify(spec, s, opts, (a, b))


def test_a_negative_target_without_removal_is_reported_infeasible(horizon):
    """The removal unit above is what makes those cases feasible. Without one, a
    net-negative target cannot be met, and the solver must say so rather than
    return a plausible optimum (seeds 14 and 20 before the removal unit)."""
    horizon(HOURS)
    spec, opts, _ = make_case(20)
    spec['generator'] = [g for g in spec['generator'] if g['iden'] != 'removal']
    assert opts['carbon-constraint'] < 0
    assert all(g['var_emis_prod'] >= 0 for g in spec['generator'])
    ok, s = solve(spec, opts)
    assert ok is False


def test_the_generator_covers_what_it_claims():
    """Guard against a generator that silently stops exercising a feature."""
    seen = set()
    for seed in SEEDS:
        spec, opts, _ = make_case(seed)
        seen.update(opts)
        seen.update('thermal' for p in spec['p2x'] if p['type'] == 'elec + ther')
        seen.update('electric process' for p in spec['p2x'] if p['type'] == 'elec')
        seen.update('inflow' for f in spec['flex'] if f.get('inflow_total', 0) > 0)
        seen.update('battery' for f in spec['flex'] if f['iden'] == 'bat')
        seen.update('negative emissions' for g in spec['generator'] if g['var_emis_prod'] < 0)
        seen.update('zero variable cost' for g in spec['generator'] if g['var_cost_prod'] == 0)
        seen.update('fixed capacity' for g in spec['generator'] if g['c_prod'] != -1)
        seen.update('zero-demand hours' for _ in [0] if min(spec['demand']['e']['profile']) == 0)
        seen.update('shortfall lower bound' for _ in [0] if spec['demand']['e']['l_ns'][0] > 0)
        seen.update('zero penalty' for _ in [0] if spec['demand']['e']['var_cost_ns'] == 0)
        if 'carbon-constraint' in opts and opts['carbon-constraint'] < 0:
            seen.add('negative carbon target')
    assert seen >= {'carbon-constraint', 'non-served-power-constraint', 'thermal', 'electric process',
                    'inflow', 'battery', 'negative emissions', 'zero variable cost', 'fixed capacity',
                    'zero-demand hours', 'shortfall lower bound', 'zero penalty', 'negative carbon target'}, seen


# --- provenance, end to end ---------------------------------------------------------

def test_provenance_matches_what_was_run(tmp_path):
    """Every digest in the stamp is the digest of the file actually used."""
    prof = tmp_path / 'shape.csv'
    np.savetxt(str(prof), np.linspace(1, 2, 8760))
    s = system(generators=[generator('g', fix=1.0, var=5.0, profile=str(prof), cf=0.5)],
               e_total=8760.0)
    path = tmp_path / 'case.json'
    path.write_text(json.dumps(s))
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'ies_optimiser.py'), str(path),
                          'carbon-constraint=10'], cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, timeout=300)
    assert out.returncode == 0, out.stdout
    doc = json.loads((tmp_path / 'case.ies-optimiser.carbon-constraint_10.0.json').read_text())
    pv = doc['provenance']
    from ies_optimiser import _install
    PACKAGE = _install.PACKAGE_DIR
    assert pv['input_sha256'] == u.file_digest(str(path))
    assert pv['profiles_sha256'] == {str(prof): u.file_digest(str(prof))}
    assert pv['options'] == {'carbon-constraint': 10.0}
    assert pv['hours'] == 8760
    for rel, digest in pv['source_files_sha256'].items():
        actual = pv['thermo_binary'] if rel == 'thermo/sim.bin' else os.path.join(PACKAGE, rel.split('/', 1)[1])
        assert digest == u.file_digest(actual), rel
    assert pv['thermo_binary'] == u.Thermo_bin and pv['thermo_binary_origin'] == 'packaged'
