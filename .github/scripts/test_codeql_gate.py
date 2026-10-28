import contextlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest

check = runpy.run_path(str(Path(__file__).with_name("check-codeql-results.py")))["check"]


class CodeQLGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def report(self, score=None, results=True, level="warning"):
        rule = {"id": "test-rule", "defaultConfiguration": {"level": level}}
        if score is not None:
            rule["properties"] = {"security-severity": str(score)}
        data = {"runs": [{"tool": {"driver": {"rules": [rule]}},
                          "results": [{"ruleId": "test-rule"}] if results else []}]}
        (self.directory / "python.sarif").write_text(json.dumps(data))

    def run_gate(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return check(self.directory)

    def test_missing_report_fails(self):
        self.assertEqual(self.run_gate(), 1)

    def test_clean_report_passes(self):
        self.report(results=False)
        self.assertEqual(self.run_gate(), 0)

    def test_medium_finding_does_not_cross_threshold(self):
        self.report(score=6.9)
        self.assertEqual(self.run_gate(), 0)

    def test_high_finding_fails(self):
        self.report(score=7.0)
        self.assertEqual(self.run_gate(), 1)

    def test_critical_finding_fails(self):
        self.report(score=9.8)
        self.assertEqual(self.run_gate(), 1)

    def test_rule_default_error_level_fails(self):
        self.report(level="error")
        self.assertEqual(self.run_gate(), 1)

    def test_malformed_report_fails_closed(self):
        (self.directory / "python.sarif").write_text("invalid json")
        with self.assertRaises(ValueError):
            self.run_gate()

    def test_empty_analysis_runs_fail_closed(self):
        (self.directory / "python.sarif").write_text('{"runs": []}')
        with self.assertRaises(ValueError):
            self.run_gate()

    def test_failed_analysis_invocation_fails_closed(self):
        self.report(results=False)
        report = self.directory / "python.sarif"
        data = json.loads(report.read_text())
        data["runs"][0]["invocations"] = [{"executionSuccessful": False}]
        report.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.run_gate()
