#!/usr/bin/env python3
"""Build the four illustrative IESO datasets from one parameter table.

    python3 tools/build_datasets.py            (from any directory)

One island node, one template. Every case offers the same generation
candidates at the same costs, on the same demand and weather; each variant
adds exactly one Power-to-X process to the base:

    datasets/elec-grid/                         the base
    datasets/elec-grid+power-to-hydrogen/       + electrolysis
    datasets/elec-grid+power-to-water-ro/       + reverse osmosis
    datasets/elec-grid+power-to-water-med/      + multi-effect distillation

The canonical hourly profiles live in datasets/elec-grid/ (dmnd.csv, solr.csv,
wind.csv) and are copied unchanged into every other dataset, so each is
self-contained. Every coefficient below carries its source; the derivations are
written out so the numbers in the JSON files can be checked by hand. The
generated inputs are rounded illustrative assumptions.

Currency: USD. Annualisation: capital x CRF(7%, life) + fixed O&M, for every
technology, each with its own source's lifetime.
"""

import hashlib
import json
import os
import shutil
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join('datasets', 'elec-grid')
PROFILES = ('dmnd.csv', 'solr.csv', 'wind.csv')

DISCOUNT = 0.07
HOURS_85 = 0.85 * 8760                  # NEA quotes fixed O&M per MWh at an 85% capacity factor
GJ_PER_MWH = 3.6
BTU_PER_KWH = 3412.14                   # heat-rate conversion: efficiency = 3412.14 / (Btu/kWh)


def crf(r, n):
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


# --- demand ------------------------------------------------------------------
# Annual electricity demand: 5.69 TWh, the 2025 total estimated from ENTSO-E
# actual load (monthly mean load x hours; 12% of 2025 hours are missing, so
# monthly means stand in for them). The hourly SHAPE is 2021 (dmnd.csv); IESO
# scales it to this total.
E_TOTAL = 5.69e6                        # MWh

# --- fuels and emission factors: Danish Energy Agency (DEA) ------------------
# Samfundsøkonomiske beregningsforudsætninger for energipriser og emissioner
# 2025, final edition 26 March 2026, fixed 2025 prices:
#   Table 5  gas oil (gasolie) import (CIF) price 2025: 116.3 DKK/GJ
#   Table 6  delivery to power station:                  +2.6 DKK/GJ
#   Table 1b exchange rate 2025:                          6.86 DKK/USD
#   Table 12 CO2: gas oil 74.1 kg/GJ; coal (steam turbine) 95.1 kg/GJ
GAS_OIL_USD_MWH = (116.3 + 2.6) / 6.86 * GJ_PER_MWH       # 62.40 USD per MWh of fuel
CO2_GAS_OIL = 74.1 * GJ_PER_MWH                           # kg per MWh of fuel
CO2_COAL = 95.1 * GJ_PER_MWH

# --- nuclear and coal: NEA/EPRI, The Costs of Generating Electricity 2025 -----
# Overnight cost: Table 3.1 OECD mean across participating countries.
# Efficiency, fuel (USD/MWh_e), O&M: means of the per-country rows of
# Tables 3.2 (large-scale nuclear, near-term; 13 legible rows) and 3.19 (coal,
# 12 rows). Fixed O&M is quoted per MWh at 85%, converted to per MW-year.
# Lifetimes: NEA methodology, nuclear 60 years, coal 40 years.
NUC_ROWS = [(33, 7.84, 17.65, 3.48), (32, 9.06, 33.44, 11.86), (32, 9.06, 33.44, 11.86),
            (32, 7.35, 17.18, 2.94), (32, 9.00, 19.35, 10.00), (32, 9.06, 27.67, 11.86),
            (32, 9.06, 33.44, 11.86), (32, 9.06, 19.97, 11.86), (32, 5.69, 24.81, 17.78),
            (32, 9.06, 33.44, 11.86), (32, 9.06, 33.44, 11.86), (32, 9.06, 33.44, 11.86),
            (32, 9.06, 32.68, 11.86)]      # efficiency %, fuel, O&M fixed, O&M variable (USD/MWh)
COAL_ROWS = [(42, 16.90, 5.72, 3.08), (38, 30.00, 20.94, 5.94), (41, 20.72, 5.49, 3.10),
             (38, 37.65, 15.54, 5.94), (50, 30.00, 13.20, 4.50), (38, 30.00, 20.94, 5.94),
             (38, 30.00, 20.94, 5.94), (38, 40.00, 20.94, 5.94), (43, 45.50, 8.25, 13.00),
             (38, 30.00, 20.94, 5.94), (38, 30.00, 20.94, 5.94), (38, 17.84, 20.94, 5.94)]


