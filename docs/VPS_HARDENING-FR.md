# Durcissement VPS — déployer le tableau de bord JuiceLab sur l'internet public

> Version anglaise : [VPS_HARDENING.md](./VPS_HARDENING.md).

Ce guide décrit le déploiement du tableau de bord enseignant JuiceLab
(Flask + SQLite) sur un VPS unique exposé via un domaine public
(ex. `juice.tonprof.fr`). Il suppose une installation mono-locataire : un
seul enseignant, un seul VPS, de nombreux étudiants sollicitant le même tableau de bord.

Périmètre : **tableau de bord uniquement**. Juice Shop tourne **sur le poste
de chaque étudiant** en mode local et pousse des événements en HTTPS vers le tableau de bord.
Le tableau de bord est la seule surface exposée publiquement.

> **Public cible** : opérateurs disposant de sudo sur un VPS Ubuntu 22.04+ fraîchement installé.
> Lire intégralement avant d'exécuter la moindre commande. Si vous ne disposez que d'un seul
> VPS et d'une seule cohorte, aucun script d'automatisation n'est fourni ; copiez-collez
> les extraits dans l'ordre indiqué.

## 0. Modèle de menace en deux phrases

Le jeton enseignant (`DASHBOARD_TEACHER_TOKEN`) constitue l'unique ligne de
défense pour la surface accessible à l'enseignant. La surface accessible aux étudiants
(`/api/cohort/join`, `/api/student/status`, `/api/sync`) est publique par
conception, mais soumise à un contrôle de débit et filtrée côté serveur sur la colonne
`status` de chaque étudiant ; un attaquant qui connaît un code de cohorte peut inonder
de demandes d'adhésion en attente, d'où la limitation de débit au niveau du mandataire inverse.

## 1. Prérequis du VPS

| Élément | Valeur |
|---|---|
| OS | Ubuntu 22.04+ ou Debian 12+ (basé sur `apt`) |
| CPU / RAM | 2 vCPU / 2 Go de RAM minimum |
| Disque | 20 Go minimum (SQLite + sauvegardes) |
| Réseau | IPv4 publique. IPv6 si disponible. |
| DNS | Un enregistrement `A` (et optionnellement `AAAA`) `juice.tonprof.fr` pointant vers le VPS, propagé avant l'étape 4 |
| SSH | Authentification par clé uniquement (sans mot de passe), utilisateur sudo non-root |
| Instantanés | Au moins un instantané avant le premier déploiement (option de retour arrière si le durcissement casse quelque chose) |

## 2. Créer l'utilisateur de service sans privilèges

```bash
sudo useradd -r -m -d /opt/juicelab -s /bin/bash juicelab
sudo install -d -o juicelab -g juicelab -m 0750 /opt/juicelab
sudo install -d -o juicelab -g juicelab -m 0750 /var/lib/juicelab
sudo install -d -o juicelab -g juicelab -m 0750 /var/log/juicelab
```

Cloner les dépôts en tant qu'utilisateur de service :

```bash
sudo -u juicelab git clone https://github.com/mo0ogly/juicelab /opt/juicelab/juicelab
sudo -u juicelab git -C /opt/juicelab/juicelab clone https://github.com/mo0ogly/juice-shop juice-shop
```

> Si vous maintenez un fork privé, remplacez les URL et configurez une clé de déploiement
> par dépôt. Ne stockez pas les clés SSH privées dans le répertoire personnel de
> l'utilisateur `juicelab` — conservez-les dans `/etc/ssh/deploy_keys/` avec
> `chmod 0400` et `User=juicelab` dans un bloc `Match User` de la configuration ssh.

## 3. Secrets

Générez trois secrets indépendants, **qu'aucun fichier suivi par git ne doit contenir** :

```bash
TEACHER_TOK=$(openssl rand -hex 32)
PROOF_SEC=$(openssl rand -hex 32)
CTF_SEC=$(openssl rand -hex 32)
```

Écrivez-les dans `/etc/juicelab/env` :

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

Vérification (le fichier ne doit pas être lisible par tous) :

```bash
ls -la /etc/juicelab/env
# -rw-r----- 1 root juicelab ... /etc/juicelab/env
```

Transmettez la valeur de `DASHBOARD_TEACHER_TOKEN` à l'enseignant via un
canal hors-bande (1Password / Signal / en personne). Ne l'envoyez jamais par courriel en clair.

## 4. Unité systemd

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

Activation et démarrage :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now juicelab-dashboard
sudo systemctl status juicelab-dashboard --no-pager
journalctl -u juicelab-dashboard -n 30 --no-pager
```

Vérification de santé (doit répondre en local, pas encore via l'IP publique) :

```bash
curl -sf http://127.0.0.1:5050/api/health
# {"ok":true,...}
```

## 5. Mandataire inverse Caddy + TLS automatique

Installation :

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

Attendez 30 à 60 secondes pour l'émission du certificat Let's Encrypt, puis :

```bash
curl -sf https://juice.tonprof.fr/api/health
# {"ok":true,...}
```

Facultatif : ajoutez une limitation de débit basique via le module
[`caddy-ratelimit`](https://github.com/mholt/caddy-ratelimit)
(compilez un binaire caddy personnalisé avec `xcaddy build --with github.com/mholt/caddy-ratelimit`).
Pour un déploiement en salle de classe unique, fail2ban au niveau OS (étape 7)
est généralement suffisant.

## 6. Pare-feu UFW

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

Vérification depuis un autre hôte :

```bash
nc -vz juice.tonprof.fr 443    # OK
nc -vz juice.tonprof.fr 5050   # connection refused
```

## 7. fail2ban pour /login

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

Remarque : Caddy journalise en JSON. Adaptez l'expression régulière du filtre pour correspondre à
`"status":401` et `"uri":"/login"` si vous passez en mode JSON exclusif.

## 8. Sauvegardes quotidiennes chiffrées

`age` est un outil de chiffrement moderne et minimal (Go, binaire unique).

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

Script de sauvegarde :

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

Exercice de restauration (à effectuer chaque trimestre) :

```bash
# Pull the latest .age locally, then on your laptop :
age -d -i ~/juicelab-backup.key < dashboard-XXXXX.sqlite.age > dashboard.sqlite
sqlite3 dashboard.sqlite ".schema students"   # smoke test
```

## 9. Mises à jour automatiques

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Optional : enable automatic reboots at 04:30 UTC when needed.
sudo sed -i 's|//Unattended-Upgrade::Automatic-Reboot "false";|Unattended-Upgrade::Automatic-Reboot "true";|' /etc/apt/apt.conf.d/50unattended-upgrades
sudo sed -i 's|//Unattended-Upgrade::Automatic-Reboot-Time "02:00";|Unattended-Upgrade::Automatic-Reboot-Time "04:30";|' /etc/apt/apt.conf.d/50unattended-upgrades
```

## 10. Verrouillage SSH

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

Vérifiez que vous pouvez toujours vous connecter depuis un SECOND terminal avant de fermer le premier.

## 11. Liste de contrôle post-déploiement

À exécuter depuis un poste de travail, PAS depuis le VPS :

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

## 12. Opérations courantes (jour 2)

| Opération | Commande |
|---|---|
| Suivre les journaux du tableau de bord | `journalctl -u juicelab-dashboard -f` |
| Suivre les journaux de Caddy | `tail -f /var/log/caddy/juicelab.log` |
| Renouveler le jeton enseignant | suivre `docs/COHORT_WORKFLOW.md` § 7 |
| Mettre à jour le code | `sudo -u juicelab git -C /opt/juicelab/juicelab pull && sudo systemctl restart juicelab-dashboard` |
| Redémarrer tout | `sudo systemctl restart juicelab-dashboard caddy fail2ban` |
| Restaurer depuis une sauvegarde | `age -d -i ~/key < dashboard-TS.sqlite.age > dashboard.sqlite ; sudo systemctl stop juicelab-dashboard ; sudo cp dashboard.sqlite /var/lib/juicelab/ ; sudo chown juicelab:juicelab /var/lib/juicelab/dashboard.sqlite ; sudo systemctl start juicelab-dashboard` |
| Supprimer une cohorte | utiliser l'interface `/admin/cohorts` |
| Renouveler le TLS manuellement | `sudo systemctl reload caddy` (Caddy renouvelle automatiquement) |

## 13. Ce que ce guide ne couvre pas

- **Multi-locataire** : plusieurs enseignants sur un seul VPS partageant le
  tableau de bord. Le jeton enseignant est un secret partagé unique ; passez à
  OIDC / SSO si vous dépassez ce cadre. Hors périmètre ici.
- **Haute disponibilité** : déploiement mono-VPS. Pour la HA, placez un
  répartiteur de charge devant deux réplicas et migrez SQLite vers PostgreSQL.
- **WAF** : Caddy en configuration de base. Pour un WAF de niveau Cloudflare, placez le tableau de bord
  derrière Cloudflare et activez le mode proxy.
- **Journaux d'audit agrégés** : ingestion SIEM. Redirigez les journaux de Caddy vers
  Loki ou Vector si nécessaire.
- **Intégration CTFd** : voir `docs/CTF-INTEGRATION.md`.

## 14. Références

- Caddy server : https://caddyserver.com/docs/
- Sécurité systemd : `man systemd.exec` (section sandbox)
- fail2ban : https://www.fail2ban.org/wiki/index.php/Main_Page
- Chiffrement age : https://age-encryption.org/
- Bonnes pratiques OWASP pour le durcissement VPS / Linux :
  https://cheatsheetseries.owasp.org/cheatsheets/Linux_security_baseline.html
