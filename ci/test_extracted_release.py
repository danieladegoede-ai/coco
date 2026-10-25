"""Follow the manual from the ZIP, outside the checkout; verify all payload hashes."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--platform',choices=('windows','linux','macos'),required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    evidence={'archive_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),'platform':a.platform}
    with tempfile.TemporaryDirectory(prefix='Group 2 extracted ') as directory:
        with zipfile.ZipFile(a.archive) as z:
            if z.testzip() is not None:raise ValueError('Corrupt archive')
            for name in z.namelist():
                if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe archive path')
            z.extractall(directory)
        work=Path(directory)/'group-2';manifest=json.loads((work/'manifest.json').read_text())
        for name,entry in manifest['files'].items():
            if hashlib.sha256((work/name).read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Extracted payload hash mismatch')
        exe=work/('group-2.exe' if a.platform=='windows' else 'macos/group-2' if a.platform=='macos' else 'group-2')
        exe.chmod(0o755)
        good=subprocess.run([str(exe)],cwd=work,capture_output=True,text=True,encoding='utf-8',timeout=60)
        if good.returncode or good.stdout or good.stderr:raise AssertionError(good)
        compiler=shutil.which('g++') or shutil.which('c++') or shutil.which('clang++')
        if not compiler:raise RuntimeError('Manual demonstration requires a C++ toolchain')
        app=work/('program.exe' if os.name=='nt' else 'program')
        compiled=subprocess.run([compiler,'-std=c++17',str(work/'program.cpp'),'-o',str(app)],cwd=work,capture_output=True,text=True,timeout=60)
        if compiled.returncode:raise AssertionError(compiled.stderr)
        result=subprocess.run([str(app)],cwd=work,capture_output=True,text=True,timeout=10)
        if result.returncode or result.stdout!='result:3:4' or result.stderr:raise AssertionError(result)
        source_bytes=(work/'SPL.txt').read_bytes()
        bad=subprocess.run([str(exe),str(work/'examples/invalid-names.spl')],cwd=work,capture_output=True,text=True,encoding='utf-8',timeout=60)
        if bad.returncode!=7 or 'NAME-UNDECLARED-VARIABLE' not in bad.stderr or (work/'program.cpp').exists() or (work/'tree.xml').exists():raise AssertionError(bad)
        if source_bytes!=(work/'SPL.txt').read_bytes():raise AssertionError('Source changed')
        evidence.update(passed=True,default_status=good.returncode,native_target_status=result.returncode,stdout=result.stdout,invalid_status=bad.returncode,payload_hashes_verified=True)
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
