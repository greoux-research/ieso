#!/usr/bin/env python3
"""Write the synthetic distribution examples in examples/.

    python tools/build_examples.py                    # (re)write the cases and profiles
    python tools/build_examples.py --check            # exit 1 if a file differs
    python tools/build_examples.py --record-expected  # solve them; write examples/expected.json

The examples are synthetic: every profile is a closed-form expression written
below, and every cost is a round illustrative number. Nothing is taken from the
datasets in datasets/ (whose profiles are licensed CC BY-NC 4.0) or from any
other source, so the examples are covered by the repository's MIT licence.

They use the model's own horizon (8760 hours) and conventions, in the
canonical input format. The installed-artifact tests (tests/installed) solve
them on every supported platform and compare with examples/expected.json,
which --record-expected writes from the reference environment: it needs IES Optimiser
installed (pip install -e . or a wheel) and records the versions it ran with.
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, 'examples')
HOURS = 8760

# Scenarios the tests solve: (name, case directory, options).
SCENARIOS = [
    ('electricity-storage', 'electricity-storage', {}),
    ('electricity-storage-carbon-cap', 'electricity-storage', {'carbon-constraint': 150.0}),
    ('power-to-x-thermal', 'power-to-x-thermal', {}),
]


# --- profiles (closed form) --------------------------------------------------------

def demand(h):
    """Electricity demand shape: a daily cycle and a winter peak, never zero."""
    day, hour = h // 24, h % 24
    daily = 1.0 + 0.25 * math.sin(2 * math.pi * (hour - 8) / 24) + 0.10 * math.sin(4 * math.pi * (hour - 3) / 24)
    season = 1.0 + 0.15 * math.cos(2 * math.pi * day / 365)
    return daily * season


def solar(h):
    """Solar availability shape: a half sine between 06:00 and 18:00, stronger in summer."""
    day, hour = h // 24, h % 24
    if not 6 <= hour < 18:
        return 0.0
    return math.sin(math.pi * (hour - 6 + 0.5) / 12) * (0.75 - 0.25 * math.cos(2 * math.pi * (day - 10) / 365))


def csv(values):
    return ''.join('%.6f\n' % v for v in values)


# --- cases ---------------------------------------------------------------------------

def electricity_demand(total, profile='demand.csv'):
    return {'iden': 'electricity', 'profile': profile, 'total': total, 'var_cost_ns': 10000, 'l_ns': [0, 1e6]}


def gen(iden, fix, var, emis, cf=0.9, profile='', kind='elec', high=1e4, **extra):
    g = {'iden': iden, 'type': kind, 'profile': profile, 'capacity_factor': cf, 'fix_cost_prod': fix,
         'var_cost_prod': var, 'var_emis_prod': emis, 'l_prod': [0, high], 'c_prod': -1}
    g.update(extra)
    return g


def electricity_storage():
    return {
        'format_version': 1,
        'demand': {'e': electricity_demand(1.0e6), 'x': []},
        'generator': [
            gen('solar', fix=60000, var=0, emis=0, cf=0.22, profile='solar.csv'),
            gen('ccgt', fix=100000, var=60, emis=370),
            gen('ocgt', fix=50000, var=110, emis=550, cf=0.95),
        ],
        'flex': [{'iden': 'battery', 'fix_cost_strg': 25000, 'hours_of_storage': 4, 'round_trip_efficiency': 0.85,
                  'l_strg': [0, 1e5], 'c_strg': -1, 'soc_ini': 0.5}],
        'p2x': [],
    }


def power_to_x_thermal():
    return {
        'format_version': 1,
        'demand': {'e': electricity_demand(0.5e6),
                   'x': [{'iden': 'water', 'total': 1.0e7, 'supply_sources': ['med'], 'var_cost_ns': 50,
                          'l_ns': [0, 1e6]}]},
        'generator': [
            gen('nuclear', fix=400000, var=12, emis=0, kind='elec + ther', turbine_t_p=[290, 70], condenser_p=0.05),
            gen('ccgt', fix=100000, var=60, emis=370),
            gen('solar', fix=60000, var=0, emis=0, cf=0.22, profile='solar.csv'),
        ],
        'flex': [],
        'p2x': [{'iden': 'med', 'type': 'elec + ther', 'temperature': 80, 'supply_sources': ['nuclear'],
                 'capacity_factor': 0.9, 'fix_cost_prod': 5000, 'var_cost_prod': 0.1,
                 'pow_use_elec_prod': 0.0015, 'pow_use_ther_prod': 0.05, 'l_prod': [0, 1e5], 'c_prod': -1,
                 'fix_cost_strg': 0.5, 'l_strg': [0, 1e7], 'c_strg': -1, 'soc_ini': 0.5}],
    }


README = """# Synthetic examples