def nea(rows, overnight_usd_kw, life, co2_fuel_kg_mwh):
    eff = np.mean([r[0] for r in rows]) / 100
    fuel, fom, vom = (float(np.mean([r[k] for r in rows])) for k in (1, 2, 3))
    return {
        'fix_cost_prod': overnight_usd_kw * 1e3 * crf(DISCOUNT, life) + fom * HOURS_85,
        'var_cost_prod': fuel + vom,
        'var_emis_prod': co2_fuel_kg_mwh / eff,
    }


# --- gas-oil turbines: Lazard LCOE+ 2026 (LCOE v19.0), midpoints --------------
# Plant costs only (capital, fixed and variable O&M, heat rate, 30-year life):
#   Gas Combined Cycle: 1,450-2,100 USD/kW; 10.00-25.50 USD/kW-yr; 2.75-5.00 USD/MWh; 6,475-6,550 Btu/kWh
#   Gas Peaking:        1,100-1,650 USD/kW; 10.00-17.00 USD/kW-yr; 3.50-5.00 USD/MWh; 10,275-11,175 Btu/kWh
# Lazard's US gas price is NOT used: the island has no gas supply, so these
# turbines burn gas oil at the DEA price, with the DEA emission factor.
def lazard(capex, fom, vom, heat_rate, life=30):
    eff = BTU_PER_KWH / np.mean(heat_rate)
    return {
        'fix_cost_prod': np.mean(capex) * 1e3 * crf(DISCOUNT, life) + np.mean(fom) * 1e3,
        'var_cost_prod': GAS_OIL_USD_MWH / eff + np.mean(vom),
        'var_emis_prod': CO2_GAS_OIL / eff,
    }


# --- solar, wind, battery: the 2021 island package (IRENA 24/7 Renewables, Europe 2025)
#   Solar PV 683 USD/kW, fixed O&M 2%/yr, 20 years, siting limit 3,000 MW
#   Wind     1,034 USD/kW, fixed O&M 3%/yr, 25 years, siting limit 1,000 MW
#   Battery  171 USD/kWh, O&M 2.5%/yr, 15 years, 4 h, 85% round trip, limit 5,000 MWh
def irena(capex, fom_share, life):
    return capex * crf(DISCOUNT, life) + fom_share * capex


GEN = {
    'nucl': dict(nea(NUC_ROWS, 11545, 60, 0.0), capacity_factor=0.85, l_prod=[0, 100e3]),
    'coal': dict(nea(COAL_ROWS, 4122, 40, CO2_COAL), capacity_factor=0.85, l_prod=[0, 100e3]),
    'ccgt': dict(lazard((1450, 2100), (10.00, 25.50), (2.75, 5.00), (6475, 6550)),
                 capacity_factor=0.85, l_prod=[0, 100e3]),
    'ocgt': dict(lazard((1100, 1650), (10.00, 17.00), (3.50, 5.00), (10275, 11175)),
                 capacity_factor=0.85, l_prod=[0, 100e3]),
    'solr': dict(fix_cost_prod=irena(683e3, 0.02, 20), var_cost_prod=0.0, var_emis_prod=0.0,
                 l_prod=[0, 3000.0]),
    'wind': dict(fix_cost_prod=irena(1034e3, 0.03, 25), var_cost_prod=0.0, var_emis_prod=0.0,
                 l_prod=[0, 1000.0]),
}
BATTERY = dict(fix_cost_strg=irena(171e3, 0.025, 15), hours_of_storage=4, round_trip_efficiency=0.85,
               l_strg=[0, 5000.0])

# Cogeneration conditions used when a unit supplies heat to MED: turbine inlet
# temperature (C) and pressure (bar), condenser pressure (bar) -- the values of
# the legacy MED dataset.
COGEN = {'nucl': [290, 70], 'coal': [564, 152], 'ccgt': [564, 152]}

