#!/usr/bin/python
# -*- coding: utf-8 -*-
# Gréoux Research - www.greoux.re


import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt

import u as u
import t as t


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
def contains_negative(arr):
    for num in arr:
        if num < 0:
            return True
    return False


# ---

def hpro_2_png(hpro, unit, png_file_name):

    # hourly profile to png
    # hpro: hourly profile (8760 values)
    # unit: unit, 'MW', e.g.
    # png_file_name: png file name

    x = []
    y = []

    for k in range(0, len(hpro)):

        x.append(k + 1)
        y.append(hpro[k])

    plt.clf()
    plt.figure(figsize=(16, 9))
    plt.fill_between(x, y)
    plt.xlim(xmin=0)
    plt.xlim(xmax=len(hpro))
    if not contains_negative(hpro):
        plt.ylim(ymin=0)
    plt.grid()
    plt.xlabel('Hour', fontsize=20)
    plt.ylabel(unit, fontsize=20)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.title('sum: ' + str(round(sum(hpro))) + ' | max: ' + str(round(max(hpro), 2)), fontsize=20)

    file_path = os.path.join('report', png_file_name)
    plt.savefig(file_path)

    file_path = os.path.join('report', png_file_name + '---data.csv')
    u.nmbzToFile(hpro, file_path)


# ---

if len(sys.argv) < 2:

    print('Example of a correct command line: \'python report.py [json file]\'')
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


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

if s['solver']['stat_succ'] == -1:

    t.init('Input Summary')

else:

    t.init('Simulation Output Summary')


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

t.add_section('Demand')


# --- demand > electricity

dmd = s['demand']['electricity']

t.add_text('Demand for ' + dmd['iden'].capitalize() + ':')

l = []

l.append('Annual Demand in MWh: ' + str(round(dmd['total'])))

hpro = demand(dmd['profile'], dmd['profile_upper_limit'], dmd['total'])

titl = 'Demand for ' + dmd['iden'].capitalize()
labl = 'Demand-for-' + dmd['iden'].capitalize()

if not all(element == hpro[0] for element in hpro):

    hpro_2_png(hpro, 'MWh', labl + '.png')

    l.append('Hourly Profile: Figure~\\ref{fig:' + labl + '}')

else:

    l.append('Hourly Profile: Uniform (' + str(round(hpro[0])) + ' MWh each Hour)')

l.append('Non-Service Penalty in [Currency] per MWh: ' + str(dmd['var_cost_ns']))
l.append('Supply Sources: Power Grid')

t.add_list(l)

if not all(element == hpro[0] for element in hpro):

    t.add_figure(labl + '.png', titl, labl)


# --- demand > x

for dmd in s['demand']['x']:

    if dmd['total'] > 0:

        t.add_text('Demand for ' + dmd['iden'].capitalize() + ':')

        l = []

        l.append('Annual Demand in Q(X): ' + str(round(dmd['total'])))
        
        hpro = demand(dmd['profile'], dmd['profile_upper_limit'], dmd['total'])

        titl = 'Demand for ' + dmd['iden'].capitalize()
        labl = 'Demand-for-' + dmd['iden'].capitalize()

        if not all(element == hpro[0] for element in hpro):

            hpro_2_png(hpro, 'Q(X)', labl + '.png')

            l.append('Hourly Profile: Figure~\\ref{fig:' + labl + '}')

        else:

            l.append('Hourly Profile: Uniform (' + str(round(hpro[0])) + ' Q(X) each Hour)')

        l.append('Non-Service Penalty in [Currency] per Q(X): ' + str(dmd['var_cost_ns']))

        Supply_Sources = ''
        for src in dmd['supply_sources']:
            Supply_Sources += ' "' + src + '"'

        if Supply_Sources != '':
            Supply_Sources = Supply_Sources.strip().replace(' ', ' , ')
            l.append('Supply Sources: Power-to-X Processes [ ' + Supply_Sources + ' ]')
        else:
            l.append('Supply Sources: [] (!)')

        t.add_list(l)

        if not all(element == hpro[0] for element in hpro):

            t.add_figure(labl + '.png', titl, labl)


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

