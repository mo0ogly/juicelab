# Solution canonique - loginAdminChallenge : Login Admin

## Contexte

Le formulaire de login de Juice Shop construit sa requête SQL en concaténant
directement le champ email saisi par l'utilisateur. C'est une vulnérabilité
classique d'injection SQL pédagogique : la concaténation de chaînes pour
construire une requête, au lieu d'une requête paramétrée, permet à un
attaquant d'injecter ses propres morceaux de SQL.

## Vulnérabilité exploitée

Injection SQL classique sur le champ email. OWASP Top 10 2021 : A03:2021
Injection. MITRE ATT&CK : T1190 Exploit Public-Facing Application. CWE-89.

Le code Juice Shop concerné se trouve dans `routes/login.ts` et utilise une
construction de requête en string :

```javascript
const query = "SELECT * FROM Users WHERE email='" + email + "' AND password='" + password + "' AND deletedAt IS NULL"
```

Cette construction est par essence vulnérable : tout caractère de l'email
saisi est interprété par SQLite. La parade est de paramétrer la requête via
les méthodes du driver SQLite.

## Étapes de résolution

1. **Étape 1 - Accéder à la page de login** : depuis l'accueil Juice Shop,
   cliquer sur le menu Account puis Login.

2. **Étape 2 - Insérer un payload SQL minimal dans le champ email** : taper
   `' OR true--` (apostrophe, espace, OR, espace, true, deux tirets) dans le
   champ email.

3. **Étape 3 - Remplir un mot de passe arbitraire** : taper n'importe quoi
   dans le champ password. Le mot de passe ne sera pas vérifié grâce au
   commentaire SQL qui neutralise la fin de la requête.

4. **Étape 4 - Soumettre** : cliquer sur Log in. La requête exécutée par
   SQLite devient :
   ```sql
   SELECT * FROM Users WHERE email='' OR true-- AND password='abc' AND deletedAt IS NULL
   ```
   Le `--` commente la fin. La condition `email='' OR true` retourne tous
   les users. SQLite renvoie le premier, qui est `admin@juice-sh.op`.

5. **Étape 5 - Vérifier** : tu es maintenant connecté en tant qu'admin
   (visible dans le menu Account). Le score-board valide automatiquement le
   challenge Login Admin.

## Validation automatique

Juice Shop détecte la résolution dans `lib/insecurity.js` : si le user
authentifié a `role='admin'` après une requête de login, le challenge
`loginAdminChallenge` passe à solved=true.

## Concept enseigné

La concaténation de chaînes pour construire une requête SQL est inherently
dangereuse. Toute saisie utilisateur incorporée dans une requête doit être
**paramétrée**, jamais concaténée. C'est le geste fondateur de la prévention
des injections, applicable bien au-delà de SQL (commandes shell, LDAP, NoSQL).

Concept secondaire : les **messages d'erreur verbeux** (stack traces,
SQLITE_ERROR avec la requête complète) divulguent la structure interne et
facilitent l'attaque. La gestion d'erreur en production doit être opaque
côté client tout en loguant côté serveur.

## Prévention

Trois pratiques cumulables :

1. **Requêtes paramétrées (prepared statements)** : la prévention canonique.
   Le driver de base sépare la requête (statique) des paramètres (utilisateur),
   et garantit que les paramètres ne peuvent pas devenir du code.

2. **ORM avec sanitization automatique** : Sequelize, TypeORM, Prisma pour
   Node.js, SQLAlchemy pour Python. Si on respecte l'API et qu'on n'utilise
   pas de raw SQL, l'injection est structurellement impossible.

3. **Defense in depth** : un WAF (par exemple ModSecurity avec OWASP CRS)
   bloque les patterns de payload SQL connus. Pas une solution principale,
   mais une couche supplémentaire.

## Variantes pour étudiants avancés

- Reproduire l'attaque sans utiliser le formulaire, en envoyant directement
  une requête POST sur `/rest/user/login` avec curl ou Postman.
- Combiner l'injection avec une UNION pour exfiltrer toutes les colonnes de
  la table Users (préparation au challenge Database Schema).
- Identifier les autres routes Juice Shop qui présentent des injections SQL
  et hiérarchiser par criticité.
- Discussion : pourquoi est-il important que `'` ne soit pas la seule
  protection à laquelle on pense ? Que se passe-t-il avec `"`, `\`, ou des
  encodages alternatifs (URL-encoded, hex) ?
