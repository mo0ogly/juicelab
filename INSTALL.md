# INSTALL

Step-by-step installation for JuiceLab. Three target audiences :

- **Section 1** — Teacher who wants to try JuiceLab on a single laptop (smoke test, 5 minutes).
- **Section 2** — Teacher who runs a 12-hour TD with N students on a shared VPS or local LAN (cohort mode).
- **Section 3** — Course coordinator who wants the full Mode C with a public CTFd leaderboard.

Section 4 covers Windows-native dev (without Docker) for contributors who edit the overlay or the dashboard.

> Read the [README](./README.md) first if you have not yet — it explains *what* JuiceLab is. This document only covers *how to install it*.

---

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Docker Engine | 24+ | All deployment scenarios |
| Docker Compose plugin | v2 | All deployment scenarios |
| Python | 3.10+ | `provision.py` (cohort), `verify_proof.py` (offline proof check) |
| Node.js | 22+ | Section 4 only (native dev without Docker) |
| Git | any | Cloning |
| RAM | 2 GB per Juice Shop instance, 100 MB for the dashboard | All |

The container build downloads ~ 700 MB on the first run (npm install). The cached subsequent build is ~ 10 seconds.

---

## 1. Single-instance smoke test (one laptop, 5 minutes)

The goal here is to validate that the build chain + dashboard + overlay all wire up correctly.

### 1.0 One-shot installer (recommended for students and the smoke test)

```bash
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab
./scripts/install-student.sh -c M2-IA-2026
```

The script :

- checks `docker`, `docker compose v2`, `openssl`
- generates `TEACHER_ADMIN_TOKEN` and `DASHBOARD_TEACHER_TOKEN` (32 chars each via `openssl rand`) and writes `docker/.env` from `.env.example` if it does not exist yet
- preserves any token already present in `docker/.env` (idempotent — re-running it does not rotate keys)
- runs `docker compose --env-file .env up -d --build`
- waits for `http://127.0.0.1:3000/` and `http://127.0.0.1:5000/api/health` to answer
- prints both teacher tokens and the student / teacher URLs at the end

Other modes :

```bash
./scripts/install-student.sh                     # interactive, asks for cohort_id
./scripts/install-student.sh -y                  # non-interactive, default cohort
./scripts/install-student.sh --reset             # docker compose down -v + clean reinstall
```

If you want to drive the manual path (custom .env, custom build args, CTFd integration, etc.), keep reading § 1.1 below.

### 1.1 Two installation paths

JuiceLab ships in **two installable forms** :

| Path | What it gives you | Best for |
|---|---|---|
| **1.1.a — 100 % Docker** | `git clone` + `docker compose up --build`. The Dockerfile clones OWASP Juice Shop at a pinned commit, applies the overlay, applies the patch, builds the slim image. No host-side merge. | Teachers running the smoke test or a TD ; CI environments. |
| **1.1.b — Native dev** | `git clone` of both `juicelab` and `juice-shop`, then `scripts/apply-overlay.sh` merges them on disk. You then run `npm start` and `python app.py` directly. | Contributors who edit overlay files and want hot-reload. |

#### 1.1.a — 100 % Docker (recommended for first install)

```bash
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab
```

Skip directly to **§ 1.2** below. The `docker compose up --build` in § 1.3 handles the upstream clone, overlay copy and patch application inside the builder stage. Nothing else needs to be on disk.

> **What the Dockerfile does internally** : in the `builder` stage, `Dockerfile.juicelab` clones <https://github.com/juice-shop/juice-shop.git> at the pinned commit `3b178fd` (overridable via `--build-arg JUICE_SHOP_COMMIT=…`), copies every file under `overlay/` into the cloned tree, then runs `git apply --3way patches/juicelab-core.patch` to wire the JuiceLab additions into the Juice Shop core. The runtime stage only contains the merged, built tree — no git, no overlay/, no patches/.

#### 1.1.b — Native dev (overlay editing on host)

