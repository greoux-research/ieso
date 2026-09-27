
This folder contains a tool for thermodynamic calculations. It estimates the coefficients *a* and *b* that relate the *missed electricity production* to the *thermal power transferred to the external process*, for a steam turbine supplying heat in cogeneration mode.

It is needed **only for thermally coupled cases** — a process of type `elec + ther`, such as MED desalination. Purely electric systems, reverse osmosis and electrolysis never call it.

It is built into the Python package by CMake (`CMakeLists.txt` at the repository root) whenever a wheel is built or IESO is installed from source, and installed as `ieso/_bin/ieso-thermo` (`ieso-thermo.exe` on Windows). IESO runs that file, found through the package itself whatever the working directory, unless `RunConfig(thermo_bin=...)` names another, and records its path, origin and digest in every result's provenance. It is compiled with the same flags as `build.sh` (no optimisation flag); on Windows the C++ runtime is linked statically.

`build.sh` (`build.bat` on Windows) builds the standalone `sim.bin` in this folder, the build the reference evidence was recorded with (see `docs/baseline-verification.md`); the package does not use it.

````
# assuming that a C++ compiler is already installed on your device
bash build.sh        # macOS, Linux  (build.bat on Windows)
````

## Usage

````
ieso-thermo TUR_T TUR_P CDR_P STX_T       # prints "a b" (sim.bin: the same interface)
ieso-thermo --limits TUR_T TUR_P CDR_P    # prints the supported extraction range (C)
````

`TUR_T`, `TUR_P`: turbine inlet temperature (°C) and pressure (bar); `CDR_P`: condenser pressure (bar); `STX_T`: steam extraction temperature (°C).

## Supported domain

- all four inputs finite numbers;
- `0 < CDR_P < TUR_P`;
- inlet steam superheated: `TUR_T` above the saturation temperature at `TUR_P`;
- `STX_T` **strictly** between the saturation temperatures at `CDR_P` and `TUR_P`, so that the extraction pressure lies between the condenser and inlet pressures. Both boundaries are excluded: at the lower one the heat would be free (`a = 0`); at the upper one extraction would be at inlet pressure;
- the result must satisfy `0 < a < 1`, `b > 0` and `a × b < 1`.

Outside it the tool prints nothing on standard output, writes the reason to standard error and exits non-zero. Before these checks, an extraction temperature above the inlet saturation temperature (for example 300 °C on a 290 °C / 70 bar turbine) was computed as a *compression* and returned plausible-looking positive coefficients.

Exit status: 0 success; 1 usage; 2 an argument is not a number; 3 outside the supported domain, or a steam-table evaluation failed.

The coefficients are printed to six significant figures, the precision IESO uses.
