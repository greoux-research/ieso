#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

"""The Python API: load an input, validate it, solve it, write the result.

    from ies_optimiser.api import load_input, validate, solve, write_result

    path = 'datasets/elec-grid/elec-grid.json'
    report = validate(path)                                     # nothing is solved or written
    if not report.valid:
        for d in report.diagnostics:
            print(d.code, d.path, d.message)
    result = solve(path, options={'carbon-constraint': 50.0})
    if result.optimal and result.accounting_ok:
        print(result.document['system']['cost'])                 # USD per year
    write_result(result, 'runs/elec-grid.ies-optimiser.carbon-constraint_50.0.json')

A case may be given as a path, as a parsed JSON document (canonical, with
"format_version": 1, or an unversioned legacy document), or as a
models.Case. Importing this module reads nothing, solves nothing, prints
nothing, writes nothing and never exits. Nothing is written unless
write_result() is called. The model, its equations, their construction order
and the result format are those of the command line (ies-optimiser INPUT.json
...), which is a thin wrapper around these functions. See docs/ies-optimiser-api.md.

Not established: thread safety. Separate calls share no mutable state in
IES Optimiser itself, but concurrent solves in one process have not been tested.
"""

import dataclasses
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import numpy as np
from ortools.linear_solver import pywraplp

from ies_optimiser import chk, eqs_dmd_e, eqs_dmd_x, eqs_flx, eqs_gen, eqs_p2x_1, eqs_p2x_2, formats, obj, opt, pos
from ies_optimiser import fcn as u
from ies_optimiser.errors import Diagnostic, IesOptimiserError, InputError, ThermoError
from ies_optimiser.models import Case
from ies_optimiser.results import RESULT_FORMAT_VERSION

PathLike = Union[str, 'os.PathLike[str]']
CaseLike = Union[Case, Mapping[str, Any], PathLike]


@dataclass(frozen=True)
class SolveResult:
    """The outcome of one solve.

    Attributes
    ----------
    document : dict
        The result, a fresh JSON-compatible dictionary with the structure the
        command line writes (docs/ies-optimiser-io-file-structure.md; JSON Schema:
        ies_optimiser/data/ies-optimiser-result-1.schema.json). When the solve was not optimal it
        holds the case's input fields, the solver status and provenance, and
        no results.
    status : str
        'optimal', 'infeasible', 'unbounded', 'abnormal (numerical trouble)',
        'feasible but not proven optimal' or 'not solved'.
    optimal : bool
        Whether the solver proved an optimal solution.
    accounting_ok : bool or None
        Whether every check in document['system']['checks'] passed; None when
        the solve was not optimal (no accounts exist).
    objective : float or None
        The solver's objective value (USD per year; it omits fixed charges on
        capacities fixed by the input), or None if not optimal.
    """
    document: Dict[str, Any]
    status: str
    optimal: bool
    accounting_ok: Optional[bool]
    objective: Optional[float]


@dataclass(frozen=True)
class ValidationReport:
    """The outcome of validate(): nothing solved, nothing written.

    Attributes
    ----------
    valid : bool
        True when every stage that ran passed.
    format : str or None
        'canonical' or 'legacy'; None when the document could not be read.
    diagnostics : list of Diagnostic
        Every problem found. Structural validation reports all its problems;
        the later stages stop at the first.
    stages : dict
        Stage name -> 'passed', 'failed', 'not run' or 'not required', for the
        stages 'file', 'options', 'structure', 'semantics' (identifiers,
        references, topology, profiles, hourly shortfall bounds) and
        'thermodynamics'.
    removed_fields : list of str
        JSON Pointers of the output-only fields removed from a legacy document.
    profile_resolution : dict
        {'mode': ..., 'base': ...}, as recorded in a result's provenance.
    case : models.Case or None
        The validated model, when the structure is valid.
    """
    valid: bool
    format: Optional[str]
    diagnostics: List[Diagnostic]
    stages: Dict[str, str]
    removed_fields: List[str] = field(default_factory=list)
    profile_resolution: Dict[str, Optional[str]] = field(default_factory=dict)
    case: Optional[Case] = None

    def to_dict(self) -> Dict[str, Any]:
        """A JSON-compatible summary (the model itself is not included)."""
        return {'valid': self.valid, 'format': self.format, 'stages': dict(self.stages),
                'diagnostics': [d.to_dict() for d in self.diagnostics],
                'removed_fields': list(self.removed_fields),
                'profile_resolution': dict(self.profile_resolution)}


