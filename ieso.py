#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""Compatibility launcher for the historical invocation, from a source checkout:

    python ieso.py INPUT.json [name=value ...]        # = ieso INPUT.json ...

It runs the installed ieso package (pip install -e . in this checkout, see
docs/ieso-setup-guide.md), exactly as the 'ieso' command and 'python -m ieso'
do. It is not the package: this file only launches it.

Python puts a script's own directory first on sys.path, and this file is
named ieso.py, so 'import ieso' would import this file again. The launcher
therefore drops its own directory from sys.path for its own process before
importing the package. When this directory is on sys.path for some other
reason (for example 'python -m pytest' run here with a non-editable install),
importing ieso would reach this file instead of the package; it then refuses
with an explanation rather than posing as the package.
"""

import os
import sys

if __name__ != '__main__':
    raise ImportError('\'' + os.path.abspath(__file__) + '\' is IESO\'s command-line launcher, not the ieso '
                      'package. It was imported because its directory is on sys.path ahead of the installed '
                      'package. Install IESO from this checkout (pip install -e .), and run from another directory '
                      'or with python -P (e.g. python -P -m pytest).')

_here = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _here]

try:
    from ieso.cli import main
except ImportError as e:
    sys.stderr.write('IESO is not installed in this Python (' + sys.executable + '): ' + str(e) + '\n'
                     'Install it from this checkout with: python -m pip install -e ' + _here + '\n')
    raise SystemExit(1)

if __name__ == '__main__':
    import ieso
    _package = os.path.dirname(os.path.abspath(ieso.__file__))
    if _package != os.path.join(_here, 'src', 'ieso'):
        sys.stderr.write('ieso.py: running the installed IESO ' + ieso.__version__ + ' from ' + _package
                         + ', not this checkout\'s src/ieso\n')
    raise SystemExit(main())
