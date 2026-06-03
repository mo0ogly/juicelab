# Workflow des cohortes — guide opérationnel

> Version anglaise : [COHORT_WORKFLOW.md](./COHORT_WORKFLOW.md).

Ce document décrit le **workflow trilatéral des cohortes**, le
**flux de connexion**, le **support multilingue**, les **popups d'aide**,
et les **aspects opérationnels** (Google OAuth, rotation du token enseignant,
dépannage). Il complète [`PEDAGOGY.md`](PEDAGOGY.md) (qui couvre le *pourquoi*)
et [`CLASSROOM-DEPLOYMENT.md`](CLASSROOM-DEPLOYMENT.md)
(qui couvre les topologies de déploiement).

## Audience

- **Enseignants (instructeurs)** : sections 1, 2, 4, 5, 7
- **Étudiants** : sections 1, 3
- **Opérateurs (administrateurs système)** : sections 6, 7

---

## 1. Workflow trilatéral en un coup d'œil

Trois acteurs interagissent en séquence linéaire :

```mermaid
sequenceDiagram
    autonumber
    participant T as Enseignant
    participant D as Dashboard (Flask :5050)
    participant S as Étudiant
    participant J as Juice Shop overlay (:3000)

    T->>D: Créer la cohorte (UX /admin/cohorts)
    T-->>S: Partager le code de cohorte + l'URL du dashboard
    S->>J: Ouvrir Juice Shop, panneau JuiceLab
    S->>J: Connexion (admin@juice-sh.op ou auto-inscription)
    Note over S,J: Bannière étape 1 "Connecte-toi" disparaît
    S->>J: Soumettre le modal d'adhésion (URL + code + email)
    J->>D: POST /api/cohort/join (status=pending)
    Note over S,J: Bannière étape 2 "Demande envoyée" apparaît
    T->>D: /admin/cohorts -> Approuver l'étudiant
    D-->>J: Prochain poll de statut (60s) renvoie "validated"
    Note over S,J: La bannière disparaît ; flux d'événements
    J->>D: POST /api/sync (event_type=...)
    D-->>T: Mise à jour de la matrice en direct sur /dashboard
```

### Prérequis (dans l'ordre)

1. **Authentification Juice Shop** — l'étudiant doit se connecter à Juice Shop
   lui-même (cela fournit le JWT utilisé par les indices, le quiz et le journal).
   Sans cette étape, la bannière d'authentification reste visible et le modal
   d'adhésion est bloqué.
2. **Demande d'adhésion à la cohorte** — l'étudiant remplit le modal JuiceLab
   avec l'URL du dashboard, le code de cohorte et son adresse e-mail.
3. **Approbation de l'enseignant** — l'enseignant clique sur Approuver dans
   `/admin/cohorts`. Les événements de l'étudiant sont bloqués sur `/api/sync`
   avec un HTTP 403 jusqu'à cette étape.

Les deux bannières (`auth-banner` et `join-banner`) **n'apparaissent jamais
en même temps** : la bannière d'adhésion est masquée tant que l'étudiant n'est
pas authentifié. Ce comportement est intentionnel afin de conserver un flux
linéaire.

---

## 2. Côté enseignant

### 2.1 Créer une cohorte

- URL : `http://127.0.0.1:5050/admin/cohorts`
- Formulaire : identifiant (alphanumérique + `-`, `_`, `.`, max 64 caractères) + libellé optionnel.
- Effets : la ligne de cohorte apparaît immédiatement dans le tableau ; la
  cohorte devient disponible pour les étudiants.

### 2.2 Approuver / rejeter les demandes d'adhésion

- Même page `/admin/cohorts` → section **Demandes d'inscription en attente**.
- Boutons **Approuver** ou **Rejeter** par demande.
- Approuver → le statut de l'étudiant passe à `validated` → `/api/sync` accepte
  leurs événements.
- Rejeter → statut `rejected` → `/api/sync` retourne 403 avec un
  message ; l'étudiant voit une bannière « Accès refusé ».

### 2.3 Dashboard en direct

- URL : `http://127.0.0.1:5050/dashboard?cohort=<id>`
- Rafraîchissement automatique toutes les 5 s. Cartes KPI : étudiants, défis, événements,
  statut en direct.
- Matrice par étudiant : pastilles par défi (résolu, indices N/5,
  journal, quiz X/100, flag +10). Cliquer sur une pastille `journal` → ouvre le
  journal en texte libre de l'étudiant dans un modal.

