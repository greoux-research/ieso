#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u

import math

import sys


def define(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: flex means (flx)

    for flx in s['flex']:

        # *_c_strg

        llim = flx['l_strg'][0]
        ulim = flx['l_strg'][1]

        if flx['c_strg'] < 0:

            # Storage capacity

            name = flx['iden'] + '_c_strg'
            flx['c_strg'] = glop.NumVar(llim, ulim, name)

            stat['capa'] += 1

        # natural inflow (reservoir hydro): exogenous energy entering the store

        inflow_total = flx.get('inflow_total', 0)

        has_inflow = inflow_total > 0

        if has_inflow:

            inflow = u.dm_h(flx.get('inflow_profile', ''), inflow_total)

            flx['e_spil'] = []

        # state of charge limits (fractions of c_strg)

        soc_min = flx.get('soc_min', 0.0)

        soc_max = flx.get('soc_max', 1.0)

        if not (0.0 <= soc_min <= soc_max <= 1.0):

            if u.Verbose:

                print('\'' + flx['iden'] + '\': soc_min and soc_max must satisfy 0 <= soc_min <= soc_max <= 1')

            sys.exit(1)

        if not (soc_min <= flx['soc_ini'] <= soc_max):

            if u.Verbose:

                print('\'' + flx['iden'] + '\': soc_ini must lie between soc_min and soc_max')

            sys.exit(1)

        # a store fed by natural inflow only (e.g. a dam) cannot be charged from the grid

        charge_allowed = flx.get('charge_allowed', True)

        char_ulim = ulim if charge_allowed else 0

        # *_e_char_[i], *_e_strg_[i], *_e_disc_[i]

        for i in range(0, u.Y2H):

            # Charge rate

            name = flx['iden'] + '_e_char_' + str(i)
            flx['e_char'].append(glop.NumVar(llim, char_ulim, name))

            stat['outp'] += 1

            # MWh of electricity being stored at a given hour

            name = flx['iden'] + '_e_strg_' + str(i)
            flx['e_strg'].append(glop.NumVar(llim, ulim, name))

            # Discharge rate

            name = flx['iden'] + '_e_disc_' + str(i)
            flx['e_disc'].append(glop.NumVar(llim, ulim, name))

            stat['outp'] += 2

            if has_inflow:

                # Spilled inflow (water released without generating)

                name = flx['iden'] + '_e_spil_' + str(i)
                flx['e_spil'].append(glop.NumVar(0, ulim, name))

                stat['outp'] += 1

        # set of constraints: electricity stored, charged or discharged is limited by capacity

        for i in range(0, u.Y2H):

            if soc_max < 1.0:

                glop.Add(flx['e_strg'][i] <= soc_max * flx['c_strg'])

            else:

                glop.Add(flx['e_strg'][i] <= flx['c_strg'])

            if soc_min > 0.0:

                glop.Add(flx['e_strg'][i] >= soc_min * flx['c_strg'])

                stat['cons'] += 1

            glop.Add(flx['e_char'][i] <= flx['c_strg'] / flx['hours_of_storage'])

            glop.Add(flx['e_disc'][i] <= flx['c_strg'] / flx['hours_of_storage'])

            stat['cons'] += 3

        # set of constraints: storage modelling

        for i in range(0, u.Y2H):

            if i == 0:

                _prev = flx['soc_ini'] * flx['c_strg']

            else:

                _prev = flx['e_strg'][i - 1]

            _flow = flx['e_char'][i] * math.sqrt(flx['round_trip_efficiency']) - flx['e_disc'][i] / math.sqrt(flx['round_trip_efficiency'])

            if has_inflow:

                # inflow enters the store directly: it is not subject to the round-trip penalty

                glop.Add(flx['e_strg'][i] == _prev + inflow[i] - flx['e_spil'][i] + _flow)

            else:

                glop.Add(flx['e_strg'][i] == _prev + _flow)

            stat['cons'] += 1

        if u.Strg_end_eq_ini:

            glop.Add(flx['e_strg'][u.Y2H - 1] == flx['soc_ini'] * flx['c_strg'])

            stat['cons'] += 1
