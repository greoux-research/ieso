#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser


import subprocess

import numpy as np

import math

import numbers

import os



from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence

from ies_optimiser import _install
from ies_optimiser.errors import InputError

# Defaults for a run. Per-run values travel in a RunConfig (below); nothing
# here is changed while a run is in progress.
HOURS_PER_YEAR = 8760
STORAGE_CLOSES_THE_YEAR = True

# Tolerances for the post-processing accounting checks. Absolute terms guard
# quantities near zero; relative terms scale with the magnitude being checked.
Balance_atol = 1e-6
Balance_rtol = 1e-9

# Feasibility of the solution against its own constraints (balances, bounds,
# capacity limits). GLOP works to a primal tolerance on its scaled problem, so
# the unscaled residual can exceed Balance_atol on large systems; these are
# the limits beyond which a residual is reported as a failed check.
Feas_atol = 1e-5
Feas_rtol = 1e-7

# Book-keeping identities (allocated + unallocated = total, cost against the
# solver objective): the same numbers summed two ways, so only rounding differs.
Recon_atol = 1e-6
Recon_rtol = 1e-9

# The thermodynamics executable installed with the package (ies_optimiser/_bin/),
# resolved once, absolutely, through the package's resources, so the binary
# executed is the binary hashed into provenance whatever the working directory.
# RunConfig.thermo_bin overrides it for a run; nothing else does.
Thermo_bin = _install.packaged_thermo()                         # default executable
Thermo_timeout = 30                                             # default timeout, s


@dataclass(frozen=True)
class RunConfig:
    """Settings for one run, passed explicitly to every stage that needs them.

    Attributes:
        hours: model horizon in hours; 8760 is a year. Every hourly profile
            must have exactly this many values. Shorter horizons are for tests.
        storage_closes_the_year: every store ends the horizon at its initial
            level (soc_ini x capacity).
        thermo_bin: the thermodynamics executable to run -- and to hash into
            provenance. Defaults to the executable installed with the package
            (ies_optimiser/_bin/ies-optimiser-thermo, ies-optimiser-thermo.exe on Windows); any other path
            is an explicit override, recorded as such in provenance.
        thermo_timeout: seconds allowed for one thermodynamics calculation.
        profile_base: the directory against which RELATIVE profile paths in the
            case resolve. None (the default) means the directory of the input
            file the case came from; a case supplied in memory, with no input
            file, then accepts only inline, empty or absolute profiles. Set it
            to resolve against another directory -- for instance the directory
            an older input's repository-relative paths were written for.
            Absolute paths are never affected. There is no fallback: a profile
            is read from where this rule places it, or the case is refused.

    The fields are checked when a RunConfig is created: hours a positive
    integer, storage_closes_the_year a bool, thermo_timeout a finite positive
    number of seconds, thermo_bin and profile_base strings or path-like
    objects (stored as strings). Anything else raises InputError (layer
    'configuration', code 'config.invalid', field the name) -- a string such
    as 'false' is not a bool, and would otherwise have read as true.
    """
    hours: int = HOURS_PER_YEAR
    storage_closes_the_year: bool = STORAGE_CLOSES_THE_YEAR
    thermo_bin: str = Thermo_bin
    thermo_timeout: float = Thermo_timeout
    profile_base: Optional[str] = None

    def __post_init__(self) -> None:

        def refuse(field: str, message: str) -> None:
            raise InputError('\'' + field + '\' ' + message + ', got ' + repr(getattr(self, field)),
                             entity='RunConfig', field=field, code='config.invalid', layer='configuration')

        def path(field: str, optional: bool) -> None:
            value = getattr(self, field)
            if value is None and optional:
                return
            if isinstance(value, bytes) or not isinstance(value, (str, os.PathLike)):
                refuse(field, 'must be a path (a string or path-like object)' + (' or None' if optional else ''))
            text = os.fspath(value)
            if not isinstance(text, str) or text == '':
                refuse(field, 'must be a non-empty text path')
            object.__setattr__(self, field, text)          # frozen: normalised once, here

        if isinstance(self.hours, bool) or not isinstance(self.hours, numbers.Integral) or self.hours < 1:
            refuse('hours', 'must be a positive integer')
        object.__setattr__(self, 'hours', int(self.hours))
        if not isinstance(self.storage_closes_the_year, bool):
            refuse('storage_closes_the_year', 'must be True or False')
        timeout = self.thermo_timeout
        if isinstance(timeout, bool) or not isinstance(timeout, numbers.Real) or not math.isfinite(timeout) \
                or timeout <= 0:
            refuse('thermo_timeout', 'must be a finite positive number of seconds')
        path('thermo_bin', optional=False)
        path('profile_base', optional=True)

