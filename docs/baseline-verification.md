# Baseline verification

> **Evidence kept outside the repository (since 2026-09-27).** Two items are
> retained locally by the maintainer and are identified here by name and
> checksum, not by location:
>
> | Item | Identified by | SHA-256 |
> |---|---|---|
> | Pre-commit evidence archive `ies-optimiser-archive-2026-09-27-precommit/`: the historical `runs/`, old `dist/` artifacts and the standalone `thermo/sim.bin`, at their original relative paths | its `MANIFEST.json`, which records each archived file's path, size, SHA-256 and whether it was tracked | `182a0d243ac2f89a94ecc3a4d9b146fdf6670a6012bad5c0cc7b6b70f66af098` |
> | Git history bundle `ieso-history.bundle`: the repository history before the re-upload, with the tags `v25.10` and `v26.05` | the file itself | `925c6f8038af80d4af35445bc016ab5593c4bfde7f2271c590f50cc8a2e0e7f9` |
>
> This repository starts at the re-upload commit and does not contain the
> commits cited below. Run the historical `git show` commands in a clone of the
> bundle, whose last commit `430d2fc` holds the code the re-upload was made from:
>
> ```bash
> git clone ieso-history.bundle ieso-history && cd ieso-history
> ```
>
> Paths of the form `runs/…`, `dist/…` and `thermo/sim.bin` below refer to the
> archive where the files are no longer in this checkout; `results/` is
> unchanged. The bundle's verification is recorded under "History and workflows
> recovered", at the end of this record.
>
> **Placeholders.** Machine-specific paths in this record are written as
> `<checkout>` (the repository checkout), `<workspace>` (the directory containing
> it), `<scratch>` (a temporary directory on the verification machine) and
> `<maintainer-local>` (a location kept by the maintainer outside the
> repository). Results under `results/` record the actual paths of the runs
> that produced them in their `provenance`, and are left as produced.

Record of the reference state established before any corrective change, as
required by the IESO correction and verification plan (Revision 3.1, stage 1).

## Where the historical results are

The eight pre-correction results this record verifies against were stored
beside their inputs under `datasets/`, and the sample profiles under
`profiles/`, until 2026-09-26. Both were then removed from the checkout — the
datasets now carry their own profiles, and current results are in
`results/` — but nothing was removed from Git history. **Throughout this
record, paths of the form `datasets/…/*.ieso*.json` and `profiles/…` refer to
commit `44db59105e1f7b37356976fd15df0f51e7c567fe`** (`44db591`, on `main`), not to the current tree.

The datasets themselves were later replaced by the illustrative island cases
(see the last section). Everything this record says about `elec-grid`,
`power-to-hydrogen`, `power-to-water-med`, `swiss-grid-2025`, `swiss-grid-2050`
and `results/2026-09-26/` describes those earlier datasets, which are at commit
`aa761ef` (inputs with their local profiles, and the verified results).

| Path at `44db591` | SHA-256 |
|---|---|
| `datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---nyiso.ieso.carbon-constraint_50.0.non-served-power-constraint_0.05.json` | `268bbdbfc09cb4f4ddae7fe49948691faeb3cc8ab895430ca0364e0666289ec2` |
| `datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---nyiso.ieso.json` | `9d4f4a27aa4171e9a6679023d8c408856f8c0f5fe54d6a64dce5b7b5a5818d60` |
| `datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med---florida.ieso.carbon-constraint_50.0.non-served-power-constraint_0.05.json` | `f530bef0cf0c4e73ce6f4bf3b46ca5fa063ea8239274c7659f78dddd797f2dda` |
| `datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med---florida.ieso.json` | `0c5914741aba0666c5ff995b7f57ad2ac876691eb9e39d42f4f86eef8585dba8` |
| `datasets/elec-grid/elec-grid---mid-west.ieso.carbon-constraint_50.0.non-served-power-constraint_0.05.json` | `a7d8d96beb3331ae6521037fca6a712fc35c648957578086afeb601b0f204113` |
| `datasets/elec-grid/elec-grid---mid-west.ieso.json` | `729946cb46852990df7abc37e3dee35538385e90eaea1baf13e9246f83ca45fa` |
| `datasets/swiss-grid-2025/swiss-grid---2025.ieso.json` | `5494c86c57ed9e43450331abba9227ac84244a31675542439df7d2528a0237b2` |
| `datasets/swiss-grid-2050/swiss-grid---2050.ieso.json` | `b474e5d3500edbcbb6d657182cd3d295bde7efb5e3ef36f2627c4673ad853eb6` |

To retrieve one, or all eight, into the ignored `runs/` directory:

```bash
mkdir -p runs/archived
git show 44db591:datasets/elec-grid/elec-grid---mid-west.ieso.json > runs/archived/elec-grid---mid-west.ieso.json
git ls-tree -r --name-only 44db591 -- datasets | grep '\.ieso' | while read p; do
    git show "44db591:$p" > "runs/archived/$(basename "$p")"; done
shasum -a 256 runs/archived/*.json        # compare with the table above
```

Compare a corrected result against its pre-correction counterpart with the
comparator's legacy mode (the corrected results for these datasets are also
retrieved from Git, at `aa761ef`):

```bash
git show aa761ef:results/2026-09-26/eg-base.ieso.json > runs/archived/eg-base.corrected.ieso.json
tools/compare_outputs.py runs/archived/eg-base.corrected.ieso.json \
    runs/archived/elec-grid---mid-west.ieso.json --legacy
```

## Baseline

| | |
|---|---|
| Commit | `a3ff7a5932fe73088d14d38385969022a9e0ec78` |
| Date | 2026-08-19 |
| Tracked files | 107 |
| Python | 3.14.4 |
| NumPy | 2.5.2 |
| OR-Tools | 9.15.6755 |
| Platform | Linux 6.18.33.2-microsoft-standard-WSL2 |
| `thermo/sim.bin` | built from source with `thermo/build.sh` (g++) |

`thermo/sim.bin` is not tracked and must be built before any thermally coupled
case is solved. It reproduces the cogeneration coefficients embedded in the
archived MED result exactly — `sim.bin 290 70 0.05 80` returns
`0.124272 1.97657` against the archived `a = 0.1243`, `b = 1.9766`.

## Reproduction of the eight archived scenario results

All eight archived configurations were re-solved from unmodified `a3ff7a5`
using `tools/run_cases.sh`, and compared with `tools/compare_outputs.py`
(rtol 1e-9, atol 1e-6; `stat_time` excluded as wall-clock).

| Case | Result |
|---|---|
| `elec-grid` base | identical |
| `elec-grid` carbon + reliability | identical |
| `power-to-hydrogen` base | identical |
| `power-to-hydrogen` carbon + reliability | identical |
| `power-to-water-med` base | identical |
| `power-to-water-med` carbon + reliability | identical |
| `swiss-grid-2025` base | identical |
| `swiss-grid-2050` base | alternative optimum — see below |

Run times on the recorded environment totalled about 40 minutes, from 3 s
(`swiss-grid-2025`) to 779 s (`power-to-water-med` base).

### Legacy placeholder schema

Six archived results write the KPI cost placeholder for **inactive** commodities
(those with `total = 0`) as `[-1, -1]`; the current code writes `-1`. Active
commodities agree to every printed digit. `ieso_modules/pos_dmd.py` is unchanged
across the whole history of this repository, so no commit here can emit
`[-1, -1]`: those results were generated by code that predates
`b9090e7 "IESO repo re-created"` (2025-10-17) and is not in this repository.

This is the substance of the traceability gap: the archived results carry no
code, input or solver identification, and six of the eight cannot be attributed
to any commit. It is the reason new results are stamped with provenance.

### `swiss-grid-2050`: a degenerate optimum

The re-solve returns a different vertex. It is cost-equivalent, not a regression:

| | Re-solve | Archived | Relative difference |
|---|---|---|---|
| Total system cost | 6,291,208,282.0225 | 6,291,208,282.0224 | 4.1e-15 |
| Total emissions | 1,903,692,038.9108 | 1,903,692,038.9113 | 2.4e-13 |
| `demand.e` cost KPI | 74.014215082610 | 74.014215082609 | 4.8e-15 |
| Non-served electricity | 0 | 0 | — |
| All installed capacities | — | — | identical |

The mechanism is identifiable rather than assumed. `solr` and `wind` both carry
zero variable cost and their capacities are equal in the two solutions, so the
208 MWh shifted between them over the year (`solr` +208, `wind` −208) is exactly
cost-neutral. The `impo-1/2/3` differences are re-timings that leave each
import's annual total unchanged, and the `hdam`/`hpmp` trajectories differ while
their annual discharge totals agree.

Code and input are identical to the archived run in this case — the archived
`swiss-grid-2050` result was committed at `a3ff7a5` itself. The remaining
difference is therefore attributable to the solver build, which the archived
result does not record. Same source, same input, different GLOP: a different
vertex of the same optimal face.

`swiss-grid-2050` is consequently a **known-degenerate case**. It is a valid
check on objective value, capacities and physical balances, and is not a valid
check on hourly dispatch.

## Reproducing this

```bash
thermo/build.sh                 # once, for thermally coupled cases
tools/run_cases.sh runs/check   # writes outside datasets/
tools/compare_outputs.py runs/check/med-base.ieso.json \
    runs/archived/elec-grid+power-to-water-med---florida.ieso.json --legacy
```

(The archived file is retrieved from Git as described at the top of this
record. As first written, this compared against it in place under
`datasets/`, and without `--legacy`, which did not exist then; run against the
current code it reports the documented corrections as differences.)

`tools/run_cases.sh` copies each input into the run directory before solving, so
nothing under `datasets/` is ever overwritten. It replaces
`re-run-all-datasets.sh`, which began by deleting the stored results.

---

# Stage 2 verification — input handling and reporting

All eight configurations were re-solved with the corrected code and compared
with the stage 1 baseline under the same pinned environment.

| Case | Result |
|---|---|
| `elec-grid` base | identical |
| `power-to-hydrogen` base | identical |
| `power-to-water-med` base | water cost and emission KPIs change (R1); everything else identical |
| `swiss-grid-2025` base | identical |
| `swiss-grid-2050` base | identical |
| `elec-grid` carbon + reliability | alternative optimum |
| `power-to-hydrogen` carbon + reliability | alternative optimum |
| `power-to-water-med` carbon + reliability | alternative optimum, plus R1 and R4 reporting changes |

## Intended reporting changes

`power-to-water-med`, corrected heat attribution (R1):

| | Base run | Carbon-capped run |
|---|---|---|
| water `kpis.cost` | 1.3974 → **0.5344** \$/m³ | 1.6384 → **0.6285** \$/m³ |
| water `kpis.emis` | 12.966 → **4.958** kg/m³ | 0.9488 → **0.3639** kg/m³ |

The allocation shares now sum to one; before the correction they summed to
1.0856 on this system, because the process's whole heat requirement was added
once for each of the three eligible suppliers rather than once for the heat
actually dispatched.

`reliability_cap` (R4) reports **0** in all three capped runs, where the annual
unmet-electricity cap is slack by about 2.5 GWh. It previously reported
−8 106.79 on `power-to-water-med`: the value of the row's *lower* bound, which
the solution rested on precisely because demand was fully served. The carbon cap
binds in all three runs and its value is unchanged — 0.1768, 0.0512 and 0.0829
respectively.

## The dispatch differences, and what causes them

Only the three runs carrying `carbon-constraint` and `non-served-power-constraint`
differ in dispatch. The cause was isolated rather than inferred: reverting the
R4 row change alone and re-solving `elec-grid` with both options returns a result
**identical** to the baseline. Every other change in this stage is therefore
inert on the optimisation, and the vertex shift is attributable to R4.

Making the two rows one-sided leaves the feasible set unchanged **for these
inputs**: total emissions are non-negative wherever every `var_emis_prod` is, and
each hourly unmet-demand variable is already bounded below by `l_ns[0]`, which is
zero throughout the bundled data. It is not a re-representation in general — for
a system containing a removal technology the change admits net-negative
emissions, which the old row forbade. What it changes here is the matrix the
simplex sees, so the solver settles on a different vertex of the same optimal
face. The primal economics are unchanged:

| Case | Cost | Emissions | Shortage penalties | Capacities |
|---|---|---|---|---|
| `elec-grid` capped | 5.7e-15 | 9.5e-16 | 2.8e-12 | identical |
| `power-to-hydrogen` capped | 3.2e-15 | 3.4e-14 | 1.7e-11 | identical |
| `power-to-water-med` capped | 2.2e-16 | 2.5e-15 | 0 | identical |

(relative differences; annual output per technology is also unchanged in every
case — only its timing moves.)

The row change is a correction, not only a re-representation. The lower bound of
zero asserted that system emissions could not be negative, which makes any
net-negative target infeasible by construction in a system containing a removal
technology. `test_a_net_negative_emissions_target_is_representable` covers this.

## Tests

