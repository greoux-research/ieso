#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u


def define(Objective, s):

    # --- --- --- --- --- --- --- --- --- Objective function

    # --- generator

    for gen in s['generator']:

        if u.capaSetToBeOptimised(gen['c_prod']):

            Objective.SetCoefficient(gen['c_prod'], gen['fix_cost_prod'])

        for i in range(0, u.Y2H):

            Objective.SetCoefficient(gen['e_prod'][i], gen['var_cost_prod'])

            if gen['type'] == 'elec + ther':

                Objective.SetCoefficient(gen['h_prod'][i], gen['var_cost_prod'] * gen['a'])

    # --- flex

    for flx in s['flex']:

        if u.capaSetToBeOptimised(flx['c_strg']):

            Objective.SetCoefficient(flx['c_strg'], flx['fix_cost_strg'])

    # --- p2x /!\ excluding energy costs

    for p2x in s['p2x']:

        if u.capaSetToBeOptimised(p2x['c_strg']):

            Objective.SetCoefficient(p2x['c_strg'], p2x['fix_cost_strg'])

        if u.capaSetToBeOptimised(p2x['c_prod']):

            Objective.SetCoefficient(p2x['c_prod'], p2x['fix_cost_prod'])

        for i in range(0, u.Y2H):

            Objective.SetCoefficient(p2x['x_prod'][i], p2x['var_cost_prod'])

    # --- non-served e
    
    dmd = s['demand']['e']

    for i in range(0, u.Y2H):

        Objective.SetCoefficient(dmd['output_ns'][i], dmd['var_cost_ns'])

    # --- non-served x
    
    for dmd in s['demand']['x']:

        if dmd['total'] > 0:

            for i in range(0, u.Y2H):

                Objective.SetCoefficient(dmd['output_ns'][i], dmd['var_cost_ns'])