# Recognised run options, their meanings and admissible values are defined
# once, by models.SolveOptions: a carbon target may be negative (net removal);
# a reliability cap is a share.


def as_profile(profile, who, hours=HOURS_PER_YEAR, base=None, field='profile', path=None):

    """
    Validate and return an hourly profile as a 1-D float array, or None when a
    flat profile is requested (the empty string).

    Accepts a CSV path (resolved by resolve_profile against `base`), a list or
    a NumPy array, and applies the same checks to
    all three: one dimension, exactly `hours` entries, every value finite and
    non-negative, and a strictly positive sum. A profile failing any of these
    has no defined normalisation, so it is rejected here with a reason rather
    than propagated into the optimisation. Refusals carry layer 'profiles', a
    'profile.*' code and `path` (a JSON Pointer to the field), and name the
    first offending hour (zero-based) where there is one.
    """

    def refuse(message, code, hour=None):
        fail(who, message, field=field, hour=hour, code=code, layer='profiles', path=path)

    # Test the type before comparing with '': a NumPy array compared against a
    # string returns an array, and using that as a truth value raises.

    if isinstance(profile, str):

        if profile == '':

            return None

        resolved = resolve_profile(profile, base, who, field, path)

        try:

            data = np.loadtxt(resolved, dtype=float)

        except Exception:

            refuse('could not read profile \'' + profile + '\' (resolved to \'' + resolved + '\')', 'profile.unreadable')

    elif isinstance(profile, (list, np.ndarray)):

        try:

            data = np.asarray(profile, dtype=float)

        except Exception:

            refuse('profile is not numeric', 'profile.type')

    else:

        refuse('profile must be a file path, a list or an array', 'profile.type')

    data = np.atleast_1d(data)

    if data.ndim != 1:

        refuse('profile must be one-dimensional, got ' + str(data.ndim) + ' dimensions', 'profile.dimensions')

    if len(data) != hours:

        refuse('profile must have ' + str(hours) + ' entries, got ' + str(len(data)), 'profile.length')

    if not np.all(np.isfinite(data)):

        i = int(np.argmin(np.isfinite(data)))

        refuse('profile contains non-finite values (first at hour ' + str(i) + ')', 'profile.not_finite', i)

    if np.any(data < 0):

        i = int(np.argmax(data < 0))

        refuse('profile contains negative values (first at hour ' + str(i) + ')', 'profile.negative', i)

    if not np.sum(data) > 0:

        refuse('profile sums to zero, so it cannot be normalised', 'profile.zero_sum')

    return data


def resolve_profile(path, base, who, field='profile', pointer=None):

    """
    The file a declared profile path refers to, as an absolute path.

    An absolute path is used as it is. A relative path is joined to `base`, the
    case's profile directory (RunConfig.profile_base, set by solve()); with no
    base it cannot be resolved and the case is refused. The working directory
    is never consulted, and no other location is tried: a file that is not
    where the rule places it is an error naming the field, the declared path
    and the location looked at.
    """

    if os.path.isabs(path):

        resolved = path

    elif base is None:

        fail(who, 'relative profile path \'' + path + '\' (field \'' + field + '\') cannot be resolved: '
             'the case has no input file and no profile_base was given', field=field,
             code='profile.unresolvable', layer='profiles', path=pointer)

    else:

        resolved = os.path.normpath(os.path.join(base, path))

    if not os.path.isfile(resolved):

        fail(who, 'profile file not found: \'' + path + '\' (field \'' + field + '\', resolved to \''
             + resolved + '\')', field=field, code='profile.not_found', layer='profiles', path=pointer)

    return resolved


def fail(who, message, field=None, hour=None, *, code='input.invalid', layer='semantics', path=None):

    """Refuse an input: raise InputError naming the entity (and field, hour),
    with a stable diagnostic code, its layer and a JSON Pointer path."""

    raise InputError(message, entity=who, field=field, hour=hour, code=code, layer=layer, path=path)


