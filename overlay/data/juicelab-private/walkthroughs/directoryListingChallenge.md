# Solution canonique - directoryListingChallenge : Confidential Document

## Contexte

Le serveur Juice Shop expose un dossier `/ftp/` qui contient plusieurs
fichiers : factures, sauvegardes de developpement, logs, et un document
confidentiel d'acquisition (acquisitions.md). Le serveur web est
configure pour autoriser le directory listing sur ce dossier, ce qui
permet a un visiteur d'enumerer tous les fichiers presents sans connaitre
leur nom a l'avance.

## Vulnerabilite exploitee

Sensitive Data Exposure via Directory Listing. OWASP Top 10 2021 :
A01:2021 Broken Access Control + A05:2021 Security Misconfiguration.
CWE-548 Exposure of Information Through Directory Listing. CWE-200
Exposure of Sensitive Information to an Unauthorized Actor.

Cote serveur, Juice Shop monte le dossier `ftp/` en static avec une
configuration permissive :

```typescript
app.use('/ftp', serveIndex('ftp', { icons: true }))
app.use('/ftp(?!/quarantine)/:file', fileServer())
```

Le `serveIndex` autorise l'enumeration. Une liste blanche d'extensions
existe (`.md`, `.pdf` autorises ; `.bak`, `.tar.gz` bloques) mais elle
ne protege pas la liste elle-meme.

## Etapes de resolution

1. **Etape 1 - Demander l'index du dossier** : taper
   `http://127.0.0.1:3000/ftp/` dans la barre d'adresse. Le navigateur
   affiche la liste des fichiers presents.

2. **Etape 2 - Reperer le fichier interessant** : parmi les entrees,
   `acquisitions.md` correspond a un document confidentiel sur une
   acquisition d'entreprise.

3. **Etape 3 - Acceder au fichier** : cliquer sur acquisitions.md ou
   taper `http://127.0.0.1:3000/ftp/acquisitions.md`. Le contenu
   s'affiche en clair dans le navigateur.

4. **Etape 4 - Validation** : Juice Shop detecte le GET reussi sur
   `/ftp/acquisitions.md` et marque le challenge solved.

## Validation automatique

Juice Shop intercepte les requetes vers `/ftp/*.md` et marque
`directoryListingChallenge` solved des qu'un fichier .md est
effectivement servi (le serveur log la requete et la route de validation
passe a true).

## Concept enseigne

Le directory listing est une mesconfiguration courante mais souvent
sous-estimee. Elle transforme la phase de reconnaissance en simple lecture
d'index et expose des fichiers oublies (sauvegardes, fichiers temporaires,
exports de bases). En production, un audit periodique du contenu des
dossiers servis est obligatoire.

Concept secondaire : la liste blanche d'extensions (autoriser .md,
bloquer .bak) est une defense partielle. Si un attaquant peut deposer un
fichier avec une extension autorisee (ex. acquisition.md cache dans une
extension allowed), la regle est contournee.

## Prevention

1. **Desactiver le directory listing** : par defaut sur la plupart des
   serveurs (nginx, Apache). Sur Express/Node, ne pas utiliser
   `serve-index` en production. Configurer le serveur pour retourner 404
   quand l'URL pointe vers un dossier.

2. **Mettre les fichiers privates hors du dossier servi** : les fichiers
   confidentiels n'ont rien a faire dans un dossier static. Stocker les
   dans un emplacement non servi (ex. `/var/secrets/`) et les delivrer
   via une route authentifiee.

3. **Audit regulier des dossiers servis** : `find ./public -type f` doit
   etre une commande qui ne reserve pas de surprise. Les sauvegardes
   doivent etre stockees ailleurs.

4. **Defense in depth** : un WAF (modsecurity, Cloudflare WAF) peut
   bloquer les requetes dont le path se termine en `/`.

## Variantes pour etudiants avances

- Enumerer le contenu de `/ftp/` via curl :
  `curl http://127.0.0.1:3000/ftp/`
- Tenter d'acceder a un fichier avec une extension bloquee :
  `curl http://127.0.0.1:3000/ftp/eastere.gg` puis tenter le path
  traversal `curl http://127.0.0.1:3000/ftp/eastere.gg%2500.md` (le
  null-byte est une variante connue de bypass).
- Discussion : pourquoi `/ftp/` est-il un nom de dossier particulierement
  parlant pour un attaquant ? Quels autres noms de dossiers sont des
  cibles classiques (`/admin/`, `/backup/`, `/.git/`) ?
- Activite : auditer une application web reelle (avec autorisation) pour
  detecter des dossiers listables avec dirb ou ffuf.
