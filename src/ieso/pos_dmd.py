#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import numpy as np

import logging

from ieso import fcn as u

log = logging.getLogger('ieso')


def accounts(prop, g_cost, g_emis, total, ns_sum, var_cost_ns, allocated_output=None, surplus=None):

    # Explicit quantities behind the cost KPI, kept apart from one another.
    #
    # 'cost' blends two different things: the resource expenditure allocated to a
    # commodity, and the penalty charged for demand that was never served. The
    # second is a modelling price on a shortfall, not money spent on supply, and
    # it is divided by demand rather than by the volume actually delivered. Both
    # conventions are preserved for compatibility, and the components are
    # reported separately so a reader need not unpick them.

    # A system that generates nothing has no output to allocate, so the share is
    # undefined rather than zero and everything derived from it is reported as
    # null. The quantities that remain observable -- what was demanded, what was
    # served, what the shortfall was charged -- are reported regardless.

    resource_cost = None if prop is None else prop * g_cost

    shortage_penalty = ns_sum * var_cost_ns

    served = total - ns_sum

    return {
        "allocation_share": prop,
        "allocated_output": allocated_output,
        "resource_cost": resource_cost,
        "shortage_penalty": shortage_penalty,
        "emissions": None if prop is None else prop * g_emis,
        "demand": total,
        "unmet_demand": ns_sum,
        "served_demand": served,
        "resource_cost_per_demand":
            None if resource_cost is None or total <= 0 else resource_cost / total,
        "resource_cost_per_served":
            None if resource_cost is None or served <= 0 else resource_cost / served,
        "surplus": surplus,
    }


def cap_report(con, cap, activity):

    # A cap is a one-sided limit, and only a limit that binds has a marginal
    # value. Report what was observed (the raw dual, the activity, the slack)
    # separately from the interpretation, rather than presenting a number that
    # looks like a marginal cost when it is not one.

    raw = con.dual_value()

    slack = cap - activity

    binding = slack <= u.Balance_atol + u.Balance_rtol * max(abs(cap), 1.0)

    value = raw * -1.0 if binding else 0.0

    return value, {
        "raw_dual": raw,
        "cap": cap,
        "activity": activity,
        "slack": slack,
        "binding": bool(binding),
        # Observation, not diagnosis. A binding row with a zero dual may be
        # degenerate, or its marginal value may genuinely be zero and unique --
        # a cap set exactly where the solution would have landed anyway binds
        # and is worth nothing. Distinguishing the two needs analysis this does
        # not perform, so the flag records only what was seen.
        "binding_zero_dual": bool(binding and abs(raw) <= u.Balance_atol),
    }


