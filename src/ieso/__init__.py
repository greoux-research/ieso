#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""IESO: a linear optimiser-based integrated energy system modelling environment.

    import ieso

    report = ieso.validate('case.json')              # nothing solved, nothing written
    result = ieso.solve('case.json', options={'carbon-constraint': 50.0})
    if result.optimal and result.accounting_ok:
        print(result.document['system']['cost'])

The names below are the public API; see docs/ieso-api.md. The public modules
are ieso.api, ieso.models, ieso.results, ieso.errors, ieso.schemas and
ieso.cli. The modelling modules (chk, fcn, eqs_*, obj, opt, pos, pos_dmd,
formats) are internal, except for fcn.RunConfig, exported here. Importing ieso
reads, writes, prints and runs nothing.
"""

from ieso._install import version as _version
from ieso.api import (SolveResult, ValidationReport, check_options, load_input, output_path, parse_case, solve,
                      to_canonical, validate, write_result)
from ieso.errors import Diagnostic, IesoError, InputError, ThermoError
from ieso.fcn import RunConfig
from ieso.models import (Case, CommodityDemand, Demand, ElectricityDemand, Generator, Process, SolveOptions,
                         Storage)

__version__: str = _version()

__all__ = [
    '__version__',
    'solve', 'validate', 'load_input', 'parse_case', 'to_canonical', 'check_options', 'write_result',
    'output_path', 'SolveResult', 'ValidationReport', 'RunConfig',
    'IesoError', 'InputError', 'ThermoError', 'Diagnostic',
    'Case', 'Demand', 'ElectricityDemand', 'CommodityDemand', 'Generator', 'Storage', 'Process', 'SolveOptions',
]
