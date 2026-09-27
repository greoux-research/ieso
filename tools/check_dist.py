#!/usr/bin/env python3
"""Check that IES Optimiser's distribution artifacts hold exactly what they should.

    python tools/check_dist.py DIST_FILE [...]      # .whl and/or .tar.gz

Prints each artifact's file list, then checks it against an allow-list:

* sdist: pyproject.toml, CMakeLists.txt, README.md, LICENSE, PKG-INFO, the
  package sources and resources under src/ies_optimiser/, and the C++ sources under
  thermo/ -- nothing else (no datasets, results, runs, tests, profiles, object
  files or executables);
* wheel: the ies_optimiser package (modules, py.typed, the two JSON Schemas, one
  thermodynamics executable in ies_optimiser/_bin/) and its dist-info (METADATA, WHEEL,
  RECORD, entry_points.txt, licenses/LICENSE), with the expected metadata:
  Requires-Python >= 3.11, the three runtime dependencies, the 'ies-optimiser' console
  entry point, a py3-none platform tag.

Exit status 0 when every artifact passes.
"""

import fnmatch
import os
import re
import sys
import tarfile
import zipfile

SDIST_ALLOWED = ['pyproject.toml', 'CMakeLists.txt', 'README.md', 'LICENSE', 'PKG-INFO',
                 'src/ies_optimiser/*.py', 'src/ies_optimiser/py.typed', 'src/ies_optimiser/data/*.schema.json',
                 'thermo/*.cpp', 'thermo/*.h', 'thermo/README.md']
SDIST_REQUIRED = ['pyproject.toml', 'CMakeLists.txt', 'README.md', 'LICENSE', 'PKG-INFO', 'src/ies_optimiser/__init__.py',
                  'src/ies_optimiser/py.typed', 'src/ies_optimiser/data/ies-optimiser-input-1.schema.json',
                  'src/ies_optimiser/data/ies-optimiser-result-1.schema.json', 'thermo/sim.cpp', 'thermo/Cogen.cpp',
                  'thermo/iesOptimiserH2O.cpp', 'thermo/Cogen.h', 'thermo/iesOptimiserH2O.h']
WHEEL_ALLOWED = ['ies_optimiser/*.py', 'ies_optimiser/py.typed', 'ies_optimiser/data/*.schema.json', 'ies_optimiser/_bin/ies-optimiser-thermo',
                 'ies_optimiser/_bin/ies-optimiser-thermo.exe', '*.dist-info/METADATA', '*.dist-info/WHEEL', '*.dist-info/RECORD',
                 '*.dist-info/entry_points.txt', '*.dist-info/licenses/LICENSE']
WHEEL_REQUIRED = ['ies_optimiser/__init__.py', 'ies_optimiser/__main__.py', 'ies_optimiser/api.py', 'ies_optimiser/cli.py', 'ies_optimiser/py.typed',
                  'ies_optimiser/data/ies-optimiser-input-1.schema.json', 'ies_optimiser/data/ies-optimiser-result-1.schema.json']
DEPENDENCIES = ('numpy', 'ortools', 'pydantic')


def allowed(name, patterns):
    return any(fnmatch.fnmatchcase(name, p) and (p.count('/') == name.count('/') or '*/' in p) for p in patterns)


def check(label, names, allowed_patterns, required, problems):
    for n in sorted(names):
        print('   ' + n)
    extra = [n for n in names if not allowed(n, allowed_patterns)]
    missing = [r for r in required if r not in names]
    if extra:
        problems.append(label + ': unexpected files ' + ', '.join(sorted(extra)))
    if missing:
        problems.append(label + ': missing ' + ', '.join(missing))


def check_sdist(path, problems):
    with tarfile.open(path) as t:
        members = [m for m in t.getmembers() if m.isfile()]
        roots = {m.name.split('/')[0] for m in members}
        if len(roots) != 1:
            problems.append('sdist: expected one top directory, found ' + ', '.join(sorted(roots)))
        names = [m.name.split('/', 1)[1] for m in members if '/' in m.name]
        print(os.path.basename(path) + ' (' + str(len(names)) + ' files)')
        check('sdist', names, SDIST_ALLOWED, SDIST_REQUIRED, problems)


def check_wheel(path, problems):
    name = os.path.basename(path)
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if not n.endswith('/')]      # repair tools may add directory entries
        print(name + ' (' + str(len(names)) + ' files)')
        check('wheel', names, WHEEL_ALLOWED, WHEEL_REQUIRED, problems)
        exes = [n for n in names if n.startswith('ies_optimiser/_bin/')]
        if len(exes) != 1:
            problems.append('wheel: expected one executable in ies_optimiser/_bin/, found ' + str(exes))
        dist = [n for n in names if n.endswith('.dist-info/METADATA')]
        meta = z.read(dist[0]).decode() if dist else ''
        entry = [n for n in names if n.endswith('.dist-info/entry_points.txt')]
        entries = z.read(entry[0]).decode() if entry else ''
    python, abi, plat = name[:-len('.whl')].split('-')[-3:]
    if (python, abi) != ('py3', 'none') or plat == 'any':
        problems.append('wheel: tag ' + '-'.join((python, abi, plat)) + ' is not py3-none-<platform>')
    if 'Requires-Python: >=3.11' not in meta:
        problems.append('wheel: Requires-Python is not >=3.11')
    for dep in DEPENDENCIES:
        if not re.search(r'^Requires-Dist: ' + dep + r'\b', meta, re.M):
            problems.append('wheel: no Requires-Dist on ' + dep)
    if not re.search(r'^ies-optimiser = ies_optimiser\.cli:main$', entries, re.M):
        problems.append('wheel: no console entry point ies-optimiser = ies_optimiser.cli:main')


def main(paths):
    if not paths:
        print(__doc__, file=sys.stderr)
        return 1
    problems = []
    for p in paths:
        if p.endswith('.whl'):
            check_wheel(p, problems)
        elif p.endswith('.tar.gz'):
            check_sdist(p, problems)
        else:
            problems.append(p + ': not a wheel or an sdist')
    for p in problems:
        print('FAIL ' + p)
    print('PASS' if not problems else 'FAILED (' + str(len(problems)) + ')')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
