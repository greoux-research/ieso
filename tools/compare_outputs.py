#!/usr/bin/env python3
"""Compare two IESO output JSONs. Reports structural, capacity, dispatch and KPI
differences with explicit tolerances. stat_time is excluded (wall clock)."""
import json, sys, numpy as np

RTOL, ATOL = 1e-9, 1e-6

def load(p):
    with open(p) as f: return json.load(f)

def cmp_series(a, b, name, out):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        out.append(f"    {name}: SHAPE {a.shape} vs {b.shape}"); return
    d = np.abs(a - b)
    if d.size and d.max() > ATOL + RTOL * np.abs(b).max():
        i = int(d.argmax())
        out.append(f"    {name}: max|d|={d.max():.6g} at h{i} ({a[i]:.6g} vs {b[i]:.6g}); "
                   f"n>{ATOL:g}={int((d>ATOL).sum())}; sum {a.sum():.10g} vs {b.sum():.10g}")

def cmp_scalar(a, b, name, out):
    # legacy placeholder: inactive commodities were written as [-1,-1], now -1
    if isinstance(a, list) and set(a) == {-1}: a = -1
    if isinstance(b, list) and set(b) == {-1}: b = -1
    if a is None or b is None or isinstance(a, (list, dict)) or isinstance(b, (list, dict)):
        if a != b: out.append(f"    {name}: {a} vs {b}   [SCHEMA]")
        return
    if abs(a - b) > ATOL + RTOL * abs(b):
        out.append(f"    {name}: {a!r} vs {b!r}  (d={a-b:.6g})")

def section(new, old, key, idfield, fields, series, out):
    n = {e[idfield]: e for e in new.get(key, [])}
    o = {e[idfield]: e for e in old.get(key, [])}
    if set(n) != set(o):
        out.append(f"  {key}: entity sets differ {sorted(set(n)^set(o))}")
    for k in sorted(set(n) & set(o)):
        sub = []
        for f in fields:
            if f in n[k] and f in o[k]: cmp_scalar(n[k][f], o[k][f], f, sub)
        for f in series:
            if n[k].get(f) and o[k].get(f): cmp_series(n[k][f], o[k][f], f, sub)
        if sub: out.append(f"  {key}[{k}]:\n" + "\n".join(sub))

def main(pnew, pold):
    new, old = load(pnew), load(pold)
    out = []
    for f in ("stat_succ", "stat_capa", "stat_outp", "stat_cons"):
        cmp_scalar(new["solver"].get(f), old["solver"].get(f), f"solver.{f}", out)
    section(new, old, "generator", "iden", ["c_prod", "a", "b"], ["e_prod", "h_prod"], out)
    section(new, old, "flex", "iden", ["c_strg"], ["e_char", "e_disc", "e_strg", "e_spil"], out)
    section(new, old, "p2x", "iden", ["c_prod", "c_strg"], ["x_prod", "x_supp", "x_strg"], out)
    for label, dn, do in [("demand.e", new["demand"]["e"], old["demand"]["e"])] + [
            (f"demand.x[{a['iden']}]", a, b)
            for a, b in zip(new["demand"]["x"], old["demand"]["x"])]:
        sub = []
        for k in ("cost", "emis", "reli"):
            cmp_scalar(dn.get("kpis", {}).get(k), do.get("kpis", {}).get(k), f"kpis.{k}", sub)
        for k in ("carbon_cap", "reliability_cap"):
            cmp_scalar(dn.get("shadow_prices", {}).get(k), do.get("shadow_prices", {}).get(k), f"sp.{k}", sub)
        for k in ("output_ns",):
            if dn.get(k) and do.get(k): cmp_series(dn[k], do[k], k, sub)
        sp_n, sp_o = dn.get("shadow_prices", {}).get("demand_match"), do.get("shadow_prices", {}).get("demand_match")
        if sp_n and sp_o: cmp_series(sp_n, sp_o, "sp.demand_match", sub)
        if sub: out.append(f"  {label}:\n" + "\n".join(sub))
    print(f"{'IDENTICAL' if not out else 'DIFFERENCES'}: {pnew.split('/')[-1]}")
    for line in out: print(line)
    return 0 if not out else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
