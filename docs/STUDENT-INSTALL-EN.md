# Student install guide — JuiceLab

> Goal: get OWASP Juice Shop + the JuiceLab overlay working on your laptop in **5 to 10 minutes**, on `http://127.0.0.1:3000`.

> Localized version: [STUDENT-INSTALL-FR.md](./STUDENT-INSTALL-FR.md) (français).

---

## 0. Pick your mode BEFORE installing

There are **two modes** and they install differently. Read this table first.

| Your situation | Mode | What you run | The teacher dashboard ? |
|---|---|---|---|
| **Lab with a teacher** (normal case) | **Cohort** | Juice Shop **only** ; your events are pushed to the teacher's dashboard | **NO, you do NOT install it.** The teacher hosts it. |
| You work **alone, no teacher** (revision, self-study) | **Solo** | Juice Shop **+** your own local dashboard | Yes, locally on `127.0.0.1:5050` |

> **WARNING — common mistake.** During a lab, **do not install the dashboard on your laptop**. Every student who runs their own dashboard ends up isolated: the teacher cannot see your progress in the cohort matrix. Use the **cohort mode** (command with `-d`, section 3.2) and ask your teacher for the **teacher dashboard IP**.

---

## 1. What you will install

| Container | Port | What it does | Installed in mode... |
|---|---|---|---|
| `juicelab-juiceshop` | 3000 | OWASP Juice Shop + the JuiceLab pedagogical overlay (`/#/juicelab`) | Cohort **and** Solo |
| `juicelab-dashboard` | 5000 | Teacher dashboard (cohort matrix, hint usage, journal preview) | **Solo only** |
| `juicelab-db` | internal | SQLite volume holding the event log | Solo only |

In **cohort mode**, only `juicelab-juiceshop` runs on your machine ; your events are pushed to the teacher's dashboard (so you have no dashboard container and no local database).

The first build downloads ~700 MB and takes 5 to 8 minutes. After that, every `docker compose up` is roughly 10 seconds.

No sensitive data leaves your laptop beyond the progression events sent to the teacher dashboard you point to.

---

## 2. Prerequisites

| Tool | Minimum version | Where to get it |
|---|---|---|
| **Docker Desktop** (Windows / macOS) or **Docker Engine** (Linux) | 24+ | <https://www.docker.com/products/docker-desktop> |
| **Docker Compose v2** | bundled with Docker Desktop ; on Linux : `sudo apt install docker-compose-v2` (distro) or `docker-compose-plugin` (official Docker repo) — see Appendix A | — |
| **Git** | any recent version | <https://git-scm.com/downloads> |
| **OpenSSL** | bundled with Git for Windows, macOS, all Linux distros | — |
| **RAM** | 4 GB free | — |
| **Disk** | 3 GB free | — |

Quick sanity check :

```bash
docker --version            # Docker version 24.x or newer
docker compose version      # Docker Compose v2.x or newer
git --version
openssl version             # any output is fine
```

If `docker compose version` errors out, your Docker is too old. On Linux : `sudo apt install docker-compose-v2` (Ubuntu/Debian standard) or `sudo apt install docker-compose-plugin` (official Docker repo). On Windows / macOS : update Docker Desktop.

---

## 3. One-shot install (recommended)

Same flow on Linux, macOS, and Windows.

### 3.1 Clone the repo

```bash
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab
```

### 3.2 Run the installer

Replace `M2-IA-2026` with the cohort identifier your teacher gave you, and `192.168.1.10` with the **teacher dashboard IP** they gave you. If you do not pass `-c`, the script asks for the cohort interactively.

#### Cohort mode — lab with a teacher (recommended)

Juice Shop only, events pushed to the teacher dashboard. **You do not install a dashboard.**

```bash
# Linux / macOS
./scripts/install-student.sh -c M2-IA-2026 -d 192.168.1.10
```

```powershell
# Windows PowerShell 7+
.\scripts\install-student.ps1 -Cohort M2-IA-2026 -Dashboard 192.168.1.10
```

> **Teacher dashboard port.** Default `5050`. If your teacher exposes a different port (often `5000`), append it to the address : `-d 192.168.1.10:5000` (or `-Dashboard 192.168.1.10:5000`). The event-push URL will follow that port.

#### Solo mode — no teacher (self-study)

