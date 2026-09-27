#!/usr/bin/env python3
"""Compare two IESO results field by field.

    tools/compare_outputs.py NEW OLD [--legacy] [--provenance]

Everything both files carry is compared, recursively: capacities, dispatch,
inventory, spill, unmet demand, surplus, heat series, coefficients, KPIs,
accounts, system totals and their reconciliation checks, availability
reports, shadow prices, cap details and solver status. Nothing is skipped
because it is absent: a field present in one file and not the other is a
difference, and each file is also checked on its own for what a result must
carry (heat output on a thermal unit, spill on an inflow-fed store, accounts on
an active demand...). A field missing from BOTH files is therefore still
caught.

Numbers are compared element by element:  |new - old| <= ATOL + RTOL * |old|.
The tolerance scales with each value, not with the largest value in a series,
so one large entry cannot excuse an error elsewhere. NaN and infinities are
reported wherever they occur, in either file.

Exclusions are explicit and are printed with every comparison:
  solver.stat_time       elapsed wall-clock time
  provenance             identifies the run (code digest, Git state, input path,
                         environment, timestamp), so it differs between any two
                         runs that are meant to be compared. --provenance
                         compares it too, except provenance.run_utc.

--legacy compares a new result against a pre-correction baseline (the archived
results under datasets/). Fields the baseline predates are listed under NOT
COMPARED -- never silently skipped -- and the old [-1, -1] cost placeholder is
read as -1. Everything the baseline does carry is compared as strictly as
ever, and a field missing from the NEW result is still a difference.

Exit status: 0 identical, 1 differences, 2 unreadable input (including
duplicate JSON keys).
"""

import json
import math
import re
import sys

RTOL, ATOL = 1e-9, 1e-6

ENTITY_LISTS = ('generator', 'flex', 'p2x', 'demand.x')

ALWAYS_EXCLUDED = {
    'solver.stat_time': 'elapsed wall-clock time',
    'provenance.run_utc': 'timestamp',
}
PROVENANCE_EXCLUDED = {'provenance': 'identifies the run; compare with --provenance'}

# Fields, and fields within blocks, that pre-correction results do not carry
# (legacy mode only). Anything under these that the baseline DOES carry is
# still compared.
LEGACY_ABSENT = re.compile(
    r'^(system|provenance|solver\.stat_status'
    r'|demand\.(e|x\[[^\]]+\])\.(accounts|surplus)'
    r'|demand\.e\.shadow_prices\.(carbon|reliability)_cap_detail'
    r'|generator\[[^\]]+\]\.availability'
    r'|p2x\[[^\]]+\]\.(availability|heat_surplus))(\..*)?$')

MAX_LINES_PER_SERIES = 1


class DuplicateKey(ValueError):
    pass


def load(path):
    def pairs(items):
        seen = {}
        for k, v in items:
            if k in seen:
                raise DuplicateKey(f"duplicate key '{k}' in {path}")
            seen[k] = v
        return seen

    with open(path) as f:
        return json.load(f, object_pairs_hook=pairs)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def generic(path):
    """'generator[chp].h_prod' -> 'generator[*].h_prod', for grouping."""
    return re.sub(r'\[[^\]]*\]', '[*]', path)


# --- one file on its own ------------------------------------------------------

def non_finite(node, path, out, limit=20):
    if len(out) >= limit:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            non_finite(v, f'{path}.{k}' if path else k, out, limit)
    elif isinstance(node, list):
        bad = [i for i, v in enumerate(node) if is_num(v) and not math.isfinite(v)]
        if bad:
            out.append(f'{path}: {len(bad)} non-finite value(s), first at [{bad[0]}]')
        for i, v in enumerate(node):
            if isinstance(v, (dict, list)):
                non_finite(v, f'{path}[{i}]', out, limit)
    elif is_num(node) and not math.isfinite(node):
        out.append(f'{path}: non-finite ({node!r})')


# Required contents, by block. NUM: a finite number; OPT: a finite number or
# null (undefined, e.g. a share when there is no output); BOOL; STR; DICT;
# HEX64: a SHA-256 digest.
NUM, OPT, BOOL, STR, DICT, HEX64, ANY = 'number', 'number or null', 'boolean', 'string', 'object', 'digest', 'any'

