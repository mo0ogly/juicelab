# Student install guide — JuiceLab

> Goal: get a working JuiceLab instance on your laptop in **5 to 10 minutes**, with the OWASP Juice Shop on `http://127.0.0.1:3000` and the teacher dashboard on `http://127.0.0.1:5000`.

> Localized version: [STUDENT-INSTALL-FR.md](./STUDENT-INSTALL-FR.md) (français).

---

## 1. What you will install

A single Docker stack with three containers :

| Container | Port | What it does |
|---|---|---|
| `juicelab-juiceshop` | 3000 | OWASP Juice Shop + the JuiceLab pedagogical overlay (`/#/juicelab`) |
| `juicelab-dashboard` | 5000 | Teacher dashboard (cohort matrix, hint usage, journal preview) |
| `juicelab-db` | internal | SQLite volume holding the event log |

The first build downloads ~700 MB and takes 5 to 8 minutes. After that, every `docker compose up` is roughly 10 seconds.

No data leaves your laptop. The dashboard runs locally on `127.0.0.1` only.

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

#### Linux / macOS — `bash`

```bash
./scripts/install-student.sh -c M2-IA-2026
```

Replace `M2-IA-2026` with the cohort identifier your teacher gave you. If you do not pass `-c`, the script asks you for it interactively.

If the script is not executable yet :

```bash
chmod +x scripts/install-student.sh
./scripts/install-student.sh -c M2-IA-2026
```

#### Windows — PowerShell 7+

```powershell
.\scripts\install-student.ps1 -Cohort M2-IA-2026
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
3. Generates two random 32-character secrets (`TEACHER_ADMIN_TOKEN`, `DASHBOARD_TEACHER_TOKEN`) using `openssl rand -hex 16` (or .NET's RNG on Windows if OpenSSL is missing).
4. Writes `JUICELAB_COHORT_ID` based on `-c <cohort>`, the env file, or an interactive prompt.
5. Runs `docker compose --env-file .env up -d --build`.
6. Polls `http://127.0.0.1:3000/` and `http://127.0.0.1:5000/api/health` until both answer.
7. Prints the URLs and the two teacher tokens.

The installer is **idempotent** : re-running it does not regenerate tokens that are already valid. If you want a clean reinstall, add `--reset` (bash) or `-Reset` (PowerShell).

### 3.4 Other modes

| Command | Effect |
|---|---|
| `./scripts/install-student.sh` | interactive, asks for cohort_id |
| `./scripts/install-student.sh -y` | non-interactive, takes all defaults (cohort = `M2-IA-2026`) |
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
| <http://127.0.0.1:5000/login> | Dashboard login page |
| <http://127.0.0.1:5000/api/health> | `{"ok": true}` |

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

If any of those fail, see § 6 below.

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
