#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser


from ies_optimiser import fcn as u


def define(glop, s, opts, stat, cfg):

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: demand (dmd)

    for dmd in s['demand']['x']:

        if dmd['total'] > 0:

            # --- x: non-served

            # Hourly demand first: unmet demand is bounded by it, so served
            # demand cannot go negative whatever l_ns or the penalty say.

            who = 'demand.x[' + dmd['iden'] + ']'

            dm = u.dm_h(dmd['profile'], dmd['total'], who, hours=cfg.hours, base=cfg.profile_base)

            bounds = u.shortfall_bounds(dm, dmd['l_ns'], who)

            dmd['output_ns'] = []

            for i in range(0, cfg.hours):

                name = dmd['iden'] + '_output_ns_' + str(i)
                dmd['output_ns'].append(glop.NumVar(bounds[i][0], bounds[i][1], name))

                stat['outp'] += 1

            # --- x: supply demand equilibrium

            dmd['__meet_dmnd'] = []

            for i in range(0, cfg.hours):

                dmd['__meet_dmnd'].append(glop.Constraint(dm[i], glop.infinity()))

                stat['cons'] += 1

                this_cons = dmd['__meet_dmnd'][len(dmd['__meet_dmnd']) - 1]

                for p2x in s['p2x']:

                    if p2x['iden'] in dmd['supply_sources']:

                        this_cons.SetCoefficient(p2x['x_supp'][i], +1)

                this_cons.SetCoefficient(dmd['output_ns'][i], +1)
