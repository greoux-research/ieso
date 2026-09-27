#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

"""The structure of an IES Optimiser result document, as typed models.

These models describe what solve() returns and the command line writes; they
exist to generate the result JSON Schema (ies_optimiser/data/ies-optimiser-result-1.schema.json)
and to check results in tests. IES Optimiser does not build its results through them:
the serialised form is the one documented in docs/ies-optimiser-io-file-structure.md,
and these models follow it exactly.

A result is one of two shapes, told apart by ``solver.stat_succ``:

* OptimalResult (``stat_succ`` 1): the case's inputs, with every capacity
  chosen by the optimiser replaced by its value, and the hourly and annual
  results, ``system`` totals and accounting checks. ``system.accounting_ok``
  false marks an accounting failure: the solve was optimal but a
  reconciliation check failed (the command line exits with status 3); every
  field is still present.
* UnsuccessfulResult (``stat_succ`` 0): the case's inputs, the solver
  status and provenance only. No result field is present, so nothing
  unavailable can be read as a number.

Sentinels kept from the original format: ``kpis`` values are -1 where not
applicable (a commodity with zero demand, or no output to allocate), and
``carbon_cap`` / ``reliability_cap`` are -1 when the option was not given.
"""

from typing import Annotated, Any, Dict, Literal, Optional, Tuple, Union

from pydantic import ConfigDict, Field, PlainValidator, RootModel, StrictBool, StrictInt, StrictStr, WithJsonSchema

from ies_optimiser import models as m
from ies_optimiser.models import FiniteList, Real

RESULT_FORMAT_VERSION = 1
"""Recorded in every result as provenance.result_format_version."""


def _nullable(v: Any) -> Any:
    return None if v is None else m._real(v)


NullableReal = Annotated[Optional[float], PlainValidator(_nullable), m._Out,
                         WithJsonSchema({'type': ['number', 'null']})]
"""A finite number, or null where the quantity is undefined (no output to allocate)."""

Series = Annotated[FiniteList, Field(description='One value per hour.')]


class _Result(m._Model):
    pass


# --- demand results -------------------------------------------------------------

class CapDetail(_Result):
    """What was observed on a cap row, kept apart from its interpretation."""
    raw_dual: Real = Field(description='The row dual as returned by the solver.')
    cap: Real = Field(description='The cap (right-hand side).')
    activity: Real = Field(description='The row activity at the solution.')
    slack: Real = Field(description='cap - activity.')
    binding: StrictBool = Field(description='Whether the row is at its cap (within tolerance).')
    binding_zero_dual: StrictBool = Field(description='Binding with a zero dual: degenerate, or a genuinely '
                                          'worthless cap. IES Optimiser does not tell them apart.')


class Kpis(_Result):
    """Compatibility KPIs; -1 where not applicable."""
    cost: Real = Field(description='(allocated resource cost + shortage penalty) / annual demand (USD/unit); '
                       'an allocation, not a production cost. -1 if not applicable.')
    emis: Real = Field(description='Allocated emissions / annual demand (kg CO2eq/unit); -1 if not applicable.')
    reli: Real = Field(description='1 - unmet / demand: an annual energy ratio; -1 if not applicable.')


class Accounts(_Result):
    """The quantities behind the cost KPI (active demands only)."""
    allocation_share: NullableReal = Field(description='Share of total electricity-equivalent output allocated '
                                           'to this commodity; null when the system produced no output.')
    allocated_output: Real = Field(description='Electricity-equivalent output allocated (MWh).')
    resource_cost: NullableReal = Field(description='System cost allocated (USD); excludes shortage penalties.')
    shortage_penalty: Real = Field(description='unmet_demand x var_cost_ns (USD): a modelled price, not spend.')
    emissions: NullableReal = Field(description='Emissions allocated (kg CO2eq).')
    demand: Real = Field(description='Annual demand.')
    unmet_demand: Real = Field(description='Annual unmet demand.')
    served_demand: Real = Field(description='Annual served demand.')
    resource_cost_per_demand: NullableReal = Field(description='resource_cost / demand (USD/unit).')
    resource_cost_per_served: NullableReal = Field(description='resource_cost / served_demand (USD/unit); null '
                                                   'when nothing was served.')
    surplus: Real = Field(description='Annual sum of the surplus series, in the commodity\'s unit.')