def load_input(path: PathLike) -> Dict[str, Any]:
    """Read an IES Optimiser input (or result) JSON file.

    Only parses the file; validation happens in parse_case(), validate() and
    solve(). Profile paths inside the input are left as written. When the case
    is solved, relative ones are resolved against the directory of the file it
    came from -- pass the path to solve() (as `case`, or as `source` with the
    parsed document).

    Raises
    ------
    InputError
        The file cannot be read or is not valid JSON (layer 'file', code
        'input.unreadable', ``entity`` the path).
    """
    try:
        with open(path, 'r') as f:
            document: Dict[str, Any] = json.load(f)
            return document
    except (OSError, ValueError) as e:
        raise InputError('could not load: ' + str(e), entity=str(path), code='input.unreadable',
                         layer='file') from e


def parse_case(case: Union[Case, Mapping[str, Any]]) -> Case:
    """Validate a case's structure and return it as a models.Case.

    Accepts a canonical document, a legacy document (its documented output
    placeholders are removed; see formats.from_legacy) or a Case. One-dimensional
    NumPy arrays are accepted as profiles. Only the structure is checked:
    identifiers, references, profiles and thermodynamics are checked by
    validate() and solve().

    Raises
    ------
    InputError
        One Diagnostic per structural problem found.
    """
    return formats.parse(case)[0]


def to_canonical(case: Union[Case, Mapping[str, Any]]) -> Dict[str, Any]:
    """The canonical (format_version 1) JSON document of a case in either
    format: inputs only, every default explicit, numbers as given.

    Raises
    ------
    InputError
        The structure is invalid.
    """
    return formats.canonical_document(parse_case(case))


