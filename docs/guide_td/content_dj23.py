"""Corrected walkthroughs for TD half-days 2 and 3 (challenges 06-13).

Same schema and sources as content_dj1.py. Challenge entries are appended
one by one (DJ23.append) to keep each edit focused and auditable.
"""

# DOM/reflected XSS probe string used by challenges 10 and 11, read from the
# server config at build time rather than spelled out as an attack payload.
DJ23 = []

DJ23.append({
    'key': 'loginAdminChallenge',
    'title': 'Login Admin',
    'day': 2, 'difficulty': 2, 'category': 'Injection',
    'goal': 'Se connecter au compte administrateur sans connaître son mot de passe.',
    'notion': 'Quand une requête SQL est construite en collant le texte saisi, '
              'ce texte peut modifier la requête elle-même (injection SQL, CWE-89).',
    'task': 'Dans une session dédiée au TD, teste comment le formulaire de '
            'connexion traite une entrée comportant des métacaractères SQL. '
            'Consigne le compte obtenu et l’effet sur la vérification du mot de passe.',
    'question': 'À quel endroit faut-il séparer les données utilisateur de la requête ?',
    'steps': [
        ('Ouvre F12, onglet Réseau, puis la page de connexion. Saisis une '
         'apostrophe seule comme email, un caractère quelconque comme mot de '
         'passe, puis Log in :', "'"),
        ('L’écran affiche seulement « [object Object] » en rouge : l’interface '
         'ne sait pas afficher l’erreur reçue (capture ci-dessous). Dans Réseau, '
         'clique sur la requête login (statut 500), onglet Réponse ou Aperçu. '
         'Repère le champ sql : ton apostrophe est collée telle quelle dans la '
         'requête, ce qui la casse (SQLITE_ERROR) :',
         "\"sql\": \"SELECT * FROM Users WHERE email = ''' AND password = "
         "'9dd4e4…' AND deletedAt IS NULL\""),
        ('Saisis maintenant comme email la chaîne donnée par la carte du défi '
         '(condition toujours vraie suivie d’un commentaire SQL) :', "' or 1=1--"),
        'Mets un mot de passe quelconque et valide. Tu es connecté en '
        'admin@juice-sh.op : le défi est résolu.',
    ],
    'validation': 'Le défi est résolu quand une session est ouverte sur le '
                  'compte administrateur par cette voie.',
    'why': "routes/login.ts:34 assemble la requête avec le texte saisi. La "
           "partie or 1=1 rend la condition toujours vraie et le commentaire "
           "neutralise la vérification du mot de passe ; le premier compte de "
           "la table, l’administrateur, est renvoyé.",
    'fix': 'Requêtes paramétrées : les valeurs passent séparément de la '
           'requête (remplacements Sequelize, correctif officiel 4). Une liste '
           'noire de caractères est contournable (correctif officiel 1).',
    'trouble': [
        ('Seulement « [object Object] » à l’écran', 'c’est normal : l’erreur '
         'SQLite se lit dans F12, Réseau, réponse de la requête login.'),
        ('Message « Invalid email or password »', 'recopie exactement la chaîne '
         'de la carte, sans espace parasite.'),
        ('Connecté mais pas en admin', 'déconnecte-toi et recommence : la voie '
         'renvoie le premier compte de la table.'),
    ],
    'further': 'Comment obtenir le même compte si tu connais seulement son email ?',
    'figure': ('login-object-object', 'Après une apostrophe dans Email : la page '
               'n’affiche que « [object Object] ». L’erreur SQL est dans la '
               'réponse réseau (instance 20.4.0-SNAPSHOT, comportement d’origine '
               'OWASP, identique en 19.2.1).'),
    'book': 334,
})

