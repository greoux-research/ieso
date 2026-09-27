# IES Optimiser

IES Optimiser (*Integrated Energy Systems Optimiser*) is a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis. It sizes and dispatches generators, storage and Power-to-X processes (electrolysis, desalination, cogeneration heat) over a year of hourly steps, with OR-Tools' GLOP solver.

- [Modelling Approach](https://github.com/greoux-research/ies-optimiser/blob/main/docs/ies-optimiser-modelling-approach.md)
- [Setup Guide](https://github.com/greoux-research/ies-optimiser/blob/main/docs/ies-optimiser-setup-guide.md)
- [IO File Structure](https://github.com/greoux-research/ies-optimiser/blob/main/docs/ies-optimiser-io-file-structure.md)
- [Inputs, Validation and the Python API](https://github.com/greoux-research/ies-optimiser/blob/main/docs/ies-optimiser-api.md)
- [Supported Platforms](https://github.com/greoux-research/ies-optimiser/blob/main/docs/support-matrix.md)
- [Changelog](https://github.com/greoux-research/ies-optimiser/blob/main/CHANGELOG.md)
- [Baseline Verification](https://github.com/greoux-research/ies-optimiser/blob/main/docs/baseline-verification.md)

## Installation

IES Optimiser needs Python 3.11 or later, on Linux x86_64 (glibc 2.28+), macOS (Apple Silicon 11+, Intel 10.15+) or Windows x86_64. Wheels include the compiled thermodynamics executable; no compiler is needed.

IES Optimiser is **not yet published on PyPI**. When it is, it will install into a fresh virtual environment with:

```bash
python3 -m venv ies-optimiser-env
source ies-optimiser-env/bin/activate          # Windows: ies-optimiser-env\Scripts\activate
python -m pip install ies-optimiser
```

Until then, install a wheel built by the repository's CI, or from a checkout; see the [Setup Guide](https://github.com/greoux-research/ies-optimiser/blob/main/docs/ies-optimiser-setup-guide.md).

## Use

A synthetic demonstration case (a solar, gas and battery system; MIT-licensed, like the code) is in the repository's [`examples/`](https://github.com/greoux-research/ies-optimiser/tree/main/examples) folder, with a thermally coupled Power-to-X case beside it; `python tools/build_examples.py` regenerates both in a checkout. From a directory holding a copy of `examples/`:

<!-- tested -->
```bash
ies-optimiser validate examples/electricity-storage/case.json      # check without solving
ies-optimiser examples/electricity-storage/case.json carbon-constraint=150
# -> examples/electricity-storage/case.ies-optimiser.carbon-constraint_150.0.json
```

<!-- tested -->
```python
import ies_optimiser

result = ies_optimiser.solve('examples/power-to-x-thermal/case.json')
if result.optimal and result.accounting_ok:
    print(result.document['system']['cost'])               # USD per year
```

`ies-optimiser --help` lists the commands; `ies-optimiser schema input` prints the JSON Schema of an input.

## Licence and data

The code, the thermodynamics sources and the synthetic examples are under the MIT licence. The illustrative datasets in [`datasets/`](https://github.com/greoux-research/ies-optimiser/tree/main/datasets) are not part of the installed package: their hourly profiles are derived from Renewables.ninja and licensed CC BY-NC 4.0.

Report problems at https://github.com/greoux-research/ies-optimiser/issues.

## Repository

- **src/ies_optimiser** — the package: the API, the input and result models, their JSON Schemas, the command line, and the model; **thermo** — the C++ thermodynamics sources, built into the package by CMake; **ies_optimiser.py** — a launcher for `python ies_optimiser.py ...` in a checkout.
- **examples** — the synthetic cases; **datasets** — four illustrative island cases (`tools/build_datasets.py`); **results** — the current verified results for them, with provenance.
- **tests** — the development suite; **tests_installed** — the tests CI runs against each built wheel, outside the checkout; **tools** — builders, the result comparator, distribution and native-executable checks, the scenario runner (writing to the ignored **runs** folder) and `product_costs.py` (IES Optimiser's product cost KPI is an allocation, not a production cost).

Every result carries a `provenance` block recording the code, the digests of the input and of each profile it references, the options applied, and the solver and environment that produced it, and a `system.checks` block recording whether its balances and accounts reconcile. Results are reproducible only against a recorded environment: a different solver build may settle on a different vertex of the same optimal face, so hourly dispatch and surplus can differ between equally optimal results.

## How to cite IES Optimiser

Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser
