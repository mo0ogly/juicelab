# Corrections des indices JuiceLab - 2026-11-16

Synthese des corrections apportees aux indices (hints N1-N5) des challenges
du parcours pendant la revue du 2026-11-16. Complement du tracker detaille
`docs/HINTS-REVIEW-20261116.md` (statut + preuve par challenge) et des
commits `fix(juicelab): verified hints lot N`.

## Methode

Chaque indice a ete confronte au code source d'OWASP Juice Shop 19.2.1
(route, condition `solveIf`, defense canonique dans `codefixes/`), puis le
payload du niveau N5 a ete rejoue sur l'instance de recette locale
(`http://127.0.0.1:43119`) quand l'operation etait non destructive. Les
packs deja exacts n'ont pas ete reecrits (regle qualite), seulement
verifies. Les reponses sensibles non rejouables (reset de mot de passe,
transaction testnet) ont ete confirmees en lecture de source.

## Synthese chiffree

- Challenges revus : **64** / 109
- Packs corriges : **43**
  - erreurs bloquantes (un eleve suivant le pack echouait) : **28**
  - corrections mineures (precision, citation, note de version) : **15**
- Packs deja corrects (verifies, non modifies) : **21**

Nettoyages transverses : retrait des **198 etiquettes internes**
`[KILL_CHAIN_*]` affichees aux eleves (65 fichiers), et
**resynchronisation du miroir** `overlay/data/juicelab-private/` (39 hints
+ 1 quiz perimes).

## Types d'erreurs recurrents

| Motif d'erreur | Exemples |
|---|---|
| Mauvais endpoint / verbe HTTP | manipulateClock, negativeOrder, continueCode |
| Mauvais champ ou cible | persistedXssUser (email), geoStalkingVisual (entreprise) |
| Mauvais identifiant | resetPasswordBjoernOwasp (gmail -> owasp.org) |
| Mecanisme invente | forgedCoupon (XOR), premiumPaywall (AES), usernameXss (nonce) |
| Payload hors limites | uploadSize (200 KB > plafond multer), basketManipulate (401) |
| Mauvaise question ou reponse | resetPasswordJim, resetPasswordBjoern |
| Etape manquante | easterEggLevelTwo (base64 avant rot13) |

## Corrections bloquantes

