# JuiceLab — deploiement docker-compose

Trois scenarios couverts :

| Scenario | Quand | Fichiers utilises |
|---|---|---|
| **Smoke test 1 instance** | Verifier que la chaine build + dashboard + plugin fonctionne | `Dockerfile.juicelab` + `Dockerfile.dashboard` + `docker-compose.yml` |
| **Cohorte de N eleves** | TD avec 1 instance par etudiant, dashboard agreges | + `provision.py` qui genere `docker-compose.cohort.yml` |
| **VPS partage** | Cohorte hebergee sur 1 VPS, sous-domaines ou reverse-proxy externe | A monter manuellement (Caddy / Traefik) — note plus bas |

## Modes de deploiement (CTFd opt-in)

Trois modes orthogonaux, selectionnes par les variables d'environnement
`CTFD_URL` et `CTFD_ADMIN_TOKEN` :

| Mode | CTFD vars | Usage | Visibilite competition |
|---|---|---|---|
| **A** Local solo | absent | 1 stack docker par PC eleve, prof recupere `proof.md` | Aucune (juicelab interne) |
| **B** Cohorte tracking | absent | dashboard central, eleves pointent vers prof | `/api/cohort` (prof) |
| **C** + CTFd central | **set** | A ou B + CTFd public, push automatique des hint penalties | Leaderboard CTFd live |

Mode A est le default. Mode C s'active a la demande sans toucher au code,
juste en remplissant `CTFD_URL`/`CTFD_ADMIN_TOKEN` dans `.env`. Voir
section "Mode C" en bas du document pour le setup CTFd.

## 0. Pre-requis

- Docker 24+ et `docker compose` plugin
- Python 3.10+ (uniquement pour `provision.py`)
- 2 GB RAM par instance Juice Shop, 100 MB pour le dashboard

## 1. Smoke test 1 instance

```bash
cd docker
cp .env.example .env
# editer .env : changer TEACHER_ADMIN_TOKEN et DASHBOARD_TEACHER_TOKEN
docker compose --env-file .env up -d --build
```

Verifier :

```bash
# eleve : http://127.0.0.1:3000/#/juicelab
curl http://127.0.0.1:3000/api/Challenges/ | head -c 80

# prof : dashboard sur http://127.0.0.1:5000/dashboard?cohort=M2-IA-2026
curl -H "X-Teacher-Token: <ton token>" \
     "http://127.0.0.1:5000/api/cohort?cohort=M2-IA-2026"
```

Logs en live :

```bash
docker compose logs -f dashboard
docker compose logs -f juicelab-demo
```

Stop + cleanup :

```bash
docker compose --env-file .env down            # arrete sans supprimer les volumes
docker compose --env-file .env down -v         # arrete + supprime le volume du dashboard
```

## 2. Cohorte de N eleves

### Etape 1 — preparer le roster

Editer `roster.txt` (ou copier `roster.example.txt`) avec un handle par ligne :

```
amelie
bobby
chloe
...
```

Regles : alphanumerique + tirets, max 30 chars, lowercase. Les commentaires `#` et les lignes vides sont ignores.

### Etape 2 — generer le compose cohort

```bash
python provision.py roster.txt --port-base 3001 \
    --output docker-compose.cohort.yml \
    --print-cors
```

Sortie : un fichier `docker-compose.cohort.yml` avec un service `juicelab-<handle>` par etudiant, mappe sur le port `3001 + index`. Egalement la valeur `DASHBOARD_CORS_ORIGINS` a coller dans `.env`.

### Etape 3 — coller le CORS dans .env

Le dashboard rejette les events qui ne viennent pas d'une origine declaree. Coller la valeur imprimee par `--print-cors` dans `.env` :

```
DASHBOARD_CORS_ORIGINS=http://127.0.0.1:3001,http://localhost:3001,http://127.0.0.1:3002,...
```

### Etape 4 — deployer

```bash
docker compose -f docker-compose.yml -f docker-compose.cohort.yml \
    --env-file .env up -d --build
```

Donner aux eleves leurs URLs respectives :

```
amelie  -> http://<IP serveur>:3001/#/juicelab
bobby   -> http://<IP serveur>:3002/#/juicelab
chloe   -> http://<IP serveur>:3003/#/juicelab
```

Le prof regarde le dashboard sur `http://<IP serveur>:5000/dashboard?cohort=M2-IA-2026` (header `X-Teacher-Token` requis).

### Etape 5 — surveillance live

