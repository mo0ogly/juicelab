"""Defender view for each TD challenge (cyberdefense students).

For every challenge: what a defender can observe (detect), and how to check
that the fix holds (verify). Recommendations, not claims about Juice Shop's
own logging: Juice Shop does not ship these detections.
"""

DEFENSE = {
    'scoreBoardChallenge': {
        'detect': 'Requêtes vers des routes absentes du menu, émises sans '
                  'navigation préalable : signe de reconnaissance par lecture '
                  'du code client.',
        'verify': 'Lister les routes du bundle et confirmer que chaque page '
                  'sensible renvoie un refus côté serveur sans session adaptée.',
    },
    'privacyPolicyChallenge': {
        'detect': 'Rien à détecter : le défi sert de référence. Note les '
                  'engagements de la politique pour les comparer aux fuites '
                  'des défis suivants.',
        'verify': 'Confronter chaque engagement de la politique à un test : '
                  'une donnée citée comme protégée doit l’être réellement.',
    },
    'directoryListingChallenge': {
        'detect': 'Accès à la racine d’un dossier servi (/ftp) suivi de '
                  'téléchargements en série : signe d’exploration de fichiers.',
        'verify': 'Après correction, /ftp et /ftp/acquisitions.md doivent '
                  'répondre 404 ; un inventaire des dossiers servis ne doit '
                  'contenir aucun document interne.',
    },
    'exposedCredentialsChallenge': {
        'detect': 'Connexion réussie d’un compte de test en production, ou '
                  'depuis une adresse inhabituelle : alerte à remonter.',
        'verify': 'Rechercher les secrets dans le bundle livré (scan de '
                  'secrets en intégration continue) et confirmer que le compte '
                  'de test est désactivé.',
    },
    'passwordHashLeakChallenge': {
        'detect': 'Appels d’API avec un paramètre de sélection de champs '
                  'contenant des noms sensibles (password) : à journaliser.',
        'verify': 'Appeler l’API avec fields=password : la réponse ne doit '
                  'jamais contenir ce champ, quelle que soit la demande.',
    },
    'loginAdminChallenge': {
        'detect': 'Erreurs SQL renvoyées par la connexion et identifiants '
                  'contenant apostrophes ou commentaires SQL : signaux typiques '
                  'dans les journaux applicatifs ou un WAF.',
        'verify': 'Avec des requêtes paramétrées, une apostrophe dans l’email '
                  'produit un simple échec de connexion, sans erreur SQL.',
    },
    'adminSectionChallenge': {
        'detect': 'Ouverture de la page d’administration par un compte dont le '
                  'rôle n’est pas admin dans la base : écart à alerter.',
        'verify': 'Appeler directement les API d’administration avec un compte '
                  'client : le serveur doit répondre 403, page affichée ou non.',
    },
    'basketAccessChallenge': {
        'detect': 'Une même session qui lit des paniers d’identifiants '
                  'différents, souvent consécutifs : énumération typique.',
        'verify': 'Demander le panier d’un autre compte avec sa propre session : '
                  'réponse attendue 403 ou 404, jamais le contenu.',
    },
    'feedbackChallenge': {
        'detect': 'Suppressions d’avis en rafale, surtout par un compte non '
                  'modérateur : à tracer avec auteur et horodatage.',
        'verify': 'Tenter la suppression avec un compte client : refus attendu. '
                  'Vérifier qu’une suppression autorisée laisse une trace d’audit.',
    },
    'localXssChallenge': {
        'detect': 'Saisies de recherche contenant des balises HTML : visibles '
                  'dans les journaux d’accès si la requête passe par le serveur, '
                  'sinon seulement côté navigateur (CSP report-uri).',
        'verify': 'Après correction, la même saisie s’affiche comme texte brut. '
                  'Une politique CSP stricte bloque en plus les scripts inline.',
    },
    'reflectedXssChallenge': {
        'detect': 'Identifiants de suivi contenant des caractères < > ou des '
                  'schémas javascript: dans les URL journalisées par le serveur.',
        'verify': 'Un identifiant hors format attendu est refusé ou affiché '
                  'échappé ; la réponse de l’API ne renvoie jamais de balise.',
    },
    'xssBonusChallenge': {
        'detect': 'Chargements vers des domaines tiers non prévus depuis la page '
                  'de recherche : visibles par CSP en mode rapport.',
        'verify': 'Avec une CSP frame-src limitée, l’iframe externe est bloquée '
                  'et signalée ; la recherche reste affichée en texte.',
    },
    'forgedFeedbackChallenge': {
        'detect': 'Avis dont l’auteur enregistré diffère de l’utilisateur de la '
                  'session qui l’a posté : comparaison à journaliser.',
        'verify': 'Envoyer un avis avec un UserId étranger : l’avis enregistré '
                  'doit porter l’identité de la session, pas celle envoyée.',
    },
}
