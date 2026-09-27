# Illustrative results

The four [example datasets](../../datasets/README.md), rerun after rounding their
inputs. Labels `eg`, `h2`, `ro` and `med` identify the electricity-only, hydrogen,
reverse-osmosis and multi-effect-distillation cases. `base` has no carbon cap;
`cn` applies `carbon-constraint=50 non-served-power-constraint=0.05`.

Each case README contains its results summary and links to the shared metric
conventions. These are model examples, not estimates for a country or current
market conditions.

Regenerate from the repository root with `bash tools/run_cases.sh runs/examples`.
The result JSONs contain input/profile hashes, solver options and code provenance;
`_environment.txt`, `_summary.txt` and the logs record this run. Source hashes
identify the executed code; the Git revision alone does not include uncommitted
input changes. This snapshot replaces the previous runs of these examples.
