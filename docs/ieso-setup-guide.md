# IESO Setup Guide

#### Introduction

This article provides a guide on how to set up and run the [Integrated Energy Systems Optimiser](https://github.com/greoux-research/ieso) (IESO), a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

IESO's modelling approach is described in [this article](ieso-modelling-approach.md). Its IO file structure is documented [at this link](ieso-io-file-structure.md).

IESO is implemented in Python 3 and doesn't require direct installation itself. It relies on two external libraries, [OR-Tools](https://developers.google.com/optimization/install) and [NumPy](https://numpy.org/install/), which need to be pre-installed. [pytest](https://docs.pytest.org/) is needed only to run the test suite.

The current release is verified on Python 3.14.4 with NumPy 2.5.2 and OR-Tools 9.15.6755. Earlier Python 3 versions are expected to work but are not exercised. The solver build matters: GLOP may settle on a different vertex of the same optimal face from one version to another, so a result is reproducible only against a recorded environment. Every result records its own — see `provenance` in the output.

---

#### Creating a virtual environment for IESO

We highly recommend creating a virtual environment for IESO to isolate project dependencies and avoid conflicts with other Python projects on your system.

**macOS and Ubuntu Linux**

1. On macOS, the `python3-venv` package should be available by default. On Ubuntu Linux, install it with:

```bash
sudo apt update
sudo apt install python3-venv
```

2. Create the IESO virtual environment:

```bash
python3 -m venv ieso
```

3. Activate the virtual environment:

```bash
source ieso/bin/activate
```

4. Install IESO dependencies:

```bash
pip install --upgrade ortools numpy
```

**Windows**

1. [Install Miniconda](https://docs.anaconda.com/free/miniconda/index.html).

2. Open the Anaconda prompt and create the IESO virtual environment:

```bash
conda create --name ieso python=3.12
```

3. Activate the virtual environment:

```bash
conda activate ieso
```

4. Install IESO dependencies:

```bash
pip install --upgrade ortools numpy
```

---

#### Getting IESO

The initial step required to run an IESO simulation is to fetch the tool [from GitHub](https://github.com/greoux-research/ieso).

---

#### Building the IESO-embedded thermodynamic calculations tool

IESO includes a thermodynamic calculations tool within its `thermo` folder. It derives the cogeneration coefficients *a* and *b* from the turbine and condenser conditions, and is therefore needed **only for thermally coupled cases** — a process declared as `elec + ther`, such as MED or MSF desalination. Purely electric processes, including reverse osmosis and electrolysis, never call it, and neither does a system without a Power-to-X process.

The compiled binary is not tracked in the repository, so it must be built before the first thermally coupled run:

- On macOS or Ubuntu Linux systems: run the script `build.sh`.
- On Windows systems: run the script `build.bat`.

This process assumes that a C++ compiler is already installed on your device. If not, you can install it following the instructions provided below.

**macOS**

On macOS, you can install the GNU Compiler Collection (GCC), which includes the GNU C++ compiler, using the Xcode Command Line Tools:

```bash
xcode-select --install
```

**Ubuntu Linux**

To install the GNU C++ compiler and other essential build tools, run the following command in your terminal:

```bash
sudo apt-get update
sudo apt-get install build-essential
```

**Windows**

- Download [MinGW](https://sourceforge.net/projects/mingw/) and install it, ensuring that the GNU C++ compiler is included in the package.
- After installation, find the binary folder of MinGW. Usually, it is located at a path such as `C:\MinGW\bin`.
- Add the path of the MinGW binary folder to your system's PATH environment variable.

---

#### Running an IESO simulation

IESO takes one mandatory argument and any number of options:

1. The first argument is a [JSON](https://en.wikipedia.org/wiki/JSON) file (referred to as `input.json`) describing the integrated energy system optimisation problem.
2. Any further arguments are `name=value` options. Two are recognised:
   - `carbon-constraint` — an emissions budget in kg CO₂eq per MWh of **primary annual electricity demand**. The budget is that figure multiplied by `demand.e.total`; it is not a limit on the emission intensity of generation, and the electricity consumed by Power-to-X processes does not enlarge it.
   - `non-served-power-constraint` — an upper bound on annual unserved **electricity**, as a fraction of `demand.e.total`. `0.05` means 5%. It *permits* shortfall up to that share; it does not require any. There is no equivalent annual bound for the other commodities — see `l_ns` in the [IO file structure](ieso-io-file-structure.md).

The output is written beside the input as `input.ieso.json`, with one `.name_value` segment appended for each option, and is structured identically to the input with the results filled in. **The output path is derived from the input path**, so running a case whose input sits in `datasets/` overwrites the result stored there. To keep runs separate, copy the input into a working directory first, or use `tools/run_cases.sh`, which does this for you.

A run that does not reach an optimal solution still writes a file, with the input values echoed back, `solver.stat_succ` at 0 and `solver.stat_status` naming the reason. Check the status before reading a result.

Before running IESO, the environment needs to be set up, as described by the examples below.

**macOS and Ubuntu Linux**

Open a Terminal window and run the following commands:

```bash
source ieso/bin/activate
cd /path/to/ieso
python3 ieso.py input.json
# a carbon budget of 100 kg CO2eq per MWh of primary electricity demand:
# python3 ieso.py input.json carbon-constraint=100
# allow up to 5% of annual electricity demand to go unserved:
# python3 ieso.py input.json non-served-power-constraint=0.05
# options combine:
# python3 ieso.py input.json carbon-constraint=50 non-served-power-constraint=0.05
```

To re-solve the bundled example datasets without overwriting the results stored
alongside them:

```bash
tools/run_cases.sh runs/mycheck
tools/compare_outputs.py runs/mycheck/med-base.ieso.json \
    datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med---florida.ieso.json
```

---

#### Running the tests

```bash
pip install pytest
python3 -m pytest tests/
```

The suite uses short horizons and expected values derived by hand, and touches
no network. It takes a few seconds.

**Windows**

Open the Anaconda prompt and run the following commands:

```bash
conda activate ieso
cd /path/to/ieso
python3 ieso.py input.json
```
