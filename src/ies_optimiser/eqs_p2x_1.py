#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser


from ies_optimiser import fcn as u


def define(glop, s, opts, stat, cfg):

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

        for i in range(0, cfg.hours):

            # Amount of product X being stored at a given hour

            # Inventory is non-negative and limited by c_strg below; l_strg
            # bounds the installed storage capacity, not the hourly level.

            name = p2x['iden'] + '_x_strg_' + str(i)
            p2x['x_strg'].append(glop.NumVar(0, glop.infinity(), name))

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

        for i in range(0, cfg.hours):

            # Hourly production rate of product X

            # Production is limited by the capacity and availability relations
            # below. Delivery is not: it draws on the store, so it can exceed
            # the production rate, which is the whole point of holding one.
            # Both variables took their bounds from l_prod, so a bound set to
            # express a siting limit also capped the delivery rate, and a
            # positive lower bound forced a minimum production *and* a minimum
            # delivery in every hour.

            name = p2x['iden'] + '_x_prod_' + str(i)
            p2x['x_prod'].append(glop.NumVar(0, glop.infinity(), name))

            # Hourly supply rate of product X

            name = p2x['iden'] + '_x_supp_' + str(i)
            p2x['x_supp'].append(glop.NumVar(0, glop.infinity(), name))

            stat['outp'] += 2

        # set of constraints: production and storage is limited by capacity

        cf = u.cf_h(p2x['profile'], p2x['capacity_factor'], p2x['iden'], hours=cfg.hours, base=cfg.profile_base)

        for i in range(0, cfg.hours):

            glop.Add(p2x['x_prod'][i] <= cf[i] * p2x['c_prod'])
            glop.Add(p2x['x_strg'][i] <= p2x['c_strg'])

            stat['cons'] += 2

            # Nameplate, as for generators, and only where cf > 1.

            if cf[i] > 1.0:

                glop.Add(p2x['x_prod'][i] <= p2x['c_prod'])

                stat['cons'] += 1

        # set of constraints: storage modelling

        for i in range(0, cfg.hours):

            if i == 0:

                glop.Add(p2x['x_strg'][i] == p2x['soc_ini'] * p2x['c_strg'] + p2x['x_prod'][i] - p2x['x_supp'][i])

            else:

                glop.Add(p2x['x_strg'][i] == p2x['x_strg'][i - 1] + p2x['x_prod'][i] - p2x['x_supp'][i])

            stat['cons'] += 1

        if cfg.storage_closes_the_year:

            glop.Add(p2x['x_strg'][cfg.hours - 1] == p2x['soc_ini'] * p2x['c_strg'])

            stat['cons'] += 1
