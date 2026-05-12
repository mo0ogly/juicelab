# Teacher guide — install and operate the JuiceLab dashboard

> Version française : [TEACHER-DASHBOARD-FR.md](./TEACHER-DASHBOARD-FR.md).

> Audience: a teacher who wants to deploy the JuiceLab dashboard on their own machine (laptop, VM, or VPS) to follow a student cohort in real time.

> Student-side install: [STUDENT-INSTALL-EN.md](./STUDENT-INSTALL-EN.md).

---

## 1. What the dashboard does

The JuiceLab dashboard is a Flask service (default port `5000`) that :

- ingests events POSTed by student JuiceLab overlays (challenge solved, hints consumed, journal written, quiz answered, flag verified)
- aggregates them in a local SQLite file (`data/dashboard.sqlite`)
- exposes a cohort matrix (who did what) as HTML + JSON + CSV
- manages cohorts (create, rename, delete, purge orphans)
- cryptographically verifies flags (HMAC-SHA256 with a secret shared between Juice Shop and the dashboard)

No student accesses the dashboard : everything is gated by a `teacher_token` cookie issued from `DASHBOARD_TEACHER_TOKEN`.

---

## 2. Prerequisites

| Tool | Min version | Notes |
|---|---|---|
| Docker Desktop / Docker Engine | 24+ | recommended for production |
| Docker Compose v2 | bundled | otherwise `sudo apt install docker-compose-plugin` |
| OR Python | 3.10+ | for `python3 app.py` direct (dev / debug) |
| OpenSSL | bundled everywhere | for token generation |
| Network | students must reach `http://<YOUR_IP>:<PORT>` | classroom LAN, VPN, or public VPS |
| RAM | 100 MB free | dashboard alone is very light |

---

## 3. Install — recommended path (Docker)

This is the only maintained path. `python3 app.py` direct = dev / debug only.

### 3.1 Clone

```bash
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab
```

### 3.2 Generate `docker/.env` with strong tokens

The student installer also works for teachers — it bootstraps `.env` cleanly :

```bash
./scripts/install-student.sh -c <COHORT_NAME>
# e.g. ./scripts/install-student.sh -c ANSSI
```

What it does for your dashboard :

- copies `docker/.env.example` → `docker/.env`
- generates `TEACHER_ADMIN_TOKEN` + `DASHBOARD_TEACHER_TOKEN` via `openssl rand -hex 16` (32 chars)
- preserves any token already valid (idempotent)
- runs `docker compose --env-file .env up -d --build`
- waits for `http://127.0.0.1:3000/` and `http://127.0.0.1:5000/api/health`
- prints both tokens in the recap

> **Note: the installer ALSO starts a local Juice Shop**, since it's designed for a student laptop. If you only want the dashboard on the teacher machine (no second Juice Shop), edit `docker/docker-compose.yml` and comment the `juiceshop` service BEFORE running the script.

### 3.3 Verify

```bash
curl http://127.0.0.1:5000/api/health
# expected: {"ok": true, "ts": "..."}

grep DASHBOARD_TEACHER_TOKEN docker/.env
# paste the value into http://127.0.0.1:5000/login
```

---

## 4. Alternative install — Python direct (dev / debug only)

```bash
cd dashboard
pip install -r requirements.txt
export DASHBOARD_TEACHER_TOKEN="$(openssl rand -hex 16)"
export DASHBOARD_PROOF_SECRET="$(openssl rand -hex 16)"
export DASHBOARD_PORT=5050
python3 app.py
```

⚠️ **Classic pitfall**: if you launch `python3 app.py` by hand, **the process does NOT use `docker/.env`**. `docker/.env` is read only by `docker compose --env-file`. A `grep DASHBOARD_TEACHER_TOKEN docker/.env` will give you ONE token, but the Python process will run with ANOTHER (the one you `export`ed in the shell that launched it).

To check what the process actually runs with :

```bash
PID=$(pgrep -f "python3.*app.py")
cat /proc/$PID/environ | tr '\0' '\n' | grep DASHBOARD_TEACHER_TOKEN
```

That value is the one to paste into `/login`.

---

## 5. Full env var reference

All read by `dashboard/app.py`. Put them in `docker/.env` (Docker) or export them in the shell (Python direct).

