# Illustrative cases

Four examples of IES Optimiser input structure and use, sharing one electricity system
and adding one Power-to-X process at a time. Inputs are illustrative assumptions,
not a representation of a country, a forecast, or current cost estimates.

| Case | Additional demand |
|---|---|
| [elec-grid](elec-grid/) | None |
| [Hydrogen](elec-grid+power-to-hydrogen/) | Electrolysis and hydrogen storage |
| [Water: RO](elec-grid+power-to-water-ro/) | Reverse osmosis and water storage |
| [Water: MED](elec-grid+power-to-water-med/) | Multi-effect distillation, cogeneration and water storage |

Each folder contains its input JSON and three 8,760-hour CSV profiles: electricity
demand (`dmnd.csv`), solar (`solr.csv`) and wind (`wind.csv`). All cases share
5.69 TWh/year of electricity demand. Capacities are optimised continuously.
`tools/build_datasets.py` regenerates the rounded inputs and copies the profiles.

Profile paths are relative to each input's own directory, so a case runs from
any directory and can be copied elsewhere with its CSVs:

```sh
ies-optimiser datasets/elec-grid/elec-grid.json
bash tools/run_cases.sh runs/examples
```

Case summaries compare **base** runs with **capped** runs: a carbon budget of
50 kg CO₂ per MWh of electricity demand and at most 5% electricity unserved.
Electricity costs are allocated resource costs per served MWh, excluding shortage
penalties. Product costs use `tools/product_costs.py`: plant and storage costs plus
energy valued at hourly electricity marginal values, not tariffs. Curtailment is
unused available solar/wind generation, distinct from generated surplus.

Profiles: demand derived from ENTSO-E; solar/wind from
[Renewables.ninja](https://www.renewables.ninja/), licensed
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
