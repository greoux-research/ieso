#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""Input formats: canonical and legacy documents, and the model's working copy.

Two input formats are read:

* canonical -- a document with ``"format_version": 1``. It holds inputs only
  and is validated directly against ieso.models.Case.
* legacy -- a document without ``format_version``: every input written before
  the canonical format existed, including the bundled datasets. Such inputs
  carry output placeholders (empty output arrays, -1 KPIs, solver statistics).
  from_legacy() removes exactly the output-only fields listed in
  LEGACY_OUTPUT_FIELDS and nothing else; any other unknown field is left in
  place, and structural validation then refuses it.

Any other ``format_version`` is refused. This module also holds the boundary
adapter that turns one-dimensional NumPy arrays given as profiles into lists,
the translation of Pydantic's errors into IESO diagnostics, and the builder of
the working dictionary the equation modules read.
"""

import copy
import json
from typing import Any, Dict, List, Mapping, Sequence, Tuple, Union

import numpy as np
from pydantic import ValidationError

from ieso.errors import Diagnostic, InputError
from ieso.models import INPUT_FORMAT_VERSION, Case, SolveOptions

CANONICAL = 'canonical'
LEGACY = 'legacy'

# Output-only fields a legacy input may carry, per object. 'array' fields must
# be absent or empty lists: one that holds values means the document is a
# result, which is refused as before. 'object' fields must be JSON objects
# (placeholders such as kpis {-1, -1, -1}); their content is output and is
# discarded, except that any non-empty list inside marks a result. 'any'
# fields are discarded whatever they hold (a and b were always overwritten).
LEGACY_OUTPUT_FIELDS: Dict[str, Dict[str, str]] = {
    'case': {'solver': 'object', 'provenance': 'object'},
    'demand': {'output_ns': 'array', 'shadow_prices': 'object', 'kpis': 'object'},
    'generator': {'e_prod': 'array', 'h_prod': 'array', 'a': 'any', 'b': 'any'},
    'flex': {'e_strg': 'array', 'e_char': 'array', 'e_disc': 'array', 'e_spil': 'array'},
    'p2x': {'x_prod': 'array', 'x_strg': 'array', 'x_supp': 'array', 'shadow_prices': 'object'},
}

# Fields found only in results. In a legacy document they mean a result was
# given as an input, and are refused with that explanation.
RESULT_ONLY_FIELDS: Dict[str, Tuple[str, ...]] = {
    'case': ('system',),
    'demand': ('surplus', 'accounts'),
    'generator': ('availability',),
    'flex': (),
    'p2x': ('heat_surplus', 'availability'),
}

SOLVER_FIELDS = ('stat_succ', 'stat_status', 'stat_time', 'stat_capa', 'stat_outp', 'stat_cons')

# Where profiles live: (list key or None, field). Only these accept NumPy arrays.
PROFILE_FIELDS = (('generator', 'profile'), ('p2x', 'profile'), ('flex', 'inflow_profile'))


def pointer(*parts: Union[str, int]) -> str:
    """A JSON Pointer (RFC 6901) from path segments."""
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


# --- entity naming, shared with the semantic layer --------------------------------

def entity_of(document: Any, loc: Sequence[Union[str, int]]) -> str:
    """The entity name IESO uses for location `loc` in `document`: an
    identifier for generators, stores and processes, 'demand.e',
    'demand.x[<iden>]', or 'input' for the case itself."""
    def iden(item: Any, fallback: str) -> str:
        v = item.get('iden') if isinstance(item, dict) else None
        return v if isinstance(v, str) and v else fallback
    try:
        if len(loc) >= 2 and loc[0] in ('generator', 'flex', 'p2x') and isinstance(loc[1], int):
            return iden(document[loc[0]][loc[1]], str(loc[0]) + '[' + str(loc[1]) + ']')
        if len(loc) >= 2 and loc[0] == 'demand' and loc[1] == 'e':
            return 'demand.e'
        if len(loc) >= 3 and loc[0] == 'demand' and loc[1] == 'x' and isinstance(loc[2], int):
            return 'demand.x[' + iden(document['demand']['x'][loc[2]], str(loc[2])) + ']'
    except (KeyError, IndexError, TypeError):
        pass
    if len(loc) >= 2 and isinstance(loc[1], int):
        return str(loc[0]) + '[' + str(loc[1]) + ']'
    return 'input'


# --- the NumPy boundary ------------------------------------------------------------

def _plain(profile: Any) -> Any:
    if isinstance(profile, np.ndarray) and profile.ndim == 1 and profile.dtype.kind in 'iuf':
        return profile.tolist()
    return profile


def numpy_profiles_to_lists(document: Mapping[str, Any]) -> Dict[str, Any]:
    """A copy of `document` in which one-dimensional numeric NumPy arrays given
    as profiles are lists. Arrays anywhere else are left for validation to refuse."""
    doc = dict(document)
    for key, field in PROFILE_FIELDS:
        if isinstance(doc.get(key), (list, tuple)):
            doc[key] = [dict(item, **{field: _plain(item[field])}) if isinstance(item, dict) and field in item
                        else item for item in doc[key]]
    demand = doc.get('demand')
    if isinstance(demand, dict):
        demand = dict(demand)
        if isinstance(demand.get('e'), dict) and 'profile' in demand['e']:
            demand['e'] = dict(demand['e'], profile=_plain(demand['e']['profile']))
        if isinstance(demand.get('x'), (list, tuple)):
            demand['x'] = [dict(d, profile=_plain(d['profile'])) if isinstance(d, dict) and 'profile' in d else d
                           for d in demand['x']]
        doc['demand'] = demand
    return doc


# --- format detection and the legacy adapter -------------------------------------------

def detect(document: Any) -> str:
    """'canonical' or 'legacy'; raises InputError for anything else."""
    if not isinstance(document, Mapping):
        raise InputError('the case must be a JSON object, got ' + type(document).__name__, entity='input',
                         code='value.type', layer='structure', path='')
    if 'format_version' not in document:
        return LEGACY
    v = document['format_version']
    if type(v) is int and v == INPUT_FORMAT_VERSION:
        return CANONICAL
    raise InputError('unsupported format_version ' + repr(v) + '; this IESO reads format_version '
                     + str(INPUT_FORMAT_VERSION) + ', or an unversioned legacy input', entity='input',
                     field='format_version', code='format.unsupported_version', layer='format',
                     path=pointer('format_version'))


def _objects(document: Mapping[str, Any]) -> List[Tuple[str, Tuple[Union[str, int], ...], Dict[str, Any]]]:
    # (kind, location, object) for every object that may hold output fields.
    out: List[Tuple[str, Tuple[Union[str, int], ...], Dict[str, Any]]] = [('case', (), dict(document))]
    demand = document.get('demand')
    if isinstance(demand, dict):
        if isinstance(demand.get('e'), dict):
            out.append(('demand', ('demand', 'e'), demand['e']))
        if isinstance(demand.get('x'), list):
            out += [('demand', ('demand', 'x', n), d) for n, d in enumerate(demand['x']) if isinstance(d, dict)]
    for key in ('generator', 'flex', 'p2x'):
        if isinstance(document.get(key), list):
            out += [(key, (key, n), item) for n, item in enumerate(document[key]) if isinstance(item, dict)]
    return out


def _holds_values(node: Any) -> bool:
    if isinstance(node, list):
        return len(node) > 0
    if isinstance(node, dict):
        return any(_holds_values(v) for v in node.values())
    return False


def from_legacy(document: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Convert a legacy (unversioned) input to the canonical form.

    Removes the output-only fields of LEGACY_OUTPUT_FIELDS, adds
    ``format_version`` and returns ``(canonical document, removed paths)``.
    Input values, including their numeric types, are untouched; unknown fields
    are left for validation to refuse. A result given as an input is refused.

    Raises
    ------
    InputError
        Output fields that hold values or are of the wrong kind, or fields
        found only in results (layer 'format').
    """
    doc = copy.deepcopy(dict(document))
    problems: List[Diagnostic] = []
    removed: List[str] = []
    for kind, loc, item in _objects(doc):
        entity = entity_of(doc, loc)
        for field in RESULT_ONLY_FIELDS[kind]:
            if field in item:
                problems.append(Diagnostic(
                    code='input.is_result', layer='format', path=pointer(*loc, field), entity=entity, field=field,
                    message='\'' + field + '\' is found only in results; an input holds no results (is this a '
                    'result file?)'))
        for field, shape in LEGACY_OUTPUT_FIELDS[kind].items():
            if field not in item:
                continue
            v = item[field]
            where = pointer(*loc, field)
            if shape == 'array' and not isinstance(v, list):
                problems.append(Diagnostic(
                    code='value.null' if v is None else 'value.type', layer='format', path=where, entity=entity,
                    field=field, message='\'' + field + '\' is an output and must be a list, got '
                    + type(v).__name__))
                continue
            if shape == 'array' and v:
                problems.append(Diagnostic(
                    code='input.is_result', layer='format', path=where, entity=entity, field=field,
                    message='\'' + field + '\' already holds ' + str(len(v)) + ' values; an input leaves output '
                    'arrays empty (is this a result file?)'))
                continue
            if shape == 'object' and not isinstance(v, dict):
                problems.append(Diagnostic(
                    code='value.null' if v is None else 'value.type', layer='format', path=where, entity=entity,
                    field=field, message='\'' + field + '\' is an output and must be an object, got '
                    + type(v).__name__))
                continue
            if shape == 'object' and field == 'solver':
                for key in v:
                    if key not in SOLVER_FIELDS:
                        problems.append(Diagnostic(
                            code='field.unknown', layer='format', path=pointer('solver', key), entity='input',
                            field=key, message='unknown field \'' + key + '\' in \'solver\' (recognised: '
                            + ', '.join(SOLVER_FIELDS) + ')'))
                continue
            if shape == 'object' and field != 'provenance' and _holds_values(v):
                problems.append(Diagnostic(
                    code='input.is_result', layer='format', path=where, entity=entity, field=field,
                    message='\'' + field + '\' holds results; an input leaves it empty (is this a result file?)'))
        if kind == 'case':
            continue
        for field in LEGACY_OUTPUT_FIELDS[kind]:
            if field in item:
                del item[field]
                removed.append(pointer(*loc, field))
    if problems:
        raise InputError.from_diagnostics(problems)
    for field in LEGACY_OUTPUT_FIELDS['case']:
        if field in doc:
            del doc[field]
            removed.append(pointer(field))
    canonical = {'format_version': INPUT_FORMAT_VERSION}
    canonical.update(doc)
    return canonical, removed


