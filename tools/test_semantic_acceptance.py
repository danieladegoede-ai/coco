"""Run the semantic rejection manifest against the full CLI or an external compiler."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.test_generated_target import compiler_command_for, normalize_compiler_command, run_process

DEFAULT_MANIFEST = ROOT / 'tests/fixtures/semantics/cases.json'


@dataclass(frozen=True, slots=True)
class SemanticReport:
    case_id: str
    passed: bool
    compiler_status: int | str
    stdout: str
    stderr: str
    reason: str | None
    command: list[str]
    artifact_dir: str | None = None


def location_matches(line: int, column: int, ranges: list[dict]) -> bool:
    return any((r['start']['line'], r['start']['column']) <= (line, column) <
               (r['end']['line'], r['end']['column']) for r in ranges)


def run_case(case: dict, source: str, *, compiler_command: Sequence[str] | None = None,
             timeout: float = 5, artifacts: Path | None = None) -> SemanticReport:
    if timeout <= 0:
        raise ValueError('Timeout must be positive.')
    compiler_command = normalize_compiler_command(compiler_command)
    with tempfile.TemporaryDirectory(prefix='spl-semantic-case-') as directory:
        work = Path(directory)
        input_path, target, xml = work/'input with spaces.spl', work/'program.cpp', work/'tree.xml'
        input_path.write_text(source, encoding='utf-8')
        target.write_text('stale target', encoding='utf-8')
        xml.write_text('stale XML', encoding='utf-8')
        command = compiler_command_for(input_path, target, compiler_command)
        status, stdout, stderr = run_process(command, work, timeout)
        reason = None
        if status != case['expected_status']:
            reason = f"Compiler status {status!r}; expected {case['expected_status']}."
        elif stdout or 'Traceback' in stderr:
            reason = 'Expected a silent successful stdout and traceback-free diagnostics.'
        elif not input_path.is_file() or input_path.read_text(encoding='utf-8') != source:
            reason = 'Compiler modified the source input.'
        elif case['valid']:
            if stderr or not target.is_file() or not xml.is_file():
                reason = 'Successful case did not publish both clean outputs.'
            elif target.read_text() == 'stale target' or xml.read_text() == 'stale XML':
                reason = 'Successful case retained stale output.'
        else:
            if target.exists() or xml.exists():
                reason = 'Rejected case retained stale or partial output.'
            elif f"[{case['expected_code']}]" not in stderr:
                reason = 'Diagnostic did not contain the expected error code.'
            elif case.get('expected_message') and case['expected_message'] not in stderr:
                reason = 'Required numeric conflict message was not preserved.'
            else:
                point = re.search(re.escape(str(input_path)) + r':(\d+):(\d+):', stderr)
                if point is None:
                    reason = 'Diagnostic did not retain the actual explicit filename and source position.'
                elif not location_matches(int(point[1]), int(point[2]), case['expected_locations']):
                    reason = 'Diagnostic points outside the independently selected fault range.'
        saved = None
        if reason:
            root = artifacts or ROOT/'build/semantic-failures'
            root.mkdir(parents=True, exist_ok=True)
            safe_id = re.sub(r'[^A-Za-z0-9_.-]', '_', case['id'])[:100]
            saved = Path(tempfile.mkdtemp(prefix=safe_id+'-', dir=root)).resolve()
            (saved/'input.spl').write_text(source, encoding='utf-8')
            (saved/'compiler.stdout.log').write_text(stdout, encoding='utf-8')
            (saved/'compiler.stderr.log').write_text(stderr, encoding='utf-8')
            for output in (target, xml):
                if output.is_file():
                    shutil.copyfile(output, saved/output.name)
            replay_case = {**case, 'file': 'input.spl'}
            (saved/'case.json').write_text(json.dumps({'cases': [replay_case]}, indent=2)+'\n')
            replay = [sys.executable, str(Path(__file__).resolve()), '--manifest', 'case.json',
                      '--timeout', str(timeout), '--artifacts', 'replay-artifacts']
            if compiler_command is not None:
                replay += ['--compiler-command', json.dumps(list(compiler_command))]
            (saved/'replay.json').write_text(json.dumps(replay, indent=2)+'\n')
            (saved/'reproduce.py').write_text(
                "import json, pathlib, subprocess\np = pathlib.Path(__file__).resolve().parent\n"
                "raise SystemExit(subprocess.run(json.loads((p/'replay.json').read_text()), cwd=p).returncode)\n")
        report = SemanticReport(case['id'], reason is None, status, stdout, stderr, reason,
                                command, str(saved) if saved else None)
        if saved:
            (saved/'report.json').write_text(json.dumps(asdict(report), indent=2)+'\n')
        return report


def run_manifest(manifest: Path = DEFAULT_MANIFEST, *, compiler_command: Sequence[str] | None = None,
                 timeout: float = 5, artifacts: Path | None = None) -> tuple[list[SemanticReport], dict]:
    cases = json.loads(manifest.read_text(encoding='utf-8'))['cases']
    reports = [run_case(c, (manifest.parent/c['file']).read_text(encoding='utf-8'),
                        compiler_command=compiler_command, timeout=timeout, artifacts=artifacts)
               for c in cases]
    return reports, {'runnable': len(reports), 'passed': sum(r.passed for r in reports),
                     'failed': sum(not r.passed for r in reports)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--compiler-command', help='JSON argv array; optional {input}/{target} placeholders')
    parser.add_argument('--timeout', type=float, default=5)
    parser.add_argument('--artifacts', type=Path)
    args = parser.parse_args(argv)
    try:
        command = json.loads(args.compiler_command) if args.compiler_command else None
    except json.JSONDecodeError as exc:
        parser.error(str(exc))
    if command is not None and (not isinstance(command, list) or not command or any(not isinstance(x,str) for x in command)):
        parser.error('--compiler-command must be a nonempty JSON argv array')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    reports, summary = run_manifest(args.manifest, compiler_command=command, timeout=args.timeout, artifacts=args.artifacts)
    print(json.dumps({'summary': summary, 'reports': [asdict(r) for r in reports]}, indent=2))
    return int(bool(summary['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
