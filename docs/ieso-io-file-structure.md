# IESO IO File Structure

#### Introduction

This article documents the input-output (IO) file structure used by the [Integrated Energy Systems Optimiser](https://github.com/greoux-research/ieso) (IESO), a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

IESO's modelling approach is described in [this article](ieso-modelling-approach.md). Installation and run instructions can be found in [the setup guide](ieso-setup-guide.md).

IESO is called with one or two arguments: (1) a JSON file (referred to as `input.json`) that describes the dataset, and (2) an optional carbon constraint. The output is a file named `input.ieso.json`. It mirrors `input.json` and adds the optimisation results in place.

---

#### A note on units and conventions

- Power is MW, energy is MWh; a PtX production capacity is Q per hour and a storage capacity is Q, where Q is m³ of water, kg of hydrogen or MWh of heat.
- Fractions are fractions, not percentages: `capacity_factor`, `round_trip_efficiency`, `soc_ini` and `non-served-power-constraint` all take values in [0, 1].
- Capacity set to `-1` is optimised; any other value pins it.
- Demand balances are **inequalities**: supply must meet demand in each hour and may exceed it. Surplus is possible and is not itself an error, but it is not reported as a separate quantity — if a system is producing more than it delivers, that shows up in the allocation shares rather than as a stated surplus.

---

#### High-level overview

An IESO dataset defines primary demands (electricity and X commodities: heat, hydrogen, water) and the supply and flexibility options that meet them. The JSON below shows the top-level structure.

```json
{
    "demand": {
        "e": {"iden": "electricity", ...},
        "x": [
            {"iden": "heat", ...},
            {"iden": "hydrogen", ...},
            {"iden": "water", ...}
        ]
    },
    "p2x": [...],
    "generator": [...],
    "flex": [...],
    "solver": {...}
}
```

The five top-level objects are: `demand` (electricity and X), `p2x` (Power-to-X processes), `generator` (power generators), `flex` (flexibility means), and `solver` (linear solver summary).

The philosophy of IESO is to first define the demand and its hourly profile, and then describe how this demand is met:

- Electricity demand — whether primary (final consumption) or secondary (for battery charging or the operation of PtX processes) — is always met by the "grid", i.e. the mix of available generators.
- Demand for commodity X (heat, hydrogen, water) is met by PtX processes, which consume electricity from the "grid" and, where relevant, heat from cogeneration plants.

---

#### Demand objects

Demand objects represent the final consumption of electricity and other commodities (heat, hydrogen, water). Each demand entry follows a consistent structure.

**Demand for electricity**

```json
{
    "iden": "electricity",
    "profile": "profiles/mid-west/dmnd.csv",
    "total": 50e+6,
    "supply_sources": [],
    "var_cost_ns": 20000,
    "l_ns": [0, 1000e+3],
    "output_ns": [],
    "shadow_prices": {
        "demand_match": [],
        "carbon_cap": -1,
        "reliability_cap": -1
    },
    "kpis": {
        "cost": -1,
        "emis": -1,
        "reli": -1
    }
}
```

**Demand for other commodities (heat, hydrogen, water)**

```json
{
    "iden": "hydrogen",
    "profile": "",
    "total": 35e+6,
    "supply_sources": ["p2x-h2"],
    "var_cost_ns": 1000,
    "l_ns": [0, 1e+9],
    "output_ns": [],
    "shadow_prices": {
        "demand_match": []
    },
    "kpis": {
        "cost": -1,
        "emis": -1,
        "reli": -1
    }
}
```

##### General attributes

- `iden` — identifier (*electricity*, *heat*, *hydrogen*, or *water*)
- `total` — annual demand (MWh, kg, or m³ depending on commodity)
- `profile` — optional CSV with 8760 hourly values. May be provided as (1) a CSV file path, (2) an array of 8760 values, or (3) empty for a flat profile.
- `supply_sources` — PtX processes supplying the X commodity (a list of `iden` of PtX processes is expected here)
- `var_cost_ns` — penalty for unmet demand (\$/MWh, \$/kg, \$/m³)
- `l_ns` — lower and upper bounds applied to **each hourly** unmet-demand variable, not to the annual total. `[0, 0]` therefore forces full service in every hour. There is no annual cap on unmet demand for an X commodity; the optional `non-served-power-constraint` run option caps annual unmet **electricity** only.

##### Outputs

- `output_ns` — hourly unmet demand
- `shadow_prices["demand_match"]` — hourly shadow prices (\$/unit), i.e. the hourly marginal value of meeting one additional unit of demand. Corresponds to the dual variable of the demand-balance constraint, reflecting the system cost reduction associated with a 1-unit increase in demand satisfaction during that hour. Defined for both electricity and all other commodities X.
- `shadow_prices["carbon_cap"]` — marginal value of relaxing the carbon cap by one unit (\$/unit), or `0` when the cap is not binding. Electricity demand only.
- `shadow_prices["carbon_cap_detail"]` — what was observed, kept separate from the interpretation above: `raw_dual`, `cap`, `activity`, `slack`, `binding`, and `binding_zero_dual`. The last records an observation and not a diagnosis: a binding row whose dual is zero may be degenerate, or its marginal value may genuinely be zero and unique — a cap set exactly where the solution would have landed anyway binds and is worth nothing. Telling those apart requires analysis IESO does not perform.
- `shadow_prices["reliability_cap"]` — marginal value of relaxing the annual unmet-electricity cap by one unit (\$/unit), or `0` when that cap is not binding. Electricity demand only.
- `shadow_prices["reliability_cap_detail"]` — as for the carbon cap.
- `kpis["cost"]` — **compatibility field, retained with its original formula**: `(allocated resource cost + shortage penalty) / annual demand` (\$/unit). Two cautions. It adds the penalty charged on unserved demand to the money actually spent on supply, and it divides by demand rather than by the volume delivered — so it is not a cost per unit delivered. Prefer the `accounts` fields below.
- `kpis["emis"]` — average emissions per unit of annual demand (kg CO₂eq/unit), on the same allocation.
- `kpis["reli"]` — share of annual demand served. An annual energy ratio, not a security-of-supply metric and not a guarantee about any individual hour.
- `accounts` — the quantities behind the cost KPI, reported separately:
    - `allocation_share` — this commodity's share of total electricity-equivalent output, the basis on which system cost and emissions are allocated. `null` if the system produced no output, in which case there is nothing to allocate and the fields derived from it are `null` too.
    - `resource_cost` — system cost allocated to this commodity (\$). Excludes shortage penalties.
    - `shortage_penalty` — `unmet_demand × var_cost_ns` (\$). A modelled price on a shortfall, not expenditure on supply.
    - `emissions` — emissions allocated to this commodity (kg CO₂eq).
    - `demand`, `unmet_demand`, `served_demand` — annual volumes.
    - `resource_cost_per_demand`, `resource_cost_per_served` — resource cost per unit demanded and per unit actually delivered (\$/unit). The second is `null` when nothing was delivered.

The allocation of joint system cost in proportion to electricity-equivalent consumption is a **convention**, not a measurement. In a system where a PtX process is a large share of load it determines how cost divides between commodities, and it should be stated wherever these figures are reported.

---

#### Power-to-X (PtX) processes &nbsp;|&nbsp; [Modelling approach →](ieso-modelling-approach.md#ptx-processes)

PtX processes convert electricity, and sometimes heat, into products such as hydrogen, water, or heat. Each process combines general attributes, a production unit, and a storage unit.

<div align="center">
<img src="assets/power-to-x.png" width="380px" alt="IESO Representation of a PtX Process">
</div>

**Electricity-consuming process (e.g., RO)**

```json
{
    "iden": "p2x-ro",
    "profile": "",
    "capacity_factor": 0.850,
    "type": "elec",
    "temperature": 0,
    "supply_sources": [],
    "fix_cost_strg": 0.22,
    "l_strg": [0, 2190e+6],
    "c_strg": -1,
    "x_strg": [],
    "fix_cost_prod": 2070,
    "var_cost_prod": 0.35,
    "pow_use_elec_prod": 4.5e-3,
    "pow_use_ther_prod": 0,
    "l_prod": [0, 1e+6],
    "c_prod": -1,
    "x_prod": [],
    "soc_ini": 1.0,
    "x_supp": [],
    "shadow_prices": {
        "demand_match": []
    }
}
```

**Electricity- and heat-consuming process (e.g., MED)**

```json
{
    "iden": "p2x-med",
    "profile": "",
    "capacity_factor": 0.850,
    "type": "elec + ther",
    "temperature": 80,
    "supply_sources": ["nucl", "coal", "ccgt"],
    "fix_cost_strg": 0.22,
    "l_strg": [0, 2190e+6],
    "c_strg": -1,
    "x_strg": [],
    "fix_cost_prod": 2185,
    "var_cost_prod": 0.26,
    "pow_use_elec_prod": 1.5e-3,
    "pow_use_ther_prod": 50e-3,
    "l_prod": [0, 1e+6],
    "c_prod": -1,
    "x_prod": [],
    "soc_ini": 1.0,
    "x_supp": [],
    "shadow_prices": {
        "demand_match": []
    }
}
```

##### General attributes

- `type` — *elec* (electric only) or *elec + ther* (electricity plus heat)
- `temperature` — required steam extraction temperature (°C, thermal processes only)
- `capacity_factor` — as for generators: a fraction, the target annual mean of the rescaled profile, and a flat hourly ceiling when no profile is given.
- `profile` — optional hourly shape with 8760 values, as (1) a CSV file path, (2) a list or array of 8760 values, or (3) empty for a flat profile. **A profile supplies shape only.** It is divided by its own maximum and then rescaled so that its mean equals `capacity_factor`, so the level is set by `capacity_factor` and the profile's own average is discarded. One consequence matters: where `capacity_factor` exceeds the profile's own mean/max ratio, the rescaled series passes one, and output is then held to the installed capacity by an explicit nameplate limit rather than by the availability relation. Values must be finite, non-negative, and not all zero.
- `supply_sources` — thermal generators supplying heat in cogeneration mode (a list of generator `iden`). A process may draw on several generators. A generator may supply **only one** process: each process carries its own heat balance against the same heat variables, so two processes sharing a generator would each be satisfied by the same heat. Such a configuration is rejected before the problem is built, as is a shared generator serving processes at different extraction temperatures.

##### Production unit

- `c_prod` — production capacity (Q/hour). Will be optimised by the solver if set to -1
- `l_prod` — lower and upper bounds on the **installed production capacity** `c_prod` (Q/hour). They bound neither the hourly production rate nor the hourly delivery rate; delivery draws on the store and may exceed the production rate.
- `fix_cost_prod` — fixed production costs (\$ per (Q/hour) per year)
- `var_cost_prod` — variable costs excluding energy (\$/Q)
- `pow_use_elec_prod` — electricity use (MWh/Q)
- `pow_use_ther_prod` — heat use (MWh/Q)

##### Storage unit

- `c_strg` — storage capacity (Q). Will be optimised by the solver if set to -1
- `l_strg` — lower and upper bounds on the **installed storage capacity** `c_strg` (Q), not on the hourly inventory.
- `fix_cost_strg` — fixed storage costs (\$ per Q per year)
- `soc_ini` — the inventory at the start of the year, as a fraction of `c_strg`. The year is closed on the same level: the store ends where it began, so nothing is created or consumed by the boundary. Seasonal accumulation within the year is permitted.

##### Outputs

- `x_prod` — hourly production (Q/hour)
- `x_strg` — storage level (Q)
- `x_supp` — hourly supply (Q/hour)
- `shadow_prices["demand_match"]` — hourly shadow heat supply prices (\$/MWh of heat), the dual of this process's heat balance. Applies to thermally coupled processes only; a purely electric process (reverse osmosis, electrolysis) has no heat constraint and the series is empty. This is the price of *heat into the process*, and is distinct from the delivery price of the product itself, which is `shadow_prices["demand_match"]` on the corresponding demand object.

---

#### Generators &nbsp;|&nbsp; [Modelling approach →](ieso-modelling-approach.md#generators)

Generators represent technologies that produce electricity, heat, or both. Dispatchable units (nuclear, coal, CCGT) may use only a capacity factor, while variable renewables (solar, wind) require hourly profiles.

<div align="center">
<img src="assets/generator.png" width="160px" alt="IESO Representation of a Generator">
</div>

**Electricity-generating plant — variable (e.g., wind)**

```json
{
    "iden": "wind",
    "profile": "profiles/florida/wind.csv",
    "capacity_factor": 0.250,
    "type": "elec",
    "fix_cost_prod": 133553,
    "var_cost_prod": 6e-6,
    "var_emis_prod": 0,
    "l_prod": [0, 100e+3],
    "c_prod": -1,
    "e_prod": [],
    "h_prod": [],
    "turbine_t_p": [],
    "condenser_p": 0,
    "a": 0,
    "b": 0
}
```

**Electricity-generating plant — fully dispatchable (e.g., OCGT)**

```json
{
    "iden": "ocgt",
    "profile": "",
    "capacity_factor": 0.850,
    "type": "elec",
    "fix_cost_prod": 75182,
    "var_cost_prod": 96.11,
    "var_emis_prod": 523,
    "l_prod": [0, 100e+3],
    "c_prod": -1,
    "e_prod": [],
    "h_prod": [],
    "turbine_t_p": [],
    "condenser_p": 0,
    "a": 0,
    "b": 0
}
```

**Cogeneration plant (e.g., CCGT)**

```json
{
    "iden": "ccgt",
    "profile": "",
    "capacity_factor": 0.850,
    "type": "elec + ther",
    "fix_cost_prod": 98749,
    "var_cost_prod": 56.44,
    "var_emis_prod": 365,
    "l_prod": [0, 100e+3],
    "c_prod": -1,
    "e_prod": [],
    "h_prod": [],
    "turbine_t_p": [564, 152],
    "condenser_p": 0.05,
    "a": 0,
    "b": 0
}
```

##### General attributes

- `type` — *elec* or *elec + ther* (thermal generators eligible to supply heat in cogeneration mode)
- `profile` — empty for dispatchable units, required for renewables. Hourly shape with 8760 values, as (1) a CSV file path, (2) a list or array of 8760 values, or (3) empty for a flat profile. **A profile supplies shape only.** It is divided by its own maximum and then rescaled so that its mean equals `capacity_factor`, so the level is set by `capacity_factor` and the profile's own average is discarded. One consequence matters: where `capacity_factor` exceeds the profile's own mean/max ratio, the rescaled series passes one, and output is then held to the installed capacity by an explicit nameplate limit rather than by the availability relation. Values must be finite, non-negative, and not all zero.
- `capacity_factor` — a **fraction**, not a percentage. With a profile it is the target annual mean of the rescaled series; without one it is a flat ceiling applied in every hour. It is not an annual energy budget and does not represent scheduled maintenance: a unit may run at that fraction of nameplate in all 8760 hours. To represent an outage, give a profile that is zero in the affected hours and set `capacity_factor` to the resulting availability, so the series peaks at one.
- `l_prod` — lower and upper bounds on the **installed capacity** `c_prod` (MW). They do not bound hourly output: a positive lower bound requires the capacity to be built, not to be run.
- `c_prod` — installed capacity (MW). Will be optimised by the solver if set to -1

##### Costs and emissions

- `fix_cost_prod` — fixed costs (\$/MW/year)
- `var_cost_prod` — variable costs (\$/MWh)
- `var_emis_prod` — emissions (kg CO₂eq/MWh)

##### Cogeneration parameters

- `turbine_t_p` — turbine inlet temperature (°C) and pressure (bar)
- `condenser_p` — condenser pressure (bar)
- `a`, `b` — coefficients describing the electricity–heat trade-off (calculated by IESO)

##### Outputs

- `e_prod` — hourly electricity production (MWh)
- `availability` — what the profile asked for against what it delivered, so the effect of the nameplate limit is visible rather than absorbed into the result: `capacity_factor_requested`, `profile_peak` (the maximum of the rescaled series), `hours_above_nameplate`, and `capacity_factor_effective` (the mean availability remaining once output is held to the installed capacity). Where the peak is at or below one, the requested and effective figures agree.
- `h_prod` — hourly heat production (MWh)

---

#### Flexibility means &nbsp;|&nbsp; [Modelling approach →](ieso-modelling-approach.md#flexibility-means)

Flexibility means represent energy storage systems such as batteries or pumped hydro. They allow electricity to be shifted in time with round-trip efficiency losses.

<div align="center">
<img src="assets/flexibility-means.png" width="200px" alt="IESO Representation of Flexibility Means">
</div>

```json
{
    "iden": "bstr",
    "fix_cost_strg": 27248,
    "hours_of_storage": 4,
    "round_trip_efficiency": 0.85,
    "l_strg": [0, 400e+3],
    "c_strg": -1,
    "e_strg": [],
    "soc_ini": 0.5,
    "soc_min": 0,
    "soc_max": 1,
    "e_char": [],
    "e_disc": []
}
```

##### General attributes

- `fix_cost_strg` — annual fixed costs (\$/MWh/year)
- `hours_of_storage` — storage duration at maximum discharge (hours). Charge and discharge power are limited to `c_strg / hours_of_storage`, which is what relates the power rating (MW) to the energy rating (MWh).
- `round_trip_efficiency` — round-trip efficiency (in [0, 1])
- `soc_ini` — initial state of charge (fraction of `c_strg`)
- `soc_min` — minimum state of charge (fraction of `c_strg`, default 0). Use it to represent dead storage, minimum operating levels, or a regulatory reserve such as the Swiss *Wasserkraftreserve*
- `soc_max` — maximum state of charge (fraction of `c_strg`, default 1). Use it to hold back head room, for instance for flood control
- `l_strg` — lower and upper bounds on the **installed energy capacity** `c_strg` (MWh). They bound neither the hourly inventory, which follows the state-of-charge limits, nor the charge and discharge powers (MW), which follow the duration limit above.
- `c_strg` — storage capacity (MWh). Will be optimised by the solver if set to -1

##### Natural inflow (optional)

Reservoir hydro is represented by a flexibility means that is replenished by an exogenous
inflow — rainfall, snowmelt, glacier melt — rather than by charging from the grid.

- `inflow_total` — annual inflow energy (MWh). Absent or 0 means no inflow, and the object behaves as a conventional storage device
- `inflow_profile` — hourly shape of the inflow. May be provided as (1) a CSV file path, (2) an array of 8760 values, or (3) empty for a flat profile. Scaled so that its sum equals `inflow_total`
- `charge_allowed` — set to `false` to forbid charging from the grid (default `true`). A dam fed only by its catchment should set this to `false`, so that it cannot act as free pumped storage

`soc_ini` must lie between `soc_min` and `soc_max`, and the storage level is held within
those bounds at every hour:

$$
\text{soc}_\text{min} \times c_\text{strg} \le e_\text{strg}(i) \le \text{soc}_\text{max} \times c_\text{strg}
$$

Leaving both at their defaults reproduces Equation 11 exactly.

With inflow present, the storage balance of Equation 13 gains two terms:

$$
e_\text{strg}(i) = e_\text{strg}(i-1) + e_\text{infl}(i) - e_\text{spil}(i) + \sqrt{r_\text{strg}} \times e_\text{char}(i) - e_\text{disc}(i) / \sqrt{r_\text{strg}}
$$

Inflow is not subject to the round-trip penalty, since water arriving in a reservoir has not
been pumped there. The spill variable $e_\text{spil}$ is free and allows water to be released
without generating; without it, inflow arriving at a full reservoir would make the problem
infeasible rather than spill, as a real dam does.

##### Outputs

- `e_strg` — energy stored (MWh)
- `e_char` — charging power (MW)
- `e_disc` — discharging power (MW)
- `e_spil` — spilled inflow (MWh). Present only when `inflow_total` > 0

---

#### System object

Totals for the run as a whole, reported directly rather than through the
commodity allocation.

##### Outputs

- `cost` — total system cost (\$): fixed capacity charges plus variable costs, for every generator, flexibility means and PtX process. Excludes shortage penalties.
- `output` — total electricity-equivalent output (MWh), the denominator of every allocation share.
- `emis` — total emissions (kg CO₂eq).
- `allocated_share_total` — sum of the commodity allocation shares. Every unit of output belongs to exactly one demand, so this must equal 1; a departure means output is being counted twice or not at all.

#### Provenance object

Written into every result, identifying what produced it.

##### Outputs

- `ieso_version` — release identifier of the code that solved the problem.
- `input`, `input_sha256` — the input file and its SHA-256 digest.
- `profiles_sha256` — each referenced profile file and its digest. Profiles are named by path rather than carried in the input, and they determine the answer as directly as anything inside it.
- `options` — the `name=value` options applied to the run.
- `hours`, `storage_closes_the_year` — the horizon, and whether storage is required to end the year where it began.
- `git_revision`, `git_dirty` — the commit the tree is on, and whether it still matches it. Both are `null` outside a Git checkout.
- `source_sha256`, `source_files_sha256` — a digest over `ieso.py`, every module in `ieso_modules/`, and the compiled `thermo/sim.bin`, with the per-file digests beside it. The version string is a label that two different trees can share; this identifies the code that actually ran, including the untracked binary that sets the cogeneration coefficients.
- `solver`, `ortools` — the solver and its version. This matters: a different build may settle on a different vertex of the same optimal face, so two runs agreeing on cost can differ hour by hour.
- `numpy`, `python`, `platform`, `run_utc` — the rest of the environment, and when the run happened.

---

#### Solver object &nbsp;|&nbsp; [Modelling approach →](ieso-modelling-approach.md#linear-optimisation-problem)

The solver object provides diagnostics for each optimisation run: status, run time, and problem size.

##### Outputs

- `stat_succ` — 1 if the solve reached an optimal solution, 0 if it did not, -1 before the run. **IESO also exits non-zero when the solve was unsuccessful**, so a calling script need not read the result to find out.
- `stat_status` — why, in words: `optimal`, `infeasible`, `unbounded`, `abnormal (numerical trouble)`, `not solved`. **A run that does not reach an optimal solution still writes an output file**, structured like any other, with the input values echoed back in place of results. Check this field before reading anything else.
- `stat_time` — elapsed time (seconds)
- `stat_capa` — number of capacity variables
- `stat_outp` — number of output variables
- `stat_cons` — total number of constraints

> **Note.** The objective minimised by the solver omits fixed capacity charges for
> assets whose capacity is *fixed* by the input (`c_prod` or `c_strg` set rather
> than `-1`), because a constant cannot change the optimum. `cost` above includes
> them. When comparing the two, reconcile with
> `system cost + shortage penalties = solver objective + fixed-capacity charges`.
