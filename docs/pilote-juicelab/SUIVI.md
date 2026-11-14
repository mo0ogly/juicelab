# Suivi du kit pilote

Demande : deux demi-journées, treize défis, extensions, PowerPoint et documents
élèves/professeur incluant installation et compte rendu. Hypothèse d'horaire :
deux fois quatre heures, pauses comprises. Le parcours produit de douze heures
n'est pas reconfiguré. Aucun code de Juice Shop ou JuiceLab modifié.

## Sources et portée

- `/home/fpizzi/workspace/juice/docs/PEDAGOGY-FR.md` et catalogue actif
  `overlay/frontend/src/assets/juicelab/selected_challenges.yml`, lus le
  14 novembre : liste de treize, missions, journaux, distinction score/preuve.
- `INSTALL.md`, scripts apply-overlay shell et PowerShell, config publique,
  package.json du snapshot : montage natif et commandes, sans validation nouvelle
  des systèmes de classe. Révisions citées dans les documents.
- Métadonnées natives conservées dans
  `.artifacts/pilote-20261114/catalogue-native-observed.json` : 118 entrées,
  dont treize actives et 105 autres. Observation de présence, pas recette.
- `models/challenge.ts` du snapshot et route admin JuiceLab : statut global
  d'une instance, ne prouve pas l'auteur individuel.
- `lib/utils.ts` du snapshot et métadonnées Docker/natif historiques :
  restriction Docker de Reflected XSS ; mode natif retenu, protection conservée.
- Message utilisateur de cette reprise : absence Join image élève, sync legacy
  fonctionnelle et acceptation pour TD. Attribué au constat enseignant ; aucune
  nouvelle observation du transport n'est revendiquée. Contrôle de réception
  demandé avant classe. Harmonisation restante, propriétaire produit.

## Vérification des artefacts

Sources de construction et diagnostic : `.artifacts/pilote-20261114/build/`.
Rendus Word et diapositives : `.artifacts/pilote-20261114/qa/` et `slides/`.
Huit Word rendus avec le LibreOffice du runtime, pages examinées. PowerPoint
25 diapositives, trois tables natives, notes sur chaque diapositive ; contrôle
de structure, géométrie, polices et import Artifact Tool effectué. Le fichier
n'a pas été ouvert dans Microsoft PowerPoint. Empreintes dans `MANIFEST.json`.
Contrôle du ZIP : membres explicites, CRC et comparaison des empreintes.

Replan : chemins de contexte rectifiés, bordure héritée de Title supprimée,
police native déclarée par typeface, numéros réels des tables corrigés, variable
du runtime fournie à l'importeur, libellé chevauchant raccourci. Les erreurs
originales et reprises sont conservées dans le build. Session Spaces refusée
selon historique ; fallback PPTX local. Page vide résiduelle :
page_ac32d2623b6081919c21b5d2ae605055, suppression non établie faute d'outil.

## Revue des modifications

Choix pédagogiques : horaires, quinze minutes par évaluation, barème 4×2 ;
propositions modifiables, sans imposer de politique au moteur. La concurrence
bornée à trois rendus ne concerne que la fabrication locale. Pas de nouveau
watchdog global de test. Fonctions de construction non triviales documentées ;
erreurs de génération propagées, erreurs du finalizer diagnostiquées puis
reprises avec préconditions corrigées. Aucun échec connu transformé en succès.
Le kit est en français ; le produit FR/EN n'est pas modifié. Pas de traduction
anglaise de ces nouveaux supports demandée. Pas de déploiement requis pour des
artefacts pédagogiques ; fichiers locaux constituent la livraison.

Limites : essais en classe non réalisés, efficacité pédagogique non mesurée,
recette indépendante d'identité du défi13 non clôturée. Deux sujets parallèles
par construction, équivalence empirique non établie. Distinguer absence de copie
et réponse vide. Aucun critère d'acceptation technique réduit par ce pilote.

Améliorations conservées : séparation des formes avant/après et du corrigé,
mesure appariée individuelle, état réel par défi, contrôle de réception legacy,
instance isolée et catalogue optionnel distinct du parcours actif. Effet sur
l'apprentissage à mesurer lors du pilote, propriétaire professeur.

