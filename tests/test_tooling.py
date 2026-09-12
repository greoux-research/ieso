"""The verification tooling itself.

A comparator that passes over what it cannot find reports agreement it has not
checked, and a failed solve that exits zero is indistinguishable from a good one
to anything calling IESO from a script. Both weaken the evidence rather than the
model, which is why they are tested.
"""

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPARE = os.path.join(ROOT, 'tools', 'compare_outputs.py')


def result(tmp_path, name, **overrides):
    """A minimal well-formed result, with fields optionally overridden."""
    doc = {
        'demand': {
            'e': {'iden': 'electricity', 'total': 100.0, 'var_cost_ns': 10.0,
                  'output_ns': [0.0] * 3,
                  'shadow_prices': {'demand_match': [1.0, 1.0, 1.0]},
                  'kpis': {'cost': 5.0, 'emis': 1.0, 'reli': 1.0}},
            'x': [{'iden': 'water', 'total': 10.0, 'var_cost_ns': 1.0,
                   'output_ns': [0.0] * 3,
                   'shadow_prices': {'demand_match': [0.5, 0.5, 0.5]},
                   'kpis': {'cost': 2.0, 'emis': 0.1, 'reli': 1.0}}],
        },
        'generator': [{'iden': 'gas', 'c_prod': 50.0, 'e_prod': [10.0, 20.0, 30.0],
                       'h_prod': [], 'type': 'elec', 'a': 0, 'b': 0}],
        'flex': [], 'p2x': [],
        'solver': {'stat_succ': 1, 'stat_status': 'optimal',
                   'stat_capa': 1, 'stat_outp': 3, 'stat_cons': 3},
    }
    for path, value in overrides.items():
        node = doc
        parts = path.split('.')
        for part in parts[:-1]:
            node = node[int(part)] if part.isdigit() else node[part]
        last = parts[-1]
        if last.isdigit():
            node[int(last)] = value
        elif value is ...:
            del node[last]
        else:
            node[last] = value
    p = tmp_path / name
    p.write_text(json.dumps(doc))
    return str(p)


def compare(a, b):
    out = subprocess.run([sys.executable, COMPARE, a, b],
                         stdout=subprocess.PIPE, text=True)
    return out.returncode, out.stdout


def test_identical_results_agree(tmp_path):
    a = result(tmp_path, 'a.json')
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 0 and 'IDENTICAL' in out


def test_a_deleted_dispatch_series_is_caught(tmp_path):
    """An empty series used to bypass comparison entirely."""
    a = result(tmp_path, 'a.json', **{'generator.0.e_prod': []})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'e_prod' in out


def test_a_missing_commodity_is_caught(tmp_path):
    """Product demands were paired with zip, which ignores missing entries."""
    a = result(tmp_path, 'a.json', **{'demand.x': []})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'commodity sets differ' in out


def test_a_missing_entity_is_caught(tmp_path):
    a = result(tmp_path, 'a.json', **{'generator': []})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'entity sets differ' in out


def test_a_missing_required_field_is_caught(tmp_path):
    a = result(tmp_path, 'a.json', **{'generator.0.c_prod': ...})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'c_prod' in out


def test_a_changed_value_is_caught(tmp_path):
    a = result(tmp_path, 'a.json', **{'generator.0.e_prod': [10.0, 20.0, 31.0]})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1


def test_legitimately_empty_series_still_agree(tmp_path):
    """h_prod is empty on a unit that is not a cogeneration plant."""
    a = result(tmp_path, 'a.json')
    b = result(tmp_path, 'b.json')
    code, _ = compare(a, b)
    assert code == 0


@pytest.mark.parametrize('series', [
    [float('nan'), 20.0, 99999.0],
    [float('inf'), 20.0, 30.0],
    [10.0, 20.0, float('-inf')],
])
def test_non_finite_values_in_a_series_are_caught(tmp_path, series):
    """NaN propagates through max() and compares False against any threshold,
    so one bad entry would report agreement for the whole series."""
    a = result(tmp_path, 'a.json', **{'generator.0.e_prod': series})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'non-finite' in out


def test_a_non_finite_scalar_is_caught(tmp_path):
    a = result(tmp_path, 'a.json', **{'generator.0.c_prod': float('nan')})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'non-finite' in out


def test_cogeneration_coefficients_are_compared(tmp_path):
    """a converts heat to forgone electricity and b caps heat output. Two
    results agreeing on dispatch but not on these describe different machines."""
    kw = {'generator.0.type': 'elec + ther', 'generator.0.a': 0.25, 'generator.0.b': 1.5}
    b = result(tmp_path, 'b.json', **kw)
    for field, changed in (('a', 0.8), ('b', 3.0)):
        a = result(tmp_path, f'a_{field}.json', **{**kw, f'generator.0.{field}': changed})
        code, out = compare(a, b)
        assert code == 1, field
        assert f'    {field}:' in out