| Challenge | Categorie | Correction (erreur -> fix, preuve) |
|---|---|---|
| `changeProductChallenge` | Broken Access Control | N4,N5 reecrits : target="_blank" obligatoire (verify.ts), sans jeton ; defense inventee remplacee par codefixes fix 3 ; teste |
| `emptyUserRegistration` | Improper Input Validation | N4,N5 reecrits : securityQuestion non requise (teste) ; N3 conserve (passwordRepeat verifie) |
| `noSqlCommandChallenge` | Injection | N2,N4,N5 reecrits : endpoint et mecanisme faux (POST objet -> GET path, plafond 2000 ms, duree > 2000 ms) ; payload sleep(200) teste |
| `xssBonusChallenge` | XSS | N5 : mecanisme de validation corrige (websocket verifyLocalXssChallenge) + defense |
| `zeroStarsChallenge` | Improper Input Validation | N2-N5 reecrits : etoiles inventees -> mat-slider 1-5, bouton disabled par !rating ; API testee, voie UI deduite du code |
| `continueCodeChallenge` | Cryptographic Issues | N1 sans endpoint ; N4-N5 : PUT (GET = 500, teste), alphabet sans espaces parasites ; encode(999) + PUT teste |
| `csafChallenge` | Miscellaneous | N2-N5 : chemin faux (csaf-aggregator -> /.well-known/csaf/), advisory express-jwt identifie, piege fins de ligne (hash recalcule different si EOL modifiees) ; soumission teste |
| `hiddenImageChallenge` | Security through Obscurity | N1-N5 : faux hint OWASP cite, reponse donnee des N3, image inventee ; chaine pickle rick verifiee (verify.ts:287) ; image porteuse 5.png deduite, extraction non reussie |
| `manipulateClockChallenge` | Improper Input Validation | N4-N5 : endpoint faux (/api/Orders -> /rest/basket/:id/checkout), couponData dans le corps du checkout ; base64 WMNSDY2019 correct ; teste |
| `missingEncodingChallenge` | Improper Input Validation | N2-N5 : glyphe unicode faux dans N2 (ᔚ -> ᓚ) ; # = separateur de fragment, %23 ; URL encodee verify.ts:71 ; teste |
| `geoStalkingVisualChallenge` | Sensitive Data Exposure | N1-N5 : cible fausse (ville/monument -> nom d entreprise, question 10 "Company you first work for"), reponse ITsec verifiee en config/lab ; reset non rejoue (ne pas changer le mdp d Emma) |
| `videoXssChallenge` | XSS | N2-N5 : enabler faux (rceOccupy -> fileWriteChallenge/Arbitrary File Write), cible = sous-titres owasp_promo.vtt (pas la video), sink = bloc <script id=subtitle> (videoHandler.ts:58) ; chaine non rejouee |
| `web3WalletChallenge` | Miscellaneous | N1-N5 : quote OWASP inventee corrigee, endpoint /rest/web3/walletExploitAddress, event on-chain ContractExploited (Sepolia, contrat 0x4137..7b0) ; source Solidity hors depot = vuln non verifiable ici ; non rejoue (testnet) |
| `loginJimChallenge` | Injection | N3-N5 : email jim@juice-sh.op visible dans les avis produit (verifie served), citations fausses corrigees (:90, pas :99-101) ; payload verifie live |
| `resetPasswordBenderChallenge` | Broken Authentication | N3-N5 : question exacte (Company you first work for), reponse exacte Stop'n'Drop (orthographe) ; source resetPassword.ts:59 ; question verifiee live |
| `resetPasswordBjoernChallenge` | Broken Authentication | N1-N5 : question fausse (lieu/ecole -> code postal ado), OSINT recadre (twist historique = format PLZ pre-1993), reponse West-2082 (resetPassword.ts:60) ; question verifiee live |
| `resetPasswordBjoernOwaspChallenge` | Broken Authentication | N1-N5 : EMAIL FAUX (gmail -> bjoern@owasp.org, verifie live : gmail = pas de question), reponse Zaya (resetPassword.ts:62) |
| `resetPasswordJimChallenge` | Broken Authentication | N1-N5 : question fausse (eldest sibling -> eldest siblings MIDDLE name) ; reponse Samuel (middle name de George Samuel Kirk) ; question verifiee live, reponse source (resetPassword.ts:58) |
| `resetPasswordMortyChallenge` | Broken Anti Automation | N1-N5 : scripts bash bruteforce retires, faille rate-limit X-Forwarded-For exacte (server.ts:344-347 max 100/5min), reponse 5N0wb41L (resetPassword.ts:61) ; question verifiee live |
| `persistedXssUserChallenge` | XSS | N2-N5 : CHAMP FAUX (Address streetAddress -> EMAIL, models/user.ts) ; POST /api/Users email=payload verifie live (201, solved) |
| `usernameXssChallenge` | XSS | N2-N5 : mecanisme FAUX (username=nonce -> CSP injectee via Image URL profileImage + sanitizeLegacy regex) ; payloads du test cypress officiel, bypass regex verifie hors ligne ; disabledEnv Docker |
| `basketManipulateChallenge` | Broken Access Control | N4-N5 : pack faux (BasketId simple -> 401 Invalid BasketId). Vraie voie = double cle BasketId (mienne 1er passe le check, victime en dernier inseree) via parseJsonCustom ; verifie live |
| `negativeOrderChallenge` | Improper Input Validation | N4-N5 : endpoint checkout faux (/api/Orders -> /rest/basket/:id/checkout) ; PUT quantity=-10 + checkout verifie live |
| `uploadSizeChallenge` | Improper Input Validation | N4-N5 : taille fausse (200KB rejete, multer plafonne a 200000) ; cible 100-200KB, 150KB verifie live (204, sans auth) |
| `forgedCouponChallenge` | Cryptographic Issues | N4-N5 : XOR invente -> vrai algo z85(MMMYY-80) mois MAJUSCULE ; coupon applique+checkout verifie live |
| `nftUnlockChallenge` | Sensitive Data Exposure | N4-N5 : seed vague -> seed BIP39 dans un avis seede, derivation cle privee + POST /rest/web3/submitKey verifie live |
| `premiumPaywallChallenge` | Cryptographic Issues | N4-N5 : AES invente (hints nient toute crypto) -> securite par obscurite, URL cachee en clair ; GET URL verifie live |
| `ghostLoginChallenge` | Broken Authentication | N4-N5 : hashcat invente -> SQLi sur compte supprime chris (deletedAt contourne par le commentaire) ; chris.pike@juice-sh.op verifie live |