# --- structural validation -------------------------------------------------------------

_BUILTIN_CODES = {
    'missing': 'field.missing',
    'extra_forbidden': 'field.unknown',
    'model_type': 'value.type', 'model_attributes_type': 'value.type', 'dict_type': 'value.type',
    'list_type': 'value.type', 'tuple_type': 'value.type',
}


def _diagnostic(error: Mapping[str, Any], document: Any) -> Diagnostic:
    loc: List[Union[str, int]] = list(error['loc'])
    ctx = dict(error.get('ctx') or {})
    kind = error['type']
    hour = None
    if 'field' in ctx:                               # a rule relating fields of one object
        loc.append(ctx['field'])
    field = next((p for p in reversed(loc) if isinstance(p, str)), None)
    if 'index' in ctx:                               # an element of an inline profile
        hour = int(ctx['index'])
        loc.append(hour)
    path = pointer(*loc)
    entity = entity_of(document, loc)
    if kind in _BUILTIN_CODES:
        code = _BUILTIN_CODES[kind]
        if code == 'value.type' and error.get('input') is None and kind != 'missing':
            code = 'value.null'
        if code == 'field.missing':
            message = 'missing required field \'' + str(field) + '\''
        elif code == 'field.unknown':
            message = 'unknown field \'' + str(field) + '\''
        elif code == 'value.null':
            message = '\'' + str(field) + '\' is null; give a value'
        else:
            wanted = 'a list' if kind in ('list_type', 'tuple_type') else 'an object'
            message = '\'' + str(field) + '\' must be ' + wanted + ', got ' + type(error.get('input')).__name__
    elif '.' in kind:                                # an IESO code raised by ieso.models
        code = kind
        text = str(error['msg'])
        message = text if text.startswith('\'') or text.startswith('missing') or field is None \
            else '\'' + field + '\' ' + text
    else:                                            # not expected: reported, never hidden
        code = 'value.invalid'
        message = '\'' + str(field) + '\': ' + str(error['msg'])
    return Diagnostic(code=code, layer='format' if code.startswith('format.') else 'structure', message=message,
                      path=path, entity=entity, field=field, hour=hour)


