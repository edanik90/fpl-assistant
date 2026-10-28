# Milestone 1 verification

Verified locally on 26 October 2026 using Docker Desktop on Apple Silicon (Linux ARM64 containers).

## Automated checks

- `docker compose config --quiet`: passed.
- `docker compose build app test`: passed; TypeScript checking and Vite production build passed.
- `docker compose --profile test run --rm test`: **15 passed**. One upstream Starlette TestClient deprecation warning recommends replacing its `httpx` integration with `httpx2` in a future dependency update; no tests failed.
- Final `docker compose up --build -d --wait app`: passed after the interface text/formatting changes; Docker reported the app healthy.
- `/api/health`: HTTP 200 with `status=ok`, `database=ok`, `schema_revision=0001_initial`.
- `/`: HTTP 200 serving the compiled React app.
- `git diff --check`: passed.

The backend suite checks migration repeatability and agreement with ORM metadata, foreign-key enforcement, demo squad integrity, integer prices, no duplicated seed records, persistence across fresh app instances, invalid input isolation, catalogue filters, static and missing API routes, cross-origin write rejection, database failure health reporting, and operation without external networking.

## Browser checks

- Viewed the squad in pitch and list modes (15 players).
- Opened the captain's detail dialog and checked current, purchase and selling prices; dismissed with Escape.
- Searched the catalogue, combined search with a position filter, verified the empty state, cleared filters, and sorted by highest price.
- Saved a note through the UI, restarted the Compose service, reloaded and verified the note remained.
- Rebuilt/recreated the app container with the final frontend and verified the same note remained in the persistent volume.
- Cleared the temporary verification note through the workspace form; confirmed saving and reloading left an empty notebook.
- Inspected phone (390 × 844) and desktop (1365 × 900) layouts. Phone document width matched viewport width, with no page-level horizontal overflow. Restored the browser's normal viewport afterward.
- No browser warnings or errors were recorded during these checks.

## Remaining scope

This verifies the fictional local demo. Real FPL imports, rule validation for a selected season, editable drafts/lineups, predictions, remote authentication/access, Ubuntu deployment, AMD64 runtime verification, and backup restoration remain future milestones. No GitHub remote was configured by this implementation.

## Container hardening verification — 28 October 2026

The runtime now uses a digest-pinned distroless C/C++ base with official CPython 3.13.18 and a collected native-library dependency set. Build/test tools stay in separate stages. Copied Debian library status records are retained for scanning; no Debian essential packages are purged. Runtime inventory contains 20 OS packages.

Completed checks:

- Built the production image for Linux ARM64 and Linux AMD64 (AMD64 execution uses Docker Desktop emulation on this Mac).
- Backend test image: **15 passed**, with the existing upstream Starlette TestClient deprecation warning.
- Smoke tests against both actual runtime architectures: passed startup/migrations, UID 10001, SQLite 3.46.1, native greenlet/Pydantic imports, compiled frontend assets, API writes and persistence after container replacement.
- Inventory checks: shell, package-manager executables, pip, mount/nsenter, infocmp and Perl absent. Affected util-linux/Perl/ncurses/systemd/ACL packages from the previous report are absent. Optional native UUID1 and interactive-terminal Python extensions are intentionally excluded.
- Trivy **0.76.1**, complete image-archive scans with no ignore rules: **0 HIGH, 0 CRITICAL** on both ARM64 and AMD64. Each architecture still reports **26 MEDIUM and 10 LOW** findings; the configured gate does not block these severities.
- The actual blocking scan with `.trivyignore.yaml` (empty), HIGH/CRITICAL severity and exit code 1: exited **0** on both architectures.
- GitHub Actions workflow syntax checked with actionlint 1.7.12; `git diff --check` passed.
- Exception mechanics tested using disposable files against an existing MEDIUM finding: an active exact-package exception suppressed its target; an expired exception and a different-package exception did not. The repository exception list remained empty. The YAML date must be unquoted with Trivy 0.76.1.
- Normal Compose service started successfully with its persistent app_data volume and reached Docker's healthy state.

