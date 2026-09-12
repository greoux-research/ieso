#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ortools.linear_solver import pywraplp

from ieso_modules import fcn as u


# A solve that does not reach OPTIMAL fails for a reason, and the reasons call
# for different responses: an infeasible model is a specification error, an
# unbounded one is a missing constraint, and a solver that stopped early is a
# limit to raise. Reporting only success or failure loses that distinction.

STATUS = {
    pywraplp.Solver.OPTIMAL: 'optimal',
    pywraplp.Solver.FEASIBLE: 'feasible but not proven optimal',
    pywraplp.Solver.INFEASIBLE: 'infeasible',
    pywraplp.Solver.UNBOUNDED: 'unbounded',
    pywraplp.Solver.ABNORMAL: 'abnormal (numerical trouble)',
    pywraplp.Solver.NOT_SOLVED: 'not solved',
}


def run(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Solve the linear optimisation problem

    status = glop.Solve()

    stat['status'] = STATUS.get(status, 'unknown status ' + str(status))

    if status != pywraplp.Solver.OPTIMAL and u.Verbose:

        print('solver did not reach an optimal solution: ' + stat['status'])

    return status == pywraplp.Solver.OPTIMAL
