"""The public input contract (Step 4): typed models, the legacy adapter,
structured diagnostics and the split between structure and semantics.

Structure is validated once, by ies_optimiser.models; semantics by
ies_optimiser.chk. Every refusal is an InputError whose diagnostics carry a
stable code, a JSON Pointer path, the entity and, where hourly, a zero-based
hour. These tests pin those codes and paths: they are the public contract.
"""

import copy
import glob
import json
import os

import numpy as np
import pytest

from ies_optimiser import api, formats
from ies_optimiser import fcn as u
from ies_optimiser.errors import InputError, ThermoError
from ies_optimiser.models import Case, Generator, SolveOptions, Storage
from conftest import demand_x, flex, generator, p2x, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS = sorted(glob.glob(os.path.join(ROOT, 'datasets', '*', '*.json')))
H = 24


def base():
    return system(generators=[generator('g', fix=1.0, var=10.0, emis=100.0)],
                  flexes=[flex('b', fix=1.0, rte=0.81, hours=2)],
                  p2xs=[p2x('p', elec_use=0.5, fix_prod=1.0, fix_strg=0.1)],
                  e_total=24.0, xs=[demand_x('water', 12.0, ['p'])])


def canonical():
    return api.to_canonical(base())


def refusal(case, **kwargs):
    with pytest.raises(InputError) as info:
        api.solve(case, config=kwargs.pop('config', u.RunConfig(hours=H)), **kwargs)
    return info.value


def only(error):
    assert len(error.diagnostics) == 1, [d.to_dict() for d in error.diagnostics]
    return error.diagnostics[0]


# --- legacy and canonical formats ------------------------------------------------------

@pytest.mark.parametrize('path', DATASETS, ids=[os.path.basename(p) for p in DATASETS])
def test_every_bundled_dataset_is_legacy_and_converts_without_changing_an_input(path):
    with open(path) as f:
        raw = json.load(f)
    model, kind, removed = formats.parse(raw)
    assert kind == 'legacy' and removed
    doc = formats.input_document(model)
    outputs = {k for fields in formats.LEGACY_OUTPUT_FIELDS.values() for k in fields}

    def same(a, b, where):
        if isinstance(a, dict):
            for k, v in a.items():
                if k not in outputs:
                    same(v, b[k], where + '/' + k)
        elif isinstance(a, list):
            assert len(a) == len(b), where
            for i, (x, y) in enumerate(zip(a, b)):
                same(x, y, where + '/' + str(i))
        else:                                   # value AND type: 0 stays 0, not 0.0
            assert a == b and type(a) is type(b), (where, a, b)

    same({k: v for k, v in raw.items() if k != 'solver'}, doc, '')


def test_legacy_and_its_canonical_form_solve_identically(horizon):
    horizon(H)
    legacy = base()
    canon = api.to_canonical(legacy)
    assert canon['format_version'] == 1 and 'solver' not in canon
    assert 'e_prod' not in canon['generator'][0] and 'kpis' not in canon['demand']['e']
    config = u.RunConfig(hours=H)
    a = api.solve(legacy, config=config).document
    b = api.solve(canon, config=config).document
    pa, pb = a.pop('provenance'), b.pop('provenance')
    for d in (a, b):
        d['solver'].pop('stat_time')
    assert a == b
    assert (pa['input_format'], pb['input_format']) == ('legacy', 'canonical')
    assert pa['result_format_version'] == pb['result_format_version'] == 1


def test_canonical_serialisation_reloads_to_the_same_case():
    canon = canonical()
    text = json.dumps(canon)
    again = api.parse_case(json.loads(text))
    assert again == api.parse_case(canon)
    assert api.to_canonical(json.loads(text)) == canon          # idempotent
    assert list(canon)[0] == 'format_version'
    # every default is explicit in the canonical form
    assert canon['flex'][0]['soc_min'] == 0.0 and canon['flex'][0]['charge_allowed'] is True
    assert canon['generator'][0]['condenser_p'] == 0.0 and canon['generator'][0]['turbine_t_p'] == []


def test_integers_are_kept_as_integers():
    s = base()
    s['generator'][0]['fix_cost_prod'] = 7
    canon = api.to_canonical(s)
    assert canon['generator'][0]['fix_cost_prod'] == 7 and type(canon['generator'][0]['fix_cost_prod']) is int
    assert type(canon['generator'][0]['c_prod']) is int                   # the -1 sentinel


