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
| scoreBoardChallenge | Miscellaneous | 1 | DONE (lot 14) | N4-N5 : mecanisme precise (pixel 1px.png, verify.ts:63) comme adminSection/privacyPolicy ; GET verifie live |
| privacyPolicyChallenge | Miscellaneous | 1 | DONE (lot 2) | N3-N5 : validation = image 81px.png (verify.ts:67), pas un appel API ; libelles de menu verifies |
| directoryListingChallenge | Sensitive Data Exposure | 1 | DONE (lot 8) | correct (non modifie) ; /ftp/acquisitions.md verifie live (solve) |
| exposedCredentialsChallenge | Sensitive Data Exposure | 2 | DONE (lot 8) | correct (non modifie) ; testing@juice-sh.op / IamUsedForTesting (login.ts:66) |
| passwordHashLeakChallenge | Sensitive Data Exposure | 2 | DONE (lot 8) | correct (non modifie) ; /rest/user/whoami?fields=password via COOKIE verifie live (currentUser.ts:52) |
| closeNotificationsChallenge | Miscellaneous | 1 | TODO |  |
| errorHandlingChallenge | Security Misconfiguration | 1 | TODO |  |
| exposedMetricsChallenge | Observability Failures | 1 | TODO |  |
| missingEncodingChallenge | Improper Input Validation | 1 | DONE (lot 3) | N2-N5 : glyphe unicode faux dans N2 (ᔚ -> ᓚ) ; # = separateur de fragment, %23 ; URL encodee verify.ts:71 ; teste |
| passwordRepeatChallenge | Improper Input Validation | 1 | TODO |  |
| redirectCryptoCurrencyChallenge | Unvalidated Redirects | 1 | TODO |  |
| web3SandboxChallenge | Broken Access Control | 1 | TODO |  |
| zeroStarsChallenge | Improper Input Validation | 1 | DONE (lot 1) | N2-N5 reecrits : etoiles inventees -> mat-slider 1-5, bouton disabled par !rating ; API testee, voie UI deduite du code |
| deprecatedInterfaceChallenge | Security Misconfiguration | 2 | TODO |  |
| emptyUserRegistration | Improper Input Validation | 2 | DONE (lot 1) | N4,N5 reecrits : securityQuestion non requise (teste) ; N3 conserve (passwordRepeat verifie) |
| geoStalkingMetaChallenge | Sensitive Data Exposure | 2 | TODO |  |
| geoStalkingVisualChallenge | Sensitive Data Exposure | 2 | DONE (lot 4) | N1-N5 : cible fausse (ville/monument -> nom d entreprise, question 10 "Company you first work for"), reponse ITsec verifiee en config/lab ; reset non rejoue (ne pas changer le mdp d Emma) |
| loginRapperChallenge | Sensitive Data Exposure | 2 | TODO |  |
| nftUnlockChallenge | Sensitive Data Exposure | 2 | DONE (lot 12) | N4-N5 : seed vague -> seed BIP39 dans un avis seede, derivation cle privee + POST /rest/web3/submitKey verifie live |
| securityPolicyChallenge | Miscellaneous | 2 | TODO |  |
| weakPasswordChallenge | Broken Authentication | 2 | DONE (lot 13) | correct (non modifie) ; admin@/admin123 verifie live (login.ts:60) |
| weirdCryptoChallenge | Cryptographic Issues | 2 | DONE (lot 12) | correct (non modifie) ; base64 via complaint verifie live (verify.ts:254) |
| loginAdminChallenge | Injection | 2 | DONE (lot 5) | correct ; payload ' OR true-- verifie live (retourne admin), solve = id admin (login.ts:70) ; non modifie |
| adminSectionChallenge | Broken Access Control | 2 | DONE (lot 2) | N2-N5 : garde AdminGuard cote client (jwtDecode sans signature), validation = image 19px.png (verify.ts:65), 3 familles de contournement ; voie deduite du code, non rejouee (Chrome) |
| basketAccessChallenge | Broken Access Control | 2 | DONE (lot 9) | correct (non modifie) ; GET /rest/basket/<autre bid> verifie live (basket.ts:21) |
| feedbackChallenge | Broken Access Control | 2 | DONE (lot 9) | correct (non modifie) ; supprimer tous les avis 5 etoiles (count rating=5 -> 0) ; non rejoue (destructif pour donnees seedees) |
| basketManipulateChallenge | Broken Access Control | 3 | DONE (lot 9) | N4-N5 : pack faux (BasketId simple -> 401 Invalid BasketId). Vraie voie = double cle BasketId (mienne 1er passe le check, victime en dernier inseree) via parseJsonCustom ; verifie live |
| captchaBypassChallenge | Broken Anti Automation | 3 | TODO |  |
| changeProductChallenge | Broken Access Control | 3 | DONE (lot 1) | N4,N5 reecrits : target="_blank" obligatoire (verify.ts), sans jeton ; defense inventee remplacee par codefixes fix 3 ; teste |
| csafChallenge | Miscellaneous | 3 | DONE (lot 2) | N2-N5 : chemin faux (csaf-aggregator -> /.well-known/csaf/), advisory express-jwt identifie, piege fins de ligne (hash recalcule different si EOL modifiees) ; soumission teste |
| dbSchemaChallenge | Injection | 3 | DONE (lot 5) | correct ; payload UNION ... FROM sqlite_master (9 colonnes) verifie live (CREATE TABLE) ; non modifie |
| forgedFeedbackChallenge | Broken Access Control | 3 | DONE (lot 9) | correct (non modifie) ; POST /api/Feedbacks UserId!=moi verifie live (solveIf avant captcha, verify.ts:29) |
| forgedReviewChallenge | Broken Access Control | 3 | DONE (lot 9) | correct ; PUT /rest/products/:id/reviews author=autre (createProductReviews.ts:17) verifie live + PATCH edit avis d autrui (updateProductReviews.ts:24) code-confirme |
| freeDeluxeChallenge | Improper Input Validation | 3 | DONE (lot 3) | N2-N5 : UserId du corps ecrase par appendUserId (trompeur), pre-requis role customer ; solve = 3e valeur de paymentMode (deluxe.ts) ; teste (paymentMode:none) |
| ghostLoginChallenge | Broken Authentication | 3 | DONE (lot 13) | N4-N5 : hashcat invente -> SQLi sur compte supprime chris (deletedAt contourne par le commentaire) ; chris.pike@juice-sh.op verifie live |
| loginAmyChallenge | Sensitive Data Exposure | 3 | TODO |  |
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
| xxeFileDisclosureChallenge | XXE | 3 | TODO |  |
| accessLogDisclosureChallenge | Observability Failures | 4 | TODO |  |
| christmasSpecialChallenge | Injection | 4 | TODO |  |
| dataExportChallenge | Sensitive Data Exposure | 4 | TODO |  |
| dlpPastebinDataLeakChallenge | Sensitive Data Exposure | 4 | TODO |  |
| easterEggLevelOneChallenge | Broken Access Control | 4 | TODO |  |
| easterEggLevelTwoChallenge | Cryptographic Issues | 4 | DONE (lot 12) | N4-N5 : etape Base64 manquante avant ROT13 (eastere.gg est base64 puis rot13) ; URL GET verifiee live |
| ephemeralAccountantChallenge | Injection | 4 | TODO |  |
| forgottenBackupChallenge | Sensitive Data Exposure | 4 | DONE (lot 8) | correct ; null-byte coupons_2013.md.bak%2500.md verifie live ; FR corrige (renvoi manipulateClock -> forgedCoupon, EN etait deja bon) |
| forgottenDevBackupChallenge | Sensitive Data Exposure | 4 | DONE (lot 8) | correct (non modifie) ; null-byte /ftp/package.json.bak%2500.md verifie live |
| hiddenImageChallenge | Security through Obscurity | 4 | DONE (lot 2) | N1-N5 : faux hint OWASP cite, reponse donnee des N3, image inventee ; chaine pickle rick verifiee (verify.ts:287) ; image porteuse 5.png deduite, extraction non reussie |
| httpHeaderXssChallenge | XSS | 4 | DONE (lot 7) | correct (non modifie) ; header True-Client-IP = payload exact (saveLoginIp.ts:23) |
| knownVulnerableComponentChallenge | Vulnerable Components | 4 | DONE (lot 11) | correct (non modifie) ; sanitize-html+1.4.2 / express-jwt+0.1.3 via complaint verifie live |
| manipulateClockChallenge | Improper Input Validation | 4 | DONE (lot 3) | N4-N5 : endpoint faux (/api/Orders -> /rest/basket/:id/checkout), couponData dans le corps du checkout ; base64 WMNSDY2019 correct ; teste |
| misplacedSignatureFileChallenge | Observability Failures | 4 | TODO |  |
| noSqlCommandChallenge | Injection | 4 | DONE (lot 1) | N2,N4,N5 reecrits : endpoint et mecanisme faux (POST objet -> GET path, plafond 2000 ms, duree > 2000 ms) ; payload sleep(200) teste |
| noSqlReviewsChallenge | Injection | 4 | TODO |  |
| nullByteChallenge | Improper Input Validation | 4 | DONE (lot 10) | correct (non modifie) ; null-byte sur encrypt.pyc / auto-solve via les autres defis /ftp (fileServer.ts:46) |
| oauthUserPasswordChallenge | Broken Authentication | 4 | DONE (lot 13) | correct (non modifie) ; bjoern.kimminich@gmail.com / base64(reverse email) verifie live (login.ts:65) |
| persistedXssFeedbackChallenge | XSS | 4 | DONE (lot 3) | N2-N5 : pre-requis file-disclosure recadre (pedagogique, pas technique), sanitize-html 1.4.2, payload <<iframe>... verifie (produit la chaine exacte) ; validation = chaine stockee (feedback.ts) |
| redirectChallenge | Unvalidated Redirects | 4 | TODO |  |
| resetPasswordBenderChallenge | Broken Authentication | 4 | DONE (lot 6) | N3-N5 : question exacte (Company you first work for), reponse exacte Stop'n'Drop (orthographe) ; source resetPassword.ts:59 ; question verifiee live |
| resetPasswordUvoginChallenge | Sensitive Data Exposure | 4 | TODO |  |
| typosquattingNpmChallenge | Vulnerable Components | 4 | DONE (lot 11) | correct (non modifie) ; epilogue-js via complaint verifie live |
| unionSqlInjectionChallenge | Injection | 4 | DONE (lot 5) | correct ; payload UNION ... FROM Users (9 colonnes) verifie live (emails exfiltres) ; non modifie |
| usernameXssChallenge | XSS | 4 | DONE (lot 7) | N2-N5 : mecanisme FAUX (username=nonce -> CSP injectee via Image URL profileImage + sanitizeLegacy regex) ; payloads du test cypress officiel, bypass regex verifie hors ligne ; disabledEnv Docker |
| localXssChallenge | XSS | 1 | DONE (lot 7) | correct (non modifie) ; payload iframe dans le champ de recherche, solve websocket (registerWebsocketEvents.ts:42) |
| reflectedXssChallenge | XSS | 2 | DONE (lot 7) | N2-N5 : route /#/track-result?id=, sink bypassSecurityTrustHtml, solve trackOrder.ts ; ajout note disabledEnv Docker/Heroku/Gitpod |
| xssBonusChallenge | XSS | 1 | DONE (lot 1) | N5 : mecanisme de validation corrige (websocket verifyLocalXssChallenge) + defense |
| changePasswordBenderChallenge | Broken Authentication | 5 | DONE (lot 13) | correct ; GET change-password?new=slurmCl4ssic&repeat=slurmCl4ssic SANS current (changePassword.ts:53) verifie live |
| dlpPasswordSprayingChallenge | Observability Failures | 5 | TODO |  |
| emailLeakChallenge | Sensitive Data Exposure | 5 | TODO |  |
| extraLanguageChallenge | Broken Anti Automation | 5 | TODO |  |
| jwtUnsignedChallenge | Vulnerable Components | 5 | DONE (lot 11) | N4-N5 : exp lointain manquant (verif echoue sans), livraison via Authorization/localStorage ; forge alg=none jwtn3d@ verifie live |
| killChatbotChallenge | Vulnerable Components | 5 | TODO |  |
| leakedApiKeyChallenge | Sensitive Data Exposure | 5 | TODO |  |
| lfrChallenge | Vulnerable Components | 5 | TODO |  |
| noSqlOrdersChallenge | Injection | 5 | TODO |  |
| rceChallenge | Insecure Deserialization | 5 | TODO |  |
| resetPasswordBjoernChallenge | Broken Authentication | 5 | DONE (lot 6) | N1-N5 : question fausse (lieu/ecole -> code postal ado), OSINT recadre (twist historique = format PLZ pre-1993), reponse West-2082 (resetPassword.ts:60) ; question verifiee live |
| resetPasswordMortyChallenge | Broken Anti Automation | 5 | DONE (lot 6) | N1-N5 : scripts bash bruteforce retires, faille rate-limit X-Forwarded-For exacte (server.ts:344-347 max 100/5min), reponse 5N0wb41L (resetPassword.ts:61) ; question verifiee live |
| retrieveBlueprintChallenge | Sensitive Data Exposure | 5 | DONE (lot 3) | N3-N5 : indice EXIF corrige (Make=OpenSCAD, pas Comment/Description ; chemin non dans EXIF), fichier JuiceShop.stl sous /assets/public/images/products/ (verify.ts:69) ; servi teste |
| supplyChainAttackChallenge | Vulnerable Components | 5 | TODO |  |
| svgInjectionChallenge | Security Misconfiguration | 5 | TODO |  |
| tokenSaleChallenge | Security through Obscurity | 5 | TODO |  |
| twoFactorAuthUnsafeSecretStorageChallenge | Broken Authentication | 5 | DONE (lot 13) | N4-N5 : hashcat sur mdp fort retire -> vrai defaut = totpSecret en clair (users.yml), exfil SQLi + TOTP + /rest/2fa/verify verifie live (2fa.ts:44) |
| typosquattingAngularChallenge | Vulnerable Components | 5 | DONE (lot 11) | correct (non modifie) ; ngy-cookie via complaint verifie live |
| xxeDosChallenge | XXE | 5 | TODO |  |
| yamlBombChallenge | Insecure Deserialization | 5 | TODO |  |
| continueCodeChallenge | Cryptographic Issues | 6 | DONE (lot 2) | N1 sans endpoint ; N4-N5 : PUT (GET = 500, teste), alphabet sans espaces parasites ; encode(999) + PUT teste |
| fileWriteChallenge | Vulnerable Components | 6 | TODO |  |
| forgedCouponChallenge | Cryptographic Issues | 6 | DONE (lot 12) | N4-N5 : XOR invente -> vrai algo z85(MMMYY-80) mois MAJUSCULE ; coupon applique+checkout verifie live |
| jwtForgedChallenge | Vulnerable Components | 6 | DONE (lot 11) | N4-N5 : cle = jwt.pub servie de CETTE instance (octets exacts, token fige echoue), disabledEnv Windows ; HS256 key-confusion rsa_lord@ forge et verifie live |
| loginSupportChallenge | Security Misconfiguration | 6 | TODO |  |
| premiumPaywallChallenge | Cryptographic Issues | 6 | DONE (lot 12) | N4-N5 : AES invente (hints nient toute crypto) -> securite par obscurite, URL cachee en clair ; GET URL verifie live |
| rceOccupyChallenge | Insecure Deserialization | 6 | TODO |  |
| ssrfChallenge | Broken Access Control | 6 | TODO |  |
| sstiChallenge | Injection | 6 | TODO |  |
| timingAttackChallenge | Broken Anti Automation | 6 | TODO |  |
| videoXssChallenge | XSS | 6 | DONE (lot 4) | N2-N5 : enabler faux (rceOccupy -> fileWriteChallenge/Arbitrary File Write), cible = sous-titres owasp_promo.vtt (pas la video), sink = bloc <script id=subtitle> (videoHandler.ts:58) ; chaine non rejouee |
| web3WalletChallenge | Miscellaneous | 6 | DONE (lot 4) | N1-N5 : quote OWASP inventee corrigee, endpoint /rest/web3/walletExploitAddress, event on-chain ContractExploited (Sepolia, contrat 0x4137..7b0) ; source Solidity hors depot = vuln non verifiable ici ; non rejoue (testnet) |