class ElectricityPrices(_Result):
    """Dual values on the electricity balance and caps."""
    demand_match: Series = Field(description='Hourly dual of the demand-balance row (USD/MWh), with every '
                                 'variable bound held fixed.')
    demand_marginal: Series = Field(description='Hourly dual-based marginal value of demand (USD/MWh): a '
                                    'subgradient, exact except at breakpoints.')
    carbon_cap: Real = Field(description='Marginal value of relaxing the carbon cap (USD per kg); 0 when not '
                             'binding; -1 when no carbon-constraint was given.')
    reliability_cap: Real = Field(description='Marginal value of relaxing the unmet-electricity cap (USD/MWh); '
                                  '0 when not binding; -1 when no non-served-power-constraint was given.')
    carbon_cap_detail: Optional[CapDetail] = Field(None, description='Present with carbon-constraint.')
    reliability_cap_detail: Optional[CapDetail] = Field(None, description='Present with '
                                                        'non-served-power-constraint.')


class CommodityPrices(_Result):
    """Dual values on a commodity balance (empty series for an inactive demand)."""
    demand_match: Series = Field(description='Hourly dual of the demand-balance row (USD/unit).')
    demand_marginal: Series = Field(description='Hourly dual-based marginal value of demand (USD/unit).')


class ElectricityDemandResult(m.ElectricityDemand):
    output_ns: Series = Field(description='Hourly unmet demand (MWh).')
    surplus: Series = Field(description='Hourly residual of the electricity balance (MWh): supply beyond '
                            'served demand and process use. Not curtailment.')
    shadow_prices: ElectricityPrices
    kpis: Kpis
    accounts: Optional[Accounts] = Field(None, description='Absent when annual demand is zero.')


class CommodityDemandResult(m.CommodityDemand):
    output_ns: Series = Field(description='Hourly unmet demand; empty for an inactive demand.')
    surplus: Series = Field(description='Hourly delivery beyond served demand; empty for an inactive demand.')
    shadow_prices: CommodityPrices
    kpis: Kpis
    accounts: Optional[Accounts] = Field(None, description='Present for an active demand.')


class DemandResult(_Result):
    e: ElectricityDemandResult
    x: Tuple[CommodityDemandResult, ...]


# --- generators, stores, processes ----------------------------------------------------

class Availability(_Result):
    """What the availability profile asked for against what it delivered."""
    capacity_factor_requested: Real
    profile_peak: Real = Field(description='Maximum of the rescaled availability series.')
    hours_above_nameplate: Real = Field(description='Hours in which the rescaled series exceeds one.')
    capacity_factor_effective: Real = Field(description='Mean availability once output is held to capacity.')


class GeneratorResult(m.Generator):
    e_prod: Series = Field(description='Hourly electricity output (MWh).')
    h_prod: Series = Field(description='Hourly heat output (MWh); empty unless the unit supplies heat.')
    a: Real = Field(description='Electricity forgone per unit of heat extracted; 0 unless the unit supplies heat.')
    b: Real = Field(description='Heat available per unit of electrical capacity; 0 unless the unit supplies heat.')
    availability: Availability


class StorageResult(m.Storage):
    e_strg: Series = Field(description='Hourly energy stored (MWh).')
    e_char: Series = Field(description='Hourly charge (MW).')
    e_disc: Series = Field(description='Hourly discharge (MW).')
    e_spil: Optional[Series] = Field(None, description='Hourly spilled inflow (MWh); present with inflow.')


class ProcessPrices(_Result):
    demand_match: Series = Field(description='Hourly dual of the process heat balance (USD/MWh of heat); '
                                 'empty for an electric process.')


class ProcessResult(m.Process):
    x_prod: Series = Field(description='Hourly production (Q/h).')
    x_strg: Series = Field(description='Hourly store level (Q).')
    x_supp: Series = Field(description='Hourly delivery (Q/h).')
    heat_surplus: Series = Field(description='Hourly heat supplied beyond the requirement (MWh); empty for an '
                                 'electric process.')
    availability: Availability
    shadow_prices: ProcessPrices


# --- system, solver, provenance ------------------------------------------------------

class Check(_Result):
    residual: Real
    tolerance: Real
    ok: StrictBool


class Allocated(_Result):
    output: Real = Field(description='Electricity-equivalent output (MWh).')
    share: NullableReal = Field(description='Share of total output; null when there is no output.')
    cost: Real = Field(description='USD.')
    emis: Real = Field(description='kg CO2eq.')


class Unallocated(Allocated):
    electricity_surplus: Real
    unused_heat: Real
    unassigned_process_use: Real


class SystemSurplus(_Result):
    electricity: Real = Field(description='Annual electricity surplus (MWh).')
    heat: Real = Field(description='Annual heat surplus (MWh of heat).')
    spill: Real = Field(description='Annual reservoir spill (MWh).')
    products: Dict[str, Real] = Field(description='Annual product surplus per active demand.')
    unassigned_product_supply: Dict[str, Real] = Field(description='Annual delivery of processes that no active '
                                                       'demand names.')


