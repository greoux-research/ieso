#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u

import sys


def define(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solver vars & cons: generators (gen)

    for gen in s['generator']:

        # *_c_prod

        llim = gen['l_prod'][0]
        ulim = gen['l_prod'][1]

        if gen['c_prod'] < 0:

            # Capacity

            name = gen['iden'] + '_c_prod'
            gen['c_prod'] = glop.NumVar(llim, ulim, name)

            stat['capa'] += 1

        # *_e_prod_[i]

        for i in range(0, u.Y2H):

            # Electricity output

            name = gen['iden'] + '_e_prod_' + str(i)
            gen['e_prod'].append(glop.NumVar(llim, ulim, name))

            stat['outp'] += 1

        # set of constraints: generation is limited by capacity

        cf = u.cf_h(gen['profile'], gen['capacity_factor'])

        for i in range(0, u.Y2H):

            glop.Add(gen['e_prod'][i] <= cf[i] * gen['c_prod'])

            stat['cons'] += 1

        # if the generator is thermal
        # and if it is coupled to a thermal p2x

        if gen['type'] == 'elec + ther':

            gen['a'] = 0
            gen['b'] = 0

            # ---

            for p2x in s['p2x']:

                if p2x['type'] == 'elec + ther' and gen['iden'] in p2x['supply_sources']:

                    a, b, oops = u.thermo(gen['turbine_t_p'][0], gen['turbine_t_p'][1], gen['condenser_p'], p2x['temperature'])

                    if oops:

                        if u.Verbose:

                            print('\'' + gen['iden'] + '\' + \'' + p2x['iden'] + '\': The thermodynamic calculations were not successful')

                        sys.exit(1)

                    else:

                        gen['a'] = a
                        gen['b'] = b

                    break

            # ---

            if gen['a'] > 0 and gen['b'] > 0:

                # *_h_prod_[i]

                for i in range(0, u.Y2H):

                    # Heat output

                    name = gen['iden'] + '_h_prod_' + str(i)
                    gen['h_prod'].append(glop.NumVar(llim, ulim, name))

                    stat['outp'] += 1

                # co-generation constraints

                for i in range(0, u.Y2H):

                    glop.Add(gen['e_prod'][i] <= cf[i] *
                               gen['c_prod'] - gen['h_prod'][i] * gen['a'])
                    glop.Add(gen['h_prod'][i] <= cf[i]
                               * gen['c_prod'] * gen['b'])

                    stat['cons'] += 2

            else:

                gen['type'] = 'elec'

                gen['a'] = 0
                gen['b'] = 0