def diagnostics_from(error: ValidationError, document: Any) -> List[Diagnostic]:
    """IESO diagnostics for a Pydantic ValidationError raised while validating `document`."""
    return [_diagnostic(e, document) for e in error.errors(include_url=False)]


def parse(case: Union[Case, Mapping[str, Any]]) -> Tuple[Case, str, List[str]]:
    """Validate the structure of a case in either format.

    Returns
    -------
    (Case, format, removed)
        The validated model, 'canonical' or 'legacy', and the JSON Pointers of
        the output-only fields removed from a legacy document.

    Raises
    ------
    InputError
        With one Diagnostic per structural problem found.
    """
    if isinstance(case, Case):
        return case, CANONICAL, []
    kind = detect(case)
    document = numpy_profiles_to_lists(case)
    removed: List[str] = []
    if kind == LEGACY:
        document, removed = from_legacy(document)
    try:
        return Case.model_validate(document), kind, removed
    except ValidationError as e:
        raise InputError.from_diagnostics(diagnostics_from(e, document)) from None


# --- documents built from a validated case ------------------------------------------------

def canonical_document(case: Case) -> Dict[str, Any]:
    """The canonical serialisation: every input field explicit (defaults
    included), ``format_version`` first, numbers as given, lists for tuples.
    Loading it again gives an equal Case."""
    return case.model_dump(mode='json', by_alias=True, exclude_none=True)


