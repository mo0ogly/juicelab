"""Closing part of the student TD guide: defensive synthesis, recap table,
before/after self-assessment (restored from the previous handout), expected
deliverable and grading grid.
"""

REFLEXES_TITLE = 'Bilan : cinq réflexes du défenseur'
REFLEXES_INTRO = (
    'Les treize défis se ramènent à quelques erreurs récurrentes. Retiens-les '
    'comme des questions à poser à toute application que tu dois défendre.'
)
REFLEXES = [
    ('Tout ce qui part au navigateur est public.',
     'Routes, secrets, contrôles d’interface : défis 01, 04, 07. Un attaquant '
     'lit le code client ; seule une vérification serveur protège.'),
    ('Le serveur décide qui a le droit, à chaque requête.',
     'Défis 07, 08, 09, 13. Vérifier la relation entre l’utilisateur connecté '
     'et l’objet demandé, pas seulement « session ouverte ».'),
    ('Une donnée n’est jamais du code.',
     'Défis 06, 10, 11, 12. Requêtes paramétrées côté base, échappement et CSP '
     'côté navigateur.'),
    ('Ne renvoyer que le nécessaire.',
     'Défis 03, 05. Listes de champs et de fichiers autorisés, jamais l’inverse.'),
    ('Ce qui n’est pas journalisé n’existe pas pour le défenseur.',
     'Chaque fiche propose un signal à surveiller : sans trace, ni détection, '
     'ni enquête, ni preuve que le correctif tient.'),
]

# Recap table: (n, title, family, key control).
RECAP = [
    ('01', 'Score Board', 'Sécurité par l’obscurité', 'Contrôle d’accès serveur'),
    ('02', 'Privacy Policy', 'Bonne pratique', 'Engagements vérifiables'),
    ('03', 'Confidential Document', 'Exposition de fichiers', 'Aucun document interne servi'),
    ('04', 'Exposed Credentials', 'Secret côté client', 'Scan de secrets, compte désactivé'),
    ('05', 'Password Hash Leak', 'Exposition excessive', 'Liste fixe de champs'),
    ('06', 'Login Admin', 'Injection SQL', 'Requêtes paramétrées'),
    ('07', 'Admin Section', 'Contrôle client seul', 'Rôle vérifié côté serveur'),
    ('08', 'View Basket', 'IDOR', 'Propriété vérifiée par requête'),
    ('09', 'Five-Star Feedback', 'Action non autorisée', 'Droits + journal d’audit'),
    ('10', 'DOM XSS', 'XSS côté client', 'Pas de contournement Angular, CSP'),
    ('11', 'Reflected XSS', 'XSS réfléchi', 'Validation de format, échappement'),
    ('12', 'Bonus Payload', 'Contenu tiers injecté', 'CSP frame-src'),
    ('13', 'Forged Feedback', 'Usurpation d’identité', 'Auteur tiré de la session'),
]

DELIVERABLE_TITLE = 'Ton rendu'
DELIVERABLE = [
    'Pour chaque défi : une observation vérifiable (capture ou requête), la '
    'cause en une phrase, la correction et le signal de détection proposé.',
    'Le journal JuiceLab rempli (au moins 50 mots utiles par défi) et le quiz envoyé.',
    'Masque toute valeur sensible (mot de passe, empreinte, jeton) dans tes '
    'captures et tes notes.',
    'Ne présente jamais un contrôle proposé comme un contrôle déjà effectué : '
    'distingue « observé » et « à vérifier ».',
]

ASSESS_TITLE = 'Évaluer son raisonnement avant et après le parcours'
ASSESS_INTRO = (
    'Cet exercice encadre les treize défis. Il se fait sur papier ou dans des '
    'notes locales, sans IA ni manipulation d’une application. Garde le même '
    'pseudonyme aux deux passages. La note manuelle sur huit points est '
    'distincte des scores automatiques du laboratoire.'
)
QUESTIONS = [
    'Que montrent réellement ces pièces, et quel effet reste à vérifier ?',
    'Quelle règle d’autorisation manque, et pourquoi l’interface masquée ne '
    'suffit-elle pas ?',
    'Quelle protection côté serveur proposes-tu, sans écrire de procédure '
    'd’attaque ?',
    'Quel signal un défenseur pourrait-il journaliser pour détecter un abus ?',
    'Décris un contrôle autorisé et un contrôle interdit avec leurs résultats '
    'attendus, et ce qui constituerait une preuve de leur exécution.',
]
BEFORE = (
    'Avant le parcours',
    'Une application fictive de réservation applique ces règles : chaque client '
    'lit ses propres réservations ; un agent lit celles de son agence ; personne '
    'ne modifie le propriétaire d’une réservation. Alice possède R17, Bob '
    'possède R24, d’agences différentes. L’interface masque le bouton de R24 à '
    'Alice. Une revue serveur indique que la lecture vérifie seulement « session '
    'connectée ». Aucun journal d’accès ni résultat d’exécution n’est fourni.'
)
AFTER = (
    'Après le parcours',
    'Une application fictive de suivi médical applique ces règles : une '
    'personne lit ses propres rendez-vous ; un soignant lit ceux des patients '
    'qu’il suit ; seul le service d’inscription attribue le propriétaire d’un '
    'dossier. Camille possède D31 ; D42 appartient à Nour, dont Camille ne suit '
    'pas les soins. L’interface cache D42 à Camille. La revue serveur relève une '
    'vérification du rôle « patient », sans lien entre la personne connectée et '
    'le dossier consulté. La spécification de création accepte un champ '
    '« propriétaire » fourni par le navigateur. Aucun résultat d’exécution '
    'n’est fourni. Ajoute ce que tu transfères du parcours : une notion, une '
    'protection et sa limite.'
)

GRID_TITLE = 'Ce qui sera évalué'
# (dimension, 0 pt, 1 pt, 2 pts)
GRID = [
    ('Observations et limites', 'Affirmations sans preuve',
     'Faits relevés, limites floues', 'Faits, preuves et inconnues distingués'),
    ('Règle manquante', 'Absente ou confuse',
     'Identifiée sans justification', 'Identifiée et reliée aux pièces'),
    ('Protection et détection', 'Côté client seulement',
     'Protection serveur sans signal', 'Protection serveur et signal journalisé'),
    ('Contrôle et transfert', 'Aucun contrôle décrit',
     'Contrôle sans critère de preuve', 'Contrôles autorisé/interdit avec preuves, transfert explicite'),
]
GRID_NOTE = (
    'Une réponse argumentée peut recevoir un crédit partiel. Ni la longueur ni '
    'la rapidité ne donnent de points. L’enseignant indique le créneau avant '
    'chaque passage ; note la durée réellement utilisée.'
)
