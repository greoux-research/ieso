"""Reference behaviour of the thermodynamics executable, for regression checks.

Two kinds of evidence are kept apart here.

* FIXTURES (tests/fixtures/thermo_reference.json) record what the reference
  build of thermo/sim.bin emitted at commit a1b2cb2: the coefficients a and b
  for both turbines of the bundled MED case across the supported extraction
  range, the domain limits, and the refusals on and outside those limits. They
  record behaviour. They do not prove it physically correct.
* PHYSICAL CHECKS compare against independent steam-table values (IAPWS-IF97)
  and properties any valid result must have. They are the evidence of
  correctness, and are deliberately loose.

Tolerance for coefficients: the executable prints 6 significant digits, so a
build that differs only in floating-point detail (another compiler, another
optimisation level) may round the 6th digit the other way. A difference of at
most one unit in the 6th significant digit is accepted; anything more is a
change of behaviour. The reference build itself must reproduce the fixture
strings exactly.
"""

import json
import math
import os
import subprocess

import pytest

from ies_optimiser import fcn as u

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'thermo_reference.json')))
PLANTS = FIXTURE['plants']
ACCEPTED = [(name, c) for name, p in PLANTS.items() for c in p['accepted']]
REFUSED = [(name, c) for name, p in PLANTS.items() for c in p['refused']]


def run(binary, *args):
    out = subprocess.run([binary] + [str(a) for a in args], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, timeout=30)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def conditions(name):
    p = PLANTS[name]
    return p['turbine_inlet_c'], p['turbine_inlet_bar'], p['condenser_bar']


def one_unit_in_6th_digit(text):
    x = float(text)
    return 10.0 ** (math.floor(math.log10(abs(x))) - 5)


def reference_binary():
    """thermo/sim.bin, if it is the build the fixtures were recorded from."""
    path = os.path.join(ROOT, 'thermo', 'sim.bin')
    if not os.path.isfile(path):
        pytest.skip('thermo/sim.bin not built')
    if u.file_digest(path) != FIXTURE['reference_executable']['sha256']:
        pytest.skip('thermo/sim.bin is not the reference build; covered by the candidate tests')
    return path


# --- fixtures: the reference build reproduces itself exactly ----------------------

@pytest.mark.parametrize('name, case', ACCEPTED, ids=[f"{n}-{c['label']}" for n, c in ACCEPTED])
def test_reference_build_reproduces_its_fixture_exactly(name, case):
    code, out, _ = run(reference_binary(), *conditions(name), repr(case['extraction_c']))
    assert code == 0
    assert out == case['stdout']


# --- fixtures: any fresh build of the current sources agrees ------------------------

@pytest.mark.parametrize('name, case', ACCEPTED, ids=[f"{n}-{c['label']}" for n, c in ACCEPTED])
def test_fresh_build_matches_the_fixture(sim_bin, name, case):
    code, out, _ = run(sim_bin, *conditions(name), repr(case['extraction_c']))
    assert code == 0
    for got, ref in zip(out.split(), case['stdout'].split()):
        assert abs(float(got) - float(ref)) <= one_unit_in_6th_digit(ref), (got, ref)


@pytest.mark.parametrize('name', PLANTS)
def test_fresh_build_reproduces_the_domain_limits(sim_bin, name):
    code, out, _ = run(sim_bin, '--limits', *conditions(name))
    assert code == 0
    for got, ref in zip(out.split(), PLANTS[name]['limits_stdout'].split()):
        assert float(got) == pytest.approx(float(ref), abs=1e-9)


@pytest.mark.parametrize('name, case', REFUSED, ids=[f"{n}-{c['label']}" for n, c in REFUSED])
def test_refusals_on_and_outside_the_domain(sim_bin, name, case):
    """Exactly on either limit, and 1 C outside, the executable refuses: status 3,
    nothing on stdout, the reason on stderr."""
    code, out, err = run(sim_bin, *conditions(name), case['extraction_c'])
    assert code == case['exit_status'] == 3
    assert out == ''
    assert case['stderr_contains'] in err