if s['solver']['stat_succ'] == -1:


    # --- generators

    if len(s['generator']) > 0:

        t.add_section('Generators')


    # ---

    for gen in s['generator']:

        # ---

        t.add_text('Generator "' + gen['iden'] + '":')

        l = []

        if gen['type'] == 'elec + ther':
            l.append('Type: Cogenerator')
        else:
            l.append('Type: Electricity-Generating Power Plant')

        cf = capacity_factor(gen['profile'], gen['profile_upper_limit'])

        titl = 'Capacity Factor\'s Upper Limit - "' + gen['iden'] + '"'
        labl = 'Capacity-Factor--s-Upper-Limit---' + gen['iden']

        if not all(element == cf[0] for element in cf):

            hpro_2_png(cf, 'Capacity Factor', labl + '.png')

            l.append('Capacity Factor\'s Upper Limit: Figure~\\ref{fig:' + labl + '}')

        else:

            l.append('Capacity Factor\'s Upper Limit: Uniform (' + str(round(cf[0], 2)) + ')')

        l.append('Fixed Costs in [Currency] per MW per Year: ' + str(gen['fix_cost_prod']))
        l.append('Variable Costs in [Currency] per MWh: ' + str(gen['var_cost_prod']))
        l.append('Variable Emissions in [Currency] per MWh: ' + str(gen['var_emis_prod']))

        if gen['c_prod'] > 0:
            l.append('Capacity in MW: ' + str(round(gen['c_prod'], 2)))

        t.add_list(l)

        if not all(element == cf[0] for element in cf):

            t.add_figure(labl + '.png', titl, labl)


    # --- flexibility means

    if len(s['flex']) > 0:

        t.add_section('Flexibility Means')


    # ---

    for flx in s['flex']:

        # ---

        t.add_text('Flexibility Mean "' + flx['iden'] + '":')

        l = []

        if flx['type'] == 'hdam':

            l.append('Type: Hydroelectric Dam')

            cf = capacity_factor(flx['profile'], flx['profile_upper_limit'])

            titl = 'Capacity Factor\'s Upper Limit - "' + flx['iden'] + '"'
            labl = 'Capacity-Factor--s-Upper-Limit---' + flx['iden']

            if not all(element == cf[0] for element in cf):

                hpro_2_png(cf, 'Capacity Factor', labl + '.png')

                l.append('Capacity Factor\'s Upper Limit: Figure~\\ref{fig:' + labl + '}')

            else:

                l.append('Capacity Factor\'s Upper Limit: Uniform (' + str(round(cf[0], 2)) + ')')

        else:

            l.append('Type: Electricity Storage System')

        l.append('Fixed Costs in [Currency] per MWh per Year: ' + str(flx['fix_cost_strg']))
        l.append('Hours of Storage at Maximum Discharge: ' + str(flx['hours_of_storage']))
        l.append('Round Trip Efficiency: ' + str(flx['round_trip_efficiency']))

        if flx['c_strg'] > 0:
            l.append('Capacity in MWh: ' + str(round(flx['c_strg'], 2)))

        t.add_list(l)

        if flx['type'] == 'hdam':

            cf = capacity_factor(flx['profile'], flx['profile_upper_limit'])

            titl = 'Capacity Factor\'s Upper Limit - "' + flx['iden'] + '"'
            labl = 'Capacity-Factor--s-Upper-Limit---' + flx['iden']

            if not all(element == cf[0] for element in cf):

                t.add_figure(labl + '.png', titl, labl)


    # --- power-to-x processes

    if len(s['p2x']) > 0:

        t.add_section('Power-to-X Processes')


    # ---

    for p2x in s['p2x']:

        # ---

        t.add_text('Power-to-X Process "' + p2x['iden'] + '":')

        l = []

        if p2x['type'] == 'elec + ther':

            l.append('Consumes Electricity (Grid-Supplied ' + str(p2x['pow_use_elec_prod']) + ' MWh per Q(X))')
            l.append('Consumes Heat (' + str(p2x['pow_use_ther_prod']) + ' MWh per Q(X) at ' + str(p2x['temperature']) + ' C)')

            Heat_Supply_Sources = ''
            for src in p2x['supply_sources']:
                Heat_Supply_Sources += ' "' + src + '"'

            if Heat_Supply_Sources != '':
                Heat_Supply_Sources = Heat_Supply_Sources.strip().replace(' ', ' , ')
                l.append('Heat Supply Sources: Cogenerators [ ' + Heat_Supply_Sources + ' ]')

        else:

            l.append('Consumes Electricity (Grid-Supplied ' + str(p2x['pow_use_elec_prod']) + ' MWh per Q(X))')

        cf = capacity_factor(p2x['profile'], p2x['profile_upper_limit'])

        titl = 'Capacity Factor\'s Upper Limit - "' + p2x['iden'] + '"'
        labl = 'Capacity-Factor--s-Upper-Limit---' + p2x['iden']

        if not all(element == cf[0] for element in cf):

            hpro_2_png(cf, 'Capacity Factor', labl + '.png')

            l.append('Capacity Factor\'s Upper Limit: Figure~\\ref{fig:' + labl + '}')

        else:

            l.append('Capacity Factor\'s Upper Limit: Uniform (' + str(round(cf[0], 2)) + ')')

        l.append('Fixed Production Costs in [Currency] per Q(X) per Hour per Year: ' + str(p2x['fix_cost_prod']))
        l.append('Variable Production Costs (Excluding Energy) in [Currency] per Q(X): ' + str(p2x['var_cost_prod']))

        if p2x['c_prod'] > 0:
            l.append('Production Capacity in Q(X) per Hour: ' + str(round(p2x['c_prod'], 2)))

        l.append('Fixed Storage Costs in [Currency] per Q(X) per Year: ' + str(p2x['fix_cost_strg']))

        if p2x['c_strg'] > 0:
            l.append('Storage Capacity in Q(X): ' + str(round(p2x['c_strg'], 2)))

        t.add_list(l)

        if not all(element == cf[0] for element in cf):

            t.add_figure(labl + '.png', titl, labl)


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

