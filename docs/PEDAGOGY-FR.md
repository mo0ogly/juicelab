# PEDAGOGY — Fondements pédagogiques de JuiceLab

> Version anglaise : [PEDAGOGY.md](./PEDAGOGY.md).

Ce document explique le *pourquoi* de la conception de JuiceLab. Chaque élément d'interface, chaque valeur par défaut, chaque règle de déverrouillage renvoie à l'un des trois piliers pédagogiques décrits ci-dessous.

> **Public visé** — enseignants qui évaluent si JuiceLab convient à leur cours, et contributeurs souhaitant rédiger un nouveau pack pédagogique et qui ont besoin de comprendre les contraintes de conception. Si vous voulez simplement *utiliser* JuiceLab, [`README.md`](../README.md) est suffisant.

## Table des matières

- [Pilier 1 — La Zone Proximale de Développement de Vygotski](#pilier-1--la-zone-proximale-de-développement-de-vygotski)
- [Pilier 2 — La Taxonomie de Bloom](#pilier-2--la-taxonomie-de-bloom)
- [Pilier 3 — Remise de preuve inviolable](#pilier-3--remise-de-preuve-inviolable)
- [Pourquoi un TD sur OWASP Juice Shop, et non Hack The Box ou TryHackMe](#pourquoi-un-td-sur-owasp-juice-shop-et-non-hack-the-box-ou-tryhackme)
- [Le parcours de 13 défis et la justification de ces 13 choix](#le-parcours-de-13-défis-et-la-justification-de-ces-13-choix)
- [Calibration de la cohorte d'indices : pourquoi 5 / 10 / 20 / 35 / 50](#calibration-de-la-cohorte-dindices--pourquoi-5--10--20--35--50)
- [Conception du quiz : pourquoi des QCM plutôt que des réponses libres](#conception-du-quiz--pourquoi-des-qcm-plutôt-que-des-réponses-libres)
- [La salle des trophées cachée : motivation intrinsèque vs extrinsèque](#la-salle-des-trophées-cachée--motivation-intrinsèque-vs-extrinsèque)
- [Références](#références)

---

## Pilier 1 — La Zone Proximale de Développement de Vygotski

Un défi se situe dans la Zone Proximale de Développement (ZPD) d'un étudiant lorsqu'il ne peut pas le résoudre seul, mais **peut** le résoudre avec la bonne quantité de guidage de la part d'une personne plus compétente. Trop peu de guidage engendre frustration et abandon. Trop de guidage amène l'étudiant à reproduire la solution sans rien apprendre.

Le *Mind in Society* de Lev Vygotski (1978) décrit un mécanisme d'« étayage » (*scaffolding*) : la personne plus compétente fournit des indices progressifs, chaque indice réduisant l'espace de recherche sans révéler la réponse. À mesure que l'étudiant gravit les indices, la charge cognitive est allégée pas à pas.

JuiceLab encode cet étayage sous la forme d'une échelle d'indices à 5 niveaux. L'étudiant gravit l'échelle *dans l'ordre* — le serveur refuse de délivrer le niveau N+1 tant que le niveau N n'a pas été consulté et acquitté. Chaque niveau possède un `pedagogical_intent` explicite :

| Niveau | Coût | Intention | Fonction cognitive activée |
|---|---|---|---|
| **N1** | 5 % | Question socratique | Réflexe / réorientation de l'attention sans révéler |
| **N2** | 10 % | Direction de recherche | Localiser la famille OWASP / MITRE / CWE |
| **N3** | 20 % | Indice technique | Identifier la surface et le *type* de charge utile |
| **N4** | 35 % | Étapes guidées | Liste ordonnée de ce qu'il faut faire, sans la charge utile |
| **N5** | 50 % | Solution complète | La charge utile exacte + la procédure détaillée |

Le coût n'est pas punitif. C'est un **dispositif d'engagement** : un étudiant qui clique sur N3 a accepté que le gain en clarté vaut 20 points. Sans coût, l'étudiant cliquerait sur tout immédiatement et n'apprendrait rien.

Le coût est également un **signal pour l'enseignant**. Le tableau de bord indique, par étudiant et par défi, quels niveaux ont été consultés. Un étudiant bloqué sur N4 depuis quinze minutes est celui qui a besoin d'un entretien individuel — pas celui qui a résolu sans aide, et pas celui qui n'a pas encore ouvert le dialogue.

> **Calibration empirique.** La cohorte 5/10/20/35/50 est issue de trois itérations d'observation en classe (cohortes M2 IA / Cybersécurité de la Sorbonne, 2025-2026). Les cohortes précédentes utilisaient 10/20/30/40/50 (linéaire) — les étudiants refusaient les indices trop agressivement parce que le coût initial semblait disproportionné par rapport au gain initial. La cohorte actuelle expose les premiers indices presque gratuitement (la question socratique est la moins chère car elle est la plus susceptible de suffire).

---

## Pilier 2 — La Taxonomie de Bloom

La *Taxonomy of Educational Objectives* de Benjamin Bloom (1956) organise les objectifs d'apprentissage en six niveaux : Mémoriser < Comprendre < Appliquer < Analyser < Évaluer < Créer. Un CTF traditionnel ne mesure que les deux premiers : l'étudiant mémorise l'astuce et l'applique. JuiceLab ajoute un quiz qui cible les niveaux 3 à 5 :

```
Mémoriser   ----> "Qu'est-ce que le XSS ?"                 (PAS ce que JuiceLab demande)
Comprendre  ----> l'onglet de présentation le fait implicitement
Appliquer   ----> résoudre le défi dans Juice Shop le fait
Analyser    ----> Q1 du quiz : "Quelle catégorie de l'OWASP Top 10 ai-je exploitée ?"
Évaluer     ----> Q2 du quiz : "Quelle défense aurait empêché cela ?"
Créer       ----> Q3 du quiz : "Comment généraliseriez-vous à une autre application ?"
```

Le score du quiz `(Q1 + Q2 + Q3) / 3` est moyenné avec le score du défi. La note finale récompense ainsi *à la fois* le faire et le comprendre — le fossé que Juice Shop seul laisse béant.

> **La taxonomie révisée de Bloom (Anderson 2001)** est cohérente avec cette conception : l'axe des processus cognitifs est identique à ces cinq niveaux (nous avons intégré Comprendre dans l'onglet de présentation). La dimension des connaissances est implicite — le quiz teste des connaissances *conceptuelles* et *procédurales*, pas factuelles.

---

## Pilier 3 — Remise de preuve inviolable

Le troisième pilier est administratif, mais il transforme la pédagogie. À la fin de chaque défi, l'étudiant télécharge un fichier Markdown signé HMAC-SHA-256 par le tableau de bord. Ce fichier contient :

- Le résumé du défi (pour que l'enseignant sache exactement ce que l'étudiant a tenté).
- L'entrée de journal (pour que l'enseignant sache ce que l'étudiant a compris).
- Les indices consultés (pour que l'enseignant sache où l'étudiant a bloqué).
- Les réponses au quiz et les scores par question.
- Le détail du score selon la formule canonique.
- Un horodatage.

L'enseignant vérifie les signatures avec le script autonome `dashboard/verify_proof.py` — sans avoir à faire confiance à la capture d'écran de l'étudiant, à l'URL du tableau de bord, ni même à sa disponibilité. La preuve est portable et auto-suffisante.

Pourquoi cela compte pédagogiquement :

1. **L'étudiant écrit lui-même le récit de sa note.** L'entrée de journal est la voix de l'étudiant. En l'obligeant à articuler ce qu'il a compris (5 mots minimum pour activer Enregistrer), JuiceLab favorise l'auto-explication, que la littérature (Chi 1989) montre constamment comme l'une des interventions d'apprentissage les plus efficaces.
2. **L'enseignant évalue des preuves, pas des souvenirs.** Avec 30 étudiants et 13 défis, l'enseignant dispose de 390 événements à évaluer. Une preuve signée par défi × étudiant est vérifiable, archivable et contrôlable des mois plus tard. Sans cela, l'enseignant s'appuierait sur des captures d'écran, des e-mails et des fils Slack — aucun de ces moyens ne passe à l'échelle.
3. **L'étudiant repart avec un portfolio.** À l'issue du TD de 12 heures, chaque étudiant dispose de 13 preuves signées dans son dossier de téléchargements. Il peut les inclure dans son portfolio pour un stage en pentest, les remettre à son prochain employeur, ou simplement les relire six mois plus tard lorsqu'il rencontre une vulnérabilité similaire dans la vraie vie.

---

## Pourquoi un TD sur OWASP Juice Shop, et non Hack The Box ou TryHackMe

| Plateforme | Adéquation pédagogique | Pourquoi JuiceLab lui est préféré |
|---|---|---|
| OWASP Juice Shop | Excellent pour la sécurité des applications web, déploiement en binaire unique, chaque défi correspond à un cas réel de l'OWASP Top 10. | C'est le substrat ; JuiceLab ajoute la couche d'étayage manquante. |
| Hack The Box | Excellent pour la progression individuelle, mais payant, basé sur des machines et non sur des concepts, et la courbe de difficulté est hostile à une cohorte débutante de 12 heures. | Hors du périmètre pour une salle hétérogène. |
| TryHackMe | Meilleure pédagogie que HTB (les rooms ont une intention), mais les rooms constituent un curriculum appartenant à un tiers. L'enseignant ne peut pas les réordonner, les approfondir ni y ajouter des contraintes. | JuiceLab est le curriculum que l'enseignant maîtrise ; Juice Shop est le moteur. |
| CTF personnalisé | Contrôle maximal, mais travail maximal. Un enseignant qui construit un CTF de zéro y consacre des semaines ; JuiceLab est l'affaire d'une après-midi. | Rentable. |

Juice Shop possède en outre trois propriétés qu'aucune autre plateforme ne réunit simultanément :

1. **Entièrement local, sans cloud ni télémétrie.** Chaque étudiant dispose de son propre conteneur ; rien ne quitte la salle de classe.
2. **La correspondance avec l'OWASP Top 10 est canonique.** Chaque défi cite la famille OWASP, la technique MITRE ATT&CK, et (pour les plus difficiles) le CWE.
3. **Le mode CTF est intégré.** Le flux de saisie de flag sur lequel s'appuie le Mode C est une fonctionnalité de Juice Shop, non un correctif de JuiceLab.

---

## Le parcours de 13 défis et la justification de ces 13 choix

Le parcours s'inscrit dans un TD de 12 heures réparti en trois demi-journées (DJ1, DJ2, DJ3). Cinq défis en DJ1 car c'est la matinée la plus longue ; quatre dans chacune des DJ2 et DJ3 car la profondeur conceptuelle augmente.

| DJ | # | Clé | Famille OWASP | Pourquoi inclus |
|---|---|---|---|---|
| 1 | 1 | `scoreBoardChallenge` | A05 Security Misconfiguration | Brise-glace. Enseigne *réfléchissez avant de cliquer* — le lien est dans le code source de la page. |
| 1 | 2 | `privacyPolicyChallenge` | A01 Broken Access Control (sans impact sur la note, mais modèle mental) | L'étudiant constate qu'« absence de lien » ne signifie pas « absence de chemin ». |
| 1 | 3 | `directoryListingChallenge` | A05 Security Misconfiguration | L'étudiant ouvre un dossier non prévu. Concept : listage activé par défaut. |
| 1 | 4 | `exposedCredentialsChallenge` | A07 Identification and Authentication Failures | L'étudiant fouille un bundle JS à la recherche de credentials. Concept : le front-end n'est pas privé. |
| 1 | 5 | `passwordHashLeakChallenge` | A02 Cryptographic Failures | Première exposition aux hashs. Concept : un hash n'est pas un secret s'il est en ligne. |
| 2 | 1 | `loginAdminChallenge` | A03 Injection (SQLi) | Le défi phare. Injection SQL sur le formulaire de connexion. |
| 2 | 2 | `adminSectionChallenge` | A01 Broken Access Control | L'étudiant trouve l'URL d'administration par déduction ou en lisant les routes. |
| 2 | 3 | `basketAccessChallenge` | A01 Broken Access Control | IDOR sur le panier — l'étudiant modifie un paramètre de requête. |
| 2 | 4 | `feedbackChallenge` | A01 Broken Access Control | L'étudiant forge un retour d'expérience au nom d'une autre personne. |
| 3 | 1 | `localXssChallenge` | A03 Injection (XSS, basé DOM) | Premier XSS. Concept : le fragment d'URL est rendu. |
| 3 | 2 | `reflectedXssChallenge` | A03 Injection (XSS, réfléchi) | Concept : une chaîne de requête peut être réfléchie. |
| 3 | 3 | `xssBonusChallenge` | A03 Injection (XSS, variation de charge utile) | Pratique — même surface, charge utile différente. |
| 3 | 4 | `bullyChatbotChallenge` | A03 Injection (injection de prompt LLM) | Passerelle vers la sécurité de l'IA. Concept : un LLM n'est qu'un chemin de code parmi d'autres. |

Le parcours est calibré pour qu'un étudiant type :

- Résolve **DJ1 en 4 heures** avec au maximum 1 à 2 indices par défi.
- Résolve **DJ2 en 4 heures** avec 2 à 3 indices sur `loginAdmin` et 1 à 2 sur les autres.
- Résolve **DJ3 en 4 heures** avec un rythme similaire et la passerelle vers la sécurité LLM à la fin.

> **Pourquoi ne pas inclure `usernameXssChallenge` ou `persistedXssFeedbackChallenge` ?** Ces deux défis sont excellents, mais ils exigent que l'étudiant ait résolu des défis antérieurs, et un TD de 12 heures ne laisse pas cette marge. Ils constituent de bons prolongements pour un second TD.

---

## Calibration de la cohorte d'indices : pourquoi 5 / 10 / 20 / 35 / 50

Trois contraintes à satisfaire simultanément :

1. La cohorte doit **totaliser plus de 100** afin que consommer les 5 indices réduise à zéro le score du défi (abandon total). 5+10+20+35+50 = 120, ramené à 0 par la formule.
2. La cohorte doit être **strictement croissante** afin que chaque nouvel indice soit plus informatif que le précédent (et donc plus coûteux).
3. La cohorte doit **concentrer les indices bon marché en tête** afin qu'un étudiant en légère difficulté paie un faible prix pour une légère clarification — et soit donc plus enclin à les utiliser.

La cohorte 5/10/20/35/50 satisfait ces trois contraintes. Elle présente en outre une quatrième propriété appréciable : **un étudiant qui consulte N1 + N2 + N3 conserve encore 65 % du score du défi** et, combiné à un quiz parfait, obtient plus de 80 / 100 au final. C'est la calibration recherchée : un étudiant qui a besoin de trois indices est malgré tout récompensé.

> **Qu'en est-il de 1 / 2 / 5 / 10 / 20 (somme = 38) ?** Le score ne descend jamais en dessous de 62, même avec tous les indices. Les étudiants s'en aperçoivent et cliquent sur tout — les indices deviennent le chemin par défaut. Mauvaise calibration.

> **Qu'en est-il de 10 / 20 / 30 / 40 / 50 (linéaire, somme = 150) ?** Les premiers indices sont trop coûteux. Les étudiants refusent N1 même lorsqu'ils sont bloqués. Mauvaise calibration.

La cohorte actuelle a été validée sur deux promotions (environ 60 étudiants) de M2 IA / Cybersécurité. La distribution des indices est approximativement de Poisson avec λ ≈ 1,2 : la plupart des étudiants consultent 0 à 2 indices par défi, très peu vont jusqu'à N4 ou N5.

---

## Conception du quiz : pourquoi des QCM plutôt que des réponses libres

Les quiz à réponse libre sont pédagogiquement plus riches (ils forcent l'articulation), mais opérationnellement intenables dans un TD de 12 heures avec 30 étudiants :

- La notation des réponses libres repose soit (a) sur la correspondance de mots-clés (que l'étudiant peut contourner), soit (b) sur une correction humaine (que l'enseignant ne peut pas effectuer pendant le TD).
- La réponse libre prend plus de temps à rédiger et à lire que d'effectuer un choix, et le TD dispose déjà d'un emploi du temps serré.
- L'onglet journal offre déjà à l'étudiant un espace de réponse libre où l'articulation constitue l'objectif même.

Le quiz est donc à choix multiples avec 4 options. Chaque option est **plausible** (les mauvaises options doivent être défendables — un étudiant qui n'a pas intériorisé le concept doit hésiter). La quatrième option est parfois le leurre qui piège une idée reçue courante.

Le quiz utilise une **égalité stricte** côté serveur (`ans === q.correct`). Pas de crédit partiel. L'étudiant obtient soit 0, soit 100 par question. C'est un choix délibéré : le quiz est rapide (3 questions, 30 secondes) et la granularité est pédagogiquement non pertinente — ce qui compte, c'est que l'étudiant ait compris, pas dans quelle mesure.

---

## La salle des trophées cachée : motivation intrinsèque vs extrinsèque

`/#/cabinet` n'est mentionné dans aucun résumé, aucun lien, aucune barre de navigation. L'étudiant la trouve en devinant l'URL — et cette découverte est elle-même la récompense pédagogique.

La littérature (Deci et Ryan, *Self-Determination Theory*, 1985) soutient que la motivation intrinsèque favorise un apprentissage plus profond que la motivation extrinsèque. La salle des trophées est le levier intrinsèque : la satisfaction d'avoir trouvé une salle cachée, peuplée des trophées dorés des propres flags vérifiés de l'étudiant.

Le score, le tableau de bord, la preuve — ce sont des leviers extrinsèques (signaux à destination des enseignants et des correcteurs). La salle des trophées est l'antidote.

> **Note opérationnelle.** La salle des trophées lit `state.challenges[key].flag_captured` dans le LocalStorage de l'étudiant. Un étudiant qui efface les données de son navigateur perd ses trophées, mais conserve l'enregistrement du tableau de bord (qui est côté serveur). Les deux stockages sont indépendants intentionnellement — la salle des trophées appartient à l'étudiant, le tableau de bord appartient à l'enseignant.

---

## Références

| Référence | Utilisée pour |
|---|---|
| Vygotsky, L. S. (1978). *Mind in Society : The Development of Higher Psychological Processes.* Harvard University Press. | Pilier 1 (ZPD, étayage) |
| Bloom, B. S. (1956). *Taxonomy of Educational Objectives.* Longmans, Green. | Pilier 2 (niveaux cognitifs) |
| Anderson, L. W., and Krathwohl, D. R. (Eds.). (2001). *A Taxonomy for Learning, Teaching, and Assessing : A Revision of Bloom's Taxonomy of Educational Objectives.* Longman. | Révision du Pilier 2 |
| Chi, M. T. H., Bassok, M., Lewis, M. W., Reimann, P., and Glaser, R. (1989). *Self-explanations : How students study and use examples in learning to solve problems.* Cognitive Science. | Pilier 3 (journal comme auto-explication) |
| Deci, E. L., and Ryan, R. M. (1985). *Intrinsic Motivation and Self-Determination in Human Behavior.* Plenum. | Salle des trophées cachée |
| Keshav, S. (2007). *How to Read a Paper.* ACM SIGCOMM CCR. | Protocole d'ancrage des sources pour les nouveaux packs (`.claude/rules/owasp-pedagogy-companion.md`) |
| OWASP. (2021). *Top 10 — A01 to A10.* | Correspondance des défis |
| OWASP. (2025). *Juice Shop documentation.* | Substrat |
| MITRE. (2024). *ATT&CK Enterprise Matrix.* | Correspondance croisée pour les packs avancés |
| MITRE. (2024). *CWE Top 25.* | Référence croisée pour les défenses |
