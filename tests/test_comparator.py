"""Mutation tests for tools/compare_outputs.py.

Each test takes a genuinely solved result, corrupts one thing -- a value, a
field, an entity, a type -- and requires the comparator to notice. A comparator
that reports agreement on anything it did not check certifies nothing; before
this suite, setting system.cost or accounts.resource_cost to 1e99 returned
IDENTICAL with exit 0.
"""

import copy
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import solved_document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPARE = os.path.join(ROOT, 'tools', 'compare_outputs.py')


@pytest.fixture(scope='module')
def doc():
    return solved_document()


TOKEN = re.compile(r'([^.\[\]]+)(?:\[([^\]]+)\])?')


def locate(d, path):
    """Resolve 'generator[chp].h_prod' or 'demand.e.surplus[0]'; return (parent, key)."""
    parts = TOKEN.findall(path)
    node = d
    for n, (name, sel) in enumerate(parts):
        last = n == len(parts) - 1
        if sel == '':
            if last:
                return node, name
            node = node[name]
        elif sel.isdigit() or sel.lstrip('-').isdigit():
            if last:
                return node[name], int(sel)
            node = node[name][int(sel)]
        else:
            match = [e for e in node[name] if e.get('iden') == sel]
            if last:
                raise ValueError('an entity selector cannot be last')
            node = match[0]
    raise ValueError(path)


def write(tmp_path, name, d):
    p = tmp_path / name
    p.write_text(json.dumps(d))
    return str(p)


