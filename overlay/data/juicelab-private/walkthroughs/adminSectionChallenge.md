# Solution canonique - adminSectionChallenge : Admin Section

## Contexte

Juice Shop possede une section administrateur accessible via la route
`/#/administration`. Cette section est gardee par une verification
client-side du role utilisateur dans le JWT stocke en localStorage. Une
fois authentifie comme admin, la route est accessible sans aucun obstacle
supplementaire.

Le challenge enchaine logiquement avec Login Admin (pre-requis SQLi sur
le formulaire de login pour obtenir une session admin).

## Vulnerabilite exploitee

Broken Access Control. OWASP Top 10 2021 : A01:2021 Broken Access
Control. CWE-285 Improper Authorization. CWE-639 Authorization Bypass
Through User-Controlled Key.

Le code Angular cible verifie le role JWT cote client uniquement :

```typescript
canActivate(): boolean {
  return this.authService.getRoleFromToken() === 'admin'
}
```

La protection est consistante uniquement parce que le serveur valide le
JWT a chaque appel API. Mais le composant Angular est servi sans
verification : si tu obtiens un JWT admin (par n'importe quel moyen),
l'acces a la page est garanti.

## Etapes de resolution

1. **Etape 1 - Pre-requis : etre admin** : si pas encore fait, resoudre
   le challenge Login Admin. Dans le formulaire de login, taper :
   - email : `' OR true--`
   - password : n'importe quoi
   - cliquer Log in

2. **Etape 2 - Decouvrir la route admin** : taper dans la barre
   d'adresse `http://127.0.0.1:3000/#/administration`. Alternativement,
   chercher dans main.js `Ctrl-Maj-F` sur "administration" pour
   confirmer la route.

3. **Etape 3 - Acces** : la page Administration s'affiche avec la liste
   des feedbacks et users.

4. **Etape 4 - Validation** : Juice Shop detecte la requete API admin
   reussie et marque le challenge solved.

## Validation automatique

Le challenge `adminSectionChallenge` passe a solved quand un user
authentifie avec role admin atteint la route `/administration`. La
detection se fait au chargement du composant via un appel API qui
necessite des privileges admin.

## Concept enseigne

Le controle d'acces ne peut pas etre client-side seul. Le frontend peut
cacher des liens et empecher le rendu de pages, mais le serveur DOIT
verifier l'autorisation a chaque requete API. Si le frontend est la
seule defense, un attaquant qui obtient un JWT admin a tous les droits
sans avoir a contourner le client.

Concept secondaire : la chaine de challenges Login Admin -> Admin Section
-> Five-Star Feedback est une exemple typique d'escalade. Chaque etape
suppose la precedente. C'est exactement ce qu'on observe en pentest :
une vulnerabilite seule peut etre tolerable, mais composee a d'autres
elle devient catastrophique.

## Prevention

1. **Verification server-side systematique** : sur chaque endpoint
   d'API admin, verifier le role du JWT (signature + claim `role`).

2. **Pas de logique sensible cote client** : le client peut decider
   quoi afficher, mais la verite vient du serveur. Si un user non-admin
   force la navigation vers /administration, la page peut s'afficher
   vide ou erreur, mais aucune donnee admin ne doit etre delivrable.

3. **Defense en profondeur** : middleware d'autorisation global qui
   route les endpoints `/api/admin/*` a travers une verification de role
   avant tout handler.

4. **Audit log** : chaque acces a la section admin est logue avec
   timestamp, user, IP. Permet la detection d'anomalies (ex. un user
   non-admin qui accede a /administration apparaitrait dans les logs et
   peut etre alerte).

## Variantes pour etudiants avances

- Tester l'acces direct a l'API admin sans le JWT admin :
  `curl http://127.0.0.1:3000/api/Users/`. Observer le 401.
- Decoder le JWT obtenu apres Login Admin sur jwt.io et identifier le
  champ qui distingue un admin (`role`).
- Forger un JWT avec role=admin sans connaitre le secret de signature.
  Tester si le serveur accepte (probablement non, sauf si la
  vulnerabilite "alg=none" est presente, ce qui donne un autre challenge
  Juice Shop : JWT None Algorithm).
- Discussion : que penser de l'argument "le client va de toute facon
  empecher l'acces" ? Quels autres exemples connais-tu d'applications
  reelles ou la securite reposait sur le client (et qui ont ete
  exploitees) ?