### 2.4 Gestion de la liste des participants

- URL : `http://127.0.0.1:5050/admin/students?cohort=<id>`
- Renommage en ligne, suppression, badges de statut (pending / validated /
  rejected).

---

## 3. Côté étudiant

### 3.1 Se connecter à Juice Shop

L'overlay est conditionné au JWT Juice Shop. Deux chemins possibles :

**Comptes pré-chargés** (le plus rapide pour les TP) :

| E-mail | Mot de passe | Rôle |
|---|---|---|
| `admin@juice-sh.op` | `admin123` | admin |
| `jim@juice-sh.op` | `ncc-1701` | customer |
| `bender@juice-sh.op` | `OhG0dPlease1nsertLiquor!` | customer |
| `support@juice-sh.op` | `J6aVjTgOpRs@?5l!Zkq2AYnCE@RF$P` | admin |
| `morty@juice-sh.op` | `focusOnScienceMorty!focusOnScience` | customer |

**Auto-inscription** : `http://127.0.0.1:3000/#/register`. Choisir un
e-mail et un mot de passe quelconques, puis se connecter via `http://127.0.0.1:3000/#/login`.

**Assistant de connexion** (sélecteur avec les comptes pré-chargés) :
`http://127.0.0.1:3000/assets/juicelab/login-helper.html`.

### 3.2 Rejoindre une cohorte

Après s'être connecté à Juice Shop :

1. Ouvrir le panneau JuiceLab dans Juice Shop (en haut à droite ou
   via `/#/juicelab`).
2. Le modal d'adhésion à la cohorte s'ouvre au premier lancement. Saisir :
   - **URL du dashboard** : l'URL du dashboard communiquée par l'enseignant
     (ex. `http://127.0.0.1:5050`).
   - **Code de cohorte** : l'identifiant de cohorte fourni par l'enseignant
     (alphanumérique, tirets).
   - **Email** : un identifiant lisible pour l'enseignant.
3. Cliquer sur **Demander l'accès**. La bannière d'adhésion affiche « Demande envoyée.
   En attente d'approbation de l'enseignant. »
4. L'overlay interroge `/api/student/status` toutes les 60 s. Dès que
   l'enseignant approuve, la bannière disparaît et les événements sont transmis.

### 3.3 Rouvrir le modal d'adhésion

L'icône engrenage (Réglages cohorte) en haut du panneau JuiceLab
rouvre le modal — à utiliser en cas d'erreur de saisie de l'URL, du code ou
de l'e-mail, ou pour changer de cohorte.

### 3.4 Popup d'aide

L'icône « ? » (Aide) en haut du panneau JuiceLab ouvre un popup
expliquant : comment rejoindre une cohorte, les statuts de demande, le changement
de langue et comment réinitialiser son inscription. Trilingue FR / EN / BR
(suit le sélecteur de langue de Juice Shop).

---

## 4. Support multilingue

| Surface | Langues supportées | Changement |
|---|---|---|
| Juice Shop (catalogue, comptes, navigation) | ~50 langues via Crowdin en amont | Sélecteur de langue en haut à droite |
| Overlay JuiceLab (briefing, indices, quiz, journal, modals) | FR / EN / BR | Hérite de la langue Juice Shop |
| Dashboard enseignant (`/dashboard`, `/admin/cohorts`, `/admin/students`, `/login`) | FR / EN | URL `?lang=fr\|en`, cookie `dash_lang`, Accept-Language, défaut FR |

Le dashboard enseignant expose un sélecteur `[FR | EN]` dans les actions
de navigation de chaque page. Un cookie persistant d'un an mémorise le choix.
L'attribut HTML `lang` est défini dynamiquement à chaque requête, de sorte que
les lecteurs d'écran adoptent la phonétique correcte.

---

## 5. Popups d'aide (intégration UX)

Deux popups en lecture seule documentent le workflow directement dans l'application :

| Côté | Déclencheur | Contenu |
|---|---|---|
| Enseignant (dashboard) | Icône « ? » dans les actions de navigation de `/dashboard`, `/admin/cohorts`, `/admin/students` | Workflow en 4 étapes, multilingue, rotation du token enseignant (CLI uniquement, jamais via l'interface), aperçu des endpoints, dépannage |
| Étudiant (overlay) | Icône « ? » à côté de l'engrenage dans l'en-tête du panneau JuiceLab | Comment rejoindre une cohorte, statuts de demande (pending / validated / rejected), changement de langue, réinitialisation de l'inscription |

Les deux popups se ferment avec `Escape` ou en cliquant en dehors.

---

## 6. Google OAuth sur les environnements locaux

Juice Shop en amont est livré avec un bouton de connexion Google OAuth. Il utilise
le **clientId de démo OWASP**, qui ne fait confiance qu'à une poignée d'hôtes
publics (`demo.owasp-juice.shop`, les environnements Heroku de staging, etc.) ainsi qu'à
une liste d'origines en boucle locale routées via des domaines proxy. Sur une
installation standard `http://127.0.0.1:3000`, **le clic échoue systématiquement** :
Google rejette l'origine.

L'overlay JuiceLab n'utilise PAS Google OAuth — les étudiants se connectent
via les comptes pré-chargés ou s'auto-inscrivent. Pour éviter ce bouton non
fonctionnel, ce fork inclut une configuration d'overlay :

- Fichier : `juice-shop/config/juicelab.yml`
- Contenu : vide `application.googleOauth.authorizedRedirects` afin que
  le composant de connexion en amont définisse `oauthUnavailable=true` et que
  la garde `@if (!oauthUnavailable)` dans le template masque le bouton.
- Activation : `juice.sh start shop` exporte `NODE_ENV=juicelab` afin que
  node-config superpose `juicelab.yml` par-dessus `default.yml`. Remplacer avec
  `JUICELAB_NODE_ENV=...` pour changer d'overlay si nécessaire.

Pour réactiver Google OAuth dans un cours disposant d'un vrai projet Google Cloud
Console et d'une origine non localhost, ajouter un autre overlay (ex.
`config/juicelab-prod.yml`) qui restaure `clientId` et
`authorizedRedirects` et démarrer avec `JUICELAB_NODE_ENV=juicelab-prod`.

---

## 7. Rotation du token enseignant

La variable d'environnement `DASHBOARD_TEACHER_TOKEN` est le **seul**
contrôle d'accès sur tous les endpoints du dashboard protégés et sur les pages
HTML d'administration. La traiter comme un secret de configuration, et non comme
une donnée applicative.

### 7.1 Pourquoi pas via l'interface

Ce choix a été délibérément fait de ne pas exposer cela comme un formulaire
d'administration. Raisons :

- Une session dashboard compromise permettrait à l'attaquant de modifier le
  token (escalade en libre-service).
- Une faute de frappe verrouille tous les enseignants légitimes — la récupération
  nécessiterait un accès SSH ou la console du conteneur.
- Toutes les preuves signées par HMAC (`DASHBOARD_PROOF_SECRET`) et les tokens
  émis avant une rotation deviennent opaques pour les vérificateurs ; cela
  invaliderait les attestations étudiantes déjà délivrées.
- Les journaux de requêtes HTTP peuvent capturer le token dans les corps `POST`.

### 7.2 Procédure correcte de rotation (CLI uniquement)

```bash
# 1) Générer un nouveau token hexadécimal de 32 octets (>= 16 caractères requis par le dashboard).
openssl rand -hex 32

# 2) Modifier le fichier d'environnement (.env, unité systemd, docker-compose, secret k8s).
#    Nom de la variable : DASHBOARD_TEACHER_TOKEN

# 3) Redémarrer le dashboard pour que la nouvelle valeur soit lue au démarrage.
bash juice.sh restart dash

# 4) Transmettre le nouveau token à l'enseignant via un canal hors-bande
#    (1Password, Signal, en personne). Jamais par e-mail en clair.
```

Le popup d'aide du dashboard présente la procédure exacte à l'enseignant
(traduite FR / EN), au cas où il souhaiterait la réaliser lui-même.

---

## 8. Dépannage

### 8.1 « Aucun event reçu pour cette cohorte »

Vérifier dans l'ordre :

1. La cohorte existe bien : `/admin/cohorts` la liste.
2. L'étudiant est **validé** (validated), pas en attente ni rejeté :
   `/admin/students?cohort=<id>` affiche son badge de statut.
3. L'étudiant a configuré la **bonne URL du dashboard** dans son
   modal d'adhésion (l'icône engrenage dans le panneau le rouvre). S'il a saisi
   une mauvaise URL, les événements partent vers `localhost` plutôt que vers
   votre serveur et n'atteignent jamais le dashboard.
4. L'instance Juice Shop utilisée par l'étudiant est **accessible** depuis
   son navigateur (un NAT ou un pare-feu peut bloquer un routeur en salle de classe).

### 8.2 Deux bannières visibles en même temps

Cela ne devrait plus se produire (la bannière d'adhésion est conditionnée à
`isAuthenticated()`). Si c'est le cas, forcer le rechargement de l'onglet Juice Shop
(Ctrl+Maj+R) pour supprimer le bundle en cache.

### 8.3 « Login with Google » apparaît toujours

Le dashboard a probablement été démarré sans `NODE_ENV=juicelab`.
Vérifier le journal du shop : la ligne de démarrage doit indiquer
`demarrage Juice Shop (npm start, port 3000, NODE_ENV=juicelab)`.
Sinon, s'assurer que `juice.sh` est à jour avec le correctif dans
`juice.sh:start_shop()` (commit `1677f09` sur le dépôt parent `juicelab`).

### 8.4 La porte de synchronisation retourne 403 après une approbation récente

L'overlay interroge `/api/student/status` toutes les 60 s. Soit attendre un
cycle de polling, soit cliquer sur l'engrenage → fermer → rouvrir (force une
récupération immédiate). Les événements sont mis en file d'attente localement
pendant l'attente et sont envoyés lors du prochain polling réussi.

### 8.5 Le dashboard retourne 502 / connexion refusée

Redémarrer : `bash juice.sh restart dash`. Vérification de santé :
`curl http://127.0.0.1:5050/api/health`. Si la base de données SQLite est
verrouillée, arrêter le dashboard, supprimer
`dashboard/data/dashboard.sqlite-shm` et `dashboard/data/dashboard.sqlite-wal`,
puis redémarrer.

---

## 9. Référence des endpoints

| Verbe | Chemin | Accès | Interface liée |
|---|---|---|---|
| GET | `/dashboard` | Authentification HTML (cookie) | Page de la matrice en direct |
| GET | `/admin/cohorts` | Authentification HTML | Page d'administration des cohortes |
| GET | `/admin/students?cohort=` | Authentification HTML | Page d'administration de la liste |
| GET | `/api/cohorts` | `X-Teacher-Token` | Liste des cohortes (utilisée par l'UI dashboard) |
| POST | `/api/cohorts` | `X-Teacher-Token` | Créer / renommer une cohorte |
| POST | `/api/cohorts/<cid>/reset` | `X-Teacher-Token` | Réinitialiser les événements et étudiants |
| DELETE | `/api/cohorts/<cid>` | `X-Teacher-Token` | Supprimer une cohorte |
| GET | `/api/cohort/exists?cohort_id=` | public | Vérification du code de cohorte en direct |
| POST | `/api/cohort/join` | public | Demande d'adhésion étudiant (modal overlay) |
| GET | `/api/student/status?student_token=` | public | Polling overlay (60 s) |
| GET | `/api/students/pending?cohort=` | `X-Teacher-Token` | Liste des demandes en attente |
| POST | `/api/students/<token>/approve` | `X-Teacher-Token` | Approuver un étudiant |
| POST | `/api/students/<token>/reject` | `X-Teacher-Token` | Rejeter un étudiant |
| POST | `/api/sync` | Porte de statut côté serveur | Ingestion des événements étudiants |
| GET | `/api/health` | public | Ping de santé |
| GET | `/api/cohort?cohort=` | `X-Teacher-Token` | Données de la matrice en direct |
| GET | `/api/journal-text` | `X-Teacher-Token` | Contenu du modal journal |
| GET | `/api/proof` | `DASHBOARD_PROOF_SECRET` | Preuve PDF signée par HMAC |
| GET | `/login` / `/logout` | HTML | Session enseignant |

Aucune route orpheline : chaque endpoint est lié à au moins une surface
UX visible (page, bouton, bannière ou boucle de polling).

---

## 10. Historique des modifications (sélection)

- **2026-05-11** — Workflow de cohorte (trilatéral) + dashboard FR/EN +
  popups d'aide + Google OAuth désactivé via l'overlay NODE_ENV. Voir
  les commits parents `0c84f1f`, `935dacb`, `1677f09` et les commits du fork
  `17a35f9`, `1810d9c`, `fd5b18d`.
