#!/usr/bin/python
# -*- coding: utf-8 -*-
# Gréoux Research - www.greoux.re


import time
import os
import sys
import json

from datetime import datetime
import numpy as np

from ortools.linear_solver import pywraplp

import u as u

import math


# ---

Y2H = 8760

Threshold = 1e-3


# ---

def capacity_factor(profile, profile_upper_limit):

    cf = []

    if profile == '':

        cf = np.full(8760, profile_upper_limit).tolist()

    else:

        data, s, n, m, oops = u.read(profile)

        if len(data) != 8760 or n or oops:

            print('Error loading \'' + profile + '\'')

            sys.exit()

        for k in range(0, len(data)):

            cf.append(profile_upper_limit * data[k] / m)

    return cf


# ---

def demand(profile, profile_upper_limit, total):

    sum_1Y = profile_upper_limit * total

    cf = []

    if profile == '':

        cf = np.full(8760, sum_1Y / 8760).tolist()

    else:

        data, s, n, m, oops = u.read(profile)

        if len(data) != 8760 or n or oops:

            print('Error loading \'' + profile + '\'')

            sys.exit()

        for k in range(0, len(data)):

            cf.append(sum_1Y * data[k] / s)

    return cf


# ---

stat_time_1 = time.time()
stat_time_2 = 0
stat_time = 0

stat_capa = 0
stat_outp = 0
stat_cons = 0


# ---

Solver = pywraplp.Solver.CreateSolver('GLOP')
Objective = Solver.Objective()
Objective.SetMinimization()


# ---

if len(sys.argv) < 2:

    print('Examples of a correct command line: \'python ieso.py input.json\' & \'python ieso.py input.json 100\'')
    sys.exit()


# ---

s = {}

try:

    f_j = open(sys.argv[1], 'r')
    jobj = json.load(f_j)
    f_j.close()

    s = jobj

except:

    print('Could not load \'' + sys.argv[1] + '\'')

    sys.exit()


# ---

print(sys.argv)


# ---

for p2x in s['p2x']:

    # *_c_strg

    llim = p2x['l_strg'][0]
    ulim = p2x['l_strg'][1]

    if p2x['c_strg'] < 0:

        name = p2x['iden'] + '_c_strg'
        p2x['c_strg'] = Solver.NumVar(llim, ulim, name)

        stat_capa += 1

    # *_x_strg_[i]

    for i in range(0, Y2H):

        name = p2x['iden'] + '_x_strg_' + str(i)
        p2x['x_strg'].append(Solver.NumVar(llim, ulim, name))

        stat_outp += 1

    # *_c_prod

    llim = p2x['l_prod'][0]
    ulim = p2x['l_prod'][1]

    if p2x['c_prod'] < 0:

        name = p2x['iden'] + '_c_prod'
        p2x['c_prod'] = Solver.NumVar(llim, ulim, name)

        stat_capa += 1

    # *_x_prod_[i], *_x_supp_[i]

    for i in range(0, Y2H):

        name = p2x['iden'] + '_x_prod_' + str(i)
        p2x['x_prod'].append(Solver.NumVar(llim, ulim, name))

        name = p2x['iden'] + '_x_supp_' + str(i)
        p2x['x_supp'].append(Solver.NumVar(llim, ulim, name))

        stat_outp += 2

    # set of constraints: generation is limited by capacity

    cf = capacity_factor(p2x['profile'], p2x['profile_upper_limit'])

    for i in range(0, Y2H):

        Solver.Add(p2x['x_prod'][i] <= cf[i] * p2x['c_prod'])
        Solver.Add(p2x['x_strg'][i] <= p2x['c_strg'])

        stat_cons += 2  # supply is only limited by the quantity of x being stored

    # set of constraints: storage modelling

    for i in range(0, Y2H):

        if i == 0:

            Solver.Add(p2x['x_strg'][i] == 0.5 * p2x['c_strg'] + p2x['x_prod'][i] - p2x['x_supp'][i])

        else:

            Solver.Add(p2x['x_strg'][i] == p2x['x_strg'][i - 1] + p2x['x_prod'][i] - p2x['x_supp'][i])

        stat_cons += 1

    Solver.Add(p2x['x_strg'][Y2H - 1] == 0.5 * p2x['c_strg'])

    stat_cons += 1


