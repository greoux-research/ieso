"""Fixtures for the installed-artifact tests.

These tests exercise the ieso package installed in the running Python -- in
CI, a wheel installed into a fresh environment with no source checkout -- and
need only the test bundle beside them:

    tests_installed/                  these tests
    tests/fixtures/thermo_reference.json
    examples/                         the synthetic cases and expected.json
    tools/check_invariants.py         the independent invariant checker
    README.md, docs/ieso-api.md, docs/ieso-setup-guide.md   (their tested examples)

Environment:
    IESO_ISOLATED=1   assert that the process cannot reach a checkout, Git or a
                      compiler, and that ieso is an installed wheel (set by the
                      CI test jobs, which run with PATH reduced to the
                      virtual environment).
"""

import copy
import importlib.util
import os
import shutil

import pytest

import ieso

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.dirname(HERE)
EXAMPLES = os.path.join(BUNDLE, 'examples')
FIXTURE = os.path.join(BUNDLE, 'tests', 'fixtures', 'thermo_reference.json')
INVARIANTS = os.path.join(BUNDLE, 'tools', 'check_invariants.py')
ISOLATED = os.environ.get('IESO_ISOLATED') == '1'


def console():
    """The installed 'ieso' console command, beside this interpreter."""
    import sys
    found = shutil.which('ieso', path=os.path.dirname(sys.executable))
    assert found, 'no ieso console script beside ' + sys.executable
    return found


@pytest.fixture(scope='session')
def examples_copy(tmp_path_factory):
    """A copy of examples/ in a directory whose name contains spaces."""
    root = tmp_path_factory.mktemp('installed') / 'examples with spaces'
    shutil.copytree(EXAMPLES, str(root))
    return root


@pytest.fixture(scope='session')
def expected():
    import json
    with open(os.path.join(EXAMPLES, 'expected.json'), encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='session')
def solved(examples_copy, expected):
    """Every expected scenario solved once through the API: name -> (SolveResult, input copy)."""
    import json
    out = {}
    for sc in expected['scenarios']:
        path = str(examples_copy / sc['case'])
        with open(path, encoding='utf-8') as f:
            case = json.load(f)
        before = copy.deepcopy(case)
        result = ieso.solve(case, options=sc['options'], source=path)
        assert case == before, 'solve() modified its input'
        out[sc['name']] = result
    return out


@pytest.fixture(scope='session')
def invariants():
    spec = importlib.util.spec_from_file_location('check_invariants', INVARIANTS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
