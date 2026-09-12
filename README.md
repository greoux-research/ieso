
# IESO v26.09

IESO (*Integrated Energy Systems Optimiser*) is a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

- [Modelling Approach](docs/ieso-modelling-approach.md)
- [Setup Guide](docs/ieso-setup-guide.md)
- [IO File Structure](docs/ieso-io-file-structure.md)
- [Baseline Verification](docs/baseline-verification.md)

# Folder structure and contents

- The main Python script **ieso.py** is located at the top level (root) alongside other building blocks in the **ieso_modules** folder.
- The **thermo** folder contains a tool for thermodynamic calculations. It is compiled from source and is needed only for thermally coupled (`elec + ther`) cases.
- Sample hourly profiles for demand, solar, and wind output are provided in the **profiles** folder.
- The **datasets** folder contains examples of IESO input/output data sets. The cost assumptions they carry are inherited illustrative examples, not a maintained cost database.
- The **tools** folder holds a non-destructive scenario runner and a result comparator.
- The **tests** folder holds the regression suite: `python3 -m pytest tests/`.

Every result carries a `provenance` block recording the code version, the digests of the input and of each profile it references, the options applied, and the solver and environment that produced it. Results are reproducible only against a recorded environment: a different solver build may settle on a different vertex of the same optimal face.

# How to cite IESO

Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso
