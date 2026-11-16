"""Teacher-only content for OWASP-JuiceLab-Recette-Prof.docx.

Complements the student sheets (content_dj1/dj23/defense) with what a
teacher needs: room setup, session flow, what a good answer contains,
frequent mistakes observed during the recette, oral follow-up questions,
and the answer key of the before/after self-assessment.
Sources: recette notes docs/RECETTE-20261114.md, results13.json (native lab,
2026-11-14) and results13-fix.json (Docker image, 2026-11-16).
"""

INTRO = (
    'Support de l’enseignant pour le TD de treize défis. Il donne la '
    'préparation de la salle, le déroulé, le corrigé commenté de chaque défi '
    '(attendus, erreurs fréquentes, relances), le corrigé de l’auto-évaluation '
    'et le procès-verbal de recette. Le support élève contient les mêmes '
    'fiches sans les attendus ni le corrigé de l’auto-évaluation.'
)

PREP_TECH = [
    ('Instance élève',
     'Image Docker JuiceLab, écoute sur 127.0.0.1:3000 (JUICELAB_DEMO_BIND). '
     'Vérifier que le port est libre avant la séance : un autre service sur '
     '3000 (cas observé : Zammad) affiche une autre application.'),
    ('Tableau de bord élève',
     'http://localhost:3000/#/juicelab : progression, indices, journal, badges.'),
    ('Dashboard enseignant',
     'http://127.0.0.1:5050/dashboard?cohort=<cohorte> avec le jeton '
     'DASHBOARD_TEACHER_TOKEN. Toujours préciser ?cohort= : sans lui, la '
     'cohorte par défaut du dashboard s’affiche.'),
    ('Remontée des événements',
     'Le dashboard n’accepte que les origines listées dans '
     'DASHBOARD_CORS_ORIGINS (http://localhost:3000 et http://127.0.0.1:3000). '
     'Une instance sur un autre port ne remonte rien.'),
    ('Reflected XSS (défi 11)',
     'L’image JuiceLab règle safetyMode: disabled pour que ce défi reste '
     'jouable en Docker. Les instances partagées sur le réseau de la salle '
     '(docker/provision.py) gardent la protection d’origine : le défi 11 y est '
     'désactivé. Prévoir alors une démonstration sur une instance locale.'),
    ('Remise à zéro',
     'docker compose --env-file .env down -v efface la base Juice Shop et le '
     'dashboard local. À réserver à la fin de séance.'),
]

FLOW_INTRO = (
    'Trois demi-journées, une progression du plus visible au plus subtil. '
    'L’enseignant fixe le créneau de chaque passage de l’auto-évaluation.'
)
# (half-day, challenges, teaching aim)
FLOW = [
    ('1', '01 à 05', 'Reconnaissance : lire ce que le serveur livre au '
     'navigateur (routes, fichiers, secrets, champs d’API).'),
    ('2', '06 à 09', 'Authentification et autorisation : injection SQL, puis '
     'contrôles d’accès absents côté serveur.'),
    ('3', '10 à 13', 'Navigateur et identité : XSS DOM puis réfléchi, contenu '
     'tiers, usurpation d’auteur.'),
]
FLOW_STEPS = [
    'Ouverture : premier passage de l’auto-évaluation (scénario « avant »).',
    'Chaque défi : briefing du coach, essai, indices si besoin, journal, quiz.',
    'Fin de demi-journée : mise en commun sur les réflexes du défenseur.',
    'Clôture du TD : second passage (scénario « après ») et rendu.',
]

# Per challenge: expected (what a good answer contains), pitfalls (seen in
# the recette or deduced from the code), relance (oral follow-up question).
TEACHER = {
    'scoreBoardChallenge': {
        'expected': 'La route trouvée dans main.js, et la distinction entre '
                    'page cachée et page protégée.',
        'pitfalls': 'URL sans # (/score-board au lieu de /#/score-board) ; '
                    'recherche dans main.js sans affichage lisible.',
        'relance': 'Une route absente du menu est-elle un contrôle d’accès ?',
    },
    'privacyPolicyChallenge': {
        'expected': 'Le chemin de menu et un type de donnée cité par la politique.',
        'pitfalls': 'Menu Privacy & Security introuvable sans connexion.',
        'relance': 'Quelle preuve faudrait-il pour affirmer qu’une donnée est protégée ?',
    },
    'directoryListingChallenge': {
        'expected': 'Le passage de /ftp/legal.md à l’index /ftp, puis au '
                    'fichier ; la notion de listage de répertoire.',
        'pitfalls': 'Confondre couper l’index et retirer les fichiers : un nom '
                    'deviné reste téléchargeable.',
        'relance': 'Pourquoi désactiver l’index ne suffit-il pas ?',
    },
    'exposedCredentialsChallenge': {
        'expected': 'L’emplacement du secret (composant de connexion compilé '
                    'dans main.js) et le risque d’un compte de test actif.',
        'pitfalls': 'Recopier le mot de passe en clair dans le rendu au lieu '
                    'de le masquer.',
        'relance': 'Quel contrôle automatique aurait bloqué cette livraison ?',
    },
    'passwordHashLeakChallenge': {
        'expected': 'La comparaison avec et sans fields, le nom du champ '
                    'sensible, la valeur masquée.',
        'pitfalls': 'Valeur de l’empreinte laissée visible ; URL ouverte hors '
                    'de la session connectée (réponse vide).',
        'relance': 'Une empreinte divulguée est-elle sans danger ? Lien avec le défi 06.',
    },
    'loginAdminChallenge': {
        'expected': 'Le compte obtenu, le rôle de la condition toujours vraie '
                    'et du commentaire, la requête paramétrée comme correction.',
        'pitfalls': 'Attendre l’erreur SQL à l’écran : la page n’affiche que '
                    '« [object Object] » (objet JSON rendu tel quel), l’erreur '
                    'se lit dans F12, Réseau. Espace parasite dans la saisie ; '
                    'liste noire de caractères proposée comme correctif.',
        'relance': 'Pourquoi un filtre de caractères n’est-il pas une correction ?',
    },
    'adminSectionChallenge': {
        'expected': 'La route d’administration, le refus avec un compte '
                    'ordinaire, l’accès avec la session du défi 06.',
        'pitfalls': 'Croire que le garde Angular protège les API ; il ne '
                    'contrôle que la navigation.',
        'relance': 'Que vérifie le serveur quand on appelle directement une API d’administration ?',
    },
    'basketAccessChallenge': {
        'expected': 'Les deux identifiants de panier (le sien, celui lu) et la '
                    'relation propriétaire que le serveur aurait dû vérifier.',
        'pitfalls': 'Oublier de recharger après modification de bid ; oublier '
                    'de restaurer sa propre valeur.',
        'relance': 'Un identifiant aléatoire remplace-t-il le contrôle de propriété ?',
    },
    'feedbackChallenge': {
        'expected': 'Le critère exact : plus aucun avis à cinq étoiles en base.',
        'pitfalls': 'Avis restants sur une autre page du tableau. Confusion '
                    'avec le défi 13 : ici on supprime, on n’usurpe pas.',
        'relance': 'Quelle trace une suppression autorisée doit-elle laisser ?',
    },
    'localXssChallenge': {
        'expected': 'L’insertion de la balise dans le DOM, l’alerte, et la '
                    'distinction entre rendu observé et validation du défi.',
        'pitfalls': 'Charge recopiée avec des apostrophes au lieu des accents '
                    'graves attendus par cette version.',
        'relance': 'Où la saisie cesse-t-elle d’être traitée comme du texte ?',
    },
    'reflectedXssChallenge': {
        'expected': 'L’emplacement du reflet (identifiant de suivi), la réponse '
                    'serveur qui contient déjà la balise, la différence avec le défi 10.',
        'pitfalls': 'Identifiant renvoyé nettoyé : défi désactivé (instance LAN '
                    'ou image ancienne, voir préparation).',
        'relance': 'Quelle observation dans Réseau prouve le reflet serveur ?',
    },
    'xssBonusChallenge': {
        'expected': 'Le type de contenu intégré (lecteur tiers) et le lien avec '
                    'la cause du défi 10.',
        'pitfalls': 'Charge tronquée au copier-coller.',
        'relance': 'Quel en-tête aurait bloqué l’intégration externe ?',
    },
    'forgedFeedbackChallenge': {
        'expected': 'Le champ manipulé (UserId), la valeur choisie, l’avis '
                    'relu avec une autre identité que la session.',
        'pitfalls': 'Envoi sans CAPTCHA : HTTP 500, carte validée mais avis non '
                    'enregistré (évaluateur monté avant la vérification). Exiger '
                    'la relecture de l’avis comme preuve.',
        'relance': 'D’où le serveur devrait-il tirer l’auteur d’un avis ?',
    },
}

