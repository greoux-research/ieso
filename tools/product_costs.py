#!/usr/bin/env python3
"""Direct production cost of each Power-to-X product in an IES Optimiser result.

    tools/product_costs.py RESULT.ies-optimiser.json [RESULT ...]

IES Optimiser's product cost KPI (demand.x[*].kpis.cost) is an ALLOCATION: the whole
system cost -- generation, storage and the processes' own plant -- is pooled
and divided among all demands in proportion to electricity-equivalent use. It
is not the cost of making the product, and it should not be compared with
published production costs.

This tool costs each product directly, from the result alone:

    plant        c_prod x fix_cost_prod + c_strg x fix_cost_strg
                 + var_cost_prod x annual production
    electricity  sum over hours of (process electricity use x demand_marginal)
    heat         sum over hours of (heat supplied x a x demand_marginal), i.e.
                 heat valued at the electricity its extraction displaces

divided by the annual demand for the product. Energy inputs are valued at the
hourly marginal value of electricity (shadow_prices.demand_marginal), which is
a convention: marginal values are not average costs, and at breakpoints a dual
is one valid value among several. The result is a production cost under that
convention, not a tariff.
"""

import json
import sys

import numpy as np


def product_costs(doc):
    price = np.asarray(doc['demand']['e']['shadow_prices']['demand_marginal'], float)
    generators = {g['iden']: g for g in doc['generator']}
    rows = []
    for d in doc['demand']['x']:
        if not d['total'] > 0:
            continue
        plant = electricity = heat = 0.0
        for name in d['supply_sources']:
            p = next(x for x in doc['p2x'] if x['iden'] == name)
            x = np.asarray(p['x_prod'], float)
            plant += p['c_prod'] * p['fix_cost_prod'] + p['c_strg'] * p['fix_cost_strg'] \
                + p['var_cost_prod'] * x.sum()
            electricity += float((x * p['pow_use_elec_prod'] * price).sum())
            if p['type'] == 'elec + ther':
                for g in p['supply_sources']:
                    h = np.asarray(generators[g]['h_prod'], float)
                    heat += float((h * generators[g]['a'] * price).sum())
        v = d['total']
        rows.append({'product': d['iden'], 'plant': plant / v, 'electricity': electricity / v,
                     'heat': heat / v, 'direct': (plant + electricity + heat) / v,
                     'allocation_kpi': d['kpis']['cost']})
    return rows


def main(paths):
    for path in paths:
        with open(path) as f:
            doc = json.load(f)
        for r in product_costs(doc):
            print(f"{path}  {r['product']}: plant {r['plant']:.3f} + electricity {r['electricity']:.3f}"
                  f" + heat {r['heat']:.3f} = {r['direct']:.3f} per unit"
                  f"  (allocation KPI {r['allocation_kpi']:.3f})")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
