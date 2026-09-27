#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

"""IES Optimiser: a linear optimiser-based integrated energy system modelling environment.

    import ies_optimiser

    report = ies_optimiser.validate('case.json')              # nothing solved, nothing written
    result = ies_optimiser.solve('case.json', options={'carbon-constraint': 50.0})
    if result.optimal and result.accounting_ok:
        print(result.document['system']['cost'])

The names below are the public API; see docs/ies-optimiser-api.md. The public modules
are ies_optimiser.api, ies_optimiser.models, ies_optimiser.results, ies_optimiser.errors, ies_optimiser.schemas and
ies_optimiser.cli. The modelling modules (chk, fcn, eqs_*, obj, opt, pos, pos_dmd,
formats) are internal, except for fcn.RunConfig, exported here. Importing ies_optimiser
reads, writes, prints and runs nothing.
"""

from ies_optimiser._install import version as _version
from ies_optimiser.api import (SolveResult, ValidationReport, check_options, load_input, output_path, parse_case, solve,
                               to_canonical, validate, write_result)
from ies_optimiser.errors import Diagnostic, IesOptimiserError, InputError, ThermoError
from ies_optimiser.fcn import RunConfig
from ies_optimiser.models import (Case, CommodityDemand, Demand, ElectricityDemand, Generator, Process, SolveOptions,
                                  Storage)

__version__: str = _version()

__all__ = [
    '__version__',
    'solve', 'validate', 'load_input', 'parse_case', 'to_canonical', 'check_options', 'write_result',
    'output_path', 'SolveResult', 'ValidationReport', 'RunConfig',
    'IesOptimiserError', 'InputError', 'ThermoError', 'Diagnostic',
    'Case', 'Demand', 'ElectricityDemand', 'CommodityDemand', 'Generator', 'Storage', 'Process', 'SolveOptions',
]
