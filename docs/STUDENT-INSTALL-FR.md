# Guide d'installation eleve — JuiceLab

> Objectif : avoir un JuiceLab fonctionnel sur ton portable en **5 a 10 minutes**, avec OWASP Juice Shop sur `http://127.0.0.1:3000` et le dashboard prof sur `http://127.0.0.1:5000`.

> Version anglaise : [STUDENT-INSTALL-EN.md](./STUDENT-INSTALL-EN.md).

---

## 1. Ce qui sera installe

Une seule stack Docker avec trois conteneurs :

| Conteneur | Port | Role |
|---|---|---|
| `juicelab-juiceshop` | 3000 | OWASP Juice Shop + l'overlay pedagogique JuiceLab (`/#/juicelab`) |
| `juicelab-dashboard` | 5000 | Dashboard enseignant (matrice cohorte, indices consommes, journal) |
| `juicelab-db` | interne | Volume SQLite pour le log d'evenements |

Le premier build telecharge ~700 Mo et prend 5 a 8 minutes. Ensuite, chaque `docker compose up` est de l'ordre de 10 secondes.

Aucune donnee ne quitte ton portable. Le dashboard est expose uniquement sur `127.0.0.1`.

---

## 2. Prerequis

| Outil | Version minimum | Ou le trouver |
|---|---|---|
| **Docker Desktop** (Windows / macOS) ou **Docker Engine** (Linux) | 24+ | <https://www.docker.com/products/docker-desktop> |
| **Docker Compose v2** | livre avec Docker Desktop ; sur Linux : `sudo apt install docker-compose-plugin` | — |
| **Git** | n'importe quelle version recente | <https://git-scm.com/downloads> |
| **OpenSSL** | livre avec Git for Windows, macOS et toutes les distros Linux | — |
| **RAM** | 4 Go libres | — |
| **Disque** | 3 Go libres | — |

Sanity check rapide :

```bash
docker --version            # Docker version 24.x ou plus
docker compose version      # Docker Compose v2.x ou plus
git --version
openssl version             # n'importe quelle sortie
```

Si `docker compose version` echoue, ton Docker est trop vieux. Sur Linux : `sudo apt install docker-compose-plugin`. Sur Windows / macOS : mets a jour Docker Desktop.

---

## 3. Installation en une commande (recommande)

Meme flux sur Linux, macOS et Windows.

### 3.1 Cloner le repo

```bash
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab
```

### 3.2 Lancer l'installeur

#### Linux / macOS — `bash`

```bash
./scripts/install-student.sh -c M2-IA-2026
```

Remplace `M2-IA-2026` par l'identifiant de cohorte que ton enseignant t'a donne. Sans `-c`, le script te le demande de maniere interactive.

Si le script n'est pas executable :

```bash
chmod +x scripts/install-student.sh
./scripts/install-student.sh -c M2-IA-2026
```

#### Windows — PowerShell 7+

```powershell
.\scripts\install-student.ps1 -Cohort M2-IA-2026
```

Si PowerShell se plaint de la politique d'execution, lance une fois :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

puis recommence.

> **PowerShell 7+ est requis.** Windows 10 a PowerShell 5.1 par defaut, qui est trop vieux. Installe PowerShell 7 depuis <https://learn.microsoft.com/fr-fr/powershell/scripting/install/installing-powershell-on-windows>.

### 3.3 Ce que fait l'installeur

Dans l'ordre :

1. Verifie que Docker, Docker Compose et OpenSSL sont disponibles.
2. Copie `docker/.env.example` vers `docker/.env` s'il n'existe pas encore.
3. Genere deux secrets aleatoires de 32 caracteres (`TEACHER_ADMIN_TOKEN`, `DASHBOARD_TEACHER_TOKEN`) avec `openssl rand -hex 16` (ou le RNG .NET sur Windows si OpenSSL est absent).
4. Ecrit `JUICELAB_COHORT_ID` selon l'argument `-c`, le fichier env, ou un prompt interactif.
5. Lance `docker compose --env-file .env up -d --build`.
6. Attend que `http://127.0.0.1:3000/` et `http://127.0.0.1:5000/api/health` repondent.
7. Affiche les URLs et les deux tokens enseignant.

L'installeur est **idempotent** : le relancer ne regenere pas les tokens deja valides. Pour une reinstallation propre, ajoute `--reset` (bash) ou `-Reset` (PowerShell).

### 3.4 Autres modes

| Commande | Effet |
|---|---|
| `./scripts/install-student.sh` | interactif, demande le cohort_id |
| `./scripts/install-student.sh -y` | non interactif, accepte tous les defauts (cohort = `M2-IA-2026`) |
| `./scripts/install-student.sh --reset` | `docker compose down -v` + reinstall complet (efface les events) |
| `.\scripts\install-student.ps1 -Yes` | idem, PowerShell |
| `.\scripts\install-student.ps1 -Reset` | idem, PowerShell |

