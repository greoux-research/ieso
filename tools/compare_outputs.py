#!/usr/bin/env python3
"""Compare two IESO results field by field.

Absence is a difference. A series that is missing, empty or of the wrong
length, an entity present in one file and not the other, a required field that
is not there at all — each is reported rather than skipped, because a
comparator that passes over what it cannot find reports agreement it has not
checked. `stat_time` is excluded as wall-clock.

Exit status is 0 only when the two results agree.
"""

import json
import math
import sys

import numpy as np

RTOL, ATOL = 1e-9, 1e-6

# What every result must carry, by section.
REQUIRED = {
    'generator': (['c_prod', 'type'], ['e_prod']),
    'flex': (['c_strg'], ['e_char', 'e_disc', 'e_strg']),
    'p2x': (['c_prod', 'c_strg'], ['x_prod', 'x_supp', 'x_strg']),
}
OPTIONAL_SERIES = {'generator': ['h_prod'], 'flex': ['e_spil'], 'p2x': []}


def load(path):
    with open(path) as f:
        return json.load(f)


def cmp_series(a, b, name, out, allow_empty=False):
    for value, which in ((a, 'new'), (b, 'old')):
        if value is None:
            out.append(f"    {name}: absent in {which}")
            return
        if not isinstance(value, list):
            out.append(f"    {name}: not a series in {which} ({type(value).__name__})")
            return
    if len(a) != len(b):
        out.append(f"    {name}: length {len(a)} vs {len(b)}")
        return
    if len(a) == 0:
        # Some series are legitimately empty: heat output on a unit that is not
        # a cogeneration plant, spillage on a store with no inflow. Where the
        # series is required, emptiness means the result carries nothing to
        # check and is reported as such.
        if not allow_empty:
            out.append(f"    {name}: empty in both — nothing verified")
        return
    a, b = np.asarray(a, float), np.asarray(b, float)
    # NaN propagates through max() and every comparison against it is False, so
    # a single non-finite entry would report agreement for the whole series.
    for value, which in ((a, 'new'), (b, 'old')):
        bad = ~np.isfinite(value)
        if bad.any():
            out.append(f"    {name}: {int(bad.sum())} non-finite value(s) in {which}, "
                       f"first at h{int(np.argmax(bad))}")
            return
    d = np.abs(a - b)
    if d.max() > ATOL + RTOL * np.abs(b).max():
        i = int(d.argmax())
        out.append(f"    {name}: max|d|={d.max():.6g} at h{i} ({a[i]:.6g} vs {b[i]:.6g}); "
                   f"n>{ATOL:g}={int((d > ATOL).sum())}; sum {a.sum():.10g} vs {b.sum():.10g}")


def cmp_scalar(a, b, name, out, required=True):
    # legacy placeholder: inactive commodities were written as [-1,-1], now -1
    if isinstance(a, list) and set(a) == {-1}:
        a = -1
    if isinstance(b, list) and set(b) == {-1}:
        b = -1
    if a is None or b is None:
        if required or not (a is None and b is None):
            out.append(f"    {name}: {a} vs {b}"
                       f"{'   [ABSENT]' if a is None or b is None else ''}")
        return
    if isinstance(a, (list, dict)) or isinstance(b, (list, dict)) \
            or isinstance(a, str) or isinstance(b, str) \
            or isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            out.append(f"    {name}: {a} vs {b}   [SCHEMA]")
        return
    for value, which in ((a, 'new'), (b, 'old')):
        if not math.isfinite(value):
            out.append(f"    {name}: non-finite in {which} ({value!r})")
            return
    if abs(a - b) > ATOL + RTOL * abs(b):
        out.append(f"    {name}: {a!r} vs {b!r}  (d={a - b:.6g})")


