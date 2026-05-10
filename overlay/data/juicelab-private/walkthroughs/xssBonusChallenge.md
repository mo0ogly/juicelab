# Solution canonique - xssBonusChallenge : Bonus Payload

## Contexte

Le challenge bonus exploite la meme vulnerabilite DOM XSS que le
challenge localXssChallenge (champ de recherche traite par
bypassSecurityTrustHtml), mais demande un payload specifique : un iframe
qui charge un track Soundcloud avec autoplay. C'est une demonstration
concrete que DOM XSS peut servir a faire executer une charge externe
arbitraire dans le contexte de la page, pas seulement un alert.

L'effet visible et auditif (musique qui se lance) rend la
demonstration percutante en cours.

## Vulnerabilite exploitee

Identique a localXssChallenge : DOM-Based Cross-Site Scripting (DOM
XSS). OWASP Top 10 2021 : A03:2021 Injection. CWE-79.

Le payload exact attendu (donne dans la description du challenge sur le
score-board) :

```html
<iframe width="100%" height="166" scrolling="no" frameborder="no"
allow="autoplay" src="https://w.soundcloud.com/player/?url=https%3A//
api.soundcloud.com/tracks/771984076&color=%23ff5500&auto_play=true&
hide_related=false&show_comments=true&show_user=true&show_reposts=false&
show_teaser=true"></iframe>
```

(une seule ligne dans le champ de recherche).

## Etapes de resolution

1. **Etape 1 - Pre-requis** : avoir resolu localXssChallenge ou au
   moins compris le mecanisme DOM XSS sur le champ de recherche.

2. **Etape 2 - Recuperer le payload** : aller sur le score-board
   `/#/score-board`, deroule le challenge "Bonus Payload", copier
   l'iframe Soundcloud complete depuis la description.

3. **Etape 3 - Augmenter le volume** : ce payload va lancer une lecture
   audio. Mettre le volume a un niveau ecoutable.

4. **Etape 4 - Coller dans le champ de recherche** : la loupe en haut
   de page Juice Shop, coller le payload tel quel.

5. **Etape 5 - Soumettre** : Entree ou clic sur la loupe. La page de
   resultats charge, et un lecteur Soundcloud apparait avec lecture
   automatique du track 771984076.

6. **Etape 6 - Validation** : Juice Shop detecte le payload exact dans
   le parametre de recherche et marque le challenge solved.

## Validation automatique

Le backend Juice Shop matche le parametre de recherche contre une regex
qui detecte la presence des chaines distinctives du payload bonus
(domaine soundcloud, track id 771984076). Quand match, le challenge
xssBonusChallenge passe a solved.

## Concept enseigne

Le DOM XSS n'est pas limite a alert. Il peut :
- Charger des ressources externes (iframe, img, script src).
- Exfiltrer des donnees du DOM ou du storage.
- Exfiltrer des cookies non-httpOnly.
- Faire des appels API authentifies au nom de la victime.
- Defacer la page (overlay, redirection).
- Mining de cryptomonnaie cote victime (cryptojacking).

L'impact est limite seulement par la creativite de l'attaquant et les
mitigations en place.

## Prevention

Identique au localXssChallenge :
- Echappement par defaut, pas de bypassSecurityTrustHtml sur input
  utilisateur.
- CSP stricte (frame-src 'self' bloquerait l'iframe externe).
- Sanitization avec DOMPurify si on doit accepter du HTML.

Specifique au cas iframe :
- CSP `frame-src 'self'` interdit les iframes externes.
- CSP `child-src 'self'` (deprecated en CSP3 mais encore parse par
  certains navigateurs) couvre aussi.
- Sandbox les iframes legitimes : `<iframe sandbox="allow-scripts">`
  limite le contexte d'execution.

## Variantes pour etudiants avances

- Adapter le payload pour utiliser une autre ressource externe (image,
  audio, video). Discuter des contraintes (CORS, Same-Origin).
- Tester l'efficacite d'une CSP : ajouter
  `Content-Security-Policy: default-src 'self'` sur le serveur Juice
  Shop (configuration locale temporaire) et observer que le payload
  est bloque par la console DevTools.
- Construire un payload qui combine alert + iframe pour confirmer DOM
  XSS et impact en meme temps.
- Discussion : quels referentiels de securite traitent specifiquement
  des risques iframe ? (CSP MDN, OWASP HTML5 Security Cheat Sheet,
  OWASP DOM-based XSS Prevention Cheat Sheet).
