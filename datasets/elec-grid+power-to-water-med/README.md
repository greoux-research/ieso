# Power to water: MED

The same electricity system plus multi-effect distillation (1.5 kWh electricity and 50 kWh heat per m³), serving 50.23 million m³/year. Nuclear, coal and combined-cycle candidates can supply heat at 80 °C; water storage is included.

Input: [elec-grid+power-to-water-med.json](elec-grid+power-to-water-med.json); profiles: `dmnd.csv`, `solr.csv`, `wind.csv`.
See [case conventions and running instructions](../README.md).

## Illustrative results

| Capacity / electricity generation | Base (MW / GWh) | Capped (MW / GWh) |
|---|---:|---:|
| Nuclear | 0.0 / 0.0 | 108.2 / 303.9 |
| Coal | 239.2 / 831.6 | 0.0 / 0.0 |
| Combined cycle | 346.0 / 538.7 | 367.9 / 381.0 |
| Open cycle | 170.9 / 27.5 | 135.9 / 3.9 |
| Solar | 1712.6 / 2506.9 | 2460.3 / 3087.1 |
| Wind | 845.2 / 2040.4 | 1000.0 / 2213.7 |

| Annual metric | Base | Capped |
|---|---:|---:|
| Battery capacity (MWh) | 3,698 | 5,000 |
| Electricity cost ($/served MWh) | 107.79 | 120.76 |
| System CO₂ emissions (kt) | 1265.5 | 284.5 |
| Unserved electricity (%) | 0.00 | 0.00 |
| Solar + wind curtailment (GWh / % available) | 584.4 / 11.4% | 1512.4 / 22.2% |
| Generated electricity surplus (GWh) | 1.79 | 0.00 |
| Process capacity (m³/h) | 6,795 | 7,085 |
| Product storage (m³) | 148,193 | 791,169 |
| Product cost ($/m³; marginal-energy convention) | 1.297 | 1.463 |
| Process heat supplied (GWh thermal) | 2511.5 | 2511.5 |

This case illustrates the trade-off between heat extraction and electricity production in cogeneration.

All runs are optimal with reconciled accounts and no unmet demand. Generation excludes battery discharge. Zero-cost renewable dispatch can vary between equally optimal solutions; curtailment and surplus describe these runs.

[Full results and provenance](../../results/elec-grid-2026-09-26/) (`med-base`, `med-cn`).
