# IES Optimiser Inputs, Validation and the Python API

This page is for people, scripts and AI assistants that prepare IES Optimiser cases,
check them and run them. The field-by-field meaning of inputs and results is in
the [IO File Structure](ies-optimiser-io-file-structure.md); the modelling is in the
[Modelling Approach](ies-optimiser-modelling-approach.md).

---

#### Commands

The command is `ies-optimiser`, installed with the package (`python -m ies_optimiser` is the same; in a source checkout, so is `python ies_optimiser.py`).

```bash
ies-optimiser CASE.json [name=value ...] [--profile-base DIR]            # solve (unchanged)
ies-optimiser validate CASE.json [name=value ...] [--profile-base DIR] [--json]
ies-optimiser schema input
ies-optimiser schema result
ies-optimiser --help
ies-optimiser --version
```

- **validate** checks a case completely and writes nothing. It never builds or solves the problem. It checks, in order:
  - the file and the options;
  - the structure;
  - the semantic rules (identifiers, references, topology, profiles and hourly shortfall bounds). Profiles are resolved exactly as a solve resolves them, then read.
  - Finally, for every generator that supplies heat to a process, it runs the thermodynamics executable (`thermo/sim.bin`) to obtain the cogeneration coefficients. It runs this stage only when a case has such a unit.

  It exits 0 when the case is valid and 1 when it is not. With `--json`, stdout holds exactly one JSON document. Logs and anything else go to stderr.
- **schema** prints the JSON Schema of the canonical input or of a result. It needs no case and no thermodynamics executable.
- A first argument that is exactly `validate` or `schema` selects that command; anything else is the solve form's input file. `--profile-base` behaves identically in both solve and validate (see [Profiles](#profiles)).

`validate --json` prints:

```json
{
  "command": "validate",
  "input": "case.json",
  "valid": false,
  "format": "canonical",
  "stages": {"file": "passed", "options": "passed", "structure": "failed",
             "semantics": "not run", "thermodynamics": "not run"},
  "diagnostics": [
    {"code": "value.out_of_range", "layer": "structure", "message": "'capacity_factor' must be <= 1.0, got 2",
     "path": "/generator/0/capacity_factor", "entity": "wind", "field": "capacity_factor", "hour": null}
  ],
  "removed_fields": [],
  "profile_resolution": {"mode": "input-directory", "base": "/abs/dir"}
}
```

---

#### Input formats: canonical and legacy

| | Canonical (format 1) | Legacy |
|---|---|---|
| Recognised by | `"format_version": 1` | no `format_version` |
| Holds | inputs only | inputs plus output placeholders |
| Validated by | the input schema and IES Optimiser | IES Optimiser, after its compatibility adapter |

- **The legacy adapter** (`ies_optimiser.formats`, `LEGACY_OUTPUT_FIELDS`) removes exactly these output-only fields and nothing else:
  - `solver` and `provenance`;
  - on demands: `output_ns`, `shadow_prices` and `kpis`;
  - on generators: `e_prod`, `h_prod`, `a` and `b`;
  - on stores: `e_strg`, `e_char`, `e_disc` and `e_spil`;
  - on processes: `x_prod`, `x_strg`, `x_supp` and `shadow_prices`.
- **Conditions on those fields:**
  - Output arrays must be empty.
  - Placeholder objects must be objects.
  - An array that holds values, or a field found only in results (`system`, `accounts`, `surplus`, `availability`, `heat_surplus`), means a result was given as an input. It is refused with the code `input.is_result`.
- **Any other unknown field** is not removed: it is refused.
- **Input values are unchanged,** numeric types included: an integer stays an integer.
- **Unsupported versions:** any `format_version` other than the integer 1 is refused with the code `format.unsupported_version`.

The bundled datasets are legacy documents and are read as they are. To convert any case into the canonical form, with every default written out:

```python
import ies_optimiser
canonical = ies_optimiser.to_canonical(ies_optimiser.load_input('datasets/elec-grid/elec-grid.json'))
```

A case gives the same result in either format. Only `provenance.input_format` differs.

---

#### Values: absent, null, empty, zero

| Written | Meaning |
|---|---|
| field absent | the documented default (listed in the schema), written into the model's copy. Fields with no default can be absent only where the schema says so: `inflow_profile` (flat), and `var_cost_ns` / `l_ns` of an inactive commodity demand |
| `null` | refused everywhere (`value.null`); omit the field instead |
| `""` profile | a flat profile |
| `[]` | no sources (`supply_sources`); not applicable (`l_ns` of an inactive demand only) |
| `0` | itself. A demand `total` of 0 makes a commodity demand inactive; a capacity of 0 builds nothing; `var_cost_ns` 0 makes a shortfall free |
| `-1` capacity | chosen by the optimiser (`-1.0` is the same) |

