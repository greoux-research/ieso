"""Generated JSON Schemas (Step 4): reproducible, versioned, and in agreement
with the models and with real documents.

The schemas describe structure only; the tests below check both directions --
documents IES Optimiser accepts or writes validate against them, and representative
malformed documents do not.
"""

import copy
import json
import os
import subprocess
import sys

import jsonschema
import pytest

from ies_optimiser import api, schemas
from ies_optimiser import fcn as u
from ies_optimiser.results import Result
from conftest import demand_x, flex, generator, p2x, solved_document, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = 24


def checked_in(kind):
    with open(schemas.path(kind), encoding='utf-8') as f:
        return f.read()


def validator(kind):
    schema = json.loads(checked_in(kind))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def base():
    return system(generators=[generator('g', fix=1.0, var=10.0, emis=100.0)],
                  flexes=[flex('b', fix=1.0, rte=0.81, hours=2)],
                  p2xs=[p2x('p', elec_use=0.5, fix_prod=1.0, fix_strg=0.1)],
                  e_total=24.0, xs=[demand_x('water', 12.0, ['p'])])


# --- reproducibility --------------------------------------------------------------------

@pytest.mark.parametrize('kind', ['input', 'result'])
def test_checked_in_schemas_match_the_current_models(kind):
    assert checked_in(kind) == schemas.generate(kind), \
        'schemas/ is stale: run python tools/generate_schemas.py'


def test_the_generation_command_agrees():
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'generate_schemas.py'), '--check'],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.path.dirname(ROOT))
    assert out.returncode == 0, out.stdout


@pytest.mark.parametrize('kind, version', [('input', 1), ('result', 1)])
def test_schemas_are_versioned_and_say_they_are_structural(kind, version):
    schema = json.loads(checked_in(kind))
    assert schema['x-ies-optimiser-format'] == {'kind': kind, 'version': version}
    assert schema['$id'].endswith('ies-optimiser-' + kind + '-' + str(version) + '.schema.json')
    assert 'structure only' in schema['description']


def test_input_schema_carries_descriptions_units_defaults_and_examples():
    schema = json.loads(checked_in('input'))
    gen = schema['$defs']['Generator']['properties']
    assert 'USD per MW per year' in gen['fix_cost_prod']['description']
    assert gen['condenser_p']['default'] == 0.0
    assert gen['c_prod']['examples'] == [-1]
    assert schema['properties']['format_version'] == {'const': 1, 'description': schema['properties']
                                                      ['format_version']['description'], 'title': 'Format version'}
    assert schema['examples'] and schema['required'][0] == 'format_version'
    storage = schema['$defs']['Storage']
    assert storage['additionalProperties'] is False
    assert 'null' not in json.dumps(storage['properties']['inflow_profile'])      # absent, never null


# --- input documents ------------------------------------------------------------------------

def test_canonical_bundled_datasets_validate(tmp_path):
    v = validator('input')
    for name in ('elec-grid', 'elec-grid+power-to-water-med'):
        with open(os.path.join(ROOT, 'datasets', name, name + '.json')) as f:
            legacy = json.load(f)
        assert list(v.iter_errors(legacy))                      # unversioned: not this schema ...
        api.parse_case(legacy)                                  # ... but read by IES Optimiser's legacy adapter
        v.validate(api.to_canonical(legacy))
    v.validate(schemas.input_schema()['examples'][0])
    api.parse_case(schemas.input_schema()['examples'][0])      # the example is valid IES Optimiser input too


@pytest.mark.parametrize('mutate', [
    lambda d: d.update(format_version=2),
    lambda d: d['generator'][0].update(capacity_factor=1.5),
    lambda d: d['generator'][0].update(capacity_factor='0.5'),
    lambda d: d['generator'][0].update(c_prod=-2),
    lambda d: d['generator'][0].update(l_prod=[1]),
    lambda d: d['generator'][0].update(type='nuclear'),
    lambda d: d['generator'][0].update(e_prod=[]),
    lambda d: d['flex'][0].update(round_trip_efficiency=0),
    lambda d: d['flex'][0].update(inflow_profile=None),
    lambda d: d['demand']['e'].pop('l_ns'),
    lambda d: d.update(solver={}),
], ids=['version', 'range', 'string', 'capacity', 'pair', 'enum', 'output', 'rte', 'null',
        'required', 'solver'])
def test_malformed_inputs_fail_both_the_schema_and_ies_optimiser(mutate):
    doc = api.to_canonical(base())
    mutate(doc)
    assert list(validator('input').iter_errors(doc))
    with pytest.raises(Exception):
        api.parse_case(doc)


def test_the_schema_does_not_claim_the_semantic_rules():
    """Structure-only: a duplicate identifier passes the schema, not IES Optimiser."""
    doc = api.to_canonical(base())
    doc['flex'].append(copy.deepcopy(doc['flex'][0]))
    validator('input').validate(doc)
    report = api.validate(doc, config=u.RunConfig(hours=H))
    assert not report.valid and report.diagnostics[0].code == 'identifier.duplicate'


# --- result documents -------------------------------------------------------------------------

def test_an_optimal_result_validates(horizon):
    horizon(H)
    doc = api.solve(base(), config=u.RunConfig(hours=H)).document
    validator('result').validate(doc)
    Result.model_validate(doc)
    full = solved_document()                  # heat, inflow, caps, provenance: every optional block
    validator('result').validate(full)
    Result.model_validate(full)


def test_an_accounting_failure_is_still_a_complete_optimal_result(horizon):
    horizon(H)
    doc = api.solve(base(), config=u.RunConfig(hours=H)).document
    doc['system']['checks']['electricity_balance']['ok'] = False
    doc['system']['accounting_ok'] = False
    validator('result').validate(doc)


def test_an_unsuccessful_result_holds_no_results(horizon):
    horizon(4)
    s = system(generators=[generator('g', var=1.0, l_prod=(0, 0.5))], e_total=4.0,
               e_kwargs={'l_ns': (0, 0)})                       # cannot meet 1 MW with 0.5 MW, no shortfall
    result = api.solve(s, config=u.RunConfig(hours=4))
    assert not result.optimal and result.status == 'infeasible'
    doc = result.document
    assert 'system' not in doc and 'e_prod' not in doc['generator'][0] and 'kpis' not in doc['demand']['e']
    validator('result').validate(doc)
    Result.model_validate(doc)
    doc['system'] = {'cost': -1}                                   # a placeholder is not a result
    assert list(validator('result').iter_errors(doc))


def test_results_missing_what_they_must_hold_are_refused(horizon):
    horizon(H)
    doc = api.solve(base(), config=u.RunConfig(hours=H)).document
    v = validator('result')
    for mutate in (lambda d: d.pop('system'),
                   lambda d: d['generator'][0].pop('e_prod'),
                   lambda d: d['provenance'].pop('result_format_version'),
                   lambda d: d['generator'][0]['e_prod'].__setitem__(0, 'x'),
                   lambda d: d['solver'].update(stat_succ=0)):
        bad = copy.deepcopy(doc)
        mutate(bad)
        assert list(v.iter_errors(bad))
