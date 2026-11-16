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
- **Arbre `juice-shop` modifié** : ~1068 fichiers ne diffèrent que par les
  fins de ligne (antérieur à la revue, propriétaire non identifié). Effet
  observé : le JSON CSAF de l'arbre (et celui du lab 43119) n'a plus le
  SHA-512 attendu ; `HEAD` et le lab 43120 l'ont.

## Suivi par challenge (109 du parcours)

| key | catégorie | diff. | statut | notes |
|---|---|---|---|---|
| scoreBoardChallenge | Miscellaneous | 1 | TODO |  |
| privacyPolicyChallenge | Miscellaneous | 1 | DONE (lot 2) | N3-N5 : validation = image 81px.png (verify.ts:67), pas un appel API ; libelles de menu verifies |
| directoryListingChallenge | Sensitive Data Exposure | 1 | TODO |  |
| exposedCredentialsChallenge | Sensitive Data Exposure | 2 | TODO |  |
| passwordHashLeakChallenge | Sensitive Data Exposure | 2 | TODO |  |
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
| nftUnlockChallenge | Sensitive Data Exposure | 2 | TODO |  |
| securityPolicyChallenge | Miscellaneous | 2 | TODO |  |
| weakPasswordChallenge | Broken Authentication | 2 | TODO |  |
| weirdCryptoChallenge | Cryptographic Issues | 2 | TODO |  |
| loginAdminChallenge | Injection | 2 | DONE (lot 5) | correct ; payload ' OR true-- verifie live (retourne admin), solve = id admin (login.ts:70) ; non modifie |
| adminSectionChallenge | Broken Access Control | 2 | DONE (lot 2) | N2-N5 : garde AdminGuard cote client (jwtDecode sans signature), validation = image 19px.png (verify.ts:65), 3 familles de contournement ; voie deduite du code, non rejouee (Chrome) |
| basketAccessChallenge | Broken Access Control | 2 | TODO |  |
| feedbackChallenge | Broken Access Control | 2 | TODO |  |
| basketManipulateChallenge | Broken Access Control | 3 | TODO |  |
| captchaBypassChallenge | Broken Anti Automation | 3 | TODO |  |
| changeProductChallenge | Broken Access Control | 3 | DONE (lot 1) | N4,N5 reecrits : target="_blank" obligatoire (verify.ts), sans jeton ; defense inventee remplacee par codefixes fix 3 ; teste |
| csafChallenge | Miscellaneous | 3 | DONE (lot 2) | N2-N5 : chemin faux (csaf-aggregator -> /.well-known/csaf/), advisory express-jwt identifie, piege fins de ligne (hash recalcule different si EOL modifiees) ; soumission teste |
| dbSchemaChallenge | Injection | 3 | DONE (lot 5) | correct ; payload UNION ... FROM sqlite_master (9 colonnes) verifie live (CREATE TABLE) ; non modifie |
| forgedFeedbackChallenge | Broken Access Control | 3 | TODO |  |
| forgedReviewChallenge | Broken Access Control | 3 | TODO |  |
| freeDeluxeChallenge | Improper Input Validation | 3 | DONE (lot 3) | N2-N5 : UserId du corps ecrase par appendUserId (trompeur), pre-requis role customer ; solve = 3e valeur de paymentMode (deluxe.ts) ; teste (paymentMode:none) |
| ghostLoginChallenge | Broken Authentication | 3 | TODO |  |
| loginAmyChallenge | Sensitive Data Exposure | 3 | TODO |  |
| loginBenderChallenge | Injection | 3 | DONE (lot 5) | N4-N5 : requete exacte (table Users + AND deletedAt IS NULL), citation ligne corrigee (loginBender.ts:101) ; payload verifie live |
| loginJimChallenge | Injection | 3 | DONE (lot 5) | N3-N5 : email jim@juice-sh.op visible dans les avis produit (verifie served), citations fausses corrigees (:90, pas :99-101) ; payload verifie live |
| negativeOrderChallenge | Improper Input Validation | 3 | TODO |  |
| nftMintChallenge | Improper Input Validation | 3 | TODO |  |
| persistedXssUserChallenge | XSS | 3 | TODO |  |
| privacyPolicyProofChallenge | Security through Obscurity | 3 | TODO |  |
| registerAdminChallenge | Improper Input Validation | 3 | TODO |  |
| resetPasswordBjoernOwaspChallenge | Broken Authentication | 3 | DONE (lot 6) | N1-N5 : EMAIL FAUX (gmail -> bjoern@owasp.org, verifie live : gmail = pas de question), reponse Zaya (resetPassword.ts:62) |
| resetPasswordJimChallenge | Broken Authentication | 3 | DONE (lot 6) | N1-N5 : question fausse (eldest sibling -> eldest siblings MIDDLE name) ; reponse Samuel (middle name de George Samuel Kirk) ; question verifiee live, reponse source (resetPassword.ts:58) |
| restfulXssChallenge | XSS | 3 | TODO |  |
| uploadSizeChallenge | Improper Input Validation | 3 | TODO |  |
| uploadTypeChallenge | Improper Input Validation | 3 | TODO |  |
| xxeFileDisclosureChallenge | XXE | 3 | TODO |  |
| accessLogDisclosureChallenge | Observability Failures | 4 | TODO |  |
| christmasSpecialChallenge | Injection | 4 | TODO |  |
| dataExportChallenge | Sensitive Data Exposure | 4 | TODO |  |
| dlpPastebinDataLeakChallenge | Sensitive Data Exposure | 4 | TODO |  |
| easterEggLevelOneChallenge | Broken Access Control | 4 | TODO |  |
| easterEggLevelTwoChallenge | Cryptographic Issues | 4 | TODO |  |
| ephemeralAccountantChallenge | Injection | 4 | TODO |  |
| forgottenBackupChallenge | Sensitive Data Exposure | 4 | TODO |  |
| forgottenDevBackupChallenge | Sensitive Data Exposure | 4 | TODO |  |
| hiddenImageChallenge | Security through Obscurity | 4 | DONE (lot 2) | N1-N5 : faux hint OWASP cite, reponse donnee des N3, image inventee ; chaine pickle rick verifiee (verify.ts:287) ; image porteuse 5.png deduite, extraction non reussie |
| httpHeaderXssChallenge | XSS | 4 | TODO |  |
| knownVulnerableComponentChallenge | Vulnerable Components | 4 | TODO |  |
| manipulateClockChallenge | Improper Input Validation | 4 | DONE (lot 3) | N4-N5 : endpoint faux (/api/Orders -> /rest/basket/:id/checkout), couponData dans le corps du checkout ; base64 WMNSDY2019 correct ; teste |
| misplacedSignatureFileChallenge | Observability Failures | 4 | TODO |  |
| noSqlCommandChallenge | Injection | 4 | DONE (lot 1) | N2,N4,N5 reecrits : endpoint et mecanisme faux (POST objet -> GET path, plafond 2000 ms, duree > 2000 ms) ; payload sleep(200) teste |
| noSqlReviewsChallenge | Injection | 4 | TODO |  |
| nullByteChallenge | Improper Input Validation | 4 | TODO |  |
| oauthUserPasswordChallenge | Broken Authentication | 4 | TODO |  |
| persistedXssFeedbackChallenge | XSS | 4 | DONE (lot 3) | N2-N5 : pre-requis file-disclosure recadre (pedagogique, pas technique), sanitize-html 1.4.2, payload <<iframe>... verifie (produit la chaine exacte) ; validation = chaine stockee (feedback.ts) |
| redirectChallenge | Unvalidated Redirects | 4 | TODO |  |
| resetPasswordBenderChallenge | Broken Authentication | 4 | DONE (lot 6) | N3-N5 : question exacte (Company you first work for), reponse exacte Stop'n'Drop (orthographe) ; source resetPassword.ts:59 ; question verifiee live |
| resetPasswordUvoginChallenge | Sensitive Data Exposure | 4 | TODO |  |
| typosquattingNpmChallenge | Vulnerable Components | 4 | TODO |  |
| unionSqlInjectionChallenge | Injection | 4 | DONE (lot 5) | correct ; payload UNION ... FROM Users (9 colonnes) verifie live (emails exfiltres) ; non modifie |
| usernameXssChallenge | XSS | 4 | TODO |  |
| localXssChallenge | XSS | 1 | TODO |  |
| reflectedXssChallenge | XSS | 2 | TODO |  |
| xssBonusChallenge | XSS | 1 | DONE (lot 1) | N5 : mecanisme de validation corrige (websocket verifyLocalXssChallenge) + defense |
| changePasswordBenderChallenge | Broken Authentication | 5 | TODO |  |
| dlpPasswordSprayingChallenge | Observability Failures | 5 | TODO |  |
| emailLeakChallenge | Sensitive Data Exposure | 5 | TODO |  |
| extraLanguageChallenge | Broken Anti Automation | 5 | TODO |  |
| jwtUnsignedChallenge | Vulnerable Components | 5 | TODO |  |
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
| twoFactorAuthUnsafeSecretStorageChallenge | Broken Authentication | 5 | TODO |  |
| typosquattingAngularChallenge | Vulnerable Components | 5 | TODO |  |
| xxeDosChallenge | XXE | 5 | TODO |  |
| yamlBombChallenge | Insecure Deserialization | 5 | TODO |  |
| continueCodeChallenge | Cryptographic Issues | 6 | DONE (lot 2) | N1 sans endpoint ; N4-N5 : PUT (GET = 500, teste), alphabet sans espaces parasites ; encode(999) + PUT teste |
| fileWriteChallenge | Vulnerable Components | 6 | TODO |  |
| forgedCouponChallenge | Cryptographic Issues | 6 | TODO |  |
| jwtForgedChallenge | Vulnerable Components | 6 | TODO |  |
| loginSupportChallenge | Security Misconfiguration | 6 | TODO |  |
| premiumPaywallChallenge | Cryptographic Issues | 6 | TODO |  |
| rceOccupyChallenge | Insecure Deserialization | 6 | TODO |  |
| ssrfChallenge | Broken Access Control | 6 | TODO |  |
| sstiChallenge | Injection | 6 | TODO |  |
| timingAttackChallenge | Broken Anti Automation | 6 | TODO |  |
| videoXssChallenge | XSS | 6 | DONE (lot 4) | N2-N5 : enabler faux (rceOccupy -> fileWriteChallenge/Arbitrary File Write), cible = sous-titres owasp_promo.vtt (pas la video), sink = bloc <script id=subtitle> (videoHandler.ts:58) ; chaine non rejouee |
| web3WalletChallenge | Miscellaneous | 6 | DONE (lot 4) | N1-N5 : quote OWASP inventee corrigee, endpoint /rest/web3/walletExploitAddress, event on-chain ContractExploited (Sepolia, contrat 0x4137..7b0) ; source Solidity hors depot = vuln non verifiable ici ; non rejoue (testnet) |