# --- Power-to-X processes -------------------------------------------------------
# RO and MED on one basis: World Bank (2019), The Role of Desalination in an
# Increasingly Water-Scarce World, Table 5.1, capital cost net of financing, as
# derived in the 2021 island study's cost evidence:
#   RO   1,170-1,230 USD/(m3/day): midpoint 1,200
#   MED  1,410-1,460 USD/(m3/day): midpoint 1,435
#   life 25 years for both -- ASSUMPTION; the study gives none
# RO non-energy O&M (the 2021 island study): fixed 75 USD/(m3/day)/yr, variable
# 0.092 USD/m3. MED non-energy O&M keeps RO's ratio to capital cost, i.e. both
# RO figures scaled by 1,435 / 1,200 (a stated convention, not an MED source).
#   RO energy 3.5 kWh/m3. MED energy 1.5 kWh/m3 electricity + 50 kWh/m3 heat,
#   extracted at 80 C (legacy MED dataset; within published MED ranges).
# Water storage: 2.50 USD/m3 over 20 years (flagged unsourced in the study),
# max 50 million m3 -- for RO; MED keeps its legacy storage cost.
RO_CAPEX, MED_CAPEX = 1200.0, 1435.0          # USD/(m3/day)
RO_FOM, RO_VOM = 75.0, 0.092                  # USD/(m3/day)/yr, USD/m3
DESAL_LIFE = 25
RO_FIX = RO_CAPEX * 24 * crf(DISCOUNT, DESAL_LIFE) + RO_FOM * 24
MED_FIX = MED_CAPEX * 24 * crf(DISCOUNT, DESAL_LIFE) + RO_FOM * (MED_CAPEX / RO_CAPEX) * 24
MED_VOM = RO_VOM * MED_CAPEX / RO_CAPEX
RO_STORE_FIX = 2.50 * crf(DISCOUNT, 20)

# Hydrogen: World Bank / ESMAP (2026), Electrolyzers for Hydrogen Production:
# Technical and Economic Characteristics, Table ES1, alkaline (ALK) at scale,
# midpoints of its global ranges:
#   installed capital    500-1,500 USD/kW          -> 1,000 USD/kW (electrical input)
#   non-electricity OPEX 2-3% of capital per year  -> 2.5% (includes stack replacement)
#   electricity use      51-56 kWh/kg H2 (AC)      -> 53.5 kWh/kg
#   project life         25 years (the report's LCOH basis)
# Per kg/h of hydrogen capacity: 1,000 USD/kW x 53.5 kW = 53,500 USD.
# The report gives no hydrogen storage cost; the store keeps its legacy value.
H2_KWH_KG = 53.5
H2_CAPEX = 1000.0 * H2_KWH_KG                  # USD per (kg/h)
H2_FIX = H2_CAPEX * crf(DISCOUNT, 25) + 0.025 * H2_CAPEX

# Product volumes. Water: the package's 50,229,696 m3/year, for RO and MED
# alike so that the two are compared on the same service. Hydrogen: the legacy
# case's 35,000 t/year was 3.5% of its 50 TWh grid's electricity (at 0.05
# MWh/kg); the same share of 5.69 TWh is 3,983 t/year. (Kept as a volume when
# the electricity use changed to 53.5 kWh/kg.)
WATER_M3 = 50229696.0
H2_KG = 35e6 * E_TOTAL / 50e6

PROCESSES = {
    'power-to-hydrogen': ('hydrogen', H2_KG, {
        'iden': 'p2x-h2', 'profile': '', 'capacity_factor': 0.85, 'type': 'elec', 'temperature': 0,
        'supply_sources': [], 'fix_cost_strg': 49.2, 'l_strg': [0, 2190e6], 'c_strg': -1,
        'fix_cost_prod': H2_FIX, 'var_cost_prod': 0, 'pow_use_elec_prod': H2_KWH_KG / 1000,
        'pow_use_ther_prod': 0,
        'l_prod': [0, 1e6], 'c_prod': -1, 'soc_ini': 0.5}),
    'power-to-water-ro': ('water', WATER_M3, {
        'iden': 'p2x-ro', 'profile': '', 'capacity_factor': 0.85, 'type': 'elec', 'temperature': 0,
        'supply_sources': [], 'fix_cost_strg': RO_STORE_FIX, 'l_strg': [0, 50e6], 'c_strg': -1,
        'fix_cost_prod': RO_FIX, 'var_cost_prod': RO_VOM, 'pow_use_elec_prod': 0.0035,
        'pow_use_ther_prod': 0, 'l_prod': [0, 1e6], 'c_prod': -1, 'soc_ini': 0.5}),
    'power-to-water-med': ('water', WATER_M3, {
        'iden': 'p2x-med', 'profile': '', 'capacity_factor': 0.85, 'type': 'elec + ther', 'temperature': 80,
        'supply_sources': ['nucl', 'coal', 'ccgt'], 'fix_cost_strg': 0.22, 'l_strg': [0, 2190e6],
        'c_strg': -1, 'fix_cost_prod': MED_FIX, 'var_cost_prod': MED_VOM, 'pow_use_elec_prod': 0.0015,
        'pow_use_ther_prod': 0.05, 'l_prod': [0, 1e6], 'c_prod': -1, 'soc_ini': 1.0}),
}