ACCOUNTS = {'allocation_share': OPT, 'allocated_output': NUM, 'resource_cost': OPT,
            'shortage_penalty': NUM, 'emissions': OPT, 'demand': NUM, 'unmet_demand': NUM,
            'served_demand': NUM, 'resource_cost_per_demand': OPT, 'resource_cost_per_served': OPT,
            'surplus': NUM}
KPIS = {'cost': NUM, 'emis': NUM, 'reli': NUM}
AVAILABILITY = {'capacity_factor_requested': NUM, 'profile_peak': NUM,
                'capacity_factor_effective': NUM, 'hours_above_nameplate': NUM}
CAP_DETAIL = {'raw_dual': NUM, 'cap': NUM, 'activity': NUM, 'slack': NUM,
              'binding': BOOL, 'binding_zero_dual': BOOL}
SHARE_BLOCK = {'output': NUM, 'share': OPT, 'cost': NUM, 'emis': NUM}
UNALLOCATED = dict(SHARE_BLOCK, electricity_surplus=NUM, unused_heat=NUM, unassigned_process_use=NUM)
SURPLUS = {'electricity': NUM, 'heat': NUM, 'spill': NUM, 'products': DICT,
           'unassigned_product_supply': DICT}
SYSTEM = {'cost': NUM, 'output': NUM, 'emis': NUM, 'allocation_defined': BOOL,
          'allocated_share_total': OPT, 'allocated': DICT, 'unallocated': DICT,
          'surplus': DICT, 'checks': DICT, 'accounting_ok': BOOL}
CHECK = {'residual': NUM, 'tolerance': NUM, 'ok': BOOL}
PROVENANCE = {'ieso_version': STR, 'input': STR, 'input_sha256': HEX64, 'profiles_sha256': DICT,
              'options': DICT, 'hours': NUM, 'storage_closes_the_year': BOOL, 'solver': STR,
              'ortools': STR, 'numpy': STR, 'python': STR, 'platform': STR, 'run_utc': STR,
              'git_scope': ANY, 'git_revision': ANY, 'git_dirty': ANY, 'enclosing_git': ANY,
              'source_sha256': HEX64, 'source_files_sha256': DICT, 'thermo_binary': STR}
SOLVER = {'stat_succ': NUM, 'stat_capa': NUM, 'stat_outp': NUM, 'stat_cons': NUM}


def kind_ok(v, kind):
    if kind == ANY:
        return True
    if kind == NUM:
        return is_num(v)
    if kind == OPT:
        return v is None or is_num(v)
    if kind == BOOL:
        return isinstance(v, bool)
    if kind == STR:
        return isinstance(v, str)
    if kind == DICT:
        return isinstance(v, dict)
    if kind == HEX64:
        return isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) is not None
    raise ValueError(kind)


