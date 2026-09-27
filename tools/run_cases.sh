#!/bin/bash
# Gréoux Research. IESO: https://github.com/greoux-research/ieso
#
# Non-destructive scenario runner.
#
# Each input is COPIED into the run directory as <label>.json before solving, so
# IESO writes its result beside the copy, named after the run label, and nothing
# under datasets/ is ever written. The copy's profile paths are relative to the
# ORIGINAL case directory, so each run is given that directory explicitly with
# --profile-base; the result's provenance records it (profile_resolution) along
# with the files actually read. Works from any directory.
#
# The cases are solved by the IESO installed in $PYTHON's environment
# (python -P -m ieso; -P keeps the calling directory, which may be this
# checkout with its ieso.py launcher, off sys.path): an editable install of
# this checkout, or a wheel. Python 3.11 or later. The
# environment record names the package that ran, its version and the
# thermodynamics executable it resolved.
#
# Usage:  tools/run_cases.sh [run-directory]     (default: <repository>/runs/<UTC timestamp>)
#         PYTHON=/path/to/python tools/run_cases.sh ...   (default: python3)
# A relative run-directory is taken from the directory the script is called from.

set -u
PY="${PYTHON:-python3}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$REPO/runs/$(date -u +%Y%m%dT%H%M%SZ)}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
mkdir -p "$OUT" || exit 1

FAILURES=0

run () {  # run <label> <input.json, relative to the repository> [name=value ...]
  local label=$1 src="$REPO/$2"; shift 2
  cp "$src" "$OUT/$label.json"
  local t0 rc t1 status
  t0=$(date +%s)
  "$PY" -P -m ieso "$OUT/$label.json" "$@" --profile-base "$(dirname "$src")" > "$OUT/$label.log" 2>&1
  rc=$?; t1=$(date +%s)
  # IESO exits 1 when the solve did not reach an optimal solution, 3 when it
  # did but the result failed its own accounting checks, 2 or 1 on a refused
  # input. Any non-zero exit is a failure here.
  [ "$rc" -ne 0 ] && FAILURES=$((FAILURES+1))
  status=$("$PY" - "$OUT/$label" <<'PY' 2>/dev/null || echo unknown
import glob, json, sys
files = sorted(glob.glob(sys.argv[1] + '.ieso*.json'))
if not files:
    print('no-output')
else:
    doc = json.load(open(files[-1]))
    ok = doc.get('system', {}).get('accounting_ok')
    print(doc['solver'].get('stat_status', 'unknown') + ('' if ok is None else ' accounts=' + ('ok' if ok else 'FAILED')))
PY
)
  printf '%-10s rc=%d %-22s %4ds opts=[%s]\n' \
    "$label" "$rc" "$status" "$((t1-t0))" "$*" | tee -a "$OUT/_summary.txt"
}

: > "$OUT/_summary.txt"
{ echo "commit:      $(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
  echo "dirty:       $(git -C "$REPO" status --porcelain 2>/dev/null | grep -q . && echo yes || echo no)"
  echo "python:      $("$PY" -V 2>&1) ($PY)"
  echo "numpy:       $("$PY" -c 'import numpy;print(numpy.__version__)' 2>/dev/null)"
  echo "ortools:     $("$PY" -c 'import ortools.init.python.init as i;print(i.OrToolsVersion.version_string())' 2>/dev/null)"
  "$PY" -P - <<'PY' 2>&1
from ieso import _install, fcn
install = _install.installation()
print('ieso:        ' + str(install['version']) + ' (' + install['kind'] + ', ' + install['package_dir'] + ')')
print('thermo:      ' + str(fcn.file_digest(fcn.Thermo_bin)) + ' (' + fcn.Thermo_bin + ')')
PY
  echo "platform:    $(uname -sr)"
  echo "recorded:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/_environment.txt"

O="carbon-constraint=50 non-served-power-constraint=0.05"
run eg-base   datasets/elec-grid/elec-grid.json
run eg-cn     datasets/elec-grid/elec-grid.json $O
run h2-base   datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen.json
run h2-cn     datasets/elec-grid+power-to-hydrogen/elec-grid+power-to-hydrogen.json $O
run ro-base   datasets/elec-grid+power-to-water-ro/elec-grid+power-to-water-ro.json
run ro-cn     datasets/elec-grid+power-to-water-ro/elec-grid+power-to-water-ro.json $O
run med-base  datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med.json
run med-cn    datasets/elec-grid+power-to-water-med/elec-grid+power-to-water-med.json $O
if [ "$FAILURES" -eq 0 ]; then
  echo "DONE" >> "$OUT/_summary.txt"
else
  echo "DONE with $FAILURES unsuccessful solve(s)" >> "$OUT/_summary.txt"
fi
echo "results in $OUT"

# Non-zero if any case failed, so a caller need not read the summary.
exit $(( FAILURES > 0 ? 1 : 0 ))