def input_document(case: Case) -> Dict[str, Any]:
    """The case's input fields as a result echoes them (canonical, without
    ``format_version``)."""
    doc = canonical_document(case)
    del doc['format_version']
    return doc


def internal_document(case: Case) -> Dict[str, Any]:
    """The working dictionary the equation and reporting modules read and fill.

    The input fields with every default written in, plus the empty output
    containers the equation modules append to: this is the only place they are
    created. It is the model's private copy and gains solver objects.
    """
    s = input_document(case)
    s['solver'] = {}
    for dmd in [s['demand']['e']] + s['demand']['x']:
        dmd['output_ns'] = []
    for gen in s['generator']:
        gen['e_prod'], gen['h_prod'] = [], []
        gen['a'], gen['b'] = 0, 0          # set by eqs_gen for a unit that supplies heat
    for flx in s['flex']:
        flx['e_strg'], flx['e_char'], flx['e_disc'] = [], [], []
    for p2x in s['p2x']:
        p2x['x_prod'], p2x['x_strg'], p2x['x_supp'] = [], [], []
        p2x['shadow_prices'] = {}
    return s


def canonical_json(case: Case) -> str:
    """The canonical document as JSON text (4-space indent, like results)."""
    return json.dumps(canonical_document(case), indent=4, allow_nan=False)


# --- run options ------------------------------------------------------------------------

def validate_options(options: Mapping[str, Any]) -> Dict[str, float]:
    """Validate run options against models.SolveOptions.

    Returns the options as floats, in the order given (the order sets the
    result file name).

    Raises
    ------
    InputError
        An unknown name, a non-numeric or non-finite value, or a value outside
        its range (layer 'options', entity 'command line', field the name).
    """
    names = SolveOptions.names()
    for name in options:
        if name not in names:
            raise InputError('unknown option \'' + str(name) + '\' (recognised: ' + ', '.join(names) + ')',
                             entity='command line', field=str(name), code='option.unknown', layer='options')
    try:
        SolveOptions.model_validate(dict(options))
    except ValidationError as e:
        problems = []
        for d in diagnostics_from(e, {}):
            problems.append(Diagnostic(code=d.code, layer='options', message=d.message, entity='command line',
                                       field=d.field))
        raise InputError.from_diagnostics(problems) from None
    return {str(name): float(value) for name, value in options.items()}
