"""Front-matter sections for the student TD guide.

Pure text/content, no formatting. Consumed by build_guide_td.py before the
13 challenge sheets. Sources: Juice Shop 20.4.0-SNAPSHOT UI and the overlay
score-board card (patches/juicelab-core.patch).
"""

INTRO = (
    'Treize défis en trois demi-journées pour apprendre à observer une '
    'application web, reproduire un comportement et expliquer la mesure de '
    'protection adaptée. Ce guide donne, pour chaque défi : le but, la notion '
    'à retenir, les étapes exactes, la façon dont Juice Shop valide, la '
    'correction, et un dépannage. Le coach JuiceLab (bouton TD) accompagne '
    'chaque défi dans le navigateur.'
)

# "Préparer ta séance" bullets.
PREP = [
    'Ouvre l’instance indiquée en cours. Sur une installation locale standard, '
    'l’adresse est http://localhost:3000. Adapte le port si besoin.',
    'Crée un compte de labo depuis Account → Login → Not yet a customer?, puis '
    'connecte-toi. Certains défis exigent une session.',
    'Ouvre ton tableau de bord JuiceLab : http://localhost:3000/#/juicelab '
    '(remplace le port si le tien diffère). C’est là que tu suis ta '
    'progression, tes indices, ton journal et tes badges. Garde cet onglet '
    'ouvert pendant toute la séance.',
    'Le titre anglais de la carte (ex. Score Board) sert d’identifiant : c’est '
    'celui utilisé dans ce guide et dans le coach.',
]

# Dedicated section on the Score Board — the challenge page the student works
# from. title, intro, then labelled paragraphs and a bullet list of columns.
SCORE_BOARD = {
    'title': 'La page des défis (Score Board)',
    'intro': (
        'Le Score Board est ta page de travail : elle liste les défis du TD et '
        'suit ton avancement. Tu l’ouvres au défi 01, puis tu y reviens entre '
        'chaque exercice. Son adresse est http://localhost:3000/#/score-board.'
    ),
    'paras': [
        ('Repérer un défi',
         'Chaque défi est une carte portant son titre anglais, sa catégorie '
         'OWASP et sa difficulté en étoiles (1 à 2 pour la demi-journée 1, '
         'jusqu’à 3 pour les défis XSS et l’avis forgé). Utilise la barre de '
         'recherche et les filtres en haut pour retrouver une carte par son nom '
         'ou sa catégorie.'),
        ('Lire l’état d’un défi',
         'Une carte non résolue est grisée. Dès que Juice Shop valide le défi, '
         'la carte prend un liseré vert et un point vert à gauche du titre, et '
         'le compteur en haut de page augmente. C’est ce changement visuel qui '
         'confirme la réussite, en plus du bandeau « solved » affiché sur le '
         'moment.'),
        ('Ouvrir le coach du TD',
         'Sur la carte, à côté de l’icône de chapeau, le bouton TD ouvre le '
         'coach JuiceLab : Briefing (mission), Hints (indices gradués), '
         'After - logbook (journal) et Quiz. Travaille un défi avec le coach '
         'ouvert à côté de la boutique.'),
        ('Suivre tes badges',
         'Ton tableau de bord JuiceLab s’ouvre à l’adresse '
         'http://localhost:3000/#/juicelab. Sa section Badges résume ton '
         'parcours : défis résolus, indices utilisés, journaux de plus de 50 '
         'mots. Compare le critère affiché sur chaque carte à ton compteur pour '
         'savoir ce qu’il te reste à faire.'),
    ],
    # Columns/landmarks of a Score Board card, shown as a bullet list.
    'landmarks': [
        'Titre anglais de la carte : l’identifiant du défi, repris dans ce guide.',
        'Catégorie OWASP : la famille de faille (ex. Sensitive Data Exposure, Injection, XSS).',
        'Étoiles de difficulté : de 1 (découverte) à 3 (plus exigeant).',
        'Liseré et point : gris tant que le défi n’est pas résolu, verts après validation.',
        'Bouton TD : ouvre le coach (briefing, indices, journal, quiz).',
    ],
    'capture': ('e-badges', 'Section Badges du panneau JuiceLab : chaque carte '
                'indique le critère et ton avancement.'),
}
