"""Run every documented SPL edge case against a packaged native executable."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tests.integration.test_edge_corpus import Edge, edge_corpus  # noqa: E402


def check_case(executable: Path, case: Edge) -> str | None:
    """Return a failure description, or None when the case passes."""
    with tempfile.TemporaryDirectory() as directory:
        workdir = Path(directory)
        (workdir / "SPL.txt").write_bytes(case.source)
        output = workdir / "tree.xml"
        if not case.accepts:
            output.write_bytes(b"stale output from a prior run")

        try:
            result = subprocess.run(
                [str(executable)],
                cwd=workdir,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return str(error)

        stderr = result.stderr.decode("utf-8", errors="replace")
        if case.accepts:
            if result.returncode != 0:
                return f"expected exit 0, got {result.returncode}: {stderr.strip()}"
            if not output.is_file():
                return "successful run did not create tree.xml"
            try:
                root = ET.parse(output).getroot()
            except ET.ParseError as error:
                return f"tree.xml is malformed: {error}"
            if root.tag != "syntax_tree":
                return f"unexpected XML root: {root.tag}"
            leaves = [entry.findtext("contents") for entry in root if entry.tag == "leaf"]
            if leaves != case.source.decode("ascii").split():
                return "XML leaf contents do not match the input tokens"
            return None

        if result.returncode == 0:
            return "invalid SPL.txt exited with status 0"
        if output.exists():
            return "invalid SPL.txt left stale tree.xml"
        if b"Traceback" in result.stderr:
            return "diagnostic contains a Python traceback"
        return None


def check_explicit_input_path(executable: Path) -> str | None:
    """Verify the documented `group-2.exe SPL.txt` form works."""
    with tempfile.TemporaryDirectory() as directory:
        workdir = Path(directory)
        (workdir / "SPL.txt").write_bytes(b": : ")
        try:
            result = subprocess.run(
                [str(executable), "SPL.txt"],
                cwd=workdir,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return str(error)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            return f"explicit SPL.txt path exited {result.returncode}: {stderr}"
        output = workdir / "tree.xml"
        if not output.is_file():
            return "explicit SPL.txt path did not create tree.xml"
        try:
            if ET.parse(output).getroot().tag != "syntax_tree":
                return "explicit SPL.txt path produced an unexpected XML root"
        except ET.ParseError as error:
            return f"explicit SPL.txt path produced malformed XML: {error}"
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file():
        parser.error(f"executable not found: {executable}")

    cases = edge_corpus()
    if len(cases) < 300:
        raise AssertionError(f"edge corpus unexpectedly has only {len(cases)} cases")
    failures = 0
    for index, case in enumerate(cases, 1):
        reason = check_case(executable, case)
        if reason is not None:
            failures += 1
            print(f"FAIL {index}/{len(cases)} {case.name}: {reason}")
            print(f"  SPL.txt bytes: {case.source!r}")
        elif index % 50 == 0 or index == len(cases):
            print(f"PASS {index}/{len(cases)} SPL.txt edge cases")
    explicit_error = check_explicit_input_path(executable)
    if explicit_error is None:
        print("PASS explicit SPL.txt argument")
    else:
        failures += 1
        print(f"FAIL explicit SPL.txt argument: {explicit_error}")
    print(f"{len(cases) + 1 - failures}/{len(cases) + 1} packaged cases passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
