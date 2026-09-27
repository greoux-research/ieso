# Electricity grid

Electricity supply and battery storage, serving 5.69 TWh/year.

Input: [elec-grid.json](elec-grid.json); profiles: `dmnd.csv`, `solr.csv`, `wind.csv`.
See [case conventions and running instructions](../README.md).

## Illustrative results

| Capacity / electricity generation | Base (MW / GWh) | Capped (MW / GWh) |
|---|---:|---:|
| Nuclear | 0.0 / 0.0 | 13.9 / 41.2 |
| Coal | 193.8 / 788.6 | 0.0 / 0.0 |
| Combined cycle | 345.9 / 560.9 | 437.9 / 548.9 |
| Open cycle | 220.3 / 28.3 | 155.1 / 6.1 |
| Solar | 1701.2 / 2504.3 | 2642.1 / 3146.6 |
| Wind | 829.3 / 1976.6 | 1000.0 / 2170.6 |

| Annual metric | Base | Capped |
|---|---:|---:|
| Battery capacity (MWh) | 3,681 | 5,000 |
| Electricity cost ($/served MWh) | 103.04 | 107.93 |
| System CO₂ emissions (kt) | 984.2 | 284.5 |
| Unserved electricity (%) | 0.00 | 0.00 |
| Solar + wind curtailment (GWh / % available) | 589.8 / 11.6% | 1806.6 / 25.4% |
| Generated electricity surplus (GWh) | 0.21 | 7.23 |

The cap replaces coal with more solar and some nuclear; wind and battery capacity reach their bounds.

All runs are optimal with reconciled accounts and no unmet demand. Generation excludes battery discharge. Zero-cost renewable dispatch can vary between equally optimal solutions; curtailment and surplus describe these runs.

[Full results and provenance](../../results/elec-grid-2026-09-26/) (`eg-base`, `eg-cn`).