| Variable | Default | Use |
|---|---|---|
| **`DASHBOARD_TEACHER_TOKEN`** | (empty → 503) | teacher login secret. Min 16 chars, otherwise the dashboard refuses to boot |
| **`DASHBOARD_PROOF_SECRET`** | (empty → flag verification disabled) | HMAC-SHA256 secret to sign flag proofs |
| `JUICESHOP_CTF_SECRET` | (empty) | CTF secret on the Juice Shop side, must match if you enable flag verification |
| `DASHBOARD_DB` | `./data/dashboard.sqlite` | SQLite file path |
| `DASHBOARD_PORT` | `5000` | HTTP port |
| `DASHBOARD_BIND` | `0.0.0.0` | listen interface. **Production: `127.0.0.1` + reverse proxy** |
| `DASHBOARD_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | origins allowed to POST (add student ports if different) |
| `DASHBOARD_DEFAULT_COHORT` | (empty) | cohort shown when `?cohort=` is missing |
| `DASHBOARD_LOG_LEVEL` | `INFO` | Python logging (DEBUG/INFO/WARNING/ERROR) |
| `DASHBOARD_HTTPS` | `false` | if `true`: `Secure` cookies + HSTS header |
| `TEACHER_ADMIN_TOKEN` | — | Juice Shop admin secret (purge instances, reset accounts) |
| `JUICELAB_COHORT_ID` | — | default cohort on the Juice Shop overlay side |
| `JUICELAB_DEFAULT_LANGUAGE` | `fr` | overlay UI language |

---

## 6. Persist the dashboard with systemd (LAN / multi-day course)

So that the dashboard survives reboots and restarts on its own, create a systemd user service.

A ready-to-edit template ships at [`scripts/juicelab-dashboard.service`](../scripts/juicelab-dashboard.service). Install it :

```bash
mkdir -p ~/.config/systemd/user
cp scripts/juicelab-dashboard.service ~/.config/systemd/user/
# Edit if your repo lives somewhere other than /home/fpizzi/juice :
$EDITOR ~/.config/systemd/user/juicelab-dashboard.service

systemctl --user daemon-reload
systemctl --user enable --now juicelab-dashboard.service
loginctl enable-linger $USER          # so the service runs even with no open session
journalctl --user -u juicelab-dashboard -f
```

The unit reads `EnvironmentFile=/home/fpizzi/juice/docker/.env`, so `DASHBOARD_TEACHER_TOKEN`, `DASHBOARD_PORT`, etc. stay in a single source of truth.

⚠️ Without `EnvironmentFile=`, systemd would NOT read `docker/.env` — the service would start without a token and give you a 503 on `/login`.

If you prefer the Docker path : replace `ExecStart` and `WorkingDirectory` to call `docker compose --env-file .env up dashboard`.

---

## 7. Network — exposing the dashboard to students

Students must reach `http://<YOUR_IP>:<PORT>`. Three cases :

### Case 1: physical classroom LAN

```bash
hostname -I        # your IP, e.g. 10.200.192.6
```

Make sure the firewall opens the port :

```bash
sudo ufw allow 5050/tcp                                  # Ubuntu/Debian
# or: sudo firewall-cmd --add-port=5050/tcp --permanent && sudo firewall-cmd --reload   # Fedora/RHEL
```

Test from a student laptop :

```bash
curl http://10.200.192.6:5050/api/health
```

### Case 2: VPN (remote students)

You publish on the VPN, students must be on it. Use the VPN IP, not the LAN IP.

### Case 3: public VPS

