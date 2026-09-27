#!/usr/bin/env python3
"""Inspect the thermodynamics executable inside an IES Optimiser wheel, or installed.

    python tools/inspect_native.py WHEEL_OR_DIR [--copy-to DIR] [--report FILE]
    python tools/inspect_native.py --installed [--report FILE]

Wheel repair tools (auditwheel, delocate, delvewheel) are written for Python
extension modules; this checks the standalone executable itself, against the
wheel's own platform tag:

* the wheel is py3-none-<platform> (never 'any'), holds exactly one
  ies_optimiser/_bin/ies-optimiser-thermo[.exe], executable (mode 755) on POSIX;
* Linux (ELF): machine matches the tag; every DT_NEEDED library is one the
  manylinux policy allows (auditwheel's policy data) and every versioned
  symbol requirement (GLIBC, GLIBCXX, CXXABI, GCC) is within the tag's policy;
* macOS (Mach-O): architecture matches the tag; the minimum OS (LC_BUILD_VERSION
  or LC_VERSION_MIN_MACOSX) is not above the tag's; only libSystem and the
  system libc++ are linked;
* Windows (PE): AMD64 for win_amd64; no C++ runtime DLL (MSVCP*, VCRUNTIME*,
  which a clean system may lack) -- only system DLLs;
* on a matching host, the executable runs: '--limits' and one coefficient
  calculation succeed.

--local-build is for a wheel built on the host from the sdist, to test that
the sdist builds and works: such a wheel carries the plain linux_<arch> tag
and is not distributable, so on Linux the manylinux policy checks are replaced
by a check that the tag is linux_<arch> and the machine matches; dependencies
are still reported, and the executable must still run. Distributable wheels
are always checked without it.

Exit status 0 when every check passes. --copy-to copies the wheel afterwards
(for use as cibuildwheel's repair command). Needs pyelftools (ELF), pefile
(PE), auditwheel (Linux policy data), and otool/lipo (macOS) as applicable.
"""

import argparse
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

EXE_NAMES = ('ies_optimiser/_bin/ies-optimiser-thermo', 'ies_optimiser/_bin/ies-optimiser-thermo.exe')
SMOKE = [['--limits', '290', '70', '0.05'], ['290', '70', '0.05', '80']]


class Report:
    def __init__(self):
        self.data = {'checks': [], 'ok': True}

    def check(self, name, ok, detail=''):
        self.data['checks'].append({'check': name, 'ok': bool(ok), 'detail': detail})
        if not ok:
            self.data['ok'] = False
        print(('PASS ' if ok else 'FAIL ') + name + ('' if not detail else ': ' + str(detail)))

    def note(self, key, value):
        self.data[key] = value
        print('     ' + key + ': ' + (json.dumps(value) if not isinstance(value, str) else value))


# --- ELF (Linux) --------------------------------------------------------------------------

def _policy(tag):
    import importlib.resources as resources
    m = re.match(r'manylinux_(\d+)_(\d+)_(\w+)$', tag)
    if not m:
        return None, None
    name = 'manylinux_' + m.group(1) + '_' + m.group(2)
    policies = json.loads((resources.files('auditwheel.policy') / 'manylinux-policy.json').read_text())
    for p in policies:
        if p['name'] == name:
            return p, m.group(3)
    return None, m.group(3)


def inspect_elf(path, tags, report, local_build=False):
    from elftools.elf.elffile import ELFFile
    from elftools.elf.dynamic import DynamicSection
    from elftools.elf.gnuversions import GNUVerNeedSection
    with open(path, 'rb') as f:
        elf = ELFFile(f)
        machine = elf['e_machine']
        needed, versions = [], set()
        for section in elf.iter_sections():
            if isinstance(section, DynamicSection):
                needed += [t.needed for t in section.iter_tags() if t.entry.d_tag == 'DT_NEEDED']
            if isinstance(section, GNUVerNeedSection):
                for _, auxs in section.iter_versions():
                    versions.update(a.name for a in auxs)
    report.note('elf_machine', machine)
    report.note('dt_needed', sorted(needed))
    report.note('symbol_versions', sorted(versions))
    if local_build:
        plain = [t for t in tags if re.match(r'linux_\w+$', t)]
        report.check('local build: plain linux_<arch> tag (not distributable)', bool(plain) and plain == tags, tags)
        for tag in plain:
            expected = {'x86_64': 'EM_X86_64', 'aarch64': 'EM_AARCH64'}.get(tag[len('linux_'):])
            report.check(tag + ': machine', machine == expected, machine)
        return
    linux = [t for t in tags if t.startswith('manylinux_')]
    report.check('manylinux platform tag', bool(linux), tags)
    for tag in linux:
        policy, arch = _policy(tag)
        report.check(tag + ': policy known to auditwheel', policy is not None)
        if policy is None:
            continue
        expected = {'x86_64': 'EM_X86_64', 'aarch64': 'EM_AARCH64'}.get(arch)
        report.check(tag + ': machine', machine == expected, machine)
        extra = sorted(set(needed) - set(policy['lib_whitelist']))
        report.check(tag + ': libraries allowed by the policy', not extra, extra or needed)
        allowed = policy['symbol_versions'][arch]
        bad = []
        for v in sorted(versions):
            space, _, ver = v.partition('_')
            if space in allowed and ver not in allowed[space]:
                bad.append(v)
            elif space not in allowed:
                bad.append(v)
        report.check(tag + ': symbol versions within the policy', not bad, bad or 'all within')