class System(_Result):
    """System totals, allocation and machine-readable accounting checks."""
    cost: Real = Field(description='Total system cost (USD), excluding shortage penalties.')
    output: Real = Field(description='Total electricity-equivalent output (MWh).')
    emis: Real = Field(description='Total emissions (kg CO2eq).')
    allocation_defined: StrictBool
    allocated_share_total: NullableReal
    allocated: Allocated
    unallocated: Unallocated
    surplus: SystemSurplus
    checks: Dict[str, Check] = Field(description='Name -> {residual, tolerance, ok}; only applicable checks.')
    accounting_ok: StrictBool = Field(description='false: an accounting check failed (exit status 3).')


class OptimalSolver(_Result):
    stat_succ: Literal[1]
    stat_status: Literal['optimal']
    stat_time: Real = Field(description='Elapsed time (s).')
    stat_capa: StrictInt
    stat_outp: StrictInt
    stat_cons: StrictInt


class UnsuccessfulSolver(_Result):
    stat_succ: Literal[0]
    stat_status: StrictStr = Field(description='Why: infeasible, unbounded, abnormal (numerical trouble), '
                                   'feasible but not proven optimal, or not solved.')
    stat_time: Real
    stat_capa: StrictInt
    stat_outp: StrictInt
    stat_cons: StrictInt


class ProfileFile(_Result):
    resolved: Optional[StrictStr]
    sha256: Optional[StrictStr]


class ProfileResolution(_Result):
    mode: Literal['input-directory', 'explicit', 'none']
    base: Optional[StrictStr]


class EnclosingGit(_Result):
    toplevel: StrictStr
    revision: Optional[StrictStr]
    dirty: Optional[StrictBool]


class Installation(_Result):
    kind: Literal['wheel', 'editable', 'source', 'unknown'] = Field(
        description='wheel: an installed distribution; editable: an editable install of a checkout; source: a '
        'checkout on the path, not installed.')
    package_dir: StrictStr = Field(description='The directory of the ies_optimiser package that ran.')


class Provenance(_Result):
    """What produced the result: code, inputs, options, environment."""
    ies_optimiser_version: StrictStr
    result_format_version: Literal[1]
    input_format: Literal['canonical', 'legacy']
    input: StrictStr = Field(description='The input path as given, or \'<in-memory>\'.')
    input_resolved: Optional[StrictStr]
    input_sha256: Optional[StrictStr] = Field(description='SHA-256 of the input file named as the source, or of '
                                              'the in-memory document as given.')
    case_sha256: StrictStr = Field(description='SHA-256 of the canonical JSON of the case actually solved (inputs '
                                   'only, defaults explicit, keys sorted).')
    source_matches_case: Optional[StrictBool] = Field(description='Whether the source file, read the same way, is '
                                                      'the case solved; null without a source file.')
    profiles_sha256: Dict[str, Optional[StrictStr]]
    profile_files: Dict[str, ProfileFile]
    profile_resolution: ProfileResolution
    options: Dict[str, Real]
    hours: StrictInt
    storage_closes_the_year: StrictBool
    solver: StrictStr
    ortools: StrictStr
    numpy: StrictStr
    python: StrictStr
    platform: StrictStr
    run_utc: StrictStr
    git_scope: Optional[Literal['ies_optimiser', 'enclosing']]
    git_revision: Optional[StrictStr]
    git_dirty: Optional[StrictBool]
    enclosing_git: Optional[EnclosingGit]
    source_sha256: StrictStr
    installation: Installation
    source_files_sha256: Dict[str, Optional[StrictStr]]
    thermo_binary: StrictStr
    thermo_binary_origin: Literal['packaged', 'override'] = Field(
        description='packaged: the executable installed with IES Optimiser; override: RunConfig.thermo_bin.')


class OptimalResult(_Result):
    """An optimal solve: inputs and results (check system.accounting_ok)."""
    demand: DemandResult
    p2x: Tuple[ProcessResult, ...]
    generator: Tuple[GeneratorResult, ...]
    flex: Tuple[StorageResult, ...]
    solver: OptimalSolver
    system: System
    provenance: Provenance


class UnsuccessfulResult(_Result):
    """A solve that did not reach an optimal solution: inputs and status only."""
    demand: m.Demand
    p2x: Tuple[m.Process, ...]
    generator: Tuple[m.Generator, ...]
    flex: Tuple[m.Storage, ...]
    solver: UnsuccessfulSolver
    provenance: Provenance


class Result(RootModel[Union[OptimalResult, UnsuccessfulResult]]):
    """An IES Optimiser result document (format 1)."""
    model_config = ConfigDict(frozen=True)
