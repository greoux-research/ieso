# IESO IO File Structure

#### Introduction

This article documents the input-output (IO) file structure used by the [Integrated Energy Systems Optimiser](https://github.com/greoux-research/ieso) (IESO), a linear optimiser-based energy system modelling environment designed to support initial investigations such as options evaluation and trend analysis.

IESO's modelling approach is described in [this article](ieso-modelling-approach.md). Installation and run instructions can be found in [the setup guide](ieso-setup-guide.md).

IESO is called with one or two arguments: (1) a JSON file (referred to as `input.json`) that describes the dataset, and (2) an optional carbon constraint. The output is a file named `input.ieso.json`. It mirrors `input.json` and adds the optimisation results in place.

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
- `l_ns` — lower and upper bounds on annual unmet demand

##### Outputs

- `output_ns` — hourly unmet demand
- `shadow_prices["demand_match"]` — hourly shadow prices (\$/unit), i.e. the hourly marginal value of meeting one additional unit of demand. Corresponds to the dual variable of the demand-balance constraint, reflecting the system cost reduction associated with a 1-unit increase in demand satisfaction during that hour. Defined for both electricity and all other commodities X.
- `shadow_prices["carbon_cap"]` — carbon constraint shadow price (\$/unit). Measures the implicit cost of relaxing the system-wide carbon emission limit by one unit. Applies only to the primary electricity demand, since the emission constraint is global and directly linked to total electricity generation.
- `shadow_prices["reliability_cap"]` — reliability constraint shadow price (\$/unit). Measures the marginal system cost of relaxing the reliability requirement by one unit of served electricity. Also applies only to the primary electricity demand, reflecting the upper constraint on non-served electricity.
- `kpis["cost"]` — average cost per unit of delivered output (\$/unit). Derived from the total system cost (fixed + variable) incurred to meet all demands, allocated to each demand category in proportion to its electricity consumption.
- `kpis["emis"]` — average emissions per unit of delivered output (kg CO₂eq/unit). Follows the same allocation principle as cost, i.e. emissions are distributed on the basis of electricity use.
- `kpis["reli"]` — reliability factor (%). Expresses the system's ability to continuously meet the hourly demand for electricity or any other commodity X throughout the year. Quantifies the proportion of total demand that is effectively served.

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
- `capacity_factor` — capacity factor of the plant (fraction)
- `profile` — optional CSV with 8760 hourly values. May be provided as (1) a CSV file path, (2) an array of 8760 values, or (3) empty for a flat profile.
- `supply_sources` — thermal generators eligible to supply heat in cogeneration mode (a list of `iden` of thermal generators is expected here)

##### Production unit

- `c_prod` — production capacity (Q/hour). Will be optimised by the solver if set to -1
- `l_prod` — lower and upper bounds (Q/hour)
- `fix_cost_prod` — fixed production costs (\$ per (Q/hour) per year)
- `var_cost_prod` — variable costs excluding energy (\$/Q)
- `pow_use_elec_prod` — electricity use (MWh/Q)
- `pow_use_ther_prod` — heat use (MWh/Q)

##### Storage unit

- `c_strg` — storage capacity (Q). Will be optimised by the solver if set to -1
- `l_strg` — lower and upper bounds (Q)
- `fix_cost_strg` — fixed storage costs (\$ per Q per year)
- `soc_ini` — initial state of charge (fraction of `c_strg`)

##### Outputs

- `x_prod` — hourly production (Q/hour)
- `x_strg` — storage level (Q)
- `x_supp` — hourly supply (Q/hour)
- `shadow_prices["demand_match"]` — hourly shadow heat supply prices (\$/MWh). Applies to thermal processes only. These are thermally coupled to cogeneration units through heat extraction constraints.

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
- `profile` — empty for dispatchable units, required for renewables (CSV, 8760 values). May be provided as (1) a CSV file path, (2) an array of 8760 values, or (3) empty for a flat profile.
- `capacity_factor` — capacity factor of the plant (fraction)
- `l_prod` — lower and upper bounds (MW)
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
    "e_char": [],
    "e_disc": []
}
```

##### General attributes

- `fix_cost_strg` — annual fixed costs (\$/MWh/year)
- `hours_of_storage` — storage duration at maximum discharge
- `round_trip_efficiency` — round-trip efficiency (in [0, 1])
- `soc_ini` — initial state of charge (fraction of `c_strg`)
- `l_strg` — lower and upper bounds (MWh)
- `c_strg` — storage capacity (MWh). Will be optimised by the solver if set to -1

##### Outputs

- `e_strg` — energy stored (MWh)
- `e_char` — charging power (MW)
- `e_disc` — discharging power (MW)

---

#### Solver object &nbsp;|&nbsp; [Modelling approach →](ieso-modelling-approach.md#linear-optimisation-problem)

The solver object provides diagnostics for each optimisation run: status, run time, and problem size.

##### Outputs

- `stat_succ` — solver status (-1 initial, 0 failed, 1 success)
- `stat_time` — elapsed time (seconds)
- `stat_capa` — number of capacity variables
- `stat_outp` — number of output variables
- `stat_cons` — total number of constraints