```bash
git clone https://github.com/mo0ogly/juicelab.git
git clone https://github.com/juice-shop/juice-shop.git
cd juicelab

# apply the overlay on top of the vanilla Juice Shop clone
./scripts/apply-overlay.sh ../juice-shop          # Linux / macOS / WSL / Git Bash
# OR
.\scripts\apply-overlay.ps1 -JuiceShopDir ..\juice-shop   # Windows PowerShell 7+
```

The installer is idempotent. Re-running it after upstream Juice Shop has been updated keeps your local overlay aligned with the patch (conflicts surface as `.rej` files you resolve by hand). Read [`overlay/README.md`](./overlay/README.md) for the layout.

For native dev, continue with § 4 below (boot Juice Shop + dashboard without Docker).

### 1.2 Configure secrets

```bash
cd docker
cp .env.example .env
```

Edit `.env` and set, **at minimum** :

```
DASHBOARD_TEACHER_TOKEN=<32 random chars, used by /login and X-Teacher-Token>
DASHBOARD_PROOF_SECRET=<32 random chars, used to HMAC-SHA-256 the lab proofs>
JUICELAB_COHORT_ID=M2-IA-2026
```

> **Token length is enforced.** The dashboard refuses to boot if either token is shorter than 16 characters. This is intentional — these tokens grant teacher-level access to the cohort matrix and the proof signing key.

> **Sharing a teacher token across machines is fine** — it is a coarse-grained credential. Sharing the proof secret across machines is also fine but means proofs signed on machine A can be verified on machine B. Pick one strategy and stick to it.

### 1.3 Boot

```bash
docker compose --env-file .env up -d --build
```

First build : ~ 8 minutes (npm install dominates). Subsequent builds : ~ 10 seconds.

### 1.4 Verify

| Endpoint | Expected |
|---|---|
| <http://127.0.0.1:3000/#/score-board> | Juice Shop score-board with **TD** buttons on the 13 selected challenge cards |
| <http://127.0.0.1:3000/#/juicelab> | JuiceLab parcours panel (overview of the 13 challenges grouped by half-day) |
| <http://127.0.0.1:5050/login> | Dashboard login page |
| <http://127.0.0.1:5050/dashboard?cohort=M2-IA-2026> | Cohort matrix (empty until students start solving) |
| `curl http://127.0.0.1:5050/api/health` | `{"ok": true}` |

Commission test : log in to the dashboard, register a Juice Shop user (`/#/register`), solve `Score Board` (the easy one — find the link in the page source), open the **TD** dialog on the score-board card, fill the journal in the *After* tab, paste the flag, click **Verify**. The dashboard cohort matrix should refresh with `solved`, `journal`, `quiz`, and `flag verified` indicators.

### 1.5 Stop

```bash
docker compose --env-file .env down            # keeps the dashboard volume (events history)
docker compose --env-file .env down -v         # wipes everything
```

---

## 2. Cohort of N students (TD on shared VPS or LAN)

Goal : every student gets their own Juice Shop instance, all instances post events to a single dashboard, the teacher watches one matrix.

### 2.1 Roster

```bash
cd docker
cp roster.example.txt roster.txt
$EDITOR roster.txt
```

One handle per line, lowercase, alphanumeric + hyphens only, max 30 characters. Empty lines and `#` comments are ignored.

```
amelie
bobby
chloe
diane
eric
```

### 2.2 Provision

```bash
python provision.py roster.txt --port-base 3001 \
  --output docker-compose.cohort.yml \
  --print-cors
```

The script generates :

- `docker-compose.cohort.yml` — one `juicelab-<handle>` service per student, mapped to `port_base + index`.
- The exact `DASHBOARD_CORS_ORIGINS` value to paste into `.env` (the dashboard rejects events from any origin not on this list).

### 2.3 Wire CORS

Paste the printed value into `.env` :

```
DASHBOARD_CORS_ORIGINS=http://127.0.0.1:3001,http://localhost:3001,http://127.0.0.1:3002,http://localhost:3002,...
```

### 2.4 Boot the cohort

```bash
docker compose -f docker-compose.yml -f docker-compose.cohort.yml \
    --env-file .env up -d --build
```

### 2.5 Distribute URLs

Hand each student their URL :

```
amelie  -> http://<server IP>:3001/#/juicelab
bobby   -> http://<server IP>:3002/#/juicelab
chloe   -> http://<server IP>:3003/#/juicelab
```

