# Solution canonique - passwordHashLeakChallenge : Password Hash Leak

## Contexte

L'endpoint Juice Shop `/rest/user/whoami` retourne par defaut quelques
champs publics de l'utilisateur courant (id, email, lastLoginIp,
profileImage). Mais le code accepte un parametre `fields` permettant
de demander des colonnes specifiques. Le filtrage est en mode
"allowlist par presence" cote frontend mais en mode "selection libre" cote
backend, ce qui est exactement ce qu'il ne faut pas faire : le client
peut demander explicitement des champs sensibles, et le backend les
retourne sans verification.

## Vulnerabilite exploitee

API Excessive Data Exposure / Mass Assignment in reverse. OWASP API
Security Top 10 2023 : API3:2023 Broken Object Property Level
Authorization. CWE-359 Exposure of Private Personal Information to an
Unauthorized Actor. CWE-200 Exposure of Sensitive Information.

Le code vulnerable se trouve dans `routes/currentUser.ts`. Extrait :

```typescript
const fieldsParam = req.query?.fields as string | undefined
const requestedFields = fieldsParam ? fieldsParam.split(',').map(f => f.trim()) : []

if (requestedFields.length > 0) {
  for (const field of requestedFields) {
    if (user?.data[field as keyof typeof user.data] !== undefined) {
      baseUser[field] = user?.data[field as keyof typeof user.data]
    }
  }
}
```

Aucune verification que le champ demande est autorise. Le code retourne
TOUS les champs demandes du moment qu'ils existent dans l'objet user en
memoire.

## Etapes de resolution

1. **Etape 1 - Se connecter** : utiliser n'importe quel compte (par
   exemple celui decouvert au challenge Exposed Credentials :
   testing@juice-sh.op / IamUsedForTesting).

2. **Etape 2 - Identifier l'endpoint whoami** : observer les requetes
   Network apres le login. La requete `/rest/user/whoami` est emise
   periodiquement.

3. **Etape 3 - Construire l'URL avec fields** : taper dans la barre
   d'adresse :
   `http://127.0.0.1:3000/rest/user/whoami?fields=password`

4. **Etape 4 - Lire la reponse JSON** : le navigateur affiche un objet
   JSON contenant un champ password avec le hash bcrypt de l'utilisateur.

5. **Etape 5 - Validation** : Juice Shop detecte que la reponse contient
   le champ password et marque `passwordHashLeakChallenge` solved.

## Validation automatique

Voir `routes/currentUser.ts` ligne 52 :

```typescript
challengeUtils.solveIf(challenges.passwordHashLeakChallenge,
  () => response?.user?.password)
```

Le challenge est marque solved des qu'une reponse de l'endpoint contient
le champ password (truthy).

## Concept enseigne

Le filtrage cote client est de la presentation, pas de la securite. Le
serveur ne doit jamais "faire confiance" au parametre client pour
decider quels champs envoyer. Le bon pattern est l'allowlist cote
serveur : une liste fixe de champs autorises, definie par role ou par
endpoint, jamais par parametre utilisateur.

Concept secondaire : un hash bcrypt n'est pas chiffre. C'est un hash
unidirectionnel sale. Mais il reste exploitable hors-ligne par
brute-force ou rainbow table contre des mots de passe faibles. La fuite
d'un hash est une etape vers la prise de compte effective.

## Prevention

1. **Allowlist server-side stricte** : Object Field Level Authorization
   (OFLA). Definir explicitement les champs autorises par role :

   ```typescript
   const PUBLIC_FIELDS = ['id', 'email', 'profileImage']
   const ADMIN_FIELDS = [...PUBLIC_FIELDS, 'lastLoginIp', 'createdAt']

   const fields = (req.query.fields ?? '').split(',')
   const allowed = req.user.role === 'admin' ? ADMIN_FIELDS : PUBLIC_FIELDS
   const safe = fields.filter(f => allowed.includes(f))
   ```

2. **Layer de presentation** : utiliser un DTO (Data Transfer Object) ou
   un serializer (DRF, Marshmallow, class-transformer) qui materialise
   la difference entre `User.password` (champ DB) et `UserPublicDTO`
   (champ API).

3. **Tests automatises** : pour chaque endpoint, un test qui verifie
   qu'aucune reponse ne contient `password`, `passwordResetToken`,
   `securityQuestion.answer` quel que soit le parametre passe.

4. **Hash robuste** : meme si le hash leak, qu'il soit difficile a
   casser. bcrypt avec cost >= 12, argon2id avec parametres OWASP, ou
   scrypt. Pas de MD5, SHA-1, ni de SHA-256 sans salt.

## Variantes pour etudiants avances

- Tester d'autres champs sensibles via le meme parametre :
  `?fields=password,securityAnswer,role`. Mesurer ce qui passe.
- Tester le bypass du frontend en utilisant directement curl avec le
  cookie d'authentification :
  `curl -b "token=<jwt>" http://127.0.0.1:3000/rest/user/whoami?fields=password`
- Tenter de cracker le hash bcrypt obtenu avec hashcat ou john (mode 3200)
  contre une wordlist standard (rockyou.txt). Si le password de
  l'utilisateur est faible, le hash tombe en quelques minutes.
- Discussion : pourquoi la sterilisation par allowlist cote serveur
  n'est-elle pas systematique dans les frameworks ? Comment GraphQL
  resout (ou aggrave) ce probleme ?
