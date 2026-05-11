# VPS hardening — deploy JuiceLab dashboard on the public internet

This guide walks through deploying the JuiceLab teacher dashboard
(Flask + SQLite) on a single VPS exposed via a public domain
(e.g. `juice.tonprof.fr`). It assumes a single-tenant install : one
teacher, one VPS, many students hitting the same dashboard.

Scope : **dashboard only**. Juice Shop itself runs **on each student's
laptop** in local mode and pushes events over HTTPS to the dashboard.
The dashboard is the only public surface.

> **Audience** : operators with sudo on a fresh Ubuntu 22.04+ VPS.
> Read end-to-end before running any command. If you only have one
> VPS and one cohort, no automation script is provided ; copy-paste
> the snippets in the listed order.

## 0. Threat model in two sentences

The dashboard token (`DASHBOARD_TEACHER_TOKEN`) is the single line of
defense for the teacher-facing surface. The student-facing surface
(`/api/cohort/join`, `/api/student/status`, `/api/sync`) is public by
design but rate-limited and gated server-side on the per-student
`status` column ; an attacker who knows a cohort code can flood
pending join requests, so we rate-limit at the reverse-proxy level.

## 1. VPS prerequisites

| Item | Value |
|---|---|
| OS | Ubuntu 22.04+ or Debian 12+ (`apt`-based) |
| CPU / RAM | 2 vCPU / 2 GB RAM minimum |
| Disk | 20 GB minimum (SQLite + backups) |
| Network | Public IPv4. IPv6 if available. |
| DNS | An `A` (and optionally `AAAA`) record `juice.tonprof.fr` pointing at the VPS, propagated before step 4 |
| SSH | Key-only auth (no password), non-root sudo user |
| Snapshots | At least one snapshot before first deploy (rollback option if hardening breaks something) |

## 2. Create the unprivileged service user

```bash
sudo useradd -r -m -d /opt/juicelab -s /bin/bash juicelab
sudo install -d -o juicelab -g juicelab -m 0750 /opt/juicelab
sudo install -d -o juicelab -g juicelab -m 0750 /var/lib/juicelab
sudo install -d -o juicelab -g juicelab -m 0750 /var/log/juicelab
```

Clone the repos as the service user :

```bash
sudo -u juicelab git clone https://github.com/mo0ogly/juicelab /opt/juicelab/juicelab
sudo -u juicelab git -C /opt/juicelab/juicelab clone https://github.com/mo0ogly/juice-shop juice-shop
```

> If you maintain a private fork, replace the URLs and set up a
> deploy key per repo. Do not store private SSH keys in the
> `juicelab` user home — keep them in `/etc/ssh/deploy_keys/` with
> `chmod 0400` and `User=juicelab` in a `Match User` ssh-config
> block.

## 3. Secrets

Generate three independent secrets, **none of which appears in any
git-tracked file** :

```bash
TEACHER_TOK=$(openssl rand -hex 32)
PROOF_SEC=$(openssl rand -hex 32)
CTF_SEC=$(openssl rand -hex 32)
```

Write them to `/etc/juicelab/env` :

```bash
sudo install -d -o root -g juicelab -m 0750 /etc/juicelab
sudo tee /etc/juicelab/env >/dev/null <<EOF
# JuiceLab dashboard runtime config. Do NOT commit this file.
DASHBOARD_TEACHER_TOKEN=$TEACHER_TOK
DASHBOARD_PROOF_SECRET=$PROOF_SEC
JUICESHOP_CTF_SECRET=$CTF_SEC

# Public-facing config
DASHBOARD_PORT=5050
DASHBOARD_BIND=127.0.0.1
DASHBOARD_HTTPS=true
DASHBOARD_CORS_ORIGINS=https://juice.tonprof.fr,http://127.0.0.1:3000,http://localhost:3000

# Default cohort id (auto-created on first sync if missing)
DASHBOARD_DEFAULT_COHORT=M2-2026
DASHBOARD_DB=/var/lib/juicelab/dashboard.sqlite
EOF
sudo chown root:juicelab /etc/juicelab/env
sudo chmod 0640 /etc/juicelab/env
```

Verification (the file must not be world-readable) :

```bash
ls -la /etc/juicelab/env
# -rw-r----- 1 root juicelab ... /etc/juicelab/env
```

Hand the value of `DASHBOARD_TEACHER_TOKEN` to the teacher via an
out-of-band channel (1Password / Signal / in-person). Never email it
in plaintext.

## 4. systemd unit

`sudo tee /etc/systemd/system/juicelab-dashboard.service >/dev/null <<'EOF'`

```ini
[Unit]
Description=JuiceLab teacher dashboard (Flask + SQLite)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=juicelab
Group=juicelab
WorkingDirectory=/opt/juicelab/juicelab/dashboard
EnvironmentFile=/etc/juicelab/env
ExecStart=/usr/bin/python3 app.py
Restart=on-failure
RestartSec=5

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/juicelab /var/log/juicelab
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Limits
LimitNOFILE=2048
TasksMax=128

[Install]
WantedBy=multi-user.target
EOF
```

