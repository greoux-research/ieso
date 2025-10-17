#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u


def define(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: demand (dmd)

    for dmd in s['demand']['x']:

        if dmd['total'] > 0:

            # --- x: non-served

            dmd['output_ns'] = []

            llim = dmd['l_ns'][0]
            ulim = dmd['l_ns'][1]

            for i in range(0, u.Y2H):

                name = dmd['iden'] + '_output_ns_' + str(i)
                dmd['output_ns'].append(glop.NumVar(llim, ulim, name))

                stat['outp'] += 1

            # --- x: supply demand equilibrium

            dm = u.dm_h(dmd['profile'], dmd['total'])

            dmd['__meet_dmnd'] = []

            for i in range(0, u.Y2H):

                dmd['__meet_dmnd'].append(glop.Constraint(dm[i], glop.infinity()))

                stat['cons'] += 1

                this_cons = dmd['__meet_dmnd'][len(dmd['__meet_dmnd']) - 1]

                for p2x in s['p2x']:

                    if p2x['iden'] in dmd['supply_sources']:

                        this_cons.SetCoefficient(p2x['x_supp'][i], +1)

                this_cons.SetCoefficient(dmd['output_ns'][i], +1)