# ---

for gen in s['generator']:

    # *_c_prod

    llim = gen['l_prod'][0]
    ulim = gen['l_prod'][1]

    if gen['c_prod'] < 0:

        name = gen['iden'] + '_c_prod'
        gen['c_prod'] = Solver.NumVar(llim, ulim, name)

        stat_capa += 1

    # *_e_prod_[i]

    for i in range(0, Y2H):

        name = gen['iden'] + '_e_prod_' + str(i)
        gen['e_prod'].append(Solver.NumVar(llim, ulim, name))

        stat_outp += 1

    # set of constraints: generation is limited by capacity

    cf = capacity_factor(gen['profile'], gen['profile_upper_limit'])

    for i in range(0, Y2H):

        Solver.Add(gen['e_prod'][i] <= cf[i] * gen['c_prod'])

        stat_cons += 1

    # if the generator is thermal
    # and if it is coupled to a thermal p2x

    if gen['type'] == 'elec + ther':

        for p2x in s['p2x']:

            if p2x['type'] == 'elec + ther' and gen['iden'] in p2x['supply_sources']:

                a, b, oops = u.thermo(gen['turbine_t_p'][0], gen['turbine_t_p'][1], gen['condenser_p'], p2x['temperature'])

                if oops:

                    print('\'' + gen['iden'] + '\' + \'' + p2x['iden'] + '\': The thermodynamic calculations were not successful')

                    sys.exit()

                else:

                    gen['a'] = a
                    gen['b'] = b

                break

        if gen['a'] > 0 and gen['b'] > 0:

            # *_h_prod_[i]

            for i in range(0, Y2H):

                name = gen['iden'] + '_h_prod_' + str(i)
                gen['h_prod'].append(Solver.NumVar(llim, ulim, name))

                stat_outp += 1

            # set of constraints: co-generation

            for i in range(0, Y2H):

                Solver.Add(gen['e_prod'][i] <= cf[i] * gen['c_prod'] - gen['h_prod'][i] * gen['a'])
                Solver.Add(gen['h_prod'][i] <= cf[i] * gen['c_prod'] * gen['b'])

                stat_cons += 2

        else:

            gen['type'] = 'elec'

            gen['a'] = 0
            gen['b'] = 0


# ---

for p2x in s['p2x']:

    if p2x['type'] == 'elec + ther' and len(p2x['supply_sources']) > 0:

        p2x['price'] = []

        for i in range(0, Y2H):

            p2x['price'].append(Solver.Constraint(0, Solver.infinity()))

            stat_cons += 1

            this_cons = p2x['price'][len(p2x['price']) - 1]

            this_cons.SetCoefficient(p2x['x_prod'][i], -1 * p2x['pow_use_ther_prod'])

            for src in p2x['supply_sources']:

                for gen in s['generator']:

                    if src == gen['iden']:

                        this_cons.SetCoefficient(gen['h_prod'][i], +1)

                        break


# ---