@pytest.mark.parametrize('version', [2, 0, '1', 1.0, True, None])
def test_unsupported_format_versions_are_refused(version):
    doc = canonical()
    doc['format_version'] = version
    d = only(refusal(doc))
    assert (d.code, d.path, d.layer) == ('format.unsupported_version', '/format_version', 'format')


def test_a_canonical_input_may_not_carry_output_fields():
    doc = canonical()
    doc['generator'][0]['e_prod'] = []
    d = only(refusal(doc))
    assert (d.code, d.path, d.entity) == ('field.unknown', '/generator/0/e_prod', 'g')


def test_legacy_adapter_removes_only_documented_output_fields():
    s = base()
    s['generator'][0]['notes'] = 'free text'          # not an output field: kept, then refused
    d = only(refusal(s))
    assert (d.code, d.path) == ('field.unknown', '/generator/0/notes')
    s = base()
    s['solver']['stat_colour'] = 'red'
    d = only(refusal(s))
    assert (d.code, d.path, d.layer) == ('field.unknown', '/solver/stat_colour', 'format')


def test_a_result_given_as_input_is_refused_as_a_result(horizon):
    horizon(H)
    result = api.solve(base(), config=u.RunConfig(hours=H)).document
    error = refusal(json.loads(json.dumps(result)))
    codes = {d.code for d in error.diagnostics}
    assert codes == {'input.is_result'}
    paths = {d.path for d in error.diagnostics}
    assert '/system' in paths and '/generator/0/e_prod' in paths
    assert 'already holds' in str(error)


def test_legacy_placeholders_of_any_documented_shape_are_accepted(horizon):
    s = base()
    s['generator'][0]['a'] = 0.3                      # always overwritten; discarded
    s['demand']['e']['kpis'] = {'cost': -1, 'emis': -1, 'reli': -1}
    s['demand']['e']['shadow_prices'] = {'demand_match': [], 'carbon_cap': -1, 'reliability_cap': -1}
    s['provenance'] = {'input': 'somewhere'}
    model, kind, removed = formats.parse(s)
    assert kind == 'legacy' and '/generator/0/a' in removed and '/provenance' in removed


# --- structural failures: codes, paths, entities, hours -----------------------------------

@pytest.mark.parametrize('where, value, code', [
    (('generator', 0, 'capacity_factor'), '0.5', 'value.type'),
    (('generator', 0, 'capacity_factor'), True, 'value.type'),
    (('generator', 0, 'capacity_factor'), float('nan'), 'value.not_finite'),
    (('generator', 0, 'capacity_factor'), float('inf'), 'value.not_finite'),
    (('generator', 0, 'capacity_factor'), 1.5, 'value.out_of_range'),
    (('generator', 0, 'c_prod'), -2, 'value.out_of_range'),
    (('generator', 0, 'l_prod'), [5, 1], 'value.inconsistent'),
    (('generator', 0, 'l_prod'), [1], 'value.length'),
    (('generator', 0, 'type'), 'nuclear', 'value.not_allowed'),
    (('generator', 0, 'iden'), '', 'value.empty'),
    (('generator', 0, 'fix_cost_prod'), None, 'value.null'),
    (('flex', 0, 'charge_allowed'), 'no', 'value.type'),
    (('flex', 0, 'round_trip_efficiency'), 0.0, 'value.out_of_range'),
    (('flex', 0, 'inflow_profile'), None, 'value.null'),
    (('p2x', 0, 'supply_sources'), 'g', 'value.type'),
    (('demand', 'e', 'total'), -5.0, 'value.out_of_range'),
    (('demand', 'x', 0, 'var_cost_ns'), -1, 'value.out_of_range'),
])
def test_structural_failures_carry_code_path_and_entity(where, value, code):
    doc = canonical()
    node = doc
    for part in where[:-1]:
        node = node[part]
    node[where[-1]] = value
    d = only(refusal(doc))
    assert d.code == code and d.layer == 'structure'
    assert d.path == formats.pointer(*where)
    assert d.field == where[-1]
    entity = {'generator': 'g', 'flex': 'b', 'p2x': 'p'}.get(where[0], 'demand.e' if where[1] == 'e'
                                                           else 'demand.x[water]')
    assert d.entity == (entity if where[-1] != 'iden' else 'generator[0]')     # no identifier to name it by


