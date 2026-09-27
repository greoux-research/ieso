# IESO

IESO (*Integrated Energy Systems Optimiser*) is a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis. It sizes and dispatches generators, storage and Power-to-X processes (electrolysis, desalination, cogeneration heat) over a year of hourly steps, with OR-Tools' GLOP solver.

- [Modelling Approach](https://github.com/greoux-research/ieso/blob/main/docs/ieso-modelling-approach.md)
- [Setup Guide](https://github.com/greoux-research/ieso/blob/main/docs/ieso-setup-guide.md)
- [IO File Structure](https://github.com/greoux-research/ieso/blob/main/docs/ieso-io-file-structure.md)
- [Inputs, Validation and the Python API](https://github.com/greoux-research/ieso/blob/main/docs/ieso-api.md)
- [Supported Platforms](https://github.com/greoux-research/ieso/blob/main/docs/support-matrix.md)
- [Changelog](https://github.com/greoux-research/ieso/blob/main/CHANGELOG.md)
- [Baseline Verification](https://github.com/greoux-research/ieso/blob/main/docs/baseline-verification.md)

## Installation

IESO needs Python 3.11 or later, on Linux x86_64 (glibc 2.28+), macOS (Apple Silicon 11+, Intel 10.15+) or Windows x86_64. Wheels include the compiled thermodynamics executable; no compiler is needed.

IESO is **not yet published on PyPI**. When it is, it will install into a fresh virtual environment with:

```bash
python3 -m venv ieso-env
source ieso-env/bin/activate          # Windows: ieso-env\Scripts\activate
python -m pip install ieso
```

Until then, install a wheel built by the repository's CI, or from a checkout; see the [Setup Guide](https://github.com/greoux-research/ieso/blob/main/docs/ieso-setup-guide.md).

## Use

A synthetic demonstration case (a solar, gas and battery system; MIT-licensed, like the code) is in the repository's [`examples/`](https://github.com/greoux-research/ieso/tree/main/examples) folder, with a thermally coupled Power-to-X case beside it; `python tools/build_examples.py` regenerates both in a checkout. From a directory holding a copy of `examples/`:

<!-- tested -->
```bash
ieso validate examples/electricity-storage/case.json      # check without solving
ieso examples/electricity-storage/case.json carbon-constraint=150
# -> examples/electricity-storage/case.ieso.carbon-constraint_150.0.json
```

<!-- tested -->
```python
import ieso

result = ieso.solve('examples/power-to-x-thermal/case.json')
if result.optimal and result.accounting_ok:
    print(result.document['system']['cost'])               # USD per year
```

`ieso --help` lists the commands; `ieso schema input` prints the JSON Schema of an input.

## Licence and data

The code, the thermodynamics sources and the synthetic examples are under the MIT licence. The illustrative datasets in [`datasets/`](https://github.com/greoux-research/ieso/tree/main/datasets) are not part of the installed package: their hourly profiles are derived from Renewables.ninja and licensed CC BY-NC 4.0.

Report problems at https://github.com/greoux-research/ieso/issues.

## Repository

- **src/ieso** — the package: the API, the input and result models, their JSON Schemas, the command line, and the model; **thermo** — the C++ thermodynamics sources, built into the package by CMake; **ieso.py** — a launcher kept for the historical `python ieso.py ...` in a checkout.
- **examples** — the synthetic cases; **datasets** — four illustrative island cases (`tools/build_datasets.py`); **results** — the current verified results for them, with provenance.
- **tests** — the development suite; **tests_installed** — the tests CI runs against each built wheel, outside the checkout; **tools** — builders, the result comparator, distribution and native-executable checks, the scenario runner (writing to the ignored **runs** folder) and `product_costs.py` (IESO's product cost KPI is an allocation, not a production cost).

Every result carries a `provenance` block recording the code, the digests of the input and of each profile it references, the options applied, and the solver and environment that produced it, and a `system.checks` block recording whether its balances and accounts reconcile. Results are reproducible only against a recorded environment: a different solver build may settle on a different vertex of the same optimal face, so hourly dispatch and surplus can differ between equally optimal results.

## How to cite IESO

Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso
