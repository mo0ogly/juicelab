# Solution canonique - exposedCredentialsChallenge : Exposed credentials

## Contexte

Un developpeur a laisse dans le code source du frontend les credentials
d'un compte de test (`testing@juice-sh.op` / `IamUsedForTesting`). Ces
identifiants sont compiles dans le bundle JavaScript livre au navigateur
et donc lisibles par n'importe qui. Le challenge consiste a les retrouver
et a se connecter avec.

## Vulnerabilite exploitee

Hardcoded Credentials. OWASP Top 10 2021 : A07:2021 Identification and
Authentication Failures + A02:2021 Cryptographic Failures (secrets en
clair). CWE-798 Use of Hard-coded Credentials. CWE-540 Inclusion of
Sensitive Information in Source Code.

Le bundle compile contient une chaine litterale `testing@juice-sh.op` et
une chaine `IamUsedForTesting` quelque part dans le code (par exemple
dans une suite de tests integree, un composant de login auto, ou un
fichier de configuration de developpement non purge avant build prod).

## Etapes de resolution

1. **Etape 1 - Ouvrir DevTools** : F12 puis onglet Sources sur Chrome
   (ou Debugger sur Firefox).

2. **Etape 2 - Recherche globale** : Ctrl-Maj-F (Cmd-Opt-F sur macOS)
   ouvre la recherche full-text dans tous les fichiers JS charges. Taper
   `password` ou `IamUsedForTesting`.

3. **Etape 3 - Identifier le couple** : un resultat pointe vers une
   chaine litterale `IamUsedForTesting` associee a `testing@juice-sh.op`
   dans un meme bloc de code.

4. **Etape 4 - Aller a la page de login** : naviguer vers
   `http://127.0.0.1:3000/#/login`.

5. **Etape 5 - Saisir les credentials** : email `testing@juice-sh.op`,
   password `IamUsedForTesting`. Cliquer Log in.

6. **Etape 6 - Validation** : la connexion reussit. Juice Shop verifie
   qu'un login a reussi avec ce couple precis et marque le challenge
   solved.

## Validation automatique

Le backend Juice Shop possede une regle qui detecte un login reussi avec
le couple (testing@juice-sh.op, IamUsedForTesting) et marque
`exposedCredentialsChallenge` solved. La validation passe par le route
handler de `/rest/user/login` qui examine la combinaison.

## Concept enseigne

Aucun secret ne doit etre dans du code source qui finit dans un bundle
public. Le frontend etant par nature distribue au client, tout ce qu'il
contient est public. Cela inclut : mots de passe de tests, cles d'API,
tokens d'identification, URLs internes, secrets de signature.

Concept secondaire : la separation des environnements (dev/staging/prod)
implique des secrets distincts. Un compte de test qui existe en
production avec un mot de passe trivial est une vulnerabilite exploitable
meme si le compte n'a pas de privileges, parce qu'il sert d'identite
authentifiee pour d'autres attaques (par exemple acces a une API
authenticated-only mais pas authorized-only).

## Prevention

1. **Pas de secrets dans le code** : utiliser des variables
   d'environnement (`.env` ignore par git), des secret managers (AWS
   Secrets Manager, HashiCorp Vault, GCP Secret Manager), ou des
   stockages dedies.

2. **Audit pre-commit** : outils comme `trufflehog`, `gitleaks`,
   `detect-secrets` scannent les commits pour des secrets potentiels.
   Hook pre-commit obligatoire en dev.

3. **Audit du bundle compile** : meme si on n'a pas hardcode de secrets,
   le bundle peut en contenir suite a une dependance. `grep -i password`
   sur le bundle est une verification minimale.

4. **Comptes de test uniquement en environnement non-prod** : les
   credentials de test n'existent jamais en production. Les seeds de
   donnees prod ne contiennent pas de comptes "testing" / "demo".

## Variantes pour etudiants avances

- Faire la decouverte avec curl + grep sans utiliser DevTools :
  `curl -s http://127.0.0.1:3000/main.js | grep -oE '[a-zA-Z]+@juice-sh\.op'`
  puis pour chaque email trouve, chercher des mots de passe a proximite.
- Ecrire un scanner de secrets simple en Python qui parcourt les bundles
  JS et applique des regex sur les chaines litterales.
- Discussion : a quel moment du cycle de developpement ces credentials
  ont-ils probablement ete commites ? Quels garde-fous CI/CD auraient
  pu les detecter avant la mise en production ?
