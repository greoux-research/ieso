"""The validate and schema commands (Step 4), through the real launcher.

python ieso.py validate CASE.json [--json] [--profile-base DIR]
python ieso.py schema input|result

validate never solves and never writes; with --json it prints exactly one
JSON document on stdout and nothing else there. schema needs no case and no
thermodynamics executable.
"""

import json
import os
import subprocess
import sys

import pytest

from ieso import api, cli, schemas
from ieso import fcn as u
from conftest import demand_x, generator, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IESO = os.path.join(ROOT, 'ieso.py')


def run(*args, cwd):
    out = subprocess.run([sys.executable, IESO] + [str(a) for a in args], cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, timeout=300)
    return out.returncode, out.stdout, out.stderr


def year_case(tmp_path, name='case.json', canonical=True, **changes):
    s = system(generators=[generator('g', fix=1.0, var=10.0, emis=100.0)], e_total=8760.0,
               xs=[demand_x('water', 0, [])])
    doc = api.to_canonical(s) if canonical else s
    for key, value in changes.items():
        doc['generator'][0][key] = value
    path = tmp_path / name
    path.write_text(json.dumps(doc))
    return path


def files(folder):
    return sorted(p.name for p in folder.iterdir())


def test_validate_json_emits_one_clean_document(tmp_path):
    path = year_case(tmp_path)
    before = files(tmp_path)
    code, out, err = run('validate', path, '--json', cwd=tmp_path)
    assert code == 0, err
    doc = json.loads(out)                                    # the whole of stdout is one JSON document
    assert doc['valid'] is True and doc['format'] == 'canonical' and doc['diagnostics'] == []
    assert doc['stages']['semantics'] == 'passed'
    assert doc['profile_resolution'] == {'mode': 'input-directory', 'base': str(tmp_path)}
    assert files(tmp_path) == before                         # nothing written


def test_validate_json_reports_structured_diagnostics(tmp_path):
    path = year_case(tmp_path, capacity_factor=2, var_cost_prod='cheap')
    code, out, err = run('validate', path, '--json', cwd=tmp_path)
    assert code == 1
    doc = json.loads(out)
    assert doc['valid'] is False and doc['stages']['structure'] == 'failed' and doc['format'] == 'canonical'
    got = {(d['code'], d['path'], d['entity'], d['layer']) for d in doc['diagnostics']}
    assert got == {('value.out_of_range', '/generator/0/capacity_factor', 'g', 'structure'),
                   ('value.type', '/generator/0/var_cost_prod', 'g', 'structure')}
    assert all(set(d) == {'code', 'layer', 'message', 'path', 'entity', 'field', 'hour'} for d in doc['diagnostics'])


def test_validate_distinguishes_a_missing_profile_file(tmp_path):
    path = year_case(tmp_path, profile='absent.csv')
    code, out, _ = run('validate', path, '--json', cwd=tmp_path)
    assert code == 1
    d = json.loads(out)['diagnostics'][0]
    assert (d['code'], d['layer'], d['path']) == ('profile.not_found', 'profiles', '/generator/0/profile')


def test_validate_honours_the_profile_base(tmp_path):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'shape.csv').write_text('\n'.join(['1.0'] * 8760))
    path = year_case(tmp_path, profile='data/shape.csv')
    elsewhere = tmp_path / 'cases'
    elsewhere.mkdir()
    moved = elsewhere / 'case.json'
    moved.write_text(path.read_text())
    assert run('validate', moved, cwd=tmp_path)[0] == 1                                  # not beside the input
    code, out, err = run('validate', moved, '--profile-base', tmp_path, '--json', cwd=ROOT)
    assert code == 0, out + err
    assert json.loads(out)['profile_resolution'] == {'mode': 'explicit', 'base': str(tmp_path)}