DJ23.append({
    'key': 'adminSectionChallenge',
    'title': 'Admin Section',
    'day': 2, 'difficulty': 2, 'category': 'Broken Access Control',
    'goal': 'Ouvrir la page d’administration de la boutique.',
    'notion': 'Une route connue n’est protégée que si le serveur vérifie les '
              'droits ; la vérification faite par l’interface se contourne.',
    'task': 'Identifie la route d’administration. Compare son accès avec un '
            'compte ordinaire et avec la session obtenue au défi précédent.',
    'question': 'Quel contrôle protège les actions d’administration même si la '
                'route est connue ?',
    'steps': [
        'Reste connecté en administrateur (défi 06).',
        'Dans main.js (F12, Sources, { }), cherche admin : une route mène vers administration.',
        ('Ouvre cette route :', 'http://localhost:3000/#/administration'),
        'La page Administration s’affiche avec la liste des clients : le défi est résolu.',
    ],
    'validation': 'La page charge l’image 19px.png ; le serveur résout le défi '
                  'à la réception de cette requête (routes/verify.ts:69).',
    'why': 'La seule barrière est un contrôle côté client (AdminGuard, '
           'frontend/src/app/app.guard.ts) qui lit le rôle dans le jeton sans '
           'en vérifier la signature. Avec une session admin, il laisse passer ; '
           'il ne protège donc rien côté serveur.',
    'fix': 'Vérifier le rôle sur le serveur pour chaque appel d’administration, '
           'et de préférence isoler l’administration du front public (correctif '
           'officiel 1). Masquer ou encoder la route n’ajoute rien.',
    'trouble': [
        ('Erreur 403 Forbidden', 'tu n’es pas en admin : refais le défi 06 avant.'),
    ],
    'further': 'Pourquoi un contrôle de droits dans le navigateur est-il toujours contournable ?',
    'book': 331,
})

DJ23.append({
    'key': 'basketAccessChallenge',
    'title': 'View Basket',
    'day': 2, 'difficulty': 2, 'category': 'Broken Access Control',
    'goal': 'Lire le panier d’un autre utilisateur.',
    'notion': 'Un identifiant d’objet dans une requête doit être vérifié contre '
              'le propriétaire ; sinon un utilisateur lit les données d’un autre '
              '(référence directe non sécurisée, IDOR).',
    'task': 'Repère l’identifiant de ton panier et la requête de lecture '
            'correspondante. Dans le labo, teste l’accès à un panier différent '
            'et relève les deux identifiants.',
    'question': 'Quelle relation le serveur devrait-il vérifier avant de renvoyer un panier ?',
    'steps': [
        'Connecte-toi, ajoute un produit au panier.',
        'F12, onglet Application (Chrome) ou Stockage (Firefox), Session Storage : relève la valeur numérique bid (ex. 1).',
        'Remplace bid par un autre nombre (ex. 2).',
        ('Ouvre le panier et recharge (F5) :', 'http://localhost:3000/#/basket'),
        'Le panier affiché est celui d’un autre compte. Relève les deux identifiants (le tien et celui consulté).',
    ],
    'validation': 'routes/basket.ts:21 résout le défi quand le panier demandé '
                  'n’est pas celui associé à ta session.',
    'why': 'Le serveur renvoie le panier dont l’identifiant est dans l’URL sans '
           'vérifier qu’il t’appartient. L’identifiant est un simple numéro, '
           'facile à deviner.',
    'fix': 'Comparer, côté serveur, le propriétaire de l’objet à l’utilisateur '
           'connecté avant de répondre (fiche OWASP Authorization).',
    'trouble': [
        ('Toujours ton panier', 'appuie sur F5 après avoir changé bid : le changement doit être relu.'),
        ('bid introuvable', 'ajoute d’abord un produit au panier pour que la clé apparaisse.'),
    ],
    'further': 'En quoi un identifiant imprévisible aiderait-il, et pourquoi ne suffit-il pas ?',
    'book': 332,
})

DJ23.append({
    'key': 'feedbackChallenge',
    'title': 'Five-Star Feedback',
    'day': 2, 'difficulty': 2, 'category': 'Broken Access Control',
    'goal': 'Faire disparaître tous les avis clients à cinq étoiles.',
    'notion': 'Une action d’administration (supprimer un avis) doit être limitée '
              'aux personnes autorisées ; ici elle valide le défi une fois tous '
              'les avis cinq étoiles retirés.',
    'task': 'Dans la rubrique des avis de la zone d’administration, atteins '
            'l’objectif indiqué sur la carte du défi. Relève le critère exact '
            'qui déclenche la validation.',
    'question': 'Comment encadrer la suppression d’avis dans une application réelle ?',
    'steps': [
        'Ouvre la zone d’administration (défi 07).',
        'Dans le tableau Customer Feedback, repère les lignes à cinq étoiles.',
        'Clique sur l’icône corbeille de chacune jusqu’à ce qu’il n’en reste aucune.',
        'Quand le dernier avis cinq étoiles est supprimé, le défi est résolu.',
    ],
    'validation': 'routes/verify.ts:235 compte les avis à cinq étoiles et résout '
                  'le défi quand ce total atteint zéro.',
    'why': 'La suppression d’un avis est accessible via l’administration, '
           'elle-même atteinte par un simple contrôle client (défi 07). Il n’y a '
           'pas de vérification de droits côté serveur sur cette action.',
    'fix': 'Réserver la suppression aux rôles autorisés, vérifiée sur le serveur, '
           'et journaliser l’action (fiche OWASP Authorization).',
    'trouble': [
        ('Le défi ne se valide pas', 'il reste un avis cinq étoiles plus bas dans le tableau : fais défiler.'),
    ],
    'further': 'Quelle trace devrait rester après la suppression d’un avis ?',
    'book': 333,
})

