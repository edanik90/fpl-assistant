# FPL Assistant

Private, single-user Fantasy Premier League planning app, intended to run in Docker on an Ubuntu Server VM hosted by Proxmox.

Status: repository and planning documents only. The application, Docker image and deployment are not implemented yet.

## Agreed first version

- Import FPL JSON snapshots from files; preserve their season, gameweek and import time.
- Manually correct bank balance, free transfers and player purchase/selling prices.
- Create and save draft squads and transfers.
- Choose a starting XI, captain, vice-captain and bench order.
- Evaluate expected points and suggest affordable transfers using a transparent statistical model.
- Keep imported actual-team snapshots separate from local drafts.
- Make no changes to the user's official FPL team.

## Proposed stack

Python/FastAPI/Pydantic, React/TypeScript/Vite, SQLite/SQLAlchemy, pandas/NumPy and OR-Tools. Docker Compose will run the app and persist its data. Package and image versions will be selected and locked during implementation.

## Documents

- [Implementation brief](docs/IMPLEMENTATION_BRIEF.md)
- [Setup and secrets plan](docs/SETUP.md)

No secrets are required to start development with synthetic fixtures and manually imported snapshots. No GitHub remote has been configured.