def test_validate_reads_legacy_inputs_and_lists_what_it_removed(tmp_path):
    path = year_case(tmp_path, canonical=False)
    code, out, _ = run('validate', path, '--json', cwd=tmp_path)
    assert code == 0
    doc = json.loads(out)
    assert doc['format'] == 'legacy' and '/solver' in doc['removed_fields']


def test_validate_text_mode_keeps_diagnostics_on_stderr(tmp_path):
    path = year_case(tmp_path, capacity_factor=2)
    code, out, err = run('validate', path, cwd=tmp_path)
    assert code == 1
    assert 'invalid' in out and 'value.out_of_range' in err and 'capacity_factor' in err


@pytest.mark.parametrize('args', [['validate'], ['validate', '--json'], ['validate', 'x.json', '--bogus'],
                                  ['validate', 'x.json', '--json=yes'], ['validate', 'x.json', 'carbon-constraint=z']])
def test_validate_usage_errors_exit_nonzero(tmp_path, args):
    code, out, _ = run(*args, cwd=tmp_path)
    assert code == 1
    if '--json' in args:
        assert json.loads(out)['valid'] is False


def test_validate_checks_options_without_solving(tmp_path):
    path = year_case(tmp_path)
    code, out, _ = run('validate', path, 'non-served-power-constraint=2', '--json', cwd=tmp_path)
    assert code == 1
    d = json.loads(out)['diagnostics'][0]
    assert (d['code'], d['layer'], d['field']) == ('value.out_of_range', 'options', 'non-served-power-constraint')


@pytest.mark.parametrize('kind', ['input', 'result'])
def test_schema_command_prints_the_checked_in_schema(tmp_path, kind):
    code, out, err = run('schema', kind, cwd=tmp_path)
    assert code == 0, err
    with open(schemas.path(kind), encoding='utf-8') as f:
        assert out == f.read()
    assert files(tmp_path) == []


def test_schema_needs_no_case_and_no_thermodynamics(monkeypatch, capsys):
    monkeypatch.setattr(u, 'thermo', lambda *a, **k: pytest.fail('schema must not run thermodynamics'))
    monkeypatch.setattr(u, 'Thermo_bin', '/nonexistent/sim.bin')
    assert cli.main(['schema', 'input']) == 0
    assert json.loads(capsys.readouterr().out)['x-ieso-format']['kind'] == 'input'
    assert cli.main(['schema']) == 1 and cli.main(['schema', 'case']) == 1


def test_the_solve_form_is_unchanged_and_rejects_validate_flags(tmp_path):
    path = year_case(tmp_path)
    code, _, err = run(path, '--json', cwd=tmp_path)
    assert code == 1 and 'unknown flag' in err
    assert not list(tmp_path.glob('*.ieso*.json'))
    code, _, err = run(path, cwd=tmp_path)
    assert code == 0, err
    doc = json.loads((tmp_path / 'case.ieso.json').read_text())
    assert doc['provenance']['input_format'] == 'canonical'


def test_statuses_stay_distinguishable(tmp_path):
    """Invalid input: exit 1, nothing written. Infeasible: exit 1, a result
    with stat_succ 0. Optimal: exit 0 (3 would be an accounting failure)."""
    invalid = year_case(tmp_path, 'invalid.json', capacity_factor=2)
    assert run(invalid, cwd=tmp_path)[0] == 1 and not (tmp_path / 'invalid.ieso.json').exists()
    infeasible = year_case(tmp_path, 'infeasible.json', l_prod=[0, 0.5])
    doc = json.loads(infeasible.read_text())
    doc['demand']['e']['l_ns'] = [0, 0]
    infeasible.write_text(json.dumps(doc))
    assert run('validate', infeasible, cwd=tmp_path)[0] == 0          # a valid case ...
    assert run(infeasible, cwd=tmp_path)[0] == 1                      # ... that is infeasible
    result = json.loads((tmp_path / 'infeasible.ieso.json').read_text())
    assert result['solver']['stat_succ'] == 0 and result['solver']['stat_status'] == 'infeasible'
