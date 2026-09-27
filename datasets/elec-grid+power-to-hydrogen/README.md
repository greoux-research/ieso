# Power to hydrogen

The same electricity system plus electrolysis (53.5 kWh/kg) and hydrogen storage, serving 3,983 t/year.

Input: [elec-grid+power-to-hydrogen.json](elec-grid+power-to-hydrogen.json); profiles: `dmnd.csv`, `solr.csv`, `wind.csv`.
See [case conventions and running instructions](../README.md).

## Illustrative results

| Capacity / electricity generation | Base (MW / GWh) | Capped (MW / GWh) |
|---|---:|---:|
| Nuclear | 0.0 / 0.0 | 9.9 / 29.4 |
| Coal | 191.0 / 777.7 | 0.0 / 0.0 |
| Combined cycle | 335.6 / 550.5 | 438.9 / 548.8 |
| Open cycle | 220.6 / 28.0 | 154.9 / 6.2 |
| Solar | 1771.8 / 2594.3 | 2756.4 / 3325.9 |
| Wind | 881.2 / 2127.8 | 1000.0 / 2221.6 |

| Annual metric | Base | Capped |
|---|---:|---:|
| Battery capacity (MWh) | 3,725 | 5,000 |
| Electricity cost ($/served MWh) | 101.80 | 106.48 |
| System CO₂ emissions (kt) | 969.4 | 284.5 |
| Unserved electricity (%) | 0.00 | 0.00 |
| Solar + wind curtailment (GWh / % available) | 604.8 / 11.4% | 1771.4 / 24.2% |
| Generated electricity surplus (GWh) | 0.50 | 1.22 |
| Process capacity (kg/h) | 875 | 1,281 |
| Product storage (kg) | 28,356 | 37,789 |
| Product cost ($/kg; marginal-energy convention) | 3.753 | 3.725 |

With the cap, a larger electrolyser and hydrogen store shift production to cheaper hours; the marginal-energy-valued hydrogen cost falls slightly.

All runs are optimal with reconciled accounts and no unmet demand. Generation excludes battery discharge. Zero-cost renewable dispatch can vary between equally optimal solutions; curtailment and surplus describe these runs.

[Full results and provenance](../../results/elec-grid-2026-09-26/) (`h2-base`, `h2-cn`).
