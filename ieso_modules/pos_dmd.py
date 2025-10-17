#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import numpy as np

from ieso_modules import fcn as u


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

                if p2x['type'] == 'elec + ther' and len(p2x['supply_sources']) > 0:

                    for gen in s['generator']:

                        if gen['iden'] in p2x['supply_sources']:

                            for i in range(0, u.Y2H):

                                demand_actually_served += p2x['x_prod'][i].solution_value() * p2x['pow_use_ther_prod'] * gen['a']

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

        dmd['shadow_prices']['carbon_cap'] = emis_con.dual_value() * -1.0

    if "non-served-power-constraint" in opts:

        dmd['shadow_prices']['reliability_cap'] = nspo_con.dual_value() * -1.0

    # --- dmd['kpis']

    if dmd['total'] > 0 and g_outp > 0:

        _prop = e_demand_actually_served / g_outp
        _cost_0 = _prop * g_cost / dmd['total']
        _cost_1 = (_prop * g_cost + np.sum(dmd['output_ns']) * dmd['var_cost_ns']) / dmd['total']
        _emis = _prop * g_emis / dmd['total']
        _reli = np.sum(dmd['output_ns']) / dmd['total']

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

            if g_outp > 0:

                _prop = x_demand_actually_served[commodity] / g_outp
                _cost_0 = _prop * g_cost / dmd['total']
                _cost_1 = (_prop * g_cost + np.sum(dmd['output_ns']) * dmd['var_cost_ns']) / dmd['total']
                _emis = _prop * g_emis / dmd['total']
                _reli = np.sum(dmd['output_ns']) / dmd['total']

                dmd['kpis'] = {
                    "cost": _cost_1, # [_cost_0, _cost_1],
                    "emis": _emis,
                    "reli": 1.0 - _reli
                }

                _sum_prop += _prop


    # === === === === === === === === ===

    if u.Verbose:

        if abs(_sum_prop - 1) > 1e+9:

            print('_sum_prop', _sum_prop)