# --- Mach-O (macOS) -------------------------------------------------------------------------

def _version(text):
    return tuple(int(x) for x in text.split('.'))


def inspect_macho(path, tags, report):
    deps = subprocess.run(['otool', '-L', path], capture_output=True, text=True, check=True).stdout
    libs = [line.strip().split(' (')[0] for line in deps.splitlines()[1:] if line.strip()]
    archs = subprocess.run(['lipo', '-archs', path], capture_output=True, text=True, check=True).stdout.split()
    loads = subprocess.run(['otool', '-l', path], capture_output=True, text=True, check=True).stdout
    minos = re.findall(r'\bminos (\d+(?:\.\d+)*)', loads) or re.findall(r'cmd LC_VERSION_MIN_MACOSX.*?\n\s*version (\S+)',
                                                                         loads, re.S)
    report.note('linked_libraries', libs)
    report.note('architectures', archs)
    report.note('minimum_os', minos)
    report.check('only system libraries (libSystem, libc++)',
                 set(libs) <= {'/usr/lib/libSystem.B.dylib', '/usr/lib/libc++.1.dylib'}, libs)
    mac = [t for t in tags if t.startswith('macosx_')]
    report.check('macosx platform tag', bool(mac), tags)
    for tag in mac:
        m = re.match(r'macosx_(\d+)_(\d+)_(\w+)$', tag)
        if not m:
            report.check(tag + ': parsed', False)
            continue
        floor, arch = (int(m.group(1)), int(m.group(2))), m.group(3)
        wanted = {'arm64': ['arm64'], 'x86_64': ['x86_64'], 'universal2': ['x86_64', 'arm64']}.get(arch)
        report.check(tag + ': architecture', wanted is not None and sorted(archs) == sorted(wanted), archs)
        report.check(tag + ': minimum OS not above the tag', bool(minos) and all(_version(v)[:2] <= floor
                                                                                   for v in minos), minos)


# --- PE (Windows) --------------------------------------------------------------------------

def inspect_pe(path, tags, report):
    import pefile
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    dlls = sorted(e.dll.decode().lower() for e in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []))
    machine = pefile.MACHINE_TYPE.get(pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine))
    report.note('imported_dlls', dlls)
    report.note('pe_machine', machine)
    runtime = [d for d in dlls if re.match(r'(msvcp|vcruntime|concrt|libstdc\+\+|libgcc|libwinpthread)', d)]
    report.check('no C++ runtime DLL (statically linked)', not runtime, runtime or dlls)
    system = [d for d in dlls if not (d in ('kernel32.dll', 'ntdll.dll', 'advapi32.dll', 'ucrtbase.dll')
                                      or d.startswith('api-ms-win-'))]
    report.check('only system DLLs', not system, system or dlls)
    report.check('win_amd64 tag and AMD64 machine', 'win_amd64' in tags and machine == 'IMAGE_FILE_MACHINE_AMD64',
                 [tags, machine])


# --- common -------------------------------------------------------------------------------

def host_matches(tags):
    system, machine = platform.system(), platform.machine().lower()
    if system == 'Linux':
        return any(t.startswith('manylinux') and t.endswith(machine) for t in tags) or \
            any(t == 'linux_' + machine for t in tags)
    if system == 'Darwin':
        return any(t.startswith('macosx') and (t.endswith(machine) or t.endswith('universal2')) for t in tags)
    if system == 'Windows':
        return 'win_amd64' in tags and machine in ('amd64', 'x86_64')
    return False