def compare(a, b, *flags):
    out = subprocess.run([sys.executable, COMPARE, a, b] + list(flags),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return out.returncode, out.stdout


def mutated(doc, path, value):
    d = copy.deepcopy(doc)
    parent, key = locate(d, path)
    if value is DELETE:
        del parent[key]
    elif callable(value):
        parent[key] = value(parent[key])
    else:
        parent[key] = value
    return d


DELETE = object()

CHANGES = [
    ('system.cost', 1e99),
    ('demand.e.accounts.resource_cost', 1e99),
    ('demand.x[water].accounts.allocation_share', lambda v: v * 1.01),
    ('demand.e.kpis.reli', lambda v: v - 0.01),
    ('generator[chp].availability.profile_peak', 42.0),
    ('p2x[med].availability.capacity_factor_effective', lambda v: v * 0.5),
    ('p2x[med].shadow_prices.demand_match[1]', lambda v: v + 1.0),
    ('p2x[med].heat_surplus[0]', lambda v: v + 1.0),
    ('demand.e.shadow_prices.demand_match[2]', lambda v: v + 1.0),
    ('demand.e.shadow_prices.carbon_cap', lambda v: v + 1.0),
    ('demand.e.shadow_prices.carbon_cap_detail.slack', lambda v: v + 1.0),
    ('demand.e.shadow_prices.reliability_cap_detail.binding', lambda v: not v),
    ('demand.e.surplus[0]', lambda v: v + 1.0),
    ('system.surplus.electricity', lambda v: v + 1.0),
    ('system.surplus.spill', lambda v: v + 1.0),
    ('system.unallocated.cost', lambda v: v + 1.0),
    ('system.allocated.emis', lambda v: v + 1.0),
    ('system.checks.cost_reconciliation.ok', lambda v: not v),
    ('system.accounting_ok', lambda v: not v),
    ('flex[dam].e_spil[2]', lambda v: v + 1.0),
    ('flex[bstr].c_strg', lambda v: v + 1.0),
    ('generator[chp].h_prod[3]', lambda v: v + 1.0),
    ('generator[chp].a', 0.8),
    ('p2x[med].x_strg[0]', lambda v: v + 1.0),
    ('demand.x[water].output_ns[0]', lambda v: v + 1.0),
    ('solver.stat_cons', lambda v: v + 1),
    ('generator[gas].c_prod', 'fifty'),                  # wrong type
    ('generator[gas].e_prod', lambda v: v + [0.0]),        # wrong length
    ('demand.e.kpis', lambda v: [v]),                     # wrong structure
]


@pytest.mark.parametrize('path, value', CHANGES, ids=[c[0] for c in CHANGES])
def test_a_changed_field_is_caught(tmp_path, doc, path, value):
    code, out = compare(write(tmp_path, 'a.json', mutated(doc, path, value)),
                        write(tmp_path, 'b.json', doc))
    assert code == 1, out
    assert 'DIFFERENCES' in out


REMOVALS = [
    'system', 'system.unallocated', 'demand.e.accounts', 'demand.e.surplus',
    'generator[chp].availability', 'p2x[med].availability', 'p2x[med].heat_surplus',
    'demand.e.shadow_prices.carbon_cap_detail', 'solver.stat_status', 'provenance',
]


@pytest.mark.parametrize('path', REMOVALS)
def test_a_field_removed_from_one_side_is_caught(tmp_path, doc, path):
    code, out = compare(write(tmp_path, 'a.json', mutated(doc, path, DELETE)),
                        write(tmp_path, 'b.json', doc))
    assert code == 1, out


@pytest.mark.parametrize('path', [
    'generator[chp].h_prod',          # required on a thermal unit
    'flex[dam].e_spil',               # required on an inflow-fed store
    'demand.e.accounts',
    'system',
    'p2x[med].shadow_prices',
])
def test_a_required_field_missing_from_both_is_caught(tmp_path, doc, path):
    """Agreement between two files that both lack a required field is not
    agreement on anything."""
    d = mutated(doc, path, DELETE)
    code, out = compare(write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', d))
    assert code == 1, out
    assert 'missing' in out


def test_required_heat_series_emptied_in_both_is_caught(tmp_path, doc):
    d = mutated(doc, 'generator[chp].h_prod', [])
    code, out = compare(write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', d))
    assert code == 1 and 'h_prod' in out


def test_non_finite_values_anywhere_are_caught(tmp_path, doc):
    d = mutated(doc, 'system.unallocated.cost', float('nan'))
    code, out = compare(write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', d))
    assert code == 1 and 'non-finite' in out


@pytest.mark.parametrize('section', ['generator', 'flex', 'p2x', 'demand.x'])
def test_duplicate_identifiers_are_caught_before_matching(tmp_path, doc, section):
    """Keying entities by identifier let a later duplicate hide an earlier,
    corrupted entry. The duplicate is now reported whichever side it is on."""
    d = copy.deepcopy(doc)
    parent, key = locate(d, section)
    items = parent[key]
    items.insert(0, copy.deepcopy(items[-1]))
    code, out = compare(write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', d))
    assert code == 1
    assert 'duplicate' in out


def test_one_large_value_does_not_hide_an_error_elsewhere(tmp_path, doc):
    """The tolerance is per element. It used to scale with the largest value in
    the series, so a 1e9 entry excused a 0.5 error in a 1.0 entry."""
    d = copy.deepcopy(doc)
    d['demand']['e']['shadow_prices']['demand_match'][0] = 1e9
    e = copy.deepcopy(d)
    e['demand']['e']['shadow_prices']['demand_match'][1] += 0.5
    code, out = compare(write(tmp_path, 'a.json', e), write(tmp_path, 'b.json', d))
    assert code == 1, out


def test_an_unexpected_field_is_caught(tmp_path, doc):
    d = copy.deepcopy(doc)
    d['generator'][0]['extra'] = 1.0
    code, out = compare(write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', doc))
    assert code == 1 and 'extra' in out


def test_duplicate_json_keys_are_an_error(tmp_path, doc):
    text = json.dumps(doc)
    bad = text.replace('"system": {', '"system": {"cost": 0, ', 1)
    p = tmp_path / 'dup.json'
    p.write_text(bad)
    code, out = compare(str(p), write(tmp_path, 'b.json', doc))
    assert code == 2 and 'duplicate key' in out


# --- explicit exclusions ------------------------------------------------------

def test_identical_results_agree_and_exclusions_are_listed(tmp_path, doc):
    d = copy.deepcopy(doc)
    d['solver']['stat_time'] = 99.0
    d['provenance']['run_utc'] = '1999-01-01T00:00:00Z'
    code, out = compare(write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', doc))
    assert code == 0, out
    assert 'IDENTICAL' in out
    assert 'solver.stat_time' in out and 'provenance' in out     # stated, not silent


def test_provenance_is_compared_on_request(tmp_path, doc):
    d = mutated(doc, 'provenance.source_sha256', '0' * 64)
    a, b = write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', doc)
    assert compare(a, b)[0] == 0
    code, out = compare(a, b, '--provenance')
    assert code == 1 and 'source_sha256' in out


# --- legacy baselines -----------------------------------------------------------

def legacy(doc):
    """What a pre-correction result looks like: no system, accounts,
    availability, surplus or provenance, and the [-1, -1] placeholder."""
    d = copy.deepcopy(doc)
    for k in ('system', 'provenance'):
        d.pop(k)
    for dm in [d['demand']['e']] + d['demand']['x']:
        dm.pop('accounts', None)
        dm.pop('surplus', None)
    for g in d['generator']:
        g.pop('availability')
    for p in d['p2x']:
        p.pop('availability')
        p.pop('heat_surplus')
    for k in ('carbon_cap_detail', 'reliability_cap_detail'):
        d['demand']['e']['shadow_prices'].pop(k)
    return d


def test_strict_mode_refuses_a_legacy_baseline(tmp_path, doc):
    code, out = compare(write(tmp_path, 'a.json', doc), write(tmp_path, 'b.json', legacy(doc)))
    assert code == 1


def test_legacy_mode_compares_what_both_carry_and_lists_the_rest(tmp_path, doc):
    code, out = compare(write(tmp_path, 'a.json', doc), write(tmp_path, 'b.json', legacy(doc)),
                        '--legacy')
    assert code == 0, out
    assert 'NOT COMPARED' in out
    for field in ('system', 'accounts', 'availability', 'heat_surplus'):
        assert field in out


def test_legacy_mode_still_catches_a_difference(tmp_path, doc):
    old = legacy(doc)
    old['generator'][0]['c_prod'] += 1.0
    code, out = compare(write(tmp_path, 'a.json', doc), write(tmp_path, 'b.json', old), '--legacy')
    assert code == 1 and 'c_prod' in out


def test_legacy_mode_does_not_excuse_a_field_missing_from_the_new_result(tmp_path, doc):
    new = mutated(doc, 'demand.e.accounts', DELETE)
    code, out = compare(write(tmp_path, 'a.json', new),
                        write(tmp_path, 'b.json', legacy(doc)), '--legacy')
    assert code == 1


# --- the same corruption on both sides ------------------------------------------
#
# A regression that drops or corrupts a field in every newly generated result
# produces two files that agree with each other. Recursive comparison cannot see
# that; each file must be checked on its own for what a result has to contain.

BOTH = [
    ('demand.e.accounts', {}),
    ('demand.e.accounts.resource_cost', DELETE),
    ('demand.x[water].accounts.served_demand', 'lots'),
    ('system.unallocated.cost', DELETE),
    ('system.allocated.share', DELETE),
    ('system.checks', {}),
    ('system.checks.cost_reconciliation', DELETE),
    ('system.checks.cost_reconciliation.ok', DELETE),
    ('system.surplus.spill', None),
    ('system.accounting_ok', 'yes'),
    ('provenance', {}),
    ('provenance.source_sha256', 'not-a-digest'),
    ('provenance.hours', DELETE),
    ('generator[gas].e_prod', lambda v: ['x'] * len(v)),
    ('generator[gas].e_prod', lambda v: [[x] for x in v]),
    ('generator[gas].e_prod', lambda v: [None] * len(v)),
    ('generator[chp].h_prod', lambda v: [True] * len(v)),
    ('flex[dam].e_spil', lambda v: v[:-1] + ['1.0']),
    ('p2x[med].x_supp', lambda v: [{'x': 1}] * len(v)),
    ('demand.e.output_ns', lambda v: [[0.0, 0.0]] * len(v)),
    ('demand.e.shadow_prices.demand_match', lambda v: ['1'] * len(v)),
    ('demand.e.shadow_prices.demand_marginal', DELETE),
    ('demand.e.kpis.reli', 'high'),
    ('demand.e.shadow_prices.carbon_cap_detail', {}),
    ('generator[chp].availability', {}),
    ('p2x[med].availability.profile_peak', DELETE),
    ('solver.stat_cons', 'many'),
    ('generator[gas].c_prod', None),
]


@pytest.mark.parametrize('path, value', BOTH, ids=[f'{p}={v!r}'[:60] if not callable(v) else p + '(fn)'
                                                  for p, v in BOTH])
def test_the_same_corruption_on_both_sides_is_caught(tmp_path, doc, path, value):
    d = mutated(doc, path, value)
    a, b = write(tmp_path, 'a.json', d), write(tmp_path, 'b.json', d)
    code, out = compare(a, b)
    assert code == 1, out
    assert 'IDENTICAL' not in out
