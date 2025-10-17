#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u


def define(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: power-to-x (p2x) [1]

    for p2x in s['p2x']:

        # *_c_strg

        llim = p2x['l_strg'][0]
        ulim = p2x['l_strg'][1]

        if p2x['c_strg'] < 0:

            # Storage capacity

            name = p2x['iden'] + '_c_strg'
            p2x['c_strg'] = glop.NumVar(llim, ulim, name)

            stat['capa'] += 1

        # *_x_strg_[i]

        for i in range(0, u.Y2H):

            # Amount of product X being stored at a given hour

            name = p2x['iden'] + '_x_strg_' + str(i)
            p2x['x_strg'].append(glop.NumVar(llim, ulim, name))

            stat['outp'] += 1

        # *_c_prod

        llim = p2x['l_prod'][0]
        ulim = p2x['l_prod'][1]

        if p2x['c_prod'] < 0:

            # Production capacity

            name = p2x['iden'] + '_c_prod'
            p2x['c_prod'] = glop.NumVar(llim, ulim, name)

            stat['capa'] += 1

        # *_x_prod_[i], *_x_supp_[i]

        for i in range(0, u.Y2H):

            # Hourly production rate of product X

            name = p2x['iden'] + '_x_prod_' + str(i)
            p2x['x_prod'].append(glop.NumVar(llim, ulim, name))

            # Hourly supply rate of product X

            name = p2x['iden'] + '_x_supp_' + str(i)
            p2x['x_supp'].append(glop.NumVar(llim, ulim, name))

            stat['outp'] += 2

        # set of constraints: production and storage is limited by capacity

        cf = u.cf_h(p2x['profile'], p2x['capacity_factor'])

        for i in range(0, u.Y2H):

            glop.Add(p2x['x_prod'][i] <= cf[i] * p2x['c_prod'])
            glop.Add(p2x['x_strg'][i] <= p2x['c_strg'])

            stat['cons'] += 2

        # set of constraints: storage modelling

        for i in range(0, u.Y2H):

            if i == 0:

                glop.Add(p2x['x_strg'][i] == p2x['soc_ini'] * p2x['c_strg'] + p2x['x_prod'][i] - p2x['x_supp'][i])

            else:

                glop.Add(p2x['x_strg'][i] == p2x['x_strg'][i - 1] + p2x['x_prod'][i] - p2x['x_supp'][i])

            stat['cons'] += 1

        if u.Strg_end_eq_ini:

            glop.Add(p2x['x_strg'][u.Y2H - 1] == p2x['soc_ini'] * p2x['c_strg'])

            stat['cons'] += 1
