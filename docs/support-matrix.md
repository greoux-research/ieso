# Supported Platforms

> **Current verification status (2026-09-27):** every platform and Python version above was built and tested on GitHub for commit `da20deb`, and the release candidate `2026.9.0rc1` was published to TestPyPI and verified from it on all four platforms. See [Baseline Verification](baseline-verification.md).

IES Optimiser is distributed as one wheel per platform (`py3-none-<platform>`: the package and its compiled thermodynamics executable, for every supported Python) and a source distribution, all published on PyPI as `ies-optimiser`.

| Platform | Wheel tag | Minimum OS | Python |
|---|---|---|---|
| Linux, x86_64 (glibc) | `manylinux_2_28_x86_64` | glibc 2.28 (RHEL/Rocky 8, Debian 10, Ubuntu 18.10 and newer) | 3.11, 3.12, 3.13, 3.14 |
| macOS, Apple Silicon (arm64) | `macosx_11_0_arm64` | macOS 11 | 3.11, 3.12, 3.13, 3.14 |
| macOS, Intel (x86_64) | `macosx_10_15_x86_64` | macOS 10.15 | 3.11, 3.12, 3.13, 3.14 |
| Windows, x86_64 (AMD64) | `win_amd64` | Windows 10 | 3.11, 3.12, 3.13, 3.14 |

Every combination above is built and tested by `.github/workflows/wheels.yml`: the wheel is built once per platform (cibuildwheel, CPython 3.11), then installed into a fresh environment on each Python version and tested outside any checkout (`tests_installed/`). The minimum OS and glibc match the floors of IES Optimiser's OR-Tools dependency, and each executable is checked against its wheel tag (`tools/inspect_native.py`). The status of each combination — verified locally, verified by completed CI, or configured and not yet run — is recorded in [Baseline Verification](baseline-verification.md).

**Not supported** — no wheel is built, and nothing is claimed:

| | Why |
|---|---|
| Linux on ARM (aarch64) | OR-Tools has wheels, but IES Optimiser's are not yet built or tested on ARM runners. |
| Windows on ARM | OR-Tools publishes no Windows ARM wheel. |
| musl Linux (Alpine) | OR-Tools publishes no musllinux wheel. |
| 32-bit platforms | No OR-Tools wheels. |
| Free-threaded Python (3.13t, 3.14t) | OR-Tools has free-threaded wheels for Linux only, and IES Optimiser is untested there. |
| Python 3.10 and earlier | Below IES Optimiser's stated minimum (3.11). |
| Python 3.15 | Not yet stable; to be added when OR-Tools publishes wheels for it. |

The source distribution builds on other platforms where a C++ compiler and wheels (or builds) of NumPy, OR-Tools and Pydantic exist; such builds are not tested.

**Dependencies.** The wheel requires `numpy>=2.0,<3`, `ortools>=9.15,<10` and `pydantic>=2.11,<3`; pip installs them from PyPI as wheels on every supported combination (checked with `pip install --only-binary=:all:` in CI). On Python 3.11, NumPy resolves to an older 2.x release than on 3.12 and later. The solver build can change which of several equally optimal dispatches is returned; the objective, capacities and accounts are what the [comparison contract](baseline-verification.md) holds fixed across platforms.

**Native executable.** Built by CMake with the flags of the reference build (no optimisation flag); on Windows the C++ runtime is linked statically, so it needs no Visual C++ redistributable. On Linux it links the system `libstdc++`, `libm` and `libc`, within the manylinux_2_28 symbol-version policy; on macOS only `libSystem` and the system `libc++`. Coefficients are compared with the reference fixture to one unit in the sixth significant digit on every platform (exactly, on the reference platform).
