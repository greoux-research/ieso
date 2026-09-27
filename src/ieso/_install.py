#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

"""Where this copy of IESO lives: its version, its files, its checkout (if
any) and its thermodynamics executable.

Nothing here reads outside the package's own directory and its distribution
metadata, and nothing is written, downloaded or compiled. The version comes
from the installed distribution's metadata, which pyproject.toml sets (the
single authoritative version); a source tree that is not installed reads
pyproject.toml itself.
"""

import os
import sys
from importlib import metadata, resources
from typing import Any, Dict, Optional

DISTRIBUTION = 'ieso'

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
"""The directory of the ieso package that is running (site-packages/ieso, or src/ieso)."""

THERMO_NAME = 'ieso-thermo.exe' if sys.platform == 'win32' else 'ieso-thermo'
"""The thermodynamics executable's file name on this platform."""


def packaged_thermo() -> str:
    """The absolute path of the thermodynamics executable installed with the
    package, whether or not it exists; never looked up in the working
    directory or a repository.

    A wheel installs it beside the modules, at ieso/_bin/, found through the
    package's resources. An editable install keeps the modules in the source
    tree and the built executable in site-packages; there it is the file the
    distribution records as ieso/_bin/<name> (its RECORD), and only when the
    distribution is an editable install of the running checkout.
    """
    beside = os.path.abspath(str(resources.files('ieso').joinpath('_bin', THERMO_NAME)))
    if os.path.isfile(beside):
        return beside
    root = checkout_root()
    dist = _distribution()
    if root is not None and dist is not None and _editable_of(dist, root):
        wanted = '/'.join(('ieso', '_bin', THERMO_NAME))
        for entry in dist.files or ():
            if str(entry).replace(os.sep, '/') == wanted:
                return os.path.abspath(str(dist.locate_file(entry)))
    return beside


def checkout_root() -> Optional[str]:
    """The source checkout this package is running from -- the directory
    holding pyproject.toml above src/ieso -- or None for an installed wheel."""
    src = os.path.dirname(PACKAGE_DIR)
    root = os.path.dirname(src)
    if os.path.basename(PACKAGE_DIR) == 'ieso' and os.path.basename(src) == 'src' \
            and os.path.isfile(os.path.join(root, 'pyproject.toml')):
        return root
    return None


def _distribution() -> Optional[metadata.Distribution]:
    try:
        return metadata.distribution(DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return None


def _same(a: str, b: str) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def installation() -> Dict[str, Any]:
    """How the running package was installed.

    Returns
    -------
    dict
        ``kind``: 'wheel' (an installed distribution whose files are the
        running ones), 'editable' (an editable install of the running
        checkout), 'source' (a checkout on the path but not installed) or
        'unknown'; ``version``; ``package_dir``; ``checkout`` (the source
        checkout's root, or None).
    """
    root = checkout_root()
    dist = _distribution()
    kind = 'unknown'
    version = None
    if dist is not None:
        installed = dist.locate_file(os.path.join('ieso', '__init__.py'))
        if _same(str(installed), os.path.join(PACKAGE_DIR, '__init__.py')):
            kind, version = 'wheel', dist.version
        elif root is not None and _editable_of(dist, root):
            kind, version = 'editable', dist.version
    if kind == 'unknown' and root is not None:
        kind, version = 'source', _pyproject_version(root)
    return {'kind': kind, 'version': version, 'package_dir': PACKAGE_DIR, 'checkout': root}


def _editable_of(dist: metadata.Distribution, root: str) -> bool:
    # PEP 610: an editable install records the project directory it points to.
    import json
    from urllib.parse import urlparse
    from urllib.request import url2pathname
    text = dist.read_text('direct_url.json')
    if not text:
        return False
    info = json.loads(text)
    if not info.get('dir_info', {}).get('editable'):
        return False
    url = urlparse(info.get('url', ''))
    # url2pathname turns '/C:/dir' into 'C:\\dir' on Windows and unquotes.
    return url.scheme == 'file' and _same(url2pathname(url.path), root)


def _pyproject_version(root: str) -> Optional[str]:
    try:
        import tomllib
        with open(os.path.join(root, 'pyproject.toml'), 'rb') as f:
            return str(tomllib.load(f)['project']['version'])
    except (ImportError, OSError, KeyError, ValueError):
        return None


def version() -> str:
    """The version of the running package ('unknown' if it cannot be told)."""
    return installation()['version'] or 'unknown'
