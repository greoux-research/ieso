#!/usr/bin/python
# -*- coding: utf-8 -*-
# Gréoux Research - www.greoux.re


import os
import sys
import json


import subprocess
import math
import numpy as np


ieso_version = '24.03'


def fileToRows(fn):

    f = open(fn, 'r')
    c = f.read()
    r = []
    r = c.split('\n')
    f.close()

    return r


def rowsToFile(rows, fn):

    with open(fn, 'w') as f:
        for row in rows:
            f.write(row + '\n')


def textToFile(text, fn):

    with open(fn, 'w') as f:
        f.write(text)


def fileToNmbz(fn):

    r = []
    rows = fileToRows(fn)

    for row in rows:
        if len(row) > 0:
            r.append(float(row))

    return r


def nmbzToFile(nmbz, fn):

    with open(fn, 'w') as f:
        for nmb in nmbz:
            f.write(str(nmb) + '\n')


def read(fn):

    bs = 8760

    try:

        a = fileToNmbz(fn)
        c = len(a)

        # c > bs

        if c > bs:

            return [], 0, 0, 0, True

        else:  # c <= bs

            # init: s, n, t

            o = []
            s = 0
            n = False
            t_index = 0
            t_value = 0

            # c = bs?

            if c == bs:

                o = a

            else:  # c < bs

                div = math.floor(bs / c)
                mod = bs % c

                arr = []

                # ---

                for k in range(0, c):

                    if k < c - 1:

                        arr.append(np.full(div, a[k]).tolist())

                    else:  # k = c - 1

                        arr.append(np.full(div + mod, a[k]).tolist())

                # ---

                for k in range(0, len(arr)):

                    for item in arr[k]:

                        o.append(item)

            # eval: s, n, t

            s = np.sum(o)

            t_index = 0
            t_value = o[t_index]

            for k in range(0, bs):

                if o[k] < 0:
                    n = True

                if o[k] >= t_value:
                    t_index = k
                    t_value = o[k]

            # finish

            return o, s, n, t_value, False

    except:

        return [], 0, 0, 0, True


def isFloat(variable):

    return isinstance(variable, (int, float))


def isString(variable):

    return isinstance(variable, str)


def thermo(Temperature_Turbine_Inlet, Pressure_Turbine_Inlet, Pressure_Condenser_Inlet, Steam_Temperature):

    a = -1
    b = -1
    e = False
    o = ''

    try:

        o = subprocess.run(['thermo/sim.bin', str(Temperature_Turbine_Inlet), str(Pressure_Turbine_Inlet), str(Pressure_Condenser_Inlet), str(Steam_Temperature)], stdout=subprocess.PIPE, text=True).stdout
        a = float(o.split(' ')[0])
        b = float(o.split(' ')[1])

    except:

        e = True

        pass

    if a < 0 or b < 0:

        e = True

    return a, b, e
