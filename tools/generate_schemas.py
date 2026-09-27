#!/usr/bin/env python3
"""Write the JSON Schemas generated from IESO's public models into the package.

    python tools/generate_schemas.py            # (re)write src/ieso/data/*.schema.json
    python tools/generate_schemas.py --check    # exit 1 if a file differs

Run it with IESO installed from this checkout (pip install -e .), from any
directory. The schemas are generated, never edited by hand: change
src/ieso/models.py or src/ieso/results.py and run this again.
"""

import os
import sys

from ieso import schemas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    check = argv == ['--check']
    if argv and not check:
        print(__doc__, file=sys.stderr)
        return 1
    folder = os.path.join(ROOT, 'src', 'ieso', 'data')
    if os.path.dirname(os.path.abspath(schemas.__file__)) != os.path.join(ROOT, 'src', 'ieso'):
        print('the ieso package imported is not this checkout\'s (' + schemas.__file__ + '); install it with '
              'pip install -e ' + ROOT, file=sys.stderr)
        return 1
    stale = []
    for kind, name in schemas.FILES.items():
        path = os.path.join(folder, name)
        text = schemas.generate(kind)
        current = None
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                current = f.read()
        if check:
            if current != text:
                stale.append(name)
        elif current != text:
            os.makedirs(folder, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            print('wrote ' + os.path.relpath(path, ROOT))
        else:
            print('unchanged ' + os.path.relpath(path, ROOT))
    if stale:
        print('out of date (run python tools/generate_schemas.py): ' + ', '.join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
