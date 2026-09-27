#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser


import math

import numpy as np

from ies_optimiser import pos_dmd

from ies_optimiser import fcn as u


def process(glop, s, opts, stat, emis_con, nspo_con, cfg):


    # --- --- --- --- --- --- --- --- --- Post processing


    # --- dmd

    pos_dmd.demand_props(s, opts, emis_con, nspo_con, glop.Objective().Value(), cfg)

    checks = s['system']['checks']

    store_resid, store_scale = 0.0, 0.0


    # --- gen

    for gen in s['generator']:

        # --- gen['availability']
        #
        # A supplied profile is rescaled so its mean equals capacity_factor, so
        # the series can pass one and the nameplate limit then holds output
        # below what the availability relation alone would permit. Report the
        # requested factor, the peak of the rescaled series and the availability
        # actually left after the limit, so that difference is visible rather
        # than absorbed silently into the result.

        gen['availability'] = availability(gen, cfg.hours, cfg.profile_base)

        # --- gen['c_prod']

        if u.capaSetToBeOptimised(gen['c_prod']):

            gen['c_prod'] = gen['c_prod'].solution_value()

        # --- gen['e_prod']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(gen['e_prod'][i].solution_value())

        gen['e_prod'] = rows

        # --- gen['h_prod']

        if gen['type'] == 'elec + ther':

            rows = []

            for i in range(0, cfg.hours):

                rows.append(gen['h_prod'][i].solution_value())

            gen['h_prod'] = rows


    # --- flx

    for flx in s['flex']:

        # --- flx['c_strg']

        if u.capaSetToBeOptimised(flx['c_strg']):

            flx['c_strg'] = flx['c_strg'].solution_value()

        # --- flx['e_strg']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(flx['e_strg'][i].solution_value())

        flx['e_strg'] = rows

        # --- flx['e_char']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(flx['e_char'][i].solution_value())

        flx['e_char'] = rows

        # --- flx['e_disc']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(flx['e_disc'][i].solution_value())

        flx['e_disc'] = rows

        # --- flx['e_spil']

        if flx.get('inflow_total', 0) > 0:

            rows = []

            for i in range(0, cfg.hours):

                rows.append(flx['e_spil'][i].solution_value())

            flx['e_spil'] = rows

        # --- checks
        #
        # Verify the storage balance itself, hour by hour:
        #
        #   e_strg[i] = e_strg[i-1] + sqrt(rte)*e_char[i] - e_disc[i]/sqrt(rte)
        #                           + inflow[i] - e_spil[i]
        #
        # The ratio of total discharge to total charge equals the round-trip
        # efficiency only for a store with no inflow whose inventory returns to
        # its starting level; it is not an invariant of a reservoir, of a store
        # left off-cycle, or of one that never charges. The balance is.

        if flx['c_strg'] > 0:

            _sqrt_rte = math.sqrt(flx['round_trip_efficiency'])

            _has_inflow = flx.get('inflow_total', 0) > 0

            _inflow = u.dm_h(flx.get('inflow_profile', ''), flx['inflow_total'], flx['iden'], hours=cfg.hours,
                             base=cfg.profile_base, field='inflow_profile') if _has_inflow else None

            _resid = 0.0

            for i in range(0, cfg.hours):

                _prev = flx['soc_ini'] * flx['c_strg'] if i == 0 else flx['e_strg'][i - 1]

                _expected = _prev + flx['e_char'][i] * _sqrt_rte - flx['e_disc'][i] / _sqrt_rte

                if _has_inflow:

                    _expected += _inflow[i] - flx['e_spil'][i]

                _resid = max(_resid, abs(flx['e_strg'][i] - _expected))

            # the year closes where it began
            if cfg.storage_closes_the_year:
                _resid = max(_resid, abs(flx['e_strg'][cfg.hours - 1] - flx['soc_ini'] * flx['c_strg']))
            store_resid = max(store_resid, _resid)
            store_scale = max(store_scale, flx['c_strg'])

    # --- p2x

    for p2x in s['p2x']:

        p2x['availability'] = availability(p2x, cfg.hours, cfg.profile_base)

        # --- p2x['c_prod']

        if u.capaSetToBeOptimised(p2x['c_prod']):

            p2x['c_prod'] = p2x['c_prod'].solution_value()

        # --- p2x['x_prod']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(p2x['x_prod'][i].solution_value())

        p2x['x_prod'] = rows

        # --- p2x['c_strg']

        if u.capaSetToBeOptimised(p2x['c_strg']):

            p2x['c_strg'] = p2x['c_strg'].solution_value()

        # --- p2x['x_strg']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(p2x['x_strg'][i].solution_value())

        p2x['x_strg'] = rows

        # --- p2x['x_supp']

        rows = []

        for i in range(0, cfg.hours):

            rows.append(p2x['x_supp'][i].solution_value())

        p2x['x_supp'] = rows

        # --- checks: product inventory x_strg[i] = x_strg[i-1] + x_prod[i] - x_supp[i]
        _resid = 0.0
        for i in range(0, cfg.hours):
            _prev = p2x['soc_ini'] * p2x['c_strg'] if i == 0 else p2x['x_strg'][i - 1]
            _resid = max(_resid, abs(p2x['x_strg'][i] - (_prev + p2x['x_prod'][i] - p2x['x_supp'][i])))
        if cfg.storage_closes_the_year:
            _resid = max(_resid, abs(p2x['x_strg'][cfg.hours - 1] - p2x['soc_ini'] * p2x['c_strg']))
        store_resid = max(store_resid, _resid)
        store_scale = max(store_scale, p2x['c_strg'], max(p2x['x_supp']) if p2x['x_supp'] else 0.0)

        # --- p2x['shadow_prices']['demand_match']
        #
        # Dual of the process heat balance: the marginal cost of one more unit of
        # heat to this process, in $ per MWh of heat. Defined only for thermally
        # coupled processes; a purely electric process has no such constraint and
        # the series stays empty. This is not the water (or other product)
        # delivery dual, which belongs to the demand object.

        p2x['shadow_prices'] = p2x.get('shadow_prices', {})

        rows = []

        if '__meet_dmnd' in p2x:

            for i in range(0, cfg.hours):

                rows.append(p2x['__meet_dmnd'][i].dual_value())

        p2x['shadow_prices']['demand_match'] = rows


    if s['flex'] or s['p2x']:
        pos_dmd.check(checks, 'storage_balance', store_resid, pos_dmd.feas_tol(store_scale))

    pos_dmd.finish_checks(s)

    # --- purge non-serializable solver objects before dumping JSON

    for p in s['p2x']:

        p.pop('__meet_dmnd', None)

    s['demand']['e'].pop('__meet_dmnd', None)

    for dx in s['demand']['x']:

        dx.pop('__meet_dmnd', None)


def availability(item, hours, base):

    """
    What the profile asked for against what it can deliver.

    A supplied profile is rescaled so its mean equals capacity_factor, so the
    series can pass one and the nameplate limit then holds output below what
    the availability relation alone would permit. Report the requested factor,
    the peak of the rescaled series and the availability actually left after
    the limit, so that difference is visible rather than absorbed silently.
    """

    _cf = u.cf_h(item['profile'], item['capacity_factor'], item['iden'], hours=hours, base=base)

    return {
        'capacity_factor_requested': item['capacity_factor'],
        'profile_peak': max(_cf),
        'capacity_factor_effective': sum(min(v, 1.0) for v in _cf) / hours,
        'hours_above_nameplate': sum(1 for v in _cf if v > 1.0),
    }