## Corrections mineures et precisions

| Challenge | Categorie | Correction |
|---|---|---|
| `adminSectionChallenge` | Broken Access Control | N2-N5 : garde AdminGuard cote client (jwtDecode sans signature), validation = image 19px.png (verify.ts:65), 3 familles de contournement ; voie deduite du code, non rejouee (Chrome) |
| `privacyPolicyChallenge` | Miscellaneous | N3-N5 : validation = image 81px.png (verify.ts:67), pas un appel API ; libelles de menu verifies |
| `freeDeluxeChallenge` | Improper Input Validation | N2-N5 : UserId du corps ecrase par appendUserId (trompeur), pre-requis role customer ; solve = 3e valeur de paymentMode (deluxe.ts) ; teste (paymentMode:none) |
| `persistedXssFeedbackChallenge` | XSS | N2-N5 : pre-requis file-disclosure recadre (pedagogique, pas technique), sanitize-html 1.4.2, payload <<iframe>... verifie (produit la chaine exacte) ; validation = chaine stockee (feedback.ts) |
| `retrieveBlueprintChallenge` | Sensitive Data Exposure | N3-N5 : indice EXIF corrige (Make=OpenSCAD, pas Comment/Description ; chemin non dans EXIF), fichier JuiceShop.stl sous /assets/public/images/products/ (verify.ts:69) ; servi teste |
| `loginBenderChallenge` | Injection | N4-N5 : requete exacte (table Users + AND deletedAt IS NULL), citation ligne corrigee (loginBender.ts:101) ; payload verifie live |
| `reflectedXssChallenge` | XSS | N2-N5 : route /#/track-result?id=, sink bypassSecurityTrustHtml, solve trackOrder.ts ; ajout note disabledEnv Docker/Heroku/Gitpod |
| `restfulXssChallenge` | XSS | N4-N5 : auth JWT inutile (PUT /api/Products/:id sans jeton) verifie live ; description setter (product.ts:47) |
| `forgottenBackupChallenge` | Sensitive Data Exposure | correct ; null-byte coupons_2013.md.bak%2500.md verifie live ; FR corrige (renvoi manipulateClock -> forgedCoupon, EN etait deja bon) |
| `forgedReviewChallenge` | Broken Access Control | correct ; PUT /rest/products/:id/reviews author=autre (createProductReviews.ts:17) verifie live + PATCH edit avis d autrui (updateProductReviews.ts:24) code-confirme |
| `jwtForgedChallenge` | Vulnerable Components | N4-N5 : cle = jwt.pub servie de CETTE instance (octets exacts, token fige echoue), disabledEnv Windows ; HS256 key-confusion rsa_lord@ forge et verifie live |
| `jwtUnsignedChallenge` | Vulnerable Components | N4-N5 : exp lointain manquant (verif echoue sans), livraison via Authorization/localStorage ; forge alg=none jwtn3d@ verifie live |
| `easterEggLevelTwoChallenge` | Cryptographic Issues | N4-N5 : etape Base64 manquante avant ROT13 (eastere.gg est base64 puis rot13) ; URL GET verifiee live |
| `changePasswordBenderChallenge` | Broken Authentication | correct ; GET change-password?new=slurmCl4ssic&repeat=slurmCl4ssic SANS current (changePassword.ts:53) verifie live |
| `twoFactorAuthUnsafeSecretStorageChallenge` | Broken Authentication | N4-N5 : hashcat sur mdp fort retire -> vrai defaut = totpSecret en clair (users.yml), exfil SQLi + TOTP + /rest/2fa/verify verifie live (2fa.ts:44) |

