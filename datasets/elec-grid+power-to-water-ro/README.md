# Power to water: RO

The same electricity system plus reverse osmosis (3.5 kWh/m³) and water storage, serving 50.23 million m³/year.

Input: [elec-grid+power-to-water-ro.json](elec-grid+power-to-water-ro.json); profiles: `dmnd.csv`, `solr.csv`, `wind.csv`.
See [case conventions and running instructions](../README.md).

## Illustrative results

| Capacity / electricity generation | Base (MW / GWh) | Capped (MW / GWh) |
|---|---:|---:|
| Nuclear | 0.0 / 0.0 | 22.4 / 69.2 |
| Coal | 206.1 / 842.7 | 0.0 / 0.0 |
| Combined cycle | 345.3 / 562.4 | 428.4 / 548.9 |
| Open cycle | 200.8 / 28.6 | 155.1 / 6.1 |
| Solar | 1725.6 / 2537.9 | 2681.6 / 3234.4 |
| Wind | 861.4 / 2064.2 | 1000.0 / 2239.1 |

| Annual metric | Base | Capped |
|---|---:|---:|
| Battery capacity (MWh) | 3,714 | 5,000 |
| Electricity cost ($/served MWh) | 107.61 | 114.04 |
| System CO₂ emissions (kt) | 1031.6 | 284.5 |
| Unserved electricity (%) | 0.00 | 0.00 |
| Solar + wind curtailment (GWh / % available) | 594.3 / 11.4% | 1717.7 / 23.9% |
| Generated electricity surplus (GWh) | 0.13 | 1.09 |
| Process capacity (m³/h) | 6,758 | 8,962 |
| Product storage (m³) | 87,261 | 1,888,277 |
| Product cost ($/m³; marginal-energy convention) | 0.896 | 1.083 |

With the cap, the model builds more desalination and water storage capacity; the reported water cost rises.

All runs are optimal with reconciled accounts and no unmet demand. Generation excludes battery discharge. Zero-cost renewable dispatch can vary between equally optimal solutions; curtailment and surplus describe these runs.

[Full results and provenance](../../results/elec-grid-2026-09-26/) (`ro-base`, `ro-cn`).