`python3 -m pytest tests/` — 34 tests, no network, a few seconds. They use short
horizons via `fcn.Y2H` and drive the same module sequence as `ieso.py`, so
nothing is restructured for testing. Expected values come from hand arithmetic
and explicit balances, never from snapshots of the code under correction.

---

# Stage 3 verification — capacity bounds and thermal topology

This stage changes the feasible set deliberately. All eight configurations were
re-solved and compared with stage 2, which isolates L1 and L2 from the earlier
reporting work.

## Constraint counts confirm where the nameplate limit applies

| Case | Stage 2 | Stage 3 | Added |
|---|---|---|---|
| `elec-grid` base / capped | 96 361 / 96 363 | 96 361 / 96 363 | none |
| `power-to-hydrogen` base / capped | 131 402 / 131 404 | 131 402 / 131 404 | none |
| `power-to-water-med` base / capped | 192 722 / 192 724 | 192 722 / 192 724 | none |
| `swiss-grid-2025` | 148 921 | 154 768 | 5 847 |
| `swiss-grid-2050` | 201 483 | 207 322 | 5 839 |

The nameplate row is added only in hours where the normalised profile exceeds
one. Everywhere else `e <= cf * c` is the tighter relation and already implies
`e <= c`, so no row is needed. No bundled dataset outside Switzerland has a
profile that exceeds one.

## What the nameplate limit changes

`swiss-grid-2025`, generator `rovr`, hour 3782 — the only hour in that dataset
where a normalised profile exceeds one for a unit that is dispatched to its
limit:

| | Stage 2 | Stage 3 |
|---|---|---|
| max `e_prod / c_prod` | 1.000 091 50 | 1.000 000 00 |
| total system cost | 6 251 234 975.24 | 6 251 234 987.95 |

Output above the installed capacity is no longer possible. The 0.336 MWh
clipped is picked up by `impo-1`, and the whole correction costs **$12.71 on a
$6.25 billion system** — a relative cost change of 2.0e-9.

In `swiss-grid-2050` the reused `l_prod` bound was already clipping `impo-2` at
8 900 MW in 118 hours, so the ratio was 1.0 before and after. What changed is
that the limit is now deliberate rather than incidental.

## Economics elsewhere are unchanged

| Case | Cost | Emissions | Shortage penalties |
|---|---|---|---|
| `elec-grid` base / capped | 1.6e-16 / 4.0e-15 | 6.1e-16 / 3.8e-15 | 5.6e-15 / 3.6e-12 |
| `power-to-hydrogen` base / capped | 0 / 9.8e-15 | 0 / 3.6e-14 | 6.8e-16 / 8.9e-11 |
| `power-to-water-med` base / capped | 0 / 4.4e-16 | 1.1e-16 / 5.9e-15 | 0 / 0 |
| `swiss-grid-2050` | 3.6e-15 | 1.9e-13 | 0 |

(relative differences.) Dispatch moves in every case, because replacing variable
bounds with constraints changes the matrix the simplex sees even where the
feasible set is identical. Annual output per technology is unchanged except in
`power-to-water-med` base, where coal and CCGT exchange 48 554 MWh of
electricity against 393 866 MWh of heat. Both carry the same extraction
coefficient a = 0.123277, and 393 866 x 0.123277 = 48 554, so the exchange is
exactly cost-neutral — which the cost column confirms to the last digit.

## A defect introduced and removed during this stage

The nameplate row was first added in every hour rather than only where it can
bind, enlarging the problem by 52 560 rows on `elec-grid` and 113 880 on
`power-to-water-med` — a 60% larger matrix on MED. Four of the eight cases then
failed to solve.

What was observed: the solver returned **`ABNORMAL`**; and restricting the
additional rows to the hours where `cf > 1` restored optimal solves on every
case, at a constraint count identical to the one before the row was introduced.

This suggests numerical sensitivity to redundant constraints. No conditioning
measurement was taken, and `ABNORMAL` on its own establishes neither the
feasibility nor the structural correctness of the model — it reports that the
solver could not complete, not why.

Two things follow.

A constraint implied by another is not free at this scale. Redundant rows add
degeneracy and cost the solve, so a limit should be imposed only where it can
actually bind.

And the failures were nearly invisible. `opt.run` returned a bare boolean, so a
non-optimal solve wrote an output file with the same schema as a successful one,
carrying the input values echoed back (`c_prod: -1`) and `stat_succ: 0` inside
the solver block, with nothing in the log but the command line. Diagnosing it
required changing the code. `opt.run` now distinguishes infeasible, unbounded,
abnormal and not-solved, prints the reason, and records it as
`solver.stat_status` — the distinction matters, because an infeasible model is a
specification error, an unbounded one a missing constraint, and an abnormal one a
conditioning problem.

**Open question for the maintainer.** A failed solve still writes a result-shaped
file. Whether `ieso.py` should decline to write one, or write it under a
different name, is a design decision and has been left alone.

---

# Stage 4 verification — documentation, version and provenance

All eight configurations were re-solved once more. Every case reaches an optimal
solution and every result is **identical** to stage 3 apart from the new
`provenance` block: the version change and the stamp alter nothing the solver
sees.

The release carries one identifier, `26.09`. The README previously said `26.05`
and `fcn.py` said `25.10`, and neither described the code that produced the
archived results.

Each result now records the code version, the SHA-256 of the input and of every
profile file it references, the options applied, the horizon and storage-closure
convention, and the solver, OR-Tools, NumPy, Python and platform versions with a
timestamp. Profiles are hashed because they sit outside the input file and
determine the answer as directly as anything inside it. The stamp is written on
the failure path too, so an unsuccessful run is traceable as well.

---

# Findings, patches, tests and observed effects

| Finding | Patched in | Covered by | Observed effect |
|---|---|---|---|
| Process heat attributed once per eligible supplier rather than per unit dispatched | `pos_dmd.py` | `test_allocation.py` | MED water cost 1.3974 → 0.5344 \$/m³, emissions 12.966 → 4.958 kg/m³; allocation shares 1.0856 → 1.0 |
| Allocation and battery diagnostics compared against `1e+9` | `pos_dmd.py`, `pos.py` | `test_allocation.py`, `test_reporting.py` | Guards now fire; the battery check verifies the storage balance rather than a ratio that holds only for a cyclic store with no inflow |
| Cost KPI blends resource cost with shortage penalty and divides by demand | `pos_dmd.py` | `test_reporting.py` | `kpis.cost` retained unchanged; `accounts` and `system` blocks added; a system generating nothing now reports observable quantities instead of nothing |
| Cap rows two-sided, so the reported dual described the wrong bound | `eqs_dmd_e.py` | `test_reporting.py` | `reliability_cap` −8106.79 → 0 where slack; net-negative emission targets became representable |
| PtX heat duals purged unread | `pos.py` | `test_reporting.py` | Documented output now produced; empty for purely electric processes |
| Arrays raised in `cf_h`/`dm_h`; validation differed by input form | `fcn.py` | `test_profiles.py` | Arrays accepted; one validator for list, array and CSV; failures name the entity |
| Capacity bounds reused as hourly operating bounds | `eqs_gen.py`, `eqs_flx.py`, `eqs_p2x_1.py` | `test_capacity_bounds.py` | Minimum capacity no longer forces output, inventory or cycling; delivery no longer capped by production capacity; `rovr` held to nameplate, at \$12.71 on \$6.25 bn |
| A generator's heat could satisfy several processes independently | `chk.py` | `test_topology.py` | Unsupported topologies refused before the problem is built |
| A non-optimal solve was indistinguishable from any other failure | `opt.py` | observed during stage 3 | `solver.stat_status` names the reason |
| Documentation disagreed with behaviour; version labels disagreed | README, three guides, `fcn.py`, `ieso.py` | — | Reconciled; release identified as 26.09; results stamped |

---

# What this establishes, and what it does not

Fifty tests pass offline in a few seconds, using short horizons and expected
values worked out by hand rather than taken from the implementation under
correction. All eight bundled configurations solve optimally, and every
difference from the preserved baseline is accounted for above.

This establishes the behaviour of the software. It does not validate any
application of it. In particular it says nothing about whether the bundled cost
assumptions are current — they are inherited illustrative examples — nor about
the 2024 published results, which were produced by code that is not in this
repository and whose applicability remains an open question.

---

# Follow-up pass — corrections to the verification tooling

An independent review of the corrected tree found four defects, all in what
verifies the model rather than in the model itself, and two in this record.
Everything below was reproduced before being fixed.

## The comparator reported agreement it had not checked

Four ways a difference could pass, each demonstrated against a counterexample:

| Defect | Demonstration |
|---|---|
| Empty or missing series bypassed comparison | A generator's entire dispatch series deleted — `IDENTICAL`, exit 0 |
| Product demands paired with `zip`, ignoring missing entries | Every product-demand result deleted — `IDENTICAL`, exit 0 |
| `NaN` propagates through `max()` and compares False against any threshold | `[NaN, 20, 99999]` against `[10, 20, 30]` — `IDENTICAL`, exit 0 |
| Cogeneration coefficients not compared | `a`, `b` changed from 0.25 / 1.5 to 0.8 / 3.0 — `IDENTICAL`, exit 0 |

Absence is now a difference. Entity and commodity sets are compared explicitly,
required fields are checked for presence, series are compared by length and
content even when empty, non-finite values in either file are reported rather
than silently passed, and `a`, `b` and `type` are compared — required once a
unit is thermally coupled, since two results agreeing on dispatch but not on
those describe different machines.

Emptiness is reported only where content is required: `h_prod` on a unit that is
not a cogeneration plant, and `e_spil` on a store with no inflow, are
legitimately empty.

**The eight saved results were re-compared under the strengthened comparator and
still agree.** Neither defect was concealing a difference — but each was capable
of it, which is why the evidence was weaker than it appeared.

## A failed solve exited zero

An intentionally infeasible case recorded `stat_status: infeasible` and exited 0,
so `tools/run_cases.sh` recorded `rc=0` and could not aggregate failures.
`ieso.py` now exits non-zero on an unsuccessful solve; the runner counts
failures, records the status of each case, and propagates a non-zero exit. The
result file is still written — that question remains open — but a caller no
longer has to parse it to learn what happened.

## Provenance labelled the code rather than identifying it

The stamp recorded the constant `26.09` and nothing else about the source, so two
trees carrying the same string and different code were indistinguishable. It now
records the Git revision and whether the tree still matches it, together with a
digest over `ieso.py`, every module, and `thermo/sim.bin` — untracked, and the
thing that sets the cogeneration coefficients directly.

## A flag asserted more than was observed

`degenerate` equated "binding with a zero dual" with degeneracy, and the
documentation claimed the marginal value was not uniquely determined. A cap set
exactly where the solution would have landed anyway binds and is worth nothing
without being degenerate. Renamed `binding_zero_dual`, and described as the
observation it is.

## Two corrections to this record

The claim that only the capacity-bound work changes the feasible set was too
broad: making the carbon row one-sided admits net-negative emissions, which the
two-sided row forbade. That is a change of feasible set for any system
containing a removal technology, and the re-representation claim holds only for
inputs whose emission factors are all non-negative.

The account of the `ABNORMAL` failures inferred more than the evidence carries,
and has been rewritten to separate the observation from the explanation.

## Closing two verification gaps

A fixed-capacity reconciliation test now asserts
`system cost + shortage penalties = objective + pinned fixed charges`
on a case that pins one generator and optimises another.

Effective availability is reported per generator: the requested capacity factor,
the peak of the rescaled profile, the hours above nameplate, and the availability
remaining once output is held to the installed capacity. On `swiss-grid-2025`
this makes the clip visible rather than absorbed — `rovr` 0.4507 requested
against 0.450700 effective, `impo-4` 0.1674 against 0.167352.

## Verification

73 tests pass, including the command line's own exit codes on a full-horizon
input. All eight bundled configurations solve optimally and are identical to the
preceding stage under the strengthened comparator.

---

# Repair pass — conservation, validation, comparator, thermodynamics, surplus

Two independent reviews of the stage-4 tree found that 73 passing tests
coexisted with defects that let the model return physically impossible
solutions, accept inputs outside its domain, and certify results it had not
checked. Each defect below was first reproduced by a regression test, run
against the unmodified code, and only then fixed. The linear formulation is
preserved throughout: no integer variables, tie-breaking costs, secondary
objectives or new operational restrictions were added.

## Starting point and environment

| | |
|---|---|
| Starting commit | `e900e3617fcf8de93f476f191e2cf3e2986e567a`, clean tree |
| Python / NumPy / OR-Tools | 3.9.6 / 2.0.2 / 9.15.6755 |
| Platform | macOS 26.5.2 (Darwin 25.5.0), Apple M4 |
| `thermo/sim.bin` | built with Apple clang 21.0.0 from the sources of each tree |