for flx in s['flex']:

    # *_c_strg

    llim = flx['l_strg'][0]
    ulim = flx['l_strg'][1]

    if flx['c_strg'] < 0:

        name = flx['iden'] + '_c_strg'
        flx['c_strg'] = Solver.NumVar(llim, ulim, name)

        stat_capa += 1

    # *_e_char_[i], *_e_strg_[i], *_e_disc_[i]

    for i in range(0, Y2H):

        if flx['type'] != 'hdam':

            name = flx['iden'] + '_e_char_' + str(i)
            flx['e_char'].append(Solver.NumVar(llim, ulim, name))

            stat_outp += 1

        name = flx['iden'] + '_e_strg_' + str(i)
        flx['e_strg'].append(Solver.NumVar(llim, ulim, name))

        name = flx['iden'] + '_e_disc_' + str(i)
        flx['e_disc'].append(Solver.NumVar(llim, ulim, name))

        stat_outp += 2

    if flx['type'] == 'hdam':

        cf = capacity_factor(flx['profile'], flx['profile_upper_limit'])

        for i in range(0, Y2H):

            flx['e_char'].append(cf[i] * flx['c_strg'] / flx['hours_of_storage'])

    # set of constraints: generation is limited by capacity

    for i in range(0, Y2H):

        if flx['type'] != 'hdam':

            Solver.Add(flx['e_char'][i] <= flx['c_strg'] / flx['hours_of_storage'])

            stat_cons += 1

        Solver.Add(flx['e_strg'][i] <= flx['c_strg'])

        Solver.Add(flx['e_disc'][i] <= flx['c_strg'] / flx['hours_of_storage'])

        stat_cons += 2

    # set of constraints: storage modelling

    for i in range(0, Y2H):

        if i == 0:

            Solver.Add(flx['e_strg'][i] == 0.5 * flx['c_strg'] + flx['e_char'][i] * math.sqrt(flx['round_trip_efficiency']) - flx['e_disc'][i] / math.sqrt(flx['round_trip_efficiency']))

        else:

            Solver.Add(flx['e_strg'][i] == flx['e_strg'][i - 1] + flx['e_char'][i] * math.sqrt(flx['round_trip_efficiency']) - flx['e_disc'][i] / math.sqrt(flx['round_trip_efficiency']))

        stat_cons += 1

    Solver.Add(flx['e_strg'][Y2H - 1] == 0.5 * flx['c_strg'])

    stat_cons += 1


# --- electricity: non-served

dmd = s['demand']['e']

dmd['output_ns'] = []

llim = dmd['l_ns'][0]
ulim = dmd['l_ns'][1]

for i in range(0, Y2H):

    name = dmd['iden'] + '_output_ns_' + str(i)
    dmd['output_ns'].append(Solver.NumVar(llim, ulim, name))

    stat_outp += 1


# --- electricity: supply demand equilibrium

dm = demand(dmd['profile'], dmd['profile_upper_limit'], dmd['total'])

dmd['price'] = []

for i in range(0, Y2H):

    dmd['price'].append(Solver.Constraint(dm[i], Solver.infinity()))

    stat_cons += 1

    this_cons = dmd['price'][len(dmd['price']) - 1]

    for p2x in s['p2x']:

        this_cons.SetCoefficient(p2x['x_prod'][i], -1 * p2x['pow_use_elec_prod'])

    for gen in s['generator']:

        this_cons.SetCoefficient(gen['e_prod'][i], +1)

    for flx in s['flex']:

        if flx['type'] != 'hdam':

            this_cons.SetCoefficient(flx['e_char'][i], -1)

        this_cons.SetCoefficient(flx['e_disc'][i], +1)

    this_cons.SetCoefficient(dmd['output_ns'][i], +1)


# --- x

for dmd in s['demand']['x']:

    if dmd['total'] > 0:

        # --- x: non-served

        dmd['output_ns'] = []

        llim = dmd['l_ns'][0]
        ulim = dmd['l_ns'][1]

        for i in range(0, Y2H):

            name = dmd['iden'] + '_output_ns_' + str(i)
            dmd['output_ns'].append(Solver.NumVar(llim, ulim, name))

            stat_outp += 1

        # --- x: supply demand equilibrium

        dm = demand(dmd['profile'], dmd['profile_upper_limit'], dmd['total'])

        dmd['price'] = []

        for i in range(0, Y2H):

            dmd['price'].append(Solver.Constraint(dm[i], Solver.infinity()))

            stat_cons += 1

            this_cons = dmd['price'][len(dmd['price']) - 1]

            for p2x in s['p2x']:

                if p2x['iden'] in dmd['supply_sources']:

                    this_cons.SetCoefficient(p2x['x_supp'][i], +1)

            this_cons.SetCoefficient(dmd['output_ns'][i], +1)


# --- emissions constraint