## Packs verifies deja corrects (non modifies)

| Challenge | Categorie | Verification |
|---|---|---|
| `dbSchemaChallenge` | Injection | correct ; payload UNION ... FROM sqlite_master (9 colonnes) verifie live (CREATE TABLE) ; non modifie |
| `loginAdminChallenge` | Injection | correct ; payload ' OR true-- verifie live (retourne admin), solve = id admin (login.ts:70) ; non modifie |
| `unionSqlInjectionChallenge` | Injection | correct ; payload UNION ... FROM Users (9 colonnes) verifie live (emails exfiltres) ; non modifie |
| `httpHeaderXssChallenge` | XSS | correct (non modifie) ; header True-Client-IP = payload exact (saveLoginIp.ts:23) |
| `localXssChallenge` | XSS | correct (non modifie) ; payload iframe dans le champ de recherche, solve websocket (registerWebsocketEvents.ts:42) |
| `directoryListingChallenge` | Sensitive Data Exposure | correct (non modifie) ; /ftp/acquisitions.md verifie live (solve) |
| `exposedCredentialsChallenge` | Sensitive Data Exposure | correct (non modifie) ; testing@juice-sh.op / IamUsedForTesting (login.ts:66) |
| `forgottenDevBackupChallenge` | Sensitive Data Exposure | correct (non modifie) ; null-byte /ftp/package.json.bak%2500.md verifie live |
| `passwordHashLeakChallenge` | Sensitive Data Exposure | correct (non modifie) ; /rest/user/whoami?fields=password via COOKIE verifie live (currentUser.ts:52) |
| `basketAccessChallenge` | Broken Access Control | correct (non modifie) ; GET /rest/basket/<autre bid> verifie live (basket.ts:21) |
| `feedbackChallenge` | Broken Access Control | correct (non modifie) ; supprimer tous les avis 5 etoiles (count rating=5 -> 0) ; non rejoue (destructif pour donnees seedees) |
| `forgedFeedbackChallenge` | Broken Access Control | correct (non modifie) ; POST /api/Feedbacks UserId!=moi verifie live (solveIf avant captcha, verify.ts:29) |
| `nullByteChallenge` | Improper Input Validation | correct (non modifie) ; null-byte sur encrypt.pyc / auto-solve via les autres defis /ftp (fileServer.ts:46) |
| `registerAdminChallenge` | Improper Input Validation | correct (non modifie) ; POST /api/Users role=admin verifie live (verify.ts:51) |
| `uploadTypeChallenge` | Improper Input Validation | correct (non modifie) ; POST /file-upload .png verifie live, sans auth (fileUpload.ts:69) |
| `knownVulnerableComponentChallenge` | Vulnerable Components | correct (non modifie) ; sanitize-html+1.4.2 / express-jwt+0.1.3 via complaint verifie live |
| `typosquattingAngularChallenge` | Vulnerable Components | correct (non modifie) ; ngy-cookie via complaint verifie live |
| `typosquattingNpmChallenge` | Vulnerable Components | correct (non modifie) ; epilogue-js via complaint verifie live |
| `weirdCryptoChallenge` | Cryptographic Issues | correct (non modifie) ; base64 via complaint verifie live (verify.ts:254) |
| `oauthUserPasswordChallenge` | Broken Authentication | correct (non modifie) ; bjoern.kimminich@gmail.com / base64(reverse email) verifie live (login.ts:65) |
| `weakPasswordChallenge` | Broken Authentication | correct (non modifie) ; admin@/admin123 verifie live (login.ts:60) |

## Points ouverts (repris du tracker)

- Les packs sont verifies contre **Juice Shop 19.2.1**. Le lab TD tourne
  en **20.4.0-SNAPSHOT** (4 fichiers divergents) : validite non
  re-etablie sur cette version.
- `usernameXss` et `reflectedXss` sont **desactives en Docker**
  (safetyMode) ; `jwtForged` est desactive sous Windows.
- Les defis non rejoues (reset de mot de passe, web3 testnet, videoXss)
  sont confirmes en lecture de code ; leur statut est signale dans
  chaque niveau N5.
