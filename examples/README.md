# Synthetic examples

Two small full-year IESO cases in the canonical input format, used by the
installed-artifact tests on every supported platform and as runnable examples:

- `electricity-storage/` -- solar, two gas units and a battery meeting an
  electricity demand (solved with and without a carbon cap in the tests);
- `power-to-x-thermal/` -- a cogeneration unit supplying heat to a
  multi-effect distillation process (thermally coupled Power-to-X), with
  electricity and water demands. Solving it runs the thermodynamics executable.

Everything here is synthetic: the profiles are closed-form expressions and the
costs round illustrative numbers, written by `tools/build_examples.py`. Nothing
is taken from the datasets in `datasets/` or any other source. The examples
are covered by the repository's MIT licence. They illustrate the model; they
describe no real system.

    ieso validate examples/power-to-x-thermal/case.json
    ieso examples/electricity-storage/case.json carbon-constraint=150

`expected.json` holds the reference results the tests compare against, with
the environment that produced them (`python tools/build_examples.py
--record-expected`).
