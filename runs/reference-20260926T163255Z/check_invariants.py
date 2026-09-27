"""Independent invariant checks on IESO results (reference-state capture, Step 1).

    python check_invariants.py RESULT.ieso.json [...]

Recomputes, from the result's own echoed input and its reported series --
never from IESO's post-processing -- the conditions every optimal solution
must satisfy. Profiles are read from the paths the result records, relative to
the repository root. Tolerance for a feasibility residual: 1e-6 + 1e-7 x scale
(scale = the largest magnitude involved), the same order as IESO's own
Feas_* tolerances; bookkeeping identities: relative 1e-9.
"""

import json
import math
import sys

import numpy as np


def profile(spec, total, hours):
    p = spec.get('profile', '')
    if p == '':
        return np.full(hours, total / hours)
    data = np.loadtxt(p) if isinstance(p, str) else np.asarray(p, float)
    return total * data / data.sum()


def availability(item, hours):
    p = item.get('profile', '')
    cf = item['capacity_factor']
    if p == '':
        return np.full(hours, cf)
    data = np.loadtxt(p) if isinstance(p, str) else np.asarray(p, float)
    n = data / data.max()
    return n * cf / n.mean()


def check(path):
    s = json.load(open(path))
    fails, notes = [], []
    tol = lambda scale: 1e-6 + 1e-7 * max(1.0, float(scale))
    def need(cond, what):
        if not cond:
            fails.append(what)

    json.dumps(s, allow_nan=False)                       # no NaN or infinity anywhere
    need(s['solver'].get('stat_status') == 'optimal' and s['solver']['stat_succ'] == 1, 'solver not optimal')
    need(s['system']['accounting_ok'] is True, 'system.accounting_ok is false')
    H = s['provenance']['hours']
    arr = lambda xs: np.asarray(xs, float)
    gens = {g['iden']: g for g in s['generator']}

    # generators: availability, nameplate, cogeneration
    for g in s['generator']:
        c, e = g['c_prod'], arr(g['e_prod'])
        lo, hi = g['l_prod']
        need(lo - 1e-9 <= c <= hi + 1e-9, f"{g['iden']}: capacity outside l_prod")
        cf = availability(g, H)
        need(e.min() >= -tol(c), f"{g['iden']}: negative output")
        if g['type'] == 'elec + ther':
            h, a, b = arr(g['h_prod']), g['a'], g['b']
            need((e + a * h - cf * c).max() <= tol(c), f"{g['iden']}: e + a h > cf c")
            need((h - b * cf * c).max() <= tol(c), f"{g['iden']}: h > b cf c")
            need((e + a * h - c).max() <= tol(c), f"{g['iden']}: e + a h > c")
        else:
            need((e - cf * c).max() <= tol(c), f"{g['iden']}: e > cf c")
            need((e - c).max() <= tol(c), f"{g['iden']}: e > c")

    # storage: bounds, duration limit, transitions, closure
    for f in s['flex']:
        c = f['c_strg']
        ch, dc, st = arr(f['e_char']), arr(f['e_disc']), arr(f['e_strg'])
        r = math.sqrt(f['round_trip_efficiency'])
        inflow = profile({'profile': f.get('inflow_profile', '')}, f.get('inflow_total', 0.0), H) \
            if f.get('inflow_total', 0) > 0 else np.zeros(H)
        spill = arr(f['e_spil']) if f.get('inflow_total', 0) > 0 else np.zeros(H)
        need(min(ch.min(), dc.min(), spill.min()) >= -tol(c), f"{f['iden']}: negative flow")
        need(max(ch.max(), dc.max()) <= c / f['hours_of_storage'] + tol(c), f"{f['iden']}: power above c/hours")
        need(st.min() >= f['soc_min'] * c - tol(c) and st.max() <= f['soc_max'] * c + tol(c), f"{f['iden']}: SOC band")
        prev = np.concatenate([[f['soc_ini'] * c], st[:-1]])
        need(np.abs(st - (prev + inflow - spill + r * ch - dc / r)).max() <= tol(c), f"{f['iden']}: storage transition")
        need(abs(st[-1] - f['soc_ini'] * c) <= tol(c), f"{f['iden']}: year not closed")
    for p in s['p2x']:
        c, cs = p['c_prod'], p['c_strg']
        xp, xs, xst = arr(p['x_prod']), arr(p['x_supp']), arr(p['x_strg'])
        need(min(xp.min(), xs.min(), xst.min()) >= -tol(max(c, cs)), f"{p['iden']}: negative flow")
        need((xp - availability(p, H) * c).max() <= tol(c), f"{p['iden']}: production above cf c")
        need((xst - cs).max() <= tol(cs), f"{p['iden']}: inventory above c_strg")
        prev = np.concatenate([[p['soc_ini'] * cs], xst[:-1]])
        need(np.abs(xst - (prev + xp - xs)).max() <= tol(max(cs, xs.max())), f"{p['iden']}: inventory transition")
        need(abs(xst[-1] - p['soc_ini'] * cs) <= tol(cs), f"{p['iden']}: year not closed")

    # electricity: shortfall bounds and balance
    e = s['demand']['e']
    dm = profile(e, e['total'], H)
    ns = arr(e['output_ns'])
    need(ns.min() >= e['l_ns'][0] - tol(dm.max()) and (ns - dm).max() <= tol(dm.max()), 'electricity: unmet outside [l_ns0, demand]')
    gen = np.sum([arr(g['e_prod']) for g in s['generator']], axis=0)
    net = np.sum([arr(f['e_disc']) - arr(f['e_char']) for f in s['flex']], axis=0) if s['flex'] else 0
    use = np.sum([p['pow_use_elec_prod'] * arr(p['x_prod']) for p in s['p2x']], axis=0) if s['p2x'] else 0
    S = gen + net - use + ns - dm
    need(S.min() >= -tol(max(dm.max(), gen.max())), 'electricity balance violated')
    need(np.abs(S - arr(e['surplus'])).max() <= tol(dm.max()), 'reported electricity surplus differs')
    notes.append(f"unmet electricity {ns.sum():.3g} MWh")

    # heat and products
    procs = {p['iden']: p for p in s['p2x']}
    for p in s['p2x']:
        if p['type'] == 'elec + ther':
            h = np.sum([arr(gens[g]['h_prod']) for g in p['supply_sources']], axis=0)
            need((p['pow_use_ther_prod'] * arr(p['x_prod']) - h).max() <= tol(h.max()), f"{p['iden']}: heat balance")
    for d in s['demand']['x']:
        if d['total'] <= 0:
            continue
        dmx = profile(d, d['total'], H)
        nsx = arr(d['output_ns'])
        need(nsx.min() >= d['l_ns'][0] - tol(dmx.max()) and (nsx - dmx).max() <= tol(dmx.max()), f"{d['iden']}: unmet outside bounds")
        sup = np.sum([arr(procs[n]['x_supp']) for n in d['supply_sources']], axis=0)
        need((sup + nsx - dmx).min() >= -tol(dmx.max()), f"{d['iden']}: product balance")
        notes.append(f"unmet {d['iden']} {nsx.sum():.3g}")

    # costs, emissions, caps and reconciliation
    cost = emis = 0.0
    for g in s['generator']:
        heat = g['a'] * arr(g['h_prod']).sum() if g['type'] == 'elec + ther' else 0.0
        cost += g['c_prod'] * g['fix_cost_prod'] + g['var_cost_prod'] * (arr(g['e_prod']).sum() + heat)
        emis += g['var_emis_prod'] * (arr(g['e_prod']).sum() + heat)
    for f in s['flex']:
        cost += f['c_strg'] * f['fix_cost_strg']
    for p in s['p2x']:
        cost += p['c_prod'] * p['fix_cost_prod'] + p['c_strg'] * p['fix_cost_strg'] + p['var_cost_prod'] * arr(p['x_prod']).sum()
    sy = s['system']
    need(abs(cost - sy['cost']) <= 1e-9 * abs(cost) + 1e-6, f"system cost {sy['cost']} != recomputed {cost}")
    need(abs(emis - sy['emis']) <= 1e-9 * abs(emis) + 1e-6, f"emissions {sy['emis']} != recomputed {emis}")
    need(abs(sy['allocated']['cost'] + sy['unallocated']['cost'] - cost) <= 1e-9 * abs(cost) + 1e-6, 'cost does not reconcile')
    need(abs(sy['allocated']['emis'] + sy['unallocated']['emis'] - emis) <= 1e-9 * abs(emis) + 1e-6, 'emissions do not reconcile')
    opts = s['provenance']['options']
    if 'carbon-constraint' in opts:
        cap = opts['carbon-constraint'] * e['total']
        need(emis <= cap + tol(max(abs(cap), abs(emis))), 'carbon cap exceeded')
    if 'non-served-power-constraint' in opts:
        need(ns.sum() <= opts['non-served-power-constraint'] * e['total'] + tol(e['total']), 'reliability cap exceeded')
    need(sy['checks']['objective_reconciliation']['ok'], 'objective_reconciliation (IESO) failed')
    return fails, notes, cost, emis


if __name__ == '__main__':
    bad = 0
    for path in sys.argv[1:]:
        fails, notes, cost, emis = check(path)
        bad += bool(fails)
        print(f"{'PASS' if not fails else 'FAIL'}  {path.split('/')[-1]}  cost {cost:,.2f}  emis {emis:,.2f}  {'; '.join(notes)}")
        for f in fails:
            print('      ' + f)
    sys.exit(1 if bad else 0)
