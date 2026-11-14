# Accompagner et évaluer le parcours JuiceLab

Ce guide accompagne le [sujet élève](ASSESSMENT-FR.md) et les journaux des treize
défis. Il sert à lire le raisonnement, préparer une reprise collective et mesurer
une évolution. Il n’établit aucun gain pédagogique déjà observé.

## Grille commune sur huit points

| Dimension | 0 point | 1 point | 2 points |
| --- | --- | --- | --- |
| Observation et limites | Conclusion sans pièce identifiable | Pièce pertinente, portée imprécise | Pièce précise, distinction constat/hypothèse et preuve manquante |
| Explication | Aucune règle pertinente | Bonne notion sans relation au cas | Règle expliquée avec acteur, action et objet du cas |
| Protection | Protection absente ou uniquement côté client | Protection serveur plausible mais incomplète | Protection reliée à la règle, identité vérifiée et objet concerné |
| Vérification et transfert | Aucun contrôle défini | Un résultat attendu ou transfert partiel | Cas autorisé et refusé, résultats attendus et preuve prévue ; adaptation au cas inédit |

Cette grille est une proposition manuelle distincte du QCM, du score d’indices
et des badges. Ne l’injecter ni dans l’historique ni dans la moyenne automatique.
Ne pas confondre journal enregistré, longueur suffisante et compréhension.

## Correction du sujet avant

1. Les règles, les propriétaires et la vérification serveur décrite sont connus.
   Le masquage du bouton est une mesure d’interface. Aucune lecture effective de
   R24 par Alice n’est prouvée : ni requête, ni réponse, ni trace ne sont fournies.
2. Être connecté ne suffit pas. Le serveur doit décider si cette personne a le
   droit de lire cette réservation, selon sa propriété ou son agence et son rôle.
3. Déduire l’identité de la session vérifiée et vérifier les relations nécessaires
   avec l’objet demandé à chaque lecture. Ne pas autoriser un changement de
   propriétaire par une valeur reçue du client. Une autre architecture est
   recevable si elle applique ces mêmes règles côté serveur.
4. Contrôle autorisé : Alice lit R17, résultat attendu accessible. Contrôle refusé :
   Alice demande R24, résultat attendu sans données de cette réservation. Un refus
   403 ou une réponse 404 destinée à masquer l’existence sont recevables si le
   contrat est documenté. Pour l’agent, tester l’agence autorisée et une autre.
   La preuve doit relier identité contrôlée, objet, résultat et trace datée.

## Correction du sujet après

1. La revue révèle l’absence de relation contrôlée et une spécification acceptant
   une propriété cliente. Cela motive une vérification ; aucun effet réel n’est
   établi par ces pièces seules.
2. Un rôle « patient » ne donne pas accès à tous les dossiers. L’accès dépend de
   la propriété ou d’une relation de soins autorisée. La propriété d’un dossier
   relève du service d’inscription prévu par le cas.
3. Appliquer ces relations côté serveur. Ignorer ou refuser un propriétaire fourni
   par un client non habilité ; le déterminer depuis le contexte autorisé. Un
   middleware commun peut servir, avec les contrôles métier nécessaires.
4. Camille peut consulter D31 ; Camille ne doit recevoir aucune donnée de D42.
   Tester séparément un soignant affecté et non affecté. Pour la création,
   vérifier que la propriété finale suit le contrat du service d’inscription.
   Prévoir des preuves datées sans données médicales réelles. Le transfert attendu
   porte sur une autorisation par relation, pas sur la mémorisation d’une route.

## Suivi de la séance

Lire ensemble progression, indices, journal et quiz dans la matrice existante.
Un nombre élevé d’indices signale un besoin possible d’accompagnement, pas un
diagnostic individuel automatique. Relire une justification et demander une
reformulation avant de conclure. Regrouper les confusions observées pour une
reprise collective ; ne pas afficher publiquement les difficultés nominatives.
Les réponses du journal sont la pièce utile pour cette grille ; un total de
points ou un badge seul ne suffit pas. Les règles d’alerte existantes ne changent pas.

## Protocole de mesure pour la prochaine séance

1. Avant le parcours, distribuer uniquement le sujet élève, annoncer les règles
   d’aide et la durée accordée, puis conserver la réponse sous pseudonyme.
2. Après le parcours, distribuer la seconde situation et recueillir une réponse
   indépendante avec les mêmes règles d’aide. Ne pas donner le corrigé avant.
3. Utiliser la même grille, idéalement sans voir le score précédent. Sur un
   échantillon choisi avant notation, confronter deux corrections et documenter
   les désaccords plutôt que les effacer.
4. Tenir un tableau : pseudonyme, variante, date, durée réelle, quatre dimensions,
   total sur huit, indices utilisés et aide extérieure déclarée. Séparer les
   absences des scores nuls. Conserver les réponses sources avec accès restreint.
5. Comparer les seuls couples complets et annoncer leur effectif, les absences,
   l’écart individuel et la médiane des écarts. Décrire aussi chaque dimension.
   Un progrès entre ces deux situations ne démontre pas à lui seul un effet
   causal de JuiceLab ; difficulté des variantes, correction et familiarisation
   peuvent intervenir. Alterner l’ordre des variantes entre groupes lors d’une
   prochaine séance permet d’examiner un effet de variante, sans le supposer nul.

Le plan est prêt à être utilisé ; aucun résultat de promotion n’est inventé.
La durée reste une décision de l’enseignant, sans seuil automatique de blocage.

Référence technique : [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
vérification à chaque requête, droits sur l’objet et contrôle côté serveur.