def profile_mean(name):
    return float(np.loadtxt(os.path.join(ROOT, BASE, name)).mean())


def build(variant):
    """The input for one dataset; variant None is the base."""
    directory = 'elec-grid' if variant is None else 'elec-grid+' + variant
    path = lambda f: f            # relative to the input file's own directory
    thermal = set(PROCESSES[variant][2]['supply_sources']) if variant else set()

    # Keep example inputs readable: whole-dollar plant/battery fixed costs,
    # cents for generator variable costs and product storage, three decimals
    # for product variable costs and profile factors, whole kg/MWh emissions.
    # Energy-use coefficients retain their meaningful small values.
    generators = []
    for iden, p in GEN.items():
        g = {'iden': iden, 'profile': '', 'capacity_factor': p.get('capacity_factor'),
             'type': 'elec + ther' if iden in thermal else 'elec',
             'fix_cost_prod': round(float(p['fix_cost_prod'])),
             'var_cost_prod': round(float(p['var_cost_prod']), 2),
             'var_emis_prod': round(float(p['var_emis_prod'])),
             'l_prod': p['l_prod'], 'c_prod': -1, 'e_prod': [], 'h_prod': [],
             'turbine_t_p': COGEN[iden] if iden in thermal else [],
             'condenser_p': 0.05 if iden in thermal else 0, 'a': 0, 'b': 0}
        if iden in ('solr', 'wind'):
            # Round the annual availability assumption; IESO rescales the profile.
            g['profile'] = path(iden + '.csv')
            g['capacity_factor'] = round(profile_mean(iden + '.csv'), 3)
        generators.append(g)

    x_demands = []
    p2x = []
    if variant:
        product, total, process = PROCESSES[variant]
        process = dict(process)
        process['fix_cost_prod'] = round(process['fix_cost_prod'])
        process['fix_cost_strg'] = round(process['fix_cost_strg'], 2)
        process['var_cost_prod'] = round(process['var_cost_prod'], 3)
        p2x.append(dict(process, x_strg=[], x_prod=[], x_supp=[], shadow_prices={'demand_match': []}))
    for name in ('heat', 'hydrogen', 'water'):
        active = variant is not None and PROCESSES[variant][0] == name
        x_demands.append({
            'iden': name, 'profile': '', 'total': float(PROCESSES[variant][1]) if active else 0,
            'supply_sources': [PROCESSES[variant][2]['iden']] if active else [],
            'var_cost_ns': 1000 if active else 0, 'l_ns': [0, 1e9] if active else [],
            'output_ns': [], 'shadow_prices': {'demand_match': []}, 'kpis': {'cost': -1, 'emis': -1, 'reli': -1}})

    return directory, {
        'demand': {
            'e': {'iden': 'electricity', 'profile': path('dmnd.csv'), 'total': E_TOTAL, 'supply_sources': [],
                  'var_cost_ns': 20000, 'l_ns': [0, 1e6], 'output_ns': [],
                  'shadow_prices': {'demand_match': [], 'carbon_cap': -1, 'reliability_cap': -1},
                  'kpis': {'cost': -1, 'emis': -1, 'reli': -1}},
            'x': x_demands,
        },
        'p2x': p2x,
        'generator': generators,
        'flex': [dict({'iden': 'bstr', 'c_strg': -1, 'e_strg': [], 'soc_ini': 0.5, 'soc_min': 0, 'soc_max': 1,
                       'e_char': [], 'e_disc': []}, **dict(BATTERY, fix_cost_strg=round(BATTERY['fix_cost_strg'])))],
        'solver': {'stat_succ': -1, 'stat_time': 0, 'stat_capa': 0, 'stat_outp': 0, 'stat_cons': 0},
    }


def main():
    os.chdir(ROOT)
    for name in PROFILES:
        if not os.path.isfile(os.path.join(BASE, name)):
            sys.exit('missing canonical profile ' + os.path.join(BASE, name))
    for variant in [None] + list(PROCESSES):
        directory, doc = build(variant)
        target = os.path.join('datasets', directory)
        os.makedirs(target, exist_ok=True)
        if variant is not None:
            for name in PROFILES:
                shutil.copyfile(os.path.join(BASE, name), os.path.join(target, name))
        out = os.path.join(target, directory + '.json')
        with open(out, 'w') as f:
            json.dump(doc, f, indent=4)
            f.write('\n')
        digest = hashlib.sha256(open(out, 'rb').read()).hexdigest()[:16]
        print(f'{out}  sha256 {digest}')


if __name__ == '__main__':
    main()
