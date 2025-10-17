#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import numpy as np

from ieso_modules import pos_dmd

from ieso_modules import fcn as u


def process(glop, s, opts, stat, emis_con, nspo_con):


    # --- --- --- --- --- --- --- --- --- Post processing


    # --- dmd

    pos_dmd.demand_props(s, opts, emis_con, nspo_con)


    # --- gen

    for gen in s['generator']:

        # --- gen['c_prod']

        if u.capaSetToBeOptimised(gen['c_prod']):

            gen['c_prod'] = gen['c_prod'].solution_value()

        # --- gen['e_prod']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(gen['e_prod'][i].solution_value())

        gen['e_prod'] = rows

        # --- gen['h_prod']

        if gen['type'] == 'elec + ther':

            rows = []

            for i in range(0, u.Y2H):

                rows.append(gen['h_prod'][i].solution_value())

            gen['h_prod'] = rows


    # --- flx

    for flx in s['flex']:

        # --- flx['c_strg']

        if u.capaSetToBeOptimised(flx['c_strg']):

            flx['c_strg'] = flx['c_strg'].solution_value()

        # --- flx['e_strg']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(flx['e_strg'][i].solution_value())

        flx['e_strg'] = rows

        # --- flx['e_char']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(flx['e_char'][i].solution_value())

        flx['e_char'] = rows

        # --- flx['e_disc']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(flx['e_disc'][i].solution_value())

        flx['e_disc'] = rows

        # --- checks

        if (flx['c_strg'] > 0) and u.Verbose:

            _rte = np.sum(flx['e_disc']) / np.sum(flx['e_char'])

            if abs(_rte - flx['round_trip_efficiency']) > 1e+9:

                print('_rte', flx['iden'], _rte)


    # --- p2x

    for p2x in s['p2x']:

        # --- p2x['c_prod']

        if u.capaSetToBeOptimised(p2x['c_prod']):

            p2x['c_prod'] = p2x['c_prod'].solution_value()

        # --- p2x['x_prod']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(p2x['x_prod'][i].solution_value())

        p2x['x_prod'] = rows

        # --- p2x['c_strg']

        if u.capaSetToBeOptimised(p2x['c_strg']):

            p2x['c_strg'] = p2x['c_strg'].solution_value()

        # --- p2x['x_strg']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(p2x['x_strg'][i].solution_value())

        p2x['x_strg'] = rows

        # --- p2x['x_supp']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(p2x['x_supp'][i].solution_value())

        p2x['x_supp'] = rows


    # --- purge non-serializable solver objects before dumping JSON

    for p in s['p2x']:

        p.pop('__meet_dmnd', None)

    s['demand']['e'].pop('__meet_dmnd', None)

    for dx in s['demand']['x']:

        dx.pop('__meet_dmnd', None)
