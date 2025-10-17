#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u


def define(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: power-to-x (p2x) [2] // Heat supply constraints

    for p2x in s['p2x']:

        if p2x['type'] == 'elec + ther' and len(p2x['supply_sources']) > 0:

            p2x['__meet_dmnd'] = []

            for i in range(0, u.Y2H):

                p2x['__meet_dmnd'].append(glop.Constraint(0, glop.infinity()))

                stat['cons'] += 1

                this_cons = p2x['__meet_dmnd'][len(p2x['__meet_dmnd']) - 1]

                this_cons.SetCoefficient(p2x['x_prod'][i], -1 * p2x['pow_use_ther_prod'])

                for gen in s['generator']:

                    if gen['iden'] in p2x['supply_sources']:

                        this_cons.SetCoefficient(gen['h_prod'][i], +1)