def test_every_structural_problem_is_reported_at_once():
    doc = canonical()
    doc['generator'][0]['capacity_factor'] = 2
    doc['flex'][0]['soc_ini'] = -1
    del doc['p2x'][0]['soc_ini']
    doc['unexpected'] = 1
    got = {(d.code, d.path) for d in refusal(doc).diagnostics}
    assert got == {('value.out_of_range', '/generator/0/capacity_factor'),
                   ('value.out_of_range', '/flex/0/soc_ini'),
                   ('field.missing', '/p2x/0/soc_ini'),
                   ('field.unknown', '/unexpected')}


def test_cross_field_rules_of_one_object_name_the_field():
    doc = canonical()
    doc['flex'][0]['soc_min'] = 0.7                    # soc_ini 0.5 is now below the band
    d = only(refusal(doc))
    assert (d.code, d.path) == ('value.inconsistent', '/flex/0/soc_ini')
    doc = canonical()
    doc['p2x'][0]['pow_use_ther_prod'] = 0.05          # heat use on an electric process
    assert only(refusal(doc)).path == '/p2x/0/pow_use_ther_prod'
    doc = canonical()
    doc['p2x'][0]['type'] = 'elec + ther'
    del doc['p2x'][0]['temperature']
    d = only(refusal(doc))
    assert (d.code, d.path) == ('field.missing', '/p2x/0/temperature')


def test_an_inline_profile_element_is_located_by_hour():
    doc = canonical()
    doc['generator'][0]['profile'] = [1.0] * H
    doc['generator'][0]['profile'][17] = float('nan')
    d = only(refusal(doc))
    assert (d.code, d.path, d.hour) == ('value.not_finite', '/generator/0/profile/17', 17)


# --- what is valid: zero, negative, absent, empty ----------------------------------------

def test_meaningful_zero_and_negative_values_are_accepted(horizon):
    horizon(4)
    s = system(generators=[generator('dac', fix=-1.0, var=0.0, emis=-50.0),
                           generator('fixed', fix=1.0, var=1.0, c_prod=0)],
               e_total=4.0, e_kwargs={'var_cost_ns': 0.0, 'l_ns': (0, 0)})
    canon = api.to_canonical(s)
    result = api.solve(canon, options={'carbon-constraint': -10.0}, config=u.RunConfig(hours=4))
    assert result.optimal
    assert result.document['generator'][1]['c_prod'] == 0
    assert api.to_canonical(s)['generator'][0]['var_emis_prod'] == -50.0


def test_an_optimised_capacity_may_be_written_as_a_real():
    doc = canonical()
    doc['generator'][0]['c_prod'] = -1.0
    assert api.parse_case(doc).generator[0].capacity == -1.0


def test_absent_null_empty_and_zero_are_distinct():
    # absent: the default is written in
    doc = canonical()
    del doc['flex'][0]['soc_max']
    assert api.to_canonical(doc)['flex'][0]['soc_max'] == 1.0
    # null: refused
    doc['flex'][0]['soc_max'] = None
    assert only(refusal(doc)).code == 'value.null'
    # empty: '' is a flat profile, [] no sources, [] a not-applicable l_ns on an inactive demand
    doc = canonical()
    inactive = next(d for d in doc['demand']['x'] if d['total'] == 0)
    inactive['l_ns'] = []
    api.parse_case(doc)
    # ... which an active demand may not use
    doc['demand']['x'][0]['l_ns'] = []
    d = only(refusal(doc))
    assert (d.code, d.path) == ('value.length', '/demand/x/0/l_ns')
    # zero total: inactive, so its penalty and bounds may be omitted
    doc = canonical()
    inactive = next(d for d in doc['demand']['x'] if d['total'] == 0)
    del inactive['var_cost_ns'], inactive['l_ns']
    api.parse_case(doc)
    # ... but not when it is active
    doc['demand']['x'][0].pop('var_cost_ns')
    d = only(refusal(doc))
    assert (d.code, d.path) == ('field.missing', '/demand/x/0/var_cost_ns')


