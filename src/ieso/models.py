#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""The public input models: the structure of a valid IESO case.

These models are IESO's single structural validator. They own every rule that
can be decided by looking at one value or one object: field types, required
fields, allowed values, finite numbers, local ranges, and unknown fields.
Rules that relate objects to one another, or to data outside the document
(profile files, hourly demand, thermodynamics), belong to the semantic layer
(ieso/chk.py). A structurally and semantically valid case may still
define an infeasible optimisation problem; that is a solver status, not an
input error.

Serialised field names are those of the existing JSON format (``fix_cost_prod``,
``l_ns``...). Python attributes carry descriptive names; both are accepted when
constructing a model::

    Generator(iden='ocgt', ...)                   # the serialised name
    Generator(identifier='ocgt', ...)             # the Python attribute

Numbers are JSON numbers: integers are accepted wherever a real value is, and
are kept as given; strings, booleans, null, NaN and infinities are refused.
"""

import math
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union

from pydantic import (BaseModel, ConfigDict, Field, PlainSerializer, PlainValidator, SerializerFunctionWrapHandler,
                      WithJsonSchema, model_serializer, model_validator)
from pydantic_core import PydanticCustomError

INPUT_FORMAT_VERSION = 1
"""The canonical input format this code writes and reads (``format_version``)."""

OPTIMISE = -1
"""The capacity sentinel: a capacity of -1 is chosen by the optimiser."""

ENTITY_TYPES = ('elec', 'elec + ther')


# --- value validators -----------------------------------------------------------
#
# Each raises a PydanticCustomError whose type is an IESO diagnostic code and
# whose message is phrased to follow the field name ("'x' must be ...").
# ieso/formats.py turns these into Diagnostic records.

def _got(v: Any) -> str:
    return type(v).__name__ if isinstance(v, (list, tuple, dict)) and len(repr(v)) > 60 else repr(v)


def _not_null(v: Any) -> Any:
    if v is None:
        raise PydanticCustomError('value.null', 'is null; omit the field to use its default, or give a value')
    return v


def _is_real(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _real(v: Any) -> Any:
    _not_null(v)
    if not _is_real(v):
        raise PydanticCustomError('value.type', 'must be a number, got {got}', {'got': _got(v)})
    if not math.isfinite(v):
        raise PydanticCustomError('value.not_finite', 'must be finite, got {got}', {'got': repr(v)})
    return v


def _ranged(ge: Optional[float] = None, gt: Optional[float] = None, le: Optional[float] = None) -> Any:
    def check(v: Any) -> Any:
        v = _real(v)
        for limit, bad, word in ((ge, ge is not None and v < ge, '>='), (gt, gt is not None and v <= gt, '>'),
                                 (le, le is not None and v > le, '<=')):
            if bad:
                raise PydanticCustomError('value.out_of_range', 'must be {word} {limit}, got {got}',
                                          {'word': word, 'limit': limit, 'got': repr(v)})
        return v
    return check


def _number_schema(ge: Optional[float] = None, gt: Optional[float] = None, le: Optional[float] = None) -> Dict[str, Any]:
    schema: Dict[str, Any] = {'type': 'number'}
    if ge is not None:
        schema['minimum'] = ge
    if gt is not None:
        schema['exclusiveMinimum'] = gt
    if le is not None:
        schema['maximum'] = le
    return schema


def _capacity(v: Any) -> Any:
    v = _real(v)
    if v < 0 and v != OPTIMISE:
        raise PydanticCustomError('value.out_of_range', 'must be -1 (optimise) or non-negative, got {got}',
                                  {'got': repr(v)})
    return v


def _pair(v: Any) -> Tuple[Any, Any]:
    _not_null(v)
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        raise PydanticCustomError('value.length', 'must hold two values [low, high], got {got}', {'got': _got(v)})
    for x in v:
        if not _is_real(x) or not math.isfinite(x):
            raise PydanticCustomError('value.type' if not _is_real(x) else 'value.not_finite',
                                      'must hold finite numbers, got {got}', {'got': _got(v)})
    if v[0] < 0:
        raise PydanticCustomError('value.out_of_range', 'must not be negative, got {got}', {'got': repr(v)})
    if v[0] > v[1]:
        raise PydanticCustomError('value.inconsistent', 'lower bound {low} exceeds upper bound {high}',
                                  {'low': repr(v[0]), 'high': repr(v[1])})
    return (v[0], v[1])


def _pair_or_empty(v: Any) -> Tuple[Any, ...]:
    _not_null(v)
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return ()
    return _pair(v)


def _profile(v: Any) -> Union[str, Tuple[Any, ...]]:
    _not_null(v)
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple)):
        for i, x in enumerate(v):
            if not _is_real(x):
                raise PydanticCustomError('value.type', 'value {index} must be a number, got {got}',
                                          {'index': i, 'got': _got(x)})
            if not math.isfinite(x):
                raise PydanticCustomError('value.not_finite', 'value {index} must be finite, got {got}',
                                          {'index': i, 'got': repr(x)})
        return tuple(v)
    raise PydanticCustomError('value.type', 'must be a file path (\'\' for a flat profile) or a list of numbers, '
                              'got {got}', {'got': type(v).__name__})


def _identifier(v: Any) -> str:
    _not_null(v)
    if not isinstance(v, str):
        raise PydanticCustomError('value.type', 'must be a string, got {got}', {'got': _got(v)})
    if not v:
        raise PydanticCustomError('value.empty', 'must not be empty')
    return v


def _names(v: Any) -> Tuple[str, ...]:
    _not_null(v)
    if not isinstance(v, (list, tuple)) or not all(isinstance(n, str) for n in v):
        raise PydanticCustomError('value.type', 'must be a list of identifiers, got {got}', {'got': _got(v)})
    return tuple(v)


def _kind(v: Any) -> str:
    _not_null(v)
    if v not in ENTITY_TYPES or not isinstance(v, str):
        raise PydanticCustomError('value.not_allowed', 'must be one of {allowed}, got {got}',
                                  {'allowed': ', '.join(repr(t) for t in ENTITY_TYPES), 'got': _got(v)})
    return v


def _flag(v: Any) -> bool:
    _not_null(v)
    if not isinstance(v, bool):
        raise PydanticCustomError('value.type', 'must be true or false, got {got}', {'got': _got(v)})
    return v


def _finite_list(v: Any) -> Tuple[Any, ...]:
    _not_null(v)
    if not isinstance(v, (list, tuple)) or not all(_is_real(x) and math.isfinite(x) for x in v):
        raise PydanticCustomError('value.type', 'must be a list of finite numbers, got {got}', {'got': _got(v)})
    return tuple(v)


def _version(v: Any) -> int:
    if type(v) is not int or v != INPUT_FORMAT_VERSION:
        raise PydanticCustomError('format.unsupported_version', 'unsupported format_version {got}; this IESO '
                                  'reads format_version {supported} (or an unversioned legacy input)',
                                  {'got': _got(v), 'supported': INPUT_FORMAT_VERSION})
    return v


# --- value types ----------------------------------------------------------------
#
# Each type validates with its own function (so every error carries an IESO
# code), serialises the value exactly as given apart from tuples becoming
# lists (so a JSON integer stays an integer), and declares its JSON Schema
# explicitly. The "Optional" variants are for fields whose absence means
# something: absent is allowed, an explicit null is refused.

def _as_json(v: Any) -> Any:
    if isinstance(v, (list, tuple)):
        return [_as_json(x) for x in v]
    return v


_Out = PlainSerializer(_as_json, return_type=Any)


def _absent_ok(check: Any) -> Any:
    # Defaults are not validated, so this sees only values actually given.
    def run(v: Any) -> Any:
        return check(_not_null(v))
    return run


Real = Annotated[float, PlainValidator(_real), _Out, WithJsonSchema(_number_schema())]
"""A finite JSON number; integers are kept as integers."""

NonNegative = Annotated[float, PlainValidator(_ranged(ge=0.0)), _Out, WithJsonSchema(_number_schema(ge=0.0))]
OptionalNonNegative = Annotated[Optional[float], PlainValidator(_absent_ok(_ranged(ge=0.0))), _Out,
                                WithJsonSchema(_number_schema(ge=0.0))]
Positive = Annotated[float, PlainValidator(_ranged(gt=0.0)), _Out, WithJsonSchema(_number_schema(gt=0.0))]
Fraction = Annotated[float, PlainValidator(_ranged(ge=0.0, le=1.0)), _Out,
                     WithJsonSchema(_number_schema(ge=0.0, le=1.0))]
OptionalFraction = Annotated[Optional[float], PlainValidator(_absent_ok(_ranged(ge=0.0, le=1.0))), _Out,
                             WithJsonSchema(_number_schema(ge=0.0, le=1.0))]
OptionalReal = Annotated[Optional[float], PlainValidator(_absent_ok(_real)), _Out, WithJsonSchema(_number_schema())]
PositiveFraction = Annotated[float, PlainValidator(_ranged(gt=0.0, le=1.0)), _Out,
                             WithJsonSchema(_number_schema(gt=0.0, le=1.0))]

Capacity = Annotated[float, PlainValidator(_capacity), _Out, WithJsonSchema({
    'type': 'number', 'anyOf': [{'const': OPTIMISE}, {'minimum': 0}]})]
"""-1 (the optimiser chooses the capacity) or a fixed, non-negative capacity."""

_PAIR_SCHEMA: Dict[str, Any] = {'type': 'array', 'prefixItems': [{'type': 'number', 'minimum': 0},
                                                                 {'type': 'number', 'minimum': 0}],
                                'items': False, 'minItems': 2, 'maxItems': 2}

Bounds = Annotated[Tuple[float, float], PlainValidator(_pair), _Out, WithJsonSchema(_PAIR_SCHEMA)]
"""[low, high] with 0 <= low <= high (the ordering is checked; JSON Schema cannot express it)."""

OptionalBounds = Annotated[Optional[Tuple[float, ...]], PlainValidator(_absent_ok(_pair_or_empty)), _Out,
                           WithJsonSchema({'anyOf': [_PAIR_SCHEMA, {'type': 'array', 'maxItems': 0}]})]

_PROFILE_SCHEMA: Dict[str, Any] = {'anyOf': [
    {'type': 'string', 'description': 'a CSV file path (one value per line, no header), or \'\' for a flat profile'},
    {'type': 'array', 'items': {'type': 'number'}, 'description': 'one value per hour'}]}

Profile = Annotated[Union[str, Tuple[float, ...]], PlainValidator(_profile), _Out, WithJsonSchema(_PROFILE_SCHEMA)]
"""'' (flat), a CSV path, or an inline list of hourly values."""

OptionalProfile = Annotated[Optional[Union[str, Tuple[float, ...]]], PlainValidator(_absent_ok(_profile)), _Out,
                            WithJsonSchema(_PROFILE_SCHEMA)]

Identifier = Annotated[str, PlainValidator(_identifier), _Out, WithJsonSchema({'type': 'string', 'minLength': 1})]
Names = Annotated[Tuple[str, ...], PlainValidator(_names), _Out,
                  WithJsonSchema({'type': 'array', 'items': {'type': 'string'}})]
FiniteList = Annotated[Tuple[float, ...], PlainValidator(_finite_list), _Out,
                       WithJsonSchema({'type': 'array', 'items': {'type': 'number'}})]
EntityType = Annotated[str, PlainValidator(_kind), _Out, WithJsonSchema({'type': 'string', 'enum': list(ENTITY_TYPES)})]
Flag = Annotated[bool, PlainValidator(_flag), _Out, WithJsonSchema({'type': 'boolean'})]
Version = Annotated[int, PlainValidator(_version), _Out, WithJsonSchema({'const': INPUT_FORMAT_VERSION})]


class _Model(BaseModel):
    # Schema titles come from the descriptive Python names ('Fixed cost'),
    # properties from the serialised ones ('fix_cost_prod').
    model_config = ConfigDict(extra='forbid', frozen=True, validate_by_name=True, validate_by_alias=True,
                              serialize_by_alias=True,
                              field_title_generator=lambda name, info: name.replace('_', ' ').capitalize())

    @model_serializer(mode='wrap')
    def _omit_absent(self, handler: SerializerFunctionWrapHandler) -> Dict[str, Any]:
        # A field whose default is None is one whose absence means something
        # (no inflow profile, a not-applicable penalty): it is omitted, never
        # written as null, so every dump validates again.
        data: Dict[str, Any] = handler(self)
        for name, info in type(self).model_fields.items():
            if info.default is None:
                for key in (info.alias, name):
                    if key in data and data[key] is None:
                        del data[key]
        return data


def _inconsistent(field: str, message: str, code: str = 'value.inconsistent') -> PydanticCustomError:
    # A rule relating two fields of one object; 'field' places it in the path.
    return PydanticCustomError(code, message, {'field': field})


# --- demands --------------------------------------------------------------------

PROFILE_DOC = ('Hourly shape: \'\' for a flat profile, a CSV file path (resolved against the input file\'s '
               'directory, or an explicit profile base; never the working directory), or a list with one value '
               'per hour (8760). Values must be finite, non-negative and not all zero.')


class ElectricityDemand(_Model):
    """Final demand for electricity (always active)."""

    identifier: Identifier = Field(alias='iden', description='Identifier, conventionally \'electricity\'.',
                                   examples=['electricity'])
    profile: Profile = Field('', description='Shape of hourly demand. ' + PROFILE_DOC, examples=['dmnd.csv'])
    annual_total: NonNegative = Field(alias='total', description='Annual demand (MWh). The hourly series is '
                                      'the profile scaled so that it sums to this total.', examples=[5.69e6])
    supply_sources: Names = Field((), description='Unused for electricity, which is always met by the '
                                  'generators; kept for symmetry with commodity demands.')
    shortfall_penalty: NonNegative = Field(alias='var_cost_ns', description='Penalty per unit of unmet demand '
                                           '(USD/MWh). Zero makes a shortfall free (the hourly bound still applies).',
                                           examples=[20000])
    shortfall_bounds: Bounds = Field(alias='l_ns', description='[low, high] bounds on unmet demand in EACH hour '
                                     '(MWh), not on the annual total. The effective upper bound is min(high, '
                                     'demand of the hour); low may not exceed the demand of any hour.',
                                     examples=[[0, 1e6]])


class CommodityDemand(_Model):
    """Final demand for a Power-to-X commodity (heat, hydrogen, water...).

    A demand with ``total`` 0 is inactive: it builds nothing, and its penalty,
    shortfall bounds and profile are not read.
    """

    identifier: Identifier = Field(alias='iden', description='Identifier of the commodity, unique among demands.',
                                   examples=['water'])
    profile: Profile = Field('', description='Shape of hourly demand. ' + PROFILE_DOC)
    annual_total: NonNegative = Field(alias='total', description='Annual demand in the commodity\'s unit (m3, '
                                      'kg, MWh of heat...). 0 makes the demand inactive.', examples=[5.0e7])
    supply_sources: Names = Field((), description='Identifiers of the processes (p2x) that deliver this '
                                  'commodity. A process may supply at most one active demand.',
                                  examples=[['p2x-ro']])
    shortfall_penalty: OptionalNonNegative = Field(
        None, alias='var_cost_ns', description='Penalty per unit of unmet demand (USD per unit). Required when '
        'the demand is active.', examples=[1000])
    shortfall_bounds: OptionalBounds = Field(
        None, alias='l_ns', description='[low, high] bounds on unmet demand in each hour. Required, as a pair, '
        'when the demand is active; an inactive demand may give [] or omit it.', examples=[[0, 1e9]])

    @model_validator(mode='after')
    def _active_demand_is_complete(self) -> 'CommodityDemand':
        if self.annual_total > 0:
            if self.shortfall_penalty is None:
                raise _inconsistent('var_cost_ns', 'missing required field \'var_cost_ns\' (the demand is active)',
                                    'field.missing')
            if self.shortfall_bounds is None:
                raise _inconsistent('l_ns', 'missing required field \'l_ns\' (the demand is active)', 'field.missing')
            if len(self.shortfall_bounds) != 2:
                raise _inconsistent('l_ns', '\'l_ns\' must hold two values [low, high] for an active demand',
                                    'value.length')
        return self


class Demand(_Model):
    """Final demands: electricity (``e``) and Power-to-X commodities (``x``)."""

    e: ElectricityDemand = Field(description='Demand for electricity.')
    x: Tuple[CommodityDemand, ...] = Field((), description='Demands for other commodities.')


# --- generators, storage, processes ---------------------------------------------

class Generator(_Model):
    """A power generator; a cogeneration unit can also supply heat to one process."""

    identifier: Identifier = Field(alias='iden', description='Identifier, unique among generators.',
                                   examples=['wind'])
    kind: EntityType = Field(alias='type', description='\'elec\', or \'elec + ther\' for a unit that can supply '
                             'heat in cogeneration mode.')
    profile: Profile = Field('', description='Availability shape. ' + PROFILE_DOC + ' A profile supplies '
                             'shape only: it is divided by its maximum and rescaled so that its mean equals '
                             'capacity_factor.', examples=['wind.csv'])
    capacity_factor: Fraction = Field(description='Fraction in [0, 1]: the target mean of the rescaled profile, '
                                      'or a flat hourly ceiling when there is no profile.', examples=[0.25])
    fixed_cost: Real = Field(alias='fix_cost_prod', description='Fixed cost (USD per MW per year). Negative '
                             'values are accepted (a subsidy).', examples=[133553])
    variable_cost: Real = Field(alias='var_cost_prod', description='Variable cost excluding energy (USD/MWh).',
                                examples=[6e-6])
    emission_factor: Real = Field(alias='var_emis_prod', description='Emissions (kg CO2eq/MWh). Negative values '
                                  'represent removal.', examples=[0])
    capacity_bounds: Bounds = Field(alias='l_prod', description='[low, high] bounds on the installed capacity '
                                    '(MW), not on hourly output.', examples=[[0, 1e5]])
    capacity: Capacity = Field(alias='c_prod', description='Installed capacity (MW); -1 lets the optimiser '
                               'choose it within capacity_bounds.', examples=[-1])
    turbine_inlet: FiniteList = Field(
        (), alias='turbine_t_p', description='Cogeneration only: turbine inlet [temperature (degC), pressure '
        '(bar)].', examples=[[564, 152]])
    condenser_pressure: Real = Field(0.0, alias='condenser_p', description='Cogeneration only: condenser '
                                     'pressure (bar).', examples=[0.05])


class Storage(_Model):
    """An electricity store (battery, pumped hydro), optionally fed by natural inflow (serialised in ``flex``)."""

    identifier: Identifier = Field(alias='iden', description='Identifier, unique among stores.', examples=['bstr'])
    fixed_cost: Real = Field(alias='fix_cost_strg', description='Fixed cost (USD per MWh of capacity per year).',
                             examples=[27248])
    duration_hours: Positive = Field(alias='hours_of_storage', description='Hours at full discharge: charge and '
                                     'discharge power are limited to capacity / duration_hours (h, > 0).',
                                     examples=[4])
    round_trip_efficiency: PositiveFraction = Field(description='Round-trip efficiency, in (0, 1].',
                                                    examples=[0.85])
    capacity_bounds: Bounds = Field(alias='l_strg', description='[low, high] bounds on the installed energy '
                                    'capacity (MWh).', examples=[[0, 4e5]])
    capacity: Capacity = Field(alias='c_strg', description='Energy capacity (MWh); -1 lets the optimiser choose '
                               'it.', examples=[-1])
    initial_state_of_charge: Fraction = Field(alias='soc_ini', description='Level at the start of the year, as a '
                                              'fraction of capacity; the year closes on the same level.',
                                              examples=[0.5])
    min_state_of_charge: Fraction = Field(0.0, alias='soc_min', description='Lowest level, as a fraction of '
                                          'capacity.')
    max_state_of_charge: Fraction = Field(1.0, alias='soc_max', description='Highest level, as a fraction of '
                                          'capacity.')
    annual_inflow: NonNegative = Field(0.0, alias='inflow_total', description='Natural inflow per year (MWh); '
                                       '0 means none.')
    inflow_profile: OptionalProfile = Field(
        None, description='Shape of the inflow, scaled to annual_inflow. Absent or \'\' means flat. ' + PROFILE_DOC)
    charge_allowed: Flag = Field(True, description='false forbids charging from the grid (a dam fed only by '
                                 'its catchment).')

    @model_validator(mode='after')
    def _levels_are_ordered(self) -> 'Storage':
        if not self.min_state_of_charge <= self.max_state_of_charge:
            raise _inconsistent('soc_min', 'soc_min and soc_max must satisfy 0 <= soc_min <= soc_max <= 1')
        if not self.min_state_of_charge <= self.initial_state_of_charge <= self.max_state_of_charge:
            raise _inconsistent('soc_ini', 'soc_ini must lie between soc_min and soc_max')
        return self


class Process(_Model):
    """A Power-to-X process: a production unit and a product store (serialised in ``p2x``).

    Quantities are in the product's unit Q (m3 of water, kg of hydrogen, MWh of heat).
    """

    identifier: Identifier = Field(alias='iden', description='Identifier, unique among processes.',
                                   examples=['p2x-ro'])
    kind: EntityType = Field(alias='type', description='\'elec\' (electricity only) or \'elec + ther\' '
                             '(electricity and heat from cogeneration units).')
    extraction_temperature: Real = Field(0, alias='temperature', description='Steam extraction temperature '
                                         '(degC). Required for \'elec + ther\'; unused otherwise.', examples=[80])
    profile: Profile = Field('', description='Availability shape, as for generators. ' + PROFILE_DOC)
    capacity_factor: Fraction = Field(description='Fraction in [0, 1], as for generators.', examples=[0.85])
    heat_sources: Names = Field((), alias='supply_sources', description='\'elec + ther\' only: identifiers of the '
                                'cogeneration generators supplying heat. A generator may supply one process.',
                                examples=[['nucl', 'ccgt']])
    production_fixed_cost: Real = Field(alias='fix_cost_prod', description='Fixed cost (USD per Q/h per year).',
                                        examples=[4271])
    production_variable_cost: Real = Field(alias='var_cost_prod', description='Variable cost excluding energy '
                                           '(USD/Q).', examples=[0.092])
    electricity_use: NonNegative = Field(alias='pow_use_elec_prod', description='Electricity use (MWh/Q).',
                                         examples=[0.0035])
    heat_use: NonNegative = Field(alias='pow_use_ther_prod', description='Heat use (MWh/Q); must be 0 for '
                                  '\'elec\'.', examples=[0])
    production_capacity_bounds: Bounds = Field(alias='l_prod', description='[low, high] bounds on the installed '
                                               'production capacity (Q/h).', examples=[[0, 1e6]])
    production_capacity: Capacity = Field(alias='c_prod', description='Production capacity (Q/h); -1 lets the '
                                          'optimiser choose it.', examples=[-1])
    storage_fixed_cost: Real = Field(alias='fix_cost_strg', description='Fixed cost of product storage (USD per Q '
                                     'per year).', examples=[0.24])
    storage_capacity_bounds: Bounds = Field(alias='l_strg', description='[low, high] bounds on the installed '
                                            'storage capacity (Q).', examples=[[0, 5e7]])
    storage_capacity: Capacity = Field(alias='c_strg', description='Storage capacity (Q); -1 lets the optimiser '
                                       'choose it.', examples=[-1])
    initial_state_of_charge: Fraction = Field(alias='soc_ini', description='Store level at the start of the year, '
                                              'as a fraction of capacity; the year closes on the same level.',
                                              examples=[0.5])

    @model_validator(mode='after')
    def _heat_matches_type(self) -> 'Process':
        if self.kind == 'elec' and self.heat_use > 0:
            raise _inconsistent('pow_use_ther_prod', '\'pow_use_ther_prod\' is ' + repr(self.heat_use) + ' but the '
                                'process type is \'elec\': its heat requirement would be ignored (use type '
                                '\'elec + ther\')')
        if self.kind == 'elec + ther' and 'extraction_temperature' not in self.model_fields_set:
            raise _inconsistent('temperature', 'missing required field \'temperature\' (the process type is '
                                '\'elec + ther\')', 'field.missing')
        return self


# --- the case ---------------------------------------------------------------------

_EXAMPLE_CASE: Dict[str, Any] = {
    'format_version': 1,
    'demand': {'e': {'iden': 'electricity', 'profile': 'dmnd.csv', 'total': 5.69e6, 'var_cost_ns': 20000,
                     'l_ns': [0, 1e6]},
               'x': [{'iden': 'water', 'total': 5.0e7, 'supply_sources': ['p2x-ro'], 'var_cost_ns': 1000,
                      'l_ns': [0, 1e9]}]},
    'generator': [{'iden': 'wind', 'type': 'elec', 'profile': 'wind.csv', 'capacity_factor': 0.25,
                   'fix_cost_prod': 133553, 'var_cost_prod': 0, 'var_emis_prod': 0, 'l_prod': [0, 1e5],
                   'c_prod': -1},
                  {'iden': 'ocgt', 'type': 'elec', 'capacity_factor': 0.85, 'fix_cost_prod': 75182,
                   'var_cost_prod': 96.11, 'var_emis_prod': 523, 'l_prod': [0, 1e5], 'c_prod': -1}],
    'flex': [{'iden': 'bstr', 'fix_cost_strg': 27248, 'hours_of_storage': 4, 'round_trip_efficiency': 0.85,
              'l_strg': [0, 4e5], 'c_strg': -1, 'soc_ini': 0.5}],
    'p2x': [{'iden': 'p2x-ro', 'type': 'elec', 'capacity_factor': 0.85, 'fix_cost_prod': 4271,
             'var_cost_prod': 0.092, 'pow_use_elec_prod': 0.0035, 'pow_use_ther_prod': 0, 'l_prod': [0, 1e6],
             'c_prod': -1, 'fix_cost_strg': 0.24, 'l_strg': [0, 5e7], 'c_strg': -1, 'soc_ini': 0.5}],
}


class Case(_Model):
    """A complete IESO case in the canonical input format.

    The canonical format is versioned (``format_version`` 1) and holds inputs
    only: no output arrays, KPIs, solver statistics or provenance. An
    unversioned document is a legacy input and is read through
    ieso.formats, which removes the documented output-only fields.
    """

    model_config = ConfigDict(json_schema_extra={'examples': [_EXAMPLE_CASE]})

    format_version: Version = Field(
        description='Input format version. Must be ' + str(INPUT_FORMAT_VERSION) + '; an input without it is read '
        'as a legacy document.')
    demand: Demand = Field(description='Final demands.')
    p2x: Tuple[Process, ...] = Field(description='Power-to-X processes.')
    generator: Tuple[Generator, ...] = Field(description='Generators.')
    flex: Tuple[Storage, ...] = Field(description='Electricity stores (flexibility means).')


# --- run options --------------------------------------------------------------------

class SolveOptions(_Model):
    """Run options, serialised under the command-line names.

    Both are optional; an absent option imposes no constraint.
    """

    carbon_constraint: OptionalReal = Field(
        None, alias='carbon-constraint', description='Emissions cap, in kg CO2eq per MWh of annual primary '
        'electricity demand, applied to total system emissions. Any finite value; a negative cap requires net '
        'removal.', examples=[50.0])
    non_served_power_constraint: OptionalFraction = Field(
        None, alias='non-served-power-constraint', description='Cap on annual unmet electricity, as a fraction '
        'of annual electricity demand, in [0, 1].', examples=[0.05])

    @classmethod
    def names(cls) -> List[str]:
        """The recognised option names, as written on the command line."""
        return sorted(f.alias for f in cls.model_fields.values() if f.alias)
