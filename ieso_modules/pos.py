#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso


import math

import numpy as np

from ieso_modules import pos_dmd

from ieso_modules import fcn as u


def process(glop, s, opts, stat, emis_con, nspo_con):


    # --- --- --- --- --- --- --- --- --- Post processing


    # --- dmd

    pos_dmd.demand_props(s, opts, emis_con, nspo_con)


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

        _cf = u.cf_h(gen['profile'], gen['capacity_factor'], gen['iden'])

        _peak = max(_cf)

        _effective = sum(min(v, 1.0) for v in _cf) / u.Y2H

        gen['availability'] = {
            'capacity_factor_requested': gen['capacity_factor'],
            'profile_peak': _peak,
            'capacity_factor_effective': _effective,
            'hours_above_nameplate': sum(1 for v in _cf if v > 1.0),
        }

        # --- gen['c_prod']

        if u.capaSetToBeOptimised(gen['c_prod']):

            gen['c_prod'] = gen['c_prod'].solution_value()

        # --- gen['e_prod']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(gen['e_prod'][i].solution_value())

        gen['e_prod'] = rows

        # --- gen['h_prod']

        if gen['type'] == 'elec + ther':

            rows = []

            for i in range(0, u.Y2H):

                rows.append(gen['h_prod'][i].solution_value())

            gen['h_prod'] = rows


    # --- flx

    for flx in s['flex']:

        # --- flx['c_strg']

        if u.capaSetToBeOptimised(flx['c_strg']):

            flx['c_strg'] = flx['c_strg'].solution_value()

        # --- flx['e_strg']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(flx['e_strg'][i].solution_value())

        flx['e_strg'] = rows

        # --- flx['e_char']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(flx['e_char'][i].solution_value())

        flx['e_char'] = rows

        # --- flx['e_disc']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(flx['e_disc'][i].solution_value())

        flx['e_disc'] = rows

        # --- flx['e_spil']

        if flx.get('inflow_total', 0) > 0:

            rows = []

            for i in range(0, u.Y2H):

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

            _inflow = u.dm_h(flx.get('inflow_profile', ''), flx['inflow_total'], flx['iden'] + ' inflow') if _has_inflow else None

            _resid = 0.0

            for i in range(0, u.Y2H):

                _prev = flx['soc_ini'] * flx['c_strg'] if i == 0 else flx['e_strg'][i - 1]

                _expected = _prev + flx['e_char'][i] * _sqrt_rte - flx['e_disc'][i] / _sqrt_rte

                if _has_inflow:

                    _expected += _inflow[i] - flx['e_spil'][i]

                _resid = max(_resid, abs(flx['e_strg'][i] - _expected))

            if _resid > u.Balance_atol + u.Balance_rtol * flx['c_strg']:

                if u.Verbose:

                    print('storage balance residual', flx['iden'], _resid)


    # --- p2x

    for p2x in s['p2x']:

        # --- p2x['c_prod']

        if u.capaSetToBeOptimised(p2x['c_prod']):

            p2x['c_prod'] = p2x['c_prod'].solution_value()

        # --- p2x['x_prod']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(p2x['x_prod'][i].solution_value())

        p2x['x_prod'] = rows

        # --- p2x['c_strg']

        if u.capaSetToBeOptimised(p2x['c_strg']):

            p2x['c_strg'] = p2x['c_strg'].solution_value()

        # --- p2x['x_strg']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(p2x['x_strg'][i].solution_value())

        p2x['x_strg'] = rows

        # --- p2x['x_supp']

        rows = []

        for i in range(0, u.Y2H):

            rows.append(p2x['x_supp'][i].solution_value())

        p2x['x_supp'] = rows

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

            for i in range(0, u.Y2H):

                rows.append(p2x['__meet_dmnd'][i].dual_value())

        p2x['shadow_prices']['demand_match'] = rows


    # --- purge non-serializable solver objects before dumping JSON

    for p in s['p2x']:

        p.pop('__meet_dmnd', None)

    s['demand']['e'].pop('__meet_dmnd', None)

    for dx in s['demand']['x']:

        dx.pop('__meet_dmnd', None)
