#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


from ieso_modules import fcn as u


def define(glop, s, opts, stat):

    # --- --- --- --- --- --- --- --- --- Configuration checks
    #
    # Run before the problem is built, so a configuration the formulation cannot
    # represent is refused rather than solved into a plausible-looking answer.

    generators = {gen['iden']: gen for gen in s['generator']}

    processes = {p2x['iden']: p2x for p2x in s['p2x']}

    # --- identifiers are unique

    for label, items in (('generator', s['generator']), ('p2x', s['p2x']), ('flex', s['flex'])):

        seen = set()

        for item in items:

            if item['iden'] in seen:

                u.fail(item['iden'], 'duplicate ' + label + ' identifier')

            seen.add(item['iden'])

    # --- demands name processes that exist

    for dmd in s['demand']['x']:

        if dmd['total'] <= 0:

            continue

        for name in dmd['supply_sources']:

            if name not in processes:

                u.fail('demand.x[' + dmd['iden'] + ']', 'unknown supply source \'' + name + '\'')

    # --- thermal processes name generators that can actually extract heat

    heat_consumers = {}

    for p2x in s['p2x']:

        if p2x['type'] != 'elec + ther':

            continue

        if not p2x['supply_sources']:

            u.fail(p2x['iden'], 'a thermally coupled process needs at least one heat supply source')

        for name in p2x['supply_sources']:

            if name not in generators:

                u.fail(p2x['iden'], 'unknown heat supply source \'' + name + '\'')

            gen = generators[name]

            if gen['type'] != 'elec + ther':

                u.fail(p2x['iden'], 'heat supply source \'' + name + '\' is not a cogeneration unit')

            if len(gen.get('turbine_t_p', [])) < 2 or not gen.get('condenser_p', 0) > 0:

                u.fail(name, 'cogeneration requires turbine_t_p and a positive condenser_p')

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
                   + '; a generator can supply heat to only one process')
