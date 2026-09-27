# Changelog

## 2026.9.0 — first packaged release (in preparation)

The first release installable with pip. Versions now follow the calendar scheme `YEAR.MONTH.PATCH` (earlier tags: `v26.05`, `v25.10`); release candidates are `2026.9.0rcN`.

### Installation and interface
- IES Optimiser is a Python package, `ies_optimiser` (Python 3.11 or later), with an `ies-optimiser` command (`python -m ies_optimiser` is the same). Wheels for Linux x86_64 (manylinux_2_28), macOS arm64 and x86_64, and Windows x86_64 include the compiled thermodynamics executable; see [Supported Platforms](docs/support-matrix.md).
- An import-safe Python API: `ies_optimiser.solve`, `ies_optimiser.validate`, `ies_optimiser.load_input`, `ies_optimiser.parse_case`, `ies_optimiser.to_canonical`, `ies_optimiser.write_result`. Importing has no side effects, inputs are never modified, nothing is written unless asked, and refusals are exceptions (`InputError`, `ThermoError`) rather than exits.
- `ies-optimiser validate CASE.json [--json]` checks a case completely without solving it; `ies-optimiser schema input|result` prints JSON Schemas generated from typed input and result models.
- Refusals carry structured diagnostics: a stable code, a JSON Pointer path, the entity, the field and a zero-based hour.

### Model and results (since v26.05)
- Unmet demand is bounded by each hour's demand; capacity bounds and operating bounds are separate; output is held to nameplate where a rescaled profile exceeds one.
- Thermal topologies the formulation cannot represent are refused; dispatched heat is attributed; cost components are separated; caps are one-sided.
- Results report surplus explicitly, accounting checks (`system.checks`, `accounting_ok`) and provenance identifying the code, the executable, the inputs and profiles consumed, and the environment.
- The bundled illustrative cases were rebuilt as four self-contained island datasets.

### Compatibility changes
- **Project rename**: `ieso` becomes `ies-optimiser` on GitHub and in distribution metadata and the CLI; Python imports use `ies_optimiser`. The base exception is `IesOptimiserError`. New output files use `.ies-optimiser.json`, provenance uses `ies_optimiser_version` and Git scope `ies_optimiser`, and schema annotations use `x-ies-optimiser-format`. Existing input values and the optimisation formulation are unchanged. Historical result files, verification records and previously built artifacts retain their original names.
- **Profile paths** resolve against the input file's own directory, never the working directory. Inputs written with paths relative to another directory run unchanged with `--profile-base DIR` (`RunConfig(profile_base=...)` in Python).
- **Input formats**: canonical inputs carry `"format_version": 1` and hold inputs only. Unversioned (legacy) inputs are still read: their documented output placeholders are removed. Unknown fields are now refused rather than ignored, and a result given as an input is refused.
- **Results of unsuccessful solves** hold the inputs, the solver status and provenance only (no output placeholders). Provenance gains `installation`, `thermo_binary_origin`, `input_format`, `result_format_version`, and `case_sha256` with `source_matches_case`, which identify the case actually solved when it differs from its source file.
- **`RunConfig`** checks its fields when created and raises `InputError` (`config.invalid`) for a malformed setting — for instance `storage_closes_the_year='false'`, which used to read as true.
- **Command**: `ies-optimiser ...` replaces `python ies_optimiser.py ...`; in a source checkout `python ies_optimiser.py` still works as a launcher for the installed package.
- **Thermodynamics executable**: installed with the package (`ies_optimiser/_bin/ies-optimiser-thermo`) instead of being built by hand in `thermo/`.
- Numerical results of the bundled configurations are unchanged by the packaging work: identical to the stored reference results under the project's comparison contract ([Baseline Verification](docs/baseline-verification.md)).

### Known limitations
- Linux on ARM, Windows on ARM, musl Linux, 32-bit platforms and free-threaded Python are not supported.
- Equally optimal solutions can differ in hourly dispatch between solver builds and platforms; objective, capacities and accounts are what is held fixed.
- The illustrative datasets (CC BY-NC 4.0 profiles) and the synthetic examples are in the repository, not in the installed package.
- Concurrent solves in one process are untested.

Report issues at https://github.com/greoux-research/ies-optimiser/issues.
