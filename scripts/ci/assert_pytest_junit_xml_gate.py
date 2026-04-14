#!/usr/bin/env python3
"""
LEAD A3: fail if pytest JUnit report has skips, errors, or failures.

Usage:
  poetry run pytest -m critical_path --junitxml=reports/critical-junit.xml
  poetry run python scripts/ci/assert_pytest_junit_xml_gate.py reports/critical-junit.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def _parse(path: str) -> tuple[int, int, int, int, int]:
    tree = ET.parse(path)
    root = tree.getroot()
    tests = passed = skipped = errors = failures = 0
    suites = []
    if root.tag == "testsuites":
        suites = [c for c in root if c.tag == "testsuite"]
    elif root.tag == "testsuite":
        suites = [root]
    else:
        raise ValueError(f"Unexpected JUnit root element: {root.tag!r}")

    for ts in suites:
        tests += int(ts.attrib.get("tests", 0) or 0)
        skipped += int(ts.attrib.get("skipped", 0) or 0)
        errors += int(ts.attrib.get("errors", 0) or 0)
        failures += int(ts.attrib.get("failures", 0) or 0)

    passed = tests - skipped - errors - failures
    return tests, passed, skipped, errors, failures


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: assert_pytest_junit_xml_gate.py <junit-report.xml>", file=sys.stderr)
        return 2
    path = argv[1]
    tests, passed, skipped, errors, failures = _parse(path)
    print(
        f"junit_gate: tests={tests} passed={passed} skipped={skipped} "
        f"errors={errors} failures={failures}"
    )
    if failures or errors or skipped:
        print(
            "GATE FAILED: require skipped=0, errors=0, failures=0",
            file=sys.stderr,
        )
        return 1
    if passed <= 0:
        print("GATE FAILED: require passed > 0", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