def test_python_boundary_parses_the_emitted_precision(sim_bin):
    """IES Optimiser uses the coefficients exactly as printed -- 6 significant digits."""
    ref = [c for c in PLANTS['nuclear']['accepted'] if c['extraction_c'] == 80][0]
    a, b, err = u.thermo(*conditions('nuclear'), 80, binary=sim_bin)
    assert err is False
    assert (a, b) == tuple(float(v) for v in ref['stdout'].split())


# --- independent physical checks ------------------------------------------------------

def test_saturation_temperatures_match_steam_tables(sim_bin):
    """IAPWS-IF97: Tsat(0.05 bar) = 32.88 C; Tsat(70 bar) = 285.83 C;
    Tsat(150 bar) = 342.16 C and Tsat(160 bar) = 347.36 C, which bracket 152 bar;
    Tsat(1 bar) = 99.61 C."""
    low, high = (float(v) for v in run(sim_bin, '--limits', *conditions('nuclear'))[1].split())
    assert low == pytest.approx(32.88, abs=0.05)
    assert high == pytest.approx(285.83, abs=0.05)
    _, high_152 = (float(v) for v in run(sim_bin, '--limits', *conditions('fossil'))[1].split())
    assert 342.16 < high_152 < 347.36
    low_1bar, _ = (float(v) for v in run(sim_bin, '--limits', 564, 152, 1.0)[1].split())
    assert low_1bar == pytest.approx(99.61, abs=0.05)


@pytest.mark.parametrize('name', PLANTS)
def test_forgone_electricity_rises_with_extraction_temperature(sim_bin, name):
    """Hotter steam has done less work in the turbine, so each unit of heat costs
    more electricity: a increases with extraction temperature. (b need not be
    monotone, and for the fossil turbine it is not.)"""
    temps = [c['extraction_c'] for c in PLANTS[name]['accepted']]
    a = [float(run(sim_bin, *conditions(name), repr(t))[1].split()[0]) for t in temps]
    assert all(x < y for x, y in zip(a, a[1:])), list(zip(temps, a))
    for t in temps:
        a_t, b_t = (float(v) for v in run(sim_bin, *conditions(name), repr(t))[1].split())
        assert 0 < a_t < 1 and b_t > 0 and a_t * b_t < 1


# --- the executable installed with the package ------------------------------------------
#
# Built by CMake with the reference build's flags (see CMakeLists.txt). On the
# platform the fixture was recorded on (macOS, arm64, Apple clang) it is held
# to the reference build's standard -- the fixture strings exactly -- and has
# been shown to meet it. On other platforms (another compiler and maths
# library) the Step 1 contract for other builds applies: one unit in the 6th
# significant digit. Limits and refusals are checked as recorded everywhere.

import platform

REFERENCE_PLATFORM = platform.system() == 'Darwin' and platform.machine() == 'arm64'

def packaged_binary():
    if not os.path.isfile(u.Thermo_bin):
        pytest.skip('IES Optimiser installed without its executable')
    return u.Thermo_bin


@pytest.mark.parametrize('name, case', ACCEPTED, ids=[f"{n}-{c['label']}" for n, c in ACCEPTED])
def test_packaged_build_reproduces_the_fixture(name, case):
    code, out, _ = run(packaged_binary(), *conditions(name), repr(case['extraction_c']))
    assert code == 0
    if REFERENCE_PLATFORM:
        assert out == case['stdout']
    for got, ref in zip(out.split(), case['stdout'].split()):
        assert abs(float(got) - float(ref)) <= one_unit_in_6th_digit(ref), (got, ref)


@pytest.mark.parametrize('name', PLANTS)
def test_packaged_build_reproduces_the_limits(name):
    code, out, _ = run(packaged_binary(), '--limits', *conditions(name))
    assert code == 0
    if REFERENCE_PLATFORM:
        assert out == PLANTS[name]['limits_stdout']
    for got, ref in zip(out.split(), PLANTS[name]['limits_stdout'].split()):
        assert float(got) == pytest.approx(float(ref), abs=1e-9)


@pytest.mark.parametrize('name, case', REFUSED, ids=[f"{n}-{c['label']}" for n, c in REFUSED])
def test_packaged_build_refuses_as_recorded(name, case):
    code, out, err = run(packaged_binary(), *conditions(name), case['extraction_c'])
    assert code == case['exit_status'] and out == '' and case['stderr_contains'] in err
