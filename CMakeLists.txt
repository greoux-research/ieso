# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso
#
# Builds the thermodynamics executable (thermo/*.cpp) and installs it inside
# the Python package, at ieso/_bin/ieso-thermo (ieso-thermo.exe on Windows).
# Run by scikit-build-core during 'python -m build' or 'pip install'; see
# pyproject.toml. It is a standalone executable called as a subprocess, not a
# Python extension.

cmake_minimum_required(VERSION 3.15...3.31)
project(ieso_thermo LANGUAGES CXX)

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

add_executable(ieso-thermo thermo/sim.cpp thermo/Cogen.cpp thermo/iesoH2O.cpp)
set_target_properties(ieso-thermo PROPERTIES POSITION_INDEPENDENT_CODE ON)
if(MSVC)
  target_compile_options(ieso-thermo PRIVATE /W4)
else()
  target_compile_options(ieso-thermo PRIVATE -Wall)
endif()
if(UNIX)
  target_link_libraries(ieso-thermo PRIVATE m)
endif()

# SKBUILD_PLATLIB_DIR is the wheel's platform-library root when built by
# scikit-build-core; a plain 'cmake --install' uses the prefix instead.
if(DEFINED SKBUILD_PLATLIB_DIR)
  set(IESO_BIN_DESTINATION "${SKBUILD_PLATLIB_DIR}/ieso/_bin")
else()
  set(IESO_BIN_DESTINATION "ieso/_bin")
endif()
install(TARGETS ieso-thermo RUNTIME DESTINATION "${IESO_BIN_DESTINATION}")
