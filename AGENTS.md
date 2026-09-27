# AGENTS.md — guide for coding assistants working on IESO

IESO is a linear energy-system optimiser (OR-Tools GLOP, 8760 hourly steps) with a small C++ thermodynamics executable. Read `docs/ieso-modelling-approach.md` before touching equations, and `docs/ieso-api.md` before touching inputs, validation or results.

## Layout and public API

- `src/ieso/` is the package. Public: `ieso` (`__init__.py` exports `solve`, `validate`, `load_input`, `parse_case`, `to_canonical`, `write_result`, `output_path`, `check_options`, `RunConfig`, the errors and the models), `ieso.api`, `ieso.models` (input models), `ieso.results` (result models), `ieso.errors` (`Diagnostic`, `InputError`, `ThermoError`), `ieso.schemas`, `ieso.cli`. Internal: `chk` (semantic validation), `fcn`, `formats`, `eqs_*`, `obj`, `opt`, `pos`, `pos_dmd`, `_install`.
- `thermo/*.cpp` + `CMakeLists.txt` build `ieso/_bin/ieso-thermo`; `pyproject.toml` holds metadata, scikit-build-core, cibuildwheel, pytest and mypy configuration.
- `tests/` development suite; `tests_installed/` tests run against an installed wheel; `examples/` synthetic cases; `datasets/` CC BY-NC data (never packaged); `results/` stored reference results (never overwrite).

## Commands

```bash
python -m pip install -e ".[dev]"          # editable install; builds the executable (C++ compiler needed)
python -m pytest                           # development suite
python -m pytest tests_installed           # installed-artifact tests
python -m mypy                             # public-boundary type check
python -m build                            # sdist + wheel into dist/
python tools/check_dist.py dist/*          # artifact contents
python tools/inspect_native.py dist/*.whl  # executable dependencies, tag, minimum OS
```

Regenerate, never hand-edit: `python tools/generate_schemas.py` (after changing `models.py`/`results.py`), `python tools/build_examples.py` (examples), `python tools/build_datasets.py` (datasets). `python tools/build_examples.py --record-expected` rewrites `examples/expected.json` and belongs only to the reference environment.

## Invariants to preserve

- The formulation is continuous and linear. Do not add integer variables, tie-breaking costs or heuristics, and do not change equations, input numerical values, solver settings or profile conventions as a side effect of other work.
- Demand balances are inequalities; surplus is reported, not forbidden. Storage closes the year at `soc_ini`. `-1` capacity means "optimise". `l_ns` bounds unmet demand in each hour, capped by that hour's demand.
- Profiles supply shape only (rescaled to `capacity_factor` or `total`); relative profile paths resolve against the input file's directory or an explicit `--profile-base`, never the working directory.
- The thermodynamics executable prints six significant digits; its domain checks, exit codes and the Python timeout are part of the contract. Cogeneration requires `0 < a < 1`, `b > 0`, `a*b < 1`.
- Input models are the only structural validator; semantic rules live in `chk.py`. Diagnostics codes and JSON Pointer paths are public contract; hours are zero-based.
- Importing `ieso` has no side effects; the API never mutates its inputs and writes nothing except through `write_result`.

## Conventions when reading results

- Units: power MW, energy MWh, product quantities in their own unit (m³, kg, MWh heat); costs USD, emissions kg CO₂eq.
- `kpis.cost` and `accounts.resource_cost` allocate the whole system cost by electricity-equivalent use: a convention, not a production cost (`tools/product_costs.py` costs products directly).
- `surplus`/`heat_surplus` are balance residuals; IESO does not report curtailment as such.
- `demand_match` and `demand_marginal` are dual values (subgradients at breakpoints), not prices paid. Different equally optimal dispatches are legitimate across solver builds.

## Releases

Published only by `.github/workflows/release.yml` (tag `v<version>`, Trusted Publishing, TestPyPI then approved PyPI); see `docs/releasing.md`. Never upload by hand, reuse a version, or publish artifacts other than those the run tested.

## Numerical verification

Any change that can affect results is checked against the Step 1 comparison contract in `docs/baseline-verification.md`: the same environment must be IDENTICAL under `tools/compare_outputs.py`; across environments: optimal, accounting_ok, independent invariants (`tools/check_invariants.py`), identical problem size, objective within 1e-10 relative, capacities within 1e-6 + 1e-7 relative, emissions within 1e-9 relative where the carbon cap binds, cogeneration coefficients within one unit in the sixth significant digit. Run the bundled configurations with `tools/run_cases.sh` into a new `runs/` directory. Never widen tolerances, weaken assertions or overwrite `results/` to make a check pass; record every verification in `docs/baseline-verification.md`.