DJ23.append({
    'key': 'localXssChallenge',
    'title': 'DOM XSS',
    'day': 3, 'difficulty': 1, 'category': 'XSS',
    'goal': 'Faire interpréter par le navigateur une balise insérée dans la recherche.',
    'notion': 'Si une saisie est réinjectée dans la page sans être neutralisée, '
              'le navigateur l’exécute comme du code (XSS, ici côté DOM).',
    'task': 'Teste comment la recherche réinsère ta saisie dans la page. Utilise '
            'la charge d’exercice indiquée dans la carte et note si elle devient '
            'un élément du DOM.',
    'question': 'Quels éléments du navigateur ou du tableau te permettent de '
                'distinguer le rendu de la validation du défi ?',
    'steps': [
        'Ouvre la barre de recherche (loupe en haut).',
        'Colle la charge d’exercice affichée sur la carte du défi (une balise iframe) et valide avec Entrée.',
        'Le navigateur interprète la balise : une petite fenêtre d’alerte « xss » apparaît.',
        'Ferme l’alerte. Le défi est résolu.',
    ],
    'validation': 'La page signale la saisie via un canal interne '
                  '(verifyLocalXssChallenge) ; le serveur résout le défi quand '
                  'elle contient la balise attendue (registerWebsocketEvents.ts:40).',
    'why': 'frontend/.../search-result.component.ts:146 marque la saisie comme '
           'sûre (bypassSecurityTrustHtml) avant de l’afficher, ce qui désactive '
           'la protection intégrée d’Angular.',
    'fix': 'Supprimer ce contournement et laisser Angular neutraliser la saisie ; '
           'un texte de recherche n’a aucune raison d’être traité comme du HTML '
           '(correctif officiel 2).',
    'trouble': [
        ('Pas d’alerte', 'recopie la charge exacte de la carte, sans espace ajouté.'),
    ],
    'further': 'Pourquoi une recherche ne devrait-elle jamais être rendue comme du HTML ?',
    'book': 328,
})

DJ23.append({
    'key': 'reflectedXssChallenge',
    'title': 'Reflected XSS',
    'day': 3, 'difficulty': 2, 'category': 'XSS',
    'goal': 'Faire interpréter la même balise, cette fois renvoyée par le serveur '
            'dans la page de suivi de commande.',
    'notion': 'Un XSS réfléchi vient d’une donnée de l’URL que le serveur renvoie '
              'telle quelle dans la réponse, puis que la page affiche.',
    'task': 'Depuis le suivi d’une commande, repère la donnée issue de l’URL qui '
            'revient dans la réponse et dans la page. Teste la charge du défi à '
            'cet emplacement.',
    'question': 'Quelle observation dans Réseau distingue ce parcours du XSS basé '
                'sur le DOM de la recherche ?',
    'steps': [
        'Connecte-toi, passe une commande, puis ouvre Order History.',
        'Clique sur le bouton camion d’une commande : l’URL contient id=<numéro de commande> et ce numéro s’affiche à l’écran.',
        'Remplace la partie id de l’URL par la charge d’exercice de la carte (balise iframe, encodée dans l’URL).',
        'Recharge l’URL : la balise est interprétée, l’alerte « xss » apparaît et le défi est résolu.',
    ],
    'validation': 'routes/trackOrder.ts:17 résout le défi quand l’identifiant '
                  'de suivi contient la balise attendue.',
    'why': 'Le numéro de suivi vient de l’URL et est réinséré dans la page sans '
           'neutralisation. Dans l’onglet Réseau, tu vois la réponse du serveur '
           'contenir déjà la balise : la différence avec le défi 10, traité '
           'entièrement dans le navigateur.',
    'fix': 'Neutraliser (échapper) toute donnée issue de l’URL avant affichage '
           '(fiche OWASP Cross Site Scripting Prevention).',
    'trouble': [
        ('Le numéro revient « nettoyé » sans alerte', 'ce défi est désactivé par '
         'défaut sous Docker (safetyMode). L’image JuiceLab corrigée le réactive ; '
         'préviens l’enseignant si l’alerte n’apparaît pas.'),
    ],
    'further': 'Pourquoi un XSS réfléchi dépend-il du serveur alors que le XSS DOM n’en dépend pas ?',
    'book': 336,
})