def test_missing_coefficients_are_caught_on_a_thermal_unit(tmp_path):
    kw = {'generator.0.type': 'elec + ther', 'generator.0.a': 0.25, 'generator.0.b': 1.5}
    a = result(tmp_path, 'a.json', **{**kw, 'generator.0.a': ...})
    b = result(tmp_path, 'b.json', **kw)
    code, out = compare(a, b)
    assert code == 1
    assert 'a:' in out


def test_a_changed_generator_type_is_caught(tmp_path):
    """eqs_gen downgrades a thermal unit to elec when it has no heat consumer."""
    a = result(tmp_path, 'a.json', **{'generator.0.type': 'elec + ther'})
    b = result(tmp_path, 'b.json', **{'generator.0.type': 'elec'})
    code, out = compare(a, b)
    assert code == 1
    assert 'type' in out


def test_a_differing_solver_status_is_caught(tmp_path):
    a = result(tmp_path, 'a.json', **{'solver.stat_status': 'infeasible',
                                      'solver.stat_succ': 0})
    b = result(tmp_path, 'b.json')
    code, out = compare(a, b)
    assert code == 1
    assert 'stat_status' in out


def test_provenance_identifies_the_running_code():
    """A version constant is a label; two trees can share it and differ."""
    from ieso_modules import fcn as u
    state = u.source_state()
    assert set(state) == {'git_revision', 'git_dirty',
                          'source_sha256', 'source_files_sha256'}
    assert len(state['source_sha256']) == 64
    files = state['source_files_sha256']
    assert 'ieso.py' in files
    assert 'ieso_modules/fcn.py' in files
    # the compiled thermodynamic binary sets the cogeneration coefficients and
    # is untracked, so it is covered whether or not it is present
    assert 'thermo/sim.bin' in files


def test_source_digest_changes_with_the_source(tmp_path, monkeypatch):
    from ieso_modules import fcn as u
    before = u.source_state()['source_sha256']
    extra = os.path.join(ROOT, 'ieso_modules', '_digest_probe.py')
    try:
        with open(extra, 'w') as f:
            f.write('# temporary file for the digest test\n')
        after = u.source_state()['source_sha256']
    finally:
        if os.path.exists(extra):
            os.remove(extra)
    assert before != after
    assert u.source_state()['source_sha256'] == before


def test_an_infeasible_model_is_reported_as_such(horizon):
    """ieso.py exits non-zero on this; the status says why."""
    from conftest import generator, solve, system
    hours = horizon(24)
    s = system(generators=[generator('gas', var=10.0, l_prod=(0, 0))],
               e_total=100.0 * hours,
               e_kwargs={'l_ns': (0, 0)})          # no capacity, no shortfall allowed
    ok, s = solve(s)
    assert ok is False
    assert s['solver']['stat_succ'] == 0


# --- the command line itself ------------------------------------------------

def cli_case(tmp_path, name, feasible):
    """A full-horizon input small enough to solve in seconds."""
    from conftest import demand_e, generator, system
    s = system(generators=[generator('gas', fix=1.0, var=10.0,
                                     l_prod=(0, 1e5) if feasible else (0, 0))],
               e_total=8760.0)
    if not feasible:
        s['demand']['e']['l_ns'] = [0, 0]          # no capacity and no shortfall allowed
    p = tmp_path / name
    p.write_text(json.dumps(s))
    return str(p)


def run_cli(path):
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'ieso.py'), path],
                         cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, timeout=300)
    return out.returncode, out.stdout


def test_cli_exits_zero_on_an_optimal_solve(tmp_path):
    code, _ = run_cli(cli_case(tmp_path, 'ok.json', feasible=True))
    assert code == 0
    written = json.load(open(str(tmp_path / 'ok.ieso.json')))
    assert written['solver']['stat_status'] == 'optimal'
    assert written['solver']['stat_succ'] == 1


def test_cli_exits_non_zero_on_an_unsuccessful_solve(tmp_path):
    """A script calling IESO must be able to tell without parsing the result."""
    code, _ = run_cli(cli_case(tmp_path, 'bad.json', feasible=False))
    assert code != 0
    written = json.load(open(str(tmp_path / 'bad.ieso.json')))
    assert written['solver']['stat_succ'] == 0
    assert written['solver']['stat_status'] != 'optimal'
    # the file is still written, and is still traceable
    assert written['provenance']['source_sha256']