def check_options(options: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    """Validate run options, returning them as floats in the order given.

    Names and admissible values are those of models.SolveOptions:
    'carbon-constraint' (kg CO2eq per MWh of primary annual electricity demand,
    any finite value) and 'non-served-power-constraint' (a fraction in [0, 1]).

    Raises
    ------
    InputError
        An unknown name, a non-numeric or non-finite value, or a value outside
        its range (layer 'options', ``entity`` 'command line', ``field`` the name).
    """
    if not options:
        return {}
    return formats.validate_options(options)


def _source(case: CaseLike, source: Optional[PathLike]) -> Tuple[Union[Case, Mapping[str, Any]], Optional[PathLike]]:
    # A path is loaded; it is then the source. A contradicting source= is refused.
    if isinstance(case, (str, os.PathLike)):
        if source is not None and os.path.abspath(str(source)) != os.path.abspath(str(case)):
            raise InputError('the case was given as \'' + str(case) + '\' but source= names \''
                             + str(source) + '\'; give one or make them agree', entity='source',
                             code='config.conflict', layer='configuration')
        return load_input(case), case
    return case, source


def _profile_base(cfg: u.RunConfig, source: Optional[PathLike]) -> Tuple[u.RunConfig, str]:
    # Where relative profile paths resolve, fixed once for this case.
    base: Optional[str]
    if cfg.profile_base is not None:
        base, mode = os.path.abspath(str(cfg.profile_base)), 'explicit'
        if not os.path.isdir(base):
            raise InputError('profile_base \'' + str(cfg.profile_base) + '\' is not a directory (resolved to \''
                             + base + '\')', entity='profile_base', code='config.profile_base',
                             layer='configuration')
    elif source is not None:
        base, mode = os.path.dirname(os.path.abspath(str(source))), 'input-directory'
    else:
        base, mode = None, 'none'
    return dataclasses.replace(cfg, profile_base=base), mode


def validate(case: CaseLike, *, options: Optional[Mapping[str, Any]] = None,
             config: Optional[u.RunConfig] = None, source: Optional[PathLike] = None,
             thermodynamics: bool = True) -> ValidationReport:
    """Validate a case completely, without building or solving the problem.

    Runs, in order: reading the file, the options, the structure (models.Case,
    reporting every problem found), then the semantic checks of
    ies_optimiser/chk.py -- identifiers, references, topology, profiles
    (resolved exactly as solve() resolves them, then read and checked) and
    hourly shortfall bounds -- and finally, with `thermodynamics`, the
    cogeneration coefficients of every heat-supplying unit, which runs the
    thermodynamics executable (config.thermo_bin). A later stage runs only
    when the earlier ones passed.

    Parameters are those of solve(). Nothing is solved and no file is written.

    Returns
    -------
    ValidationReport
        Never raises for a problem with the case, the options or the
        configuration: those are reported as diagnostics.
    """
    cfg = config if config is not None else u.RunConfig()
    stages = {k: 'not run' for k in ('file', 'options', 'structure', 'semantics', 'thermodynamics')}
    fmt: Optional[str] = None
    removed: List[str] = []
    model: Optional[Case] = None
    resolution: Dict[str, Optional[str]] = {}

    def report(error: Optional[IesOptimiserError], stage: Optional[str]) -> ValidationReport:
        if stage is not None:
            stages[stage] = 'failed'
        return ValidationReport(valid=error is None, format=fmt, diagnostics=list(error.diagnostics) if error else [],
                                stages=stages, removed_fields=removed, profile_resolution=resolution, case=model)

    try:
        document, source = _source(case, source)
    except InputError as e:
        return report(e, 'file')
    stages['file'] = 'passed' if source is not None else 'not required'
    try:
        opts = check_options(options)
    except InputError as e:
        return report(e, 'options')
    stages['options'] = 'passed'
    try:
        fmt = formats.CANONICAL if isinstance(document, Case) else formats.detect(document)
        model, fmt, removed = formats.parse(document)
    except InputError as e:
        return report(e, 'structure')
    stages['structure'] = 'passed'
    try:
        run, mode = _profile_base(cfg, source)
    except InputError as e:
        return report(e, 'semantics')
    resolution = {'mode': mode, 'base': run.profile_base}
    s = formats.internal_document(model)
    try:
        chk.validate(s, opts, run)
    except InputError as e:
        return report(e, 'semantics')
    stages['semantics'] = 'passed'
    suppliers = chk.heat_suppliers(s)
    if not suppliers:
        stages['thermodynamics'] = 'not required'
    elif thermodynamics:
        try:
            for n, gen, p2x in suppliers:
                chk.cogeneration(gen, p2x, run, path=formats.pointer('generator', n))
        except ThermoError as e:
            return report(e, 'thermodynamics')
        stages['thermodynamics'] = 'passed'
    return report(None, None)


def solve(case: CaseLike, *,
          options: Optional[Mapping[str, Any]] = None,
          config: Optional[u.RunConfig] = None,
          source: Optional[PathLike] = None) -> SolveResult:
    """Build and solve one IES Optimiser case.

    Parameters
    ----------
    case : models.Case, dict or path
        The input: a Case, a parsed document (canonical or legacy) or a path to
        a JSON file.
    options : mapping, optional
        Run options, e.g. {'carbon-constraint': 50.0,
        'non-served-power-constraint': 0.05}; see check_options().
    config : RunConfig, optional
        Horizon, storage closure, thermodynamics and profile-base settings for
        this run; defaults to a year of 8,760 hours, closed storage, the
        thermodynamics executable installed with the package
        (ies_optimiser/_bin/ies-optimiser-thermo) with a 30 s timeout, and profiles resolved
        against the input file's directory.
    source : path, optional
        The file the case came from, recorded (with its SHA-256) in the
        result's provenance; its directory is where relative profile paths
        resolve unless config.profile_base says otherwise. Set automatically
        when `case` is a path. Without it, provenance records the input as
        '<in-memory>' with the SHA-256 of its canonical JSON serialisation,
        and relative profile paths need config.profile_base.

    Profile paths: absolute paths are used as written; relative paths resolve
    against config.profile_base if set ('explicit'), otherwise against the
    source file's directory ('input-directory'); an in-memory case with neither
    accepts only inline, empty or absolute profiles ('none'). The working
    directory is never used, and no other location is tried.

    Returns
    -------
    SolveResult
        Check ``optimal`` and then ``accounting_ok`` before reading any
        figure. An infeasible or otherwise unsuccessful solve is a status, not
        an exception.

    Side effects: none on the caller's data -- the case, including nested
    lists, dicts and arrays, is copied before use and left unchanged. No file
    is written. Diagnostics go to the 'ies_optimiser' logger.

    Raises
    ------
    InputError
        The case, the options or the configuration are outside the contract,
        or a profile cannot be found where the rule places it; nothing is
        solved. Its diagnostics carry the code, path, entity and hour.
    ThermoError
        Cogeneration coefficients could not be obtained for a heat-supplying
        unit.
    """
    cfg = config if config is not None else u.RunConfig()
    document_in, source = _source(case, source)
    opts = check_options(options)
    model, fmt, _ = formats.parse(document_in)
    cfg, profile_mode = _profile_base(cfg, source)

    work = formats.internal_document(model)          # private: gains solver objects below
    stat = {'time': time.time(), 'capa': 0, 'outp': 0, 'cons': 0}

    glop = pywraplp.Solver.CreateSolver('GLOP')
    objective = glop.Objective()
    objective.SetMinimization()

    chk.define(glop, work, opts, stat, cfg)
    eqs_p2x_1.define(glop, work, opts, stat, cfg)
    eqs_gen.define(glop, work, opts, stat, cfg)
    eqs_p2x_2.define(glop, work, opts, stat, cfg)
    eqs_flx.define(glop, work, opts, stat, cfg)
    emis_con, nspo_con = eqs_dmd_e.define(glop, work, opts, stat, cfg)
    eqs_dmd_x.define(glop, work, opts, stat, cfg)

    obj.define(objective, work, cfg)

    success = opt.run(glop, work, opts, stat)
    stat['time'] = time.time() - stat['time']

    document: Dict[str, Any]
    if success:
        work['solver']['stat_succ'] = 1
        pos.process(glop, work, opts, stat, emis_con, nspo_con, cfg)
        document = work
        objective_value: Optional[float] = objective.Value()
    else:
        # The case's input fields only: no output placeholders, which could be
        # mistaken for results. The working copy is discarded.
        document = formats.input_document(model)
        document['solver'] = {'stat_succ': 0}
        objective_value = None

    document['provenance'] = u.provenance(None if source is None else str(source), opts, document, cfg, profile_mode)
    if source is None:
        document['provenance']['input'] = '<in-memory>'
        in_memory = formats.canonical_document(document_in) if isinstance(document_in, Case) else document_in
        document['provenance']['input_sha256'] = hashlib.sha256(
            json.dumps(_jsonable(in_memory), sort_keys=True).encode()).hexdigest()
    document['provenance']['input_format'] = fmt
    document['provenance']['result_format_version'] = RESULT_FORMAT_VERSION
    # input_sha256 identifies the file named as the source (or, in memory, the
    # document as given); the case actually solved may differ from that file --
    # a scenario edited in memory -- so it is identified on its own.
    case_digest = _case_digest(model)
    document['provenance']['case_sha256'] = case_digest
    document['provenance']['source_matches_case'] = None if source is None else \
        _source_digest(source) == case_digest

    document['solver']['stat_status'] = stat.get('status', 'unknown')
    document['solver']['stat_time'] = stat['time']
    document['solver']['stat_capa'] = stat['capa']
    document['solver']['stat_outp'] = stat['outp']
    document['solver']['stat_cons'] = stat['cons']

    document = _jsonable(document)
    return SolveResult(document=document, status=document['solver']['stat_status'], optimal=bool(success),
                       accounting_ok=document['system']['accounting_ok'] if success else None,
                       objective=objective_value)


def _case_digest(model: Case) -> str:
    """SHA-256 of the case's canonical JSON (inputs only, every default
    explicit, keys sorted): the same for a legacy document and its canonical
    form, different whenever any input value differs."""
    text = json.dumps(formats.canonical_document(model), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _source_digest(source: PathLike) -> Optional[str]:
    # The canonical digest of the source file as read now, or None if it no
    # longer reads as a valid case.
    try:
        return _case_digest(formats.parse(load_input(source))[0])
    except IesOptimiserError:
        return None


def write_result(result: Union[SolveResult, Mapping[str, Any]], path: PathLike) -> None:
    """Write a result as JSON (4-space indented, as the command line does)."""
    document = result.document if isinstance(result, SolveResult) else result
    with open(path, 'w') as f:
        json.dump(document, f, indent=4)


def output_path(input_path: PathLike, options: Optional[Mapping[str, float]] = None) -> str:
    """The command line's result path: beside the input, '.json' -> '.ies-optimiser.json',
    one '.name_value' segment per option, in the order given."""
    return u.output_path(input_path, dict(options or {}))


def _jsonable(node: Any) -> Any:
    """A copy of `node` in plain JSON types; anything else is a defect and raises."""
    if isinstance(node, dict):
        return {str(k): _jsonable(v) for k, v in node.items()}
    if isinstance(node, (list, tuple)):
        return [_jsonable(v) for v in node]
    if isinstance(node, np.ndarray):
        return [_jsonable(v) for v in node.tolist()]
    if isinstance(node, (bool, np.bool_)):
        return bool(node)
    if isinstance(node, (int, np.integer)):
        return int(node)
    if isinstance(node, (float, np.floating)):
        return float(node)
    if node is None or isinstance(node, str):
        return node
    raise TypeError('result holds a non-JSON value of type ' + type(node).__name__)
