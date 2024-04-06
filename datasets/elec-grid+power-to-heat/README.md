
This example considers an annual electricity demand of 50 TWh, which is supplied by a mix of energy sources including nuclear, coal, combined cycle gas turbine (CCGT), open cycle gas turbine (OCGT), solar, wind, and battery storage.

Furthermore, an additional 20 TWh of industrial heat (at 160 C) per year is generated through a *power-to-heat* process linked to nuclear, coal, and CCGT power generation.

````
# optimisation example
# without carbon constraint

python ieso.py datasets/elec-grid+power-to-heat/elec-grid+power-to-heat---ercot.json
````

````
# optimisation example
# with carbon constraint
# 100 kg per MWh of primary electricity demand

python ieso.py datasets/elec-grid+power-to-heat/elec-grid+power-to-heat---ercot.json 100
````

````
# simulation report generation example

python report.py datasets/elec-grid+power-to-heat/elec-grid+power-to-heat---ercot.ieso.json
````
