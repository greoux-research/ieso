#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u

import math


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

        # *_e_char_[i], *_e_strg_[i], *_e_disc_[i]

        for i in range(0, u.Y2H):

            # Charge rate

            name = flx['iden'] + '_e_char_' + str(i)
            flx['e_char'].append(glop.NumVar(llim, ulim, name))

            stat['outp'] += 1

            # MWh of electricity being stored at a given hour

            name = flx['iden'] + '_e_strg_' + str(i)
            flx['e_strg'].append(glop.NumVar(llim, ulim, name))

            # Discharge rate

            name = flx['iden'] + '_e_disc_' + str(i)
            flx['e_disc'].append(glop.NumVar(llim, ulim, name))

            stat['outp'] += 2

        # set of constraints: electricity stored, charged or discharged is limited by capacity

        for i in range(0, u.Y2H):

            glop.Add(flx['e_strg'][i] <= flx['c_strg'])

            glop.Add(flx['e_char'][i] <= flx['c_strg'] / flx['hours_of_storage'])

            glop.Add(flx['e_disc'][i] <= flx['c_strg'] / flx['hours_of_storage'])

            stat['cons'] += 3

        # set of constraints: storage modelling

        for i in range(0, u.Y2H):

            if i == 0:

                glop.Add(flx['e_strg'][i] == flx['soc_ini'] * flx['c_strg'] + flx['e_char'][i] * math.sqrt(flx['round_trip_efficiency']) - flx['e_disc'][i] / math.sqrt(flx['round_trip_efficiency']))

            else:

                glop.Add(flx['e_strg'][i] == flx['e_strg'][i - 1] + flx['e_char'][i] * math.sqrt(flx['round_trip_efficiency']) - flx['e_disc'][i] / math.sqrt(flx['round_trip_efficiency']))

            stat['cons'] += 1

        if u.Strg_end_eq_ini:

            glop.Add(flx['e_strg'][u.Y2H - 1] == flx['soc_ini'] * flx['c_strg'])

            stat['cons'] += 1
