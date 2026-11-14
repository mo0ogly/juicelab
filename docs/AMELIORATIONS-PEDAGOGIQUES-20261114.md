# Améliorations de la couche pédagogique JuiceLab

Demande de Fabrice : améliorer son travail JuiceLab antérieur puis « fais tout »,
en conservant Juice Shop comme base. Ce lot modifie la surcouche, ses contenus,
son dashboard et ses supports ; aucun mécanisme de défi upstream n’est modifié
dans cet incrément. Le patch d’intégration préexistant est conservé. Aucun commit,
push ou publication externe n’est effectué.

## Résultat et portée

| Besoin | Réalisation | Vérification |
| --- | --- | --- |
| Parcours cohérent | Catalogue actif13 identique aux clés des badges ; catalogue110 historique archivé dans docs/reference | Test de correspondance et sélecteur réellement servi avec treize options |
| Avant le défi | Treize briefings FR/EN avec mission, objectifs, prérequis et travail attendu ; procédures retirées de ces briefings publics | Packs servis comparés aux sources et au conteneur ; affichage FR/EN observé |
| Pendant | Rôle des cinq niveaux et coût cumulatif affichés ; contenus techniques privés inchangés | Interface FR/EN et calcul réel du service frontend exercés |
| Après | Treize journaux FR/EN demandent observation et limite, explication, protection et transfert défensif | Enregistrement UI, HTTP201, matrice professeur et texte SQLite exact concordants dans la démonstration isolée |
| Notation | Plancher frontend0 aligné sur la preuve existante ; arrondi dashboard aligné sur Python round de la preuve | Cas aucun indice, N1, N1–N3, N1–N5, bonus et quiz absent ; divergence antérieure97/98 couverte |
| Quiz13 | Q3 corrige l’exclusion générale des règles métier et rappelle l’autorisation par objet côté serveur | Référence OWASP lue, pack installé comparé ; treize packs de questions FR/EN consultés sans clé de correction publique |
| Professeur | Grille manuelle8 points, corrigés et protocole avant/après en FR/EN | Questions et corrigés rapprochés ; grille distincte des scores automatiques |
| Supports | Word élève10 pages et professeur13 pages ; trois captures élève actualisées sans notification | Rendus relus, 39 liens et treize signets professeur, six images élève et treize images professeur vérifiés |
| Sélecteur | selectedKey devient un signal Angular, pour invalider nom et métadonnées | Passage Score Board → Forged Feedback → Score Board observé sur le bundle installé |

Les effets sur l’apprentissage restent à mesurer. Les statistiques historiques
non rapprochées ne sont plus présentées comme des résultats. Les deux situations
avant/après portent sur l’autorisation ; elles n’évaluent pas à elles seules les
treize notions ni un effet causal de JuiceLab. Les journaux complètent cette
observation. La grille manuelle ne modifie aucune note historique.

## Instance locale et entrées réelles

- Instance distincte : `juicelab-pedagogy-20261114`, sur
  http://127.0.0.1:32768/#/juicelab ; conteneur sain sous Node24.20.0.
- Version : 20.4.0-SNAPSHOT. Image active :
  `sha256:102b8858c72f0aae9cc2a38a6e6dcd4a624d0a38b3c7720957c392861dcc178c`.
- Dashboard de démonstration : boucle locale38143, base dédiée dans le dossier
  de preuves, authentification enseignant conservée. Aucune base de promotion
  réelle n’est utilisée ; le monitor automatique est désactivé pour cette fixture.
- Le build Docker standard a compilé l’overlay et le serveur. La correction
  finale du sélecteur utilise ensuite `npm run build:frontend`, configuration
  production, sous le Node24.20.0 de cette image, avec dépendances locales
  montées en lecture seule. Versions observées : Angular core22.2.6,
  build22.2.7, TypeScript6.0.3, satisfaisant le manifeste du snapshot.
- `docker/Dockerfile.frontend-refresh` réemballe le frontend de production pour
  ce dernier incrément frontend seul. Il exige explicitement une image de base
  déjà construite avec le serveur et les packs privés correspondants. Il ne
  remplace pas le build standard pour un changement backend ou de pack privé.
  Le quiz13 fait partie du build standard préalable, pas de ce raccourci.
- Vingt-huit ressources servies sont comparées aux sources/build et au conteneur.
  Les cinq sources frontend modifiées et le pack privé13 sont également comparés.
  La présence de sources dans l’image ne remplace pas la preuve du bundle servi.

Le test utilise une connexion normale au compte de démonstration du laboratoire.
Cette connexion émet sa validation native Exposed Credentials dans cette instance
isolée ; les événements du bridge ne constituent pas une recette de ce défi.
Aucun envoi d’usurpation du défi13 n’est effectué.

## Preuves et reprise

Dossier local : `.swarm-fixtures/pedagogy-20261114/`. Lexar n’était pas montée ;
repli local annoncé, sans écriture sous un point de montage absent ni nettoyage
d’un autre travail. Principaux éléments :

- `before/` et `before.json` : sources antérieures ; captures historiques conservées.
- `tests-python-final.log` : 29 tests ciblés réussis ; `tests-scoring.log` :
  service frontend réel, témoin antérieur50 après cinq indices puis cas corrigés.
- `docker-build.log`, `frontend-build.log`, `docker-refresh.log` : constructions.
- `installed.json`, `installed-source-check.json`, `ui-check.json` : instance,
  ressources, sélection réactive, FR/EN, journal et briefing manquant.
- `journal-receipt-check.json` : texte de démonstration exact et son empreinte,
  relecture SQLite en mode ro.
