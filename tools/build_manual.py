"""Compile the LaTeX manual twice; retain PDF and reproducible source metadata."""
from __future__ import annotations
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main() -> int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'output/pdf');p.add_argument('--engine',help='pdflatex or tectonic executable');a=p.parse_args()
 engine=a.engine or shutil.which('pdflatex') or shutil.which('tectonic')
 if not engine:p.error('Install pdflatex (texlive-latex-extra) or supply --engine /path/to/tectonic')
 engine=str(Path(engine).resolve());commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='group2 latex ') as directory:
  work=Path(directory);shutil.copy2(ROOT/'release/group-2.tex',work/'group-2.tex')
  (work/'build-info.tex').write_text('\\newcommand{\\SourceCommit}{'+commit+'}\n')
  if 'tectonic' in Path(engine).name:
   command=[engine,'--keep-logs','--keep-intermediates','group-2.tex']
   subprocess.run(command,cwd=work,check=True)
  else:
   command=[engine,'-interaction=nonstopmode','-halt-on-error','group-2.tex']
   for _ in range(2):subprocess.run(command,cwd=work,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  log=(work/'group-2.log').read_text(errors='replace')
  if 'Overfull \\hbox' in log or 'Overfull \\vbox' in log:raise RuntimeError('LaTeX overfull layout; inspect the manual before delivery')
  shutil.copy2(work/'group-2.pdf',output/'group-2.pdf');(output/'latex.log').write_text(log)
 text=subprocess.check_output(['pdftotext',str(output/'group-2.pdf'),'-'],text=True)
 for required in ('Declaration 1: submission category','Declaration 2: complete ZIP contents','result:3:4','program.cpp','u20598425','u20620111','u21434019','u21448842'):
  if required not in text:raise RuntimeError(f'Manual missing expected text: {required}')
 info=subprocess.check_output(['pdfinfo',str(output/'group-2.pdf')],text=True)
 pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
 if pages!=5:raise RuntimeError(f'Expected five designed pages, got {pages}')
 (output/'manual-manifest.json').write_text(json.dumps({'source_commit':commit,'pages':pages,'personal_signatures':0,'submission_ready':False,'engine':Path(engine).name},indent=2)+'\n')
 print(f'Created five-page LaTeX manual: {output/"group-2.pdf"}; personal signatures intentionally blank')
 return 0


if __name__=='__main__':raise SystemExit(main())