---

## 4. Verifier l'installation

Ouvre ces URLs dans ton navigateur :

| URL | Attendu |
|---|---|
| <http://127.0.0.1:3000/#/score-board> | Score-board Juice Shop avec un bouton **TD** sur chacun des 13 challenges selectionnes |
| <http://127.0.0.1:3000/#/juicelab> | Panel parcours JuiceLab (13 challenges groupes par demi-journee) |
| <http://127.0.0.1:5000/login> | Page de login dashboard |
| <http://127.0.0.1:5000/api/health> | `{"ok": true}` |

Smoke test bout-en-bout :

1. Cree un compte sur Juice Shop (`/#/register`).
2. Resous **Score Board** (le lien est dans le code source de la page — `Ctrl+U`).
3. Clique sur **TD** dans la carte Score Board.
4. Dans le dialogue, remplis le journal *After* (quelques phrases qui expliquent ta resolution).
5. Colle le flag, clique **Verify**.
6. Connecte-toi au dashboard (`/login`, colle le `DASHBOARD_TEACHER_TOKEN` affiche par l'installeur).
7. Ouvre `/dashboard?cohort=<ta-cohorte>`. Tu dois voir ta ligne avec `solved`, `journal`, `quiz`, `flag verified`.

Si quelque chose echoue, voir § 6 ci-dessous.

---

## 5. Utilisation au quotidien

Une fois installe, tu n'as **pas** besoin de relancer l'installeur. La stack survit aux reboots :

```bash
# Demarrer / reprendre
cd juicelab/docker
docker compose --env-file .env up -d

# Arreter (conserve l'historique des events)
docker compose --env-file .env down

# Logs en direct (utile quand quelque chose casse)
docker compose --env-file .env logs -f

# Reset complet (efface la base — repart de zero)
docker compose --env-file .env down -v
```

Ta progression Juice Shop, tes journaux et tes reponses au quiz sont stockes cote client dans `localStorage` (cle `juicelab_state_v1`). Ils survivent aux redemarrages de conteneurs mais **pas** a un `docker compose down -v` (la base du dashboard est aussi effacee).

---

## 6. Depannage

### Port deja utilise (`3000` ou `5000`)

Une autre appli squatte le port. Soit tu l'arretes, soit tu changes le port hote dans `docker/docker-compose.yml` et tu rebuild.

### `docker compose: command not found`

Ton Docker est trop vieux ou le plugin Compose est manquant.
- Linux : `sudo apt install docker-compose-plugin`
- Windows / macOS : mets a jour Docker Desktop.

### `permission denied` sur le script (Linux / macOS)

```bash
chmod +x scripts/install-student.sh
```

### PowerShell : *"l'execution de scripts est desactivee sur ce systeme"*

Une fois par utilisateur :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Le build echoue sur des doublons SVG `flag-icons`

Ce bug a ete patche cote repo (voir `overlay/frontend/src/assets/flag-icons-patched.min.css`). Si tu le rencontres encore, tu as clone une vieille revision : `git pull` puis relance l'installeur avec `--reset`.

### Le dashboard retourne 401 / 403

Le token dans le cookie de ton navigateur ne correspond pas a celui de `docker/.env`. Ouvre `docker/.env`, copie la valeur de `DASHBOARD_TEACHER_TOKEN`, reconnecte-toi sur `/login`.

### Les conteneurs sont en crash-loop

```bash
cd juicelab/docker
docker compose --env-file .env logs --tail=200 juiceshop
docker compose --env-file .env logs --tail=200 dashboard
```

Envoie les 50 dernieres lignes du conteneur en faute a ton enseignant.

### J'ai perdu mes tokens enseignant

```bash
grep TOKEN juicelab/docker/.env
```

Les tokens sont en clair dans ce fichier sur ton portable. Pour les regenerer : supprime les lignes correspondantes dans `docker/.env` et relance l'installeur — il en genere des neufs.

---

## 7. Desinstaller

```bash
cd juicelab/docker
docker compose --env-file .env down -v   # arret + suppression des volumes
cd ../..
rm -rf juicelab                          # suppression du repo clone
docker image prune                       # optionnel, libere du disque
```

---

## 8. Ou demander de l'aide

- Ouvre une issue sur <https://github.com/mo0ogly/juicelab/issues> avec :
  - ton OS + version de Docker Desktop
  - les 50 dernieres lignes de `docker compose logs`
  - la commande exacte qui a echoue et la sortie complete

Ton enseignant et `gabrielhociel@gmail.com` sont les mainteneurs.
