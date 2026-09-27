#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

"""Launcher for running from a source checkout:

    python ies_optimiser.py INPUT.json [name=value ...]        # = ies-optimiser INPUT.json ...

It runs the installed ies_optimiser package (pip install -e . in this checkout, see
docs/ies-optimiser-setup-guide.md), exactly as the 'ies-optimiser' command and 'python -m ies_optimiser'
do. It is not the package: this file only launches it.

Python puts a script's own directory first on sys.path, and this file is
named ies_optimiser.py, so 'import ies_optimiser' would import this file again. The launcher
therefore drops its own directory from sys.path for its own process before
importing the package. When this directory is on sys.path for some other
reason (for example 'python -m pytest' run here with a non-editable install),
importing ies_optimiser would reach this file instead of the package; it then refuses
with an explanation rather than posing as the package.
"""

import os
import sys

if __name__ != '__main__':
    raise ImportError('\'' + os.path.abspath(__file__) + '\' is IES Optimiser\'s command-line launcher, not the ies_optimiser '
                      'package. It was imported because its directory is on sys.path ahead of the installed '
                      'package. Install IES Optimiser from this checkout (pip install -e .), and run from another directory '
                      'or with python -P (e.g. python -P -m pytest).')

_here = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _here]

try:
    from ies_optimiser.cli import main
except ImportError as e:
    sys.stderr.write('IES Optimiser is not installed in this Python (' + sys.executable + '): ' + str(e) + '\n'
                     'Install it from this checkout with: python -m pip install -e ' + _here + '\n')
    raise SystemExit(1)

if __name__ == '__main__':
    import ies_optimiser
    _package = os.path.dirname(os.path.abspath(ies_optimiser.__file__))
    if _package != os.path.join(_here, 'src', 'ies_optimiser'):
        sys.stderr.write('ies_optimiser.py: running the installed IES Optimiser ' + ies_optimiser.__version__ + ' from ' + _package
                         + ', not this checkout\'s src/ies_optimiser\n')
    raise SystemExit(main())