Installs Juice Shop **and** a local dashboard on `127.0.0.1:5050`. Only use this if you work alone.

```bash
# Linux / macOS
./scripts/install-student.sh -c M2-IA-2026
```

```powershell
# Windows PowerShell 7+
.\scripts\install-student.ps1 -Cohort M2-IA-2026
```

If the bash script is not executable yet :

```bash
chmod +x scripts/install-student.sh
```

If PowerShell complains about execution policy, run once :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

then retry the command.

> **PowerShell 7+ is required.** Windows 10 ships with PowerShell 5.1 which is too old. Install PowerShell 7 from <https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows>.

### 3.3 What the installer does

In order :

1. Verifies that Docker, Docker Compose, and OpenSSL are available.
2. Copies `docker/.env.example` into `docker/.env` if it does not exist yet.
3. Generates three random 32-character secrets (`TEACHER_ADMIN_TOKEN`, `DASHBOARD_TEACHER_TOKEN`, `DASHBOARD_PROOF_SECRET`) using `openssl rand -hex 16` (or .NET's RNG on Windows if OpenSSL is missing).
4. Writes `JUICELAB_COHORT_ID` based on `-c <cohort>`, the env file, or an interactive prompt, and `JUICELAB_INSTANCE_LABEL` based on `-l`. This label is the **name of your machine** as seen by the teacher in the cohort matrix — it is independent of the Juice Shop account you will create afterwards.
5. In cohort mode (`-d HOST`), writes `DASHBOARD_PUBLIC_HOST` = the teacher dashboard IP, then runs `docker compose up -d --build juicelab-demo` (Juice Shop only). In solo mode, runs `docker compose up -d --build` (Juice Shop + local dashboard).
6. Polls `http://127.0.0.1:3000/` (and, in solo mode, `http://127.0.0.1:5050/api/health`) until it answers.
7. Prints the URLs and the tokens.

The installer is **idempotent** : re-running it does not regenerate tokens that are already valid. If you want a clean reinstall, add `--reset` (bash) or `-Reset` (PowerShell).

### 3.4 Other modes

| Command | Effect |
|---|---|
| `./scripts/install-student.sh -c COHORT -d TEACHER_IP[:PORT]` | **cohort mode** : Juice Shop only, events to the teacher dashboard at `TEACHER_IP` (port `5050` by default, `:5000` or other if specified) |
| `./scripts/install-student.sh -c COHORT` | **solo mode** : Juice Shop + local dashboard on `127.0.0.1:5050` |
| `./scripts/install-student.sh` | interactive, asks for cohort_id (solo mode) |
| `./scripts/install-student.sh -y` | non-interactive, takes all defaults (cohort = `M2-IA-2026`, solo mode) |
| `./scripts/install-student.sh --reset` | `docker compose down -v` + reinstall from scratch (wipes events) |
| `.\scripts\install-student.ps1 -Yes` | same, PowerShell |
| `.\scripts\install-student.ps1 -Reset` | same, PowerShell |

---

## 4. Verify the install

Open these URLs in your browser :

| URL | Expected |
|---|---|
| <http://127.0.0.1:3000/#/score-board> | Juice Shop score-board with a **TD** button on each of the 13 selected challenge cards |
| <http://127.0.0.1:3000/#/juicelab> | "Log in to Juice Shop" screen (normal before login) |
| `http://<DASHBOARD>:5050/login` | Dashboard login page |
| `http://<DASHBOARD>:5050/api/health` | `{"ok": true}` |

> **`<DASHBOARD>` = which address ?** In **solo mode** it is `127.0.0.1` (the dashboard runs on your laptop). In **cohort mode** the dashboard is **remote**: use the **teacher server IP** (`-d <IP>`), never `127.0.0.1`. Your Juice Shop always stays on `127.0.0.1:3000`. The dashboard host port is **5050** by default (`5000` is only the container-internal port).

> **`/#/juicelab` shows "Log in to Juice Shop"?** That is expected. The JuiceLab panel is only shown to authenticated users. Follow the smoke test below — the panel appears as soon as you are logged in.

> **`!!! Teacher dashboard unreachable` during install?** Also expected if the teacher has not started their dashboard yet, or if you are not on the same network. The install is still successful: events will be pushed as soon as the dashboard becomes available.

End-to-end smoke test :

1. Register an account on Juice Shop (`/#/register`).
2. Solve **Score Board** (find the link in the page source — `Ctrl+U`).
3. Click **TD** on the Score Board card.
4. In the dialog, fill the *After* journal (a few sentences explaining how you solved it).
5. Paste the flag, click **Verify**.
6. Log in to the dashboard (`/login`, paste `DASHBOARD_TEACHER_TOKEN` from the installer recap).
7. Open `/dashboard?cohort=<your-cohort>`. You should see your row with `solved`, `journal`, `quiz`, `flag verified`.

Once logged in, the pedagogical Coach panel shows up on `/#/juicelab` (briefing, graded hints, quiz, badges) :

![Student-side pedagogical Coach panel](img/student-overlay.png)

If any of those fail, see § 6 below.

> **Two separate identities**
>
> | Identifier | Source | Role |
> |---|---|---|
> | **Label** (`-l fabrice`) | `docker/.env`, set by the teacher at install time | Identifies **your machine** in the teacher's cohort matrix — fixed, independent of Juice Shop |
> | **Juice Shop email** | Account you create on `/#/register` | Unlocks the JuiceLab panel — can be any address |
>
> The teacher sees column `fabrice` in the cohort matrix. The Juice Shop account email is never shown in standard TD mode (scenario 4).

Two options for the Juice Shop account:
- **Fake email**: `fabrice@juicelab.local` or any address in `x@y.z` format — Juice Shop never verifies that the address exists.
- **Google login**: the "Login with Google" button works on `127.0.0.1:3000`. OWASP ships a proxy (`local3000.owasp-juice.shop`) that intercepts the OAuth callback and redirects it to localhost. Your real Google account email will then be used as the Juice Shop identifier.

---

## 5. Daily use

Once installed, you do **not** need to re-run the installer. The stack persists across reboots :

```bash
# Start / resume
cd juicelab/docker
docker compose --env-file .env up -d

# Stop (keeps your event history)
docker compose --env-file .env down

# Tail logs (helpful when something looks broken)
docker compose --env-file .env logs -f

# Full reset (wipes the database — start over)
docker compose --env-file .env down -v
```

Your Juice Shop progress, journals, and quiz answers are stored client-side in `localStorage` (key `juicelab_state_v1`). They survive container restarts but **not** a `docker compose down -v` (because the dashboard DB is wiped too).

---

## 6. Troubleshooting

### Port already in use (`3000` or `5000`)

Another app is squatting the port. Either stop it, or change the host port mapping in `docker/docker-compose.yml` and rebuild.

### `docker compose: command not found`

Your Docker is too old or Compose plugin is missing.
- Linux (Ubuntu/Debian standard) : `sudo apt install docker-compose-v2`
- Linux (official Docker repo) : `sudo apt install docker-compose-plugin`
- Windows / macOS : update Docker Desktop to the latest version.

> **Note:** the two packages are mutually exclusive — do not install both. On Ubuntu 25.04 and later, use `docker-compose-v2`.

### `permission denied` on the script (Linux / macOS)

```bash
chmod +x scripts/install-student.sh
```

### PowerShell : *"running scripts is disabled on this system"*

Once per user :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### The build fails on `flag-icons` SVG duplicates

This bug was patched on the repo side (see `overlay/frontend/src/assets/flag-icons-patched.min.css`). If you still hit it, you cloned an old revision : `git pull` and re-run the installer with `--reset`.

### The build fails: `patch does not apply` (Windows / line endings)

Symptom — the build stops at the `git apply` step with, on many files:

```
error: patch failed: config/default.yml:458
error: config/default.yml: patch does not apply
```

Cause — you are on **Windows** and Git rewrote the patch line endings to CRLF
(`core.autocrlf=true` by default). The CRLF patch does not apply to Juice Shop's
LF sources inside the Linux build container. macOS / Linux are unaffected.

Fix — the repo now pins LF line endings (`.gitattributes`). **Re-clone cleanly**
to get the files in the right format:

```powershell
cd ..
Remove-Item -Recurse -Force juicelab
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab
.\scripts\install-student.ps1 -Dashboard 187.124.39.123 -Cohort JUICELAB-JUIN-2026 -Label PRENOM
```

If the error persists after re-cloning, force the Git config BEFORE re-cloning:

```powershell
git config --global core.autocrlf false
```

### Dashboard returns 401 / 403

The token in your browser cookie does not match the one in `docker/.env`. Open `docker/.env`, copy the value of `DASHBOARD_TEACHER_TOKEN`, log in again at `/login`.

### Containers crash-loop

```bash
cd juicelab/docker
docker compose --env-file .env logs --tail=200 juiceshop
docker compose --env-file .env logs --tail=200 dashboard
```

Send the last 50 lines of the failing container to your teacher.

### I lost my teacher tokens

```bash
grep TOKEN juicelab/docker/.env
```

Tokens are stored there in plain text on your laptop. If you want to rotate them : delete the lines from `docker/.env` and re-run the installer — it will regenerate fresh ones.

### Dashboard does not receive my events (CORS `X-User-Email` error) or proof / flag check returns 503

Symptoms in the browser console :

- `Request header field X-User-Email is not allowed by Access-Control-Allow-Headers`
- `Proof download failed: HTTP 503 (proof signing disabled)`

These are bugs fixed in a recent version of the repo. Update your clone and re-run the installer in **your usual mode** (it is idempotent: it adds the missing proof secret and re-applies the fixes without touching your existing tokens) :

```bash
cd juicelab
git pull
# same arguments as your initial install :
./scripts/install-student.sh -c M2-IA-2026 -d 192.168.1.10   # cohort mode
# or, in solo mode :
./scripts/install-student.sh -c M2-IA-2026
```

> **Cohort mode:** the 503 proof error comes from the **teacher's dashboard**, not yours (you have no local dashboard). Report it to your teacher — they must set `DASHBOARD_PROOF_SECRET` server-side. The CORS error is fixed on the teacher dashboard after their `git pull`.

CORS check (the header must show up in the queried dashboard's response) :

```bash
curl -s -i -X OPTIONS http://<DASHBOARD_IP>:5050/api/sync \
  -H 'Origin: http://127.0.0.1:3000' \
  -H 'Access-Control-Request-Headers: X-User-Email' | grep -i allow-headers
```

Note : CTF flag verification stays disabled until `JUICESHOP_CTF_SECRET` is set in the dashboard's `docker/.env` (sync and proof work without it). Ask your teacher for the key if the exercise requires flag verification.

---

## 7. Uninstall

```bash
cd juicelab/docker
docker compose --env-file .env down -v   # stop containers + delete volumes
cd ../..
rm -rf juicelab                          # delete the cloned repo
docker image prune                       # optional, free disk
```

---

## 8. Where to ask for help

- Open an issue at <https://github.com/mo0ogly/juicelab/issues> with :
  - your OS + Docker Desktop version
  - the last 50 lines of `docker compose logs`
  - the exact command that failed and its full output

Your teacher and `gabrielhociel@gmail.com` are the maintainers.

---

## Appendix A — Installing Docker and Docker Compose on Linux

Two **mutually exclusive** methods. Pick one OR the other.

### Method A — distribution packages (recommended for a lab)

```bash
sudo apt update
sudo apt install -y docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker   # or log out and back in
docker compose version
```

`docker-compose-v2` pulls `docker.io` as a dependency: a single command installs everything. This is the pragmatic choice for a student laptop — version freshness does not matter here.

### Method B — official Docker repository (if you need the latest version)

```bash
# Set up the official repository first: https://docs.docker.com/engine/install/ubuntu/
sudo apt install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

> **Pitfall:** if you already ran Method A, remove it first: `sudo apt remove docker-compose-v2 docker.io`

### Verification (both methods)

```bash
docker run --rm hello-world
docker compose version
```

### arm64 note (Apple Silicon / Snapdragon)

On arm64 machines (Qualcomm X1E, Apple M1/M2/M3), Docker builds may fail with `E: Dynamic MMap ran out of room`. This is a known issue: the Debian bullseye package list is too large for the default APT cache. The project's `Dockerfile.juicelab` already includes the fix (`APT::Cache-Start "100663296"`). If you encounter this on another Dockerfile, the solution is:

```dockerfile
RUN printf 'APT::Cache-Start "100663296";\n' > /etc/apt/apt.conf.d/70cache \
 && apt-get update \
 && apt-get install -y --no-install-recommends <package> \
 && rm -rf /var/lib/apt/lists/* /etc/apt/apt.conf.d/70cache
```