- **Numbers:** they must be JSON numbers. Integers are accepted wherever a real value is. Strings, booleans, `NaN` and infinities are refused.
- **Negative values accepted:**
  - emission factors (removal);
  - costs (subsidies);
  - a carbon cap (`carbon-constraint`, which then requires net removal).
- **Units** are stated in each field's description in the schema and the models. For example, `fix_cost_prod` is in USD per MW per year for a generator.

<a id="profiles"></a>
**Profiles.** A profile takes one of three forms:

- `""` for a flat profile;
- a CSV path (one value per line, no header);
- a list of 8760 numbers. A one-dimensional NumPy array is also accepted from Python.

A relative path resolves against the input file's directory, or against `--profile-base` / `RunConfig(profile_base=...)` if given. It never resolves against the working directory.

---

#### Validation layers

Each rule has one owner. A valid case may still be **infeasible**: that is a solver status, not an input error.

| Layer | Owner | Rules |
|---|---|---|
| `file` | `api.load_input` | the file can be read and parsed as JSON |
| `format` | `formats` | `format_version`, the legacy adapter |
| `structure` | `models` (Pydantic) | types, required and unknown fields, allowed values, finite numbers, ranges, and rules within one object (`soc_min <= soc_ini <= soc_max`, heat use only on `elec + ther`, `temperature` required for `elec + ther`, `var_cost_ns` / `l_ns` required on an active demand) |
| `semantics` | `chk` | unique identifiers; demands name existing processes; a process supplies at most one active demand; heat sources exist, are cogeneration units with turbine data, and supply one process each; `l_ns[0]` at most the demand of every hour |
| `profiles` | `chk` / `fcn.as_profile` | the file exists where the rule places it, and it holds exactly 8760 finite, non-negative values, not all zero |
| `thermodynamics` | `chk.cogeneration` | admissible coefficients from `thermo/sim.bin` (`0 < a < 1`, `b > 0`, `a*b < 1`) |
| `options` | `models.SolveOptions` | recognised names, finite values, `non-served-power-constraint` in [0, 1] |
| `configuration` | `api`, `cli` | flags, `profile_base` is a directory, `source=` agrees with the case path |

Structure reports every problem it finds; later layers stop at the first.

---

#### Diagnostics

Every refusal is an `ies_optimiser.IesOptimiserError` holding `diagnostics`, a list of `Diagnostic` records. Each record has these fields:

- `code`: stable; this is the contract, while messages may be reworded;
- `layer`;
- `message`;
- `path`: a JSON Pointer into the case, using the serialised names, e.g. `/demand/x/1/l_ns`. It is `null` when the problem is not in the case;
- `entity`: an identifier, `demand.e`, `demand.x[water]`, `input` or `command line`;
- `field`;
- `hour`: **zero-based** (0 is the first hour of the year). It is set for hourly checks and for elements of inline profiles.

| Code | Meaning |
|---|---|
| `input.unreadable` | the file cannot be read or is not JSON |
| `input.is_result` | a result was given as an input |
| `format.unsupported_version` | `format_version` is not 1 |
| `field.missing`, `field.unknown` | a required field is absent; a field is not part of the format |
| `value.null`, `value.type`, `value.not_finite`, `value.out_of_range`, `value.not_allowed`, `value.empty`, `value.length`, `value.inconsistent` | a malformed value |
| `identifier.duplicate`, `reference.unknown` | identifiers and references |
| `topology.process_shared`, `topology.no_heat_source`, `topology.not_cogeneration`, `topology.heat_shared`, `cogeneration.parameters` | ownership and thermal topology |
| `shortfall.exceeds_demand` | `l_ns[0]` above the demand of an hour (`hour` set) |
| `profile.not_found`, `profile.unresolvable`, `profile.unreadable`, `profile.type`, `profile.dimensions`, `profile.length`, `profile.not_finite`, `profile.negative`, `profile.zero_sum` | profiles |
| `thermo.failed` | no admissible cogeneration coefficients (`ThermoError`) |
| `option.syntax`, `option.unknown`, `option.repeated` | run options on the command line |
| `flag.unknown`, `flag.value`, `flag.repeated`, `command.usage`, `config.conflict`, `config.profile_base`, `config.invalid` | command line and configuration |

---

#### Python

The example uses the synthetic cases in the repository's `examples/` directory; it is run by the installed-artifact tests.

