#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""The IESO command line.

    ieso INPUT.json [name=value ...] [--profile-base DIR]
    ieso validate INPUT.json [name=value ...] [--profile-base DIR] [--json]
    ieso schema input|result
    ieso --help | --version

'ieso' is the console command installed with the package; 'python -m ieso'
and, in a source checkout, 'python ieso.py' run the same command line.

The first form solves, as it always has. 'validate' checks a case completely
-- structure, identifiers, references, topology, profiles (resolved and read),
hourly shortfall bounds and, for units that supply heat, the thermodynamics
(it runs the packaged executable, ieso/_bin/ieso-thermo) -- without building or solving the problem, and
writes no file. 'schema' prints the JSON Schema of the canonical input or of a
result; it needs no case and no thermodynamics executable. A first argument
that is exactly 'validate' or 'schema' selects the command; anything else is
the solve form's input file.

Relative profile paths in INPUT.json resolve against INPUT.json's own
directory. --profile-base DIR resolves them against DIR instead (a relative DIR
is taken from the current directory); it is how an older input written with
repository-relative paths is run:  ieso old.json --profile-base /path/to/ieso
It is not a model option: it does not enter the result's file name or the
model, and is recorded in the result's provenance (profile_resolution).

With --json, validate prints exactly one JSON document on stdout; everything
else (logs, diagnostics in text form) goes to stderr.

Exit status:
    0  solve: optimal and every accounting check passed (result written);
       validate: valid; schema, --help, --version: printed
    1  input, options, profiles, configuration or thermodynamics refused
       (nothing written), or the solve did not reach an optimal solution
       (result written, status inside); validate: invalid
    3  solve: optimal, but an accounting check failed (result written)
"""

import json
import logging
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from ieso import api, schemas
from ieso import fcn as u
from ieso.errors import IesoError, InputError

log = logging.getLogger('ieso')

# Recognised flags: name -> whether it takes a value.
FLAGS = {'--profile-base': True, '--json': False}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run IESO on the command line's arguments; return the exit status."""
    logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stderr)
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        log.error('Examples of a correct command line: \'ieso input.json\', '
                  '\'ieso validate input.json --json\', \'ieso schema input\' (\'ieso --help\' for more)')
        return 1
    if args[0] in ('-h', '--help') or (args[0] in ('validate', 'schema') and args[1:2] in (['-h'], ['--help'])):
        sys.stdout.write(__doc__ or '')
        return 0
    if args[0] == '--version':
        from ieso._install import version
        print('ieso ' + version())
        return 0
    if args[0] == 'schema':
        return schema(args[1:])
    if args[0] == 'validate':
        return validate(args[1:])
    return solve(args)


def solve(args: List[str]) -> int:
    """The solve form: INPUT.json [name=value ...] [--profile-base DIR]."""
    json_file = args[0]

    try:
        # Options and flags are validated before the input is read or anything
        # is solved, so a misspelt or malformed request fails at once.
        flags, option_args = split_flags(args[1:], allowed=('--profile-base',))
        opts = u.parse_options(option_args)
        profile_base = flags.get('--profile-base')
        config = u.RunConfig(profile_base=profile_base if isinstance(profile_base, str) else None)
        case = api.load_input(json_file)
        result = api.solve(case, options=opts, config=config, source=json_file)
    except IesoError as e:
        log.error('%s', e)
        return 1

    api.write_result(result, api.output_path(json_file, opts))

    # A run that did not reach an optimal solution exits 1; the file is still
    # written and its status says why. An optimal solve whose accounts fail to
    # reconcile exits 3.
    if not result.optimal:
        return 1
    return 0 if result.accounting_ok else 3


def validate(args: List[str]) -> int:
    """validate INPUT.json [name=value ...] [--profile-base DIR] [--json]."""
    as_json = '--json' in args
    json_file = args[0] if args and not args[0].startswith('--') else None
    try:
        if json_file is None:
            raise InputError('validate needs an input file: ieso validate INPUT.json [--json]',
                             entity='command line', code='command.usage', layer='configuration')
        flags, option_args = split_flags(args[1:], allowed=('--profile-base', '--json'))
        opts = u.parse_options(option_args)
    except InputError as e:
        return _report_usage(e, json_file, as_json)
    profile_base = flags.get('--profile-base')
    config = u.RunConfig(profile_base=profile_base if isinstance(profile_base, str) else None)
    report = api.validate(json_file, options=opts, config=config)

    if as_json:
        document = {'command': 'validate', 'input': json_file}
        document.update(report.to_dict())
        print(json.dumps(document, indent=2))
    else:
        for d in report.diagnostics:
            log.error('%s [%s%s]', d, d.code, '' if d.path is None else ' at ' + d.path)
        state = 'valid' if report.valid else 'invalid'
        detail = ', '.join(k + ' ' + v for k, v in report.stages.items())
        print(json_file + ': ' + state + (' (' + report.format + ' format)' if report.format else '')
              + ' -- ' + detail)
    return 0 if report.valid else 1


def _report_usage(error: InputError, json_file: Optional[str], as_json: bool) -> int:
    if as_json:
        print(json.dumps({'command': 'validate', 'input': json_file, 'valid': False, 'format': None,
                          'stages': {}, 'diagnostics': [d.to_dict() for d in error.diagnostics],
                          'removed_fields': [], 'profile_resolution': {}}, indent=2))
    else:
        for d in error.diagnostics:
            log.error('%s', d)
    return 1


def schema(args: List[str]) -> int:
    """schema input|result: print the JSON Schema on stdout."""
    if len(args) != 1 or args[0] not in schemas.FILES:
        log.error('usage: ieso schema input|result')
        return 1
    sys.stdout.write(schemas.generate(args[0]))
    return 0


def split_flags(args: Sequence[str], allowed: Sequence[str] = tuple(FLAGS)) -> Tuple[Dict[str, object], List[str]]:
    """Separate '--flag [VALUE]' / '--flag=VALUE' arguments from name=value options.

    Only the flags in `allowed` are recognised; a flag that takes a value takes
    one non-empty value, and each may be given once. Everything else is left
    for parse_options.
    """
    flags: Dict[str, object] = {}
    rest = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith('--'):
            name, eq, value = arg.partition('=')
            if name not in allowed:
                raise InputError('unknown flag \'' + name + '\' (recognised: ' + ', '.join(allowed) + ')',
                                 entity='command line', field=name, code='flag.unknown', layer='configuration')
            if not FLAGS[name]:
                if eq:
                    raise InputError('flag \'' + name + '\' takes no value', entity='command line', field=name,
                                     code='flag.value', layer='configuration')
                value = ''
            else:
                if not eq:
                    if i + 1 >= len(args):
                        raise InputError('flag \'' + name + '\' needs a value', entity='command line', field=name,
                                         code='flag.value', layer='configuration')
                    i += 1
                    value = args[i]
                if value == '':
                    raise InputError('flag \'' + name + '\' needs a value', entity='command line', field=name,
                                     code='flag.value', layer='configuration')
            if name in flags:
                raise InputError('flag \'' + name + '\' given more than once', entity='command line', field=name,
                                 code='flag.repeated', layer='configuration')
            flags[name] = value if FLAGS[name] else True
        else:
            rest.append(arg)
        i += 1
    return flags, rest
