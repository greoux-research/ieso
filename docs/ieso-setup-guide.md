# IESO Setup Guide

#### Introduction

This article provides a guide on how to set up and run the [Integrated Energy Systems Optimiser](https://github.com/greoux-research/ieso) (IESO), a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

IESO's modelling approach is described in [this article](ieso-modelling-approach.md). Its IO file structure is documented [at this link](ieso-io-file-structure.md).

IESO is implemented in Python 3 and doesn't require direct installation itself. However, it relies on external libraries — [OR-Tools](https://developers.google.com/optimization/install), [NumPy](https://numpy.org/install/), and [Matplotlib](https://matplotlib.org/stable/users/installing/index.html) — which need to be pre-installed.

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
pip install --upgrade ortools protobuf numpy matplotlib
```

**Windows**

1. [Install Miniconda](https://docs.anaconda.com/free/miniconda/index.html).

2. Open the Anaconda prompt and create the IESO virtual environment:

```bash
conda create --name ieso python=3.8
```

3. Activate the virtual environment:

```bash
conda activate ieso
```

4. Install IESO dependencies:

```bash
pip install --upgrade ortools protobuf numpy matplotlib
```

---

#### Getting IESO

The initial step required to run an IESO simulation is to fetch the tool [from GitHub](https://github.com/greoux-research/ieso).

---

#### Building the IESO-embedded thermodynamic calculations tool

IESO includes a thermodynamic calculations tool within its `thermo` folder. This tool needs to be compiled before use:

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

IESO is called with one or two arguments:

1. The first argument (mandatory) is a [JSON](https://en.wikipedia.org/wiki/JSON) file (referred to as `input.json`) that describes the integrated energy system optimisation problem.
2. The second argument (optional) specifies the carbon constraint.

The output of IESO materialises as a JSON file named `input.ieso.json`, structured identically to `input.json` but inclusive of the simulation results.

Before running IESO, the environment needs to be set up, as described by the examples below.

**macOS and Ubuntu Linux**

Open a Terminal window and run the following commands:

```bash
source ieso/bin/activate
cd /path/to/ieso
python3 ieso.py input.json
# to introduce a carbon constraint of 100 kg per MWh:
# python3 ieso.py input.json carbon-constraint=100
# to limit the amount of non-served power to 5% of the total annual demand:
# python3 ieso.py input.json non-served-power-constraint=0.05
```

**Windows**

Open the Anaconda prompt and run the following commands:

```bash
conda activate ieso
cd /path/to/ieso
python3 ieso.py input.json
```
