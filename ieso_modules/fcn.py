#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import subprocess

import numpy as np

import json

import sys


ieso_version = '26.09'
Verbose = True
Y2H = 8760
Strg_end_eq_ini = True

# Tolerances for the post-processing accounting checks. Absolute terms guard
# quantities near zero; relative terms scale with the magnitude being checked.
Balance_atol = 1e-6
Balance_rtol = 1e-9


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


def as_profile(profile, who):

    """
    Validate and return an hourly profile as a 1-D float array, or None when a
    flat profile is requested (the empty string).

    Accepts a CSV path, a list or a NumPy array, and applies the same checks to
    all three: one dimension, exactly Y2H entries, every value finite and
    non-negative, and a strictly positive sum. A profile failing any of these
    has no defined normalisation, so it is rejected here with a reason rather
    than propagated into the optimisation.
    """

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    import os

    # Test the type before comparing with '': a NumPy array compared against a
    # string returns an array, and using that as a truth value raises.

    if isinstance(profile, str):

        if profile == '':

            return None

        if not os.path.isfile(profile):

            fail(who, 'profile file not found: \'' + profile + '\'')

        try:

            data = np.loadtxt(profile, dtype=float)

        except Exception:

            fail(who, 'could not read profile \'' + profile + '\'')

    elif isinstance(profile, (list, np.ndarray)):

        try:

            data = np.asarray(profile, dtype=float)

        except Exception:

            fail(who, 'profile is not numeric')

    else:

        fail(who, 'profile must be a file path, a list or an array')

    data = np.atleast_1d(data)

    if data.ndim != 1:

        fail(who, 'profile must be one-dimensional, got ' + str(data.ndim) + ' dimensions')

    if len(data) != Y2H:

        fail(who, 'profile must have ' + str(Y2H) + ' entries, got ' + str(len(data)))

    if not np.all(np.isfinite(data)):

        fail(who, 'profile contains non-finite values')

    if np.any(data < 0):

        fail(who, 'profile contains negative values')

    if not np.sum(data) > 0:

        fail(who, 'profile sums to zero, so it cannot be normalised')

    return data


def fail(who, message):

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    if Verbose:

        print('\'' + str(who) + '\': ' + message)

    sys.exit(1)


def file_digest(path):

    # SHA-256 of a file, or None if it cannot be read.

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    import hashlib
    import os

    if not (isinstance(path, str) and path and os.path.isfile(path)):

        return None

    h = hashlib.sha256()

    with open(path, 'rb') as f:

        for block in iter(lambda: f.read(1 << 16), b''):

            h.update(block)

    return h.hexdigest()


def provenance(json_file, opts, s):

    """
    Identify what produced a result: the code, the inputs, the options and the
    environment.

    A result that cannot be traced to the code and data behind it cannot be
    reproduced or superseded with confidence. Profiles are hashed alongside the
    input file because they determine the answer just as directly, and they are
    referenced by path rather than carried inside it.
    """

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    import datetime
    import platform

    profiles = {}

    for group in ('generator', 'p2x'):

        for item in s.get(group, []):

            path = item.get('profile', '')

            if isinstance(path, str) and path:

                profiles[path] = file_digest(path)

    for item in s.get('flex', []):

        path = item.get('inflow_profile', '')

        if isinstance(path, str) and path:

            profiles[path] = file_digest(path)

    for key in ('e',):

        path = s['demand'][key].get('profile', '')

        if isinstance(path, str) and path:

            profiles[path] = file_digest(path)

    for dmd in s['demand'].get('x', []):

        path = dmd.get('profile', '')

        if isinstance(path, str) and path:

            profiles[path] = file_digest(path)

    try:

        import ortools.init.python.init as _ort

        solver_version = _ort.OrToolsVersion.version_string()

    except Exception:

        solver_version = 'unknown'

    return {
        'ieso_version': ieso_version,
        'input': str(json_file),
        'input_sha256': file_digest(json_file),
        'profiles_sha256': profiles,
        'options': dict(opts),
        'hours': Y2H,
        'storage_closes_the_year': Strg_end_eq_ini,
        'solver': 'GLOP',
        'ortools': solver_version,
        'numpy': np.__version__,
        'python': platform.python_version(),
        'platform': platform.platform(),
        'run_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }


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


def dm_h(profile, total, who='dm_h'):

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

    data = as_profile(profile, who)

    if data is None:

        output = np.full(Y2H, total / Y2H).tolist()

    else:

        output = ((total / np.sum(data)) * data).tolist()

    output = np.array(output, dtype=float).tolist()

    if Verbose and False:

        print('dm_h', profile, output[0], output[1], output[2], '..', output[Y2H - 1])

    return output


def cf_h(profile, capacity_factor, who='cf_h'):

    """
    Build an hourly availability series normalised to target 'capacity_factor'.
    mean(output) = capacity_factor

    The supplied profile contributes its shape only: it is divided by its own
    maximum and then rescaled so that its mean equals capacity_factor. The level
    is therefore set by capacity_factor, not by the profile. A profile whose own
    mean/max ratio is below capacity_factor will consequently peak above one.
    """

    global ieso_version, Verbose, Y2H, Strg_end_eq_ini

    data = as_profile(profile, who)

    if data is None:

        output = np.full(Y2H, capacity_factor).tolist()

    else:

        output = normalize(data, capacity_factor)

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

