#!/bin/bash
# Gréoux Research. IESO: https://github.com/greoux-research/ieso
#
# Non-destructive scenario runner.
#
# Each input is COPIED into the run directory before solving, so IESO writes its
# output beside the copy and the tracked results under datasets/ are never
# touched. Profile paths inside the inputs are relative to the repository root,
# which is why the solver is invoked from there.
#
# Usage:  tools/run_cases.sh [run-directory]     (default: runs/<UTC timestamp>)

set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$REPO/runs/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
cd "$REPO" || exit 1

run () {  # run <label> <input.json> [name=value ...]
  local label=$1 src=$2; shift 2
  cp "$src" "$OUT/$label.json"
  local t0 rc t1
  t0=$(date +%s)
  python3 ieso.py "$OUT/$label.json" "$@" > "$OUT/$label.log" 2>&1
  rc=$?; t1=$(date +%s)
  printf '%-10s rc=%d %4ds opts=[%s]\n' "$label" "$rc" "$((t1-t0))" "$*" | tee -a "$OUT/_summary.txt"
}

: > "$OUT/_summary.txt"
{ echo "commit:      $(git rev-parse HEAD 2>/dev/null)"
  echo "python:      $(python3 -V 2>&1)"
  echo "numpy:       $(python3 -c 'import numpy;print(numpy.__version__)' 2>/dev/null)"
  echo "ortools:     $(python3 -c 'import ortools.init.python.init as i;print(i.OrToolsVersion.version_string())' 2>/dev/null)"
  echo "platform:    $(uname -sr)"
  echo "recorded:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/_environment.txt"

O="carbon-constraint=50 non-served-power-constraint=0.05"
run eg-base   datasets/elec-grid/elec-grid---mid-west.json
run eg-cn     datasets/elec-grid/elec-grid---mid-west.json $O
run h2-base   datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---nyiso.json
run h2-cn     datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen---nyiso.json $O
run med-base  datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med---florida.json
run med-cn    datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med---florida.json $O
run swiss2025 datasets/swiss-grid-2025/swiss-grid---2025.json
run swiss2050 datasets/swiss-grid-2050/swiss-grid---2050.json
echo "DONE" >> "$OUT/_summary.txt"
echo "results in $OUT"
