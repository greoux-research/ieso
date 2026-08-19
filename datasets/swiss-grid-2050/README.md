
A first, **provisional** IESO representation of the Swiss electricity system in 2050.

The purpose is to make an interactive session possible, not to produce a research result.
Structure and costs follow OECD NEA report No. 7631, [*Achieving Net Zero Carbon Emissions
in Switzerland in 2050: Low Carbon Scenarios and their System Costs*](https://www.oecd-nea.org/jcms/pl_74877/achieving-net-zero-carbon-emissions-in-switzerland-in-2050-low-carbon-scenarios-and-their-system-costs?details=true)
(2022). Hourly profiles are real, taken from ENTSO-E for calendar 2025.
The dataset has **not** been cross-checked against the NEA scenarios. Read *Data gaps*
before drawing any conclusion from a run.

```bash
python ieso.py datasets/swiss-grid/swiss-grid---2050.json
```

About 10 seconds, 184 000 variables, 201 000 constraints.

# System represented

Annual demand is **85 TWh**, the 2050 figure from the JASM CLI scenario as adopted by
NEA 7631. The existing fleet is fixed; solar, wind and batteries are built by the optimiser.

| Component | `iden` | Capacity | Basis |
|---|---|---|---|
| Nuclear, long-term operation | `nucl` | 2 205 MW fixed | Gösgen 985 + Leibstadt 1 220 |
| Run-of-river hydro | `rovr` | 4 190 MW fixed | NEA 7631 §4.1 |
| Waste and CHP | `ther` | 870 MW fixed | NEA 7631 §4.1 |
| Reservoir hydro | `hdam` | 8 850 GWh / 8 800 MW | NEA 7631 Fig. 3.7, Annex A |
| Pumped storage | `hpmp` | 3 580 MW | NEA 7631 §4.1; energy capacity assumed |
| Solar PV | `solr` | optimised, ≤ 50 GW | EP2050+ reaches 37.5 GW |
| Onshore wind | `wind` | optimised, ≤ 5 GW | EP2050+ reaches 2.2 GW |
| Batteries | `bstr` | optimised, ≤ 100 GWh | — |
| New nuclear | `nunw` | **disabled** (`l_prod: [0, 0]`) | game lever |
| New gas (CCGT) | `ccgt` | **disabled** (`l_prod: [0, 0]`) | game lever |
| Imports | `impo-1/2/3` | 8 900 MW, price-banded | NTC from NEA 7631 Table 4.5 |

Costs come from Table 3.6 of NEA 7631: annualised investment plus fixed O&M into
`fix_cost_prod`, variable O&M plus fuel plus waste into `var_cost_prod`. Carbon is
deliberately **not** priced into `var_cost_prod` — it sits in `var_emis_prod`, so the
`carbon-constraint` option acts as a cap without double-counting.

The two disabled technologies are present so the file documents every lever the session
needs. Raising `l_prod[1]` to 3 200 enables new nuclear; to 2 000 enables gas.

# Profiles

Everything the dataset needs is in this folder. Paths in the JSON are relative to the
repository root, so runs are launched from there.

Four series are real ENTSO-E observations for calendar year 2025, zone CH, shifted one hour
from UTC to align with CET. Each is a single column of 8760 values, no header.

| File | Units | Source | Annual | mean/max | Used by |
|---|---|---|---|---|---|
| `dmnd.csv` | MW | ENTSO-E actual load | 62.07 TWh, 10.33 GW peak | 0.686 | `demand.e.profile` |
| `solr.csv` | MW | ENTSO-E generation, B16 solar | 5.16 TWh | 0.147 | generator `solr` |
| `wind.csv` | MW | ENTSO-E generation, B19 wind onshore | 0.15 TWh | 0.228 | generator `wind` |
| `rovr.csv` | MW | ENTSO-E generation, B11 run-of-river | 14.50 TWh | 0.451 | generator `rovr` |
| `inflow.csv` | ratio | POSY template workbook | 18.4 TWh on 8.8 GW | — | flex `hdam`, `inflow_profile` |
| `impo-1.csv` | 0/1 | derived from `price-ch-2025.csv` | 2 921 hours | 0.333 | generator `impo-1` |
| `impo-2.csv` | 0/1 | derived from `price-ch-2025.csv` | 2 930 hours | 0.334 | generator `impo-2` |
| `impo-3.csv` | 0/1 | derived from `price-ch-2025.csv` | 2 909 hours | 0.332 | generator `impo-3` |
| `price-ch-2025.csv` | EUR/MWh | ENTSO-E day-ahead, CH | mean 101.7 | — | **not read by the model** |

`price-ch-2025.csv` is the only file the solver never opens. It is kept because the three
import tranches are derived from it, and without it they cannot be audited or regenerated.
Delete it only if you are content for the tranche definitions to be unverifiable.

### How the profiles are interpreted

Only the *shape* of a profile matters. `cf_h` divides by the maximum, then rescales so the
mean equals the stated `capacity_factor`. Two consequences:

- The units of a generation profile are irrelevant — MW, per-unit, anything monotonic works.
- `capacity_factor` must not exceed the profile's own mean/max ratio, or hourly output would
  exceed nameplate. This is why `rovr` uses 0.395 rather than the 0.482 implied by the
  report's 17.7 TWh: the 2025 profile's mean/max is 0.451.

The demand profile is handled differently: `dm_h` rescales it so the annual sum equals
`demand.e.total`, preserving shape but discarding level.

The import profiles are 0/1 masks. With `capacity_factor` set to the mask's own mean, the
rescaling is exactly neutral, so each tranche offers its full 8 900 MW in the hours where
the Swiss day-ahead price fell in that band, and nothing in any other hour.

`inflow.csv` is not passed through `cf_h` at all. It is a shape scaled by `inflow_total`
(18.4 TWh) via `dm_h`, in MWh per hour.

### Regenerating

The ENTSO-E series were pulled for `2025-01-01` to `2026-01-01` (exclusive), hourly
aggregation, and concatenated from two half-year requests because the API caps responses at
5 000 rows. The import masks are the terciles of the day-ahead price series: band edges
94.8 and 117.0 EUR/MWh, with tranche prices set to each band's mean converted at
1.10 USD/EUR.

Reservoir inflow has no ENTSO-E equivalent. It was extracted from the `chronicles` and
`natural_input` sheets of `src/IO/Data/templates/time_series.xlsx` in the POSY repository,
[git.oecd-nea.org/posy/posy](https://git.oecd-nea.org/posy/posy).

# Modelling choices

### Reservoir hydro as an inflow-fed store

This dataset relies on an extension to IESO's `flex` object. A flexibility means may carry
`inflow_profile`, `inflow_total` and `charge_allowed`, giving

```
e_strg(i) = e_strg(i-1) + inflow(i) - e_spil(i) + √r·e_char(i) - e_disc(i)/√r
```

Inflow enters the store directly and escapes the round-trip penalty, since water arriving in
a lake was not pumped there. A free spill variable is created whenever inflow is present;
without it a wet period at a full reservoir would be infeasible rather than simply spilling.

This mirrors POSY's storage formulation, which carries a natural intake with `is_natural`
and `is_charged` flags. One deliberate difference: POSY expresses inflow as a ratio to
discharging capacity, so inflow scales with the plant. IESO uses absolute annual energy,
because a river does not grow when a larger turbine is installed.

The dam has `charge_allowed: false` and unit round-trip efficiency. Pumped storage is a
separate object that can charge from the grid at 0.80. Keeping them apart stops the
reservoir behaving as free, unlimited pumped storage, which would make the battery lever in
the session meaningless.

### Imports as price-banded tranches

POSY represents each neighbour by an hourly spot price and an hourly NTC, setting the Swiss
price to that of the cheapest unsaturated interconnector — a rule needing binary variables.
IESO is pure LP and cannot express it.

Instead, the 2025 Swiss day-ahead price series is split into terciles, and each tercile
becomes an import tranche of the full 8 900 MW NTC, available only in the hours where the
price actually fell in that band:

| Tranche | Hours | Price |
|---|---|---|
| `impo-1` | 2 921 (33.3%) | 67.1 USD/MWh |
| `impo-2` | 2 930 (33.4%) | 115.4 USD/MWh |
| `impo-3` | 2 909 (33.2%) | 153.2 USD/MWh |

Band edges are 94.8 and 117.0 EUR/MWh; prices are converted at 1.10 USD/EUR.

The point of banding by observed hour rather than by a flat annual block is that the winter
scarcity then comes from the data rather than from an assumption. The expensive tranche
covers **97% of February and 83% of January**, against 5–8% of the summer months. That
single feature is what makes the session's winter question real.

IESO's dual on the hourly demand constraint consequently returns an import price when
imports are marginal and a domestic one when they are exhausted — the same two-regime
behaviour POSY imposes, emerging from the simplex instead.

### What is not represented

- **Exports.** IESO has no revenue-earning sink, so trade appears on the import side only.
  This penalises the flexible hydro and nuclear that earn export revenue in NEA 7631.
- **Hydrogen and heat.** The `p2x` list is empty; NEA 7631 imposes 8 TWh for electrolysis.
- **Voluntary demand response.** Only involuntary non-served energy, at 10 000 USD/MWh.
- **Unit commitment, ramping, reserves, network.** Absent by design in IESO.
- **Perfect foresight.** As in POSY, the reservoir is dispatched with full knowledge of the
  year ahead. NEA 7631 is explicit that this drains reservoirs earlier than real operators.

# Data gaps

Ordered by how much they distort the answer.

**1. 2025 prices are used for a 2050 world.**
The import tranches are real, but they are *today's* prices. By 2050 the neighbours are
assumed to have decarbonised, which is precisely what NEA 7631 modelled by using a 2040
"decarb" price scenario rather than observed prices. Cheap summer imports in this dataset
reflect today's European solar glut, not a 2050 system.

**2. Carbon intensity of imports — still invented.**
All three tranches carry 200 kg CO₂/MWh, a rough weighting of French, German, Italian and
Austrian intensities. It is the last fully invented number in the dataset, and it produces
the entire emissions KPI: 23.5 TWh of imports × 200 kg ÷ 85 TWh = 55.4 kg/MWh, exactly the
figure reported. For a Swiss audience this is the most contested number in the exercise.

**3. Demand shape is 2025, not 2050.**
`dmnd.csv` is the 2025 shape scaled to 85 TWh. The real 2050 curve is far more volatile —
electric vehicles, heat pumps, electrolysis — and NEA 7631 shows both a higher peak and a
loss of familiar daily and seasonal patterns. Using 2025 understates the flexibility
requirement, flattering every scenario roughly equally.

**4. Run-of-river energy is uncertain by about 20%.**
ENTSO-E gives 14.5 TWh for 2025; NEA 7631 gives 17.7 TWh for 2019. That is either a dry year
or a difference in which plants ENTSO-E covers. Run-of-river is a fifth of Swiss supply, so
3 TWh is material.

**5. PV capital cost is 2020-vintage.**
Table 3.6 uses 1 000 USD/kW overnight, giving an implied LCOE of 84.3 USD/MWh. Utility-scale
PV has fallen substantially since. This directly causes the result in the next section.

**6. Round-trip efficiencies are assumed.** 0.80 pumped, 0.85 battery. NEA 7631 publishes
neither; the POSY template ships 0.8 for hydro storage, which looks illustrative.

**7. Pumped storage energy capacity is assumed.** 28 640 MWh, i.e. 8 hours at 3 580 MW. The
report gives the power rating but not the volume.

**8. Reservoir initial state of charge is assumed.** `soc_ini: 0.60`. IESO forces the year to
close at the same level, so the guess binds twice.

**9. Reservoir inflow provenance unconfirmed.** `inflow.csv` comes from the POSY template
workbook and matches Annex A at 18.4 TWh on 8.8 GW, but the author has not confirmed it is
the real Swiss series.

# What the base run says

| | |
|---|---|
| Cost | 74.75 USD/MWh |
| Emissions | 55.4 kg CO₂/MWh — see gap 2 |
| Reliability | 1.00000 |
| Wind built | 5 000 MW (at its bound) |
| Solar built | **0 MW** |
| Imports | 23.5 TWh (27.7% of demand) |
| Shadow price | mean 101.5, p95 153.2 USD/MWh |

Two results need understanding before they are shown to anyone.

**Solar builds nothing.** Its implied LCOE of 84.3 USD/MWh exceeds the 67.1 USD/MWh cheap
import tranche, and that tranche is available in summer daylight — exactly when Swiss PV
generates. The optimiser is right on these inputs, but the inputs contain two distortions
pointing the same way: 2020-vintage PV capex (gap 5) and 2025 import prices standing in for
2050 (gap 1). Real Swiss PV deployment is also driven by policy and energy security rather
than merit order. Do not present this as a finding.

**Wind hits its bound.** Wind at 77.7 USD/MWh beats PV, so it fills the 5 GW cap. NEA 7631
anticipates this exactly — it notes an unconstrained optimisation would favour wind, and
imposes a 90/10 solar-to-wind split for land-use and policy reasons. No such constraint is
applied here.

Encouragingly, pumped storage now cycles 3.0 TWh, against 0.04 TWh when imports were flat
annual blocks. The seasonal price spread gives it something real to arbitrage.

# Next (v1)

- Replace 2025 prices with a 2050 decarbonised-neighbour price scenario
- Source or defend a carbon intensity for imports
- Obtain or reconstruct a 2050 demand shape
- Refresh PV and battery capital costs to current values
- Resolve the run-of-river energy discrepancy
- Decide whether to impose a solar/wind split, or defend the unconstrained result
- Reproduce the NEA scenario capacities as a validation target
- Consider adding export revenue, and measure how much its absence distorts the ranking

# Attribution

Hourly load, generation and day-ahead price series: ENTSO-E Transparency Platform, calendar
year 2025.

Reservoir inflow extracted from **POSY**, the NEA power system model —
[git.oecd-nea.org/posy/posy](https://git.oecd-nea.org/posy/posy) — MIT licence,
© 2023 OECD Nuclear Energy Agency.

Cost and capacity assumptions derived from **OECD NEA report No. 7631**,
[*Achieving Net Zero Carbon Emissions in Switzerland in 2050: Low Carbon Scenarios and their
System Costs*](https://www.oecd-nea.org/jcms/pl_74877/achieving-net-zero-carbon-emissions-in-switzerland-in-2050-low-carbon-scenarios-and-their-system-costs?details=true),
OECD 2022.