Le `instance_label` est l'handle de l'eleve, donc dans le dashboard chaque event est attribue. Le `student_token` reste un UUID local genere par le navigateur — pour le mapper au handle, c'est l'`instance_label` qui sert de pont.

```bash
docker compose -f docker-compose.yml -f docker-compose.cohort.yml \
    --env-file .env ps
docker compose logs -f juicelab-amelie
```

### Etape 6 — fin du TD

```bash
docker compose -f docker-compose.yml -f docker-compose.cohort.yml \
    --env-file .env down -v
```

## 3. VPS partage avec reverse-proxy

Pour un deploiement public, ajouter un reverse-proxy (Caddy / Traefik / nginx) devant les containers :

```caddy
# Caddyfile
amelie.juicelab.tld { reverse_proxy 127.0.0.1:3001 }
bobby.juicelab.tld  { reverse_proxy 127.0.0.1:3002 }
dashboard.juicelab.tld { reverse_proxy 127.0.0.1:5000 }
```

Penser a :
- Generer le HTTPS (Let's Encrypt par Caddy ou certbot)
- Etendre `DASHBOARD_CORS_ORIGINS` aux noms de domaine HTTPS publics
- Adapter `JUICELAB_DASHBOARD_URL` dans `.env` a l'URL publique
- Restreindre l'acces au dashboard par IP au pare-feu si la cible est publique

## 4. Mode C — CTFd central pour la competition

Active le push automatique des penalites hints vers un CTFd central, pour
qu'un eleve qui pioche dans les hints juicelab voit aussi son score CTFd
diminuer. Sans cela, le leaderboard CTFd reflete uniquement la rapidite
de paste du flag, pas l'effort reel.

### Etape 1 — heberger CTFd

Option (a) — CTFd dans le meme compose :

1. Decommenter le service `ctfd` dans `docker-compose.yml` (et les volumes
   `ctfd_uploads`/`ctfd_logs`).
2. Generer un secret pour `CTFD_SECRET_KEY` et l'ajouter au `.env`.
3. `docker compose --env-file .env up -d ctfd`
4. Ouvrir `http://127.0.0.1:8000`, faire le setup initial (admin user,
   nom du CTF, mode equipes).

Option (b) — CTFd separe (VPS du prof, autre machine LAN) : suivre la
[doc officielle CTFd](https://docs.ctfd.io/) et se contenter de noter
l'URL publique.

### Etape 2 — peupler les challenges via juice-shop-ctf-cli

```powershell
npm install -g juice-shop-ctf-cli

@'
ctfFramework: CTFd
juiceShopUrl: http://127.0.0.1:3000
ctfKey: <contenu de juice-shop/ctf.key>
insertHints: none
'@ | Out-File juicelab-ctfd.yml

juice-shop-ctf --config juicelab-ctfd.yml --output cohort-2026.csv
```

Dans CTFd : `Admin > Config > Backup > Import CSV`, choisir "Challenges"
puis le fichier `cohort-2026.csv`.

`insertHints: none` est important : on veut les hints juicelab, pas les
hints natifs OWASP. Sinon double exposition.

### Etape 3 — generer un admin token

Dans CTFd : `Admin > Settings > Access Tokens > Generate`. Copier le
token et le mettre dans `.env` :

```
CTFD_URL=http://127.0.0.1:8000
CTFD_ADMIN_TOKEN=ctfd_xxxxxxxxxxxxxxxxxxxxxxxx
CTFD_PENALTY_FORMULA=mirror_juicelab
CTFD_TEAM_MODE=team
```

### Etape 4 — alignement de la cle HMAC

Les trois sources doivent partager la **meme cle** pour que le flag
HMAC genere par Juice Shop soit accepte par CTFd ET par le dashboard :

```
juice-shop/ctf.key                      (lu par lib/utils.ts)
docker/.env JUICESHOP_CTF_SECRET        (lu par dashboard /api/verify-flag)
juicelab-ctfd.yml ctfKey                (lu par juice-shop-ctf-cli, donne le hash dans CSV CTFd)
```

Test canary : pour `challenge.name = "Score Board"` avec la `ctf.key`
de ce repo, l'HMAC-SHA1 attendu est
`2614339936e8282e2f820f023d4d998a1f95e02a`. Si CTFd refuse ce flag,
verifier l'alignement.

### Etape 5 — pre-provisionner les teams CTFd

Pour chaque eleve, creer une team CTFd avec :
- `affiliation: <COHORT_ID>` (ex. `M2-IA-2026`)
- `email: <email du JWT Juice Shop>`

Le dashboard utilise `email` comme bridge identite : `juicelab-sync`
extrait l'email du JWT, l'inclut dans le payload `data` des events
`hint_revealed`, et le dashboard appelle `GET CTFD/api/v1/teams` pour
trouver le `team_id` correspondant. Pas d'inscription = pas de push
(retry au prochain hint event).

### Etape 6 — restart le dashboard

```powershell
docker compose --env-file .env restart dashboard
docker compose logs dashboard | grep -i ctfd
# attendu : "CTFd push enabled (Mode C)"
```

### Etape 7 — monitoring

```powershell
# status (auth via header X-Teacher-Token)
curl -H "X-Teacher-Token: $env:DASHBOARD_TEACHER_TOKEN" `
     http://127.0.0.1:5000/api/admin/ctfd-status

# Reponse :
# {"enabled":true,"ctfd_url":"http://127.0.0.1:8000","team_mode":"team",
#  "penalty_formula":"mirror_juicelab","teams_mapped":12,
#  "pending_pushes":0,"last_error":null}
```

### Etape 8 — reconciliation manuelle

Si CTFd a ete down quand un hint a ete revele, l'event reste avec
`award_pushed_at = NULL`. Pour rattraper :

```powershell
curl -X POST -H "X-Teacher-Token: $env:DASHBOARD_TEACHER_TOKEN" `
     http://127.0.0.1:5000/api/admin/reconcile-awards

# Reponse : {"retried": N, "succeeded": M, "failed": K}
```

### Troubleshooting Mode C

| Symptome | Cause probable | Fix |
|---|---|---|
| `"enabled": false` | `CTFD_URL` ou `CTFD_ADMIN_TOKEN` absent | Editer `.env`, `docker compose restart dashboard` |
| `"teams_mapped": 0` apres plusieurs hints | Email JWT != email team CTFd | Aligner les emails ou verifier `affiliation` |
| `"pending_pushes": N` qui grandit | CTFd unreachable ou token invalide | `last_error` indique la cause, fix puis `/api/admin/reconcile-awards` |
| Award appliquee sur le mauvais team | Mauvaise resolution email/affiliation | Purger la table `student_team_mapping` (`docker compose exec dashboard sqlite3 /app/data/dashboard.sqlite "DELETE FROM student_team_mapping;"`) puis nouveau hint |
| Flag refuse par CTFd | `ctfKey` du CSV != `ctf.key` Juice Shop | Re-generer le CSV avec la bonne `ctfKey`, re-importer |

## 5. Limitations connues

1. **State server-side non persistant** : le `consumedHintsByStudent` du backend Juice Shop est en memoire. Apres restart d'un container, les eleves repartent de zero. Acceptable en TD continu, pas en multi-jour.
2. **student_token = UUID navigateur** : un eleve qui change de navigateur ou vide le LocalStorage perd son tracking. Le dashboard verra apparaitre 2 students differents pour le meme humain. Mitigation : leur dire de toujours utiliser le meme navigateur pendant les 12h du TD.
3. **challenges.solved global par instance** : OK car 1 container par eleve.
4. **DB SQLite locale par container Juice Shop** : pas de partage d'etat entre containers, c'est ce qu'on veut.
5. **DB SQLite du dashboard** : un seul fichier dans le volume. 30 eleves x 50 events l'heure x 12h = ~18000 rows, sans probleme.
6. **Pas de HTTPS interne** : les events transitent en HTTP cleartext entre les containers et le dashboard. OK en reseau Docker prive, a securiser pour un deploiement public.

## 6. Troubleshooting

| Symptome | Cause probable | Fix |
|---|---|---|
| Build Docker lent (~10 min) | npm install dans Dockerfile | normal au 1er build, cache au 2e |
| `dashboard unhealthy` | DASHBOARD_TEACHER_TOKEN < 16 chars | mettre 32+ chars dans .env |
| Plugin Coach blanc | dashboard_url incorrect dans config.json | verifier env JUICELAB_DASHBOARD_URL |
| Events qui n'arrivent pas | CORS rejette | DASHBOARD_CORS_ORIGINS doit lister TOUS les ports |
| `juicelab-amelie` ne demarre pas | port 3001 occupe | choisir un port-base libre dans provision.py |
| Restart d'un container = state perdu | state in-memory | accepter (TD court) ou implementer persistence Redis |
