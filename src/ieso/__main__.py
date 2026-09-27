#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""python -m ieso ...: the same command line as the ieso console command."""

from ieso.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
