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