def smoke(path, report):
    for args in SMOKE:
        out = subprocess.run([path] + args, capture_output=True, text=True, timeout=30)
        report.check('runs: ' + ' '.join(args), out.returncode == 0 and len(out.stdout.split()) == 2,
                     out.stdout.strip() or out.stderr.strip())


def inspect(path, tags, report, local_build=False):
    with open(path, 'rb') as f:
        magic = f.read(4)
    if magic == b'\x7fELF':
        inspect_elf(path, tags, report, local_build)
    elif magic in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe'):
        inspect_macho(path, tags, report)
    elif magic[:2] == b'MZ':
        inspect_pe(path, tags, report)
    else:
        report.check('recognised executable format', False, magic)
        return
    if host_matches(tags):
        smoke(path, report)
    else:
        report.note('run', 'skipped: the host does not match ' + ', '.join(tags))


def wheel_of(target):
    if os.path.isdir(target):
        wheels = [os.path.join(target, n) for n in os.listdir(target) if n.endswith('.whl')]
        if len(wheels) != 1:
            raise SystemExit('expected exactly one wheel in ' + target + ', found ' + str(len(wheels)))
        return wheels[0]
    return target


def from_wheel(target, report, local_build=False):
    wheel = wheel_of(target)
    report.note('wheel', os.path.basename(wheel))
    name = os.path.basename(wheel)[:-len('.whl')]
    python, abi, plat = name.split('-')[-3:]
    tags = plat.split('.')
    report.check('py3-none platform wheel', python == 'py3' and abi == 'none' and 'any' not in tags, name)
    with zipfile.ZipFile(wheel) as z:
        exes = [i for i in z.infolist() if i.filename in EXE_NAMES]
        report.check('exactly one thermodynamics executable', len(exes) == 1, [i.filename for i in exes])
        if len(exes) != 1:
            return wheel
        info = exes[0]
        mode = info.external_attr >> 16
        windows = info.filename.endswith('.exe')
        report.check('executable named for its platform',
                     windows == any(t.startswith('win') for t in tags), info.filename)
        if not windows:
            report.check('mode 755', stat.S_IMODE(mode) == 0o755, oct(stat.S_IMODE(mode)))
        folder = tempfile.mkdtemp()
        path = z.extract(info, folder)
        os.chmod(path, 0o755)
        inspect(path, tags, report, local_build)
        shutil.rmtree(folder, ignore_errors=True)
    return wheel


def installed(report, local_build=False):
    import ies_optimiser
    from ies_optimiser import _install, fcn
    report.note('package', os.path.dirname(os.path.abspath(ies_optimiser.__file__)))
    report.note('installation', _install.installation()['kind'])
    path = fcn.Thermo_bin
    report.check('packaged executable exists', os.path.isfile(path), path)
    report.check('packaged executable is executable', os.access(path, os.X_OK), path)
    report.check('named for the platform', os.path.basename(path) == _install.THERMO_NAME, os.path.basename(path))
    from importlib import metadata
    wheel = metadata.distribution('ies-optimiser').read_text('WHEEL') or ''
    tags = [t.split('-')[-1] for t in re.findall(r'^Tag: (\S+)$', wheel, re.M)]
    report.note('wheel_tags', tags)
    if os.path.isfile(path):
        inspect(path, sorted({p for t in tags for p in t.split('.')}), report, local_build)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('target', nargs='?', help='a wheel, or a directory holding exactly one')
    ap.add_argument('--installed', action='store_true', help='inspect the ies_optimiser package installed in this Python')
    ap.add_argument('--copy-to', help='copy the wheel here when every check passes')
    ap.add_argument('--report', help='write the findings as JSON')
    ap.add_argument('--local-build', action='store_true',
                    help='a host-built wheel from the sdist (linux_<arch>), not a distributable one')
    args = ap.parse_args(argv)
    report = Report()
    report.note('host', platform.platform())
    if args.local_build:
        report.note('mode', 'local build: not checked as a distributable wheel')
    if args.installed:
        installed(report, args.local_build)
        wheel = None
    elif args.target:
        wheel = from_wheel(args.target, report, args.local_build)
    else:
        ap.error('give a wheel or --installed')
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report.data, f, indent=2)
    if not report.data['ok']:
        return 1
    if args.copy_to and wheel:
        os.makedirs(args.copy_to, exist_ok=True)
        shutil.copy2(wheel, args.copy_to)
        print('copied ' + os.path.basename(wheel) + ' to ' + args.copy_to)
    return 0


if __name__ == '__main__':
    sys.exit(main())
