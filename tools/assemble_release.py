"""Assemble only verified matching native artifacts; never fabricate signatures."""
from __future__ import annotations
import argparse,hashlib,json,stat,subprocess,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def sha(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_artifacts(artifacts: Path,commit: str) -> dict:
    from tests.edge5000.cases import CASES
    required={c.case_id for c in CASES}
    result={}
    for platform in ('windows','linux','macos'):
        directory=artifacts/f'native-{platform}'
        manifest=json.loads((directory/'build-manifest.json').read_text())
        filename='group-2.exe' if platform=='windows' else 'group-2'
        binary=directory/filename
        if manifest['dirty'] or manifest['source_commit']!=commit:raise ValueError('Native source provenance is dirty or mismatched')
        if manifest['os']!=platform or manifest['sha256']!=sha(binary):raise ValueError('Native platform/hash mismatch')
        acceptance=json.loads((directory/'acceptance.json').read_text())
        if not acceptance['passed'] or acceptance['executable_sha256']!=sha(binary):raise ValueError('Native acceptance evidence missing or hash mismatch')
        ids=[]
        for shard in range(4):
            path=artifacts/f'package-evidence-{platform}-{shard}'/f'package-{platform}-{shard}.json'
            report=json.loads(path.read_text())
            if not report['passed'] or report['executable_sha256']!=sha(binary):raise ValueError('Packaged edge evidence failed or binary changed')
            if report['shard_count']!=4 or report['shard_index']!=shard:raise ValueError('Unexpected shard identity')
            for case in report['results']:
                if not case['passed'] or case['skipped'] or case['run']!=1:raise ValueError('Skipped/failed edge case')
                ids.append(case['id'])
        if len(ids)!=5000 or len(set(ids))!=5000 or set(ids)!=required:raise ValueError('Packaged corpus coverage is incomplete or duplicated')
        result[platform]=manifest
    gcc=json.loads((artifacts/'gcc13-evidence/gcc13.json').read_text())
    if set(gcc)!={'g++13','gcc13'} or not all(all(c['passed'] for c in r['reports']) for r in gcc.values()):raise ValueError('GNU 13 compatibility gate did not pass')
    manual=json.loads((artifacts/'user-manual/manual-manifest.json').read_text())
    if manual['source_commit']!=commit or manual['pages']!=5:raise ValueError('Manual provenance/page count mismatch')
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifests=validate_artifacts(a.artifacts,commit)
    files={'group-2.exe':a.artifacts/'native-windows/group-2.exe',
           'group-2':a.artifacts/'native-linux/group-2',
           'macos/group-2':a.artifacts/'native-macos/group-2',
           'group-2.pdf':a.artifacts/'user-manual/group-2.pdf',
           'SPL.txt':ROOT/'release/example.spl','examples/invalid-names.spl':ROOT/'release/invalid-names.spl'}
    manifest={'schema':1,'source_commit':commit,'category':'First Class','submission_ready':False,
              'personal_signatures':0,'blockers':['Eight personal signatures: four on each declaration','Speaker verifies and uploads the final signed archive to the First Class slot only'],
              'native_builds':manifests,'files':{name:{'bytes':path.stat().st_size,'sha256':sha(path)} for name,path in files.items()},
              'package_cases_per_platform':5000,'target_compilers_validated':['g++-13','gcc-13 -x c++ ... -lstdc++']}
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
    receipt=output/'manifest.json';receipt.write_text(json.dumps(manifest,indent=2)+'\n')
    files['manifest.json']=receipt
    archive=output/'group-2-candidate.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,path in sorted(files.items()):
            info=zipfile.ZipInfo('group-2/'+name,date_time=(2026,10,25,0,0,0));info.create_system=3
            executable=name in ('group-2.exe','group-2','macos/group-2')
            info.external_attr=(stat.S_IFREG|(0o755 if executable else 0o644))<<16
            info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,path.read_bytes())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('Archive integrity test failed')
    (output/'SHA256SUMS.txt').write_text(f'{sha(archive)}  {archive.name}\n')
    (output/'REMAINING_PERSONAL_ACTIONS.txt').write_text('Unsigned release candidate. Each member must personally sign both declarations. Reassemble with the signed manual, verify the exact final ZIP, submit only in the First Class slot, and retain the portal receipt/downloaded hash. No approval or upload is fabricated.\n')
    print(f'Built {archive}; unsigned personal declarations remain a real submission gate.')
    return 0


if __name__=='__main__':raise SystemExit(main())