def g_figs(s, cfg):

    # --- --- --- --- --- --- --- --- --- Global figures

    # --- global electricity generation figure /!\ excluding non-served e

    g_outp = 0.0

    # g_outp  = sum of ( gen['e_prod'] + gen['h_prod'] * gen['a'] ) across technologies and hours
    # g_outp += sum of ( flx['e_disc'] - flx['e_char'] ) across technologies and hours

    # --- generator

    for gen in s['generator']:

        for i in range(0, cfg.hours):

            g_outp += gen['e_prod'][i].solution_value()

            if gen['type'] == 'elec + ther':

                g_outp += gen['h_prod'][i].solution_value() * gen['a']

    # --- flex

    for flx in s['flex']:

        for i in range(0, cfg.hours):

            g_outp += flx['e_disc'][i].solution_value() - flx['e_char'][i].solution_value()

    # --- global cost figure /!\ excluding penalties for non serving demand for e & x

    g_cost = 0.0

    # fixed and variable costs associated with all assets in the system

    # --- generator

    for gen in s['generator']:

        if u.capaSetToBeOptimised(gen['c_prod']):

            g_cost += gen['c_prod'].solution_value() * gen['fix_cost_prod']

        else:

            g_cost += gen['c_prod'] * gen['fix_cost_prod']

        for i in range(0, cfg.hours):

            g_cost += gen['e_prod'][i].solution_value() * gen['var_cost_prod']

            if gen['type'] == 'elec + ther':

                g_cost += gen['h_prod'][i].solution_value() * gen['var_cost_prod'] * gen['a']

    # --- flex

    for flx in s['flex']:

        if u.capaSetToBeOptimised(flx['c_strg']):

            g_cost += flx['c_strg'].solution_value() * flx['fix_cost_strg']

        else:

            g_cost += flx['c_strg'] * flx['fix_cost_strg']

    # --- p2x /!\ excluding energy costs

    for p2x in s['p2x']:

        if u.capaSetToBeOptimised(p2x['c_strg']):

            g_cost += p2x['c_strg'].solution_value() * p2x['fix_cost_strg']

        else:

            g_cost += p2x['c_strg'] * p2x['fix_cost_strg']

        if u.capaSetToBeOptimised(p2x['c_prod']):

            g_cost += p2x['c_prod'].solution_value() * p2x['fix_cost_prod']

        else:

            g_cost += p2x['c_prod'] * p2x['fix_cost_prod']

        for i in range(0, cfg.hours):

            g_cost += p2x['x_prod'][i].solution_value() * p2x['var_cost_prod']

    # --- global emissions figure

    g_emis = 0.0

    for gen in s['generator']:

        for i in range(0, cfg.hours):

            g_emis += gen['e_prod'][i].solution_value() * gen['var_emis_prod']

            if gen['type'] == 'elec + ther':

                g_emis += gen['h_prod'][i].solution_value() * gen['var_emis_prod'] * gen['a']

    # --- finish line

    return g_outp, g_cost, g_emis


def _v(x):

    return x.solution_value() if hasattr(x, 'solution_value') else float(x)


def _arr(xs, hours):

    return np.array([_v(x) for x in xs], dtype=float) if len(xs) else np.zeros(hours)


def check(checks, name, residual, tolerance):

    """Record one accounting check in a machine-readable form."""

    residual = float(residual)

    checks[name] = {
        "residual": residual,
        "tolerance": float(tolerance),
        "ok": bool(np.isfinite(residual) and residual <= tolerance),
    }


def demand_marginal(rows, ns_vars, dm, l_ns):

    """
    Dual-based marginal value of demand, hour by hour.

    Unmet demand is bounded above by min(l_ns[1], demand), so where the
    shortfall sits at a bound set by demand, demand enters two places: the
    balance row and that bound. The row dual (demand_match) holds every bound
    fixed; adding the shortfall variable's reduced cost -- the dual of the
    demand-set bound -- gives the dual value of demand in both places.

    What this is, precisely: the objective is a convex, piecewise-linear
    function of an hour's demand (the carbon budget and reliability cap held
    fixed), and this value is a subgradient of it. It therefore always lies
    between the left and right derivatives, and equals the derivative wherever
    the two agree. At a breakpoint -- demand exactly at zero, at a capacity
    limit, at a change of marginal unit -- it may be any value between them,
    and is not guaranteed to be either one-sided derivative: at zero demand
    with a 100 $/MWh unit it can be 0 while the next MWh costs 100. Exact
    one-sided derivatives would need a parametric re-solve per hour and are
    not computed.
    """

    high = float(l_ns[1])

    out = []

    for i in range(len(rows)):

        value = rows[i].dual_value()

        if dm[i] < high:

            reduced = ns_vars[i].reduced_cost()

            if reduced < 0:

                value += reduced

        out.append(value)

    return out


def feas_tol(scale):

    return u.Feas_atol + u.Feas_rtol * max(1.0, float(scale))


def recon_tol(scale):

    return u.Recon_atol + u.Recon_rtol * max(1.0, abs(float(scale)))