Enable + start :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now juicelab-dashboard
sudo systemctl status juicelab-dashboard --no-pager
journalctl -u juicelab-dashboard -n 30 --no-pager
```

Health check (must answer locally, not yet over public IP) :

```bash
curl -sf http://127.0.0.1:5050/api/health
# {"ok":true,...}
```

## 5. Caddy reverse proxy + auto-TLS

Install :

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Caddyfile :

```bash
sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
{
  # Global options
  email teacher@example.com   # used by Let's Encrypt for renewal warnings
}

juice.tonprof.fr {
  encode gzip zstd

  # Strict security headers
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options    "nosniff"
    X-Frame-Options           "DENY"
    Referrer-Policy           "strict-origin-when-cross-origin"
    Permissions-Policy        "interest-cohort=()"
    -Server
  }

  # Reverse proxy to the dashboard bound on loopback only
  reverse_proxy 127.0.0.1:5050

  # Access log (rotate via logrotate)
  log {
    output file /var/log/caddy/juicelab.log {
      roll_size     50mb
      roll_keep     14
      roll_keep_for 720h
    }
    format json
    level INFO
  }
}
EOF

sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Wait 30-60 s for Let's Encrypt issuance, then :

```bash
curl -sf https://juice.tonprof.fr/api/health
# {"ok":true,...}
```

