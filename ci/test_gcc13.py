"""A34 target compatibility gate, using both GNU driver commands."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.test_generated_target import run_manifest
from tools.build_native import binary_identity

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--executable',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 if not shutil.which('g++-13') or not shutil.which('gcc-13'):p.error('Both GNU 13 drivers must be installed')
 executable=a.executable.resolve();digest=hashlib.sha256(executable.read_bytes()).hexdigest()
 if binary_identity(executable)!=('linux','x86_64'):p.error('GNU 13 gate requires the release Linux x64 executable')
 result={}
 for name,compiler in (('g++13',shutil.which('g++-13')),('gcc13',str(ROOT/'ci/gcc_cpp.py'))):
  reports,summary=run_manifest(ROOT/'tests/fixtures/codegen/acceptance/cases.json',compiler_command=[str(executable)],target_compiler=compiler,timeout=60)
  driver=shutil.which('g++-13' if name=='g++13' else 'gcc-13')
  version=subprocess.check_output([driver,'--version'],text=True).splitlines()[0]
  result[name]={'summary':summary,'reports':[r.to_json() for r in reports],
                'executable_sha256':digest,'target_compiler_version':version}
 unchanged=hashlib.sha256(executable.read_bytes()).hexdigest()==digest
 for section in result.values():section['unchanged_binary']=unchanged
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n')
 return 0 if unchanged and all(all(r['passed'] for r in section['reports']) for section in result.values()) else 1
if __name__=='__main__':raise SystemExit(main())
