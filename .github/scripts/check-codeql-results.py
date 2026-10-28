"""A successful CodeQL upload alone is not evidence of a clean analysis."""
import json
from pathlib import Path
import sys


def check(directory: Path) -> int:
    reports = sorted(directory.glob("*.sarif"))
    if not reports:
        print("CodeQL did not produce a SARIF report.")
        return 1
    failures = []
    for report in reports:
        data = json.loads(report.read_text())
        if not data.get("runs"):
            raise ValueError(f"No analysis runs in {report.name}")
        for run in data["runs"]:
            if any(invocation.get("executionSuccessful") is False for invocation in run.get("invocations", [])):
                raise ValueError(f"Analysis failed in {report.name}")
            rules = {rule["id"]: rule for rule in run["tool"]["driver"].get("rules", [])}
            for result in run.get("results", []):
                rule = rules.get(result["ruleId"], {})
                score = rule.get("properties", {}).get("security-severity")
                level = result.get("level", rule.get("defaultConfiguration", {}).get("level", "warning"))
                if (score is not None and float(score) >= 7) or level == "error":
                    failures.append(f"{report.name}: {result['ruleId']}")
    if failures:
        print("Blocking CodeQL findings:\n" + "\n".join(failures))
        return 1
    print("No high/critical security findings or error-level results in CodeQL reports.")
    return 0


if __name__ == "__main__":
    sys.exit(check(Path(sys.argv[1])))
