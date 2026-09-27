#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

"""Exceptions and structured diagnostics raised by IES Optimiser's library code.

Library code never terminates Python; it raises one of these, and only the
command line (ies_optimiser/cli.py) turns them into exit codes. A solver outcome
such as infeasibility is not an exception: it is reported as a result status.
Any other exception is a defect in IES Optimiser, not a problem with the input, and is
deliberately not caught or disguised as one of these.

Every IesOptimiserError carries one or more Diagnostic records, IES Optimiser's own stable
description of what was refused. The format does not expose Pydantic's error
representation; see docs/ies-optimiser-api.md for the list of codes.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

# Where in the pipeline a diagnostic arose. Each layer is distinguishable from
# the others, and none of them is a solver outcome.
LAYERS = (
    'file',             # the input file could not be read or parsed
    'format',           # format version, legacy adaptation
    'structure',        # types, required fields, allowed values, local ranges
    'semantics',        # identifiers, references, topology, hourly bounds
    'profiles',         # profile files and series: location, content, length
    'thermodynamics',   # cogeneration coefficients (ies_optimiser/_bin/ies-optimiser-thermo)
    'options',          # run options (carbon-constraint, ...)
    'configuration',    # RunConfig / command-line flags
)


@dataclass(frozen=True)
class Diagnostic:
    """One refused aspect of an input, in IES Optimiser's stable public format.

    Attributes
    ----------
    code : str
        Stable, dotted identifier of the rule, e.g. ``'value.out_of_range'``,
        ``'reference.unknown'``, ``'profile.not_found'``. Codes are the
        contract; messages may be reworded.
    layer : str
        Which validation layer raised it (one of ``LAYERS``).
    message : str
        Human-readable explanation.
    path : str or None
        JSON Pointer (RFC 6901) into the case document, using the serialised
        field names, e.g. ``'/generator/2/capacity_factor'``; ``None`` when the
        problem is not located in the case (an option, a flag, a file).
    entity : str or None
        The entity concerned: an identifier such as ``'ccgt'``, ``'demand.e'``,
        ``'demand.x[water]'``, ``'input'``, ``'command line'`` or a file path.
    field : str or None
        The serialised field name, where one applies.
    hour : int or None
        Zero-based hour index (0 is the first hour of the year), for hourly
        checks and for elements of inline profiles.
    """
    code: str
    layer: str
    message: str
    path: Optional[str] = None
    entity: Optional[str] = None
    field: Optional[str] = None
    hour: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """The diagnostic as a plain JSON-compatible dictionary."""
        return asdict(self)

    def __str__(self) -> str:
        where = '' if self.entity is None else '\'' + self.entity + '\': '
        return where + self.message


class IesOptimiserError(Exception):
    """Base class for the errors IES Optimiser raises deliberately.

    Attributes
    ----------
    diagnostics : list of Diagnostic
        At least one; structural validation reports every problem it finds.
    """

    diagnostics: List[Diagnostic]


class InputError(IesOptimiserError, ValueError):
    """The input, a profile, a command-line option or the configuration is
    outside the documented contract.

    Attributes
    ----------
    message : str
        Why it was refused (the first diagnostic's message).
    entity : str
        What the problem concerns: an identifier such as 'ccgt', a path such as
        'demand.x[water]' or 'demand.e', 'command line', or a file.
    field : str or None
        The offending field, where known (e.g. 'l_ns', 'capacity_factor').
    hour : int or None
        The offending hour (0-based), where the check is hourly.
    code, layer, path : str, str, str or None
        As in the first Diagnostic.
    diagnostics : list of Diagnostic
        Every problem found; the attributes above describe the first.
    """

    def __init__(self, message: str, *, entity: str, field: Optional[str] = None,
                 hour: Optional[int] = None, code: str = 'input.invalid', layer: str = 'semantics',
                 path: Optional[str] = None, diagnostics: Optional[Sequence[Diagnostic]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.entity = entity
        self.field = field
        self.hour = hour
        self.code = code
        self.layer = layer
        self.path = path
        self.diagnostics = list(diagnostics) if diagnostics else [
            Diagnostic(code=code, layer=layer, message=message, path=path, entity=entity, field=field, hour=hour)]

    @classmethod
    def from_diagnostics(cls, diagnostics: Sequence[Diagnostic]) -> 'InputError':
        """An InputError reporting `diagnostics` (at least one); the first sets
        the scalar attributes."""
        first = diagnostics[0]
        return cls(first.message, entity=first.entity if first.entity is not None else 'input',
                   field=first.field, hour=first.hour, code=first.code, layer=first.layer,
                   path=first.path, diagnostics=diagnostics)

    def __str__(self) -> str:
        return '; '.join(str(d) for d in self.diagnostics)


class ThermoError(IesOptimiserError):
    """Cogeneration coefficients could not be obtained for a heat-supplying unit.

    Raised when the thermodynamics executable is missing, times out, fails, or
    returns coefficients outside the admissible range -- including for turbine or
    extraction conditions outside the supported domain. Its diagnostic has code
    ``'thermo.failed'`` and layer ``'thermodynamics'``.

    Attributes
    ----------
    generator : str
        The heat-supplying generator's identifier.
    process : str
        The thermally coupled process it supplies.
    reason : str
        What the executable (or its checks) reported.
    """

    def __init__(self, message: str, *, generator: str, process: str, reason: str,
                 path: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.generator = generator
        self.process = process
        self.reason = reason
        self.diagnostics = [Diagnostic(code='thermo.failed', layer='thermodynamics', path=path,
                                       entity=generator, field='turbine_t_p',
                                       message='supplying heat to \'' + process + '\': ' + message)]

    def __str__(self) -> str:
        return '\'' + self.generator + '\' + \'' + self.process + '\': ' + self.message
