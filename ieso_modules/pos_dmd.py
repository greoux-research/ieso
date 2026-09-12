#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import numpy as np

from ieso_modules import fcn as u


def accounts(prop, g_cost, g_emis, total, ns_sum, var_cost_ns):

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


def g_figs(s):

    # --- --- --- --- --- --- --- --- --- Global figures

    # --- global electricity generation figure /!\ excluding non-served e

    g_outp = 0.0

    # g_outp  = sum of ( gen['e_prod'] + gen['h_prod'] * gen['a'] ) across technologies and hours
    # g_outp += sum of ( flx['e_disc'] - flx['e_char'] ) across technologies and hours

    # --- generator

    for gen in s['generator']:

        for i in range(0, u.Y2H):

            g_outp += gen['e_prod'][i].solution_value()

            if gen['type'] == 'elec + ther':

                g_outp += gen['h_prod'][i].solution_value() * gen['a']

    # --- flex

    for flx in s['flex']:

        for i in range(0, u.Y2H):

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

        for i in range(0, u.Y2H):

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

        for i in range(0, u.Y2H):

            g_cost += p2x['x_prod'][i].solution_value() * p2x['var_cost_prod']

    # --- global emissions figure

    g_emis = 0.0

    for gen in s['generator']:

        for i in range(0, u.Y2H):

            g_emis += gen['e_prod'][i].solution_value() * gen['var_emis_prod']

            if gen['type'] == 'elec + ther':

                g_emis += gen['h_prod'][i].solution_value() * gen['var_emis_prod'] * gen['a']

    # --- finish line

    return g_outp, g_cost, g_emis