def test_models_can_be_built_in_python_with_descriptive_names(horizon):
    horizon(4)
    model = api.parse_case(canonical())
    gas = Generator(identifier='gas', kind='elec', capacity_factor=1.0, fixed_cost=1.0, variable_cost=30.0,
                    emission_factor=400.0, capacity_bounds=(0, 100), capacity=-1)
    case = model.model_copy(update={'generator': (gas,)})
    case = Case.model_validate(case.model_dump(by_alias=True))        # re-validated, not trusted
    assert api.to_canonical(case)['generator'][0]['fix_cost_prod'] == 1.0
    with pytest.raises(Exception):
        gas.fixed_cost = 2.0                                          # frozen
    with pytest.raises(InputError):
        api.parse_case({'format_version': 1, 'demand': {}, 'p2x': [], 'generator': [], 'flex': []})


def test_numpy_profiles_are_accepted_at_the_boundary_only(horizon):
    horizon(H)
    doc = canonical()
    doc['generator'][0]['profile'] = np.linspace(1.0, 2.0, H)
    before = copy.deepcopy(doc)
    result = api.solve(doc, config=u.RunConfig(hours=H))
    assert result.optimal
    assert isinstance(doc['generator'][0]['profile'], np.ndarray)             # the caller's array is untouched
    assert np.array_equal(doc['generator'][0]['profile'], before['generator'][0]['profile'])
    doc['generator'][0]['var_cost_prod'] = np.float32(1.0)                     # not a profile: refused
    assert only(refusal(doc)).code == 'value.type'


def test_options_are_validated_by_the_options_model():
    assert SolveOptions.names() == ['carbon-constraint', 'non-served-power-constraint']
    assert api.check_options({'non-served-power-constraint': 0, 'carbon-constraint': -3}) == \
        {'non-served-power-constraint': 0.0, 'carbon-constraint': -3.0}
    for bad, code in [({'carbon-constraint': float('nan')}, 'value.not_finite'),
                      ({'carbon-constraint': 'x'}, 'value.type'),
                      ({'carbon-constraint': True}, 'value.type'),
                      ({'non-served-power-constraint': 1.5}, 'value.out_of_range'),
                      ({'carbon-contraint': 1}, 'option.unknown')]:
        with pytest.raises(InputError) as info:
            api.check_options(bad)
        d = only(info.value)
        assert (d.code, d.layer, d.entity) == (code, 'options', 'command line')


# --- semantic failures ----------------------------------------------------------------------

def test_semantic_failures_carry_code_path_entity_and_hour(horizon, tmp_path):
    horizon(H)
    cases = []
    doc = canonical()
    doc['flex'].append(copy.deepcopy(doc['flex'][0]))
    cases.append((doc, 'identifier.duplicate', '/flex/1/iden', 'b', None))
    doc = canonical()
    doc['demand']['x'][0]['supply_sources'] = ['nowhere']
    cases.append((doc, 'reference.unknown', '/demand/x/0/supply_sources', 'demand.x[water]', None))
    doc = canonical()
    doc['demand']['x'][1].update(total=5.0, supply_sources=['p'], var_cost_ns=1.0, l_ns=[0, 1])
    cases.append((doc, 'topology.process_shared', '/p2x/0', 'p', None))
    doc = canonical()
    doc['demand']['e']['profile'] = [0.0] * 5 + [1.0] * (H - 5)
    doc['demand']['e']['l_ns'] = [0.5, 10]              # above the zero demand of hours 0 to 4
    cases.append((doc, 'shortfall.exceeds_demand', '/demand/e/l_ns', 'demand.e', 0))
    doc = canonical()
    doc['generator'][0]['profile'] = [1.0] * (H - 1)
    cases.append((doc, 'profile.length', '/generator/0/profile', 'g', None))
    doc = canonical()
    doc['generator'][0]['profile'] = [1.0] * 3 + [-1.0] + [1.0] * (H - 4)
    cases.append((doc, 'profile.negative', '/generator/0/profile', 'g', 3))
    doc = canonical()
    doc['generator'][0]['profile'] = 'missing.csv'
    cases.append((doc, 'profile.unresolvable', '/generator/0/profile', 'g', None))
    for doc, code, path, entity, hour in cases:
        d = only(refusal(doc))
        assert (d.code, d.path, d.entity, d.hour) == (code, path, entity, hour), d.to_dict()


def test_a_missing_profile_file_is_its_own_layer(tmp_path):
    doc = canonical()
    doc['generator'][0]['profile'] = 'missing.csv'
    path = tmp_path / 'case.json'
    path.write_text(json.dumps(doc))
    report = api.validate(str(path), config=u.RunConfig(hours=H))
    d = only(report)
    assert (d.code, d.layer, d.path) == ('profile.not_found', 'profiles', '/generator/0/profile')
    assert str(tmp_path / 'missing.csv') in d.message
    assert report.stages['structure'] == 'passed' and report.stages['semantics'] == 'failed'


