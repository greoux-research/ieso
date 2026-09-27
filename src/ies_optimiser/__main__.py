#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

"""python -m ies_optimiser ...: the same command line as the ies-optimiser console command."""

from ies_optimiser.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
