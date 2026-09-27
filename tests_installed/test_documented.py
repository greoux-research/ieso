"""The documented examples work against the installed package.

Code blocks in README.md, docs/ieso-api.md and docs/ieso-setup-guide.md that are preceded
by the line '<!-- tested -->' are run here, from a directory holding a copy of
examples/: Python blocks as scripts, shell blocks line by line (each 'ieso ...'
or 'python -m ieso ...' command must exit 0).
"""

import os
import re
import shlex
import shutil
import subprocess
import sys

import pytest

from conftest import BUNDLE, EXAMPLES, console

DOCS = [os.path.join(BUNDLE, 'README.md')] + [os.path.join(BUNDLE, 'docs', n) for n in ('ieso-api.md', 'ieso-setup-guide.md')]
BLOCK = re.compile(r'^<!-- tested -->\s*\n```(\w+)\n(.*?)^```', re.M | re.S)


def blocks():
    found = []
    for doc in DOCS:
        with open(doc, encoding='utf-8') as f:
            text = f.read()
        for n, m in enumerate(BLOCK.finditer(text)):
            found.append((os.path.basename(doc) + '#' + str(n), m.group(1), m.group(2)))
    return found


BLOCKS = blocks()


def test_the_docs_have_tested_examples():
    kinds = {k for _, k, _ in BLOCKS}
    assert {'python', 'bash'} <= kinds, BLOCKS


@pytest.fixture
def workdir(tmp_path):
    shutil.copytree(EXAMPLES, str(tmp_path / 'examples'))
    return tmp_path


@pytest.mark.parametrize('name, kind, code', BLOCKS, ids=[b[0] for b in BLOCKS])
def test_documented_example_runs(workdir, name, kind, code):
    if kind == 'python':
        out = subprocess.run([sys.executable, '-c', code], cwd=str(workdir), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, timeout=900)
        assert out.returncode == 0, out.stdout + out.stderr
        return
    assert kind == 'bash'
    ran = 0
    for line in code.splitlines():
        line = line.split(' #')[0].strip()
        if not line or line.startswith('#'):
            continue
        args = shlex.split(line)
        if args[0] == 'ieso':
            args[0] = console()
        elif args[:3] == ['python', '-m', 'ieso'] or args[:3] == ['python3', '-m', 'ieso']:
            args = [sys.executable, '-m', 'ieso'] + args[3:]
        else:
            pytest.fail('a tested shell block may only run ieso commands: ' + line)
        out = subprocess.run(args, cwd=str(workdir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             timeout=900)
        assert out.returncode == 0, line + '\n' + out.stdout + out.stderr
        ran += 1
    assert ran