Scans used the vulnerability database downloaded on 28 October 2026. Results can change as advisories or detection rules change. CPython's source-built interpreter is tracked by its official image digest and `/usr/local/share/fpl-runtime/inventory.json`; copied Debian library versions remain in dpkg status records. These results do not establish that the application is free of all security issues. Server deployment and backup restoration are still pending.

The workflow now retains the complete unfiltered scan as an artifact, then applies the blocking policy separately with package-scoped, expiring exceptions supported. No vulnerability risk acceptance was applied during this work. See SECURITY.md for the decision and review process.

## Milestone 2 verification — 28 October 2026

Implemented on `codex/snapshot-imports`, based on merged `origin/main` (`1c38c70`).

- Backend suite: **41 passed**, including strict/atomic imports, source references, missing versus confirmed-zero money, history retention, deduplication, snapshot isolation, stale correction rejection, offline persistence, populated milestone 1 upgrades, and rollback of schema/revision/data when a migration fails. The existing upstream Starlette TestClient deprecation warning remains.
- TypeScript checking, `npm ci` and Vite production builds passed for ARM64 and AMD64. npm reported zero vulnerabilities during both final builds. No runtime or development dependency versions were added or changed; the frontend app version is now 0.2.0.
- Both final production images passed the expanded runtime smoke test: migrations, static example download, JSON import, unknown values, invalid-import rejection, immutable originals, saved corrections, persistent selection and equality of the complete effective overview after container replacement. AMD64 runs under Docker Desktop emulation on this Apple Silicon Mac. Each smoke test used and removed its own disposable volume; the normal app volume was preserved.
- Trivy 0.76.1 scanned exported archives of both final images using HIGH/CRITICAL severity, `--ignore-unfixed=false`, the repository's empty `.trivyignore.yaml`, and exit code 1: **0 HIGH, 0 CRITICAL; both exited 0**. These are blocking-policy scans, not new full lower-severity reports. The complete-report CI step remains enabled.
- Bandit: no issues identified. actionlint passed. The existing CodeQL-gate unit suite passed **9 tests**. `git diff --check` passed.
- Normal Compose app rebuilt, recreated and healthy at `http://localhost:8000`, preserving existing workspace notes and demo data. Health revision is `0002_imports`.
- A SQLite backup was created before the upgrade in the existing volume: `/data/fpl-assistant.before-m2.20261028T194132Z.sqlite3`. It was created with SQLite's backup API while the old service was running. This does not substitute for the later deployment backup/restore milestone.

Browser checks completed using the tracked fictional import example:

- Selected imported snapshot, provenance and history count displayed correctly; absent budget and ownership prices were unknown.
- Saved bank £1.7m, two free transfers, and slot 1 purchase/selling prices £4.3m/£4.4m through the correction form; revision 1 and its reason appeared in history and the squad summary updated.
- Unsaved corrections disabled snapshot switching/importing, survived navigation between pages, and could be discarded.
- Replacing a player cleared both ownership prices; discarding restored the saved player/prices.
- Switching to the demo showed revision 0; switching back retained the imported snapshot's revision 1. Loading original values staged unknown fields without saving over the import; those staged edits were discarded.
- Final app recreation and browser reopen retained the selected snapshot and corrected bank. Existing workspace notes were unchanged. The fictional example and its single verification correction remain available for inspection.
- At 390 × 844, the import page's document width matched the viewport (390 px); the correction table scrolls within its own container. The temporary viewport override was reset. Final browser logs contained no warnings/errors.

**Verification limit:** browser automation could not open the native file chooser, so the example was loaded through `POST /api/imports` for browser checks. The file chooser and separate-file selection workflow still need a manual browser check. API ingestion, validation and persistence are exercised in both automated suites and the actual runtime. No personal FPL files, account login, upstream requests, GitHub Actions run, or Ubuntu deployment were exercised. Full season-specific squad/formation/transfer/chip legality remains milestone 3 scope; imported season/capture metadata is user supplied and cannot establish cross-file season provenance by itself.
