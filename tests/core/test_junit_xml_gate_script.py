"""LEAD A3: assert_pytest_junit_xml_gate.py parses junit and exits with expected code."""

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "ci" / "assert_pytest_junit_xml_gate.py"


def _run_gate(xml_content: str, tmp_path: Path) -> int:
    p = tmp_path / "report.xml"
    p.write_text(xml_content, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(p)],
        check=False,
        capture_output=True,
        text=True,
    ).returncode


def test_junit_gate_passes_clean_report(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="2" failures="0" errors="0" skipped="0"></testsuite>
</testsuites>
"""
    assert _run_gate(xml, tmp_path) == 0


def test_junit_gate_fails_on_skipped(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="2" failures="0" errors="0" skipped="1"></testsuite>
</testsuites>
"""
    assert _run_gate(xml, tmp_path) == 1


def test_junit_gate_fails_on_zero_passed(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="0" failures="0" errors="0" skipped="0"></testsuite>
</testsuites>
"""
    assert _run_gate(xml, tmp_path) == 1
