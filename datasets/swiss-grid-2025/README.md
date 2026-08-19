
A **calibration case**: the Swiss electricity system as it actually ran in calendar year
2025, rebuilt in IESO and checked against observation.

Its purpose is not to answer a policy question. It exists to establish whether IESO
reproduces a real system before [`swiss-grid-2050`](../swiss-grid-2050/) is used to explore a
hypothetical one. This mirrors the method of OECD NEA report No. 7631, which calibrates its
POSY model against 2019 in Chapter 3.3 before running 2050 scenarios in Chapter 4.

```bash
python ieso.py datasets/swiss-grid-2025/swiss-grid---2025.json
```

About 2 seconds. There are no capacity variables — every capacity is observed — so only
dispatch is solved.

**Read the verdict below before using this.** The model balances and prices well, but it
gets reservoir hydro timing badly wrong, for reasons that matter to the 2050 case.

# Construction

Everything is one vintage: calendar 2025, ENTSO-E Transparency Platform, zone CH.

### Demand

```
demand = domestic load + exports = 62.07 + 23.21 = 85.28 TWh
```

Switzerland is a transit corridor, not an island: in 2025 it imported 15.8 TWh from France
and exported 16.1 TWh to Italy. Annually it was almost exactly balanced — 23.57 TWh in
against 23.21 TWh out, a net import of 0.36 TWh — but the monthly swing is large, importing
from October to March and exporting from April to September.

IESO has no revenue-earning sink, so exports cannot be optimised. Instead they are treated
as **exogenous demand the model must serve**, which closes the Swiss balance exactly:

```
generation + imports = load + exports
```

This is faithful for a backcast, where exports are known. It gives up the ability to model
export *arbitrage*, which matters — see the verdict.

### Supply, fixed from observation

Five technologies are pinned to their observed hourly output. Capacity is set to the
observed annual peak and `capacity_factor` to the observed annual mean over that peak, so
`cf_h` reproduces the measured series.

| `iden` | Source | Capacity | CF | Annual |
|---|---|---|---|---|
| `nucl` | B14 nuclear | 2 979 MW | 0.706 | 18.42 TWh |
| `rovr` | B11 run-of-river | 3 674 MW | 0.451 | 14.50 TWh |
| `solr` | B16 solar | 4 018 MW | 0.147 | 5.16 TWh |
| `wind` | B19 wind onshore | 76 MW | 0.228 | 0.15 TWh |
| `hpmp` | B10 pumped storage | 4 225 MW | 0.217 | 8.01 TWh |
| `dist` | residual, flat | 710 MW | 0.900 | 5.60 TWh |

**Outages come for free.** Swiss nuclear runs must-run baseload, so its observed output *is*
its availability — refuelling stops and unplanned trips are already in the series. Nuclear's
0.706 load factor against a 2 979 MW peak is what those outages look like. NEA 7631 achieves
the same thing by explicitly forcing historical outages and one refuelling stop per unit.

`dist` closes a real gap. ENTSO-E's Swiss generation reporting covers transmission-connected
units, so small hydro, rooftop PV and decentralised CHP are missing. The balance leaves
5.60 TWh unaccounted, which `dist` supplies as a flat must-run block. It is a residual, not
a measurement.

Pumped storage appears as a **fixed generator, not as storage**. ENTSO-E publishes its
turbining but returns null for pumping consumption, and Swiss load already includes pumping
demand. Modelling it as storage would double-count. The cost is that pumped cycling is not
validated here.

### Supply, free

**Reservoir hydro** (`hdam`) is the one genuine dispatch decision. Capacity 8 850 GWh over
**3 466 MW**, no grid charging, fed by an inflow of 9.85 TWh — set equal to observed reservoir
generation, since inflow is not published by ENTSO-E. Its *shape* is the melt-driven series
from POSY.

The discharge rating is the observed 2025 reservoir peak, not the 8.8 GW quoted in
NEA 7631 — that figure is the *clustered* reservoir-plus-pumped rating, and applying it to
reservoir alone gave the model 2.5x the turbine capacity Switzerland actually used. The
8 850 GWh volume is kept, since Swiss storage lakes serve both reservoir and pumped-storage
operation and the observed level swing is consistent with that basis. The mismatch between a
combined-basis volume and a reservoir-only inflow is a known residual inconsistency.

That makes annual reservoir energy **calibrated, not validated**. What is validated is the
*timing*: given melt-shaped inflow and real prices, does cost minimisation release the water
when Switzerland actually released it?

**Imports** are six tranches from the sextiles of the observed Swiss day-ahead curve, each
offering the full 8 900 MW NTC in the hours its price band occurred:

| Tranche | Hours | Price |
|---|---|---|
| `impo-1` | 1 461 | 37.8 USD/MWh |
| `impo-2` | 1 460 | 96.5 |
| `impo-3` | 1 464 | 109.6 |
| `impo-4` | 1 466 | 121.2 |
| `impo-5` | 1 450 | 137.0 |
| `impo-6` | 1 459 | 169.2 |

Six rather than the three used in the 2050 case, because validating against a real price
duration curve needs the resolution. Prices converted at 1.10 USD/EUR.

# Verdict

### What works

| Test | Result |
|---|---|
| Feasibility | solves, zero unserved energy |
| Annual imports | 23.60 TWh model vs **23.57 TWh** observed |
| Fixed generation | reproduced to within 0.02 TWh on every technology |
| Hourly price | correlation **+0.846**, mean 106.0 vs 111.9 USD/MWh observed |

