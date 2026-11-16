# Revue des hints JuiceLab — 2026-11-16

Suivi de la demande « améliorer les hints des challenges » (périmètre validé
le 2026-11-16 : retrait des étiquettes internes, resynchronisation `overlay/`,
réécriture des workflows dupliqués, revue pédagogique complète).

Source servie : `juice-shop/data/juicelab-private/hints/<key>.yaml`.
Miroir d'installation : `overlay/data/juicelab-private/hints/` (recopié par
`scripts/apply-overlay.sh`). Les deux doivent rester identiques
(`diff -rq overlay/data/juicelab-private juice-shop/data/juicelab-private`).

Ce document remplace, pour les hints, le tracker
`.claude/output/owasp-pedagogy-companion/TRACKER.md` : ce chemin est
gitignoré et le tracker comme `lint_juicelab_pedagogy.py` étaient absents le
2026-11-16 (introuvables dans le dépôt et l'historique Git).

## Méthode par challenge

1. Lire l'entrée `data/static/challenges.yml` (description + liste `hints`).
2. Lire le code qui résout le challenge (`solveIf` / `solve`) et la route.
3. Lire `data/static/codefixes/<key>*` s'il existe (défense canonique).
4. Comparer chaque affirmation N1-N5 au code : endpoint, verbe, champ,
   condition de validation, défense.
5. Rejouer le payload N5 sur un lab de même version que le code
   (19.2.1 = lab 127.0.0.1:43119, fixture `.swarm-fixtures/juice-recette-20261114/run`).
6. Réécrire les niveaux faux ; signaler dans le texte ce qui est déduit du
   code sans avoir été rejoué.
7. Contrôles : YAML, coûts 5/10/20/35/50, champs FR/EN/intent non vides,
   < 800 lignes, miroir `overlay/` identique.

## Constats globaux

| Constat | Preuve | État |
|---|---|---|
| Étiquettes `[KILL_CHAIN_*]` affichées aux élèves dans les hints (198 occurrences, 65 fichiers) | aucun filtrage dans `routes/juicelab.ts` ni l'overlay | Retirées 2026-11-16 ; sens conservé (les textes PROBABLE contiennent déjà la réserve en clair) |
| Miroir `overlay/` périmé (39 hints + quiz `forgedFeedbackChallenge`) | `diff -rq` ; commit juice-shop 765d4d35c (23:04) postérieur à b923c1c (21:28) | Resynchronisé 2026-11-16 |
| Copier-coller entre packs | recouvrement de phrases max 0,20 (rceChallenge / rceOccupyChallenge), 0 paire > 0,40 | Non confirmé ; « Workflow complet » n'est qu'un en-tête commun |
| Erreurs factuelles dans les N4/N5 | 4 packs sur 5 du lot 1 donnaient un payload ou une condition fausse | Revue complète nécessaire (voir tableau) |
| Étiquettes `[KILL_CHAIN_*]` dans briefing/quiz (152) | voulues par `.claude/rules/owasp-pedagogy-companion.md` pour le briefing | Hors périmètre hints, conservées |

## Points ouverts

- **Attention version (2026-11-16)** : les eleves executent 20.4.0-SNAPSHOT (image Docker), pas 19.2.1. Les references fichier:ligne verifiees sur 19.2.1 peuvent etre decalees (constate sur scoreBoard, privacyPolicy, adminSection) ; server.ts servi est decale de +1 par l'import du patch JuiceLab. Recaler sur le code servi (docker exec juicelab-demo) avant de citer une ligne.
- **Version** : les packs sont vérifiés contre Juice Shop 19.2.1 (code du
  dépôt). Le lab TD 20.4.0-SNAPSHOT diffère sur `routes/showProductReviews.ts`,
  `models/feedback.ts`, `routes/verify.ts`, `server.ts` : validité des hints
  sur 20.4.0 non établie.
- **Navigateur** : Chrome 130 plante au démarrage (code 133, SIGTRAP) dans la
  session du 2026-11-16, avec ou sans bac à sable ; cause non établie. Les
  voies purement UI ne sont pas rejouées tant que ce point reste ouvert.
- **Parcours** : `selected_challenges.yml` annonce `total_challenges: 110`
  mais liste 109 clés ; `bullyChatbotChallenge` (retiré au profit de
  `forgedFeedbackChallenge`) conserve un pack de hints.
- **Effets de bord en recette** sur le lab 43119 : challenges résolus
  `noSqlCommandChallenge`, `zeroStarsChallenge`, `changeProductChallenge`
  (description O-Saft restaurée), `emptyUserRegistration`,
  `passwordRepeatChallenge` (corps sans `passwordRepeat`) ; un feedback 0
  étoile et un utilisateur à email vide créés. Lot 2 : `csafChallenge`,
  `continueCodeChallenge` résolus ; un feedback contenant le hash CSAF créé.
  Lot 3 (compte recette `lot3-recette@local.test`) : `freeDeluxeChallenge`,
  `manipulateClockChallenge`, `missingEncodingChallenge` résolus ; compte passé
  deluxe, une commande 75% et un article au panier créés. `persistedXss`
  non rejoué en base (payload vérifié hors ligne contre sanitize-html 1.4.2).
  Lot 4 : aucun effet de bord (geoStalkingVisual non rejoué pour préserver le
  mot de passe d'Emma ; videoXss exige la chaîne fileWrite ; web3Wallet exige
  une transaction Sepolia réelle). Vérifications par lecture du code + config
  lab, assets servis confirmés (IMG_4253.jpg, owasp_promo.vtt : 200).
  Lot 5 (famille Injection SQL) : loginAdmin/Bender/Jim/dbSchema/union
  tous rejoués live sur 43119 (injections de login + UNION sur /rest/products
  /search). Premiers packs trouvés déjà corrects : dbSchema et unionSql (non
  modifiés) ; loginAdmin correct. Corrections mineures loginBender/Jim :
  requête SQL exacte + citations de lignes du tutoriel natif.
  Lot 6 (famille Reset Password) : réponses confirmées en source
  (resetPassword.ts:58-62), questions confirmées live via
  /rest/user/security-question (sans effet de bord). Resets NON rejoués
  pour préserver les mots de passe des comptes seedés. Erreurs majeures :
  questions fausses (Jim, Bjoern interne) et EMAIL faux pour BjoernOwasp
  (gmail au lieu de bjoern@owasp.org).
  Lot 7 (famille XSS) : localXss et httpHeaderXss deja corrects (non
  modifies). persistedXssUser (champ email, pas Address) et restfulXss
  (PUT sans auth) rejoues live. usernameXss corrige sur le mecanisme (CSP
  via Image URL + sanitizeLegacy), payloads tires du test cypress officiel.
  reflectedXss/usernameXss : disabledEnv Docker signale. Effets de bord :
  un compte a email-payload cree, produit 3 modifie puis restaure.
  Lot 8 (Sensitive Data Exposure / fichiers oublies) : les 5 packs deja
  corrects, 4 rejoues live (directoryListing, forgottenDev/Backup via
  null-byte, passwordHashLeak via cookie), exposedCredentials code-confirme.
  Seule correction : renvoi FR faux dans forgottenBackup. Note mecanisme :
  whoami lit le token dans le COOKIE, pas le header Bearer.
  Lot 9 (Broken Access Control) : basketAccess/forgedFeedback/forgedReview
  rejoues live, feedback code-confirme (non rejoue, destructif). Seule
  erreur : basketManipulate (BasketId simple -> 401 ; vraie voie = double
  cle BasketId / parseJsonCustom, verifiee live). Effets de bord : items
  ajoutes au panier 2, un avis produit 1 au nom d'admin, un feedback UserId=1.
  Lot 10 (Improper Input Validation) : registerAdmin/uploadType/nullByte
  deja corrects. Corrections : negativeOrder (endpoint checkout) et
  uploadSize (fenetre de taille 100-200KB, multer plafonne a 200000).
  Rejoues live. Effets de bord : compte role=admin cree, commande a total
  negatif, 2 uploads.
  Lot 11 (JWT / Vulnerable Components) : les 5 methodes correctes, toutes
  rejouees live (jwtUnsigned alg=none, jwtForged HS256 key-confusion avec
  jwt.pub servie, 3 composants via complaint). jwtUnsigned/jwtForged
  affines (exp, source de cle, Windows). Effets de bord : 3 complaints.
  Lot 12 (Cryptographic Issues) : weirdCrypto correct. 4 corrections,
  toutes rejouees live : forgedCoupon (XOR invente -> z85 MMMYY-80),
  premiumPaywall (AES invente -> obscurite), nftUnlock (seed dans un avis
  seede -> derivation cle), easterEgg2 (base64 avant rot13). Effets de
  bord : 1 complaint, 1 commande a -80%, submitKey.
  Lot 13 (Broken Authentication) : weakPassword/oauth/changePasswordBender
  corrects (verifies live). Corrections : ghostLogin (hashcat -> SQLi sur
  le compte supprime chris) et 2FA (hashcat sur mdp fort -> vrai defaut =
  totpSecret en clair, flux 2FA rejoue live). Effets de bord : logins
  ghost/bender, mdp Bender change (slurmCl4ssic), 2FA wurstbrot resolu.
- **Arbre `juice-shop` modifié** : ~1068 fichiers ne diffèrent que par les
  fins de ligne (antérieur à la revue, propriétaire non identifié). Effet
  observé : le JSON CSAF de l'arbre (et celui du lab 43119) n'a plus le
  SHA-512 attendu ; `HEAD` et le lab 43120 l'ont.

## Suivi par challenge (109 du parcours)

| key | catégorie | diff. | statut | notes |
|---|---|---|---|---|
| scoreBoardChallenge | Miscellaneous | 1 | DONE (lot 14) | N4-N5 : mecanisme precise (pixel 1px.png, verify.ts:63) comme adminSection/privacyPolicy ; GET verifie live ; 2026-11-16 lignes recalees sur 20.4 servi (html:41, verify.ts:67) |
| privacyPolicyChallenge | Miscellaneous | 1 | DONE (lot 2) | N3-N5 : validation = image 81px.png (verify.ts:67), pas un appel API ; libelles de menu verifies ; 2026-11-16 ligne recalee sur 20.4 servi (verify.ts:71) |
| directoryListingChallenge | Sensitive Data Exposure | 1 | DONE (lot 8) | correct (non modifie) ; /ftp/acquisitions.md verifie live (solve) |
| exposedCredentialsChallenge | Sensitive Data Exposure | 2 | DONE (lot 8) | correct (non modifie) ; testing@juice-sh.op / IamUsedForTesting (login.ts:66) |
| passwordHashLeakChallenge | Sensitive Data Exposure | 2 | DONE (lot 8) | correct (non modifie) ; /rest/user/whoami?fields=password via COOKIE verifie live (currentUser.ts:52) |
| closeNotificationsChallenge | Miscellaneous | 1 | TODO |  |
| errorHandlingChallenge | Security Misconfiguration | 1 | DONE (lot 20) | correct (non modifie) ; GET /api/Users/abc -> 500, status>401 (verify.ts:77) ; verifie live |
| exposedMetricsChallenge | Observability Failures | 1 | DONE (lot 18) | correct (non modifie) ; GET /metrics verifie live (metrics.ts:68) |
| missingEncodingChallenge | Improper Input Validation | 1 | DONE (lot 3) | N2-N5 : glyphe unicode faux dans N2 (ᔚ -> ᓚ) ; # = separateur de fragment, %23 ; URL encodee verify.ts:71 ; teste |
| passwordRepeatChallenge | Improper Input Validation | 1 | TODO |  |
| redirectCryptoCurrencyChallenge | Unvalidated Redirects | 1 | DONE (lot 15) | correct (non modifie) ; /redirect?to=<adresse crypto exacte> verifie live (redirect.ts:17) |
| web3SandboxChallenge | Broken Access Control | 1 | DONE (lot 18) | N5 : mecanisme precise (pixel 11px.png, verify.ts:64) ; GET verifie live |
| zeroStarsChallenge | Improper Input Validation | 1 | DONE (lot 1) | N2-N5 reecrits : etoiles inventees -> mat-slider 1-5, bouton disabled par !rating ; API testee, voie UI deduite du code |
| deprecatedInterfaceChallenge | Security Misconfiguration | 2 | DONE (lot 20) | correct (non modifie) ; upload XML -> solve (fileUpload.ts:77) ; verifie live |
| emptyUserRegistration | Improper Input Validation | 2 | DONE (lot 1) | N4,N5 reecrits : securityQuestion non requise (teste) ; N3 conserve (passwordRepeat verifie) |
| geoStalkingMetaChallenge | Sensitive Data Exposure | 2 | DONE (lot 16) | N4-N5 : vecteur EXIF GPS (36 57N 84 20W), question 14 corrigee, reponse Daniel Boone National Forest ; reset non rejoue |
| geoStalkingVisualChallenge | Sensitive Data Exposure | 2 | DONE (lot 4) | N1-N5 : cible fausse (ville/monument -> nom d entreprise, question 10 "Company you first work for"), reponse ITsec verifiee en config/lab ; reset non rejoue (ne pas changer le mdp d Emma) |
| loginRapperChallenge | Sensitive Data Exposure | 2 | DONE (lot 16) | N4-N5 : email corrige (mc-safesearch -> mc.safesearch point), Mr. N00dles ; verifie live |
| nftUnlockChallenge | Sensitive Data Exposure | 2 | DONE (lot 12) | N4-N5 : seed vague -> seed BIP39 dans un avis seede, derivation cle privee + POST /rest/web3/submitKey verifie live |
| securityPolicyChallenge | Miscellaneous | 2 | TODO |  |
| weakPasswordChallenge | Broken Authentication | 2 | DONE (lot 13) | correct (non modifie) ; admin@/admin123 verifie live (login.ts:60) |
| weirdCryptoChallenge | Cryptographic Issues | 2 | DONE (lot 12) | correct (non modifie) ; base64 via complaint verifie live (verify.ts:254) |
| loginAdminChallenge | Injection | 2 | DONE (lot 5) | correct ; payload ' OR true-- verifie live (retourne admin), solve = id admin (login.ts:70) ; N3 precise (2026-11-16) : l'ecran n'affiche que [object Object] (comportement OWASP d'origine, verifie 19.2.1 et 20.4), l'erreur SQL se lit dans Reseau |
| adminSectionChallenge | Broken Access Control | 2 | DONE (lot 2) | N2-N5 : garde AdminGuard cote client (jwtDecode sans signature), validation = image 19px.png (verify.ts:65), 3 familles de contournement ; voie deduite du code, non rejouee (Chrome) ; 2026-11-16 lignes recalees sur 20.4 servi (html:127, verify.ts:69), voie rejouee en recette 13/13 |
| basketAccessChallenge | Broken Access Control | 2 | DONE (lot 9) | correct (non modifie) ; GET /rest/basket/<autre bid> verifie live (basket.ts:21) |
| feedbackChallenge | Broken Access Control | 2 | DONE (lot 9) | correct (non modifie) ; supprimer tous les avis 5 etoiles (count rating=5 -> 0) ; non rejoue (destructif pour donnees seedees) ; 2026-11-16 N4 reecrit : bouton jamais disabled (administration.component.html:78), scenario 'erreurs de permission' invente retire ; DELETE /api/Feedbacks/:id autorise par session seule (server.ts:394 servi), verifie jim 200 / anonyme 401 |
| basketManipulateChallenge | Broken Access Control | 3 | DONE (lot 9) | N4-N5 : pack faux (BasketId simple -> 401 Invalid BasketId). Vraie voie = double cle BasketId (mienne 1er passe le check, victime en dernier inseree) via parseJsonCustom ; verifie live |
| captchaBypassChallenge | Broken Anti Automation | 3 | DONE (lot 20) | N4-N5 : endpoint corrige (/api/captcha -> /rest/captcha), 10 feedbacks < 20s ; verifie live |
| changeProductChallenge | Broken Access Control | 3 | DONE (lot 1) | N4,N5 reecrits : target="_blank" obligatoire (verify.ts), sans jeton ; defense inventee remplacee par codefixes fix 3 ; teste |
| csafChallenge | Miscellaneous | 3 | DONE (lot 2) | N2-N5 : chemin faux (csaf-aggregator -> /.well-known/csaf/), advisory express-jwt identifie, piege fins de ligne (hash recalcule different si EOL modifiees) ; soumission teste |
| dbSchemaChallenge | Injection | 3 | DONE (lot 5) | correct ; payload UNION ... FROM sqlite_master (9 colonnes) verifie live (CREATE TABLE) ; non modifie |
| forgedFeedbackChallenge | Broken Access Control | 3 | DONE (lot 9) | correct (non modifie) ; POST /api/Feedbacks UserId!=moi verifie live (solveIf avant captcha, verify.ts:29) |
| forgedReviewChallenge | Broken Access Control | 3 | DONE (lot 9) | correct ; PUT /rest/products/:id/reviews author=autre (createProductReviews.ts:17) verifie live + PATCH edit avis d autrui (updateProductReviews.ts:24) code-confirme |
| freeDeluxeChallenge | Improper Input Validation | 3 | DONE (lot 3) | N2-N5 : UserId du corps ecrase par appendUserId (trompeur), pre-requis role customer ; solve = 3e valeur de paymentMode (deluxe.ts) ; teste (paymentMode:none) |
| ghostLoginChallenge | Broken Authentication | 3 | DONE (lot 13) | N4-N5 : hashcat invente -> SQLi sur compte supprime chris (deletedAt contourne par le commentaire) ; chris.pike@juice-sh.op verifie live |
| loginAmyChallenge | Sensitive Data Exposure | 3 | DONE (lot 16) | N4-N5 : mot de passe FAUX (K1f...Bo0m! -> K1f + 21 points, 24 car.) verifie live |
| loginBenderChallenge | Injection | 3 | DONE (lot 5) | N4-N5 : requete exacte (table Users + AND deletedAt IS NULL), citation ligne corrigee (loginBender.ts:101) ; payload verifie live |
| loginJimChallenge | Injection | 3 | DONE (lot 5) | N3-N5 : email jim@juice-sh.op visible dans les avis produit (verifie served), citations fausses corrigees (:90, pas :99-101) ; payload verifie live |
| negativeOrderChallenge | Improper Input Validation | 3 | DONE (lot 10) | N4-N5 : endpoint checkout faux (/api/Orders -> /rest/basket/:id/checkout) ; PUT quantity=-10 + checkout verifie live |
| nftMintChallenge | Improper Input Validation | 3 | TODO |  |
| persistedXssUserChallenge | XSS | 3 | DONE (lot 7) | N2-N5 : CHAMP FAUX (Address streetAddress -> EMAIL, models/user.ts) ; POST /api/Users email=payload verifie live (201, solved) |
| privacyPolicyProofChallenge | Security through Obscurity | 3 | TODO |  |
| registerAdminChallenge | Improper Input Validation | 3 | DONE (lot 10) | correct (non modifie) ; POST /api/Users role=admin verifie live (verify.ts:51) |
| resetPasswordBjoernOwaspChallenge | Broken Authentication | 3 | DONE (lot 6) | N1-N5 : EMAIL FAUX (gmail -> bjoern@owasp.org, verifie live : gmail = pas de question), reponse Zaya (resetPassword.ts:62) |
| resetPasswordJimChallenge | Broken Authentication | 3 | DONE (lot 6) | N1-N5 : question fausse (eldest sibling -> eldest siblings MIDDLE name) ; reponse Samuel (middle name de George Samuel Kirk) ; question verifiee live, reponse source (resetPassword.ts:58) |
| restfulXssChallenge | XSS | 3 | DONE (lot 7) | N4-N5 : auth JWT inutile (PUT /api/Products/:id sans jeton) verifie live ; description setter (product.ts:47) |
| uploadSizeChallenge | Improper Input Validation | 3 | DONE (lot 10) | N4-N5 : taille fausse (200KB rejete, multer plafonne a 200000) ; cible 100-200KB, 150KB verifie live (204, sans auth) |
| uploadTypeChallenge | Improper Input Validation | 3 | DONE (lot 10) | correct (non modifie) ; POST /file-upload .png verifie live, sans auth (fileUpload.ts:69) |
| xxeFileDisclosureChallenge | XXE | 3 | DONE (lot 15) | correct (non modifie) ; upload XML XXE file:///etc/passwd verifie live (fileUpload.ts:85) |
| accessLogDisclosureChallenge | Observability Failures | 4 | DONE (lot 15) | correct (non modifie) ; GET /support/logs/access.log verifie live (verify.ts:72) |
| christmasSpecialChallenge | Injection | 4 | DONE (lot 14) | correct (non modifie) ; SQLi search OR true-- (soft-delete), produit id 10 + checkout verifie live |
| dataExportChallenge | Sensitive Data Exposure | 4 | DONE (lot 19) | N4-N5 : mecanisme reel (prefixe orderId = hash email au moment commande vs hash email courant) ; commande + changement email + export ; captcha image, non rejoue de bout en bout |
| dlpPastebinDataLeakChallenge | Sensitive Data Exposure | 4 | DONE (lot 19) | N4-N5 : mots-cles exacts hueteroneel + eurogium edule (produit Rippertuer), Op.and ; soumission verifiee live |
| easterEggLevelOneChallenge | Broken Access Control | 4 | TODO |  |
| easterEggLevelTwoChallenge | Cryptographic Issues | 4 | DONE (lot 12) | N4-N5 : etape Base64 manquante avant ROT13 (eastere.gg est base64 puis rot13) ; URL GET verifiee live |
| ephemeralAccountantChallenge | Injection | 4 | DONE (lot 14) | N4-N5 : role FAUX (accountant -> accounting), 9 col -> 13, totpSecret vide sinon 2FA ; UNION 13 col verifie live |
| forgottenBackupChallenge | Sensitive Data Exposure | 4 | DONE (lot 8) | correct ; null-byte coupons_2013.md.bak%2500.md verifie live ; FR corrige (renvoi manipulateClock -> forgedCoupon, EN etait deja bon) |
| forgottenDevBackupChallenge | Sensitive Data Exposure | 4 | DONE (lot 8) | correct (non modifie) ; null-byte /ftp/package.json.bak%2500.md verifie live |
| hiddenImageChallenge | Security through Obscurity | 4 | DONE (lot 2) | N1-N5 : faux hint OWASP cite, reponse donnee des N3, image inventee ; chaine pickle rick verifiee (verify.ts:287) ; image porteuse 5.png deduite, extraction non reussie |
| httpHeaderXssChallenge | XSS | 4 | DONE (lot 7) | correct (non modifie) ; header True-Client-IP = payload exact (saveLoginIp.ts:23) |
| knownVulnerableComponentChallenge | Vulnerable Components | 4 | DONE (lot 11) | correct (non modifie) ; sanitize-html+1.4.2 / express-jwt+0.1.3 via complaint verifie live |
| manipulateClockChallenge | Improper Input Validation | 4 | DONE (lot 3) | N4-N5 : endpoint faux (/api/Orders -> /rest/basket/:id/checkout), couponData dans le corps du checkout ; base64 WMNSDY2019 correct ; teste |
| misplacedSignatureFileChallenge | Observability Failures | 4 | DONE (lot 18) | N4-N5 : null-byte verifie %2500 (suspicious_errors.yml, fileServer.ts:44) ; verifie live |
| noSqlCommandChallenge | Injection | 4 | DONE (lot 1) | N2,N4,N5 reecrits : endpoint et mecanisme faux (POST objet -> GET path, plafond 2000 ms, duree > 2000 ms) ; payload sleep(200) teste |
| noSqlReviewsChallenge | Injection | 4 | DONE (lot 14) | correct (non modifie) ; PATCH id={$ne:-1} modifie plusieurs avis verifie live (updateProductReviews.ts:23) |
| nullByteChallenge | Improper Input Validation | 4 | DONE (lot 10) | correct (non modifie) ; null-byte sur encrypt.pyc / auto-solve via les autres defis /ftp (fileServer.ts:46) |
| oauthUserPasswordChallenge | Broken Authentication | 4 | DONE (lot 13) | correct (non modifie) ; bjoern.kimminich@gmail.com / base64(reverse email) verifie live (login.ts:65) |
| persistedXssFeedbackChallenge | XSS | 4 | DONE (lot 3) | N2-N5 : pre-requis file-disclosure recadre (pedagogique, pas technique), sanitize-html 1.4.2, payload <<iframe>... verifie (produit la chaine exacte) ; validation = chaine stockee (feedback.ts) |
| redirectChallenge | Unvalidated Redirects | 4 | DONE (lot 15) | N4-N5 : chemin obsolete (bkimminich -> juice-shop/juice-shop) ; faille includes(), payload attacker.com?x=<allowlist> verifie live |
| resetPasswordBenderChallenge | Broken Authentication | 4 | DONE (lot 6) | N3-N5 : question exacte (Company you first work for), reponse exacte Stop'n'Drop (orthographe) ; source resetPassword.ts:59 ; question verifiee live |
| resetPasswordUvoginChallenge | Sensitive Data Exposure | 4 | DONE (lot 19) | N4-N5 : question corrigee (anime -> Your favorite movie Q12), reponse Silence of the Lambs (resetPassword.ts:63) ; reset non rejoue |
| typosquattingNpmChallenge | Vulnerable Components | 4 | DONE (lot 11) | correct (non modifie) ; epilogue-js via complaint verifie live |
| unionSqlInjectionChallenge | Injection | 4 | DONE (lot 5) | correct ; payload UNION ... FROM Users (9 colonnes) verifie live (emails exfiltres) ; non modifie |
| usernameXssChallenge | XSS | 4 | DONE (lot 7) | N2-N5 : mecanisme FAUX (username=nonce -> CSP injectee via Image URL profileImage + sanitizeLegacy regex) ; payloads du test cypress officiel, bypass regex verifie hors ligne ; disabledEnv Docker |
| localXssChallenge | XSS | 1 | DONE (lot 7) | correct (non modifie) ; payload iframe dans le champ de recherche, solve websocket (registerWebsocketEvents.ts:42) |
| reflectedXssChallenge | XSS | 2 | DONE (lot 7) | N2-N5 : route /#/track-result?id=, sink bypassSecurityTrustHtml, solve trackOrder.ts ; ajout note disabledEnv Docker/Heroku/Gitpod |
| xssBonusChallenge | XSS | 1 | DONE (lot 1) | N5 : mecanisme de validation corrige (websocket verifyLocalXssChallenge) + defense |
| changePasswordBenderChallenge | Broken Authentication | 5 | DONE (lot 13) | correct ; GET change-password?new=slurmCl4ssic&repeat=slurmCl4ssic SANS current (changePassword.ts:53) verifie live |
| dlpPasswordSprayingChallenge | Observability Failures | 5 | DONE (lot 16) | N5 blinde ; vraie source = fuite access.log (pas spraying), J12934@ / mot de passe exact verifie live |
| emailLeakChallenge | Sensitive Data Exposure | 5 | DONE (lot 19) | N4-N5 : vrai mecanisme JSONP (whoami?callback=, currentUser.ts:57) ; verifie live |
| extraLanguageChallenge | Broken Anti Automation | 5 | DONE (lot 20) | correct (non modifie) ; GET /assets/i18n/tlh_AA.json (Klingon, verify.ts:68) ; verifie live |
| jwtUnsignedChallenge | Vulnerable Components | 5 | DONE (lot 11) | N4-N5 : exp lointain manquant (verif echoue sans), livraison via Authorization/localStorage ; forge alg=none jwtn3d@ verifie live |
| killChatbotChallenge | Vulnerable Components | 5 | DONE (lot 17) | N4-N5 : vecteur FAUX (template throw -> injection code dans username du profil, payload test cypress) ; code-confirme |
| leakedApiKeyChallenge | Sensitive Data Exposure | 5 | DONE (lot 19) | N4-N5 : cle exacte 6PPi37DBxP4lDwlriuaxP15HaDJpsUXY5TspVmie via feedback/complaint ; verifie live |
| lfrChallenge | Vulnerable Components | 5 | DONE (lot 17) | N4-N5 : moteur hbs, payload reel layout=../package.json + cookie (pas header), package.json faux ; verifie live (dataErasure.ts) |
| noSqlOrdersChallenge | Injection | 5 | DONE (lot 14) | N4-N5 : objet $ne FAUX -> injection JS dans la chaine $where ; verifie live (trackOrder.ts:20) |
| rceChallenge | Insecure Deserialization | 5 | DONE (lot 17) | N4-N5 : endpoint corrige (/api/b2b -> /b2b/v2/orders), while(true){} -> Infinite loop detected ; verifie live (b2bOrder.ts:31) |
| resetPasswordBjoernChallenge | Broken Authentication | 5 | DONE (lot 6) | N1-N5 : question fausse (lieu/ecole -> code postal ado), OSINT recadre (twist historique = format PLZ pre-1993), reponse West-2082 (resetPassword.ts:60) ; question verifiee live |
| resetPasswordMortyChallenge | Broken Anti Automation | 5 | DONE (lot 6) | N1-N5 : scripts bash bruteforce retires, faille rate-limit X-Forwarded-For exacte (server.ts:344-347 max 100/5min), reponse 5N0wb41L (resetPassword.ts:61) ; question verifiee live |
| retrieveBlueprintChallenge | Sensitive Data Exposure | 5 | DONE (lot 3) | N3-N5 : indice EXIF corrige (Make=OpenSCAD, pas Comment/Description ; chemin non dans EXIF), fichier JuiceShop.stl sous /assets/public/images/products/ (verify.ts:69) ; servi teste |
| supplyChainAttackChallenge | Vulnerable Components | 5 | DONE (lot 17) | correct (non modifie) ; eslint-scope/issues/39 via complaint verifie live (verify.ts:291) |
| svgInjectionChallenge | Security Misconfiguration | 5 | DONE (lot 20) | N4-N5 : vecteur FAUX (fichier SVG -> param testDecal sur /#/deluxe-membership via /redirect), payload test cypress avec suffixe github pour isRedirectAllowed ; code-confirme |
| tokenSaleChallenge | Security through Obscurity | 5 | TODO |  |
| twoFactorAuthUnsafeSecretStorageChallenge | Broken Authentication | 5 | DONE (lot 13) | N4-N5 : hashcat sur mdp fort retire -> vrai defaut = totpSecret en clair (users.yml), exfil SQLi + TOTP + /rest/2fa/verify verifie live (2fa.ts:44) |
| typosquattingAngularChallenge | Vulnerable Components | 5 | DONE (lot 11) | correct (non modifie) ; ngy-cookie via complaint verifie live |
| xxeDosChallenge | XXE | 5 | DONE (lot 15) | correct (non modifie) ; XML /dev/random ou blowup -> timeout ; code-confirme (DoS non rejoue), disabledEnv Docker |
| yamlBombChallenge | Insecure Deserialization | 5 | TODO |  |
| continueCodeChallenge | Cryptographic Issues | 6 | DONE (lot 2) | N1 sans endpoint ; N4-N5 : PUT (GET = 500, teste), alphabet sans espaces parasites ; encode(999) + PUT teste |
| fileWriteChallenge | Vulnerable Components | 6 | DONE (lot 17) | correct (non modifie) ; zip slip ../../ftp/legal.md (fileUpload.ts:43) ; code-confirme (non rejoue, ecraserait legal.md) |
| forgedCouponChallenge | Cryptographic Issues | 6 | DONE (lot 12) | N4-N5 : XOR invente -> vrai algo z85(MMMYY-80) mois MAJUSCULE ; coupon applique+checkout verifie live |
| jwtForgedChallenge | Vulnerable Components | 6 | DONE (lot 11) | N4-N5 : cle = jwt.pub servie de CETTE instance (octets exacts, token fige echoue), disabledEnv Windows ; HS256 key-confusion rsa_lord@ forge et verifie live |
| loginSupportChallenge | Security Misconfiguration | 6 | DONE (lot 16) | N5 blinde ; source kdbx /ftp/incident-support.kdbx + crack, email support@ / mot de passe exact verifie live |
| premiumPaywallChallenge | Cryptographic Issues | 6 | DONE (lot 12) | N4-N5 : AES invente (hints nient toute crypto) -> securite par obscurite, URL cachee en clair ; GET URL verifie live |
| rceOccupyChallenge | Insecure Deserialization | 6 | DONE (lot 18) | N4-N5 : endpoint (/b2b/v2/orders) + payload FAUX (for borne = boucle detectee -> ReDoS) ; 503 timeout 2.0s verifie live |
| ssrfChallenge | Broken Access Control | 6 | DONE (lot 18) | N4-N5 : flux simplifie/exact (image URL profil -> /solve/challenges/server-side interne, puis GET avec key) ; verifie live |
| sstiChallenge | Injection | 6 | DONE (lot 14) | N4-N5 : vecteur FAUX (b2b -> eval des accolades diese dans le username du profil, userProfile.ts:54) + endpoint /solve/challenges/server-side ; vecteur code-confirme, chaine malware non rejouee |
| timingAttackChallenge | Broken Anti Automation | 6 | TODO |  |
| videoXssChallenge | XSS | 6 | DONE (lot 4) | N2-N5 : enabler faux (rceOccupy -> fileWriteChallenge/Arbitrary File Write), cible = sous-titres owasp_promo.vtt (pas la video), sink = bloc <script id=subtitle> (videoHandler.ts:58) ; chaine non rejouee |
| web3WalletChallenge | Miscellaneous | 6 | DONE (lot 4) | N1-N5 : quote OWASP inventee corrigee, endpoint /rest/web3/walletExploitAddress, event on-chain ContractExploited (Sepolia, contrat 0x4137..7b0) ; source Solidity hors depot = vuln non verifiable ici ; non rejoue (testnet) |