def demand_props(s, opts, emis_con, nspo_con):


    # --- --- --- --- --- --- --- --- --- Assign costs and emissions to e & x


    # === === === === === === === === ===

    g_outp, g_cost, g_emis = g_figs(s)


    # === === === === === === === === ===

    # e demand actually served
    # s['demand']['e']['total'] - sum of ( s['demand']['e']['output_ns'] ) across hours

    dmd = s['demand']['e']

    e_demand_actually_served = dmd['total']

    for i in range(0, u.Y2H):

        e_demand_actually_served -= dmd['output_ns'][i].solution_value()


    # === === === === === === === === ===

    # x demand actually served
    # electricity consumption of PtX processes

    x_demand_actually_served = {}

    for dmd in s['demand']['x']:

        commodity = dmd['iden']

        demand_actually_served = 0

        for p2x in s['p2x']:

            if p2x['iden'] in dmd['supply_sources']:  # PtX processes meeting the demand for X

                # electricity

                for i in range(0, u.Y2H):

                    demand_actually_served += p2x['x_prod'][i].solution_value() * p2x['pow_use_elec_prod']

                # heat
                #
                # Attribute the heat actually dispatched by each supplier, converted
                # to electricity-equivalent by that supplier's own coefficient 'a'.
                # Adding the process's whole heat requirement once per eligible
                # supplier counts the same heat len(supply_sources) times over.
                #
                # This is exact only while a generator's heat serves a single
                # process; shared-source topologies are rejected up front because
                # the formulation cannot apportion heat between consumers.

                if p2x['type'] == 'elec + ther' and len(p2x['supply_sources']) > 0:

                    for gen in s['generator']:

                        if gen['iden'] in p2x['supply_sources'] and gen['type'] == 'elec + ther':

                            for i in range(0, u.Y2H):

                                demand_actually_served += gen['h_prod'][i].solution_value() * gen['a']

        x_demand_actually_served[commodity] = demand_actually_served


    # === === === === === === === === ===

    _sum_prop = 0


    # === === === === === === === === ===

    dmd = s['demand']['e']

    dmd['shadow_prices'] = {
        "demand_match": [],
        "carbon_cap": -1,
        "reliability_cap": -1
    }

    dmd['kpis'] = {
        "cost": -1, # "cost": [-1, -1]
        "emis": -1,
        "reli": -1
    }

    # --- dmd['output_ns']

    rows = []

    for i in range(0, u.Y2H):

        rows.append(dmd['output_ns'][i].solution_value())

    dmd['output_ns'] = rows

    # --- dmd['shadow_prices']

    rows = []

    for i in range(0, u.Y2H):

        rows.append(dmd['__meet_dmnd'][i].dual_value())

    dmd['shadow_prices']['demand_match'] = rows

    if "carbon-constraint" in opts:

        _value, _detail = cap_report(emis_con, dmd['total'] * opts["carbon-constraint"], g_emis)

        dmd['shadow_prices']['carbon_cap'] = _value
        dmd['shadow_prices']['carbon_cap_detail'] = _detail

    if "non-served-power-constraint" in opts:

        _value, _detail = cap_report(nspo_con,
                                     dmd['total'] * opts["non-served-power-constraint"],
                                     float(np.sum(dmd['output_ns'])))

        dmd['shadow_prices']['reliability_cap'] = _value
        dmd['shadow_prices']['reliability_cap_detail'] = _detail

    # --- dmd['kpis']

    if dmd['total'] > 0:

        _ns_sum = float(np.sum(dmd['output_ns']))
        _prop = e_demand_actually_served / g_outp if g_outp > 0 else None

        dmd['accounts'] = accounts(_prop, g_cost, g_emis, dmd['total'], _ns_sum, dmd['var_cost_ns'])

        if g_outp > 0:

            _cost_1 = (_prop * g_cost + _ns_sum * dmd['var_cost_ns']) / dmd['total']
            _emis = _prop * g_emis / dmd['total']
            _reli = _ns_sum / dmd['total']

            dmd['kpis'] = {
                "cost": _cost_1, # [_cost_0, _cost_1],
                "emis": _emis,
                "reli": 1.0 - _reli
            }

            _sum_prop += _prop


    # === === === === === === === === ===

    for dmd in s['demand']['x']:

        dmd['shadow_prices'] = {
            "demand_match": []
        }

        dmd['kpis'] = {
            "cost": -1, # "cost": [-1, -1]
            "emis": -1,
            "reli": -1
        }

        if dmd['total'] > 0:

            commodity = dmd['iden']

            # --- dmd['output_ns']

            rows = []

            for i in range(0, u.Y2H):

                rows.append(dmd['output_ns'][i].solution_value())

            dmd['output_ns'] = rows

            # --- dmd['shadow_prices']

            rows = []

            for i in range(0, u.Y2H):

                rows.append(dmd['__meet_dmnd'][i].dual_value())

            dmd['shadow_prices']['demand_match'] = rows

            # --- dmd['kpis']

            _ns_sum = float(np.sum(dmd['output_ns']))
            _prop = x_demand_actually_served[commodity] / g_outp if g_outp > 0 else None

            dmd['accounts'] = accounts(_prop, g_cost, g_emis, dmd['total'], _ns_sum, dmd['var_cost_ns'])

            if g_outp > 0:

                _cost_1 = (_prop * g_cost + _ns_sum * dmd['var_cost_ns']) / dmd['total']
                _emis = _prop * g_emis / dmd['total']
                _reli = _ns_sum / dmd['total']

                dmd['kpis'] = {
                    "cost": _cost_1, # [_cost_0, _cost_1],
                    "emis": _emis,
                    "reli": 1.0 - _reli
                }

                _sum_prop += _prop


    # === === === === === === === === ===

    # System totals, reported directly rather than through the allocation.

    s['system'] = {
        "cost": g_cost,
        "output": g_outp,
        "emis": g_emis,
        "allocated_share_total": _sum_prop,
    }

    # Every unit of electricity-equivalent output is allocated to exactly one
    # demand, so the shares must sum to one. A residual means output is being
    # counted more than once, or not at all — the condition this check exists to
    # catch. The threshold it previously carried, 1e+9, could never be exceeded.

    if abs(_sum_prop - 1) > u.Balance_atol + u.Balance_rtol * max(abs(_sum_prop), 1.0):

        if u.Verbose:

            print('allocation shares do not sum to one:', _sum_prop)
