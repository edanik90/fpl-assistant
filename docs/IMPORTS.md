# Snapshot imports and corrections (milestone 2)

Use **Data & imports** in the sidebar. Imports happen on your local app server; the app never contacts FPL, authenticates to an FPL account, or submits team changes.

## Try the complete workflow

1. Download the fictional example from **Data & imports**. It contains the same fictional players as the demo, with separate numeric source IDs and deliberately missing budget and ownership prices.
2. Select that file under **One snapshot bundle**, then choose **Validate & import**.
3. Check its season, gameweek, capture time and source. The selected snapshot is persisted and appears in **My squad** and **Player library**.
4. Under **Correct your actual squad**, enter confirmed bank/free transfers, transfer hit, chip state, and each player's purchase/selling prices. Blank means unknown; zero means confirmed zero. Prices in the form are £ millions: `4.5` becomes the integer `45` in storage.
5. Replace a player in the relevant slot if the snapshot is outdated. Replacement clears that slot's ownership prices so another player's prices cannot carry over. Slots 1–11 are starters and 12–15 are ordered substitutes. Choose a captain and a different vice-captain.
6. Enter a reason and **Save correction**. This appends a revision; it leaves the original import unchanged. Refresh or restart the app and check the saved values.
7. Switch between the demo and imported snapshots with **Selected snapshot**. Each has independent corrections. Unsaved corrections prevent switching/importing until saved or discarded; they remain in the form when visiting another page.

**Load original values** fills the correction form from the original snapshot. Save it to record a restoration revision. **View original JSON** shows the original normalized fields plus original monetary values; **Correction history** shows revision numbers, reasons and timestamps. Full historical values are also available through the corrections API.

These controls record corrections to your *actual team*. Proposed transfers, independent drafts, affordability checks and season-specific formation/club/chip/transfer rules belong to milestone 3. Milestone 2 validates structural integrity, not full FPL legality. The displayed squad value uses market prices; it is not spending power.

## Import existing local files

Choose **Separate FPL JSON files** and supply:

- A bootstrap object with `teams` and `elements`.
- A fixtures JSON array. Include fixtures referenced by any supplied histories, including earlier gameweeks. Unscheduled fixtures may have `event: null` and unknown kickoff times. The squad board shows only the selected gameweek, including multiple fixtures per club.
- A team object with a `picks` array of 15 distinct catalogue players, slots 1–15, and boolean `is_captain`/`is_vice_captain`. This accommodates public gameweek-picks and private my-team-shaped local files; no authentication integration is provided.
- Optional element-summary objects with `history` arrays (one player per file). Supported match statistics are retained, with missing statistics represented as null. The original normalized JSON exposes those records; predictions are not calculated yet.

Enter the season, gameweek and capture time yourself. The local time from the form is stored in UTC. Public deadline picks may differ from a current squad after subsequent transfers; choose **A gameweek deadline** for those files. These endpoint payloads have no reliable common season identifier: the app cannot prove that your files belong to the same season or capture. Check that yourself. It validates IDs and history/fixture references within the supplied bundle.

Files must already be available through a source you are permitted to use. This milestone does not add fetching or instructions for bypassing upstream access restrictions.

## Bundle format

The [fictional example](../frontend/public/examples/snapshot.json) is a complete working template. Bundle keys:

| Key | Meaning |
| --- | --- |
| `label` | Required snapshot name, 1–80 characters |
| `season` | Required consecutive years, e.g. `2026/27` |
| `gameweek` | Required integer, 1–60 (a format bound, not a season rules assertion) |
| `captured_at` | Required ISO timestamp with timezone |
| `kind` | `deadline`, `current` or `manual` |
| `bootstrap`, `fixtures`, `team` | Required source objects/array described above |
| `player_histories` | Optional array of element-summary objects |
| `bank_tenths`, `free_transfers`, `transfer_hits`, `chip` | Optional, explicit confirmed metadata; otherwise null |

Catalogue elements require `id`, `first_name`, `second_name`, `web_name`, `team`, `element_type` (1–4) and integer `now_cost` (units of £0.1m). Fixtures require `id`, `team_h`, `team_a`; `event` and `kickoff_time` are optional. Picks require `element`, `position`, and the two captain flags; optional `purchase_price`/`selling_price` are already in £0.1m units. Histories require `element`, `fixture`, `opponent_team`, `round`, `minutes`, `total_points`; optional expected-goal statistics use decimal strings, as in the example. See `/api/docs` for all accepted fields and bounds.

A bundle is limited to **8 MiB** after JSON serialization. Import fewer history files if needed. Source fields outside the supported schema are discarded, including unrelated private account details. Top-level bundle metadata rejects unknown keys to catch typos. Do not include cookies or credentials in any import. Supported fields are stored in SQLite, not the repository or image. Store personal source files under ignored `snapshots/` or outside the checkout; `frontend/public/examples/` is exclusively for the tracked fictional example.

Absent bank/free transfers are **never** inferred from `entry_history.bank` or `transfers.limit`: those values can describe different moments or transfer/chip semantics. Purchase and selling prices are never replaced with market price or calculated using an assumed season rule.

## Versioning and failure behavior

Imports are atomic. Invalid JSON, oversized uploads, duplicate source IDs, missing references, invalid types/negative money, duplicate squad members/slots or invalid captain identity reject the whole request. No partial snapshot or selection is saved. Normalized bundle content is hashed: repeating the same content (even with another label) selects the existing snapshot and preserves its corrections. Changed data or capture metadata creates a new snapshot. Original fields are retained unchanged; corrections are appended separately.

Correction writes send the expected revision. A stale editor receives HTTP 409 and keeps its unsaved fields; reload before reapplying the intended edit. The app does not silently overwrite a newer correction from another tab. A new import does not overwrite workspace notes or another snapshot's history. There is no snapshot deletion in this milestone.

API additions:

- `GET /api/snapshots`: immutable original snapshot summaries.
- `POST /api/imports`: validated bundle; selects and returns effective overview.
- `PUT /api/selection`: `{ "snapshot_id": 2 }`; selects and returns effective overview.
- `GET /api/snapshots/{id}/original`: normalized original import and base values.
- `GET /api/snapshots/{id}/corrections`: all correction values/reasons/timestamps, newest first.
- `POST /api/snapshots/{id}/corrections`: `{ "expected_revision": 0, "reason": "…", "values": { "bank_tenths": null, "free_transfers": null, "transfer_hits": null, "chip": null, "picks": […] } }`.

`GET /api/overview` and `/api/players` use the selected snapshot; the overview includes effective corrected picks/budget and a correction revision. Original pick IDs in correction values are local database player IDs, not FPL source IDs.

## Database upgrade

Startup migrates existing data from `0001_initial` to `0002_imports`, preserving workspace notes and demo rows. Nullable money fields allow honest unknown values; separate selection and correction tables persist the new state. SQLite foreign keys are disabled only on the startup migration connection during table rebuilds, checked before completion, and re-enabled before serving requests. Fresh and populated milestone 1 databases are covered by tests.

Before upgrading your own installation, stop the app and back up its SQLite database/volume. Do not delete the Compose volume. Downgrading this migration is intentionally refused because unknown values cannot be represented honestly by milestone 1; restore a pre-upgrade backup with the previous app version instead. Full deployment backup/restore procedures remain part of the server milestone.
