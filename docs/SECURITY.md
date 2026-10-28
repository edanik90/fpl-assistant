# Container security and reviewed exceptions

## Runtime design

The final image uses Google's distroless C/C++ runtime for Debian 13, pinned by multi-architecture digest. The build stage supplies the official, patched CPython 3.13 interpreter, production dependencies and the interpreter's required shared libraries. App/migration sources and compiled frontend assets are copied separately.

`scripts/prepare-runtime.py` stages this filesystem without purging Debian packages. It deliberately excludes build/test tooling, pip/ensurepip, Tk, interactive terminal extensions and the optional native UUID1 helper. Python's UUID4 support remains available. `ldd` identifies required native libraries; Debian status records for every copied library and a build inventory are retained so scanning still sees their versions. The distroless base supplies its matched loader, glibc and C++ runtime. Do not delete package metadata to conceal findings.

The shipped image has no shell, apt/dpkg executables, mount/nsenter, infocmp or Perl interpreter. It runs as UID/GID 10001, compatible with the existing data volume. Compose retains its loopback binding, read-only root filesystem, dropped capabilities and no-new-privileges. Use `docker compose exec app /usr/bin/python3 ...` for diagnostics; shell and pip commands are unavailable.

References: [distroless documentation](https://github.com/GoogleContainerTools/distroless), [Docker image guidance](https://docs.docker.com/build/building/best-practices/).

## CI behavior

The Trivy action revision and scanner version are separate. `uses: aquasecurity/trivy-action@...` pins the wrapper; **`with.version: v0.76.1`** in `.github/workflows/ci.yml` selects the scanner binary.

The container job builds the actual runtime and runs `scripts/smoke-container.py` in a disposable container/volume without external networking. This tests startup/migrations, native libraries, static assets, writes, persistence after replacement, numeric UID and absence of unnecessary utilities/packages.

Next it saves a complete JSON vulnerability report with all severities and no exceptions. Findings alone do not fail that reporting step; execution errors still fail it. A separate blocking scan enforces HIGH/CRITICAL findings with `--ignore-unfixed=false`, explicitly loads `.trivyignore.yaml`, and displays suppressed findings using `--show-suppressed`. The complete JSON report is retained as a GitHub Actions artifact for 14 days, including when the gate fails.

The aggregate `PR gate` still requires this job to succeed. Every HIGH/CRITICAL finding without an applicable unexpired exception blocks it. Scanner/database failures also block it. **No vulnerability exceptions are accepted in the initial ignore file.** The vulnerability database can change independently of image/scanner pins, so a later scan may find new issues in an unchanged image.

## Severity versus applicability

Before accepting a finding, determine:

1. Whether the affected component exists in the actual image. A source-package CVE may appear against several binary packages; identify which contains the affected code.
2. Whether application inputs can reach the code, including subprocesses, optional features and required privileges.
3. The potential impact and deployment controls. Non-root execution reduces some risks but does not prove a finding harmless.
4. Whether a patch, component removal or safe image update is available.
5. Evidence of exploitation, including vendor advisories and exploitation likelihood.

CVSS describes severity; its exploitability subscore is not an attack probability. [EPSS](https://www.first.org/epss/) estimates exploitation in the wild over the next 30 days, rather than the probability of compromise of this particular app. A low EPSS score is a prioritization signal, not sufficient evidence for an exception by itself. Record its value and observation date when using it in a decision.

| Decision | Meaning | Required evidence |
| --- | --- | --- |
| Fix/investigate | Applicable vulnerability or uncertain reachability | Affected version and remediation/investigation issue |
| Not affected / false-positive finding | Affected component/code is absent, or the affected-version mapping is wrong | Vendor statement, actual image inventory and code-path analysis |
| Risk accepted | Vulnerable code exists and the owner accepts residual risk temporarily | Impact/exposure, controls, explicit approval and expiry |

A VEX statement is useful for a machine-readable not-affected assessment. Risk acceptance should not be labeled a false positive. Suppression changes the merge decision; it does not patch anything.

## Accepting a specific finding

1. Download the full `container-security-...` artifact from the workflow run. Find `VulnerabilityID`, `PkgName`, `InstalledVersion` and **`PkgIdentifier.PURL`** in `trivy-results.json`.
2. Investigate the vendor advisory and actual affected code. Record image/base digest, architecture, reachability, impact, controls and available fix.
3. Open a tracking issue and record the repository owner's approval. Use a short review period, such as 30 days.
4. Add an entry to `.trivyignore.yaml` with the exact package PURL from that report, `expired_at`, and an explanatory `statement`. Explicitly list each package/architecture reviewed.
5. Commit it through a pull request. Review exception/workflow changes as security decisions. Check that suppressed findings remain visible in the log and complete report.
6. Remove the entry when patched. Trivy stops applying an expired entry; a matching HIGH/CRITICAL finding then blocks the gate again. Re-review earlier if deployment/image changes invalidate its assumptions.

Example **template only**, not an approved assessment of this CVE:

```yaml
vulnerabilities:
  - id: CVE-2025-69720
    purls:
      - "COPY_THE_EXACT_PACKAGE_PURL_FROM_THE_JSON_REPORT"
    expired_at: 2026-11-27
    statement: >-
      Decision: REPLACE_WITH_NOT_AFFECTED_OR_RISK_ACCEPTED.
      Owner: REPLACE_WITH_APPROVER; approved: REPLACE_WITH_DATE.
      Tracking issue: REPLACE_WITH_ISSUE_URL.
      Evidence: REPLACE_WITH_ADVISORY_AND_IMAGE_EVIDENCE.
      Exposure/impact: REPLACE_WITH_ASSESSMENT.
      Controls and re-review conditions: REPLACE_WITH_DETAILS.
```

Do not paste the template unchanged. Use an **unquoted YAML date** for `expired_at`, as shown; Trivy 0.76.1 rejects a quoted date-only string. Without `purls`, a CVE exception applies to every matching package; without expiry it is indefinite. The `statement` documents the reason but does not affect matching. The YAML format is experimental: keep it explicitly configured and retest when changing scanner versions. See [Trivy's field definitions, expiry and VEX options](https://trivy.dev/docs/latest/guide/configuration/filtering/).

Do not globally ignore unfixed findings or add a blanket list of CVEs to make the gate pass. If you choose a different policy, record that policy change explicitly.

## Local verification

```sh
docker compose build app test
docker compose --profile test run --rm test
python3 scripts/smoke-container.py --image fpl-assistant:local
```

The smoke test only creates/removes its own temporary container and volume. It does not modify Compose's app_data volume. To scan without mounting the Docker socket into a scanner container:

```sh
docker image save fpl-assistant:local -o /tmp/fpl-runtime.tar
trivy image --input /tmp/fpl-runtime.tar --scanners vuln \
  --ignorefile /dev/null --format json --output /tmp/fpl-trivy-full.json
trivy image --input /tmp/fpl-runtime.tar --scanners vuln \
  --severity HIGH,CRITICAL --ignore-unfixed=false \
  --ignorefile .trivyignore.yaml --show-suppressed --exit-code 1
```

Use the CI scanner version. Test the actual server architecture: ARM64 results do not prove AMD64 inventory/binaries are identical. Python modules requiring a newly introduced native library must be included in the staging inventory and tested when adding features.