def parse_options(args: Sequence[str]) -> Dict[str, float]:

    """
    Parse 'name=value' command-line options, refusing anything that is not one.

    An unrecognised name used to be accepted and ignored, so a misspelt
    constraint silently removed itself from the model while still appearing in
    the output file name and provenance. A bare 'name value' pair was dropped
    without trace. Every argument must now be a recognised name, given once,
    with a numeric value; its admissible range is checked by
    formats.validate_options (models.SolveOptions). Order is kept: it sets the
    result file name.
    """

    from ies_optimiser.formats import validate_options
    from ies_optimiser.models import SolveOptions

    names = SolveOptions.names()

    def refuse(message, code, field=None):
        fail('command line', message, field=field, code=code, layer='options')

    opts = {}

    for arg in args:

        if '=' not in arg:

            refuse('argument \'' + arg + '\' is not of the form name=value (recognised: ' + ', '.join(names) + ')',
                   'option.syntax')

        name, text = arg.split('=', 1)

        if name not in names:

            refuse('unknown option \'' + name + '\' (recognised: ' + ', '.join(names) + ')', 'option.unknown', name)

        if name in opts:

            refuse('option \'' + name + '\' given more than once', 'option.repeated', name)

        try:

            opts[name] = float(text)

        except ValueError:

            refuse('value of \'' + name + '\' is not a number: \'' + text + '\'', 'value.type', name)

    return validate_options(opts)


def output_path(json_file: Any, opts: Mapping[str, float]) -> str:

    """
    The result path: beside the input, '.json' replaced by '.ies-optimiser.json', with
    one '.name_value' segment per option in the order given.

    Only the file name's own suffix is replaced. Replacing '.json' anywhere in
    the path rewrote directory names that happened to contain it.
    """


    folder, name = os.path.split(str(json_file))

    stem = name[:-len('.json')] if name.endswith('.json') else name

    stem += '.ies-optimiser' + ''.join('.' + str(k) + '_' + str(v) for k, v in opts.items())

    return os.path.join(folder, stem + '.json')


def file_digest(path):

    # SHA-256 of a file, or None if it cannot be read.


    import hashlib
    import os

    if not (isinstance(path, str) and path and os.path.isfile(path)):

        return None

    h = hashlib.sha256()

    with open(path, 'rb') as f:

        for block in iter(lambda: f.read(1 << 16), b''):

            h.update(block)

    return h.hexdigest()


def source_state(thermo_bin=Thermo_bin):

    """
    Identify the code that is actually running.

    A version constant is a label, not an identifier: two trees can carry the
    same string and different source. Four things are recorded instead, and
    they are complementary. The installation says how the running package got
    there (a wheel, an editable install, a source tree) and its distribution
    version. The Git revision says which commit, when IES Optimiser runs from its own
    checkout, and the dirty flag whether the tree still matches it. The source
    digest covers every module of the running package, so an installation
    without Git is still identified, and it includes the thermodynamics
    executable actually run, which sets the cogeneration coefficients directly.
    """

    import hashlib

    install = _install.installation()

    root = install['checkout']

    def git(*args):

        try:

            out = subprocess.run(('git', '-C', root) + args, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True, timeout=10)

            return out.stdout.strip() if out.returncode == 0 else None

        except Exception:

            return None

    # Git is consulted only for a source checkout (editable or source): an
    # installed wheel has no revision of its own, and the repository enclosing
    # a virtual environment or a vendored copy says nothing about IES Optimiser. Within
    # a checkout, only a repository whose top level is the checkout's root
    # describes IES Optimiser; an enclosing one is recorded as such, separately.

    scope = None

    revision = None

    dirty = None

    enclosing = None

    toplevel = git('rev-parse', '--show-toplevel') if root is not None else None

    if toplevel is not None:

        head = git('rev-parse', 'HEAD')

        porcelain = git('status', '--porcelain')

        state = bool(porcelain) if porcelain is not None else None

        if os.path.realpath(toplevel) == os.path.realpath(root):

            scope, revision, dirty = 'ies_optimiser', head, state

        else:

            scope = 'enclosing'

            enclosing = {'toplevel': toplevel, 'revision': head, 'dirty': state}

    # Source digest: every module of the running package, plus the
    # thermodynamics executable, hashed in a fixed order.

    package = install['package_dir']

    sources = [os.path.join(package, n) for n in sorted(os.listdir(package)) if n.endswith('.py')]

    files = {}

    digest = hashlib.sha256()

    # The executable is keyed as thermo/sim.bin whatever its location and
    # name, so digests remain comparable; its actual path is recorded beside
    # them, with whether it is the packaged one or an override.

    for path in sources + [thermo_bin]:

        rel = 'thermo/sim.bin' if path == thermo_bin else 'ies_optimiser/' + os.path.basename(path)

        one = file_digest(path)

        files[rel] = one

        digest.update(rel.encode())

        digest.update((one or 'absent').encode())

    return {
        'installation': {'kind': install['kind'], 'package_dir': package},
        'git_scope': scope,
        'git_revision': revision,
        'git_dirty': dirty,
        'enclosing_git': enclosing,
        'source_sha256': digest.hexdigest(),
        'source_files_sha256': files,
        'thermo_binary': thermo_bin,
        'thermo_binary_origin': 'packaged' if thermo_bin == Thermo_bin else 'override',
    }