DJ23.append({
    'key': 'xssBonusChallenge',
    'title': 'Bonus Payload',
    'day': 3, 'difficulty': 1, 'category': 'XSS',
    'goal': 'Utiliser la charge bonus fournie sur la carte pour intégrer un '
            'lecteur audio dans la page de recherche.',
    'notion': 'Le même défaut que le défi 10 permet d’intégrer du contenu '
              'externe (ici un lecteur SoundCloud) : une saisie rendue comme du '
              'HTML peut charger des ressources tierces.',
    'task': 'Reviens sur la surface de recherche. Essaie la charge bonus fournie '
            'sur la carte et observe le type de contenu que le navigateur tente '
            'd’intégrer.',
    'question': 'Quels risques introduit une intégration HTML provenant d’un '
                'champ de recherche ?',
    'steps': [
        'Ouvre la carte du défi et copie la charge bonus affichée (une balise iframe vers un lecteur audio).',
        'Colle-la dans la barre de recherche et valide avec Entrée.',
        'Le navigateur insère un lecteur SoundCloud dans la page : le défi est résolu.',
    ],
    'validation': 'registerWebsocketEvents.ts:41 résout le défi quand la saisie '
                  'contient exactement la charge bonus définie dans la config.',
    'why': 'Même cause que le défi 10 : la recherche est rendue comme du HTML. '
           'Une saisie peut donc charger une ressource d’un autre site.',
    'fix': 'Identique au défi 10 : ne pas traiter la recherche comme du HTML. '
           'La lecture du son relève du service externe et n’est pas évaluée.',
    'trouble': [
        ('Pas de lecteur', 'la charge doit être copiée entière depuis la carte, sans coupure.'),
    ],
    'further': 'En quoi charger une ressource externe depuis une saisie est-il un risque, au-delà de l’alerte ?',
    'book': 323,
})

DJ23.append({
    'key': 'forgedFeedbackChallenge',
    'title': 'Forged Feedback',
    'day': 3, 'difficulty': 3, 'category': 'Broken Access Control',
    'goal': 'Poster un avis au nom d’un autre utilisateur.',
    'notion': 'Le serveur doit déduire l’auteur d’une action de la session, pas '
              'd’un champ que le navigateur peut modifier.',
    'task': 'Avec un compte de labo connecté, poste un avis client au nom d’un '
            'autre utilisateur. Relève le champ que tu as manipulé et la valeur '
            'choisie.',
    'question': 'Où le serveur devrait-il déterminer l’auteur d’un avis au lieu '
                'de faire confiance au client ?',
    'steps': [
        ('Connecte-toi et ouvre le formulaire de contact :', 'http://localhost:3000/#/contact'),
        'F12, onglet Éléments (Inspecteur) : repère en haut du formulaire un champ caché userId (attribut hidden).',
        'Retire l’attribut hidden de ce champ : il devient visible dans le formulaire.',
        'Saisis l’identifiant d’un autre utilisateur dans ce champ, écris un commentaire, règle la note, résous le captcha et envoie.',
        'L’avis est enregistré au nom de l’autre utilisateur : le défi est résolu.',
    ],
    'validation': 'routes/verify.ts:30-38 résout le défi quand le UserId envoyé '
                  'diffère de celui de ta session.',
    'why': 'Le formulaire fixe l’auteur dans un champ caché envoyé par le '
           'navigateur. Comme le serveur lui fait confiance, ce champ peut être '
           'changé pour désigner un autre compte.',
    'fix': 'Déterminer l’auteur à partir de la session authentifiée côté serveur '
           'et ignorer tout UserId reçu du client (fiche OWASP Authorization).',
    'trouble': [
        ('Erreur à l’envoi', 'résous le captcha affiché sur la page avant de soumettre.'),
        ('Le champ userId reste caché', 'sélectionne bien la balise input userId avant de supprimer hidden.'),
    ],
    'further': 'Quelle autre action d’une application ne devrait jamais lire son auteur depuis le client ?',
    'book': 344,
})