def schema(doc, which, legacy):
    """What a result must carry, conditionally, checked on this file alone.

    Two results that share a defect agree with each other, so agreement proves
    nothing about a field both files lack or both corrupt. Everything a result
    must contain is therefore checked here, per file: presence, type, and for
    every series its length and that each element is a number.
    """
    out = []

    def fields(node, spec, path):
        if not isinstance(node, dict):
            out.append(f'{path}: expected an object in {which}, got {type(node).__name__}')
            return
        for key, kind in spec.items():
            if key not in node:
                out.append(f'{path}.{key}: missing in {which}')
            elif not kind_ok(node[key], kind):
                out.append(f'{path}.{key}: expected {kind} in {which}, got {node[key]!r:.60}')

    def need(node, key, path, kind=None, length=None):
        if not isinstance(node, dict) or key not in node:
            out.append(f'{path}.{key}: missing in {which}')
            return None
        v = node[key]
        if kind == 'list':
            if not isinstance(v, list):
                out.append(f'{path}.{key}: expected a series in {which}, got {type(v).__name__}')
                return v
            if length is not None and len(v) != length:
                what = 'empty' if not v else f'length {len(v)}'
                out.append(f'{path}.{key}: {what} in {which}, expected {length}')
            bad = [i for i, x in enumerate(v) if not is_num(x)]
            if bad:
                out.append(f'{path}.{key}: {len(bad)} entr(ies) not a number in {which}, '
                           f'first at [{bad[0]}] ({v[bad[0]]!r:.40})')
        elif kind is not None and not kind_ok(v, kind):
            out.append(f'{path}.{key}: expected {kind} in {which}, got {v!r:.60}')
        return v

    strict = not legacy
    for key in ('demand', 'generator', 'flex', 'p2x', 'solver') + (('system', 'provenance') if strict else ()):
        if key not in doc:
            out.append(f'{key}: missing in {which}')
    if out:
        return out

    solver = doc['solver']
    fields(solver, SOLVER, 'solver')
    if strict:
        need(solver, 'stat_status', 'solver', STR)
        fields(doc['provenance'], PROVENANCE, 'provenance')
        # Added with case-relative profile paths; optional so that results
        # written before them still validate, but checked when present.
        pv = doc['provenance'] if isinstance(doc['provenance'], dict) else {}
        if 'profile_resolution' in pv:
            fields(pv['profile_resolution'], {'mode': STR, 'base': ANY}, 'provenance.profile_resolution')
            if isinstance(pv['profile_resolution'], dict) and \
                    pv['profile_resolution'].get('mode') not in ('input-directory', 'explicit', 'none'):
                out.append(f"provenance.profile_resolution.mode: unknown value in {which}")
        if 'profile_files' in pv:
            if not isinstance(pv['profile_files'], dict):
                out.append(f'provenance.profile_files: expected object in {which}')
            else:
                for ref, entry in pv['profile_files'].items():
                    fields(entry, {'resolved': STR, 'sha256': HEX64}, f'provenance.profile_files[{ref}]')
    if solver.get('stat_succ') != 1:
        return out                        # a failure-shaped file carries no results

    H = doc.get('provenance', {}).get('hours') if isinstance(doc.get('provenance'), dict) else None
    if not is_num(H):
        e = doc['demand'].get('e', {})
        H = len(e.get('output_ns', [])) or None

    for g in doc['generator']:
        p = f"generator[{g.get('iden')}]"
        need(g, 'c_prod', p, NUM)
        kind = need(g, 'type', p, STR)
        need(g, 'e_prod', p, 'list', H)
        for k in ('a', 'b'):
            v = need(g, k, p, NUM)
            if kind == 'elec + ther' and is_num(v) and not v > 0:
                out.append(f'{p}.{k}: must be positive on a thermal unit in {which}, got {v}')
        need(g, 'h_prod', p, 'list', H if kind == 'elec + ther' else 0)
        if strict:
            fields(need(g, 'availability', p, DICT), AVAILABILITY, p + '.availability')

    for f in doc['flex']:
        p = f"flex[{f.get('iden')}]"
        need(f, 'c_strg', p, NUM)
        for k in ('e_char', 'e_disc', 'e_strg'):
            need(f, k, p, 'list', H)
        if (f.get('inflow_total', 0) or 0) > 0:
            need(f, 'e_spil', p, 'list', H)

    for x in doc['p2x']:
        p = f"p2x[{x.get('iden')}]"
        for k in ('c_prod', 'c_strg'):
            need(x, k, p, NUM)
        for k in ('x_prod', 'x_supp', 'x_strg'):
            need(x, k, p, 'list', H)
        sp = need(x, 'shadow_prices', p, DICT)
        thermal = x.get('type') == 'elec + ther'
        if isinstance(sp, dict):
            need(sp, 'demand_match', p + '.shadow_prices', 'list', H if thermal else 0)
        if strict:
            fields(need(x, 'availability', p, DICT), AVAILABILITY, p + '.availability')
            need(x, 'heat_surplus', p, 'list', H if thermal else 0)

    demands = [('demand.e', doc['demand'].get('e', {}))] + \
        [(f"demand.x[{d.get('iden')}]", d) for d in doc['demand'].get('x', [])]
    for p, d in demands:
        if not (d.get('total', 0) or 0) > 0:
            continue
        need(d, 'output_ns', p, 'list', H)
        sp = need(d, 'shadow_prices', p, DICT)
        if isinstance(sp, dict):
            need(sp, 'demand_match', p + '.shadow_prices', 'list', H)
            if strict:
                need(sp, 'demand_marginal', p + '.shadow_prices', 'list', H)
        fields(need(d, 'kpis', p, DICT), KPIS, p + '.kpis')
        if strict:
            fields(need(d, 'accounts', p, DICT), ACCOUNTS, p + '.accounts')
            need(d, 'surplus', p, 'list', H)

    opts = doc['provenance'].get('options', {}) if strict and isinstance(doc['provenance'], dict) else {}
    e_sp = doc['demand'].get('e', {}).get('shadow_prices', {})
    for opt, key in (('carbon-constraint', 'carbon_cap'), ('non-served-power-constraint', 'reliability_cap')):
        if opt in opts:
            need(e_sp, key, 'demand.e.shadow_prices', NUM)
            fields(need(e_sp, key + '_detail', 'demand.e.shadow_prices', DICT), CAP_DETAIL,
                   'demand.e.shadow_prices.' + key + '_detail')

    if strict:
        sy = doc['system']
        fields(sy, SYSTEM, 'system')
        if not isinstance(sy, dict):
            return out
        if isinstance(sy.get('allocated'), dict):
            fields(sy['allocated'], SHARE_BLOCK, 'system.allocated')
        if isinstance(sy.get('unallocated'), dict):
            fields(sy['unallocated'], UNALLOCATED, 'system.unallocated')
        if isinstance(sy.get('surplus'), dict):
            fields(sy['surplus'], SURPLUS, 'system.surplus')
            for k in ('products', 'unassigned_product_supply'):
                for name, v in (sy['surplus'].get(k) or {}).items():
                    if not is_num(v):
                        out.append(f'system.surplus.{k}.{name}: expected number in {which}, got {v!r:.40}')
        checks = sy.get('checks')
        if isinstance(checks, dict):
            # the checks every optimal result carries, and those its content implies
            required = ['electricity_balance', 'shortfall_bounds', 'output_reconciliation',
                        'cost_reconciliation', 'emissions_reconciliation', 'objective_reconciliation']
            if sy.get('allocation_defined') is True:
                required.append('allocated_cost_reconciliation')
            if doc['flex'] or doc['p2x']:
                required.append('storage_balance')
            if any(g.get('type') == 'elec + ther' for g in doc['generator']):
                required.append('heat_balance')
            if any((d.get('total', 0) or 0) > 0 for d in doc['demand'].get('x', [])):
                required.append('product_balance')
            required += [key for opt, key in (('carbon-constraint', 'carbon_cap'),
                                              ('non-served-power-constraint', 'reliability_cap'))
                         if opt in opts]
            for name in required:
                if name not in checks:
                    out.append(f'system.checks.{name}: missing in {which}')
            for name, c in checks.items():
                fields(c, CHECK, f'system.checks.{name}')
            if isinstance(sy.get('accounting_ok'), bool) and all(isinstance(c, dict) for c in checks.values()):
                if sy['accounting_ok'] != all(c.get('ok') is True for c in checks.values()):
                    out.append(f'system.accounting_ok: disagrees with system.checks in {which}')
    return out