This is **not** the reference environment of stages 1–4 (Python 3.14.4, NumPy
2.5.2 on Linux); OR-Tools is the same version. To keep before/after comparable,
the pre-repair code (a clean export of `e900e36`) and the repaired tree were
both run in this one environment. Nothing below compares across environments.

Existing suite on the starting tree: 73 passed. The new regression tests run
against the starting tree: 161 failed, 95 passed, 1 skipped. The ones that
passed are checks that legitimate configurations stay accepted.

## Findings, fixes and tests

| # | Finding (reproduced) | Fixed in | Regression tests |
|---|---|---|---|
| A1 | Unmet demand unbounded above: on the electricity balance it powered processes (2 MWh demand, 22 MWh "unmet", served −20); on a product balance, served demand went negative | `fcn.shortfall_bounds`, `eqs_dmd_e.py`, `eqs_dmd_x.py`: `l_ns[0] <= unmet[i] <= min(l_ns[1], demand[i])`; a lower bound above any hour's demand is refused, naming the hour | `test_conservation.py` |
| A1 | Negative shortage penalties accepted | `chk.py` (zero stays valid) | `test_conservation.py` |
| A2 | One process's delivery satisfied every demand naming it (shares summed to 1.67) | `chk.py`: a process supplies at most one active demand | `test_conservation.py` |
| A2 | Duplicate demand identifiers overwrote allocation quantities (shares 1.33) | `chk.py` | `test_conservation.py` |
| A3 | No coherent input contract: efficiency 4 created energy, 0 divided by zero; negative capacity factor "optimal"; process `soc_ini` 1.5 silently forced its store to zero; NaN accepted; `c_prod = -2` read as "optimise" | `chk.py` validation pass (documented in the IO guide, "Validation"); negative emissions, negative targets, zero costs and negative economic costs remain accepted | `test_validation.py` |
| A3 | A result fed back as input appended variables after its numbers | `chk.py`: populated output arrays refused, absent ones created | `test_validation.py` |
| A4 | Misspelt or malformed options silently ignored (`carbon-contraint=0` solved uncapped; `carbon-constraint 0` dropped without trace); NaN accepted | `fcn.parse_options`, called before the input is read | `test_validation.py` (CLI) |
| B | Comparator ignored `system`, `accounts`, availability, process heat duals and cap details; both-missing required fields passed; duplicate identifiers masked earlier entries; one large value widened the tolerance for a whole series | `tools/compare_outputs.py` rewritten: recursive comparison, per-element tolerance, conditional schema per file, duplicate detection, JSON duplicate keys, explicit exclusions, separate `--legacy` mode | `test_comparator.py` (mutation tests), `test_tooling.py` |
| C1 | Extraction above the inlet saturation temperature (300 °C on 290 °C / 70 bar) returned `0.620405 1.69702`; limits computed but never enforced; failure reported on stderr with exit 0 | `Cogen.cpp`, `sim.cpp`: domain enforced (open interval, boundaries excluded), superheat and pressure ordering, admissibility `0 < a < 1, b > 0, a·b < 1`, exit codes, `--limits`; `fcn.thermo`: return code, timeout, parsing and admissibility checked | `test_thermo.py` (compiled binary) |
| C2 | Binary executed relative to the working directory but hashed from the repository | `fcn.Thermo_bin`, one absolute path for both | `test_thermo.py` (decoy binary, CLI from another directory) |
| C3 | An enclosing repository's commit reported as IESO's revision | `fcn.source_state`: `git_scope`, `enclosing_git` | `test_thermo.py` |
| C4 | Output path built by replacing `.json` anywhere in the path | `fcn.output_path` | `test_thermo.py` |
| D | Surplus unreported and its cost unallocated (negative-emissions case: \$20 spent, \$10 allocated); "shares sum to one" wrong whenever surplus exists; reliability −1 when nothing was generated | `pos_dmd.py`, `pos.py`: hourly `surplus`, `heat_surplus`, `unallocated` block, reconciliation and feasibility checks in `system.checks`, `accounting_ok`, exit status 3; reliability independent of allocation | `test_surplus.py`, `test_allocation.py` |
| D | PtX availability not reported | `pos.py` | `test_comparator.py`, `test_invariants.py` |
| E | Invariants tested only on hand-picked cases | — | `test_invariants.py`: 24 recorded seeds, invariants recomputed from inputs and reported series |

The accounting equations, with units, are written out at the head of
`pos_dmd.demand_props` and in the IO guide.

## Tests

```
<scratch>/ieso-review-venv/bin/python -m pytest -p no:cacheprovider tests/
285 passed, 3 warnings in 21.37s
```

The warnings are OR-Tools' SWIG deprecation notices. None skipped: the
thermodynamics tests compiled `thermo/*.cpp` and ran against the result, and
the end-to-end CLI test found the repository's `thermo/sim.bin`.

## Scenario comparison, same environment

All eight configurations re-solved with the pre-repair export and with the
repaired tree, into separate run directories. Every run is optimal; every
repaired result has `accounting_ok: true`, and all eight share
`source_sha256 6bdea6e8…063993f`. The archived `datasets/*.ieso*.json` files
were checked by SHA-256 before and after: unchanged.

| Case | Objective (rel.) | Emissions (rel.) | Capacities (max rel.) | Annual totals | Hourly series changed | KPIs, cap duals |
|---|---|---|---|---|---|---|
| `elec-grid` base | 0 | 0 | 0 | unchanged | 0 of 9 | unchanged |
| `elec-grid` capped | 0 | 0 | 0 | unchanged | 0 of 9 | unchanged |
| `power-to-hydrogen` base | 5.7e-15 | 8.7e-15 | 7.3e-15 | unchanged | 8 of 12 | unchanged |
| `power-to-hydrogen` capped | 3.5e-15 | 1.2e-13 | 5.8e-13 | unchanged | 8 of 12 | unchanged |
| `power-to-water-med` base | 4.8e-14 | 1.2e-13 | 4.8e-14 | coal/CCGT e and h exchanged (below) | 10 of 15 | unchanged |
| `power-to-water-med` capped | 4.0e-15 | 1.0e-13 | 4.7e-14 | unchanged | 12 of 15 | unchanged |
| `swiss-grid-2025` | 0 | 0 | 0 | unchanged | 0 of 15 | unchanged |
| `swiss-grid-2050` | 0 | 0 | 0 | unchanged | 0 of 19 | unchanged |

(Objective = system cost + shortage penalties. Constraint counts are unchanged:
the repair adds bounds, not rows.)

**Why dispatch moved where it did.** The cause was isolated rather than
assumed. Re-solving `power-to-hydrogen` base with the repaired tree but the two
new shortfall upper bounds reverted (electricity and product) reproduces the
pre-repair result **identically**; reverting the product bound alone does not.
The new bounds do not bind at any of these optima — unmet demand is zero
throughout — but they change the bounds the simplex works with, and it settles
on another vertex of the same optimal face. This is the same mechanism recorded
at stages 2 and 3.

**MED base, coal and CCGT.** Annual heat moved from CCGT to coal
(2.47 TWh) and electricity the other way (0.30 TWh). Both units carry
a = 0.123277, and each unit's electricity-equivalent output e + a·h — which
fixes its fuel, cost and emissions — is unchanged to 5e-14. The exchange is
exactly cost- and emission-neutral: an alternative optimum, not a regression.

**Surplus and reconciliation on the bundled cases.** Surplus is at rounding
level everywhere (|electricity surplus| ≤ 7e-9 MWh a year, product and heat
≤ 5e-7), so allocated shares sum to one to 1e-13 and no reported KPI moved. The
largest check residual in any case is 1.8e-4 of its tolerance
(`objective_reconciliation` on MED base: under \$0.001 on \$3.7 bn).

**Against the archived results** (`compare_outputs.py --legacy`), the repaired
results differ exactly where the record says they should: the MED water KPIs
(0.5344 against 1.3974 \$/m³, 4.958 against 12.966 kg/m³), the Swiss 2025
nameplate clip at hour 3782 (0.336 MWh from `rovr` to `impo-1`, 5 847 more
constraints), and the stage-3 dispatch shift on `elec-grid`. The comparison
also shows that the archived `elec-grid` result predates the `soc_min` and
`soc_max` input fields, which the previous comparator did not examine.

Current results, with the run summary, environment and logs, are in
`results/2026-09-26/`.

## What this establishes, and what it does not

It establishes that the defects above are corrected, each by a test that failed
before the correction; that 285 tests pass, including invariant checks on 24
generated systems and the compiled thermodynamics executable; and that the
eight bundled configurations solve optimally with reconciling accounts and
unchanged economics.

It does not establish that IESO is free of defects. The generated cases are
small (24 hours) and drawn from one generator; the bundled scenarios exercise
one input family each; and the reference environment of earlier stages was not
available, so nothing here speaks to Python 3.14 / NumPy 2.5.

## Decisions, and what remains open

These are modelling or design choices, distinct from the fixes above:

- **Product surplus stays in its commodity's share.** Its energy is an input
  to that chain, so moving it to "unallocated" would count it twice. Unused
  heat is attributed to its suppliers pro rata to their heat in the hour.
  Both are conventions, documented as such.
- **Negative economic costs are accepted.** Treated as a domain choice (a
  subsidy or revenue), bounded by capacity limits, not as malformed input.
- **Allocation with zero output.** Shares are `null` and the whole system cost
  is reported as unallocated; nothing is fabricated.
- **Exit status 3** for an optimal solve whose accounts fail to reconcile.
- **A failed solve still writes a result-shaped file** (the open question
  from stage 3). Unchanged; the exit status and `stat_status` identify it.
- **One process per demand.** Splitting one process between demands would
  need delivery-allocation variables; it is refused, not approximated.
- **Profile paths** remain relative to the working directory; only the
  thermodynamics executable is resolved from the repository.
- **Coefficient precision.** `sim.bin` prints *a* and *b* to six significant
  figures, and the model uses them at that precision, as before.
- **The version label** is still `26.09`. The repair changes reported fields and
  refuses inputs that used to be accepted; whether that warrants a new label is
  the maintainer's decision. Until then, `source_sha256` identifies the code.

---

# Second review of the repair pass

A further independent review reproduced three gaps that the 285 tests did not
cover. Each was reproduced here before being fixed, and each fix has a test
that failed first.

| Finding (reproduced) | Fixed in | Tests |
|---|---|---|
| `demand_match` documented as the marginal cost of demand, but it is the balance-row dual with every bound fixed. With the new shortfall bound set by demand, the two differ wherever that bound binds: one hour, generation 100 \$/MWh, shortage 10 \$/MWh, demand shed — objective 110 → 110.01 for +0.001 MWh (10 \$/MWh), reported 100 | `pos_dmd.demand_marginal`: adds the shortfall variable's reduced cost where it sits at a demand-set bound (GLOP: row dual 100, reduced cost −90). `demand_match` kept as the row dual and relabelled; `demand_marginal` added | `test_duals.py`: finite differences of the objective, electricity and product, binding and non-binding bounds, a configured `l_ns[1]` that demand does not move, three hours each against its own difference; invariant in `test_invariants.py` |
| Comparator returned `IDENTICAL` for two identically corrupted results: empty `accounts`, missing `system.unallocated.cost`, empty `system.checks`, empty `provenance`, dispatch entries replaced by strings or nested lists | `tools/compare_outputs.py`: per-file schema now checks every required nested field and its type, every series element, digests, the checks a run must carry, and that `accounting_ok` agrees with them | `test_comparator.py`: 28 corruptions applied to **both** files |
| Defaults accepted by validation but never stored, and explicit nulls let through: omitted generator `profile` → `KeyError`; omitted `a` → `KeyError` in reporting; `soc_min: null`, `inflow_total: null` → `TypeError` | `chk.py`: an omitted optional field takes its default *in the input*; `a`, `b` initialised on every generator; an explicit null is refused | `test_validation.py`: each optional field omitted, run end to end and reconciled; each null refused |

The fixture that builds a solved result for the comparator tests stamped
provenance for a file that did not exist, leaving `input_sha256` null; the
strengthened schema caught it, and the fixture now writes its input first.

## Verification after the second review

```
<scratch>/ieso-review-venv/bin/python -m pytest -p no:cacheprovider tests/
353 passed, 3 warnings in 21.70s
```

All eight configurations were re-solved once more with the final code (same
environment). All are optimal with `accounting_ok: true` and share
`source_sha256 45714034…4b1898ca`; `results/2026-09-26/` now holds these runs,
replacing the earlier ones from this pass. Against the previous run, with the new
field set aside, the only differences are the defaults now written into the
echoed input (`charge_allowed`, `inflow_total` on the batteries): every capacity,
dispatch series, dual, KPI, account and total is identical. In all eight cases
`demand_marginal` equals `demand_match` in every hour — no shortfall bound binds
in the bundled data — so the correction changes what is reported only where
demand is shed at a bound that demand itself sets. The archived
`datasets/*.ieso*.json` files remain byte-for-byte unchanged.