Read [`docs/VPS_HARDENING.md`](./VPS_HARDENING.md) (HSTS, nginx + Let's Encrypt reverse proxy, `DASHBOARD_BIND=127.0.0.1`). NEVER expose raw Flask on the public internet.

---

## 8. Verify students are arriving

Once your dashboard is up and the message has been sent to students :

```bash
# list ingested events (events table)
docker exec juicelab-dashboard \
  sqlite3 /app/data/dashboard.sqlite \
  "SELECT cohort_id, COUNT(*) FROM events GROUP BY cohort_id;"

# tail logs to see live POSTs
cd docker
docker compose --env-file .env logs -f dashboard
```

UI :
- `/admin/cohorts` — list / create / purge cohorts
- `/admin/students?cohort=ANSSI` — matrix with one row per student
- `/dashboard?cohort=ANSSI` — aggregate view
- `/api/cohorts/ANSSI/csv` — CSV export (auth via `X-Teacher-Token: <token>` header)

---

## 9. Cohort management — typical workflow

### Create a cohort

No need to create it manually : the cohort is created automatically on the first event a student POSTs with `cohort_id: "ANSSI"`. You can also pre-create via `/admin/cohorts` or :

```bash
curl -X POST -H "X-Teacher-Token: <TOKEN>" -H "Content-Type: application/json" \
  -d '{"cohort_id":"ANSSI","label":"M2 ANSSI 2026"}' \
  http://127.0.0.1:5000/api/cohorts
```

Accepted `cohort_id` format : `[a-zA-Z0-9_.-]{1,64}`.

### Approve / block a student (optional)

By default, any `student_token` POSTing an event for a known cohort is accepted (implicit `validated` status).

You can enable the manual approval workflow : see `docs/COHORT_WORKFLOW.md`.

### Purge orphans (test students)

```bash
curl -X POST -H "X-Teacher-Token: <TOKEN>" \
  http://127.0.0.1:5000/api/cohorts/ANSSI/purge-orphans
```

Removes events from student_tokens that are not present in the `students` table (useful after testing).

### Full cohort reset

```bash
curl -X POST -H "X-Teacher-Token: <TOKEN>" \
  http://127.0.0.1:5000/api/cohorts/ANSSI/reset
```

⚠️ **Irreversible.** Wipes events + students for this cohort.

---

## 10. Security — checklist before a real lab

- [ ] `DASHBOARD_TEACHER_TOKEN` ≥ 32 chars, randomly generated (`openssl rand -hex 16`). **NEVER** `change-me-please-1234567890` (test placeholder).
- [ ] `DASHBOARD_PROOF_SECRET` set if you use flag verification.
- [ ] `JUICESHOP_CTF_SECRET` matches the one in Juice Shop on the student side (if flag verify is on).
- [ ] `DASHBOARD_BIND=127.0.0.1` + reverse proxy if exposing on a public VPS.
- [ ] `DASHBOARD_HTTPS=true` behind a TLS reverse proxy.
- [ ] Firewall opens ONLY the port students must reach.
- [ ] `.env` in `.gitignore` (already done, double-check `git status` after editing).
- [ ] Regular backup of `data/dashboard.sqlite` (Docker volume `juicelab_dashboard_db`) before the lab ends.

---

## 11. DB backup / restore

```bash
# backup (hot, SQLite supports concurrent readers)
docker exec juicelab-dashboard \
  sqlite3 /app/data/dashboard.sqlite ".backup '/tmp/db.backup'"
docker cp juicelab-dashboard:/tmp/db.backup ./dashboard-$(date +%Y%m%d-%H%M).sqlite

# restore
docker cp ./dashboard-20260512-1430.sqlite juicelab-dashboard:/app/data/dashboard.sqlite
docker compose --env-file .env restart dashboard
```

---

## 12. Troubleshooting

### `/login` gives 503 "Dashboard disabled"

`DASHBOARD_TEACHER_TOKEN` not set or < 16 chars in the process env. See § 4 pitfall.

### The token from `docker/.env` does not work

You launched `python3 app.py` directly → that process ignores `docker/.env`. Check via `cat /proc/$PID/environ | tr '\0' '\n' | grep TOKEN`.

### Students see `CORS error`

Add their origin to `DASHBOARD_CORS_ORIGINS` (comma-separated) in `docker/.env`, then :

```bash
docker compose --env-file .env restart dashboard
```

### Students see `403 join not approved`

You enabled the manual approval workflow and have not validated the student. Either approve via `/admin/students`, or disable the workflow (see `docs/COHORT_WORKFLOW.md`).

### Dashboard container crash-loop

```bash
docker compose --env-file .env logs --tail=200 dashboard
```

Common cause: `DASHBOARD_TEACHER_TOKEN` < 16 chars → fail-fast at boot.

---

## 13. Going further

- [`docs/COHORT_WORKFLOW.md`](./COHORT_WORKFLOW.md) — manual approval workflow
- [`docs/CLASSROOM-DEPLOYMENT.md`](./CLASSROOM-DEPLOYMENT.md) — multi-laptop classroom deployment
- [`docs/CTF-INTEGRATION.md`](./CTF-INTEGRATION.md) — CTFd integration (Mode C)
- [`docs/SECURITY_POSTURE.md`](./SECURITY_POSTURE.md) — threat model + mitigations
- [`docs/THREAT_MODEL.md`](./THREAT_MODEL.md) — formal analysis
- [`docs/VPS_HARDENING.md`](./VPS_HARDENING.md) if you deploy on the public internet
