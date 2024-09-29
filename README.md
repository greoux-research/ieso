# IESO

IESO (*Integrated Energy Systems Optimiser*) is a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

- [Modelling Approach](https://greoux.re/blog/index.php/ieso-modelling-approach/)
- [Setup Guide](https://greoux.re/code/index.php/ieso-setup-guide/)
- [IO File Structure](https://greoux.re/code/index.php/ieso-io-file-structure/)

# Folder structure and contents

- The main Python script **ieso.py** and the post-processing script **report.py** are located at the top level (root) alongside other utilities (**t.py** and **u.py**) and folders.
- The **thermo** folder contains a tool for thermodynamic calculations.
- Sample hourly profiles for demand, solar, and wind output are provided in the **profiles** folder.
- Finally, the **datasets** folder contains examples of IESO input/output data sets and simulation reports.

# How to cite IESO

Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

# Changelog

September 29, 2024:

- Updated this README.md file to include links to IESO [modelling approach](https://greoux.re/blog/index.php/ieso-modelling-approach/) and [IO file structure](https://greoux.re/code/index.php/ieso-io-file-structure/).
- Minor change to the JSON object describing the demand for electricity.

April 16, 2024:

- t.py: Fixed a minor write error on Windows.

April 6, 2024:

- Uploaded to GitHub.