The price result is the encouraging one, but it is **partly circular**: the tranche prices
are themselves derived from the observed curve. What the model genuinely chooses is which
tranche is marginal in each hour, and it lands close. Annual import volume matching is not
independent either — it is the residual once everything else is fixed.

### What fails

Reservoir dispatch, and it fails on **amplitude rather than timing**.

| | Model | Observed |
|---|---|---|
| January reservoir output | 2.43 TWh | 0.98 TWh |
| February | 2.31 TWh | 0.83 TWh |
| June | 0.07 TWh | 0.97 TWh |
| Monthly spread (sd) | 0.80 TWh | **0.17 TWh** |
| Mean absolute error, reservoir | **0.66 TWh/month** | — |
| Mean absolute error, imports | **0.67 TWh/month** | — |
| Minimum reservoir level | 1.2% in March | never approached |

Observed Swiss reservoir output is remarkably flat — 0.42 to 0.98 TWh every month, standard
deviation 0.17. The model swings from 0.07 to 2.43, standard deviation 0.80. It empties the
reservoir across January to March to capture the year's highest prices, runs it near-dry
until the melt, and buys cheap summer imports instead.

Correlation is the wrong statistic here: against a near-flat observed series it measures
noise. Mean absolute error is the honest metric, and it is reported above.

The **seasonal phase is right**. The modelled level peaks in September–October at 71% and
bottoms in March, which is when Swiss reservoirs really do peak and bottom. What is wrong is
the depth of the drawdown: reality bottoms near 20%, the model at 1.2%.

Autumn is reproduced well — October through December errors are 0.13, 0.09 and 0.07 TWh on
reservoir and 0.19, 0.02 and 0.00 TWh on imports. The failure is concentrated in the winter
drawdown and the summer dry spell that follows it.

### What the discharge-cap fix bought

The first version of this dataset gave `hdam` the 8 800 MW clustered rating. Correcting it to
the observed 3 466 MW:

| | Before | After |
|---|---|---|
| Peak reservoir output | 8 800 MW | **3 466 MW** (= observed) |
| Reservoir MAE | 0.737 | **0.659** TWh/month (11% better) |
| Imports MAE | 0.741 | **0.667** TWh/month (10% better) |
| Hourly price correlation | +0.846 | **+0.861** |
| Minimum level | 0.0% | 1.2% |

Worth doing — it makes the plant physically real and fixes autumn almost entirely — but it
closes only about a tenth of the gap. The rest is structural.

### Why

**Perfect foresight, principally.** NEA 7631 documents the same pathology for POSY: water is
held back in reality for "the option value of possibly selling at even higher prices later."
A deterministic LP has no option value — it knows December's prices in January, so holding
water back is strictly dominated. No parameter fixes this; it needs stochastic or
rolling-horizon optimisation.

**No minimum fill requirement.** Switzerland mandates a winter hydro reserve
(*Wasserkraftreserve*), on the order of 400–500 GWh. That is roughly 5% of storage — too
small on its own to explain the drawdown, and an earlier draft of this file overstated its
role. But combined with dead storage and minimum operating levels, a floor around 15–20%
would be defensible on physical grounds and would attack precisely the amplitude error,
which is the part that is actually wrong.

**No export revenue.** Exports enter as fixed demand, so the model cannot choose to generate
in summer and sell. Reality earns money exporting to Italy from April to September; the
model sees only an obligation it can meet with cheap imports.

# What this means for the 2050 case

The engine is sound: it balances, it prices, it handles inflow-fed storage and outage
profiles correctly. But **reservoir dispatch cannot be trusted without a minimum fill
constraint**, and the 2050 case currently has none either. Any 2050 result that turns on
winter hydro availability is therefore suspect until that is fixed.

That is precisely the kind of thing a calibration case exists to find, and it would have
gone unnoticed had the 2050 dataset been built alone.

# Next

- Add a minimum reservoir level. IESO's `l_strg[0]` bounds charge and discharge as well as
  level, so this needs a small extension — an optional `soc_min_profile` on the flexibility
  means. Since the error is amplitude and not phase, a floor is the right shape of fix
- Re-run and check the mean absolute error, not the correlation
- Source real inflow from SFOE weekly reservoir levels, so annual reservoir energy becomes a
  validation target rather than an input
- Pull hourly cross-border flows, replacing the current monthly export shaping
- Add export revenue, once IESO can represent it

# Attribution

Hourly load, generation, day-ahead price and cross-border flow series: ENTSO-E Transparency
Platform, calendar year 2025, zone CH. Reservoir inflow shape from **POSY** —
[git.oecd-nea.org/posy/posy](https://git.oecd-nea.org/posy/posy) — MIT licence, © 2023 OECD
Nuclear Energy Agency. Cost assumptions from **OECD NEA report No. 7631**,
[*Achieving Net Zero Carbon Emissions in Switzerland in 2050*](https://www.oecd-nea.org/jcms/pl_74877/achieving-net-zero-carbon-emissions-in-switzerland-in-2050-low-carbon-scenarios-and-their-system-costs?details=true),
OECD 2022 — though with all capacities fixed, only variable costs affect the result.

Solar and wind fixed costs use **IRENA**, *24/7 Renewables: The Economics of Firm Solar and
Wind*, Annexes B–D (Europe, 2025), for consistency with
[`swiss-grid-2050`](../swiss-grid-2050/). Because every capacity here is observed rather than
optimised, this changes the reported cost KPI but not a single dispatch decision.

This dataset contains no new-build nuclear or gas, so the **Lazard** *Levelized Cost of
Energy+* v19.0 figures used for those technologies in `swiss-grid-2050` do not apply here.
`nucl` represents long-term operation of the existing fleet and stays on the NEA 7631
refurbishment basis.
