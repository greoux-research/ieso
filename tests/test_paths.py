"""Profile paths: resolved against the input file's directory, portable, explicit.

Rules under test: a relative profile path resolves against the directory of the
input file it came from (or an explicit profile base); an absolute path is used
as written; empty and inline profiles are unaffected; the working directory is
never consulted, and nothing falls back to another location.
"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

from ies_optimiser import api
from ies_optimiser import fcn as u
from ies_optimiser.errors import InputError
from conftest import demand_x, flex, generator, p2x, system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = 24


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def write_case(directory, profile_ref='dmnd.csv', hours=H, name='case.json', csv_values=None):
    """A case directory: case.json plus dmnd.csv and solr.csv beside it."""
    os.makedirs(directory, exist_ok=True)
    values = csv_values if csv_values is not None else np.linspace(1.0, 2.0, hours)
    np.savetxt(os.path.join(directory, 'dmnd.csv'), values)
    np.savetxt(os.path.join(directory, 'solr.csv'), np.abs(np.sin(np.arange(hours))) + 0.1)
    s = system(generators=[generator('gas', fix=1.0, var=30.0),
                           generator('solr', fix=0.5, var=0.0, profile='solr.csv', cf=0.3)],
               e_total=10.0 * hours, e_kwargs={'profile': profile_ref})
    path = os.path.join(directory, name)
    with open(path, 'w') as f:
        json.dump(s, f)
    return path


def numbers(doc):
    """The mathematical part of a result: everything but provenance and timing."""
    d = copy.deepcopy(doc)
    d.pop('provenance')
    d['solver'].pop('stat_time')
    return d


def cfg(**kw):
    return u.RunConfig(hours=H, **kw)


# --- the default: the input file's directory --------------------------------------------

def test_relative_profiles_resolve_against_the_input_directory(tmp_path):
    path = write_case(str(tmp_path / 'case'))
    result = api.solve(path, config=cfg())
    assert result.optimal
    pv = result.document['provenance']
    assert pv['profile_resolution'] == {'mode': 'input-directory', 'base': str(tmp_path / 'case')}
    assert pv['profile_files']['dmnd.csv'] == {'resolved': str(tmp_path / 'case' / 'dmnd.csv'),
                                               'sha256': sha(tmp_path / 'case' / 'dmnd.csv')}
    assert pv['profiles_sha256'] == {'solr.csv': sha(tmp_path / 'case' / 'solr.csv'),
                                     'dmnd.csv': sha(tmp_path / 'case' / 'dmnd.csv')}
    assert pv['input_resolved'] == path and pv['input_sha256'] == sha(path)


def test_the_working_directory_does_not_matter(tmp_path, monkeypatch):
    path = write_case(str(tmp_path / 'case'))
    results = []
    for cwd in (tmp_path, tmp_path / 'case', ROOT):
        monkeypatch.chdir(cwd)
        results.append(api.solve(path, config=cfg()).document)
    assert numbers(results[0]) == numbers(results[1]) == numbers(results[2])
    assert os.getcwd() == ROOT                               # IES Optimiser did not change directory itself


def test_a_decoy_in_the_working_directory_is_never_read(tmp_path, monkeypatch):
    """A different dmnd.csv in the working directory must be ignored: the case's
    own file is read, and provenance hashes it."""
    path = write_case(str(tmp_path / 'case'))
    np.savetxt(str(tmp_path / 'dmnd.csv'), np.linspace(5.0, 1.0, H))          # different shape
    monkeypatch.chdir(tmp_path)
    doc = api.solve(path, config=cfg()).document
    assert doc['provenance']['profiles_sha256']['dmnd.csv'] == sha(tmp_path / 'case' / 'dmnd.csv')
    assert doc['provenance']['profiles_sha256']['dmnd.csv'] != sha(tmp_path / 'dmnd.csv')
    reference = api.solve(path, config=cfg()).document       # same case, same answer
    assert numbers(doc) == numbers(reference)


def test_a_copied_case_directory_gives_the_same_answer(tmp_path):
    original = write_case(str(tmp_path / 'a'))
    shutil.copytree(str(tmp_path / 'a'), str(tmp_path / 'b'))
    moved = str(tmp_path / 'b' / 'case.json')
    shutil.rmtree(str(tmp_path / 'a'))                       # the original is gone: nothing can leak from it
    r = api.solve(moved, config=cfg()).document
    assert r['provenance']['profile_resolution']['base'] == str(tmp_path / 'b')
    assert r['provenance']['profiles_sha256']['dmnd.csv'] == sha(tmp_path / 'b' / 'dmnd.csv')
    fresh = write_case(str(tmp_path / 'c'))
    c = api.solve(fresh, config=cfg()).document
    assert numbers(r) == numbers(c)
    assert r['provenance']['input_sha256'] == c['provenance']['input_sha256']      # same bytes
    assert r['provenance']['profiles_sha256'] == c['provenance']['profiles_sha256']


def test_paths_with_spaces(tmp_path):
    path = write_case(str(tmp_path / 'my cases' / 'case one'), name='the case.json')
    result = api.solve(path, config=cfg())
    assert result.optimal
    assert result.document['provenance']['profile_files']['dmnd.csv']['resolved'] == \
        str(tmp_path / 'my cases' / 'case one' / 'dmnd.csv')


def test_absolute_profile_paths_are_used_as_written(tmp_path):
    elsewhere = tmp_path / 'shared'
    elsewhere.mkdir()
    np.savetxt(str(elsewhere / 'demand.csv'), np.linspace(1.0, 3.0, H))
    path = write_case(str(tmp_path / 'case'), profile_ref=str(elsewhere / 'demand.csv'))
    doc = api.solve(path, config=cfg()).document
    assert doc['provenance']['profile_files'][str(elsewhere / 'demand.csv')]['resolved'] == str(elsewhere / 'demand.csv')
    # an explicit base moves the relative solr.csv but not the absolute demand path
    doc2 = api.solve(path, config=cfg(profile_base=str(tmp_path / 'case'))).document
    assert doc2['provenance']['profile_files'][str(elsewhere / 'demand.csv')]['resolved'] == str(elsewhere / 'demand.csv')
    assert numbers(doc2) == numbers(doc)


# --- in-memory cases -------------------------------------------------------------------

def test_inline_and_empty_profiles_need_no_base():
    s = system(generators=[generator('gas', var=1.0), generator('solr', var=0.0, profile=list(np.linspace(0.1, 1, H)), cf=0.3)],
               e_total=float(H), e_kwargs={'profile': ''})
    result = api.solve(s, config=cfg())
    assert result.optimal
    assert result.document['provenance']['profile_resolution'] == {'mode': 'none', 'base': None}
    assert result.document['provenance']['profiles_sha256'] == {}


def test_an_in_memory_case_with_relative_paths_needs_a_base(tmp_path):
    write_case(str(tmp_path / 'case'))
    case = json.load(open(str(tmp_path / 'case' / 'case.json')))
    before = copy.deepcopy(case)
    with pytest.raises(InputError) as info:
        api.solve(case, config=cfg())
    assert 'cannot be resolved' in str(info.value) and info.value.field == 'profile'
    ok = api.solve(case, config=cfg(profile_base=str(tmp_path / 'case')))
    assert ok.optimal
    assert ok.document['provenance']['profile_resolution'] == {'mode': 'explicit', 'base': str(tmp_path / 'case')}
    assert case == before                                     # the caller's case is untouched either way


def test_source_supplies_the_base_for_a_parsed_document(tmp_path):
    path = write_case(str(tmp_path / 'case'))
    result = api.solve(api.load_input(path), config=cfg(), source=path)
    assert result.document['provenance']['profile_resolution']['mode'] == 'input-directory'


# --- failures and conflicts -----------------------------------------------------------------

def test_a_missing_profile_names_field_declared_path_and_location(tmp_path):
    path = write_case(str(tmp_path / 'case'))
    os.remove(str(tmp_path / 'case' / 'dmnd.csv'))
    with pytest.raises(InputError) as info:
        api.solve(path, config=cfg())
    e = info.value
    assert e.entity == 'demand.e' and e.field == 'profile'
    assert "'dmnd.csv'" in str(e) and str(tmp_path / 'case' / 'dmnd.csv') in str(e)


def test_no_fallback_to_the_working_directory(tmp_path, monkeypatch):
    """The file exists in the working directory but not beside the input: refused."""
    path = write_case(str(tmp_path / 'case'))
    os.remove(str(tmp_path / 'case' / 'dmnd.csv'))
    np.savetxt(str(tmp_path / 'dmnd.csv'), np.linspace(1.0, 2.0, H))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(InputError):
        api.solve(path, config=cfg())


def test_conflicting_configuration_is_refused(tmp_path):
    path = write_case(str(tmp_path / 'case'))
    with pytest.raises(InputError) as info:
        api.solve(path, config=cfg(), source=str(tmp_path / 'other.json'))
    assert info.value.entity == 'source'
    with pytest.raises(InputError) as info:
        api.solve(path, config=cfg(profile_base=str(tmp_path / 'no-such-dir')))
    assert info.value.entity == 'profile_base'


# --- explicit legacy compatibility -----------------------------------------------------------

def test_an_old_root_relative_input_runs_with_an_explicit_base(tmp_path):
    """Old inputs named profiles relative to a root directory (the repository),
    e.g. 'datasets/x/dmnd.csv'. They run unchanged by naming that directory;
    without it they are refused -- nothing retries another location."""
    root = tmp_path / 'root'
    case_dir = root / 'datasets' / 'x'
    write_case(str(case_dir))
    old = json.load(open(str(case_dir / 'case.json')))
    old['demand']['e']['profile'] = 'datasets/x/dmnd.csv'
    old['generator'][1]['profile'] = 'datasets/x/solr.csv'
    old_path = str(case_dir / 'old.json')
    json.dump(old, open(old_path, 'w'))
    with pytest.raises(InputError):
        api.solve(old_path, config=cfg())
    legacy = api.solve(old_path, config=cfg(profile_base=str(root))).document
    current = api.solve(str(case_dir / 'case.json'), config=cfg()).document
    # identical once the declared path strings are mapped to their new names
    renamed = numbers(legacy)
    renamed['demand']['e']['profile'] = 'dmnd.csv'
    renamed['generator'][1]['profile'] = 'solr.csv'
    assert renamed == numbers(current)
    assert legacy['provenance']['profiles_sha256']['datasets/x/dmnd.csv'] == \
        current['provenance']['profiles_sha256']['dmnd.csv']
    assert legacy['provenance']['profile_resolution'] == {'mode': 'explicit', 'base': str(root)}


# --- the command line ------------------------------------------------------------------------

def full_year(directory):
    return write_case(directory, hours=8760)


def cli(args, cwd):
    return subprocess.run([sys.executable, os.path.join(ROOT, 'ies_optimiser.py')] + args, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)


def test_cli_from_any_directory_with_a_decoy(tmp_path):
    path = full_year(str(tmp_path / 'case dir'))
    np.savetxt(str(tmp_path / 'dmnd.csv'), np.linspace(9.0, 1.0, 8760))       # decoy in the cwd
    out = cli([path, 'carbon-constraint=500'], cwd=str(tmp_path))
    assert out.returncode == 0, out.stdout
    doc = json.loads(open(os.path.join(str(tmp_path / 'case dir'), 'case.ies-optimiser.carbon-constraint_500.0.json')).read())
    assert doc['provenance']['profiles_sha256']['dmnd.csv'] == sha(tmp_path / 'case dir' / 'dmnd.csv')
    assert doc['provenance']['options'] == {'carbon-constraint': 500.0}      # the flag is not an option


def test_cli_profile_base_as_the_runner_uses_it(tmp_path):
    """The case runner copies an input elsewhere and names the original case
    directory with --profile-base. The copy then reads the original's CSVs, and
    the result is named after the copy, with no trace of the flag in the name."""
    original = full_year(str(tmp_path / 'datasets' / 'x'))
    runs = tmp_path / 'runs'
    runs.mkdir()
    copy_path = str(runs / 'label.json')
    shutil.copyfile(original, copy_path)
    out = cli([copy_path, 'carbon-constraint=500', '--profile-base', str(tmp_path / 'datasets' / 'x')], cwd='/')
    assert out.returncode == 0, out.stdout
    written = sorted(p.name for p in runs.iterdir())
    assert written == ['label.ies-optimiser.carbon-constraint_500.0.json', 'label.json']
    pv = json.loads((runs / 'label.ies-optimiser.carbon-constraint_500.0.json').read_text())['provenance']
    assert pv['profile_resolution'] == {'mode': 'explicit', 'base': str(tmp_path / 'datasets' / 'x')}
    assert pv['input_sha256'] == sha(original)
    assert not any(p.name.endswith('.ies-optimiser.json') for p in (tmp_path / 'datasets' / 'x').iterdir())


@pytest.mark.parametrize('args, reason', [
    (['--profile-base'], 'needs a value'),
    (['--profile-base='], 'needs a value'),
    (['--profile-base', 'a', '--profile-base', 'b'], 'more than once'),
    (['--profile-bse', '.'], 'unknown flag'),
    (['--profile-base', '/no/such/directory'], 'not a directory'),
])
def test_cli_flag_errors_fail_before_solving(tmp_path, args, reason):
    path = full_year(str(tmp_path / 'case'))
    out = cli([path] + args, cwd=str(tmp_path))
    assert out.returncode == 1 and reason in out.stdout
    assert not [p for p in (tmp_path / 'case').iterdir() if '.ies-optimiser' in p.name]