def section(new, old, key, out):
    ents_n = {e['iden']: e for e in new.get(key, [])}
    ents_o = {e['iden']: e for e in old.get(key, [])}
    if set(ents_n) != set(ents_o):
        only_new = sorted(set(ents_n) - set(ents_o))
        only_old = sorted(set(ents_o) - set(ents_n))
        out.append(f"  {key}: entity sets differ — only in new: {only_new or '-'}; "
                   f"only in old: {only_old or '-'}")
    scalars, series = REQUIRED[key]
    for k in sorted(set(ents_n) & set(ents_o)):
        sub = []
        for f in scalars:
            cmp_scalar(ents_n[k].get(f), ents_o[k].get(f), f, sub)
        for f in series:
            cmp_series(ents_n[k].get(f), ents_o[k].get(f), f, sub)
        for f in OPTIONAL_SERIES[key]:
            if ents_n[k].get(f) is not None or ents_o[k].get(f) is not None:
                cmp_series(ents_n[k].get(f), ents_o[k].get(f), f, sub, allow_empty=True)
        if key == 'generator':
            # a and b convert heat to forgone electricity and cap heat output.
            # They are set from the turbine conditions at build time, so two
            # results that agree on dispatch but not on these describe different
            # machines. Required once a unit is thermally coupled.
            thermal = 'elec + ther' in (ents_n[k].get('type'), ents_o[k].get('type'))
            for f in ('a', 'b'):
                cmp_scalar(ents_n[k].get(f), ents_o[k].get(f), f, sub,
                           required=thermal)
        if sub:
            out.append(f"  {key}[{k}]:\n" + "\n".join(sub))


def demand(new, old, out):
    pairs = [('demand.e', new['demand']['e'], old['demand']['e'])]

    xn = {d['iden']: d for d in new['demand'].get('x', [])}
    xo = {d['iden']: d for d in old['demand'].get('x', [])}
    if set(xn) != set(xo):
        out.append(f"  demand.x: commodity sets differ — only in new: "
                   f"{sorted(set(xn) - set(xo)) or '-'}; only in old: "
                   f"{sorted(set(xo) - set(xn)) or '-'}")
    for k in sorted(set(xn) & set(xo)):
        pairs.append((f"demand.x[{k}]", xn[k], xo[k]))

    for label, dn, do in pairs:
        sub = []
        active = (dn.get('total', 0) or 0) > 0 or (do.get('total', 0) or 0) > 0
        cmp_scalar(dn.get('total'), do.get('total'), 'total', sub)
        for k in ('cost', 'emis', 'reli'):
            cmp_scalar(dn.get('kpis', {}).get(k), do.get('kpis', {}).get(k),
                       f'kpis.{k}', sub, required=active)
        for k in ('carbon_cap', 'reliability_cap'):
            if k in dn.get('shadow_prices', {}) or k in do.get('shadow_prices', {}):
                cmp_scalar(dn.get('shadow_prices', {}).get(k),
                           do.get('shadow_prices', {}).get(k), f'sp.{k}', sub)
        if active:
            cmp_series(dn.get('output_ns'), do.get('output_ns'), 'output_ns', sub)
            cmp_series(dn.get('shadow_prices', {}).get('demand_match'),
                       do.get('shadow_prices', {}).get('demand_match'),
                       'sp.demand_match', sub)
        if sub:
            out.append(f"  {label}:\n" + "\n".join(sub))


def main(pnew, pold):
    new, old = load(pnew), load(pold)
    out = []

    for f in ('stat_succ', 'stat_status', 'stat_capa', 'stat_outp', 'stat_cons'):
        if f in new.get('solver', {}) or f in old.get('solver', {}):
            cmp_scalar(new.get('solver', {}).get(f), old.get('solver', {}).get(f),
                       f'solver.{f}', out)

    for key in ('generator', 'flex', 'p2x'):
        section(new, old, key, out)
    demand(new, old, out)

    print(f"{'IDENTICAL' if not out else 'DIFFERENCES'}: {pnew.split('/')[-1]}")
    for line in out:
        print(line)
    return 0 if not out else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
