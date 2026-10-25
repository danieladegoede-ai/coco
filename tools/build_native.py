"""Build one native one-file compiler on its own OS and record provenance."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def binary_identity(path: Path) -> tuple[str,str]:
    data=path.read_bytes()
    if data[:2]==b'MZ':
        offset=struct.unpack_from('<I',data,0x3c)[0]
        if data[offset:offset+4]!=b'PE\0\0':raise ValueError('Invalid PE signature')
        machine=struct.unpack_from('<H',data,offset+4)[0]
        return 'windows','x86_64' if machine==0x8664 else hex(machine)
    if data[:4]==b'\x7fELF':
        if data[4:6]!=b'\x02\x01':raise ValueError('Expected little-endian ELF64')
        machine=struct.unpack_from('<H',data,18)[0]
        return 'linux','x86_64' if machine==62 else hex(machine)
    if data[:4]==b'\xcf\xfa\xed\xfe':
        machine=struct.unpack_from('<I',data,4)[0]
        return 'macos','arm64' if machine==0x100000c else 'x86_64' if machine==0x1000007 else hex(machine)
    raise ValueError('Unrecognized native executable format')


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist'/'native')
    parser.add_argument('--allow-dirty',action='store_true',help='Development only; records dirty provenance')
    args=parser.parse_args()
    host={'Windows':'windows','Linux':'linux','Darwin':'macos'}.get(platform.system())
    if host is None:parser.error('Unsupported build OS')
    machine={'AMD64':'x86_64','aarch64':'arm64'}.get(platform.machine(),platform.machine())
    if (host,machine) not in (('windows','x86_64'),('linux','x86_64'),('macos','arm64')):
        parser.error(f'No release target configured for {host}/{machine}')
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    if dirty and not args.allow_dirty:parser.error('Build from a committed clean checkout, or use --allow-dirty for a development artifact')
    destination=args.output.resolve();destination.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-m','PyInstaller','--clean','--noconfirm','--onefile','--console','--noupx',
             '--name','group-2','--paths',str(ROOT/'src'),'--distpath',str(destination),
             '--workpath',str(ROOT/'build'/'pyinstaller'/host),'--specpath',str(ROOT/'build'/'spec'),
             str(ROOT/'packaging'/'entrypoint.py')]
    subprocess.run(command,cwd=ROOT,check=True)
    executable=destination/('group-2.exe' if host=='windows' else 'group-2')
    actual=binary_identity(executable)
    if actual!=(host,machine):raise RuntimeError(f'Native format {actual} disagrees with build host {host}/{machine}')
    record={'schema':1,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'source_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
            'dirty':dirty,'os':host,'architecture':machine,'platform':platform.platform(),'python':platform.python_version(),
            'pyinstaller':importlib.metadata.version('pyinstaller'),'build_command':command,
            'filename':executable.name,'sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'bytes':executable.stat().st_size}
    (destination/'build-manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
