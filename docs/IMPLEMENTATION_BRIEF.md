# Implementation brief

Agreed on 26 October 2026. This is the full product specification. Milestones 1 and 2 are implemented; later milestones remain planned. See README.md for the current runnable feature set and verification commands.

## User and hosting

One user, private non-commercial use, local/server hosting. The server runs Proxmox. Use an Ubuntu Server VM and Docker Compose. The user requires fully self-hosted secrets management. Develop on the user's Apple Silicon Mac; ensure the deployed image supports the server architecture.

## Domain model

Persist versioned imports, source/season/player IDs, fixtures, match statistics, actual-team snapshots, manual corrections and independent named drafts. Record data timestamps. An import must never silently overwrite a saved draft. Personal imports and databases stay outside Git and image build contexts.

Use integer units of GBP 0.1 million for budgets and prices. Store individual purchase and selling prices. Calculate affordability from bank plus selling proceeds, not current market value. Keep free transfers, transfer hits and chip state explicit. Validate rules for the selected season rather than assuming they never change.

## Pages

1. Squad/transfers: player filtering, current squad and drafts, transfers in/out, bank, selling prices, free transfers, hits, save/reset/compare drafts.
2. Lineup: legal starting XI, captain/vice-captain, ordered bench, formation and projected points. Changes affect drafts only.
3. Evaluation: next-gameweek and configurable multi-gameweek expected points, weaknesses, feasible transfer plans, uncertainty and explanations. Include no-transfer/roll options.

## Data ingestion

Start with synthetic fixtures plus local JSON imports of the FPL bootstrap catalogue, fixtures, player match histories and a team snapshot. The app must remain usable without an authenticated FPL session. Provide manual squad and budget corrections when snapshot fields are absent.

Public gameweek picks describe a squad after that gameweek's deadline and may not match later transfers. The private my-team endpoint is known to provide current picks, selling prices and transfer status, but its authentication integration has not been tested for this user and is outside the initial scope.

FPL website endpoints have no supported developer contract. FPL terms clause 28(d) prohibits automated extraction. Resolve permitted access separately before adding scheduled FPL fetching. No upstream write operations are allowed by the product requirements.

## Prediction and optimisation

Start with an explainable baseline: shrink recent xG/xA rates toward longer-term rates, estimate expected minutes and probability of reaching appearance thresholds, adjust for opponent and home/away, and include clean sheets, saves, defensive contributions, cards and bonus where supportable. Handle blank/double gameweeks by fixture. Model parameters and assumptions must be visible; missing data is not zero.

Compare proposed transfers against a no-transfer baseline over the same horizon. Account for bank, sales, player prices, squad/club limits, free transfers, hits, captaincy and the future value of retaining transfers. Backtest using only information available at each historical decision point. Show expected points and uncertainty rather than claiming an objective universal team rating.

## Milestones

1. Runnable Docker app, SQLite migrations, health check and synthetic demonstration data.
2. Validated snapshot import and manual squad/budget corrections.
3. Persistent drafts and transfer/formation/captaincy validation.
4. Expected-points baseline and explainable transfer suggestions.
5. Tests for consequential budget/rule cases, database persistence, import validation and isolation from upstream FPL writes.
6. Deploy to Ubuntu VM with persistent storage, backup/restore instructions and private access.

## Research references

- FPL player catalogue: https://fantasy.premierleague.com/api/bootstrap-static/
- Example match history: https://fantasy.premierleague.com/api/element-summary/1/
- FPL terms: https://fantasy.premierleague.com/help/terms
- FPL pricing/selling guidance: https://www.premierleague.com/en/news/4661030
- Historical data archive (not a weekly current feed): https://github.com/vaastav/Fantasy-Premier-League
