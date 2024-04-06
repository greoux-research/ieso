
This example considers an annual electricity demand of 50 TWh, which is supplied by a mix of energy sources including nuclear, coal, combined cycle gas turbine (CCGT), open cycle gas turbine (OCGT), solar, wind, and battery storage.

Furthermore, a freshwater volume of 365 million cubic metres per year is desalinated through *seawater reverse osmosis* (RO).

````
# optimisation example
# without carbon constraint

python ieso.py datasets/elec-grid+power-to-water-ro/elec-grid+power-to-water-ro---mid-west.json
````

````
# optimisation example
# with carbon constraint
# 100 kg per MWh of primary electricity demand

python ieso.py datasets/elec-grid+power-to-water-ro/elec-grid+power-to-water-ro---mid-west.json 100
````

````
# simulation report generation example

python report.py datasets/elec-grid+power-to-water-ro/elec-grid+power-to-water-ro---mid-west.ieso.json
````