- `capture-clean.cjs`, captures `*-clean.png` et `captures/` : images natives.
- `documents-final-check.json`, `word-build/`, `qa-student-final/` et
  `qa-teacher-final/` : contrôles, générateur, fichiers et rendus.
- `delivery-final.json` : empreintes installées, sauvegardes et commande de
  restauration à utiliser seulement si la cible n’a pas changé depuis livraison.

Pour régénérer uniquement les annexes à partir des guides Markdown, utiliser
`scripts/learning_documents.py` avec le Python du runtime documents ; il produit
des candidats sans remplacer les Word actifs. Pour régénérer aussi les captures
et pages initiales, le générateur complet conservé dans `word-build/build_docs.py`
utilise `captures/`, les résultats historiques et ce même helper. Toute modification
exige un nouveau rendu. Ne pas présenter les anciens rendus comme ceux d’un nouveau
Word. Ces fichiers persistent ; un rechargement automatique des autres chats ou
processus n’est pas établi.

## Revue des politiques fonctions et erreurs

**Politiques.** Les treize clés et leur ordre sont le périmètre pédagogique
versionné : YAML public → lecture/tri du pack → signal de sélection et badges →
interface exercée. Les coûts5/10/20/35/50 restent ceux des treize packs privés.
Le plancher0 et l’arrondi vers l’entier pair réutilisent le contrat de la preuve
professeur ; ils ne deviennent pas des réglages Admin/API. Ils sont exposés dans
les exemples, le score du panneau, la preuve et la moyenne du dashboard. La grille
0/1/2 par dimension est une consigne d’évaluation manuelle modifiable par
l’enseignant, pas une politique de calcul automatique. Les ports, identifiants
et monitor désactivé appartiennent à la fixture. La configuration CORS du dashboard
est persistée dans sa configuration privée, validée par le lanceur sur boucle
locale, puis consommée par Flask et exercée par l’enregistrement réel du journal.
COPY chown1001 reprend l’identité technique du runtime de base.

**Fonctions.** Les nouvelles méthodes de localisation précisent champs optionnels,
langue, sortie vide et absence d’effets de bord. Le service de score documente
l’entrée typée et la portée d’affichage. Le résumé de cohorte documente l’arrondi,
les scores partiels et la propagation des erreurs DB. Le helper Word documente
audience, sources, sauvegardes, erreurs et absence de validation visuelle implicite.
Les exemples de notation sont exercés par les fonctions réelles. La documentation
FR/EN, les schémas de types et le contexte de reprise sont mis à jour.

**Erreurs et incidents.**

- Le chargement du briefing distingue attente et indisponibilité ; un404 injecté
  après un témoin valide produit l’état indisponible, sans objectifs périmés.
- La première compilation ciblée hors réseau a refusé l’inlining d’une police
  Google (`EAI_AGAIN`). Log conservé ; accès réseau rétabli, profil de production
  conservé et compilation réussie, sans télécharger à nouveau les dépendances.
- La première vérification de langue cherchait aria-label sur le conteneur du
  bouton radio. DOM observé : l’attribut est sur input. Script et preuve d’échec
  conservés dans `ui-attempt1/`, sélecteur corrigé puis parcours complet réussi.
- Les premières images étaient masquées par le snackbar de langue. Source lue :
  notification native5000ms. La reprise attend sa disparition effective dans le
  DOM et produit les captures propres ; aucun délai global ajouté.
- Une commande Word a d’abord refusé un cwd encore absent, avant toute mutation.
  Répertoire créé depuis un cwd existant, puis génération et rendus réussis.
- La vérification finale des liens a relevé deux références README vers
  ARCHITECTURE.md à la racine, alors que les documents sont dans docs/.
  Chemins FR/EN corrigés puis vérifiés. Les sauvegardes docker/.env.* sont
  ignorées avant publication, avec exception explicite pour .env.example ;
  aucune sauvegarde locale de secrets n’entre dans le commit.
- L’étape Docker chown a été lente, avec progression CPU et pression disque
  observées. L’accès à /proc/io a été refusé ; aucun contournement. Pas de timeout
  durci, pas de nettoyage concurrent. Le refresh frontend évite de reconduire
  l’installation complète des dépendances pour le seul correctif du sélecteur.

Les erreurs de construction, d’empreinte ou d’assertion ne deviennent pas des
succès vides. Les sauvegardes et preuves d’échec restent conservées. Le dernier
Word élève a été relu page par page ; le Word professeur final conserve les mêmes
pages que le rendu déjà relu, avec comparaison d’octets des PNG.

## Éléments restant ouverts

L’acceptation historique du défi13 reste ouverte sous son critère complet décrit
dans [RECETTE-20261114.md](RECETTE-20261114.md). Cette amélioration ne la réduit pas.
Propriétaire : responsable de recette ; condition : preuve contemporaine liant
identité authentifiée et envoi exact, puis résultat et stockage concordants.

La mesure en classe attend la prochaine séance et ses réponses anonymisées.
Propriétaire : enseignant ; critère : couples avant/après complets, effectif et
limites publiés avec les mesures. Les autres contenus de l’ancienne extension
restent hors de la validation du parcours actif ; leur relecture n’est pas une
compatibilité globale déjà établie. Ces limites n’empêchent pas la livraison de
la couche pédagogique vérifiée ici.

Les régressions de ce lot sont intégrées à dashboard/tests/test_learning_layer.py,
donc à la collecte pytest existante de la CI. PyYAML est ajouté uniquement aux
outils de test du job correspondant pour lire les packs YAML ; aucune dépendance
runtime du dashboard n’est ajoutée. La réussite de la CI distante n’est pas
déduite des tests locaux.