Two small full-year IES Optimiser cases in the canonical input format, used by the
installed-artifact tests on every supported platform and as runnable examples:

- `electricity-storage/` -- solar, two gas units and a battery meeting an
  electricity demand (solved with and without a carbon cap in the tests);
- `power-to-x-thermal/` -- a cogeneration unit supplying heat to a
  multi-effect distillation process (thermally coupled Power-to-X), with
  electricity and water demands. Solving it runs the thermodynamics executable.

Everything here is synthetic: the profiles are closed-form expressions and the
costs round illustrative numbers, written by `tools/build_examples.py`. Nothing
is taken from the datasets in `datasets/` or any other source. The examples
are covered by the repository's MIT licence. They illustrate the model; they
describe no real system.

    ies-optimiser validate examples/power-to-x-thermal/case.json
    ies-optimiser examples/electricity-storage/case.json carbon-constraint=150

`expected.json` holds the reference results the tests compare against, with
the environment that produced them (`python tools/build_examples.py
--record-expected`).
"""


def files():
    hours = range(HOURS)
    out = {
        'README.md': README,
        'electricity-storage/case.json': json.dumps(electricity_storage(), indent=4) + '\n',
        'electricity-storage/demand.csv': csv(demand(h) for h in hours),
        'electricity-storage/solar.csv': csv(solar(h) for h in hours),
        'power-to-x-thermal/case.json': json.dumps(power_to_x_thermal(), indent=4) + '\n',
        'power-to-x-thermal/demand.csv': csv(demand(h) for h in hours),
        'power-to-x-thermal/solar.csv': csv(solar(h) for h in hours),
    }
    return out


def record_expected():
    import platform
    import ies_optimiser
    from importlib import metadata
    scenarios = []
    for name, folder, options in SCENARIOS:
        path = os.path.join(EXAMPLES, folder, 'case.json')
        result = ies_optimiser.solve(path, options=options)
        doc = result.document
        capacities = {}
        for g in doc['generator']:
            capacities['generator/' + g['iden'] + '/c_prod'] = g['c_prod']
        for f in doc['flex']:
            capacities['flex/' + f['iden'] + '/c_strg'] = f['c_strg']
        for p in doc['p2x']:
            capacities['p2x/' + p['iden'] + '/c_prod'] = p['c_prod']
            capacities['p2x/' + p['iden'] + '/c_strg'] = p['c_strg']
        cap = doc['demand']['e']['shadow_prices'].get('carbon_cap_detail')
        scenarios.append({
            'name': name, 'case': folder + '/case.json', 'options': options,
            'status': result.status, 'accounting_ok': result.accounting_ok, 'objective': result.objective,
            'system_cost': doc['system']['cost'], 'emissions': doc['system']['emis'],
            'carbon_cap_binding': None if cap is None else cap['binding'],
            'problem_size': {k: doc['solver'][k] for k in ('stat_capa', 'stat_outp', 'stat_cons')},
            'capacities': capacities,
            'cogeneration': {g['iden']: [g['a'], g['b']] for g in doc['generator'] if g['type'] == 'elec + ther'},
        })
    expected = {
        'recorded_with': {'ies_optimiser': ies_optimiser.__version__, 'python': platform.python_version(),
                          'platform': platform.platform(), 'numpy': metadata.version('numpy'),
                          'ortools': metadata.version('ortools'), 'pydantic': metadata.version('pydantic')},
        'contract': 'Step 1 cross-environment contract (docs/baseline-verification.md): optimal, accounting_ok, '
                    'identical problem size, objective rel 1e-10, capacities abs 1e-6 + rel 1e-7, emissions '
                    'rel 1e-9 where the carbon cap binds, cogeneration coefficients within one unit in the '
                    '6th significant digit.',
        'scenarios': scenarios,
    }
    with open(os.path.join(EXAMPLES, 'expected.json'), 'w', encoding='utf-8') as f:
        json.dump(expected, f, indent=2)
        f.write('\n')
    print('wrote examples/expected.json')


def main(argv):
    if argv == ['--record-expected']:
        record_expected()
        return 0
    check = argv == ['--check']
    if argv and not check:
        print(__doc__, file=sys.stderr)
        return 1
    stale = []
    for rel, text in files().items():
        path = os.path.join(EXAMPLES, *rel.split('/'))
        current = None
        if os.path.isfile(path):
            with open(path, encoding='utf-8', newline='') as f:
                current = f.read()
        if current == text:
            continue
        if check:
            stale.append(rel)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
            print('wrote examples/' + rel)
    if stale:
        print('out of date (run python tools/build_examples.py): ' + ', '.join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
