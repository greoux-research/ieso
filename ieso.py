#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ortools.linear_solver import pywraplp

from ieso_modules import eqs_p2x_1, eqs_gen, eqs_p2x_2, eqs_flx, eqs_dmd_e, eqs_dmd_x, obj, opt, pos

from ieso_modules import fcn as u

import sys

import json

import time

import numpy as np

import math


# --- --- --- --- --- --- --- --- --- Load input, opts, and stats

start_time = time.time()

argv = sys.argv

# --

if u.Verbose:

    print(argv)

if len(argv) < 2:

    if u.Verbose:

        print('Examples of a correct command line: \'python ieso.py input.json\'')

    sys.exit(1)

# --

json_file = argv[1]

s = u.get_json(json_file)

# --

opts = {}

for arg in argv[2:]:

    if '=' in arg:

        k, v = arg.split('=', 1)

        opts[k] = float(v)

# --

stat = {
    'time': time.time(),
    'capa': 0,
    'outp': 0,
    'cons': 0
}


# --- --- --- --- --- --- --- --- --- Instantiate solver and objective

glop = pywraplp.Solver.CreateSolver('GLOP')

glop_objf = glop.Objective()

glop_objf.SetMinimization()


# --- --- --- --- --- --- --- --- --- Define equations and constraints

eqs_p2x_1.define(glop, s, opts, stat)
eqs_gen.define(glop, s, opts, stat)
eqs_p2x_2.define(glop, s, opts, stat)
eqs_flx.define(glop, s, opts, stat)
emis_con, nspo_con = eqs_dmd_e.define(glop, s, opts, stat)
eqs_dmd_x.define(glop, s, opts, stat)


# --- --- --- --- --- --- --- --- --- Define objective function

obj.define(glop_objf, s)


# --- --- --- --- --- --- --- --- --- Solve the model

success = opt.run(glop, s, opts, stat)

stat['time'] = time.time() - stat['time']


# --- --- --- --- --- --- --- --- --- Post-processing (if successful)

if success:

    s['solver']['stat_succ'] = 1

    pos.process(glop, s, opts, stat, emis_con, nspo_con)

else:

    s = u.get_json(json_file)

    s['solver']['stat_succ'] = 0


# --- --- --- --- --- --- --- --- --- Finish line

s['solver']['stat_time'] = stat['time']
s['solver']['stat_capa'] = stat['capa']
s['solver']['stat_outp'] = stat['outp']
s['solver']['stat_cons'] = stat['cons']

json_outp = str(json_file).replace('.json', '') + '.ieso.json'

for k, v in opts.items():

    json_outp = json_outp.replace('.json', '') + f'.{k}_{v}.json'

with open(json_outp, 'w') as f:

    json.dump(s, f, indent=4)
