#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import time

from ortools.linear_solver import pywraplp


def run(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solve the linear optimisation problem

    if glop.Solve() == pywraplp.Solver.OPTIMAL:

        return True

    else:

        return False
