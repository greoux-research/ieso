#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""JSON Schemas generated from the public models.

The schemas are derived from ieso.models (inputs) and
ieso.results (results); there is no hand-written copy of their rules.
The copies shipped in the package (ieso/data/, see path()) are written by

    python tools/generate_schemas.py

and a test fails if they differ from what the current models generate. The
command line prints the same text: ieso schema input|result.

A schema describes structure only. Identifiers, references, topology, profile
contents and lengths, hourly shortfall bounds and thermodynamic admissibility
are checked by IESO itself (ieso validate CASE.json), and a valid
case may still be infeasible.
"""

import json
import os
from typing import Any, Dict

from ieso.models import INPUT_FORMAT_VERSION, Case
from ieso.results import RESULT_FORMAT_VERSION, Result

BASE_ID = 'https://github.com/greoux-research/ieso/schemas/'

STRUCTURE_ONLY = ('This schema describes structure only. Unique identifiers, references between objects, '
                  'thermal topology, profile files and their contents and lengths, hourly shortfall bounds and '
                  'thermodynamic admissibility are checked by IESO (ieso validate CASE.json). A valid '
                  'case may still define an infeasible optimisation problem.')

FILES = {
    'input': 'ieso-input-' + str(INPUT_FORMAT_VERSION) + '.schema.json',
    'result': 'ieso-result-' + str(RESULT_FORMAT_VERSION) + '.schema.json',
}


def path(kind: str) -> str:
    """The absolute path of the shipped schema file for 'input' or 'result'
    (inside the installed package)."""
    if kind not in FILES:
        raise ValueError('unknown schema \'' + kind + '\' (expected input or result)')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', FILES[kind])


def _no_null_defaults(node: Any) -> Any:
    # A field whose default is None may be absent but never null; its schema
    # has no default rather than a misleading "default": null.
    if isinstance(node, dict):
        return {k: _no_null_defaults(v) for k, v in node.items() if not (k == 'default' and v is None)}
    if isinstance(node, list):
        return [_no_null_defaults(v) for v in node]
    return node


def _envelope(schema: Dict[str, Any], kind: str, version: int, title: str, description: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': BASE_ID + FILES[kind],
        'title': title,
        'description': description + ' ' + STRUCTURE_ONLY,
        'x-ieso-format': {'kind': kind, 'version': version},
    }
    out.update({k: v for k, v in _no_null_defaults(schema).items() if k not in ('title', 'description')})
    return out


def input_schema() -> Dict[str, Any]:
    """The canonical input schema (format_version 1)."""
    return _envelope(Case.model_json_schema(by_alias=True, mode='validation'), 'input', INPUT_FORMAT_VERSION,
                     'IESO input, format ' + str(INPUT_FORMAT_VERSION),
                     'A canonical IESO case: inputs only, with "format_version": ' + str(INPUT_FORMAT_VERSION)
                     + '. Unversioned legacy documents are accepted by IESO through its compatibility adapter, '
                     'not by this schema.')


def result_schema() -> Dict[str, Any]:
    """The result schema (result_format_version 1)."""
    return _envelope(Result.model_json_schema(by_alias=True, mode='validation'), 'result', RESULT_FORMAT_VERSION,
                     'IESO result, format ' + str(RESULT_FORMAT_VERSION),
                     'An IESO result: OptimalResult when solver.stat_succ is 1 (check system.accounting_ok), '
                     'UnsuccessfulResult when it is 0 (inputs, status and provenance only).')


def render(schema: Dict[str, Any]) -> str:
    """The text shipped in ieso/data/ and printed by the command line."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + '\n'


def generate(kind: str) -> str:
    """render() of the 'input' or 'result' schema."""
    if kind == 'input':
        return render(input_schema())
    if kind == 'result':
        return render(result_schema())
    raise ValueError('unknown schema \'' + kind + '\' (expected input or result)')
