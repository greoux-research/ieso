#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u


def define(glop, s, opts, stat):

    dmd = s['demand']['e']

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: demand (dmd) for e

    dmd['output_ns'] = []

    llim = dmd['l_ns'][0]
    ulim = dmd['l_ns'][1]

    for i in range(0, u.Y2H):

        name = dmd['iden'] + '_output_ns_' + str(i)
        dmd['output_ns'].append(glop.NumVar(llim, ulim, name))

        stat['outp'] += 1

    # --- --- --- --- --- --- --- --- --- Matching the demand for e

    dm = u.dm_h(dmd['profile'], dmd['total'])

    dmd['__meet_dmnd'] = []

    for i in range(0, u.Y2H):

        dmd['__meet_dmnd'].append(glop.Constraint(dm[i], glop.infinity()))

        stat['cons'] += 1

        this_cons = dmd['__meet_dmnd'][len(dmd['__meet_dmnd']) - 1]

        for p2x in s['p2x']:

            this_cons.SetCoefficient(p2x['x_prod'][i], -1 * p2x['pow_use_elec_prod'])

        for gen in s['generator']:

            this_cons.SetCoefficient(gen['e_prod'][i], +1)

        for flx in s['flex']:

            this_cons.SetCoefficient(flx['e_char'][i], -1)

            this_cons.SetCoefficient(flx['e_disc'][i], +1)

        this_cons.SetCoefficient(dmd['output_ns'][i], +1)

    # --- --- --- --- --- --- --- --- --- Additional constraints

    emis_con = -1
    nspo_con = -1

    # --- --- --- --- --- --- --- --- --- Emissions constraint

    if "carbon-constraint" in opts:

        emis_cap = opts["carbon-constraint"]  # kg CO2 per MWh

        totl_dmd = dmd['total']

        emis_con = glop.Constraint(0, totl_dmd * emis_cap)

        stat['cons'] += 1

        for gen in s['generator']:

            for i in range(0, u.Y2H):

                emis_con.SetCoefficient(gen['e_prod'][i], +1 * gen['var_emis_prod'])

                if gen['type'] == 'elec + ther':

                    emis_con.SetCoefficient(gen['h_prod'][i], +1 * gen['a'] * gen['var_emis_prod'])


    # --- --- --- --- --- --- --- --- --- Nxon-served power constraint

    if "non-served-power-constraint" in opts:

        max_fraction = opts["non-served-power-constraint"] # % of total demand

        totl_dmd = dmd['total']

        nspo_con = glop.Constraint(0, totl_dmd * max_fraction)

        stat['cons'] += 1

        for i in range(0, u.Y2H):

            nspo_con.SetCoefficient(dmd['output_ns'][i], +1)

    return emis_con, nspo_con