if len(sys.argv) >= 3:

    dmd = s['demand']['e']

    emis_cap = float(sys.argv[2])

    totl_dmd = 0

    totl_dmd += dmd['total']

    emis_con = Solver.Constraint(0, totl_dmd * emis_cap)

    stat_cons += 1

    for gen in s['generator']:

        if gen['var_emis_prod'] > 0:

            for i in range(0, Y2H):

                emis_con.SetCoefficient(gen['e_prod'][i], +1 * gen['var_emis_prod'])

                if gen['type'] == 'elec + ther':

                    emis_con.SetCoefficient(gen['h_prod'][i], +1 * gen['a'] * gen['var_emis_prod'])

    if dmd['var_emis_ns'] > 0:

        for i in range(0, Y2H):

            emis_con.SetCoefficient(dmd['output_ns'][i], +1 * dmd['var_emis_ns'])


# --- objective function

for p2x in s['p2x']:

    if not u.isFloat(p2x['c_strg']):

        Objective.SetCoefficient(p2x['c_strg'], p2x['fix_cost_strg'])

    if not u.isFloat(p2x['c_prod']):

        Objective.SetCoefficient(p2x['c_prod'], p2x['fix_cost_prod'])

    for i in range(0, Y2H):

        Objective.SetCoefficient(p2x['x_prod'][i], p2x['var_cost_prod'])

for gen in s['generator']:

    if not u.isFloat(gen['c_prod']):

        Objective.SetCoefficient(gen['c_prod'], gen['fix_cost_prod'])

    for i in range(0, Y2H):

        Objective.SetCoefficient(gen['e_prod'][i], gen['var_cost_prod'])

        if gen['type'] == 'elec + ther':

            Objective.SetCoefficient(gen['h_prod'][i], gen['var_cost_prod'] * gen['a'])

for flx in s['flex']:

    if not u.isFloat(flx['c_strg']):

        Objective.SetCoefficient(flx['c_strg'], flx['fix_cost_strg'])

dmd = s['demand']['e']

for i in range(0, Y2H):

    Objective.SetCoefficient(dmd['output_ns'][i], dmd['var_cost_ns'])

for dmd in s['demand']['x']:

    if dmd['total'] > 0:

        for i in range(0, Y2H):

            Objective.SetCoefficient(dmd['output_ns'][i], dmd['var_cost_ns'])


# --- optimise

