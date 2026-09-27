# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser
#
# Builds the thermodynamics executable (thermo/*.cpp) and installs it inside
# the Python package, at ies_optimiser/_bin/ies-optimiser-thermo (ies-optimiser-thermo.exe on Windows).
# Run by scikit-build-core during 'python -m build' or 'pip install'; see
# pyproject.toml. It is a standalone executable called as a subprocess, not a
# Python extension.

cmake_minimum_required(VERSION 3.15...3.31)
project(ies_optimiser_thermo LANGUAGES CXX)

# Compiled with the flags of thermo/build.sh, the build that produced the
# reference executable (g++ -fPIC -Wall, no optimisation flag and no -std
# flag), so the packaged tool performs the same floating-point operations. The
# build type's own flags (Release adds -O3 -DNDEBUG) are deliberately cleared.
foreach(config RELEASE RELWITHDEBINFO MINSIZEREL DEBUG)
  set(CMAKE_CXX_FLAGS_${config} "")
endforeach()

# On Windows the C++ runtime is linked statically (/MT): the executable is run
# as a separate process, outside Python's DLL directories, and msvcp140.dll is
# not guaranteed on a clean system. tools/inspect_native.py checks the result.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

add_executable(ies-optimiser-thermo thermo/sim.cpp thermo/Cogen.cpp thermo/iesOptimiserH2O.cpp)
set_target_properties(ies-optimiser-thermo PROPERTIES POSITION_INDEPENDENT_CODE ON)
if(MSVC)
  target_compile_options(ies-optimiser-thermo PRIVATE /W4)
else()
  target_compile_options(ies-optimiser-thermo PRIVATE -Wall)
endif()
if(UNIX)
  target_link_libraries(ies-optimiser-thermo PRIVATE m)
endif()

# SKBUILD_PLATLIB_DIR is the wheel's platform-library root when built by
# scikit-build-core; a plain 'cmake --install' uses the prefix instead.
if(DEFINED SKBUILD_PLATLIB_DIR)
  set(IES_OPTIMISER_BIN_DESTINATION "${SKBUILD_PLATLIB_DIR}/ies_optimiser/_bin")
else()
  set(IES_OPTIMISER_BIN_DESTINATION "ies_optimiser/_bin")
endif()
install(TARGETS ies-optimiser-thermo RUNTIME DESTINATION "${IES_OPTIMISER_BIN_DESTINATION}")
