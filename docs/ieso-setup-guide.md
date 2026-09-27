# IESO Setup Guide

#### Introduction

This article provides a guide on how to set up and run the [Integrated Energy Systems Optimiser](https://github.com/greoux-research/ieso) (IESO), a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

IESO's modelling approach is described in [this article](ieso-modelling-approach.md). Its IO file structure is documented [at this link](ieso-io-file-structure.md).

IESO is a Python package, `ieso`, with a small C++ thermodynamics executable built into it. It needs Python 3.11 or later and installs three libraries with it: [OR-Tools](https://developers.google.com/optimization/install) (the GLOP solver), [NumPy](https://numpy.org/install/) and [Pydantic](https://docs.pydantic.dev/) 2 (input validation and JSON Schemas). The platforms and Python versions it is built and tested for are listed in [Supported Platforms](support-matrix.md).

**IESO is not yet published on a package index**: `pip install ieso` does not install it. Install it from a wheel file, or from a source checkout, as below.

The solver build matters: GLOP may settle on a different vertex of the same optimal face from one version to another, so a result is reproducible only against a recorded environment. Every result records its own — see `provenance` in the output.

---

#### Installing from a wheel

A wheel (`ieso-<version>-py3-none-<platform>.whl`) holds the package and the compiled thermodynamics executable for one platform; it needs no compiler, no Git and no source checkout. Wheels are built by the repository's CI (`.github/workflows/wheels.yml`, kept as downloadable artifacts) or locally (see [Building distributions](#building-distributions)).

```bash
python3 -m venv ieso-env
source ieso-env/bin/activate            # Windows: ieso-env\Scripts\activate
python -m pip install ./ieso-2026.9.0-py3-none-macosx_11_0_arm64.whl
ieso --version
```

pip installs the wheel's dependencies from PyPI. Use the wheel built for your platform; pip refuses one that is not.

---

#### Installing for development

From a source checkout (fetched [from GitHub](https://github.com/greoux-research/ieso)), an editable install builds the thermodynamics executable once and imports the package from `src/ieso`, so Python changes take effect immediately. It needs a C++ compiler (Xcode Command Line Tools on macOS: `xcode-select --install`; `build-essential` on Ubuntu; Visual Studio Build Tools with the C++ workload on Windows). CMake, Ninja and scikit-build-core are fetched by pip into an isolated build environment.

```bash
cd /path/to/ieso
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"       # pytest, jsonschema, mypy, build
```

After a change to `thermo/*.cpp`, run the install command again to rebuild the executable. The historical invocation, `python ieso.py ...`, still works in a checkout: `ieso.py` is a launcher for the installed package (it is not the package, and refuses to be imported as one).

**The thermodynamics executable** (`ieso/_bin/ieso-thermo`, `ieso-thermo.exe` on Windows) derives the cogeneration coefficients *a* and *b* from turbine and condenser conditions. It is used **only for thermally coupled cases** — a process declared as `elec + ther`, such as MED desalination. It is built into every wheel and found through the package itself, never the working directory; `RunConfig(thermo_bin=...)` overrides it for a run, and provenance records which one ran. `thermo/build.sh` (`build.bat` on Windows) still builds the standalone `thermo/sim.bin` that the reference evidence was recorded with; the package does not use it.

---

#### Running an IESO simulation

IESO takes one mandatory argument and any number of options:

1. The first argument is a [JSON](https://en.wikipedia.org/wiki/JSON) file (referred to as `input.json`) describing the integrated energy system optimisation problem.
2. Any further arguments are `name=value` options. Two are recognised:
   - `carbon-constraint` — an emissions budget in kg CO₂eq per MWh of **primary annual electricity demand**. The budget is that figure multiplied by `demand.e.total`; it is not a limit on the emission intensity of generation, and the electricity consumed by Power-to-X processes does not enlarge it. Any finite value, including a negative (net-removal) target.
   - `non-served-power-constraint` — an upper bound on annual unserved **electricity**, as a fraction of `demand.e.total`, in `[0, 1]`. `0.05` means 5%. It *permits* shortfall up to that share; it does not require any. There is no equivalent annual bound for the other commodities — see `l_ns` in the [IO file structure](ieso-io-file-structure.md).

   Options are checked before the input is read. An unknown name (`carbon-contraint=50`), an argument without `=` (`carbon-constraint 50`), a missing or non-numeric value, NaN or infinity, a value outside its range, or an option given twice is refused: IESO prints the reason and exits with status 1 without solving or writing anything. A misspelt option used to be accepted and ignored, silently removing the constraint it named.

The output is written beside the input as `input.ieso.json` (only the file name's final `.json` is replaced, so directory names are left alone), with one `.name_value` segment appended for each option in the order given, and is structured identically to the input with the results filled in. **The output path is derived from the input path**, so running a case whose input sits in `datasets/` writes its result into that dataset's directory. Nothing is ever written inside the installed package. To keep results out of the datasets, copy the input into a working directory first, or use `tools/run_cases.sh`, which copies each input into a run directory under the ignored `runs/` folder.

A run that does not reach an optimal solution still writes a file, with the input values echoed back, `solver.stat_succ` at 0 and `solver.stat_status` naming the reason. Check the status before reading a result.

Exit status:

| Status | Meaning | Result file |
|---|---|---|
| 0 | optimal, and every accounting check in `system.checks` passed | written |
| 1 | input or options refused (the reason is printed), or no optimal solution | written only in the second case |
| 3 | optimal, but an accounting check failed (`system.accounting_ok` is false) | written; do not use it until the failure is understood |

**Profile paths.** A relative profile path in an input resolves against the directory of that input file — not the working directory — so a case directory holding its JSON and CSVs can be moved or copied and run from anywhere. Absolute paths are used as written; empty and inline profiles are unaffected. A file that is not where this rule places it is an error naming the field, the declared path and the location looked at; no other location is tried. The thermodynamics executable is always the one installed with the package, wherever IESO is run from.

**Older inputs** written with paths relative to some other directory — the bundled datasets before 26 September 2026 used paths relative to the repository root, such as `datasets/elec-grid/dmnd.csv` — run unchanged by naming that directory explicitly:

```bash
ieso path/to/old-case.json --profile-base /path/to/ieso
```

`--profile-base DIR` (or `--profile-base=DIR`; a relative `DIR` is taken from the current directory) replaces the input file's directory as the base for relative profile paths. It is not a model option: it does not enter the result's file name, and it is recorded in the result's provenance. From Python, pass `config=RunConfig(profile_base=DIR)`.

The command is `ieso` (or `python -m ieso`). With the environment active, from a checkout (the paths below are the repository's synthetic examples):

<!-- tested -->
```bash
ieso --version
ieso validate examples/power-to-x-thermal/case.json
ieso examples/electricity-storage/case.json
ieso examples/electricity-storage/case.json carbon-constraint=150 non-served-power-constraint=0.05
python -m ieso schema input
```

`ieso validate` runs every check a solve runs before building the problem — including reading the profiles and, for units that supply heat, running the thermodynamics executable — writes nothing, and with `--json` prints one JSON document with structured diagnostics. `ieso schema input|result` prints a JSON Schema. [Inputs, Validation and the Python API](ieso-api.md) describes the input formats, the diagnostics and the Python API.

To re-solve the bundled datasets into a separate run directory, with the IESO installed in a given Python, and compare a result with the current verified one:

```bash
PYTHON=/path/to/venv/bin/python tools/run_cases.sh runs/mycheck
tools/compare_outputs.py runs/mycheck/med-base.ieso.json results/elec-grid-2026-09-26/med-base.ieso.json
```

The current verified results, with provenance, are under `results/`. The
pre-correction results they were verified against are kept in Git history,
not in the checkout; [Baseline Verification](baseline-verification.md#where-the-historical-results-are)
gives the commit, their checksums and the `git show` command that retrieves
them. Compare against one with `--legacy`.

---

#### Using IESO from Python

```python
import ieso

report = ieso.validate('examples/electricity-storage/case.json')   # nothing solved, nothing written
try:
    result = ieso.solve('examples/electricity-storage/case.json', options={'carbon-constraint': 150.0})
except ieso.IesoError as e:                     # refused (InputError, ThermoError); nothing was solved
    raise SystemExit(str(e))
if result.optimal and result.accounting_ok:
    print(result.document['system']['cost'])    # USD per year
```

The API, its guarantees (no side effects on import, inputs never modified, nothing written unless asked) and its error handling are described in [Inputs, Validation and the Python API](ieso-api.md).

---

#### Running the tests

In a development install (`pip install -e ".[dev]"`):

```bash
python -m pytest                      # the development suite (tests/)
python -m mypy                        # type check of the public boundary (configured in pyproject.toml)
python -m pytest tests_installed      # the installed-artifact tests, against whatever ieso is installed
```

The development suite uses short horizons and expected values derived by hand, and touches no network; the thermodynamics tests also compile `thermo/*.cpp` with the C++ compiler on `PATH` (skipped, and said so, without one). `tests_installed/` is what CI runs against each built wheel, outside the checkout: the synthetic examples at their full 8760-hour horizon, compared with `examples/expected.json` under the [comparison contract](baseline-verification.md), the thermodynamics fixtures, the entry points and the documented examples.

Generated files are never edited by hand; regenerate them after changing their source (a test fails while they differ):

```bash
python tools/generate_schemas.py      # src/ieso/data/*.schema.json, from src/ieso/models.py and results.py
python tools/build_examples.py        # examples/, from the formulas in the script
python tools/build_examples.py --record-expected   # examples/expected.json, in the reference environment only
```

To re-solve the eight bundled configurations and compare them against another set of results:

```bash
PYTHON=/path/to/python tools/run_cases.sh runs/mycheck
tools/compare_outputs.py runs/mycheck/eg-base.ieso.json runs/previous/eg-base.ieso.json
```

`compare_outputs.py` compares every field both results carry, requires what a result must carry, and lists what it excludes. Against the pre-correction results kept in Git history, add `--legacy`: fields those results predate are listed as not compared rather than skipped silently.

---

#### Building distributions

```bash
python -m pip install build
python -m build                        # dist/ieso-<version>.tar.gz, then a wheel built from it
python tools/check_dist.py dist/*      # the artifacts hold exactly what they should
python tools/inspect_native.py dist/*.whl   # the executable's platform, dependencies and minimum OS
```

A wheel is `py3-none-<platform>`: one per platform, for every supported Python. Building one needs a C++ compiler; CMake and Ninja come from PyPI. Cross-platform wheels are built by `.github/workflows/wheels.yml` with cibuildwheel, configured in `pyproject.toml` (`[tool.cibuildwheel]`); see [Supported Platforms](support-matrix.md).

---

#### Licensing

IESO's code, including the thermodynamics sources and the synthetic examples in `examples/`, is under the MIT licence (`LICENSE`), and is what the wheel and the source distribution contain. The datasets in `datasets/` are not distributed in either: their hourly profiles are derived from Renewables.ninja and licensed **CC BY-NC 4.0** (non-commercial; see `datasets/README.md`). They remain in the repository for the verification evidence.
