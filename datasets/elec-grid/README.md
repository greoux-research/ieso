
This example assumes an annual electricity demand of 50 terawatt-hours (TWh). This demand is fulfilled by a combination of energy sources including nuclear, coal, combined cycle gas turbine (CCGT), open cycle gas turbine (OCGT), solar, wind, and battery storage.

````
# optimisation example
# without carbon constraint

python ieso.py datasets/elec-grid/elec-grid---mid-west.json
````

````
# optimisation example
# with carbon constraint
# 100 kg per MWh of primary electricity demand

python ieso.py datasets/elec-grid/elec-grid---mid-west.json 100
````

````
# simulation report generation example

python report.py datasets/elec-grid/elec-grid---mid-west.ieso.json
````
