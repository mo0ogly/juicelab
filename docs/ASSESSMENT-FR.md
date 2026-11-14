# Évaluer son raisonnement avant et après JuiceLab

Cet exercice complète le parcours de treize défis. Il se réalise sur papier ou
dans des notes locales, sans compte payant, IA ou manipulation d’une application.
Conserve le même pseudonyme entre les deux passages. La note manuelle sur huit
points reste distincte des scores automatiques du laboratoire.

## Avant le parcours

Une application fictive de réservation applique les règles suivantes : chaque
client peut lire ses propres réservations ; un agent peut lire les réservations
de son agence ; personne ne peut modifier le propriétaire d’une réservation.
Dans les pièces fournies, Alice possède R17, Bob possède R24 et ils appartiennent
à des agences différentes. L’interface masque le bouton de R24 à Alice.
Une revue serveur indique que la lecture vérifie seulement « session connectée ».
Aucun journal d’accès ni résultat d’exécution n’est fourni.

Rédige quatre réponses courtes :

1. Que montrent réellement ces pièces, et quel effet reste à vérifier ?
2. Quelle règle d’autorisation manque, et pourquoi le bouton masqué ne suffit-il pas ?
3. Quelle protection côté serveur proposes-tu, sans écrire de procédure d’attaque ?
4. Décris un contrôle autorisé et un contrôle interdit avec leurs résultats attendus.
   Précise ce qui constituerait une preuve de leur exécution.

## Après le parcours

Une application fictive de suivi médical applique ces règles : une personne peut
lire ses propres rendez-vous ; un soignant peut lire ceux des patients dont il
assure le suivi ; seul le service d’inscription attribue le propriétaire d’un dossier.
Camille possède D31 ; D42 appartient à Nour et Camille ne participe pas à ses soins.
L’interface cache D42 à Camille. La revue serveur relève une vérification du rôle
« patient », sans relation entre la personne connectée et le dossier consulté.
La spécification de création accepte en outre un champ « propriétaire » fourni
par le navigateur. Aucun résultat d’exécution n’est fourni.

Réponds aux quatre mêmes questions, appliquées à ces nouvelles pièces. Ajoute ce
que tu transfères du parcours JuiceLab : une notion, une protection et sa limite.
Ne présente pas le contrôle proposé comme un contrôle déjà effectué.

## Ce qui sera évalué

Chaque dimension vaut zéro, un ou deux points : précision des observations et
limites ; explication de la règle ; pertinence de la protection ; qualité du
contrôle et du transfert. Une réponse argumentée peut recevoir un crédit partiel.
La longueur du texte et la rapidité ne donnent pas de points en elles-mêmes.
L’enseignant indique le créneau accordé avant chaque passage ; consigne la durée
réellement utilisée plutôt qu’une durée supposée.

Entre les deux passages, utilise les indices lorsque tu en as besoin et remplis
le journal. N’inclus ni mot de passe, jeton, donnée personnelle réelle ou preuve
provenant d’un système extérieur au laboratoire autorisé.