Optional : add basic rate-limiting via the
[`caddy-ratelimit`](https://github.com/mholt/caddy-ratelimit) module
(build a custom caddy binary with `xcaddy build --with github.com/mholt/caddy-ratelimit`).
For a single-classroom deployment, fail2ban at the OS level (step 7)
is usually enough.

## 6. UFW firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5050/tcp   # block direct dashboard access (must go through Caddy)
sudo ufw deny 3000/tcp   # block direct Juice Shop if you run it on the VPS too
sudo ufw enable
sudo ufw status verbose
```

Verify from another host :

```bash
nc -vz juice.tonprof.fr 443    # OK
nc -vz juice.tonprof.fr 5050   # connection refused
```

## 7. fail2ban for /login

```bash
sudo apt install -y fail2ban

sudo tee /etc/fail2ban/filter.d/juicelab.conf >/dev/null <<'EOF'
[Definition]
failregex = ^.* "POST /login HTTP/.*" 401 .*$
ignoreregex =
EOF

sudo tee /etc/fail2ban/jail.d/juicelab.local >/dev/null <<'EOF'
[juicelab]
enabled  = true
port     = http,https
filter   = juicelab
logpath  = /var/log/caddy/juicelab.log
maxretry = 5
findtime = 600
bantime  = 3600
EOF

sudo systemctl reload fail2ban
sudo fail2ban-client status juicelab
```

Note : Caddy logs JSON. Adapt the filter regex to match
`"status":401` and `"uri":"/login"` if you switch to JSON-only.

## 8. Encrypted daily backups

`age` is a minimal modern encryption tool (Go, single binary).

```bash
sudo apt install -y age cron

# Generate a key on the OPERATOR laptop (not the VPS!).
age-keygen -o ~/juicelab-backup.key
# AGE-SECRET-KEY-1...   <- private, KEEP SAFE
# # public key: age1...  <- copy this line for the VPS cron

# Drop the public key on the VPS (no secret material).
sudo tee /etc/juicelab/backup.pub >/dev/null <<EOF
age1...
EOF
sudo chmod 0644 /etc/juicelab/backup.pub
```

Backup script :

```bash
sudo tee /usr/local/sbin/juicelab-backup >/dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
SRC=/var/lib/juicelab/dashboard.sqlite
DST_DIR=/var/lib/juicelab/backups
mkdir -p "$DST_DIR"
PUB=$(cat /etc/juicelab/backup.pub)
# Use sqlite .backup to grab a consistent snapshot while the dashboard runs.
sqlite3 "$SRC" ".backup '/tmp/dashboard-$TS.sqlite'"
age -r "$PUB" -o "$DST_DIR/dashboard-$TS.sqlite.age" "/tmp/dashboard-$TS.sqlite"
rm -f "/tmp/dashboard-$TS.sqlite"
# Keep 30 days, delete the rest.
find "$DST_DIR" -type f -name '*.sqlite.age' -mtime +30 -delete
EOF
sudo chmod 0755 /usr/local/sbin/juicelab-backup

sudo tee /etc/cron.d/juicelab-backup >/dev/null <<'EOF'
# JuiceLab encrypted backup, every night at 03:30 UTC.
30 3 * * * root /usr/local/sbin/juicelab-backup >> /var/log/juicelab/backup.log 2>&1
EOF
```

Restore drill (run quarterly) :

```bash
# Pull the latest .age locally, then on your laptop :
age -d -i ~/juicelab-backup.key < dashboard-XXXXX.sqlite.age > dashboard.sqlite
sqlite3 dashboard.sqlite ".schema students"   # smoke test
```

## 9. Auto-updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Optional : enable automatic reboots at 04:30 UTC when needed.
sudo sed -i 's|//Unattended-Upgrade::Automatic-Reboot "false";|Unattended-Upgrade::Automatic-Reboot "true";|' /etc/apt/apt.conf.d/50unattended-upgrades
sudo sed -i 's|//Unattended-Upgrade::Automatic-Reboot-Time "02:00";|Unattended-Upgrade::Automatic-Reboot-Time "04:30";|' /etc/apt/apt.conf.d/50unattended-upgrades
```

## 10. SSH lockdown

`sudo tee /etc/ssh/sshd_config.d/juicelab.conf >/dev/null <<'EOF'`

```sshd
Port 22
PasswordAuthentication no
PermitRootLogin no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
AllowUsers your-admin-user
ClientAliveInterval 300
ClientAliveCountMax 2
EOF
sudo systemctl reload ssh
```

Verify you can still log in from a SECOND terminal before closing the
first one.

## 11. Post-deploy verification checklist

Run from a laptop, NOT the VPS :

```bash
# 1. DNS
dig +short juice.tonprof.fr A         # = VPS IP
# 2. TLS A grade
curl -sIv https://juice.tonprof.fr 2>&1 | head -25
# 3. HSTS header present
curl -sI https://juice.tonprof.fr/api/health | grep -i strict-transport
# 4. HTTP redirects to HTTPS
curl -sI http://juice.tonprof.fr/api/health | grep -i location
# 5. Direct dashboard port blocked
nc -vz juice.tonprof.fr 5050   # connection refused
# 6. Health check via TLS
curl -sf https://juice.tonprof.fr/api/health
# 7. /login flow
curl -i -X POST https://juice.tonprof.fr/login -d 'token=wrong&next=/dashboard' | head -5
# expect 401
# 8. fail2ban detects 5 wrong logins
for i in 1 2 3 4 5 6; do curl -s -X POST https://juice.tonprof.fr/login -d 'token=wrong&next=/dashboard' >/dev/null; done
ssh juicelab-vps "sudo fail2ban-client status juicelab"
# 9. CORS scope
curl -sI -H 'Origin: https://evil.example' https://juice.tonprof.fr/api/cohorts | grep -i access-control
# should not contain evil.example
# 10. backup file exists after 24h
ssh juicelab-vps "ls -la /var/lib/juicelab/backups/"
# 11. systemd unit unprivileged
ssh juicelab-vps "ps -o user,pid,cmd -C python3 | head -3"
# user = juicelab, never root
# 12. logs do NOT contain the teacher token
ssh juicelab-vps "sudo grep -i 'teacher_token=[^&\"]\\+' /var/log/caddy/juicelab.log | head -3"
# expect empty (Caddy stores headers and bodies separately if format=json)
```

## 12. Day-2 operations

| Operation | Command |
|---|---|
| Tail dashboard logs | `journalctl -u juicelab-dashboard -f` |
| Tail caddy logs | `tail -f /var/log/caddy/juicelab.log` |
| Rotate teacher token | follow `docs/COHORT_WORKFLOW.md` § 7 |
| Update code | `sudo -u juicelab git -C /opt/juicelab/juicelab pull && sudo systemctl restart juicelab-dashboard` |
| Restart all | `sudo systemctl restart juicelab-dashboard caddy fail2ban` |
| Restore from backup | `age -d -i ~/key < dashboard-TS.sqlite.age > dashboard.sqlite ; sudo systemctl stop juicelab-dashboard ; sudo cp dashboard.sqlite /var/lib/juicelab/ ; sudo chown juicelab:juicelab /var/lib/juicelab/dashboard.sqlite ; sudo systemctl start juicelab-dashboard` |
| Wipe a cohort | use `/admin/cohorts` UI |
| Renew TLS manually | `sudo systemctl reload caddy` (Caddy renews automatically) |

## 13. What this guide does NOT cover

- **Multi-tenant** : multiple teachers on a single VPS sharing the
  dashboard. The teacher token is a single shared secret ; pivot to
  OIDC / SSO if you outgrow that. Out of scope here.
- **High availability** : single-VPS deployment. For HA, put a load
  balancer in front of two replicas and migrate SQLite to PostgreSQL.
- **WAF** : Caddy basic. For Cloudflare-grade WAF, put the dashboard
  behind Cloudflare and enable proxy mode.
- **Aggregated audit logs** : SIEM ingestion. Pipe Caddy logs to
  Loki or Vector if needed.
- **CTFd integration** : see `docs/CTF-INTEGRATION.md`.

## 14. References

- Caddy server : https://caddyserver.com/docs/
- systemd security : `man systemd.exec` (sandbox section)
- fail2ban : https://www.fail2ban.org/wiki/index.php/Main_Page
- age encryption : https://age-encryption.org/
- OWASP best practices for VPS / Linux hardening :
  https://cheatsheetseries.owasp.org/cheatsheets/Linux_security_baseline.html