## Third review: what `demand_marginal` is

The documentation above first described `demand_marginal` as the derivative
of the objective for an increase in demand. That is true away from
breakpoints and not in general. Reproduced: one hour, a 1 MW unit at
100 \$/MWh, shortage at 1000 \$/MWh, demand 0 — the value reported is 0,
while demand of 0.001 MWh costs \$0.10, a right derivative of 100. At demand
exactly 1 MW the left derivative is 100 and the right 1000.

An optimal dual is a subgradient of the (convex, piecewise-linear) objective
as a function of the hour's demand: it lies between the one-sided derivatives,
and equals them where they agree, but at a breakpoint it may be anywhere
between. The field is now documented as exactly that — a dual-based marginal
value — in the code, the IO guide and the modelling approach. No exact
one-sided derivative is computed; that would need a parametric re-solve for
each hour.

Tests: the zero-demand counterexample and a capacity breakpoint
(`test_duals.py`), and on each of the 24 generated systems the inequality
`(f(d) - f(d-h))/h <= demand_marginal <= (f(d+h) - f(d))/h`, which holds for
any step h at breakpoints and elsewhere (`test_invariants.py`). The reported
numbers are unchanged; only their description was wrong.

Because the docstring is part of the hashed source, the eight configurations
were re-solved once more so that the stored results identify the current code:
all optimal, `accounting_ok: true`, **identical** under the strict comparator to
the previous run, now sharing `source_sha256 1dc6468a…ca42dfe1`.
`results/2026-09-26/` holds these runs. Final suite: 379 passed.

---

# Repository clean-up: self-contained datasets

On 2026-09-26, after `44db591`, the repository was reorganised without
changing the model, its inputs' numbers, or its results.

- **Profiles moved into their datasets.** The mid-west, NYISO and Florida
  profiles used by the three regional datasets were copied into those
  datasets' directories (`dmnd.csv`, `solr.csv`, `wind.csv`), each verified
  byte-for-byte against its source, and the three inputs were pointed at them.
  Parsed field by field, each input differs from its predecessor in exactly its
  three `profile` paths. The shared `profiles/` folder, including the regional
  profiles no dataset used, was removed. Paths stay relative to the repository
  root; path resolution is unchanged.
- **Historical results removed from the checkout.** The eight pre-correction
  results were verified byte-for-byte at `44db591` and removed; the section at
  the top of this record lists them with their checksums, and its retrieval
  commands were executed and reproduce all eight checksums. Git history is
  untouched, so removing them does not shrink the repository's history.
- `ieso_modules/README.md`, a one-line folder description, was removed;
  `.pytest_cache/` is ignored.

Verification, in the environment of the results above: 379 tests passed, none
skipped. All eight configurations were re-solved and are optimal with
`accounting_ok: true`. With the nine profile paths mapped to their new
locations, every result is **identical** under the strict comparator to the
result it replaces. With `--provenance`, the only differences are the run's
`input` path, `git_revision` (`e900e36` → `44db591`) and, for the three
regional datasets, `input_sha256`; the profile digests and `source_sha256`
(`1dc6468a…ca42dfe1`) are unchanged. `results/2026-09-26/` holds these runs.

---

# Illustrative datasets replaced

After `aa761ef` the bundled datasets were replaced by four illustrative cases
on one template: an island electricity system, one node, every generation
technology a candidate (`elec-grid`), plus variants adding electrolysis,
reverse osmosis or MED. The model code is unchanged — the new results carry the
same `source_sha256` (`1dc6468a…ca42dfe1`) as the results verified above.

- **Removed from the checkout, kept in history at `aa761ef`:** the regional
  `elec-grid`, `power-to-hydrogen` and `power-to-water-med` inputs with their
  mid-west, NYISO and Florida profiles; the `swiss-grid-2025` and
  `swiss-grid-2050` datasets; `results/2026-09-26/`.
- **Inputs** are generated by `tools/build_datasets.py`, which carries every
  coefficient with its source; `datasets/README.md` lists sources, licences and
  caveats. Demand: 5.69 TWh (2025, estimated from ENTSO-E monthly mean load for
  bidding zone `CY`) on the 2021 hourly shape of the 2021 island study
  (ENTSO-E zone `CY`, 95% observed). Weather: that study's Renewables.ninja
  MERRA-2 profiles for 2021 — solar at 34.88 °N 33.63 °E, wind at 35.05 °N
  33.20 °E. The zone and site are recorded here for traceability; the datasets
  themselves do not name the system.
- **Sources:** NEA/EPRI 2025 OECD means (nuclear, coal); Lazard LCOE+ 2026
  plant costs (combined and open cycle, burning gas oil); Danish Energy Agency
  2025 calculation assumptions (gas-oil price, CO₂ factors); IRENA via the
  island study (solar, wind, battery, RO); legacy values (hydrogen, MED).
- **Verification:** 379 tests passed. All eight runs are optimal, reconcile
  (`accounting_ok: true`) and pass the comparator's strict per-file schema
  check. MED's cogeneration coefficients come from the compiled thermodynamics
  executable (a = 0.124272, b = 1.97657 for the nuclear conditions; 0.123277,
  1.57164 for coal and combined cycle). Results are in
  `results/elec-grid-2026-09-26/`.

## Desalination and hydrogen costs revised after a benchmark review

A third-party review compared the Power-to-X inputs with published benchmarks.
Checked against the World Bank (2019) report itself, its central point holds:
MED capital cost exceeds RO's (Table ES.1, 2016 US$: MED-TVC averages 1,400
and Mediterranean SWRO 1,200 $/(m³/day)), and the legacy MED input implied the
opposite. Several of its specifics did not hold — the report's title, a 20–40%
premium (the report's own averages give about 17%), the IAEA DEEP figures (no
published defaults found), and a recommended 5,115 $/(m³/h)/yr that needs an
unstated MED fixed O&M of about 90 $/(m³/day)/yr to reproduce.

Changes, all in `tools/build_datasets.py`:

- **MED**: capital 1,435 $/(m³/day) (World Bank Table 5.1 net of financing, as
  RO's 1,200), 25 years; non-energy O&M at RO's ratio to capital. Fixed cost
  2,185 → 5,108 $/(m³/h)/yr; variable 0.26 → 0.110 $/m³.
- **Hydrogen**: World Bank / ESMAP (2026) *Electrolyzers for Hydrogen
  Production*, Table ES1, alkaline midpoints — 1,000 $/kW, 2.5%/yr
  non-electricity OPEX, 53.5 kWh/kg, 25 years. Fixed cost 2,486 → 5,928
  $/(kg/h)/yr; electricity 50 → 53.5 kWh/kg. The report gives no storage cost,
  so the store keeps its legacy value.

The review also exposed a reporting issue. IESO's product cost KPI allocates
the whole system cost — including the Power-to-X plant — by
electricity-equivalent use, so it is not a production cost: before these
changes it reported RO water at 0.38 $/m³ although its plant alone costs
0.67 $/m³. `tools/product_costs.py` now costs products directly, and the IO
guide and dataset READMEs say which figure to compare with benchmarks. With
the revised inputs, direct costs are RO 0.90, MED 1.30 $/m³ and hydrogen
3.76 $/kg (base runs), within the World Bank's water-cost ranges.

Verification: the two changed inputs differ from their predecessors only in
the four intended fields; the base and RO inputs are byte-identical. All eight
runs are optimal with `accounting_ok: true` and pass the strict per-file schema
check; the four unchanged runs are identical under the strict comparator to
the previous snapshot. 379 tests passed. Results replace those in
`results/elec-grid-2026-09-26/`.

---

# Reference state before the packaging and API refactor

Recorded 2026-09-26 as Step 1 of the planned refactor (import-safe API,
portable profile paths, typed input models and schemas, installable wheels).
It fixes what the refactor must preserve and how that will be checked. No
model code, input, interface or path convention was changed in recording it.

## Starting point

| | |
|---|---|
| Commit | `a1b2cb248d9164a6ac07eb3d15ae065336795711` on `main`, level with `origin/main`, clean working tree |
| Python / NumPy / OR-Tools | 3.9.6 / 2.0.2 / 9.15.6755 (GLOP), pytest 8.4.2 |
| Platform | macOS 26.5.2 (Darwin 25.5.0), arm64, Apple M4 |
| Compiler | Apple clang 21.0.0 (clang-2100.1.1.101); `g++` is clang |
| Model code digest (`source_sha256`) | `1dc6468a9f25879c80699bd23bbdd782ed6dc4f230e8f2825dbf6f22ca42dfe1` |
| `thermo/sim.bin` | `72a69d6890285dddfbce71481584f1c27c0993ce1711240a417334e6f0456969` |
| Tests | 379 in 13 files before this step; 413 after it (34 added, below) |
| Bundled runs | 8: four datasets × base and capped (`carbon-constraint=50`, `non-served-power-constraint=0.05`), as listed in `tools/run_cases.sh` |

**The executable IESO runs is the one provenance hashes.** `fcn.Thermo_bin`
resolves to `thermo/sim.bin` in the repository, and `source_state()` hashes
that same path. A fresh build of the current `thermo/*.cpp` with
`thermo/build.sh`'s commands is **byte-identical** to it, so the reference
executable is the current source (its older timestamp predates later Git
checkouts, not source edits). An `-O2` build of the same sources emits
identical coefficients and limits for every fixture case on this platform.

Inputs:

| File | SHA-256 |
|---|---|
| `datasets/elec-grid/elec-grid.json` | `c77753a748d72e2af8e6baa0b2e9810c475e70283924295f661d983a076bcdff` |
| `datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen.json` | `2c7abd909046cca8290d272d3d1f87f0a03a3ebb48ecc59381fb1f164386fa97` |
| `datasets/elec-grid+power-to-water-ro/elec-grid+power-to-water-ro.json` | `bc6aaac998998f91a6482197d12a0d394971cc799c5f6f6ee6b806c4f67a4216` |
| `datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med.json` | `c6d26923ccd250ce9fe93663a26975649ae2c9cb45d9d1704dd95191c3420143` |
| `dmnd.csv` (identical in all four datasets) | `d6dd348cac21c8a14dea4dc2a86732c7b4f303ce698e203526837b52d596d418` |
| `solr.csv` (identical in all four) | `6ff417974a5d00d08b5bde54cd5ba45c4a13888217f943ca68a9c4ea502d4f5f` |
| `wind.csv` (identical in all four) | `3cc524a93bb95750561f9998542fa7d820674941fb1e6f7f44400a390ce5d45f` |

## Reference results

The reference is `results/elec-grid-2026-09-26/`, committed at `a1b2cb2`;
all 19 files there are byte-identical to `git show a1b2cb2:results/elec-grid-2026-09-26/<file>`.
They record `git_revision` `a663acb` with `git_dirty: true` because they were
produced just before that commit; their `source_sha256` (`1dc6468a…`) and
executable digest (`72a69d68…`) equal the current tree's, which is what
identifies the code.

## Fresh verification

Evidence is in `runs/reference-20260926T163255Z/` (ignored, not committed): a
hash manifest of every file above, a preserved copy of the reference
executable, two candidate builds, the eight fresh results with their logs and
run records, test output, comparator output and the invariant checker.

- **Tests**: 379 passed before, 413 after this step's additions; none skipped,
  so the compiled-thermodynamics and repository-binary tests ran.
- **Runs**: all eight optimal, `accounting_ok: true`, no unmet demand; the
  capped runs sit exactly on the carbon cap (284.5 kt = 50 kg/MWh × 5.69 TWh).
- **Independent invariants** (`check_invariants.py`, recomputing from the
  input and the reported series, not from IESO's post-processing): capacity
  and nameplate limits, cogeneration limits, storage bounds, transitions and
  year-end closure for batteries and product stores, unmet demand within
  `[l_ns[0], demand]` every hour, electricity, heat and product balances,
  carbon and reliability caps, and system cost and emissions recomputed from
  capacities and flows and reconciled with `allocated + unallocated`. All eight
  fresh and all eight stored results pass. The checker was itself shown to fail
  on five deliberate corruptions (output above capacity, unmet above demand, an
  open storage year, a broken heat balance, an altered system cost).
- **Comparator** (`tools/compare_outputs.py`, default strict mode: every field
  both files carry, per-element |Δ| ≤ 1e-6 + 1e-9 × |reference|, per-file
  schema, non-finite scan; `solver.stat_time` and `provenance` excluded):
  **all eight fresh results `IDENTICAL` to the reference.** With
  `--provenance`, the only differences are `provenance.input` (run directory),
  `provenance.git_revision` (`a663acb` → `a1b2cb2`) and, for `eg-base` only,
  `provenance.git_dirty`.
- **An observation, not a defect in the numbers**: the fixture file below was
  written at 16:34:23 UTC, nine seconds after `eg-base` started, so the seven
  later runs recorded `git_dirty: true` while `eg-base` recorded `false`. Their
  `source_sha256` is identical. `git_dirty` counts any untracked file,
  including tests, so it can report a modified tree when the model code is
  untouched; the source digest is the reliable identifier. The packaging work
  should keep that distinction.

## Thermodynamics regression evidence

`tests/fixtures/thermo_reference.json` records what the reference executable
emits for both turbines of the bundled MED case (290 °C / 70 bar and 564 °C /
152 bar, condenser 0.05 bar): its domain limits, coefficients at five
extraction temperatures from just inside the lower limit to just inside the
upper (including the 80 °C of the MED case), and its refusals exactly on and
1 °C outside each limit (status 3, empty stdout, reason on stderr).
`tests/test_thermo_reference.py` (34 tests) separates:

- **fixtures** — recorded behaviour, not proof of correctness. The reference
  build must reproduce the strings exactly; any other build within one unit of
  the 6th significant digit (the printed precision; a different compiler may
  round that digit the other way); limits within 1e-9 °C; refusals identical.
  IESO consumes the coefficients at the printed precision, which is tested.
- **physical checks** — independent: saturation temperatures against
  IAPWS-IF97 steam tables (32.88 °C at 0.05 bar, 285.83 °C at 70 bar, 99.61 °C
  at 1 bar, and 152 bar bracketed by 342.16 and 347.36 °C at 150 and 160 bar),
  admissibility (0 < a < 1, b > 0, a·b < 1), and `a` rising with extraction
  temperature. `b` is not monotone — for the fossil turbine it rises to
  1.575 at 150 °C and then falls — so no such check is made on it.

## Comparison contract for the refactor

**Equivalent inputs.** Each case's parsed input must equal the reference
input field by field, except for profile path strings when Step 2 changes the
path convention; the profile files' digests must be unchanged. Options,
horizon (8760 h), storage closure, the `fcn` tolerance constants and the
thermodynamic coefficients must be unchanged. Problem size — `stat_capa`,
`stat_outp`, `stat_cons` — is determined by the inputs and must be identical
in every environment; a change means the LP changed.

**Always required, in every environment**: status `optimal`;
`system.accounting_ok: true`; the independent invariants above, with
feasibility residuals within 1e-6 + 1e-7 × scale (scale the largest magnitude
involved, in the quantity's own unit) and bookkeeping identities within a
relative 1e-9.

**Same environment** (Python 3.9.6 / NumPy 2.0.2 / OR-Tools 9.15.6755 on this
macOS arm64 machine): the strict comparator must report `IDENTICAL` for all
eight runs against the reference. Any difference is investigated before it is
accepted.

**Other environments** (another OS, architecture, Python, NumPy or solver
build) may settle on another vertex of the same optimal face, so hourly
dispatch, surplus, duals and allocation shares are not required to match.
Required instead, relative to the reference:

| Quantity | Unit | Tolerance | Why |
|---|---|---|---|
| Objective: system cost + shortage penalties | USD/yr | relative 1e-10 | alternative optima in this record differ by ≤ 5e-14; the smallest real change recorded (the $12.71 nameplate correction) was 2e-9, which this still catches |
| Emissions | kg CO₂/yr | relative 1e-9 when the carbon cap binds (determined by the cap); otherwise investigate any change beyond 1e-9 | not in the objective, so an alternative optimum could move them; earlier alternative optima moved them ≤ 2e-13 |
| Capacities | MW, MWh, Q/h | absolute 1e-6 + relative 1e-7 | expected equal; a difference is accepted only if the objective and invariants hold and it is shown to be cost-neutral |
| Annual output per technology | MWh/yr | informative | may shift between equally priced options, as the coal/CCGT heat exchange of stage 2; explained, not assumed |
| Thermodynamic coefficients | — | reference build exact; other builds ≤ 1 unit in 6th significant digit | the printed precision |

Beyond tolerance, or a failed invariant anywhere: investigate and report;
never widen a tolerance, exclude a field or replace the reference to pass. No
bit-for-bit equivalence is promised across compilers or solver builds.

**Provenance fields expected to change** during packaging: `ieso_version`
(if the version scheme changes), `git_scope`, `git_revision`, `git_dirty`,
`enclosing_git`, the keys of `source_files_sha256` and hence `source_sha256`
(module paths move), `thermo_binary` (the executable moves into the package),
`input` and, once paths change, `input_sha256` and the keys of
`profiles_sha256`; and `python`, `numpy`, `platform`, `run_utc`. These are
checked separately, not by the numerical comparison: every digest must equal
the digest of the file actually used (as `test_provenance_matches_what_was_run`
does), profile digest *values* must be unchanged, and the executable digest
must equal that of the binary IESO executed.

## Step 2: import-safe API — verification

The command line was separated from a small Python API, with no change to the
formulation, equation construction order, solver settings, accounting or
thermodynamic precision.

**Interfaces.** `ieso_modules/api.py`: `load_input(path)`,
`solve(case, *, options=None, config=None, source=None) -> SolveResult`,
`write_result(result, path)`, `output_path(input, options)`.
`ieso_modules/errors.py`: `InputError` (`entity`, `field`, `hour`),
`ThermoError` (`generator`, `process`, `reason`). `ieso_modules/cli.py`:
`main(argv) -> int`; `ieso.py` is now only a guarded launcher. Per-run
settings travel in `fcn.RunConfig` (`hours` 8760, `storage_closes_the_year`
true, `thermo_bin` `thermo/sim.bin`, `thermo_timeout` 30 s) instead of the
former globals `fcn.Y2H`, `fcn.Strg_end_eq_ini`, `fcn.Verbose` and the
module-level executable path; each model module receives it explicitly. Library
code no longer exits or prints: the 54 `fcn.fail` refusals (38 in `chk.py`,
16 in `fcn.py`) and the two direct exits in `eqs_flx.py` now raise
`InputError`; the thermodynamics refusal in `eqs_gen.py` raises `ThermoError`;
`fcn.get_json`, which exited on an unreadable file, is replaced by
`api.load_input`, which raises `InputError`; and diagnostics go to the `ieso` logger, configured only by
the command line. `solve()` works on a private deep copy, so the caller's
case — nested lists, dictionaries and arrays included — is never modified, and
the returned document holds only plain JSON types.

**Preserved.** Invocation (`python ieso.py INPUT.json [name=value ...]`),
option names and ranges, output file naming, the serialised result, exit codes
0, 1 and 3, profile-path semantics.

**Tests.** 428 passed, none skipped: the 413 of Step 1, adjusted where they
patched the removed globals or expected an exit (they now pass the horizon or
executable per run and expect the exceptions), plus 15 in `tests/test_api.py`
— import safety with unrelated `sys.argv` (no subprocess, solver, file write,
output or exit), unchanged inputs after success, infeasibility and refusal,
independence of repeated solves, catchable errors with their context, plain
serialisable results for successful and failed solves, CLI and API equivalence
under the strict comparator, and exit codes. Two tests had been passing for the
wrong reason once the executable stopped being a patchable global — they were
silently using the repository binary instead of the freshly built one — and now
configure it explicitly.

**Runs.** `runs/step2-20260926T165659Z/` (ignored), same environment as Step 1. All eight optimal,
`accounting_ok: true`; all eight pass the independent invariant checks; all
eight **`IDENTICAL`** to `results/elec-grid-2026-09-26/` under the strict
comparator (numbers, problem sizes, cogeneration coefficients). Provenance
differs only where expected: `source_sha256` and `source_files_sha256` (the
code changed; the digest now covers 17 files and equals the current tree's),
`git_revision` and `input`. Input, profile and executable digests are
unchanged. The Python example in the setup guide was executed as written.

## Step 3: profile paths relative to the input file (2026-09-26)

**Rule.** A relative profile path resolves against the directory of the input
JSON file; an absolute path is used as written; empty and inline profiles are
unchanged. Nothing else is tried: not the working directory, not the
repository root. A missing file is refused with an `InputError` naming the
field, the declared path and the resolved location. A case solved in memory
(`api.solve(document)` without `source=`) accepts only inline, empty or
absolute profiles unless `RunConfig(profile_base=DIR)` is given.

**Legacy inputs.** Inputs written before this step use repository-relative
paths (`datasets/<case>/X.csv`). They are run with an explicit base,
`python ieso.py old.json --profile-base /path/to/ieso` (or
`RunConfig(profile_base=...)`); the mode is never inferred from which files
exist. A `profile_base` that is not a directory, a repeated or valueless flag,
an unknown flag, and a `source=` that contradicts a path given as the case are
refused. `--profile-base` is not a model option: it does not enter the result
file name or the solver, and is recorded in provenance.

**Changed interfaces.** `fcn.resolve_profile(path, base, who, field)`;
`fcn.as_profile`, `dm_h` and `cf_h` take `base` and `field`; `RunConfig` gains
`profile_base`; `cli.split_flags` and the `--profile-base` flag. Provenance
gains `input_resolved` (absolute path of the input actually loaded),
`profile_files` (per declared path: the file consumed and its SHA-256) and
`profile_resolution` (`mode` `input-directory` / `explicit` / `none`, and
`base`). `profiles_sha256` keeps its form, keyed by the declared path, with the
digest of the file actually read. `tools/compare_outputs.py --provenance`
checks the new fields when present.

**Migration.** The twelve profile strings in the four bundled JSONs are now
local names (`dmnd.csv`, `solr.csv`, `wind.csv`); no other byte of their
content changed, and no CSV changed. `tools/build_datasets.py` writes local names
and regenerates the four JSONs byte for byte (it is a fixed point).
`tools/run_cases.sh` no longer changes directory: it can be called from
anywhere, resolves a relative output directory against the caller's working
directory, copies each JSON into it under the same labels as before, and runs
the copy with `--profile-base` set to the case's own directory.

**Tests.** 449 passed, none skipped (3 DeprecationWarnings from OR-Tools' SWIG
bindings, emitted on import). New: 20 in `tests/test_paths.py` — resolution against
the input directory, independence from the working directory, a decoy CSV in the
working directory never read, a copied case directory giving an identical
result, paths with spaces, absolute paths, inline and empty profiles without a
base, in-memory cases with and without a base, `source=` as the base for a
parsed document, missing-file messages, no working-directory fallback,
conflicting configuration, a root-relative input under an explicit base, the
command line from another directory, the runner's own invocation, and flag
errors raised before solving. One case in `tests/test_profiles.py` separates
"not found" from "cannot be resolved".

**Runs.** `runs/step3-20260926T171649Z/` (ignored), same environment as Step 1
(Python 3.9.6, NumPy 2.0.2, OR-Tools 9.15.6755, `sim.bin` 72a69d68…).
The runner was started from `<workspace>`, outside the repository, with
the relative output directory `ieso/runs/step3-20260926T171649Z/cases`.

- All eight optimal, `accounting_ok: true`, exit 0.
- All eight pass the independent invariant checks
  (`check_invariants.py` in the evidence directory; it reads profiles from
  `provenance.profile_files`; it was run from outside the repository).
- All eight **`IDENTICAL`** to `results/elec-grid-2026-09-26/` under the strict
  comparator, after mapping the three expected profile strings in a copy of each
  reference (`datasets/<case>/X.csv` → `X.csv`). Nothing else was mapped.
- Provenance differs only where expected (`comparison.txt`):
  - `input`, `input_resolved` (new), `input_sha256`: the migrated input.
  - `profiles_sha256` has renamed keys but equal digests.
  - `profile_files` (new) has digests equal to `profiles_sha256`.
  - `profile_resolution` (new) is `explicit`, with the base set to the case directory.
  - `git_revision`, `source_sha256` and `source_files_sha256` changed because the code changed.
  - The executable digest is unchanged.
- `input_sha256` equals the digest of `input_resolved` in every run. The eight results
  pass `compare_outputs.py --provenance`.

**Legacy check.** The pre-migration inputs of commit `a1b2cb2`
(`elec-grid.json`, `elec-grid+power-to-water-med.json`) were run with
`--profile-base <checkout>` from the scratch directory
(`legacy/`). Both results are **`IDENTICAL`** to `eg-base` and `med-base`,
with no mapping. Their `input_sha256` and `profiles_sha256` equal the
reference's. Run without the flag, the same input is refused, and the refusal
names `solr`, the field, the declared path and the resolved location.

**Limitations.** The runner is exercised end to end here, not in the unit
suite (the suite covers its exact invocation of `ieso.py`). `git_dirty` still
counts untracked files. Thread safety of concurrent solves is still not
established.

## Step 4: typed input models, JSON Schemas and structured diagnostics (2026-09-26)

**What changed.**

*One structural validator.* `ieso_modules/models.py` holds Pydantic models for the case (`Case`, `Demand`, `ElectricityDemand`, `CommodityDemand`, `Generator`, `Storage`, `Process`) and for the run options (`SolveOptions`).
- The models own types, required and unknown fields, allowed values, finite numbers, ranges, and the rules within one object. They are now the only structural validator: the corresponding checks were removed from `chk.py`, and the two duplicate state-of-charge checks from `eqs_flx.py`.
- Serialised field names are unchanged. Python attributes are descriptive and documented with units.
- Every value type has its own validator and serialiser: an integer stays an integer, and strings, booleans, null, NaN and infinities are refused.

*Semantic layer.* `chk.py` is now the semantic layer: identifiers, references, ownership, thermal topology, profiles and hourly shortfall bounds.
- The shortfall check is now also made before construction, so `validate` finds it.
- `chk.cogeneration` is the single place the thermodynamics executable is called, by both `eqs_gen` and `validate`.

*Formats.* `ieso_modules/formats.py` handles the input formats:
- Version detection: the canonical format carries `format_version` 1, and an unversioned document is legacy.
- The legacy adapter removes only the documented output fields (`LEGACY_OUTPUT_FIELDS`), and refuses a result given as input.
- A boundary adapter converts NumPy profiles to lists.
- It translates Pydantic errors into IESO diagnostics.
- It builds the working document the equation modules read.

*Diagnostics.* `errors.Diagnostic` records `code`, `layer`, `message`, `path` (JSON Pointer), `entity`, `field` and `hour` (zero-based). `InputError` and `ThermoError` keep their Step 2 attributes and gain `diagnostics`.

*Result models and schemas.*
- `ieso_modules/results.py` holds the result models: `OptimalResult`, `UnsuccessfulResult` and the union `Result`.
- `ieso_modules/schemas.py` and `tools/generate_schemas.py` generate `schemas/ieso-input-1.schema.json` and `schemas/ieso-result-1.schema.json`.

*API and command line.*
- The API gains `validate()` (returns a `ValidationReport`), `parse_case()` and `to_canonical()`. `solve()` accepts a `Case`.
- The command line gains `validate CASE.json [--json]` and `schema input|result`. The solve form is unchanged.

*Tooling and docs.*
- Pydantic (>= 2.11) is declared where the other dependencies are, in the setup guide.
- mypy checks the public boundary (`mypy.ini`, strict, seven modules).
- New page: `docs/ieso-api.md`. The IO reference's validation table now names each rule's layer.

**Deliberate behaviour changes.** None affects the bundled cases or any numerical result.
- *Unknown fields are refused* anywhere in an input. Before, they were ignored, including at the top level of a legacy document.
- *Inactive commodity demands:* on a demand with `total` 0, the types and ranges of `var_cost_ns` and `l_ns` are now checked, although those fields are never read.
- *Legacy placeholder objects* (`kpis`, `shadow_prices`, `solver`, `provenance`) must be objects, not `null`.
- *An unsuccessful result* now holds the case's input fields (defaults written in), the solver status and provenance. It no longer echoes empty output arrays or -1 placeholders.
- *`output_ns`* is present on every demand of an optimal result: an empty list on an inactive demand. The bundled inputs already carried it.
- *Result key order* now follows the models. Key order is serialisation only: the comparator does not compare it, and nothing reads it.
- *Provenance* gains `input_format` and `result_format_version`.
- *`str(InputError)`* joins all its diagnostics.

**Tests.**
- 540 passed, none skipped: the 449 of Step 3, unchanged, plus 91 new ones.
  - `tests/test_models.py`, 51 tests:
    - legacy-to-canonical equivalence (all four datasets, value and type, and an identical solve);
    - unknown fields, malformed and non-finite values;
    - valid zero and negative values; absent, null, empty and zero;
    - diagnostic codes, paths, entities and hours for structural and semantic failures;
    - canonical serialisation and reload;
    - the NumPy boundary; options;
    - validation without solving; the thermodynamics stage;
    - immutability and repeated independent solves.
  - `tests/test_schemas.py`, 22 tests:
    - generated schemas equal the checked-in files;
    - representative valid and invalid inputs;
    - optimal, accounting-failure and unsuccessful results.
  - `tests/test_cli_commands.py`, 18 tests: JSON cleanliness, exit status, profile base, schema output, and statuses staying distinguishable.
- `python -m mypy`: no issues in the seven boundary modules.
- `tools/generate_schemas.py --check`: current.
- Environment: Python 3.9.6, NumPy 2.0.2, OR-Tools 9.15.6755, Pydantic 2.13.5 (pydantic-core 2.46.5), jsonschema 4.25.1, mypy 1.19.1; `sim.bin` 72a69d68….

**Runs.** `runs/step4-20260926T175530Z/` (ignored), started from `<workspace>` with a relative output directory, as in Step 3.
- All eight optimal, `accounting_ok: true`, exit 0.
- **`IDENTICAL`** to `results/elec-grid-2026-09-26/` under the strict comparator, after the same three profile-string mappings as Step 3 and nothing else.
- **`IDENTICAL`** to the Step 3 runs with no mapping at all.
- Provenance (`comparison.txt`) differs only in:
  - `input`, `input_resolved`, `source_sha256` and `source_files_sha256`;
  - the new `input_format` (`legacy`) and `result_format_version` (1);
  - against the reference, the Step 3 fields.

  `input_sha256` and the profile digests equal Step 3's.
- Problem sizes (`stat_capa`, `stat_outp`, `stat_cons`) are compared by the comparator and are identical, so construction and its order are unchanged. `opt.py` was not edited.
- Independent invariant checks pass for all eight, and for the two canonical runs below (`invariants.txt`).
- All ten fresh results validate against `schemas/ieso-result-1.schema.json` and `results.Result` (`result-schema.txt`). The stored reference results predate format 1 and are, as expected, not format-1 results.

**Legacy and canonical.**
- `to_canonical()` of `elec-grid` and of `elec-grid+power-to-water-med` (with its carbon and reliability caps), solved with `--profile-base` set to the dataset's directory: **`IDENTICAL`** to the legacy runs.
- In each of those four legacy datasets, every input value is identical, value and type, in the model's working document. The only fields added are `inflow_total` 0.0 and `charge_allowed` true, which the old validator also wrote in and the reference results carry.
- The pre-migration inputs of commit `a1b2cb2` pass `validate --profile-base` and solve **`IDENTICAL`** to `eg-base` and `med-base` (`legacy/`).

**Limitations.**
- The schemas cannot express cross-field rules such as `low <= high` or the state-of-charge order. The models and IESO check them.
- Stored results from before format 1 do not validate against the format-1 result schema.
- The model-building modules are not type-checked yet.
- Thread safety is not established.
- `git_dirty` counts untracked files.

## Step 5: an installable package (2026-09-26, completed 2026-09-27)

**What changed.**
- **Layout:** the modules moved from `ieso_modules/` to `src/ieso/`. The package has an explicit public API in `__init__.py`, plus `__main__.py`, `py.typed`, and the schemas in `ieso/data/`.
- **Launcher:** `ieso.py` remains a compatibility launcher. It runs the installed package, never imports itself, and refuses to be imported as the package.
- **Build:** `pyproject.toml` uses scikit-build-core. It holds the single version, 2026.9.0, `requires-python >= 3.11`, the runtime dependencies `numpy>=2.0,<3`, `ortools>=9.15,<10` and `pydantic>=2.11,<3`, the `dev` extra, the `ieso` console command, an allow-listed sdist and the mypy configuration.
- **Executable:** `CMakeLists.txt` builds `thermo/*.cpp` into `ieso/_bin/ieso-thermo` with the reference build's flags (`-Wall`, no optimisation flag).
- **Installation awareness** (`ieso/_install.py`):
  - The version comes from the distribution metadata.
  - The executable is found through the package's resources, or through the distribution's RECORD for an editable install.
  - Provenance gains `installation` and `thermo_binary_origin`.
  - Git is consulted only for a source checkout.
- **Tools and tests:** they now import the installed package, with no `sys.path` insertion.

**Environment change.**
- The machine had only Python 3.9.6. With your approval, uv (installed in a throwaway venv) installed CPython 3.12.14 in uv's default managed-Python directory.
- Development venv: NumPy 2.0.2, OR-Tools 9.15.6755 and Pydantic 2.13.5, as in the reference. The one transitive difference is `absl-py` 2.5.0 (2.3.1 before).
- Before the move, the unchanged checkout passed all 540 tests on 3.12. Its 8 annual runs (`runs/step5-premove-py312-20260926T181453Z/`) are **`IDENTICAL`** to the reference and to Step 4, so the interpreter change alone changes nothing.

**Artifacts.**
- Build tools: scikit-build-core 1.1.0, CMake 4.4.3 and Ninja 1.13.2, fetched from PyPI into the isolated build environment.
- The wheel is `py3-none-<platform>`.
- The wheel built from the working source and the one built from the extracted sdist contain byte-identical executables.
- The executable links only `libSystem` and `libc++`.
- The packaged executable reproduces every entry of the Step 1 thermodynamics fixture exactly.
- A fresh 3.12 venv was tested with PATH reduced to the venv (so no Git or compiler was reachable), with `python -I` and from outside the repository. There, the wheel imported from site-packages and a thermally coupled case solved, using and hashing the packaged executable.
- The annual verification, the documentation and this record were left open when Step 5 stopped. They are completed under Step 6 below, against the final wheel.

## Step 6: cross-platform builds and verification of the installed artifacts (2026-09-27)

**Support matrix** (`docs/support-matrix.md`):
- Platforms: Linux x86_64 (manylinux_2_28), macOS arm64 (11.0), macOS x86_64 (10.15) and Windows AMD64, each on Python 3.11, 3.12, 3.13 and 3.14.
- Floors: the OS and glibc minimums are those of the OR-Tools 9.15.6755 wheels. That is still the newest OR-Tools release, with cp311–cp314 wheels on exactly these platforms.
- Excluded, with reasons:
  - Linux ARM: not built or tested yet.
  - Windows ARM, musl and 32-bit: OR-Tools publishes no wheels for them.
  - Free-threaded builds: Linux-only upstream, and untested.
  - Python 3.10 and earlier, and 3.15.

**What was added.**
- **Build and test configuration:**
  - `[tool.cibuildwheel]` in `pyproject.toml`: a single CPython 3.11 build per platform (the wheel is py3-none), explicit architectures, manylinux_2_28, and macOS deployment targets 11.0 and 10.15.
  - Repair commands: auditwheel, delocate, or none on Windows, each followed by `tools/inspect_native.py`.
  - An installed-test run inside cibuildwheel.
- **Workflow** (`.github/workflows/wheels.yml`):
  - Jobs: bundle, sdist (with a wheel built from it and tested), wheels (four platforms), installed tests on Linux (in `python:<v>-slim` containers, with no compiler, Git or checkout), installed tests on macOS and Windows (a fresh venv, no checkout step), the POSIX development suite, and a single `gate` job.
  - Security: actions are pinned to commit SHAs, permissions are `contents: read`, and there are no secrets, publishing or releases.
- **Tools:**
  - `tools/inspect_native.py`: checks the executable itself against the wheel tag. It uses auditwheel's policy data for ELF (libraries and GLIBC, GLIBCXX and CXXABI symbol versions), otool and lipo for Mach-O (architecture and minimum OS), and pefile for PE (no C++ runtime DLL). On a matching host it also runs the executable.
  - `tools/check_dist.py`: allow-lists the artifact contents.
  - `tools/test_installed_wheel.py`: runs the isolated installation and tests.
  - `tools/check_invariants.py`: the Step 1 checker, now tracked.
- **Tests and examples:**
  - `tests_installed/`: 45 tests.
  - `examples/`: two synthetic full-year cases, MIT-licensed and generated by `tools/build_examples.py`.
  - `examples/expected.json`: recorded in the reference environment.
- **Guidance:** `AGENTS.md`.

**Two narrow fixes found by the portability review.**
- `thermo/Cogen.cpp` used `std::setprecision` without including `<iomanip>`.
  - libc++ (macOS) provides it transitively; libstdc++ (GCC, MinGW) and MSVC need the include.
  - The include was added. No algorithm or output changed: the rebuilt executable reproduces the fixture exactly, 20 of 20.
- The Windows C++ runtime is now linked statically (`CMAKE_MSVC_RUNTIME_LIBRARY`).
  - The executable runs as a separate process, outside Python's DLL directories.
  - `msvcp140.dll` is not guaranteed on a clean system.

**Adjusted test.** The development test of the packaged executable demands exact fixture strings on macOS arm64, where exactness is established. Elsewhere it applies the Step 1 rule for other builds: one unit in the sixth significant digit. The installed tests apply that rule on every platform.

**Verified locally** (macOS 26.5.2 arm64, Apple clang 21):
- **Development suite:** 571 passed; mypy clean; schemas and examples current; actionlint clean on the workflow; the cibuildwheel configuration validates against its schema, with one build selected per platform.
- **The macOS arm64 wheel,** built as CI builds it (`MACOSX_DEPLOYMENT_TARGET=11.0`, delocate-wheel), is `py3-none-macosx_11_0_arm64`.
  - Its executable has minimum OS 11.0, is arm64 and links only `libSystem` and `libc++`.
  - `check_dist` and `inspect_native` pass, and the executable reproduces the fixture exactly.
  - SHA-256 digests are in `runs/step6-wheel-20260927T031218Z/artifacts/SHA256SUMS`.
- **Isolated installed-wheel tests,** 45 of 45 passed with no skips, on Python 3.11.16, 3.12.14, 3.13.15 and 3.14.7 (uv-managed), with dependencies as pip resolves them:
  - NumPy 2.4.6 on 3.11 and 2.5.3 on 3.12–3.14; OR-Tools 9.15.6755; Pydantic 2.13.5.
  - Also on 3.12 with the reference pins.
  - Reports are in `runs/step6-wheel-20260927T031218Z/installed-tests/`.
  - Isolation: a fresh venv in a temporary directory, installed with `--only-binary=:all:`; PATH reduced to the venv, so no Git, compiler, CMake or Ninja was reachable (asserted); no PYTHONPATH; `python -P`; the test bundle copied outside the repository; installation kind `wheel` (asserted). `sys.path` held only the interpreter and the venv.
- **Wheel from the sdist:** built from the extracted sdist in a separate directory, as CI's `sdist` job does, it passes `check_dist` and the same 45 isolated tests on 3.12.
- **Parser check:** the ELF and PE paths of `inspect_native.py` were exercised on NumPy's manylinux and win_amd64 binaries, which contain no IESO code; they correctly flag bundled libraries and MSVC runtime DLLs.
- **Reference environment:** the installed wheel, with Python 3.12.14, NumPy 2.0.2 and OR-Tools 9.15.6755, ran all eight annual configurations from outside the repository into `runs/step6-wheel-20260927T031218Z/cases`.
  - All eight optimal, `accounting_ok`, and passing the independent invariants.
  - **`IDENTICAL`** to `results/elec-grid-2026-09-26/` (the same three profile-string mappings as Steps 3–4), to the Step 4 runs and to the pre-move 3.12 runs, the last two without any mapping (`comparison.txt`).
  - Provenance differs only in `installation`, `thermo_binary`, `thermo_binary_origin`, the source digests, `ieso_version` (`2026.9.0`), `python`, the input paths, and the Git fields (null for a wheel). Input and profile digests are unchanged.

**Configured, not yet executed:** everything in `.github/workflows/wheels.yml`. Nothing has been pushed or dispatched, so these are unverified:
- the Linux, Windows and macOS x86_64 builds, including the GCC and MSVC compiles, auditwheel on an executable-only wheel, and the Windows static runtime;
- the installed tests on those platforms;
- the `python:<v>-slim` containers, the `macos-15-intel` runner label and the POSIX development suite on Linux.

**Release gate: not passed.** Cross-platform verification is pending until the workflow has run successfully, with `gate` green, on a pushed branch or by manual dispatch. Publishing (Step 7) must wait for it.

## Step 7: release preparation (2026-09-27) — no release made

**Readiness at the start.**
- **Source:** `main` at `a1b2cb2`, level with `origin/main`. The changes of Steps 2–7 are all uncommitted: 63 paths at the start of this step.
- **GitHub:** `greoux-research/ieso` is public, with no workflows and no workflow runs. Nothing from Step 6 has run remotely, so no cross-platform gate has passed.
- **Earlier releases:** tags and GitHub releases `v25.10` and `v26.05`.
- **Package indexes:** PyPI and TestPyPI serve no `ieso` project (both JSON and simple endpoints return 404). That does not show the name can be registered.

**Version.** The first candidate is `2026.9.0rc1`, set in `pyproject.toml`. It is a prerelease, published to TestPyPI only. The final `2026.9.0` is a separate candidate, with its own commit, run and artifacts. `tools/release_check.py` requires the tag to name the source version, the commit to be on `main`, and the version to be new on both indexes.

**Prepared.**
- **`release.yml`**, triggered by a `v*` tag only:
  - check, then build with the whole of `wheels.yml` (made callable);
  - collect: twine check, content checks and `SHA256SUMS`;
  - upload to TestPyPI (environment `testpypi`), then verify on all four platforms (Python 3.11 and 3.14) with `verify-index.yml` and `tools/verify_index_install.py`;
  - final versions only: PyPI (environment `pypi`, with required reviewers), then verification including an unversioned `pip install ieso`.
- **Publishing safeguards:**
  - Publishing uses `pypa/gh-action-pypi-publish` v1.14.2, pinned to a SHA, with Trusted Publishing.
  - `id-token: write` is granted only to the two upload jobs.
  - The upload jobs never rebuild: they check the files against `SHA256SUMS` before uploading.
- **Documentation:** `docs/releasing.md` (the account-side settings), `CHANGELOG.md`, and a README that works as the PyPI page (absolute links; installation described as not yet published; tested examples).

**Local rehearsal (not a release artifact).** On macOS arm64:
- `python -m build` built the rc1 sdist, then a wheel from it, with `MACOSX_DEPLOYMENT_TARGET=11.0`, and delocate processed the wheel.
- `twine check --strict` passed, as did `check_dist` (the sdist holds only the package, native sources and metadata) and `inspect_native`.
- SHA-256 digests are in `runs/step7-rehearsal-20260927T033914Z/SHA256SUMS`.
- `verify_index_install.py`, pointed at a local PEP 503 index serving that wheel:
  - it installed only `ieso` from that index, with hash and version checked against `SHA256SUMS`;
  - then it installed the dependencies from production PyPI in a separate step;
  - all 47 installed tests passed in isolation, and the native inspection passed.
  - The hash, host and version checks also failed when fed a wrong hash, host or version.
- The development suite (571 tests), mypy and the generated-file checks pass at `2026.9.0rc1`.

**Not done, and why.**
- Nothing has been committed, tagged, pushed, dispatched or uploaded. Those actions need your explicit authorisation, and the account-side Trusted Publishing and environment settings are yours to make.
- Consequently, none of these has run: the cross-platform CI (Step 6), the release workflow, the TestPyPI upload and verification, and the PyPI upload and verification.
- **The release gate has not passed. IESO is not published.**

### Step 7 review: three findings, fixed (2026-09-27)

An independent review of the prepared release found three defects. All three were reproduced and are fixed, with no change to equations, numerical inputs or conventions.

1. **The sdist job would fail on its own wheel's tag.**
   - The wheel it builds from the sdist is `linux_x86_64`, built on the runner and never distributed. `inspect_native.py` required a manylinux tag for every ELF wheel, so the job, and with it the release gate, would have failed.
   - Fix: `--local-build` (in `inspect_native.py` and `test_installed_wheel.py`) checks such a wheel as what it is: a plain `linux_<arch>` tag and nothing else, a matching machine, reported dependencies, and an executable that runs. The sdist job uses it.
   - Distributable wheels are still held to the manylinux policy, without the flag. A manylinux tag is refused in local-build mode, so the flag cannot disguise a distributable wheel. Both paths were exercised on a real ELF binary.
2. **A case edited in memory recorded its source file's hash.**
   - `solve(case, source=path)` hashed the file, even when the dictionary solved differed from it. Reproduced: a total demand of 2 in the file and 4 in memory gave one `input_sha256`.
   - Fix: provenance keeps `input_sha256` for the file named, and adds `case_sha256` (the canonical digest of the case actually solved) and `source_matches_case`.
3. **`RunConfig` accepted malformed settings.**
   - `hours=0` raised `ZeroDivisionError` inside `validate()`. `storage_closes_the_year='false'` read as true and changed the result.
   - Fix: `RunConfig` checks its fields when created. It requires a positive integer horizon (booleans excluded), a real bool, a finite positive timeout, and paths as strings or path-like objects (normalised to strings). Anything else raises `InputError` (`config.invalid`, layer `configuration`, the field named).

**Tests added:** 21 cases of malformed settings, path-like normalisation, and provenance for edited, file, path, in-memory, legacy and canonical cases, plus an installed-test assertion.

**Verification:**
- Development suite: 594 passed. mypy is clean, and the schemas (the result schema regenerated) and the examples are current. actionlint is clean.
- The rc1 rehearsal artifacts were rebuilt and pass twine, the content checks and the native checks.
- Isolated installed-wheel tests (Python 3.12, reference pins): 47 passed.
- All eight annual configurations, through the rebuilt wheel, are **`IDENTICAL`** to the stored reference (profile strings mapped) and to the Step 6 wheel runs, and pass the independent invariants. Provenance differs from Step 6 only in the new fields, the code digest and the installation paths.
- Evidence: `runs/step7-review-fixes-20260927T035032Z/`.

Cross-platform CI and publication remain pending, exactly as before.


## Project rename verification — 2026-09-27

The project is now `ies-optimiser` (distribution and CLI), with Python package
`ies_optimiser`. Documentation, source and native identifiers, schema filenames,
output filenames and provenance names follow the rename. Earlier entries in this
record, `results/`, previously built `dist/` artifacts and `examples/expected.json`
retain the names under which their evidence was recorded. No input numbers,
solver settings, equations, profile conventions or comparison tolerances changed.

Verification used Python 3.12.14, NumPy 2.5.3, OR-Tools 9.15.6755 and Pydantic
2.13.5 on macOS arm64. The pre-rename sources were copied before renaming;
they and the renamed editable package ran in the same Python environment.
The baseline used the existing packaged thermodynamics executable; the renamed
executable was rebuilt from the renamed C++ sources, whose only changes are
identifiers and includes. All Python numeric literals were also checked unchanged.

- Development suite: **594 passed**. The initial run exposed seven output-suffix
  mismatches; after correcting the runtime suffix to `.ies-optimiser`, the full
  suite passed. The subsequent comparator compatibility tests passed **92 tests**,
  including five new cases covering historical provenance, missing/ambiguous
  version fields, invalid types and detection of changed numerical values.
- Public-boundary mypy: **passed**, 10 source files. Generated schemas and
  examples: **up to date**. Dataset regeneration left all JSON inputs and profiles
  unchanged. `git diff --check`: **passed**.
- A source distribution and a macOS arm64 wheel built from that sdist: **passed**
  content inspection. Native inspection: **passed**, system libraries only,
  arm64, macOS 11.0 minimum, executable permissions and thermodynamics probes.
- Fresh wheel installation outside the checkout, with the isolation harness:
  **47 passed**; installed native inspection also **passed**. Build artifacts are
  local verification artifacts under `<scratch>/ies-optimiser-dist/`; nothing
  was uploaded, committed or pushed.
- All eight bundled configurations were run through `tools/run_cases.sh` (the
  pre-rename copy for the baseline), into `runs/rename-baseline-final-20260927/`
  and `runs/rename-after-20260927/`. Every solve was **optimal** with
  **accounting_ok=true**. All eight comparisons are **IDENTICAL** under
  `tools/compare_outputs.py`, and a separate recursive equality check found
  exact equality after excluding only provenance and `solver.stat_time`.
  Independent `tools/check_invariants.py` checks: **8/8 passed**. Thus problem
  sizes, objective, capacities, emissions, coefficients and all dispatch values
  are unchanged in this environment.

The comparator requires exactly one string version field: current
`ies_optimiser_version` or historical `ieso_version`. This keeps archived results
comparable without rewriting them. Explicit `--provenance` comparisons still
report the field rename; numerical assertions and tolerances are unchanged.
The first comparison correctly rejected the old spelling until this explicit
compatibility handling was added. Preliminary baseline attempts using the old
editable environment could not resolve the moved package; the successful baseline
above uses the preserved source copy and the common verification environment.

Per-case comparison reports, `_invariants.txt`, environment records and test/build
logs are under `runs/rename-after-20260927/` (logs in `verification/`). The existing
`results/` references were not modified. No `.github/workflows/` directory was
present in this checkout to update or run; cross-platform CI remains unverified
for this rename.

### Follow-up review and corrections — 2026-09-27

The user supplied an independent review reporting a fresh editable build,
**599 development tests passed**, clean mypy/generated-file checks and the same
renamed thermodynamics digest. The reviewer also reported eight optimal annual
runs, reconciling accounts, independent invariants passing, and IDENTICAL results
against the pre-rename baseline in the same environment.

Against the committed NumPy 2.0.2 references, the review reports cost agreement
within 3e-15 relative and identical capacities, problem sizes and cogeneration
coefficients. Dispatch differences observed with NumPy 2.5.3 produced identical
comparison reports before and after the rename, supporting the conclusion that
they were not introduced by the rename. These additional cross-environment
findings are attributed to the supplied review; its scratchpad reports were not
provided with the feedback and were not independently rerun during this follow-up.

The review identified and this follow-up corrected two test guards: flag-error
checks now look for `.ies-optimiser` outputs, and source provenance still guards
against the historical `ieso_modules/` layout. Wheel installation examples now
use the normalized `ies_optimiser-2026.9.0rc1-...whl` filename. Comment placement,
import alignment and the documented CLI spelling were corrected as well.

A `.gitignore` now excludes new run, build, distribution, native-object and
Python-cache artifacts. It does not untrack the historical artifacts already in
the repository. No reference artifacts or index entries were removed. The
`.github/workflows/` files and the old Git history were afterwards recovered
from a local clone of the original repository; see the next section.

Follow-up validation: `tests/test_paths.py`, `tests/test_tooling.py` and
`tests/test_comparator.py`: **132 passed**, with three upstream SWIG deprecation
warnings. `git diff --check` passed. Ignore checks confirmed new `runs/`, `build/`,
`dist/` and Python cache files are excluded while previously tracked artifacts
remain tracked. All five historical commit IDs listed by the reviewer were
confirmed absent locally (`git cat-file`). No solver code or inputs changed in
this follow-up, so annual numerical runs were not repeated.

### History and workflows recovered — 2026-09-27

**Source.** A local clone of the original repository
(`origin https://github.com/greoux-research/ieso.git`, since renamed) was found at
`<scratch>/ieso-ci-repro/ieso`: 31 commits on `main` ending at
`430d2fcf486b8fc57236bdf9ac1934dfef720054`, the tags `v25.10` (`b9090e7`) and
`v26.05` (`e3f4548`), and the three workflows. Its only uncommitted change, the
`[tool.mypy]` comment in `pyproject.toml`, is already in this repository. The
public repository no longer serves these commits (`44db591` is not found there).

**The re-upload is that history's continuation.** The tree of the re-upload
commit `9ad6f45` equals that of `430d2fc` except for: that one `pyproject.toml`
change; `.github/` and `.gitignore`, absent from the re-upload; and files the old
`.gitignore` excluded, present in the re-upload (`runs/`, `dist/`, `__pycache__/`,
`thermo/*.o`, `thermo/sim.bin`). Those were never tracked before the re-upload.

**Bundle.** `git bundle create <maintainer-local>/ieso-history.bundle --all`, from that
clone: 15,499,778 bytes, SHA-256
`925c6f8038af80d4af35445bc016ab5593c4bfde7f2271c590f50cc8a2e0e7f9`, holding
`refs/heads/main` (`430d2fc`) and both tags. `git bundle verify`: complete
history. Checked in a fresh clone of the bundle alone:

- every commit this record cites resolves: `44db591`, `a3ff7a5`, `e900e36`,
  `aa761ef`, `a663acb`, `a1b2cb2` (short and full forms) and `b9090e7`;
- the eight pre-correction results at `44db591` reproduce the SHA-256 digests of
  the table at the top of this record, 8 of 8;
- the four Step 1 inputs at `a1b2cb2` reproduce the digests of the Step 1 table,
  4 of 4;
- `aa761ef:results/2026-09-26/` is present.

The bundle is a single file on one disk, outside this repository. Copying it
elsewhere, or pushing it to an archive repository, is still to be decided.

**Workflows.** `wheels.yml`, `release.yml` and `verify-index.yml` were restored
from `430d2fc` with 14 changed lines and nothing else:

- artifact file names `ieso-*` → `ies_optimiser-*` (wheel and sdist names
  normalise the hyphen to an underscore), in the release file checks,
  `SHA256SUMS`, the upload staging, and the extracted-sdist directory;
- PyPI and TestPyPI project URLs → `/project/ies-optimiser/`;
- bundled documentation → `docs/ies-optimiser-api.md`,
  `docs/ies-optimiser-setup-guide.md`;
- comments: "IESO" → "IES Optimiser", and `pip install ies-optimiser`.

Validation, local only:

- No YAML key, job, action pin or indentation changed, so the structure is the
  one Step 7 recorded as actionlint-clean. The recovery review did not locate
  actionlint; the subsequent follow-up found the existing binary and re-ran it
  successfully, as recorded below.
- The release job's file checks, checksum and upload-staging commands were run
  against empty files named as this build names them
  (`ies_optimiser-2026.9.0rc1-py3-none-<tag>.whl` for the four tags, and the
  sdist). All checks passed, and 5 files were staged with `SHA256SUMS` left
  behind. The old `ieso-*` pattern matches none of these files.
- The sdist built for this rename extracts to `ies_optimiser-2026.9.0rc1/`, the
  directory `wheels.yml` changes into.
- Every repository path the workflows name exists.
- `tools/release_check.py --tag v2026.9.0rc1` passes, and refuses `v2026.9.0`.

**Package name.** On 2026-09-27, PyPI and TestPyPI answered 404 on both their
JSON and simple endpoints for `ies-optimiser`, `ies_optimiser` and
`ies.optimiser`. The name is unregistered; that does not prove it can be
registered.

**Not done.** Nothing was committed, pushed, tagged or dispatched. No workflow
has run on GitHub, so the cross-platform release gate of Step 6 still has not
passed. Trusted Publishing (project `ies-optimiser`, repository
`ies-optimiser`) and the `testpypi` and `pypi` environments of the new GitHub
repository were not yet configured at the time of recovery; the maintainer
subsequently confirmed their configuration (see the cleanup entry below).

### Recovery follow-up validation — 2026-09-27

The existing `<scratch>/ieso-ci-tools/bin/actionlint` was located and run
against all three restored `.github/workflows/*.yml` files: **passed**, exit 0,
no diagnostics and no download required. This validates the workflow definitions
locally; it does not replace executing the platform jobs on GitHub.

`git bundle verify <maintainer-local>/ieso-history.bundle` was independently
re-run: **complete history**, with `main`, both historical tags and the original
remote refs. Its SHA-256 matches the recovery record above exactly. The release
and support documentation now reflects restored workflows with GitHub execution
still pending, instead of incorrectly reporting the directory as absent.

`git diff --check` passed. HEAD remains `9ad6f4570c9e1d1417b278d53f5cba8f73098b12`;
nothing was committed, pushed, tagged, published or dispatched. The bundle and
temporary recovery clone were not deleted or modified.

### Pre-commit repository cleanup — 2026-09-27

With the maintainer's authorization, 499 local files (482,546,093 bytes) were
archived to `<maintainer-local>/ies-optimiser-archive-2026-09-27-precommit/`.
Every copy was verified by SHA-256 before its source was removed. The archive
contains the historical and rename-verification `runs/`, obsolete `dist/`
artifacts, Python/type-checker caches, native object files and the standalone
reference `thermo/sim.bin`. Its `MANIFEST.json` records paths, sizes, hashes and
tracked status; `README.txt` explains restoration. Of those files, 392 were
tracked and will be removed from the repository by the maintainer's next commit.
The index was not staged or otherwise changed by this cleanup.

Source files, native build sources, workflows, tools, tests and fixtures,
examples, datasets, documentation and all `results/` reference files were kept.
The separate `<maintainer-local>/ieso-history.bundle` was not changed. The existing
`.gitignore` prevents generated artifacts from being added again. This cleanup
changes no equations, input values, solver settings or runtime code.

The maintainer confirms Trusted Publishing is configured on both PyPI and
TestPyPI for project `ies-optimiser`, repository `ies-optimiser`, and that GitHub
`testpypi` and `pypi` environments have been created. This is maintainer-reported
configuration, not a completed release verification; the first GitHub workflow
execution remains pending. No commit, push, tag or publication was performed.

Cleanup validation: full development suite **589 passed, 10 skipped**, with
three upstream SWIG deprecation warnings. The ten skips are exclusively the
historical reference executable's fixture-replay tests because `thermo/sim.bin`
is now archived; fresh-source thermodynamics and installed-package tests in the
development suite passed. No tests or assertions were modified for the cleanup.
Public-boundary mypy: **passed**, 10 files. Generated schemas/examples: **current**.
All three workflows: **actionlint passed**. `git diff --check`: **passed**.
Every file in `results/` was independently compared byte-for-byte with HEAD:
**unchanged**. The checkout now contains approximately 43,939 KB of files outside
`.git` (including the retained reference results). Numerical runs were not
repeated because no runtime code or model input changed.

## First remote CI and TestPyPI release candidate — 2026-09-27

The rename, the restored workflows and the cleanup were committed and pushed
by the maintainer as `da20deb796d23f22ba23c947d4779c4eb10403a9` on `main`. It
is the first commit to run the workflows prepared in Steps 6 and 7.

**Cross-platform verification: `wheels.yml` on `main`.** Run
[36307899271](https://github.com/greoux-research/ies-optimiser/actions/runs/36307899271),
triggered by the push (08:58–09:32 UTC): **25 of 25 jobs succeeded**,
including `gate`.

- **Wheels** built, repaired and native-checked on all four platforms of the
  support matrix: Linux x86_64 (manylinux, GCC), macOS arm64, macOS x86_64 and
  Windows AMD64 (MSVC, static runtime). Before this run, only macOS arm64 had
  been built.
- **Installed-wheel tests** in isolation: 16 of 16, one per platform and Python
  version (3.11, 3.12, 3.13 and 3.14). Linux ran in `python:<v>-slim`
  containers; macOS and Windows used fresh environments with no checkout.
- **Source distribution:** built, content-checked, and a wheel built from it
  was tested.
- **Development suite, mypy and generated-file checks:** passed on Ubuntu and
  macOS.

Every item the Step 6 record listed as "configured, not yet executed" has now
run and passed. The cross-platform release gate of Step 6 has passed.

**Release candidate: `release.yml` on tag `v2026.9.0rc1`.** The annotated tag
points to `da20deb`. Run
[36309847312](https://github.com/greoux-research/ies-optimiser/actions/runs/36309847312)
(09:35–10:30 UTC): **36 jobs succeeded and 2 were skipped by design**.

| Stage | Result |
|---|---|
| `check`: the tag names the source version, the commit is on `main`, and the version is new on both indexes | passed |
| `build`: the whole of `wheels.yml`, again, on the tagged commit | passed |
| `collect`: file-name checks, `twine check --strict`, content checks, `SHA256SUMS` | passed |
| `testpypi`: upload through Trusted Publishing, with no API token | passed |
| `verify-testpypi`: installed from TestPyPI and tested on the four platforms, Python 3.11 and 3.14 each | 8 of 8 passed |
| `pypi`, `verify-pypi` | skipped: a prerelease stops after TestPyPI |

The verification jobs install only `ies-optimiser` from TestPyPI, checking its
hash against the run's `SHA256SUMS` and the host it came from. They then install
the dependencies from PyPI and run the installed-artifact tests.

**Published on TestPyPI** as
[`ies-optimiser` 2026.9.0rc1](https://test.pypi.org/project/ies-optimiser/2026.9.0rc1/),
uploaded 10:16:57–10:17:04 UTC, `Requires-Python >=3.11`. SHA-256 as served by
TestPyPI:

| File | SHA-256 |
|---|---|
| `ies_optimiser-2026.9.0rc1-py3-none-macosx_10_15_x86_64.whl` | `cf1a2d2ec02092884345842de0de06ee18a9f8abf2bf5c6612563bfe8c0863f8` |
| `ies_optimiser-2026.9.0rc1-py3-none-macosx_11_0_arm64.whl` | `5dcb449deb1c1cb738c9db2b377012424d449eb4e462a5929cb9d1f41443cd69` |
| `ies_optimiser-2026.9.0rc1-py3-none-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl` | `2f0261daeed9af1d8fbbd50b1f0f68ca9080eb6c13505850d14186cc0fc4b2c8` |
| `ies_optimiser-2026.9.0rc1-py3-none-win_amd64.whl` | `31577fa64595ab9f55e3bbf105308fb4fb63aac3e3821819ca1e9a6843ee6fca` |
| `ies_optimiser-2026.9.0rc1.tar.gz` | `c923fb8ded9c709e606ba7682d5115fa1e83662744892e5d6310e072e54f7e27` |

These digests were read from TestPyPI's JSON API after the run. The run's own
`SHA256SUMS` is in its `release-dist` artifact, which was not downloaded here.
Its agreement with these files is what `verify-testpypi` checked on every
platform.

**Observation: the Linux wheel's tags.** The Linux wheel carries two platform
tags, `manylinux_2_24` and `manylinux_2_28`: auditwheel found the executable
compatible with glibc 2.24 and added the older tag. The effective floor stays
glibc 2.28, set by the OR-Tools dependency, as `docs/support-matrix.md` states.
Restricting the wheel to the documented tag is a possible change to the repair
command; it is not required.

**What this establishes, and what it does not.** It establishes that the
renamed package builds, installs and passes its installed-artifact tests on
every supported platform and Python version. It also shows that Trusted
Publishing to TestPyPI works end to end, with the published files being those
that were tested. It does not cover PyPI: no final version has been released.
The `pypi` job, its manual approval and `verify-pypi`, including the unversioned
`pip install ies-optimiser`, have not run. The installed tests compare the
synthetic examples under the cross-environment contract. The eight bundled
annual configurations were not re-run by CI.

**Remaining:** a final release, `2026.9.0`, which follows `docs/releasing.md`
and needs approval in the `pypi` environment; and the off-disk backup of the
evidence archive and history bundle.