# --- the two files together -----------------------------------------------------

class Comparison:

    def __init__(self, legacy=False, provenance=False):
        self.legacy = legacy
        self.excluded = dict(ALWAYS_EXCLUDED)
        if not provenance:
            self.excluded.update(PROVENANCE_EXCLUDED)
        self.out = []
        self.not_compared = set()

    def diff(self, path, message):
        self.out.append(f'  {path}: {message}')

    def excluded_path(self, path):
        return any(path == p or path.startswith(p + '.') for p in self.excluded)

    def entities(self, a, b, path):
        """Match a list of entities by 'iden', refusing duplicates first."""
        maps = []
        for items, which in ((a, 'new'), (b, 'old')):
            m, dup = {}, []
            for n, item in enumerate(items):
                key = item.get('iden') if isinstance(item, dict) else None
                if key is None:
                    self.diff(f'{path}[{n}]', f"entry without 'iden' in {which}")
                    continue
                if key in m:
                    dup.append(key)
                m[key] = item
            for key in sorted(set(dup)):
                self.diff(path, f"duplicate identifier '{key}' in {which}; entries cannot be matched")
            maps.append((m, set(dup)))
        (ma, da), (mb, db) = maps
        if set(ma) != set(mb):
            what = 'commodity' if path == 'demand.x' else 'entity'
            self.diff(path, f'{what} sets differ — only in new: {sorted(set(ma) - set(mb)) or "-"}; '
                            f'only in old: {sorted(set(mb) - set(ma)) or "-"}')
        for key in sorted(set(ma) & set(mb)):
            if key in da or key in db:
                continue
            self.node(ma[key], mb[key], f'{path}[{key}]')

    def series(self, a, b, path):
        bad = []
        worst = None
        for i, (x, y) in enumerate(zip(a, b)):
            if not (is_num(x) and is_num(y)):
                if x != y:
                    bad.append(i)
                continue
            if not (math.isfinite(x) and math.isfinite(y)):
                if not (x == y or (math.isnan(x) and math.isnan(y))):
                    bad.append(i)
                continue          # non-finite values are reported by the scan
            d = abs(x - y)
            if d > ATOL + RTOL * abs(y):
                bad.append(i)
                if worst is None or d > worst[0]:
                    worst = (d, i, x, y)
        if bad:
            detail = f'; largest |d|={worst[0]:.6g} at [{worst[1]}] ({worst[2]:.10g} vs {worst[3]:.10g})' \
                if worst else ''
            self.diff(path, f'{len(bad)} of {len(a)} value(s) differ, first at [{bad[0]}]{detail}')

    def node(self, a, b, path):
        if self.excluded_path(path):
            return
        if self.legacy:
            a, b = legacy_placeholder(a), legacy_placeholder(b)
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                sub = f'{path}.{k}' if path else k
                if self.excluded_path(sub):
                    continue
                if k not in b and k in a and self.legacy and LEGACY_ABSENT.match(sub):
                    self.not_compared.add(generic(sub))
                    continue
                if k not in a:
                    self.diff(sub, 'absent in new')
                elif k not in b:
                    self.diff(sub, 'absent in old')
                else:
                    if sub in ENTITY_LISTS and isinstance(a[k], list) and isinstance(b[k], list):
                        self.entities(a[k], b[k], sub)
                    else:
                        self.node(a[k], b[k], sub)
            return
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                self.diff(path, f'length {len(a)} vs {len(b)}')
                return
            if all(is_num(v) or v is None for v in a + b) and a:
                self.series(a, b, path)
                return
            for i, (x, y) in enumerate(zip(a, b)):
                self.node(x, y, f'{path}[{i}]')
            return
        if is_num(a) and is_num(b):
            if not (math.isfinite(a) and math.isfinite(b)):
                return            # reported by the scan
            if abs(a - b) > ATOL + RTOL * abs(b):
                self.diff(path, f'{a!r} vs {b!r}  (d={a - b:.6g})')
            return
        if type(a) is not type(b) and not (is_num(a) and is_num(b)):
            self.diff(path, f'{a!r} vs {b!r}   [TYPE: {type(a).__name__} vs {type(b).__name__}]')
            return
        if a != b:
            self.diff(path, f'{a!r} vs {b!r}')