if Solver.Solve() == pywraplp.Solver.OPTIMAL:


    # --- success

    s['solver']['stat_succ'] = 1


    # --- gen

    for gen in s['generator']:

        # ---

        c_prod = 0

        if not u.isFloat(gen['c_prod']):

            c_prod = gen['c_prod'].solution_value()

            if abs(c_prod) < Threshold:

                gen['c_prod'] = -1

            else:

                gen['c_prod'] = c_prod

        else:

            c_prod = gen['c_prod']

        # ---

        if abs(c_prod) < Threshold:

            gen['e_prod'] = []
            gen['h_prod'] = []

        else:

            # ---

            rows = []

            for i in range(0, Y2H):

                rows.append(gen['e_prod'][i].solution_value())

            if sum(rows) < Threshold:

                gen['e_prod'] = []

            else:

                gen['e_prod'] = rows

            # ---

            if gen['type'] == 'elec + ther':

                rows = []

                for i in range(0, Y2H):

                    rows.append(gen['h_prod'][i].solution_value())

                if sum(rows) < Threshold:

                    gen['h_prod'] = []

                else:

                    gen['h_prod'] = rows


    # --- flx

    for flx in s['flex']:

        # ---

        c_strg = 0

        if not u.isFloat(flx['c_strg']):

            c_strg = flx['c_strg'].solution_value()

            if abs(c_strg) < Threshold:

                flx['c_strg'] = -1

            else:

                flx['c_strg'] = c_strg

        else:

            c_strg = flx['c_strg']

        # ---

        if abs(c_strg) < Threshold:

            flx['e_strg'] = []

        else:

            rows = []

            for i in range(0, Y2H):

                rows.append(flx['e_strg'][i].solution_value())

            if sum(rows) < Threshold:

                flx['e_strg'] = []

            else:

                flx['e_strg'] = rows

        # ---

        rows = []

        for i in range(0, Y2H):

            if flx['type'] != 'hdam':

                rows.append(flx['e_char'][i].solution_value())

            else:

                rows.append(flx['e_char'][i])

        if sum(rows) < Threshold:

            flx['e_char'] = []

        else:

            flx['e_char'] = rows

        # ---

        rows = []

        for i in range(0, Y2H):

            rows.append(flx['e_disc'][i].solution_value())

        if sum(rows) < Threshold:

            flx['e_disc'] = []

        else:

            flx['e_disc'] = rows


    # --- p2x

    for p2x in s['p2x']:

        # ---

        c_prod = 0

        if not u.isFloat(p2x['c_prod']):

            c_prod = p2x['c_prod'].solution_value()

            if abs(c_prod) < Threshold:

                p2x['c_prod'] = -1

            else:

                p2x['c_prod'] = c_prod

        else:

            c_prod = p2x['c_prod']

        # ---

        if abs(c_prod) < Threshold:

            p2x['x_prod'] = []

        else:

            rows = []

            for i in range(0, Y2H):

                rows.append(p2x['x_prod'][i].solution_value())

            if sum(rows) < Threshold:

                p2x['x_prod'] = []

            else:

                p2x['x_prod'] = rows

        # ---

        if p2x['type'] == 'elec + ther' and len(p2x['supply_sources']) > 0:

            # ---

            rows = []

            for i in range(0, Y2H):

                rows.append(p2x['price'][i].dual_value())

            if sum(rows) < Threshold:

                p2x['price'] = []

            else:

                p2x['price'] = rows

            # ---

            if len(p2x['price']) == 0:

                p2x['price_average'] = -1

            else:

                sum_heat_input = 0
                sum_heat_input_x_price = 0

                for i in range(0, Y2H):

                    sum_heat_input += p2x['x_prod'][i]
                    sum_heat_input_x_price += p2x['x_prod'][i] * p2x['price'][i]

                if sum_heat_input <= 0:

                    p2x['price_average'] = -1

                else:

                    p2x['price_average'] = sum_heat_input_x_price / sum_heat_input

        # ---

        c_strg = 0

        if not u.isFloat(p2x['c_strg']):

            c_strg = p2x['c_strg'].solution_value()

            if abs(c_strg) < Threshold:

                p2x['c_strg'] = -1

            else:

                p2x['c_strg'] = c_strg

        else:

            c_strg = p2x['c_strg']

        # ---

        if abs(c_strg) < Threshold:

            p2x['x_strg'] = []

        else:

            rows = []

            for i in range(0, Y2H):

                rows.append(p2x['x_strg'][i].solution_value())

            if sum(rows) < Threshold:

                p2x['x_strg'] = []

            else:

                p2x['x_strg'] = rows

        # ---

        rows = []

        for i in range(0, Y2H):

            rows.append(p2x['x_supp'][i].solution_value())

        if sum(rows) < Threshold:

            p2x['x_supp'] = []

        else:

            p2x['x_supp'] = rows


    # ---

    dmd = s['demand']['e']

    if dmd['total'] <= 0:

        dmd['output_ns'] = []
        dmd['price'] = []
        dmd['price_average'] = -1

    else:

        # ---

        dm = demand(dmd['profile'], dmd['profile_upper_limit'], dmd['total'])

        # ---

        rows = []

        for i in range(0, Y2H):

            rows.append(dmd['output_ns'][i].solution_value())

        if sum(rows) < Threshold:

            dmd['output_ns'] = []

        else:

            dmd['output_ns'] = rows

        # ---

        rows = []

        for i in range(0, Y2H):

            rows.append(dmd['price'][i].dual_value())

        if sum(rows) < Threshold:

            dmd['price'] = []

        else:

            dmd['price'] = rows

        # ---

        if len(dmd['price']) == 0:

            dmd['price_average'] = -1

        else:

            if dmd['total'] <= 0:

                dmd['price_average'] = -1

            else:

                demand_x_price = 0

                for i in range(0, Y2H):

                    demand_x_price += dm[i] * dmd['price'][i]

                dmd['price_average'] = demand_x_price / dmd['total']


    # ---

    for dmd in s['demand']['x']:

        if dmd['total'] <= 0:

            dmd['output_ns'] = []
            dmd['price'] = []
            dmd['price_average'] = -1

        else:

            # ---

            dm = demand(dmd['profile'], dmd['profile_upper_limit'], dmd['total'])

            # ---

            rows = []

            for i in range(0, Y2H):

                rows.append(dmd['output_ns'][i].solution_value())

            if sum(rows) < Threshold:

                dmd['output_ns'] = []

            else:

                dmd['output_ns'] = rows

            # ---

            rows = []

            for i in range(0, Y2H):

                rows.append(dmd['price'][i].dual_value())

            if sum(rows) < Threshold:

                dmd['price'] = []

            else:

                dmd['price'] = rows

            # ---

            if len(dmd['price']) == 0:

                dmd['price_average'] = -1

            else:

                if dmd['total'] <= 0:

                    dmd['price_average'] = -1

                else:

                    demand_x_price = 0

                    for i in range(0, Y2H):

                        demand_x_price += dm[i] * dmd['price'][i]

                    dmd['price_average'] = demand_x_price / dmd['total']


    # ---

    generation = 0
    generation_x_costs = 0
    generation_x_emissions = 0

    # ---

    for gen in s['generator']:

        if gen['c_prod'] > -1:

            generation_x_costs += gen['c_prod'] * gen['fix_cost_prod']

        if len(gen['e_prod']) > 0:

            for i in range(0, Y2H):

                generation += gen['e_prod'][i]
                generation_x_costs += gen['e_prod'][i] * gen['var_cost_prod']
                generation_x_emissions += gen['e_prod'][i] * gen['var_emis_prod']

        if gen['type'] == 'elec + ther' and len(gen['h_prod']) > 0:

            for i in range(0, Y2H):

                generation += gen['h_prod'][i] * gen['a']
                generation_x_costs += gen['h_prod'][i] * gen['a'] * gen['var_cost_prod']
                generation_x_emissions += gen['h_prod'][i] * gen['a'] * gen['var_emis_prod']

    # ---

    dmd = s['demand']['e']

    if len(dmd['output_ns']) > 0:

        for i in range(0, Y2H):

            generation += dmd['output_ns'][i]
            generation_x_costs += dmd['output_ns'][i] * dmd['var_cost_ns']
            generation_x_emissions += dmd['output_ns'][i] * dmd['var_emis_ns']

    # ---

    if generation <= 0:

        s['solver']['stat_cost'] = -1
        s['solver']['stat_emis'] = -1

    else:

        s['solver']['stat_cost'] = generation_x_costs / generation
        s['solver']['stat_emis'] = generation_x_emissions / generation


    # --- finish

    stat_time_2 = time.time()
    stat_time = float(stat_time_2) - float(stat_time_1)


else:


    # --- failure

    s['solver']['stat_succ'] = 0


    # --- finish

    stat_time_2 = time.time()
    stat_time = float(stat_time_2) - float(stat_time_1)


s['solver']['stat_time'] = stat_time
s['solver']['stat_capa'] = stat_capa
s['solver']['stat_outp'] = stat_outp
s['solver']['stat_cons'] = stat_cons


if s['solver']['stat_succ'] == 0:

    s_i = {}

    try:

        f_j = open(sys.argv[1], 'r')
        jobj = json.load(f_j)
        f_j.close()

        s_i = jobj

    except:

        pass

    s_i['solver'] = s['solver']

    s = s_i


json_outp = str(sys.argv[1]).replace('.json', '') + '.ieso.json'


if len(sys.argv) >= 3:

    json_outp = json_outp.replace('.json', '') + '.carbon_constraint_=_' + str(sys.argv[2]) + '.json'


with open(json_outp, 'w') as f:

    json.dump(s, f, indent=4)
