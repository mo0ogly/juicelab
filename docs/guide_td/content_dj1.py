"""Corrected walkthroughs for TD half-day 1 (challenges 01-05).

Each entry is a dict consumed by build_guide_td.py. Facts come from the
Juice Shop 20.4.0-SNAPSHOT sources (file:line given in ``validation``) and
from the 13-challenge recipe replayed on that version (results13.json,
2026-11-14). Book pages refer to "Pwning OWASP Juice Shop" (v19 appendix),
cited, never reproduced.

Keys:
    key, title, day, difficulty, category: identity of the challenge.
    goal: one sentence, what the student must obtain.
    notion: the security idea to remember.
    task, question: the exercise statement shown before the solution.
    steps: ordered list; a step is a str or (str, code) to show a literal.
    validation: how Juice Shop decides the challenge is solved.
    why: why this is a vulnerability.
    fix: the defensive measure.
    trouble: list of (symptom, remedy) pairs.
    further: open question to extend the reasoning.
    book: printed page in the book appendix, or None when absent.
"""

DJ1 = [
    {
        'key': 'scoreBoardChallenge',
        'title': 'Score Board',
        'day': 1, 'difficulty': 1, 'category': 'Miscellaneous',
        'goal': 'Afficher la page cachée qui liste tous les défis.',
        'notion': 'Cacher une page du menu ne la protège pas : tout le code de '
                  'l’interface est envoyé au navigateur, routes comprises.',
        'task': 'Retrouve le tableau des défis en inspectant les ressources '
                'JavaScript servies à ton navigateur. Relève l’indice qui t’a '
                'permis de reconnaître une route.',
        'question': 'Quelle différence fais-tu entre une page absente du menu et '
                    'une page réservée par un contrôle d’accès ?',
        'steps': [
            'Ouvre http://localhost:3000 puis les outils de développement (F12), onglet Sources (Chrome) ou Débogueur (Firefox).',
            'Ouvre le fichier main.js et active l’affichage lisible avec le bouton { }.',
            ('Cherche (Ctrl+F) le mot score. Une des occurrences est une déclaration de route :', "path: 'score-board'"),
            ('Ouvre cette route dans la barre d’adresse :', 'http://localhost:3000/#/score-board'),
            'Le tableau s’affiche et un bandeau vert annonce la résolution. Le menu propose désormais Score Board.',
        ],
        'validation': 'La page Score Board charge une petite image (1px.png). '
                      'Le serveur résout le défi quand il reçoit cette requête '
                      '(routes/verify.ts:67).',
        'why': 'La route n’est retirée que du menu. Aucune vérification ne '
               'protège la page : quiconque lit le code la trouve.',
        'fix': 'Ici, rien : le tableau est fait pour être trouvé. Dans une vraie '
               'application, une page sensible exige un contrôle d’accès côté '
               'serveur. Masquer ou chiffrer le nom de la route n’ajoute aucune '
               'sécurité (explications officielles des correctifs du défi).',
        'trouble': [
            ('main.js est illisible', 'utilise le bouton { } (pretty print) avant de chercher.'),
            ('Rien ne se passe en ouvrant l’URL', 'vérifie le # : l’adresse est /#/score-board, pas /score-board.'),
        ],
        'further': 'Quelles autres routes intéressantes repères-tu dans la même liste ?',
        'book': 328,
    },
    {
        'key': 'privacyPolicyChallenge',
        'title': 'Privacy Policy',
        'day': 1, 'difficulty': 1, 'category': 'Miscellaneous',
        'goal': 'Lire la politique de confidentialité de la boutique.',
        'notion': 'Un défi de bonne pratique : savoir où une application '
                  'explique le traitement de tes données. Ouvrir la page ne '
                  'prouve pas que ces données sont protégées.',
        'task': 'Depuis ton compte Juice Shop, retrouve la politique de '
                'confidentialité. Indique comment tu l’as atteinte et relève un '
                'type d’information présenté sur la page.',
        'question': 'Est-ce que l’ouverture de la page démontre que tes données '
                    'sont protégées ?',
        'steps': [
            'Connecte-toi avec ton compte de labo.',
            'Clique sur Account, puis Privacy & Security, puis Privacy Policy.',
            ('La page s’ouvre à l’adresse :', 'http://localhost:3000/#/privacy-security/privacy-policy'),
            'Le défi est résolu à l’ouverture. Relève un type de donnée cité par la politique.',
        ],
        'validation': 'La page charge l’image 81px.png ; le serveur résout le '
                      'défi à la réception de cette requête (routes/verify.ts:71).',
        'why': 'Pas de faille ici : le défi apprend à repérer les engagements '
               'de l’application avant de tester ce qu’elle fait réellement.',
        'fix': 'Sans objet. Retiens l’écart entre une politique écrite et un '
               'comportement vérifié : les défis suivants montrent des fuites '
               'que la politique ne mentionne pas.',
        'trouble': [
            ('Le menu Privacy & Security est absent', 'connecte-toi d’abord : le menu dépend de la session.'),
        ],
        'further': 'Parmi les données citées, lesquelles retrouves-tu exposées dans les défis 04 et 05 ?',
        'book': 327,
    },
    {
        'key': 'directoryListingChallenge',
        'title': 'Confidential Document',
        'day': 1, 'difficulty': 1, 'category': 'Sensitive Data Exposure',
        'goal': 'Ouvrir un document interne laissé sur le serveur.',
        'notion': 'Un répertoire listable expose tous ses fichiers, même ceux '
                  'qu’aucune page ne référence (listage de répertoire, CWE-548).',
        'task': 'À partir d’un lien public de la boutique, recherche un document '
                'interne accessible. Explique comment tu es passé du lien initial '
                'au fichier.',
        'question': 'Quelle configuration permet de découvrir les autres fichiers '
                    'du même répertoire ?',
        'steps': [
            'Ouvre le menu, puis About Us. Survole le lien vers les conditions d’utilisation : il pointe vers /ftp/legal.md.',
            ('Remonte d’un niveau en ouvrant le dossier lui-même :', 'http://localhost:3000/ftp'),
            'Le serveur affiche la liste des fichiers du dossier.',
            ('Ouvre le document confidentiel :', 'http://localhost:3000/ftp/acquisitions.md'),
        ],
        'validation': 'Le serveur résout le défi quand acquisitions.md est '
                      'téléchargé depuis /ftp (routes/fileServer.ts:29).',
        'why': 'server.ts:295 active l’index du dossier /ftp et server.ts:296 '
               'sert chaque fichier. Un document interne se retrouve dans un '
               'dossier public, et l’index le rend visible.',
        'fix': 'Retirer le dossier /ftp et ranger le contenu légitime ailleurs. '
               'Couper seulement l’index ne suffit pas : un fichier dont on '
               'devine le nom reste téléchargeable (explications officielles '
               'des correctifs du défi).',
        'trouble': [
            ('Erreur 403 sur un fichier', 'normal pour certains fichiers filtrés : ce n’est pas celui du défi.'),
        ],
        'further': 'Quels autres fichiers de /ftp te semblent sensibles, et pourquoi ?',
        'book': 323,
    },
    {
        'key': 'exposedCredentialsChallenge',
        'title': 'Exposed Credentials',
        'day': 1, 'difficulty': 2, 'category': 'Sensitive Data Exposure',
        'goal': 'Se connecter avec un compte de test dont l’identifiant et le '
                'mot de passe sont écrits dans le code de l’interface.',
        'notion': 'Un secret placé dans le code client est public : le navigateur '
                  'le télécharge (identifiants en dur, CWE-798).',
        'task': 'Inspecte le JavaScript livré à la page de connexion. Recherche '
                'un compte de test exposé et vérifie son usage dans le labo.',
        'question': 'Pourquoi un compte de test utilisable présente-t-il un risque '
                    'lorsqu’il est livré au navigateur ?',
        'steps': [
            'Déconnecte-toi, ouvre la page de connexion, puis F12, onglet Sources, fichier main.js en affichage lisible.',
            ('Cherche testing. Le composant de connexion contient deux propriétés :', "testingUsername = 'testing@juice-sh.op'\ntestingPassword = 'IamUsedForTesting'"),
            'Saisis ces deux valeurs dans le formulaire et clique sur Log in.',
            'La connexion réussit et le défi est résolu.',
        ],
        'validation': 'routes/login.ts:65 résout le défi quand la connexion '
                      'utilise exactement cet email et ce mot de passe.',
        'why': 'Le développeur a laissé un compte de test valide dans '
               'frontend/src/app/login/login.component.ts:72-73. Le code est '
               'compilé dans main.js, donc lisible par tout visiteur.',
        'fix': 'Ne jamais livrer de secret au client. Supprimer le compte de test '
               'en production, ou le désactiver ; garder les secrets dans un '
               'gestionnaire côté serveur (fiche OWASP Secrets Management).',
        'trouble': [
            ('Identifiants refusés', 'vérifie les majuscules : IamUsedForTesting.'),
        ],
        'further': 'Comment détecterais-tu automatiquement ce type d’erreur avant la mise en ligne ?',
        'book': None,
    },
    {
        'key': 'passwordHashLeakChallenge',
        'title': 'Password Hash Leak',
        'day': 1, 'difficulty': 2, 'category': 'Sensitive Data Exposure',
        'goal': 'Obtenir l’empreinte (hash) du mot de passe de ton propre '
                'compte depuis une API.',
        'notion': 'Une API qui renvoie les champs demandés par le client peut '
                  'livrer des données sensibles (exposition excessive de données, '
                  'OWASP API Security 2019 API3).',
        'task': 'Avec ton compte de labo, compare la réponse de l’API de profil '
                'par défaut et avec une sélection explicite de champs. Note le '
                'nom du champ sensible et masque sa valeur dans ton rendu.',
        'question': 'Pourquoi faut-il restreindre les champs renvoyés même pour un '
                    'utilisateur connecté ?',
        'steps': [
            'Connecte-toi, puis F12, onglet Réseau (Network). Recharge la page.',
            ('Repère l’appel au profil. Sa réponse contient id, email, lastLoginIp et profileImage, sans mot de passe :', '/rest/user/whoami'),
            ('Ouvre dans un nouvel onglet la même adresse avec le paramètre fields :', 'http://localhost:3000/rest/user/whoami?fields=id,email,password'),
            'La réponse contient maintenant le champ password : le défi est résolu. Masque cette valeur dans tes notes.',
        ],
        'validation': 'routes/currentUser.ts:52 résout le défi dès que la réponse '
                      'contient un champ password.',
        'why': 'routes/currentUser.ts:24-33 recopie chaque champ demandé dans '
               'fields sans liste autorisée. Le client choisit ce que le serveur '
               'révèle.',
        'fix': 'Construire la réponse à partir d’une liste fixe de champs '
               'publics ; ne jamais exposer password, même haché.',
        'trouble': [
            ('La réponse est vide', 'ouvre l’URL dans le même navigateur que ta session connectée.'),
        ],
        'further': 'Une empreinte de mot de passe sans le mot de passe est-elle sans danger ? Pense au défi 06.',
        'book': None,
    },
]