Clôture documentaire : huit DOCX totalisent 18 pages après compactage du catalogue
à trois pages. Les 25 diapositives ont été examinées ; le libellé12 corrigé a été
rendu et revu. Les 25 parties de notes ont du contenu. ZIP final vérifié : onze
membres attendus, CRC et octets conformes au manifeste ; aucun journal technique,
script, archive imbriquée ou secret de déploiement inclus. SHA256 archive :
`d550d6c24d79b4469f0d3f77928941008d21c2b418bd0e738c598bdeef5ce922`.

## Révision V2 après rejet du support

Fabrice a rejeté la qualité pédagogique/visuelle du premier PowerPoint. Les
contrôles structurels précédents ne constituaient pas une acceptation. Le besoin
initial et l'historique sont conservés ; les originaux V1 restent localement dans
old/v1. Aucun fichier ancien n'est inclus dans l'archive V2.

La V2 remplace les compositions de texte répétitives par une progression de
34 diapositives : exemple fictif, diagrammes d'architecture et de décision,
matrice de droits, captures réelles et planches tirées des notes S1 ISI5.
Deux extraits sources sont reproduits : cours1 §3 p5 et cours7 §9 p8, avec source
et application. Les schémas demeurent modifiables ; les captures et extraits
source sont des images préservées. Chaque diapositive contient des notes.

Installation : guide02 réécrit, guide10 ajouté pour les anciens environnements.
Le code lu établit la copie écrasante de l'overlay avant patch, l'absence de volume
Juice Shop dans le Compose de référence et la persistance du token navigateur.
La reprise proposée conserve les travaux et crée un nouveau laboratoire séparé ;
une migration automatique et une restauration exacte ne sont pas établies.

Préparation : fiche11 et complément professeur12 ajoutés, sélection source dans
REFERENCES_COURS.md. Les cinq références utiles et les pages choisies ont été
examinées. Les deux numérotations FR/anciens PDF restent distinctes. La lecture
XSS des pages3/9/10 a été ajoutée après découverte du dossier voisin. Les notes
des cours complets ne sont pas intégrées au dépôt. Les précisions et limites des
lectures sont transmises dans la fiche12, sans modifier les originaux.

Le prétest est maintenant immédiatement après la couverture, avant les planches.
La préparation effectuée avant A doit être consignée ; ce point de départ mesure
alors l'état après préparation, pas avant toute exposition. L'équivalence des
formes et l'effet causal restent non établis.

Dernier PPTX34diapositives : SHA256
`c4363b0dd1b0a3efcb29697cdff3989c1ec8510c713c53f3ca0fa14c53d66f64`.
Contrôles : structure, géométrie, douze tables natives, trois polices déclarées,
import Artifact Tool ; 34 notes inspectées et tous les rendus examinés. Révision
visuelle de la flèche de transfert et des définitions XSS/DOM incluse. Pas de
test dans Microsoft PowerPoint revendiqué. Onze Word/26pages au total ; les
quatre nouveaux/modifiés ont été rendus et examinés dans leur dernière version.
Les autres sont identiques aux octets examinés en V1.

Preuves de cette reprise :
`/home/fpizzi/Documents/ChatGPT/juice/.artifacts/pilote-v2/` ; reçu final
`build/pptx-validation-livraison.json`. Lexar montée sur /dev/sdb1 mais pleine ;
repli local annoncé, aucun nettoyage ni modification de cours sur la clé.
Erreurs et diagnostics préservés dans PLAN.md et logs de construction. Le refus
EEXIST d'un reçu de validation a été traité par un nouveau reçu et la validation
du même candidat rendu ; aucun contrôle n'a été désactivé.

Revue des choix : temps de lecture50min et blocs de séance sont des propositions
pédagogiques explicites. Aucune politique moteur, erreur ou fonction publique de
l'application modifiée. Génération sans appel au laboratoire, erreurs propagées.
Aucun nouveau délai global de test imposé. Pas de redéploiement produit requis
pour ces documents. Liens d'entrée français/anglais mis à jour ; kit francophone.
