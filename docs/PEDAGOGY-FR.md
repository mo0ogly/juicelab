# Pédagogie de JuiceLab

JuiceLab ajoute une couche d’accompagnement à OWASP Juice Shop pour le parcours
M2 de douze heures. Les améliorations du 14 novembre portent sur cette couche ;
elles ne changent pas les mécanismes des défis. L’intégration existante applique
un patch de raccordement : « surcouche » ne signifie pas absence de tout patch.

Version anglaise : [PEDAGOGY.md](PEDAGOGY.md).

## Séance pilote en deux demi journées

Le [kit pilote francophone](pilote-juicelab/LIRE_AVANT_DISTRIBUTION.txt) réunit le
PowerPoint, les consignes, la première installation, la reprise d’un ancien labo,
le compte rendu et les évaluations. La préparation sélectionne des passages des
cours S1 ISI5, avec leurs [références vérifiées](pilote-juicelab/REFERENCES_COURS.md).
Deux blocs de quatre heures sont proposés ; ils ne garantissent pas treize
résolutions individuelles. Le parcours produit de douze heures reste distinct.

## Avant pendant et après le défi

Chaque briefing public du parcours présente une mission d’apprentissage, deux
objectifs, les prérequis et le travail attendu. Il ne donne pas la procédure de
résolution. Le périmètre reste le laboratoire local autorisé.

Les indices privés sont révélés par les routes pédagogiques existantes, dans
l’ordre N1 à N5. Leur rôle est affiché avant consultation : question de réflexion,
direction, indice technique, étapes guidées, puis solution complète. Cette
révision ne modifie ni leurs procédures techniques ni les walkthroughs.

Après le défi, le journal demande une observation accompagnée de sa preuve et
d’une limite, une explication, une protection justifiée et un transfert défensif
vers une application fictive différente. Le QCM fournit un score automatique ;
il ne suffit pas à démontrer la capacité d’analyse ou de création. Le professeur
évalue le raisonnement avec la [grille dédiée](TEACHER-GUIDE-FR.md).

Enregistrer le journal exige cinq mots dans l’interface existante. Le conseil de
cinquante mots est une aide à la rédaction ; les badges conservent leur propre
règle de longueur. Aucune de ces longueurs ne mesure la qualité de la réponse.
La synchronisation du journal dépend de la configuration et de sa réception par
le dashboard. Un enregistrement local ne prouve pas cette réception.

## Parcours actif

Base de livraison : 20.4.0-SNAPSHOT, commit décrit dans [DOCKER.md](DOCKER.md).
Le [catalogue public](../overlay/frontend/src/assets/juicelab/selected_challenges.yml)
contient les treize défis ci-dessous, comme les badges. Le catalogue étendu
historique est [conservé séparément](reference/selected-challenges-legacy-20260511.yml) ;
il n’est pas une liste validée pour cette version.

| Demi-journée | Ordre | Défi | Clé |
| --- | --- | --- | --- |
| 1 | 1 | Score Board | `scoreBoardChallenge` |
| 1 | 2 | Privacy Policy | `privacyPolicyChallenge` |
| 1 | 3 | Confidential Document | `directoryListingChallenge` |
| 1 | 4 | Exposed credentials | `exposedCredentialsChallenge` |
| 1 | 5 | Password Hash Leak | `passwordHashLeakChallenge` |
| 2 | 1 | Login Admin | `loginAdminChallenge` |
| 2 | 2 | Admin Section | `adminSectionChallenge` |
| 2 | 3 | View Basket | `basketAccessChallenge` |
| 2 | 4 | Five-Star Feedback | `feedbackChallenge` |
| 3 | 1 | DOM XSS | `localXssChallenge` |
| 3 | 2 | Reflected XSS | `reflectedXssChallenge` |
| 3 | 3 | Bonus Payload | `xssBonusChallenge` |
| 3 | 4 | Forged Feedback | `forgedFeedbackChallenge` |

## Barème expliqué

Les coûts 5, 10, 20, 35 et 50 s’additionnent ; ils ne remplacent pas le coût
précédent. Score défi = max(0, 100 − somme des coûts). Score final par défi après
quiz = min(100, arrondi((score défi + score quiz)/2) + bonus flag).
L’arrondi de la preuve et du dashboard est l’arrondi Python à l’entier le plus
proche, égalités vers l’entier pair. Le bonus existant vaut dix points après
vérification du flag, zéro sinon. Sans quiz, seule une valeur partielle est
présentée : aucune note finale n’est déduite d’un quiz absent.

| Indices consultés | Coût cumulé | Score défi | Quiz | Bonus | Score final |
| --- | --- | --- | --- | --- | --- |
| Aucun | 0 | 100 | 100 | 0 | 100 |
| N1 | 5 | 95 | 100 | 0 | 98 |
| N1 à N3 | 35 | 65 | 100 | 0 | 82 |
| N1 à N5 | 120 | 0 | 100 | 0 | 50 |
| N1 à N5 | 120 | 0 | 100 | 10 | 60 |

Le plancher de l’overlay est aligné sur la preuve professeur à zéro ; les
anciennes sauvegardes score_net ne sont pas une note de référence. Le panneau
d’indices recalcule son affichage à partir des niveaux consommés. Les attestations
agrégées de cohorte restent distinctes d’une preuve par défi.

## Évaluer et mesurer

Le [sujet avant après](ASSESSMENT-FR.md) utilise deux situations défensives inédites,
sans service payant et sans nouvelle exploitation. La [grille professeur](TEACHER-GUIDE-FR.md)
fournit les attendus, le crédit partiel et un protocole de comparaison. La grille
manuelle sur huit points reste distincte du score automatique ; elle ne modifie
pas rétroactivement les notes ou événements existants.

L’effet des cinq niveaux, la durée de résolution et le gain d’apprentissage
restent à mesurer. Les anciennes affirmations de deux promotions, environ
soixante étudiants et distribution de Poisson ne sont pas étayées par un jeu de
mesures rapproché ; elles ne sont pas reprises comme résultats. La réduction
éventuelle de la réticence à demander un indice est une hypothèse.

## Portée des preuves

Une signature HMAC permet de vérifier l’intégrité d’une preuve sous les
hypothèses de gestion de la clé. Elle ne prouve pas la vérité des événements
reçus, l’identité de leur auteur ou sa compréhension. Une carte verte seule ne
prouve pas un effet métier. La recette du défi13 reste ouverte avec son critère
complet : voir [RECETTE-20261114.md](RECETTE-20261114.md).

Référence du quiz13 corrigé : [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
permissions à chaque requête, contrôles par objet et localisation côté serveur.
Un middleware commun ne dispense pas des règles métier nécessaires.