The teacher watches `http://<server IP>:5050/dashboard?cohort=M2-IA-2026` (login with `DASHBOARD_TEACHER_TOKEN`).

### 2.6 Live monitoring

```bash
docker compose -f docker-compose.yml -f docker-compose.cohort.yml \
    --env-file .env ps
docker compose logs -f juicelab-amelie
```

### 2.7 End of TD

```bash
docker compose -f docker-compose.yml -f docker-compose.cohort.yml \
    --env-file .env down -v
```

> **Persistence note.** The Juice Shop in-memory `consumedHintsByStudent` map is lost on container restart. This is acceptable for a 12-hour TD where instances stay up. For multi-day courses, migrate to Redis (tracked in [#2](https://github.com/mo0ogly/juicelab/issues/2)).

---

## 3. Public deployment with CTFd (Mode C)

Goal : add a public CTFd leaderboard so the cohort sees real-effort competition. JuiceLab pushes hint penalties as negative awards so a student who consumed N4 cannot pass a student who solved unaided.

### 3.1 Host CTFd

Two options :

**(a) CTFd in the same Docker Compose** :

1. Uncomment the `ctfd` service in `docker/docker-compose.yml` (and the `ctfd_uploads` / `ctfd_logs` volumes).
2. Generate `CTFD_SECRET_KEY` and add it to `.env`.
3. `docker compose --env-file .env up -d ctfd`
4. Open <http://127.0.0.1:8000>, complete the setup wizard.

**(b) CTFd elsewhere** : follow the [official CTFd docs](https://docs.ctfd.io/), note its public URL.

### 3.2 Import the challenges with juice-shop-ctf-cli

```powershell
npm install -g juice-shop-ctf-cli

@'
ctfFramework: CTFd
juiceShopUrl: http://127.0.0.1:3000
ctfKey: <copy the contents of juice-shop/ctf.key>
insertHints: none
'@ | Out-File juicelab-ctfd.yml

juice-shop-ctf --config juicelab-ctfd.yml --output cohort-2026.csv
```

In CTFd : `Admin > Config > Backup > Import CSV` → "Challenges" → upload `cohort-2026.csv`.

> `insertHints: none` is intentional. We want JuiceLab hints (5-level, gated), not Juice Shop's stock hints — otherwise students get double exposure.

### 3.3 Generate a CTFd admin token

`Admin > Settings > Access Tokens > Generate`. Add to `.env` :

```
CTFD_URL=http://127.0.0.1:8000
CTFD_ADMIN_TOKEN=ctfd_xxxxxxxxxxxxxxxxxxxxxxxx
CTFD_PENALTY_FORMULA=mirror_juicelab
CTFD_TEAM_MODE=team
```

### 3.4 Align the HMAC keys

Three files share the same secret. They must match :

| File | Read by |
|---|---|
| `juice-shop/ctf.key` | `juice-shop/lib/utils.ts` (Juice Shop core flag generation) |
| `docker/.env` `JUICESHOP_CTF_SECRET` | `dashboard/app.py /api/verify-flag` |
| `juicelab-ctfd.yml` `ctfKey` | `juice-shop-ctf-cli` (writes the hash into the imported CSV) |

**Canary test** : for `challenge.name = "Score Board"` with the default `ctf.key` of this repo, the expected HMAC-SHA-1 is `2614339936e8282e2f820f023d4d998a1f95e02a`. If the dashboard returns `{valid: false}` for a flag the student copied verbatim, this is the alignment to check.

### 3.5 Pre-provision CTFd teams

For every student, create a CTFd team with :

- `affiliation: <COHORT_ID>` (e.g. `M2-IA-2026`)
- `email: <the email the student used for the Juice Shop registration>`

The dashboard uses `email` as the bridge identifier : it extracts the email from the JWT in the `juicelab-sync` payload, calls `GET CTFD/api/v1/teams`, and matches by email. Students without a CTFd team are silently skipped (the push retries at the next event).

### 3.6 Restart the dashboard

```powershell
docker compose --env-file .env restart dashboard
docker compose logs dashboard | grep -i ctfd
```

Expected : `CTFd push enabled (Mode C)`.

### 3.7 Monitor

```powershell
curl -H "X-Teacher-Token: $env:DASHBOARD_TEACHER_TOKEN" `
     http://127.0.0.1:5050/api/admin/ctfd-status

# {
#   "enabled": true,
#   "ctfd_url": "http://127.0.0.1:8000",
#   "team_mode": "team",
#   "penalty_formula": "mirror_juicelab",
#   "teams_mapped": 12,
#   "pending_pushes": 0,
#   "last_error": null
# }
```

### 3.8 Reconcile (if CTFd was offline)

```powershell
curl -X POST -H "X-Teacher-Token: $env:DASHBOARD_TEACHER_TOKEN" `
     http://127.0.0.1:5050/api/admin/reconcile-awards
# { "retried": N, "succeeded": M, "failed": K }
```

Detailed Mode C troubleshooting : see [`docs/CTF-INTEGRATION.md`](./docs/CTF-INTEGRATION.md).

---

## 4. Native dev (Windows / macOS / Linux without Docker)

For contributors who edit the overlay or the dashboard.

### 4.1 Boot Juice Shop

```powershell
cd juice-shop
npm install
$env:TEACHER_ADMIN_TOKEN = "<32 random chars>"
$env:DASHBOARD_PROOF_SECRET = "<32 random chars>"
npm start
# listening on port 3000
```

### 4.2 Boot the dashboard

```powershell
cd dashboard
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DASHBOARD_TEACHER_TOKEN = "<same 32 chars as above>"
$env:DASHBOARD_PROOF_SECRET = "<same as TEACHER_ADMIN_TOKEN>"
$env:DASHBOARD_DEFAULT_COHORT = "M2-IA-2026"
python app.py
# listening on http://0.0.0.0:5050
```

### 4.3 Or use the launcher

```powershell
cd <repo root>
.\juice.ps1 start          # boots both
.\juice.ps1 status
.\juice.ps1 logs shop      # tail Juice Shop log
.\juice.ps1 health         # curl /health on both
.\juice.ps1 stop
```

### 4.4 Run the tests

```powershell
cd dashboard
python -m pytest tests/ -v
# 10 tests should pass (hermetic SQLite per test)

cd ../juice-shop/frontend
npm run build              # the Angular overlay must build green
npm run test               # Karma unit tests
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `dashboard unhealthy` after `docker compose up` | `DASHBOARD_TEACHER_TOKEN` < 16 chars | Set 32+ chars in `.env` |
| Coach overlay shows `Dashboard URL non configuree` | Frontend `config.json` missing or `JUICELAB_DASHBOARD_URL` not exported | Check `frontend/src/assets/juicelab/config.json` is generated by `entrypoint.sh` ; check `.env` has `JUICELAB_DASHBOARD_URL=http://dashboard:5000` |
| Events do not arrive in the dashboard | CORS rejects | Ensure `DASHBOARD_CORS_ORIGINS` lists every student port, exactly the value `provision.py --print-cors` produced |
| Hint level 3 returns 403 | Server-side gating refuses N+1 before N is consumed | Click hints in order N1 → N2 → N3 |
| Walkthrough returns 403 | Challenge not yet solved | Solve the challenge first, then the walkthrough opens |
| Flag verification returns `{valid: false}` | `JUICESHOP_CTF_SECRET` (dashboard) != `ctf.key` (Juice Shop) | Re-run the canary test in 3.4 |
| Score board has no **TD** button | The patch was not applied | Confirm `juice-shop/frontend/src/app/score-board/components/challenge-card/` includes the JuiceLab modifications |
| `juicelab-amelie` container fails to start | port `3001` already taken | Pass a different `--port-base` to `provision.py` |
| Build is very slow on the first run (~ 10 min) | `npm install` inside the Dockerfile | Normal — subsequent builds use the layer cache |

For anything not listed, open a Discussion or an Issue.

---

## Next steps

- Read [`ARCHITECTURE.md`](./ARCHITECTURE.md) to understand the data flow.
- Read [`docs/PEDAGOGY.md`](./docs/PEDAGOGY.md) to understand the why.
- Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) before opening a PR.
