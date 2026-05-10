# Solution canonique - scoreBoardChallenge : Score Board

## Contexte

Toute SPA Angular declare ses routes dans une table chargee cote client.
Juice Shop dissimule la page Score Board en ne mettant pas de lien dans le
menu, mais la route reste presente dans le bundle JavaScript livre au
navigateur. C'est une illustration directe du principe "security by
obscurity n'est pas de la securite" : ce qui n'est pas affiche n'est pas
pour autant inaccessible.

## Vulnerabilite exploitee

Information disclosure via code analysis. OWASP Top 10 2021 : A01:2021
Broken Access Control (le contenu sensible n'est protege que par
l'absence de lien). CWE-540 Inclusion of Sensitive Information in Source
Code. MITRE ATT&CK : T1083 File and Directory Discovery (variante web).

Le composant Angular cible est declare avec un path explicit dans
`frontend/src/app/app.routing.ts` :

```typescript
{ path: 'score-board', component: ScoreBoardComponent }
```

Cette declaration est compilee dans le bundle main.js livre au client. La
recherche full-text dans les Sources DevTools la fait apparaitre.

## Etapes de resolution

1. **Etape 1 - Identifier l'absence de lien** : verifier qu'aucune entree
   du menu ne pointe vers le score-board.

2. **Etape 2 - Ouvrir les DevTools** : F12 puis onglet Sources.

3. **Etape 3 - Recherche globale** : Ctrl-Maj-F sur "score-board" ou
   "scoreBoard". La table de routes apparait.

4. **Etape 4 - Naviguer vers la route** : taper directement
   `http://127.0.0.1:3000/#/score-board` dans la barre d'adresse.

5. **Etape 5 - Validation** : la page Score Board s'affiche, et l'entree
   "Find the carefully hidden Score Board page" passe en solved.

## Validation automatique

Juice Shop detecte la resolution par l'appel d'API que fait le frontend
quand le composant Score Board s'initialise. Le challenge
`scoreBoardChallenge` passe a solved=true.

## Concept enseigne

Tout ce qui est livre au navigateur est public. Une URL non listee
publiquement n'est pas une URL secrete. Le seul controle d'acces qui
fonctionne pour des donnees sensibles est une verification d'autorisation
cote serveur (JWT, session, RBAC), pas un masquage cote client.

Concept secondaire : le code analysis est une demarche valide en pentest.
Lire le bundle JavaScript pour cartographier les routes, endpoints et
constantes est la premiere etape de toute reconnaissance moderne sur une
SPA.

## Prevention

1. **Authentification + autorisation server-side** : pour toute page ou
   donnee qui doit etre privee, le serveur verifie l'identite et le role
   sur chaque requete API qui alimente la page.

2. **Minification et obfuscation ne suffisent pas** : elles ralentissent
   l'analyse mais ne la previennent pas. Un attaquant peut toujours
   utiliser un beautifier (npm package `js-beautify`) pour rendre le code
   lisible.

3. **Pas de chemins sensibles dans le bundle public** : les routes admin
   peuvent etre lazy-loaded depuis un module charge uniquement apres
   authentification reussie. Cela rend la decouverte plus difficile sans
   pour autant la rendre impossible.

## Variantes pour etudiants avances

- Reproduire la decouverte sans DevTools, juste avec curl :
  `curl http://127.0.0.1:3000/main.js | grep score-board`.
- Ecrire un script qui extrait toutes les routes du bundle main.js (par
  exemple avec `grep -oE "path:\s*'[^']+'"`).
- Discussion : comment un projet maintient-il la liste des routes
  admin sans les exposer ? Quelles solutions existent en Angular (lazy
  loading + guard cote serveur + module separe) ?