<!-- tested -->
```python
import ies_optimiser

path = 'examples/power-to-x-thermal/case.json'
report = ies_optimiser.validate(path)                   # a ValidationReport; never raises for a bad case
if not report.valid:
    for d in report.diagnostics:
        print(d.code, d.path, d.hour, d.message)

try:
    result = ies_optimiser.solve(path, options={'carbon-constraint': 100.0})
except ies_optimiser.IesOptimiserError as e:                    # InputError or ThermoError; nothing was solved
    print([d.to_dict() for d in e.diagnostics])
else:
    if not result.optimal:
        print('no optimal solution:', result.status)       # infeasible, unbounded, ...
    elif not result.accounting_ok:
        print('accounting check failed:', result.document['system']['checks'])
    else:
        print(result.document['system']['cost'])            # USD per year
    ies_optimiser.write_result(result, ies_optimiser.output_path(path, {'carbon-constraint': 100.0}))
```

- **Passing a case:** `solve`, `validate`, `parse_case` and `to_canonical` accept any of these:
  - a path;
  - a parsed document, in either format;
  - a `models.Case`.

  Pass the path, or `source=`, so that relative profile paths can be resolved.
- **Building a case in Python:** the models (`Case`, `Demand`, `ElectricityDemand`, `CommodityDemand`, `Generator`, `Storage`, `Process`, `SolveOptions`) accept the serialised names or descriptive Python names, such as `Generator(identifier='ocgt', fixed_cost=75182, ...)`. They are frozen, so they cannot be modified after creation.
- **Per-run settings:** `config=ies_optimiser.RunConfig(...)` sets the horizon, storage closure, thermodynamics executable and timeout, and profile base for one run. They are checked when the `RunConfig` is created (a positive integer horizon, a real bool, a finite positive timeout, paths as strings or path-like objects); anything else raises `InputError` with code `config.invalid` and layer `configuration`.
- **Side effects:**
  - Importing a module does nothing.
  - No function modifies the case it is given, including nested lists, dicts and arrays.
  - Nothing is written except by `write_result`.
  - Diagnostics go to the `ies_optimiser` logger; the library configures no logging.
  - Repeated solves are independent.
  - Thread safety has not been established.
- **Outcomes stay distinguishable:**
  - An invalid input, a missing profile or a thermodynamics failure raises an exception, and nothing is solved.
  - Infeasibility is `result.optimal == False` with a status, and the command line exits 1 after writing the result.
  - An accounting failure is `result.accounting_ok == False`, and the command line exits 3.

---

#### Results

- **Two shapes,** described by the result schema (`ies-optimiser schema result`; shipped as `ies_optimiser/data/ies-optimiser-result-1.schema.json`):
  - **Optimal** (`solver.stat_succ` 1): inputs, hourly and annual results, `system` totals and checks.
  - **Unsuccessful** (`stat_succ` 0): inputs, solver status and provenance only. No result field and no placeholder is present, so an unavailable output cannot be read as a number.
- **Version and format:** every result records `provenance.result_format_version` (1) and `provenance.input_format`.
- **Sentinels kept for compatibility:**
  - `kpis` values are -1 where not applicable.
  - `carbon_cap` / `reliability_cap` are -1 when that option was not given.
  - `null` marks undefined allocations when there is no output at all.

Three conventions matter when reading results:

- **Allocated cost is not product cost.**
  - `kpis.cost` and `accounts.resource_cost` allocate the whole system cost, including the processes' own plant, to demands in proportion to electricity-equivalent use. This is a convention, not a measurement.
  - `tools/product_costs.py` costs a product directly instead: its plant plus its electricity and heat valued at the hourly `demand_marginal`.
  - Neither is a tariff.
- **Surplus is not curtailment.**
  - `surplus` (on demands) and `heat_surplus` (on processes) are the hourly residuals of balance inequalities: supply beyond what was used. Its cost and emissions are reported as unallocated in `system`.
  - IES Optimiser does not report curtailment of renewable availability as such. Availability minus dispatch can be computed from `e_prod` and the availability profile.
- **Duals are marginal values, not prices paid.**
  - `demand_match` is the balance-row dual, with every bound held fixed.
  - `demand_marginal` adds the reduced cost where unmet demand sits at a bound set by demand. It is a subgradient: exact except at breakpoints, where it is one valid value among several.
  - The carbon and reliability cap values are the duals of those caps, with `*_detail` records of what was observed.

---

#### Schemas

The input and result schemas are shipped in the package (`ies_optimiser/data/ies-optimiser-input-1.schema.json`, `ies_optimiser/data/ies-optimiser-result-1.schema.json`; `ies_optimiser.schemas.path(kind)` gives their location, `ies-optimiser schema input|result` prints them). They are generated from the models; do not edit them. In a checkout, regenerate them with:

```bash
python tools/generate_schemas.py            # --check only compares
```

A test fails if they differ from the models. They describe **structure only**: identifiers, references, topology, profile contents and lengths, hourly bounds and thermodynamics are checked by IES Optimiser (`ies-optimiser validate`).