def test_thermal_topology_failures(horizon):
    horizon(H)
    doc = canonical()
    doc['generator'].append(api.to_canonical(system(generators=[
        generator('chp', fix=1.0, var=1.0, kind='elec + ther', turbine=(564, 152), cond=0.05)]))['generator'][0])
    doc['p2x'][0].update(type='elec + ther', temperature=80, supply_sources=['g'], pow_use_ther_prod=0.1)
    d = only(refusal(doc))
    assert (d.code, d.path) == ('topology.not_cogeneration', '/p2x/0/supply_sources')
    doc['p2x'][0]['supply_sources'] = ['chp']
    doc['p2x'].append(dict(copy.deepcopy(doc['p2x'][0]), iden='p2'))
    d = only(refusal(doc))
    assert (d.code, d.path, d.entity) == ('topology.heat_shared', '/generator/1', 'chp')


# --- validation without solving -------------------------------------------------------------

def test_validate_reports_instead_of_raising_and_never_solves(monkeypatch):
    from ies_optimiser import opt
    monkeypatch.setattr(opt, 'run', lambda *a, **k: pytest.fail('validate must not solve'))
    report = api.validate(canonical(), config=u.RunConfig(hours=H))
    assert report.valid and report.format == 'canonical'
    assert report.stages == {'file': 'not required', 'options': 'passed', 'structure': 'passed',
                             'semantics': 'passed', 'thermodynamics': 'not required'}
    bad = canonical()
    bad['generator'][0]['capacity_factor'] = 3
    report = api.validate(bad, config=u.RunConfig(hours=H))
    assert not report.valid and report.stages['structure'] == 'failed'
    assert report.stages['semantics'] == 'not run'
    json.dumps(report.to_dict(), allow_nan=False)


def test_validate_runs_the_thermodynamics_and_reports_its_failure(tmp_path):
    doc = canonical()
    doc['generator'].append(api.to_canonical(system(generators=[
        generator('chp', fix=1.0, var=1.0, kind='elec + ther', turbine=(564, 152), cond=0.05)]))['generator'][0])
    doc['p2x'][0].update(type='elec + ther', temperature=80, supply_sources=['chp'], pow_use_ther_prod=0.1)
    bad = tmp_path / 'sim.bin'
    bad.write_text('#!/bin/sh\necho "error" >&2\nexit 3\n')
    bad.chmod(0o755)
    report = api.validate(doc, config=u.RunConfig(hours=H, thermo_bin=str(bad)))
    d = only(report)
    assert (d.code, d.layer, d.entity, d.path) == ('thermo.failed', 'thermodynamics', 'chp', '/generator/1')
    assert report.stages['semantics'] == 'passed' and report.stages['thermodynamics'] == 'failed'
    skipped = api.validate(doc, config=u.RunConfig(hours=H, thermo_bin=str(bad)), thermodynamics=False)
    assert skipped.valid and skipped.stages['thermodynamics'] == 'not run'
    with pytest.raises(ThermoError) as info:                        # solve raises the same diagnostic
        api.solve(doc, config=u.RunConfig(hours=H, thermo_bin=str(bad)))
    assert info.value.diagnostics == report.diagnostics


def test_parsing_and_validation_leave_the_caller_s_document_unchanged():
    for doc in (base(), canonical()):
        before = copy.deepcopy(doc)
        api.parse_case(doc)
        api.to_canonical(doc)
        api.validate(doc, config=u.RunConfig(hours=H))
        assert doc == before


def test_a_case_model_solves_repeatedly_and_independently(horizon):
    horizon(H)
    model = api.parse_case(base())
    config = u.RunConfig(hours=H)
    a, b = api.solve(model, config=config), api.solve(model, config=config)
    assert a.document is not b.document
    for d in (a.document, b.document):
        d['solver'].pop('stat_time'), d['provenance'].pop('run_utc')
    assert a.document == b.document
    assert model == api.parse_case(base())
    assert a.document['provenance']['input'] == '<in-memory>'


def test_storage_model_documents_units():
    fields = Storage.model_fields
    assert 'MWh' in fields['capacity'].description
    assert fields['capacity'].alias == 'c_strg'