def provenance(json_file: Optional[str], opts: Mapping[str, float], s: Dict[str, Any], cfg: RunConfig = RunConfig(),
               profile_mode: Optional[str] = None) -> Dict[str, Any]:

    """
    Identify what produced a result: the code, the inputs, the options and the
    environment.

    A result that cannot be traced to the code and data behind it cannot be
    reproduced or superseded with confidence. Profiles are hashed alongside the
    input file because they determine the answer just as directly, and they are
    referenced by path rather than carried inside it.
    """


    import datetime
    import platform

    profile_base = cfg.profile_base

    # Declared references, as written in the case, in a fixed order.
    declared = []

    for group in ('generator', 'p2x'):

        for item in s.get(group, []):

            declared.append((item.get('iden'), 'profile', item.get('profile', '')))

    for item in s.get('flex', []):

        declared.append((item.get('iden'), 'inflow_profile', item.get('inflow_profile', '')))

    declared.append(('demand.e', 'profile', s['demand']['e'].get('profile', '')))

    for dmd in s['demand'].get('x', []):

        declared.append(('demand.x[' + str(dmd.get('iden')) + ']', 'profile', dmd.get('profile', '')))

    # The files consumed: each declared path resolved exactly as the model
    # resolved it (resolve_profile, same base), and hashed at that location.
    profiles = {}

    profile_files = {}

    for who, field, path in declared:

        if not (isinstance(path, str) and path):

            continue

        if os.path.isabs(path) or profile_base is not None:

            resolved = path if os.path.isabs(path) else os.path.normpath(os.path.join(profile_base, path))

        else:

            resolved = None

        digest = file_digest(resolved) if resolved else None

        profiles[path] = digest

        profile_files[path] = {'resolved': resolved, 'sha256': digest}

    try:

        import ortools.init.python.init as _ort

        solver_version = _ort.OrToolsVersion.version_string()

    except Exception:

        solver_version = 'unknown'

    stamp = {
        'ies_optimiser_version': _install.version(),
        'input': str(json_file),
        'input_resolved': os.path.abspath(str(json_file)) if json_file is not None else None,
        'input_sha256': file_digest(json_file),
        'profiles_sha256': profiles,
        'profile_files': profile_files,
        'profile_resolution': {'mode': profile_mode, 'base': profile_base},
        'options': dict(opts),
        'hours': cfg.hours,
        'storage_closes_the_year': cfg.storage_closes_the_year,
        'solver': 'GLOP',
        'ortools': solver_version,
        'numpy': np.__version__,
        'python': platform.python_version(),
        'platform': platform.platform(),
        'run_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    stamp.update(source_state(cfg.thermo_bin))

    return stamp


def load(csv_path, hours=HOURS_PER_YEAR):

    # Load time series data from a CSV file and validate it
    # csv_path: Path to the CSV file.
    # The file is expected to contain a single column of numerical values without a header.


    try:

        data = np.loadtxt(csv_path, dtype=float)

        if len(data) != hours:

            # the number of rows does not match the horizon (8760)

            return None, None, True

        else:

            return data, np.any(data < 0), False

    except:

        return None, None, True


def normalize(hpro, cp):

    # Normalise a time series profile and scale it to a specified capacity factor.


    max_ = np.max(hpro)
    npro = hpro / max_
    sum_ = np.sum(npro)
    cor_ = cp / (sum_ / len(hpro))
    npro = cor_ * npro

    return npro


def dm_h(profile, total, who='dm_h', hours=HOURS_PER_YEAR, base=None, field='profile'):

    """
    Build an hourly demand series (output) such that its sum equals 'total'.
    sum(output) = total

    Parameters
    ----------
    profile : str | list | np.ndarray
        - If a string: path to a CSV file containing a single-column hourly profile with `hours` rows.
        - If a list or NumPy array: array of `hours` numerical values (new feature).
        - If empty string: a flat profile is used.
    total : float
        Total annual demand (MWh, etc.)

    Returns
    -------
    output : list of floats
        Normalised hourly demand profile scaled so that sum(output) = total.
    """


    data = as_profile(profile, who, hours, base, field)

    if data is None:

        output = np.full(hours, total / hours).tolist()

    else:

        output = ((total / np.sum(data)) * data).tolist()

    output = np.array(output, dtype=float).tolist()

    return output


def shortfall_bounds(dm, l_ns, who, path=None):

    """
    Hourly bounds on unmet demand: l_ns[0] <= unmet[i] <= min(l_ns[1], dm[i]).

    Unmet demand cannot exceed demand. On the electricity balance an unbounded
    shortfall offsets process consumption, so shedding demand that never
    existed could power a process; on a product balance it let served demand go
    negative. A lower bound above the demand of any hour asks for more to be
    unmet than was demanded, and is refused, naming the first such hour.
    """


    low, high = float(l_ns[0]), float(l_ns[1])

    bounds = []

    for i, d in enumerate(dm):

        if low > d + Balance_rtol * max(1.0, abs(d)):

            fail(who, 'l_ns lower bound ' + str(low) + ' exceeds the demand of hour ' + str(i)
                 + ' (' + str(d) + '): unmet demand cannot exceed demand', field='l_ns', hour=i,
                 code='shortfall.exceeds_demand', path=path)

        bounds.append((low, max(low, min(high, d))))

    return bounds


def cf_h(profile, capacity_factor, who='cf_h', hours=HOURS_PER_YEAR, base=None, field='profile'):

    """
    Build an hourly availability series normalised to target 'capacity_factor'.
    mean(output) = capacity_factor

    The supplied profile contributes its shape only: it is divided by its own
    maximum and then rescaled so that its mean equals capacity_factor. The level
    is therefore set by capacity_factor, not by the profile. A profile whose own
    mean/max ratio is below capacity_factor will consequently peak above one.
    """


    data = as_profile(profile, who, hours, base, field)

    if data is None:

        output = np.full(hours, capacity_factor).tolist()

    else:

        output = normalize(data, capacity_factor)

    output = np.array(output, dtype=float).tolist()

    return output


def thermo(Temperature_Turbine_Inlet, Pressure_Turbine_Inlet, Pressure_Condenser_Inlet, Steam_Temperature,
           *, binary=Thermo_bin, timeout=Thermo_timeout):

    """
    Cogeneration coefficients (a, b) from the thermodynamics executable.

    Returns (a, b, False) on success, or (-1, -1, reason) where reason says
    why no admissible coefficients were obtained. The executable is resolved
    from an absolute path (`binary`, default the executable installed with the
    package, ies_optimiser/_bin/ies-optimiser-thermo), never from the working directory, and it
    is the same file source_state() hashes when given the same `binary`.

    Admissible coefficients satisfy 0 < a < 1, b > 0 and a * b < 1: heat
    costs some electricity but less than its own energy, and at full heat
    extraction the plant still produces electricity (a * b is the share of
    unextracted output lost when all steam is extracted).
    """


    args = [binary] + [repr(float(v)) for v in (Temperature_Turbine_Inlet, Pressure_Turbine_Inlet,
                                                    Pressure_Condenser_Inlet, Steam_Temperature)]

    if not os.path.isfile(binary):

        return -1, -1, ('thermodynamics executable not found at ' + binary
                        + ' (it is installed with IES Optimiser; reinstall, or see the setup guide to build it)')

    try:

        out = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             timeout=timeout)

    except subprocess.TimeoutExpired:

        return -1, -1, 'thermodynamics executable timed out after ' + str(timeout) + ' s'

    except OSError as e:

        return -1, -1, 'thermodynamics executable could not be run: ' + str(e)

    if out.returncode != 0:

        return -1, -1, ('thermodynamics executable exited with status ' + str(out.returncode)
                        + ': ' + (out.stderr.strip() or 'no message'))

    tokens = out.stdout.split()

    try:

        if len(tokens) != 2:

            raise ValueError

        a, b = float(tokens[0]), float(tokens[1])

    except ValueError:

        return -1, -1, 'malformed output from the thermodynamics executable: \'' + out.stdout.strip() + '\''

    if not (math.isfinite(a) and math.isfinite(b)):

        return -1, -1, 'non-finite coefficients a = ' + str(a) + ', b = ' + str(b)

    if not (0.0 < a < 1.0 and b > 0.0 and a * b < 1.0):

        return -1, -1, ('coefficients a = ' + str(a) + ', b = ' + str(b)
                        + ' are not admissible (need 0 < a < 1, b > 0, a*b < 1)')

    return a, b, False


def capaSetToBeOptimised(variable):


    isSetToBeOptimised = not isinstance(variable, (int, float))

    return isSetToBeOptimised

