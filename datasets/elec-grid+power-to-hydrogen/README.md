
This example considers an annual electricity demand of 50 TWh, which is supplied by a mix of energy sources including nuclear, coal, combined cycle gas turbine (CCGT), open cycle gas turbine (OCGT), solar, wind, and battery storage.

Furthermore, an additional 35000 tonnes of hydrogen per year is produced through *alkaline water electrolysis*.

````
# optimisation example
# without carbon constraint

python ieso.py datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---california.json
````

````
# optimisation example
# with carbon constraint
# 100 kg per MWh of primary electricity demand

python ieso.py datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---california.json 100
````

````
# simulation report generation example

python report.py datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---california.ieso.json
````
