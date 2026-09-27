#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""Semantic validation: the rules that relate a case's objects to one another
and to data outside the document.

Structure -- types, required fields, allowed values, finite numbers, local
ranges and unknown fields -- is validated first, once, by the public input
models (ieso/models.py). The functions here receive the working
document built from a validated model (formats.internal_document) and check:

* identifiers: unique among generators, among stores, among processes, and
  across all demands;
* references and ownership: a demand names existing processes, and a process
  supplies at most one active demand;
* thermal topology: a thermally coupled process draws heat from existing
  cogeneration units with turbine data, and a generator supplies heat to at
  most one process;
* profiles: every profile that will be read resolves to a file (or is inline),
  and holds exactly `hours` finite, non-negative values that are not all zero;
* hourly shortfall bounds: l_ns[0] does not exceed the demand of any hour;
* optionally, thermodynamics: the cogeneration coefficients of every
  heat-supplying unit can be obtained and are admissible (runs the packaged
  thermodynamics executable, ieso/_bin/ieso-thermo, or RunConfig.thermo_bin).

The first problem found is raised as an InputError (or ThermoError), with a
stable code, a JSON Pointer path, the entity, the field and, for hourly
checks, the zero-based hour. What is deliberately NOT refused: negative
emission factors (removal technologies), negative carbon targets, zero variable
costs, zero shortage penalties, and negative economic costs generally.
"""

from typing import Any, Dict, List, Mapping, Optional, Tuple

from ieso import fcn as u
from ieso.errors import ThermoError
from ieso.formats import pointer


def who_demand(n, dmd):

    return 'demand.e' if n == 0 else 'demand.x[' + dmd['iden'] + ']'


def demand_loc(n):

    return ('demand', 'e') if n == 0 else ('demand', 'x', n - 1)


def active(n, dmd):

    # The electricity demand is always built; a commodity demand of zero is not.
    return n == 0 or dmd['total'] > 0


def identifiers(s):

    for label in ('generator', 'p2x', 'flex'):

        seen = set()

        for n, item in enumerate(s[label]):

            if item['iden'] in seen:

                u.fail(item['iden'], 'duplicate ' + label + ' identifier', field='iden',
                       code='identifier.duplicate', path=pointer(label, n, 'iden'))

            seen.add(item['iden'])

    # Demand identifiers key the allocation accounts: a duplicate overwrote the
    # first entry's quantities and the shares no longer summed to one.

    seen = set()

    for n, dmd in enumerate([s['demand']['e']] + s['demand']['x']):

        if dmd['iden'] in seen:

            u.fail('demand.x[' + dmd['iden'] + ']', 'duplicate demand identifier \'' + dmd['iden'] + '\'',
                   field='iden', code='identifier.duplicate', path=pointer(*demand_loc(n), 'iden'))

        seen.add(dmd['iden'])


def profiles(s, cfg):

    """Every profile the model will read: resolved, loaded and checked."""

    for n, gen in enumerate(s['generator']):

        u.as_profile(gen['profile'], gen['iden'], cfg.hours, cfg.profile_base, 'profile',
                     path=pointer('generator', n, 'profile'))

    for n, flx in enumerate(s['flex']):

        if flx['inflow_total'] > 0:

            u.as_profile(flx.get('inflow_profile', ''), flx['iden'], cfg.hours, cfg.profile_base, 'inflow_profile',
                         path=pointer('flex', n, 'inflow_profile'))

    for n, p2x in enumerate(s['p2x']):

        u.as_profile(p2x['profile'], p2x['iden'], cfg.hours, cfg.profile_base, 'profile',
                     path=pointer('p2x', n, 'profile'))

    for n, dmd in enumerate([s['demand']['e']] + s['demand']['x']):

        if active(n, dmd):

            u.as_profile(dmd['profile'], who_demand(n, dmd), cfg.hours, cfg.profile_base, 'profile',
                         path=pointer(*demand_loc(n), 'profile'))


def topology(s):

    generators = {gen['iden']: n for n, gen in enumerate(s['generator'])}

    processes = {p2x['iden']: n for n, p2x in enumerate(s['p2x'])}

    # --- demands name processes that exist, and a process serves one demand
    #
    # Each product balance credits the whole of x_supp for every process it
    # names, so a process named by two active demands satisfied both with the
    # same output. Apportioning one process's delivery between demands needs
    # allocation variables this model does not have, so the configuration is
    # refused. Several processes supplying one demand remain supported.

    served_by = {}

    for n, dmd in enumerate(s['demand']['x']):

        if dmd['total'] <= 0:

            continue

        for name in dmd['supply_sources']:

            if name not in processes:

                u.fail('demand.x[' + dmd['iden'] + ']', 'unknown supply source \'' + name + '\'',
                       field='supply_sources', code='reference.unknown',
                       path=pointer('demand', 'x', n, 'supply_sources'))

            served_by.setdefault(name, []).append(dmd['iden'])

    for name, demands in served_by.items():

        if len(demands) > 1:

            u.fail(name, 'process \'' + name + '\' supplies more than one demand ('
                   + ', '.join(demands) + '); its output would be counted once for each',
                   code='topology.process_shared', path=pointer('p2x', processes[name]))

    # --- thermal processes name generators that can actually extract heat

    heat_consumers = {}

    for m, p2x in enumerate(s['p2x']):

        if p2x['type'] != 'elec + ther':

            continue

        where = pointer('p2x', m, 'supply_sources')

        if not p2x['supply_sources']:

            u.fail(p2x['iden'], 'a thermally coupled process needs at least one heat supply source',
                   field='supply_sources', code='topology.no_heat_source', path=where)

        for name in p2x['supply_sources']:

            if name not in generators:

                u.fail(p2x['iden'], 'unknown heat supply source \'' + name + '\'', field='supply_sources',
                       code='reference.unknown', path=where)

            n = generators[name]

            gen = s['generator'][n]

            if gen['type'] != 'elec + ther':

                u.fail(p2x['iden'], 'heat supply source \'' + name + '\' is not a cogeneration unit',
                       field='supply_sources', code='topology.not_cogeneration', path=where)

            if len(gen['turbine_t_p']) < 2 or not gen['condenser_p'] > 0:

                field = 'turbine_t_p' if len(gen['turbine_t_p']) < 2 else 'condenser_p'

                u.fail(name, 'cogeneration requires turbine_t_p and a positive condenser_p', field=field,
                       code='cogeneration.parameters', path=pointer('generator', n, field))

            heat_consumers.setdefault(name, []).append(p2x['iden'])

    # --- a generator's heat cannot be shared between processes
    #
    # Each thermally coupled process carries its own heat balance against the
    # same h_prod variables, so two processes drawing on one generator are each
    # satisfied by the same heat: it is counted once per process and the energy
    # is spent twice. The extraction temperature is also taken from whichever
    # process is encountered first, so a second process at a different
    # temperature would silently inherit the first one's coefficients.
    #
    # Apportioning heat between consumers needs a formulation this model does
    # not have, so the configuration is refused rather than approximated. One
    # process drawing on several generators remains supported, as do independent
    # thermal groups.

    for name, consumers in heat_consumers.items():

        if len(consumers) > 1:

            u.fail(name, 'heat is shared between processes ' + ', '.join(sorted(consumers))
                   + '; a generator can supply heat to only one process', code='topology.heat_shared',
                   path=pointer('generator', generators[name]))


def shortfalls(s, cfg):

    """l_ns[0] against the demand of every hour (fcn.shortfall_bounds)."""

    for n, dmd in enumerate([s['demand']['e']] + s['demand']['x']):

        if not active(n, dmd):

            continue

        who = who_demand(n, dmd)

        dm = u.dm_h(dmd['profile'], dmd['total'], who, hours=cfg.hours, base=cfg.profile_base)

        u.shortfall_bounds(dm, dmd['l_ns'], who, path=pointer(*demand_loc(n), 'l_ns'))


def heat_suppliers(s: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any], Dict[str, Any]]]:

    """(generator index, generator, process) for every unit that supplies heat.

    After topology() each cogeneration unit supplies at most one process; a
    unit that no process draws on is not listed.
    """

    pairs = []

    for n, gen in enumerate(s['generator']):

        if gen['type'] != 'elec + ther':

            continue

        for p2x in s['p2x']:

            if p2x['type'] == 'elec + ther' and gen['iden'] in p2x['supply_sources']:

                pairs.append((n, gen, p2x))

                break

    return pairs


def cogeneration(gen: Dict[str, Any], p2x: Dict[str, Any], cfg: u.RunConfig,
                 path: Optional[str] = None) -> Tuple[float, float]:

    """
    The coefficients (a, b) of `gen` supplying heat to `p2x`, from the
    thermodynamics executable. A coupled unit without admissible coefficients
    is an input error; it is never converted to electric-only.
    """

    a, b, oops = u.thermo(gen['turbine_t_p'][0], gen['turbine_t_p'][1], gen['condenser_p'], p2x['temperature'],
                          binary=cfg.thermo_bin, timeout=cfg.thermo_timeout)

    if oops:

        reason = oops if isinstance(oops, str) else 'no admissible coefficients'

        raise ThermoError('thermodynamic calculation failed (turbine inlet '
                          + str(gen['turbine_t_p'][0]) + ' C / ' + str(gen['turbine_t_p'][1])
                          + ' bar, condenser ' + str(gen['condenser_p']) + ' bar, extraction '
                          + str(p2x['temperature']) + ' C): ' + reason,
                          generator=gen['iden'], process=p2x['iden'], reason=reason, path=path)

    return a, b


def validate(s: Dict[str, Any], opts: Mapping[str, float], cfg: u.RunConfig = u.RunConfig(),
             thermodynamics: bool = False) -> None:

    """
    Check the semantic rules on the working document `s`; raise on the first
    failure. With `thermodynamics`, also obtain every heat-supplying unit's
    cogeneration coefficients (the solve itself does this while building the
    problem, in eqs_gen).
    """

    identifiers(s)

    profiles(s, cfg)

    topology(s)

    shortfalls(s, cfg)

    if thermodynamics:

        for n, gen, p2x in heat_suppliers(s):

            cogeneration(gen, p2x, cfg, path=pointer('generator', n))


def define(glop: Any, s: Dict[str, Any], opts: Mapping[str, float], stat: Dict[str, Any], cfg: u.RunConfig) -> None:

    validate(s, opts, cfg)