def legacy_placeholder(v):
    # inactive commodities were written as [-1, -1] before; now -1
    if isinstance(v, list) and len(v) == 2 and all(is_num(x) and x == -1 for x in v):
        return -1
    return v


def main(argv):
    flags = [a for a in argv[1:] if a.startswith('--')]
    files = [a for a in argv[1:] if not a.startswith('--')]
    unknown = set(flags) - {'--legacy', '--provenance'}
    if len(files) != 2 or unknown:
        print(__doc__)
        return 2
    legacy, provenance = '--legacy' in flags, '--provenance' in flags
    pnew, pold = files
    try:
        new, old = load(pnew), load(pold)
    except (OSError, ValueError) as e:
        print(f'ERROR: {e}')
        return 2

    cmp = Comparison(legacy=legacy, provenance=provenance)
    problems = []
    for doc, which, relaxed in ((new, 'new', False), (old, 'old', legacy)):
        problems += [f'  {m}' for m in schema(doc, which, relaxed)]
        found = []
        non_finite(doc, '', found)
        problems += [f'  {m} in {which}' for m in found]
    cmp.node(new, old, '')
    lines = problems + cmp.out

    print(f"{'IDENTICAL' if not lines else 'DIFFERENCES'}: {pnew.split('/')[-1]}"
          f"{'  [legacy baseline]' if legacy else ''}")
    for line in lines:
        print(line)
    print('Excluded: ' + '; '.join(f'{k} ({v})' for k, v in cmp.excluded.items()))
    if cmp.not_compared:
        print('NOT COMPARED (absent from the legacy baseline): ' + ', '.join(sorted(cmp.not_compared)))
    return 0 if not lines else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