# Answer key of the before/after self-assessment, one entry per question
# (same order as content_outro.QUESTIONS).
KEY_BEFORE = [
    'Les pièces montrent une règle métier et une revue serveur limitée à '
    '« session connectée ». Aucun accès réel de R24 par Alice n’est prouvé : '
    'l’effet reste à vérifier.',
    'Manque la vérification de relation : le client propriétaire ou l’agent '
    'de la même agence. Masquer le bouton ne bloque pas une requête directe.',
    'Au serveur, à chaque lecture : comparer l’utilisateur connecté au '
    'propriétaire ou à l’agence de la réservation ; refuser sinon.',
    'Journaliser les refus et les lectures hors agence ; alerter sur une même '
    'session qui parcourt des identifiants successifs.',
    'Autorisé : Alice lit R17, réponse 200. Interdit : Alice demande R24, '
    'réponse 403 ou 404. Preuve : requêtes, réponses et journaux horodatés '
    'd’un test réellement exécuté.',
]
KEY_AFTER = [
    'Deux constats de revue : rôle vérifié sans relation au dossier, et champ '
    'propriétaire accepté du navigateur. Aucune lecture de D42 par Camille '
    'n’est prouvée.',
    'Manquent la relation personne–dossier (propre dossier ou patient suivi) '
    'et l’attribution du propriétaire par le seul service d’inscription. '
    'Cacher D42 dans l’interface ne protège rien.',
    'Contrôle de relation au serveur pour chaque lecture ; ignorer le champ '
    'propriétaire reçu à la création et le fixer côté serveur.',
    'Journaliser les lectures de dossiers sans lien de soin et les créations '
    'portant un propriétaire différent de l’appelant.',
    'Autorisé : Camille lit D31. Interdits : Camille lit D42 ; une création '
    'qui impose un autre propriétaire. Résultats et preuves comme au premier '
    'passage. Transfert attendu : défis 08 (propriété) et 13 (auteur fourni '
    'par le client), avec la limite d’un test ponctuel.',
]

RECETTE_INTRO = (
    'Procès-verbal des essais qui fondent ce support, tous sur OWASP Juice '
    'Shop 20.4.0-SNAPSHOT : laboratoire natif (hors Docker) le 14 novembre '
    '2026, 13/13 ; image Docker JuiceLab le même soir, 12/13 ; image Docker '
    'corrigée le 16 novembre 2026, 13/13. Le fichier de résultats du '
    'laboratoire natif a été écrasé par la relance Docker ; son résultat est '
    'consigné dans docs/RECETTE-20261114.md.'
)
RECETTE_PROTOCOL = (
    'Un défi est « validé » quand l’API /api/Challenges passe de solved=false '
    'à solved=true après la manipulation, sur une instance vierge, et que la '
    'carte du tableau devient verte (capture). Le script de recette rejoue les '
    'treize défis dans Chrome sans intervention.'
)
RECETTE_FINDINGS = [
    ('Reflected XSS en Docker',
     'Première campagne Docker : 12/13. Le défi porte disabledEnv: [Docker, '
     'Heroku] et le réglage amont safetyMode: auto le désactive en conteneur ; '
     'l’identifiant revient nettoyé. Corrigé le 16 novembre : safetyMode: '
     'disabled dans overlay/config/juicelab.yml, instance liée à 127.0.0.1. '
     'Nouvelle campagne sur image vierge : 13/13.'),
    ('Défi 13 de substitution',
     'Bully Chatbot est absent du catalogue 20.4.0 (118 défis). Il est '
     'remplacé par Forged Feedback, présent et validé.'),
    ('Forged Feedback sans CAPTCHA',
     'Le POST sans CAPTCHA renvoie HTTP 500 mais valide la carte : '
     'l’évaluateur du défi s’exécute avant la vérification du CAPTCHA. L’avis '
     'n’est alors pas enregistré ; seule la voie formulaire avec CAPTCHA '
     'l’enregistre.'),
    ('Bonus Payload',
     'Insertion de l’iframe et validation établies ; la lecture du son relève '
     'du service externe et n’est pas testée.'),
]
RECETTE_SOURCES = (
    'Solutions de référence : « Pwning OWASP Juice Shop » (docs/juice-shop.pdf), '
    'annexe Challenge solutions, version 19.0.0 — Exposed Credentials et '
    'Password Hash Leak n’y figurent pas. Code cité : sources Juice Shop '
    '20.4.0-SNAPSHOT. Notes complètes : docs/RECETTE-20261114.md.'
)
