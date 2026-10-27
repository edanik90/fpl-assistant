# Setup and secrets plan

Updated 26 October 2026. Milestone 1 runs locally in Docker. The Ubuntu VM, remote access and self-hosted secrets service remain deployment plans.

## 1. Development computer

Git and Docker Desktop are installed on the user's Apple Silicon Mac. The Docker engine and Compose were verified during milestone 1. The current shell may not include Docker's CLI directory; for that Terminal session run:

```sh
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
docker version
docker compose version
```

Launch Docker Desktop before running the app. From the repository, run:

```sh
docker compose up --build -d --wait app
```

Open http://localhost:8000. To run the isolated backend tests:

```sh
docker compose --profile test run --build --rm test
```

The app binds to localhost only and uses the persistent `fpl-assistant_app_data` Docker volume. Workspace name/notes survive app restarts. The seed is fictional and never replaces existing notes. See the README for port overrides, API endpoints, storage, shutdown commands and the current feature boundaries.

The Docker workflow provides Python and Node.js in containers. Installing host Python, Node.js, an IDE or GitHub CLI is optional, not a prerequisite. Do not replace macOS's system Python.

Download: https://docs.docker.com/desktop/setup/install/mac-install/

## 2. Local project and GitHub

The local repository is /Users/edt_90/Documents/Codex/fpl-assistant. Add that folder as a local project in Codex, named FPL Assistant. If using Edit project > Add folder, make this folder primary. Keep the implementation brief available to future chats.

Create a private GitHub repository named fpl-assistant under the intended personal account. Leave README, .gitignore and license initialization unchecked because local files already exist. A remote URL and authenticated Git connection are needed before publishing the local repository. No remote has been created or configured by this setup work.

GitHub stores source code and reviewed templates. Personal snapshots, the SQLite database, plaintext credentials and secret-manager backups stay out of Git. A private repository is not a secrets vault. GitHub Actions secrets are unnecessary until a CI/deployment workflow needs them.

References:
- https://learn.chatgpt.com/docs/projects
- https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository

## 3. Proxmox VM

Suggested initial VM: Ubuntu Server 24.04 LTS, 4 vCPU, 8 GB RAM and 60 GB SSD-backed disk. This is a starting allocation for the app plus Infisical and its dependencies; measure usage and adjust. Docker also supports Ubuntu 26.04 LTS, so either supported LTS is technically suitable.

Create a QEMU VM in Proxmox, upload/mount the official Ubuntu Server ISO, install Ubuntu with OpenSSH, and reserve a stable LAN IP. Install/enable the QEMU guest agent and enable its corresponding Proxmox setting. Apply OS updates. Install Docker Engine and the Compose plugin from Docker's official apt repository in the VM. Docker Desktop is for the Mac, not required in the server VM.

Use separate Compose projects for the FPL app and Infisical. Keep services private, with a deliberate HTTPS or SSH-tunnel access route. Do not publish PostgreSQL/Redis ports to the LAN. Docker-published ports need explicit access controls; do not assume UFW alone restricts them.

Sources:
- https://ubuntu.com/download/server
- https://docs.docker.com/engine/install/ubuntu/
- https://infisical.com/docs/self-hosting/deployment-options/docker-compose

## 4. Fully self-hosted secrets

Proposed tool: self-hosted Infisical using its core secrets-management functionality. Its Compose deployment runs Infisical, PostgreSQL and Redis. Review the selected version's available roles/licensing before depending on advanced policies or paid features. Pin the reviewed image version rather than following latest automatically.

Create separate projects for development and production if fine-grained environment restrictions are unavailable in the chosen edition. Use a dedicated application machine identity with the minimum available permissions. The deployment client must explicitly target the local Infisical URL; do not leave a cloud default configured.

The first version needs no FPL password, paid-data API key or language-model API key. Add actual secrets only as features require them.

| Information | Storage |
| --- | --- |
| Non-secret settings (port, timezone, data path) | Reviewed config / .env.example |
| Future API keys or application signing secrets | The self-hosted Infisical project |
| Runtime values required by the backend | Files supplied at startup via Compose secrets, or the application's secret-loader integration |
| Infisical's own encryption key, auth secret and database credentials | Restricted host bootstrap configuration outside Git |
| Credential allowing the app to authenticate to Infisical | Restricted host credential file; mounted only into the secret-loader/backend that needs it |
| Personal FPL snapshots, drafts and SQLite | Persistent app data volume; backed up privately |
| GitHub authentication / SSH private keys | Developer or deployment user's credential storage; not supplied to the app |

There must be a small amount of bootstrap credential material outside the vault: Infisical cannot fetch the key needed to start itself from its own unavailable API. For example, place its required bootstrap .env at /opt/infisical/.env, outside the code repository, with the owning administrator as its only ordinary reader (`chmod 600`). Keep separate encrypted offline backups of the recovery material. Never keep the only copy of Infisical's encryption key inside Infisical or solely in the same VM.

Docker Compose secrets mount files under /run/secrets. Ordinary Compose does not encrypt the source file on the host; protect its permissions and storage. The app will explicitly implement reading any *_FILE configuration; the suffix is not automatic Docker behavior. Do not bake secrets into an image or frontend bundle. Do not print values in logs or commit them in examples.

Back up Infisical's PostgreSQL database and encryption/recovery configuration, plus the app's SQLite database and snapshots. Store backups outside this VM and test restoration. A VM snapshot alone is not the only backup.

Sources:
- https://infisical.com/docs/self-hosting/overview
- https://infisical.com/docs/self-hosting/deployment-options/docker-compose
- https://infisical.com/docs/documentation/platform/identities/universal-auth
- https://docs.docker.com/compose/how-tos/use-secrets/

## 5. Implementation sequence

Local Docker development and the synthetic demo are implemented. Next, add validated file imports/manual corrections, followed by independent saved drafts and prediction. Create the VM and secrets service alongside app development. Secrets management must not block development with synthetic data. Before deploying, build/test for the server architecture and verify private access, persistence and backup restoration.

Pending user setup details: final VM IP, chosen Ubuntu LTS, GitHub repository URL, and preferred private-access URL/tunnel. These do not block local development.
