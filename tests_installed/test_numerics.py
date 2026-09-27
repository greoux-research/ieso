"""Numerical acceptance on the installed artifact, under the Step 1 contract.

The synthetic examples are solved at the model's own horizon (8760 hours) and
compared with examples/expected.json, recorded in the reference environment:

* status optimal, every accounting check passed, identical problem size;
* objective within a relative 1e-10;
* every optimised capacity within 1e-6 + 1e-7 x |reference|;
* emissions within a relative 1e-9 where the carbon cap binds;
* cogeneration coefficients within one unit in the 6th significant digit
  (the executable prints six significant digits; another build may round the
  last one the other way);
* the independent invariant checker passes.

Hourly dispatch is not compared: equally optimal solutions may differ in it
from one platform or solver build to another.

The thermodynamics executable is checked against the fixture recorded from the
reference build (tests/fixtures/thermo_reference.json): coefficients within
one unit in the 6th significant digit, limits within 1e-9, refusals as recorded.
"""

import json
import math
import os
import subprocess
import sys

import pytest

from ies_optimiser import fcn

from conftest import FIXTURE


def expected_scenarios():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(os.path.dirname(here), 'examples', 'expected.json'), encoding='utf-8') as f:
        return json.load(f)['scenarios']


SCENARIOS = expected_scenarios()


def one_unit_in_6th_digit(x):
    return 10.0 ** (math.floor(math.log10(abs(x))) - 5)


@pytest.mark.parametrize('sc', SCENARIOS, ids=[s['name'] for s in SCENARIOS])
def test_scenario_meets_the_contract(solved, sc):
    result = solved[sc['name']]
    doc = result.document
    assert result.status == sc['status'] == 'optimal'
    assert result.accounting_ok is True and sc['accounting_ok'] is True
    assert {k: doc['solver'][k] for k in sc['problem_size']} == sc['problem_size']
    assert abs(result.objective - sc['objective']) <= 1e-10 * abs(sc['objective']), \
        (result.objective, sc['objective'])
    got = {}
    for g in doc['generator']:
        got['generator/' + g['iden'] + '/c_prod'] = g['c_prod']
    for f in doc['flex']:
        got['flex/' + f['iden'] + '/c_strg'] = f['c_strg']
    for p in doc['p2x']:
        got['p2x/' + p['iden'] + '/c_prod'] = p['c_prod']
        got['p2x/' + p['iden'] + '/c_strg'] = p['c_strg']
    assert set(got) == set(sc['capacities'])
    for key, ref in sc['capacities'].items():
        assert abs(got[key] - ref) <= 1e-6 + 1e-7 * abs(ref), (key, got[key], ref)
    if sc['carbon_cap_binding']:
        assert abs(doc['system']['emis'] - sc['emissions']) <= 1e-9 * abs(sc['emissions'])
    for gen, (a, b) in sc['cogeneration'].items():
        g = next(x for x in doc['generator'] if x['iden'] == gen)
        assert abs(g['a'] - a) <= one_unit_in_6th_digit(a) and abs(g['b'] - b) <= one_unit_in_6th_digit(b)


@pytest.mark.parametrize('sc', SCENARIOS, ids=[s['name'] for s in SCENARIOS])
def test_independent_invariants_hold(solved, sc, invariants, tmp_path):
    path = tmp_path / (sc['name'] + '.ies-optimiser.json')
    path.write_text(json.dumps(solved[sc['name']].document), encoding='utf-8')
    fails, notes, cost, emis = invariants.check(str(path))
    assert fails == [], fails


# --- the thermodynamics executable -----------------------------------------------------------

with open(FIXTURE, encoding='utf-8') as _f:
    REFERENCE = json.load(_f)
PLANTS = REFERENCE['plants']
ACCEPTED = [(n, c) for n, p in PLANTS.items() for c in p['accepted']]
REFUSED = [(n, c) for n, p in PLANTS.items() for c in p['refused']]


def run(*args):
    out = subprocess.run([fcn.Thermo_bin] + [str(a) for a in args], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, timeout=30)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def conditions(name):
    p = PLANTS[name]
    return p['turbine_inlet_c'], p['turbine_inlet_bar'], p['condenser_bar']


@pytest.mark.parametrize('name, case', ACCEPTED, ids=[f"{n}-{c['label']}" for n, c in ACCEPTED])
def test_coefficients_match_the_reference_fixture(name, case):
    code, out, _ = run(*conditions(name), repr(case['extraction_c']))
    assert code == 0
    got, ref = out.split(), case['stdout'].split()
    assert len(got) == 2
    for g, r in zip(got, ref):
        assert abs(float(g) - float(r)) <= one_unit_in_6th_digit(float(r)), (got, ref)


@pytest.mark.parametrize('name', PLANTS)
def test_domain_limits_match(name):
    code, out, _ = run('--limits', *conditions(name))
    assert code == 0
    for g, r in zip(out.split(), PLANTS[name]['limits_stdout'].split()):
        assert abs(float(g) - float(r)) <= 1e-9


@pytest.mark.parametrize('name, case', REFUSED, ids=[f"{n}-{c['label']}" for n, c in REFUSED])
def test_refusals_on_and_outside_the_domain(name, case):
    code, out, err = run(*conditions(name), case['extraction_c'])
    assert code == case['exit_status'] and out == '' and case['stderr_contains'] in err


def test_python_uses_the_emitted_precision_unchanged():
    a, b, err = fcn.thermo(290, 70, 0.05, 80)
    code, out, _ = run(290, 70, 0.05, 80)
    assert err is False and code == 0
    assert (a, b) == tuple(float(x) for x in out.split())


@pytest.mark.skipif(sys.platform == 'win32', reason='uses a POSIX shell script as the slow executable')
def test_the_timeout_is_enforced(tmp_path):
    slow = tmp_path / 'slow'
    slow.write_text('#!/bin/sh\nexec /bin/sleep 5\n')
    slow.chmod(0o755)
    a, b, err = fcn.thermo(290, 70, 0.05, 80, binary=str(slow), timeout=0.5)
    assert (a, b) == (-1, -1) and 'timed out' in err
