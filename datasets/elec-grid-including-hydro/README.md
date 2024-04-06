
This example assumes an annual electricity demand of 50 terawatt-hours (TWh). This demand is fulfilled by a combination of energy sources including nuclear, coal, combined cycle gas turbines (CCGT), open cycle gas turbines (OCGT), solar, wind, battery storage, and various forms of existing hydropower plants: run-of-the-river hydro, hydro dams, and pumped storage hydro.

````
# optimisation example
# without carbon constraint

python ieso.py datasets/elec-grid-including-hydro/elec-grid-including-hydro---user.json
````

````
# optimisation example
# with carbon constraint
# 100 kg per MWh of primary electricity demand

python ieso.py datasets/elec-grid-including-hydro/elec-grid-including-hydro---user.json 100
````

````
# simulation report generation example

python report.py datasets/elec-grid-including-hydro/elec-grid-including-hydro---user.ieso.json
````