if s['solver']['stat_succ'] == 0:

    print('Optimiser failed to converge')

    sys.exit()


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

if s['solver']['stat_succ'] == 1:


    # --- generators

    if len(s['generator']) > 0:

        t.add_section('Generators')


    # ---

    for gen in s['generator']:

        # ---

        t.add_text('Generator "' + gen['iden'] + '":')

        l = []

        if gen['type'] == 'elec + ther':
            values_of_a_and_b = ' ($a = ' + str(round(gen['a'], 2)) + '$; $b = ' + str(round(gen['b'], 2)) + '$)'
            l.append('Type: Cogenerator' + values_of_a_and_b)
        else:
            l.append('Type: Electricity-Generating Power Plant')

        l.append('Fixed Costs in [Currency] per MW per Year: ' + str(gen['fix_cost_prod']))
        l.append('Variable Costs in [Currency] per MWh: ' + str(gen['var_cost_prod']))
        l.append('Variable Emissions in [Currency] per MWh: ' + str(gen['var_emis_prod']))

        # ---

        if gen['c_prod'] == -1:

            l.append('\\textcolor{BrickRed}{The optimiser did not suggest adding generation capacity}')

        else:

            l.append('\\textcolor{MidnightBlue}{Capacity in MW: ' + str(round(gen['c_prod'], 2)) + '}')

            if len(gen['e_prod']) > 0:

                labl = 'Electricity-Generation-by-' + gen['iden']
                l.append('Electricity Generation: ' + str(round(sum(gen['e_prod']))) + ' MWh (Figure~\\ref{fig:' + labl + '})')

            if len(gen['h_prod']) > 0:

                labl = 'Heat-Generation-by-' + gen['iden']
                l.append('Heat Generation: ' + str(round(sum(gen['h_prod']))) + ' MWh (Figure~\\ref{fig:' + labl + '})')

            if len(gen['e_prod']) > 0:

                cf = capacity_factor(gen['profile'], gen['profile_upper_limit'])

                if not all(element == cf[0] for element in cf):

                    # solar and wind (curtailment)

                    curt_h = 0
                    curt_e = 0

                    for i in range(0, Y2H):

                        delta = cf[i] * gen['c_prod'] - gen['e_prod'][i]

                        if delta > Threshold:

                            curt_h += 1
                            curt_e += delta

                    Curtailment = ''

                    Curtailment += str(curt_h) + ' Hours; '
                    Curtailment += str(str(round(curt_e, 2))) + ' MWh '

                    if sum(gen['e_prod']) > 0:

                        Curtailment += 'or ' + str(round(100 * curt_e / sum(gen['e_prod']), 2)) + ' \\% of the Tech.\'s Annual Gen. Volume'

                    l.append('Curtailment: ' + Curtailment)

                else:

                    # dispatchables (ramping requirements)

                    e_prod_prev = gen['e_prod'][Y2H - 1]

                    changes = 0

                    for i in range(0, Y2H):

                        delta = abs(gen['e_prod'][i] - e_prod_prev)

                        e_prod_prev = gen['e_prod'][i]

                        if delta > Threshold:

                            changes += 1

                    l.append('Number of Successive Changes in Output: ' + str(changes))

        # ---

        t.add_list(l)

        # ---

        if gen['c_prod'] > 0:

            if len(gen['e_prod']) > 0:

                hpro = gen['e_prod']
                titl = 'Electricity Generation by "' + gen['iden'] + '"'
                labl = 'Electricity-Generation-by-' + gen['iden']
                hpro_2_png(hpro, 'MWh', labl + '.png')
                t.add_figure(labl + '.png', titl, labl)

            if gen['type'] == 'elec + ther':

                if len(gen['h_prod']) > 0:

                    hpro = gen['h_prod']
                    titl = 'Heat Generation by "' + gen['iden'] + '"'
                    labl = 'Heat-Generation-by-' + gen['iden']
                    hpro_2_png(hpro, 'MWh', labl + '.png')
                    t.add_figure(labl + '.png', titl, labl)


    # --- flexibility means

    if len(s['flex']) > 0:

        t.add_section('Flexibility Means')


    # ---

    for flx in s['flex']:

        # ---

        t.add_text('Flexibility Mean "' + flx['iden'] + '":')

        l = []

        if flx['type'] == 'hdam':

            l.append('Type: Hydroelectric Dam')

        else:

            l.append('Type: Electricity Storage System')

        l.append('Fixed Costs in [Currency] per MWh per Year: ' + str(flx['fix_cost_strg']))
        l.append('Hours of Storage at Maximum Discharge: ' + str(flx['hours_of_storage']))
        l.append('Round Trip Efficiency: ' + str(flx['round_trip_efficiency']))

        # ---

        if flx['c_strg'] == -1:

            l.append('\\textcolor{BrickRed}{The optimiser did not suggest adding storage capacity}')

        else:

            l.append('\\textcolor{MidnightBlue}{Capacity in MWh: ' + str(round(flx['c_strg'], 2)) + '}')

            if len(flx['e_char']) > 0 and len(flx['e_disc']) > 0:

                labl = 'Electricity-Charged-and-Discharged-by-' + flx['iden']
                l.append('Electricity Charged (-) and Discharged (+): Figure~\\ref{fig:' + labl + '}')

            if len(flx['e_strg']) > 0:

                labl = 'Electricity-Stored-by-' + flx['iden']
                l.append('Electricity Stored: Figure~\\ref{fig:' + labl + '}')

        # ---

        t.add_list(l)

        # ---

        if flx['c_strg'] > 0:

            if len(flx['e_char']) > 0 and len(flx['e_disc']) > 0:

                diff_disc_char = []
                for i in range(0, Y2H):
                    diff_disc_char.append(flx['e_disc'][i] - flx['e_char'][i])
                hpro = diff_disc_char
                titl = 'Electricity Charged (-) and Discharged (+) by "' + flx['iden'] + '"'
                labl = 'Electricity-Charged-and-Discharged-by-' + flx['iden']
                hpro_2_png(hpro, 'MWh', labl + '.png')
                t.add_figure(labl + '.png', titl, labl)

            if len(flx['e_strg']) > 0:

                hpro = flx['e_strg']
                titl = 'Electricity Stored by "' + flx['iden'] + '"'
                labl = 'Electricity-Stored-by-' + flx['iden']
                hpro_2_png(hpro, 'MWh', labl + '.png')
                t.add_figure(labl + '.png', titl, labl)


    # --- power-to-x processes

    if len(s['p2x']) > 0:

        t.add_section('Power-to-X Processes')


    # ---

    for p2x in s['p2x']:

        # ---

        t.add_text('Power-to-X Process "' + p2x['iden'] + '":')

        l = []

        if p2x['type'] == 'elec + ther':

            l.append('Consumes Electricity (Grid-Supplied ' + str(p2x['pow_use_elec_prod']) + ' MWh per Q(X))')
            l.append('Consumes Heat (' + str(p2x['pow_use_ther_prod']) + ' MWh per Q(X) at ' + str(p2x['temperature']) + ' C)')

            Heat_Supply_Sources = ''
            for src in p2x['supply_sources']:
                Heat_Supply_Sources += ' "' + src + '"'

            if Heat_Supply_Sources != '':
                Heat_Supply_Sources = Heat_Supply_Sources.strip().replace(' ', ' , ')
                l.append('Heat Supply Sources: Cogenerators [ ' + Heat_Supply_Sources + ' ]')

        else:

            l.append('Consumes Electricity (Grid-Supplied ' + str(p2x['pow_use_elec_prod']) + ' MWh per Q(X))')

        l.append('Fixed Production Costs in [Currency] per Q(X) per Hour per Year: ' + str(p2x['fix_cost_prod']))
        l.append('Variable Production Costs (Excluding Energy) in [Currency] per Q(X): ' + str(p2x['var_cost_prod']))

        # ---

        if p2x['c_prod'] == -1:

            l.append('\\textcolor{BrickRed}{The optimiser did not suggest adding production capacity}')

        else:

            l.append('\\textcolor{MidnightBlue}{Production Capacity in Q(X) per Hour: ' + str(round(p2x['c_prod'], 2)) + '}')

            if len(p2x['x_prod']) > 0:

                labl = 'Production-Profile---' + p2x['iden']
                l.append('Production Profile: Figure~\\ref{fig:' + labl + '}')

        # ---
            
        l.append('Fixed Storage Costs in [Currency] per Q(X) per Year: ' + str(p2x['fix_cost_strg']))

        # ---

        if p2x['c_strg'] == -1:

            l.append('\\textcolor{BrickRed}{The optimiser did not suggest adding storage capacity}')

        else:

            Storage_Capacity = str(round(p2x['c_strg'], 2)) + ' Q(X)'

            if p2x['c_prod'] > 0 and p2x['profile_upper_limit'] > 0 and p2x['profile_upper_limit'] <= 1:
                Storage_Capacity += ' or ' + str(round(p2x['c_strg'] / (p2x['profile_upper_limit'] * p2x['c_prod']))) + ' Hours of Production at Max. Capacity'

            l.append('\\textcolor{MidnightBlue}{Storage Capacity: ' + Storage_Capacity + '}')

            if len(p2x['x_strg']) > 0:

                labl = 'Storage-Profile---' + p2x['iden']
                l.append('Storage Profile: Figure~\\ref{fig:' + labl + '}')

        # ---

        if len(p2x['x_supp']) > 0:

            labl = 'Supply-Profile---' + p2x['iden']
            l.append('Supply Profile: Figure~\\ref{fig:' + labl + '}')

        # ---

        t.add_list(l)

        # ---

        if p2x['c_prod'] > 0:

            if len(p2x['x_prod']) > 0:

                hpro = p2x['x_prod']
                titl = 'Production Profile - "' + p2x['iden'] + '"'
                labl = 'Production-Profile---' + p2x['iden']
                hpro_2_png(hpro, 'Q(X) per Hour', labl + '.png')
                t.add_figure(labl + '.png', titl, labl)

        if p2x['c_strg'] > 0:

            if len(p2x['x_strg']) > 0:

                hpro = p2x['x_strg']
                titl = 'Storage Profile - "' + p2x['iden'] + '"'
                labl = 'Storage-Profile---' + p2x['iden']
                hpro_2_png(hpro, 'Q(X)', labl + '.png')
                t.add_figure(labl + '.png', titl, labl)

        if len(p2x['x_supp']) > 0:

            hpro = p2x['x_supp']
            titl = 'Supply Profile - "' + p2x['iden'] + '"'
            labl = 'Supply-Profile---' + p2x['iden']
            hpro_2_png(hpro, 'Q(X) per Hour', labl + '.png')
            t.add_figure(labl + '.png', titl, labl)


    # ---

    generation = 0
    generation_x_costs = 0
    generation_x_emissions = 0

    for gen in s['generator']:

        if gen['c_prod'] > 0:

            generation_x_costs += gen['c_prod'] * gen['fix_cost_prod']

            for i in range(0, Y2H):

                generation += gen['e_prod'][i]
                generation_x_costs += gen['e_prod'][i] * gen['var_cost_prod']
                generation_x_emissions += gen['e_prod'][i] * gen['var_emis_prod']

                if gen['type'] == 'elec + ther':

                    generation += gen['h_prod'][i] * gen['a']
                    generation_x_costs += gen['h_prod'][i] * gen['a'] * gen['var_cost_prod']
                    generation_x_emissions += gen['h_prod'][i] * gen['a'] * gen['var_emis_prod']

    if len(dmd['output_ns']) > 0:

        dmd = s['demand']['electricity']

        for i in range(0, Y2H):

            generation += dmd['output_ns'][i]
            generation_x_costs += dmd['output_ns'][i] * dmd['var_cost_ns']
            generation_x_emissions += dmd['output_ns'][i] * dmd['var_emis_ns']

    if generation > 0:

        t.add_section('Costs and Emissions')

        t.add_text('Generation Costs and Emissions on a per MWh Basis:')

        l = []

        l.append('Generation Costs in [Currency] per MWh: ' + str(round(generation_x_costs / generation, 2)))
        l.append('Generation Emissions in kg per MWh: ' + str(round(generation_x_emissions / generation, 2)))

        t.add_list(l)


    # ---

    t.add_section('Prices')


    # ---

    dmd = s['demand']['electricity']

    if len(dmd['price']) > 0:

        t.add_text(dmd['iden'].capitalize() + ':')

        l = []

        l.append('Average Price in [Currency] per MWh: ' + str(round(dmd['price_average'], 2)))

        labl = dmd['iden'].capitalize() + '-Price-Profile'
        l.append('Price Profile: Figure~\\ref{fig:' + labl + '}')

        t.add_list(l)

        hpro = dmd['price'] # sorted(dmd['price'], reverse=True)
        titl = dmd['iden'].capitalize() + ' Price Profile'
        labl = dmd['iden'].capitalize() + '-Price-Profile'
        hpro_2_png(hpro, '$ per MWh', labl + '.png')
        t.add_figure(labl + '.png', titl, labl)

    # ---

    for dmd in s['demand']['x']:

        if dmd['total'] > 0:

            if len(dmd['price']) > 0:

                t.add_text(dmd['iden'].capitalize() + ':')

                l = []

                l.append('Average Price in [Currency] per Q(X): ' + str(round(dmd['price_average'], 2)))

                labl = dmd['iden'].capitalize() + '-Price-Profile'
                l.append('Price Profile: Figure~\\ref{fig:' + labl + '}')

                t.add_list(l)

                hpro = dmd['price'] # sorted(dmd['price'], reverse=True)
                titl = dmd['iden'].capitalize() + ' Price Profile'
                labl = dmd['iden'].capitalize() + '-Price-Profile'
                hpro_2_png(hpro, '$ per Q(X)', labl + '.png')
                t.add_figure(labl + '.png', titl, labl)


    # ---

    for p2x in s['p2x']:

        if p2x['type'] == 'elec + ther' and len(p2x['supply_sources']) > 0:

            if p2x['c_prod'] > 0:

                if len(p2x['price']) > 0:

                    t.add_text('"' + p2x['iden'] + '" Heat Supply:')

                    l = []

                    l.append('Average Price in [Currency] per MWh: ' + str(round(p2x['price_average'], 2)))

                    labl = p2x['iden'] + '-Heat-Supply-Price-Profile'
                    l.append('Price Profile: Figure~\\ref{fig:' + labl + '}')

                    t.add_list(l)

                    hpro = p2x['price'] # sorted(p2x['price'], reverse=True)
                    titl = '"' + p2x['iden'] + '" Heat Supply Price Profile'
                    labl = p2x['iden'] + '-Heat-Supply-Price-Profile'
                    hpro_2_png(hpro, '$ per MWh', labl + '.png')
                    t.add_figure(labl + '.png', titl, labl)


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

t.save()