def demand_props(s, opts, emis_con, nspo_con, objective, cfg):

    # --- --- --- --- --- --- --- --- --- Surplus, allocation and reconciliation
    #
    # Units: electricity MWh, heat MWh (thermal), product Q (kg, m3, MWh heat).
    # Hour i; g generator; f flexibility means; p process; d product demand;
    # u_p = pow_use_elec_prod, t_p = pow_use_ther_prod, a_g = heat coefficient.
    #
    # The demand balances are inequalities; their residuals are the surpluses:
    #
    #   S_e[i]   = sum_g e_g[i] + sum_f (disc_f - char_f)[i] - sum_p u_p x_prod_p[i]
    #              + ns_e[i] - dm_e[i]                                     (MWh)
    #   S_h,p[i] = sum_{g in src(p)} h_g[i] - t_p x_prod_p[i]               (MWh heat)
    #   S_x,d[i] = sum_{p in src(d)} x_supp_p[i] + ns_d[i] - dm_d[i]        (Q)
    #
    # Spill (e_spil) is inflow released without generating. It never becomes
    # output, so it is reported but carries no share of anything.
    #
    # Allocation base: electricity-equivalent output (heat valued at the
    # electricity it displaces, a_g h_g):
    #
    #   OUT = sum_g sum_i (e_g + a_g h_g) + sum_f sum_i (disc_f - char_f)
    #
    # which, by the electricity balance, divides exactly into
    #
    #   allocated   = served_e + sum_{p owned} (u_p X_p + used heat_p)
    #   unallocated = sum_i S_e + unused heat + sum_{p unowned} (u_p X_p + used heat_p)
    #
    # 'Owned' processes are those named by an active product demand (at most
    # one each, enforced in chk). Unused heat S_h,p is attributed to the
    # process's suppliers in proportion to their heat in that hour, and valued
    # at each supplier's own a_g. A process's energy is an input to its
    # commodity whether or not all its product is delivered, so product
    # surplus is reported in its own units and stays inside that commodity's
    # share: counting it as unallocated as well would count the same energy
    # twice. Storage losses (charge exceeding discharge) reduce OUT and are
    # thus borne by every share, as before.
    #
    #   share_d = allocated_d / OUT,  cost_d = share_d * system cost,
    #   emis_d = share_d * system emissions; the unallocated share likewise, so
    #   allocated + unallocated = system total, for output, cost and emissions.
    #
    # When OUT is zero there is nothing to allocate by: shares are undefined
    # (null), nothing is allocated, and the whole system cost and emissions are
    # reported as unallocated. Shortage penalties are never part of any of it.

    g_outp, g_cost, g_emis = g_figs(s, cfg)

    H = cfg.hours

    checks = {}

    # === === === === === === === === === hourly flows

    gen_e = {gen['iden']: _arr(gen['e_prod'], H) for gen in s['generator']}

    gen_h = {gen['iden']: _arr(gen['h_prod'], H) for gen in s['generator'] if gen['type'] == 'elec + ther'}

    gen_a = {gen['iden']: gen['a'] for gen in s['generator']}

    flx_net = np.zeros(H)

    spill = 0.0

    for flx in s['flex']:

        flx_net += _arr(flx['e_disc'], H) - _arr(flx['e_char'], H)

        if flx.get('inflow_total', 0) > 0:

            spill += float(np.sum(_arr(flx['e_spil'], H)))

    x_prod = {p['iden']: _arr(p['x_prod'], H) for p in s['p2x']}

    x_supp = {p['iden']: _arr(p['x_supp'], H) for p in s['p2x']}

    elec_use = {p['iden']: p['pow_use_elec_prod'] * x_prod[p['iden']] for p in s['p2x']}

    # === === === === === === === === === electricity

    dmd = s['demand']['e']

    dm_e = np.array(u.dm_h(dmd['profile'], dmd['total'], 'demand.e', hours=H, base=cfg.profile_base), dtype=float)

    ns_e = _arr(dmd['output_ns'], H)

    gen_total = np.sum(list(gen_e.values()), axis=0) if gen_e else np.zeros(H)

    use_total = np.sum(list(elec_use.values()), axis=0) if elec_use else np.zeros(H)

    S_e = gen_total + flx_net - use_total + ns_e - dm_e

    e_scale = max(np.max(np.abs(dm_e)), np.max(np.abs(gen_total)), np.max(np.abs(use_total)))

    check(checks, 'electricity_balance', max(0.0, -np.min(S_e)), feas_tol(e_scale))

    short_resid = max(0.0, -np.min(ns_e), np.max(ns_e - dm_e))

    short_scale = np.max(np.abs(dm_e))

    # === === === === === === === === === heat

    heat_used_eq = {}                 # process -> electricity-equivalent heat used

    heat_unused_eq = 0.0

    heat_surplus_total = 0.0

    heat_resid, heat_scale = 0.0, 0.0

    for p2x in s['p2x']:

        heat_used_eq[p2x['iden']] = 0.0

        p2x['heat_surplus'] = []

        if p2x['type'] != 'elec + ther':

            continue

        suppliers = [g for g in p2x['supply_sources'] if g in gen_h]

        supplied = np.sum([gen_h[g] for g in suppliers], axis=0) if suppliers else np.zeros(H)

        need = p2x['pow_use_ther_prod'] * x_prod[p2x['iden']]

        S_h = supplied - need

        p2x['heat_surplus'] = S_h.tolist()

        heat_surplus_total += float(np.sum(S_h))

        heat_resid = max(heat_resid, -float(np.min(S_h)))

        heat_scale = max(heat_scale, float(np.max(np.abs(supplied))), float(np.max(np.abs(need))))

        with np.errstate(divide='ignore', invalid='ignore'):

            fraction = np.where(supplied > u.Balance_atol, S_h / np.where(supplied > u.Balance_atol, supplied, 1.0), 0.0)

        for g in suppliers:

            unused = gen_h[g] * fraction

            heat_used_eq[p2x['iden']] += gen_a[g] * float(np.sum(gen_h[g] - unused))

            heat_unused_eq += gen_a[g] * float(np.sum(unused))

    if gen_h:

        check(checks, 'heat_balance', max(0.0, heat_resid), feas_tol(heat_scale))

    # === === === === === === === === === products

    owner = {}

    for d in s['demand']['x']:

        if d['total'] > 0:

            for name in d['supply_sources']:

                owner[name] = d['iden']

    def process_eq(name, p2x):

        return float(np.sum(elec_use[name])) + heat_used_eq[name]

    unassigned_eq = 0.0

    unassigned_supply = {}

    for p2x in s['p2x']:

        if p2x['iden'] not in owner:

            unassigned_eq += process_eq(p2x['iden'], p2x)

            unassigned_supply[p2x['iden']] = float(np.sum(x_supp[p2x['iden']]))

    # === === === === === === === === === allocation

    e_ns_sum = float(np.sum(ns_e))

    allocated_out = {}

    if dmd['total'] > 0:

        allocated_out[dmd['iden']] = dmd['total'] - e_ns_sum

    for d in s['demand']['x']:

        if d['total'] > 0:

            allocated_out[d['iden']] = sum(process_eq(p['iden'], p) for p in s['p2x']
                                           if owner.get(p['iden']) == d['iden'])

    unalloc_components = {
        "electricity_surplus": float(np.sum(S_e)),
        "unused_heat": heat_unused_eq,
        "unassigned_process_use": unassigned_eq,
    }

    unalloc_out = sum(unalloc_components.values())

    alloc_out_total = sum(allocated_out.values())

    defined = g_outp > u.Balance_atol

    def share(q):

        return q / g_outp if defined else None

    # === === === === === === === === === electricity demand object

    dmd['shadow_prices'] = {
        "demand_match": [],
        "carbon_cap": -1,
        "reliability_cap": -1
    }

    dmd['kpis'] = {
        "cost": -1,
        "emis": -1,
        "reli": -1
    }

    dmd['shadow_prices']['demand_match'] = [dmd['__meet_dmnd'][i].dual_value() for i in range(H)]

    dmd['shadow_prices']['demand_marginal'] = demand_marginal(dmd['__meet_dmnd'], dmd['output_ns'], dm_e, dmd['l_ns'])

    dmd['output_ns'] = ns_e.tolist()

    dmd['surplus'] = S_e.tolist()

    if "carbon-constraint" in opts:

        cap = dmd['total'] * opts["carbon-constraint"]

        _value, _detail = cap_report(emis_con, cap, g_emis)

        dmd['shadow_prices']['carbon_cap'] = _value

        dmd['shadow_prices']['carbon_cap_detail'] = _detail

        check(checks, 'carbon_cap', max(0.0, g_emis - cap), feas_tol(max(abs(cap), abs(g_emis))))

    if "non-served-power-constraint" in opts:

        cap = dmd['total'] * opts["non-served-power-constraint"]

        _value, _detail = cap_report(nspo_con, cap, e_ns_sum)

        dmd['shadow_prices']['reliability_cap'] = _value

        dmd['shadow_prices']['reliability_cap_detail'] = _detail

        check(checks, 'reliability_cap', max(0.0, e_ns_sum - cap), feas_tol(cap))

    penalties = 0.0

    def fill(d, ns_sum, surplus_total):

        # Reliability is the served share of demand, known whenever demand is
        # positive; it does not depend on there being output to allocate.

        prop = share(allocated_out[d['iden']])

        d['accounts'] = accounts(prop, g_cost, g_emis, d['total'], ns_sum, d['var_cost_ns'],
                                 allocated_out[d['iden']], surplus_total)

        d['kpis'] = {
            "cost": (prop * g_cost + ns_sum * d['var_cost_ns']) / d['total'] if defined else -1,
            "emis": prop * g_emis / d['total'] if defined else -1,
            "reli": 1.0 - ns_sum / d['total'],
        }

        return ns_sum * d['var_cost_ns']

    if dmd['total'] > 0:

        penalties += fill(dmd, e_ns_sum, float(np.sum(S_e)))

    # === === === === === === === === === product demand objects

    product_surplus = {}

    prod_resid, prod_scale = 0.0, 0.0

    for d in s['demand']['x']:

        d['shadow_prices'] = {
            "demand_match": [],
            "demand_marginal": []
        }

        d['kpis'] = {
            "cost": -1,
            "emis": -1,
            "reli": -1
        }

        d['surplus'] = []

        if d['total'] > 0:

            who = 'demand.x[' + d['iden'] + ']'

            dm = np.array(u.dm_h(d['profile'], d['total'], who, hours=H, base=cfg.profile_base), dtype=float)

            ns = _arr(d['output_ns'], H)

            supplied = np.sum([x_supp[p] for p in d['supply_sources']], axis=0) \
                if d['supply_sources'] else np.zeros(H)

            S_x = supplied + ns - dm

            d['shadow_prices']['demand_match'] = [d['__meet_dmnd'][i].dual_value() for i in range(H)]

            d['shadow_prices']['demand_marginal'] = demand_marginal(d['__meet_dmnd'], d['output_ns'], dm, d['l_ns'])

            d['output_ns'] = ns.tolist()

            d['surplus'] = S_x.tolist()

            product_surplus[d['iden']] = float(np.sum(S_x))

            prod_resid = max(prod_resid, -float(np.min(S_x)))

            prod_scale = max(prod_scale, float(np.max(np.abs(dm))), float(np.max(np.abs(supplied))))

            short_resid = max(short_resid, -float(np.min(ns)), float(np.max(ns - dm)))

            short_scale = max(short_scale, float(np.max(np.abs(dm))))

            penalties += fill(d, float(np.sum(ns)), float(np.sum(S_x)))

    if product_surplus:

        check(checks, 'product_balance', max(0.0, prod_resid), feas_tol(prod_scale))

    check(checks, 'shortfall_bounds', short_resid, feas_tol(short_scale))

    # === === === === === === === === === system totals and reconciliation

    if defined:

        allocated = {"output": alloc_out_total, "share": alloc_out_total / g_outp,
                     "cost": alloc_out_total / g_outp * g_cost, "emis": alloc_out_total / g_outp * g_emis}

        unallocated = {"output": unalloc_out, "share": unalloc_out / g_outp,
                       "cost": unalloc_out / g_outp * g_cost, "emis": unalloc_out / g_outp * g_emis}

    else:

        allocated = {"output": alloc_out_total, "share": None, "cost": 0.0, "emis": 0.0}

        unallocated = {"output": unalloc_out, "share": None, "cost": g_cost, "emis": g_emis}

    unallocated.update(unalloc_components)

    shares = [d['accounts']['allocation_share'] for d in [dmd] + s['demand']['x']
              if d['total'] > 0 and 'accounts' in d]

    s['system'] = {
        "cost": g_cost,
        "output": g_outp,
        "emis": g_emis,
        "allocation_defined": bool(defined),
        "allocated_share_total": sum(shares) if defined else None,
        "allocated": allocated,
        "unallocated": unallocated,
        "surplus": {
            "electricity": float(np.sum(S_e)),
            "heat": heat_surplus_total,
            "spill": spill,
            "products": product_surplus,
            "unassigned_product_supply": unassigned_supply,
        },
    }

    # Output divides into allocated and unallocated by the electricity balance,
    # identically; a residual here means a flow is counted twice or not at all.
    # Where OUT is zero, allocated + unallocated must be zero too.

    check(checks, 'output_reconciliation', abs(alloc_out_total + unalloc_out - g_outp),
          recon_tol(max(abs(g_outp), abs(alloc_out_total) + abs(unalloc_out))))

    check(checks, 'cost_reconciliation', abs(allocated['cost'] + unallocated['cost'] - g_cost), recon_tol(g_cost))

    check(checks, 'emissions_reconciliation', abs(allocated['emis'] + unallocated['emis'] - g_emis), recon_tol(g_emis))

    if defined:

        commodity_cost = sum(d['accounts']['resource_cost'] for d in [dmd] + s['demand']['x']
                             if d['total'] > 0 and 'accounts' in d)

        check(checks, 'allocated_cost_reconciliation', abs(commodity_cost - allocated['cost']),
              recon_tol(g_cost))

    # The objective omits fixed charges on capacities fixed by the input.

    if objective is not None:

        fixed = 0.0

        for gen in s['generator']:

            if not u.capaSetToBeOptimised(gen['c_prod']):

                fixed += gen['c_prod'] * gen['fix_cost_prod']

        for flx in s['flex']:

            if not u.capaSetToBeOptimised(flx['c_strg']):

                fixed += flx['c_strg'] * flx['fix_cost_strg']

        for p2x in s['p2x']:

            if not u.capaSetToBeOptimised(p2x['c_prod']):

                fixed += p2x['c_prod'] * p2x['fix_cost_prod']

            if not u.capaSetToBeOptimised(p2x['c_strg']):

                fixed += p2x['c_strg'] * p2x['fix_cost_strg']

        lhs, rhs = g_cost + penalties, objective + fixed

        check(checks, 'objective_reconciliation', abs(lhs - rhs), recon_tol(max(abs(lhs), abs(rhs))))

    s['system']['checks'] = checks

    s['system']['accounting_ok'] = all(c['ok'] for c in checks.values())


def finish_checks(s):

    """Recompute the overall flag after later checks are added; report failures."""

    checks = s['system']['checks']

    s['system']['accounting_ok'] = all(c['ok'] for c in checks.values())

    for name, c in checks.items():

        if not c['ok']:

            log.warning('accounting check failed: %s (residual %r > tolerance %r)', name, c['residual'], c['tolerance'])