#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import subprocess

import numpy as np

import json

import sys


ieso_version = '25.10'
Verbose = True
Y2H = 8760
Strg_end_eq_ini = True


def get_json(json_file):

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    try:

        f_j = open(json_file, 'r')
        jobj = json.load(f_j)
        f_j.close()

        return jobj

    except:

        if Verbose:

            print('Could not load \'' + json_file + '\'')

        sys.exit(1)


def load(csv_path):

    # Load time series data from a CSV file and validate it
    # csv_path: Path to the CSV file.
    # The file is expected to contain a single column of numerical values without a header.

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    try:

        data = np.loadtxt(csv_path, dtype=float)

        if len(data) != Y2H:

            # the number of rows does not match Y2H (8760)

            return None, None, True

        else:

            return data, np.any(data < 0), False

    except:

        return None, None, True


def normalize(hpro, cp):

    # Normalise a time series profile and scale it to a specified capacity factor.

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    max_ = np.max(hpro)
    npro = hpro / max_
    sum_ = np.sum(npro)
    cor_ = cp / (sum_ / Y2H)
    npro = cor_ * npro

    return npro


def dm_h(profile, total):

    """
    Build an hourly demand series (output) such that its sum equals 'total'.
    sum(output) = total

    Parameters
    ----------
    profile : str | list | np.ndarray
        - If a string: path to a CSV file containing a single-column hourly profile with Y2H rows.
        - If a list or NumPy array: array of Y2H numerical values (new feature).
        - If empty string: a flat profile is used.
    total : float
        Total annual demand (MWh, etc.)

    Returns
    -------
    output : list of floats
        Normalised hourly demand profile scaled so that sum(output) = total.
    """

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    import numpy as np
    import sys
    import os

    output = []

    if profile == '':

        # Case 1: Empty string - flat profile

        output = np.full(Y2H, total / Y2H).tolist()

    elif isinstance(profile, (list, np.ndarray)):

        # Case 2: Profile provided directly as numerical array

        data = np.array(profile, dtype=float)

        if len(data) != Y2H:

            print(f"Error: Expected profile length {Y2H}, got {len(data)}")

            sys.exit(1)

        if np.any(data < 0):

            print("Error: Profile contains negative values.")

            sys.exit(1)

        data_sum = np.sum(data)

        if data_sum == 0:

            print("Error: Profile sum is zero.")

            sys.exit(1)

        output = ((total / data_sum) * data).tolist()

    elif isinstance(profile, str) and os.path.isfile(profile):

        # Case 3: Profile is a path to CSV file

        data, negative_entries, oops = load(profile)

        if negative_entries or oops:

            if Verbose:

                print("Error loading '" + profile + "'")

            sys.exit(1)

        data_sum = np.sum(data)

        output = ((total / data_sum) * data).tolist()

    else:

        print("Error: Invalid 'profile' input. Must be a file path, list, or array.")

        sys.exit(1)

    output = np.array(output, dtype=float).tolist()

    if Verbose and False:

        print('dm_h', profile, output[0], output[1], output[2], '..', output[Y2H - 1])

    return output


def cf_h(profile, capacity_factor):

    """
    Build an hourly generation series (output) normalised to target 'capacity_factor'.
    sum(output) / Y2H = capacity_factor

    Parameters
    ----------
    profile : str | list | np.ndarray
        - If a string: path to a CSV file containing a single-column hourly profile with Y2H rows.
        - If a list or NumPy array: array of Y2H numerical values (new feature).
        - If empty string: a flat profile is used.
    capacity_factor : float
        Target capacity factor (0–1).

    Returns
    -------
    output : list of floats
        Normalised hourly capacity profile scaled so that average(output) = capacity_factor.
    """

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    import numpy as np
    import sys
    import os

    output = []

    if profile == '':

        # Case 1: Empty string - flat profile

        output = np.full(Y2H, capacity_factor).tolist()

    elif isinstance(profile, (list, np.ndarray)):

        # Case 2: Direct numerical array input

        data = np.array(profile, dtype=float)

        if len(data) != Y2H:

            print(f"Error: Expected profile length {Y2H}, got {len(data)}")

            sys.exit(1)

        if np.any(data < 0):

            print("Error: Profile contains negative values.")

            sys.exit(1)

        if np.sum(data) == 0:

            print("Error: Profile sum is zero.")

            sys.exit(1)

        output = normalize(data, capacity_factor)

    elif isinstance(profile, str) and os.path.isfile(profile):

        # Case 3: Profile from CSV file

        data, negative_entries, oops = load(profile)

        if negative_entries or oops:

            if Verbose:

                print("Error loading '" + profile + "'")

            sys.exit(1)

        output = normalize(data, capacity_factor)

    else:

        print("Error: Invalid 'profile' input. Must be a file path, list, or array.")

        sys.exit(1)

    output = np.array(output, dtype=float).tolist()

    if Verbose and False:

        print('cf_h', profile, output[0], output[1], output[2], '..', output[Y2H - 1])

    return output


def thermo(Temperature_Turbine_Inlet, Pressure_Turbine_Inlet, Pressure_Condenser_Inlet, Steam_Temperature):

    # Run an external thermodynamic simulation and parse results.

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    a = -1
    b = -1
    e = False
    o = ''

    try:

        o = subprocess.run(['thermo/sim.bin', str(Temperature_Turbine_Inlet), str(Pressure_Turbine_Inlet), str(
            Pressure_Condenser_Inlet), str(Steam_Temperature)], stdout=subprocess.PIPE, text=True).stdout
        a = float(o.split(' ')[0])
        b = float(o.split(' ')[1])

    except:

        e = True

        pass

    if a < 0 or b < 0:

        e = True

    return a, b, e


def capaSetToBeOptimised(variable):

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    isSetToBeOptimised = not isinstance(variable, (int, float))

    return isSetToBeOptimised

