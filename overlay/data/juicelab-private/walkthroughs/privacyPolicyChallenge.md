# Solution canonique - privacyPolicyChallenge : Privacy Policy

## Contexte

Le challenge demande simplement de lire la politique de confidentialite.
Il n'a pas de dimension offensive : son interet pedagogique est
d'introduire le principe d'observation, l'usage du menu lateral, et la
notion qu'une application doit afficher ses obligations legales (RGPD
2016/679 dans l'UE).

## Vulnerabilite exploitee

Aucune au sens strict. Le challenge teste la navigation et la decouverte
UX. Il sert d'echauffement pour aborder ensuite des challenges
exploitant des routes cachees.

Categorie OWASP : non-applicable. CWE : non-applicable.

## Etapes de resolution

1. **Etape 1 - Ouvrir le menu lateral** : cliquer sur l'icone hamburger
   en haut a gauche de la page d'accueil Juice Shop.

2. **Etape 2 - Identifier l'entree Privacy Policy** : dans le panneau
   lateral, parmi les entrees About, Customer Feedback, Photo Wall,
   Privacy Policy.

3. **Etape 3 - Cliquer sur Privacy Policy** : la page de politique de
   confidentialite s'affiche.

4. **Etape 4 - Validation** : Juice Shop detecte que la route
   `/privacy-security/privacy-policy` est atteinte et marque le
   challenge solved.

## Validation automatique

Juice Shop detecte la resolution sur l'evenement de navigation Angular
vers la route. Le challenge `privacyPolicyChallenge` passe a solved=true
des que le composant correspondant s'initialise.

## Concept enseigne

Lire le contenu d'une page web est aussi de l'audit. Ne jamais survoler
les pages institutionnelles (mentions legales, politique de
confidentialite, conditions d'utilisation) : elles peuvent contenir des
informations utiles pour la phase de reconnaissance (juridiction du
prestataire, sous-traitants cites, dates de mise a jour, etc.).

Concept secondaire : l'UX d'une application impose souvent une
hierarchie d'information ou ce qui est important pour l'utilisateur n'est
pas important pour le legal et inversement. Identifier ces decisions
est utile pour cartographier mentalement la surface.

## Prevention

Aucune prevention applicable, c'est une page legitime a afficher. La
seule consideration : s'assurer que le contenu est a jour (RGPD impose
une mise a jour quand la collecte change).

## Variantes pour etudiants avances

- Lire le contenu de la politique et identifier 3 informations
  exploitables par un attaquant en ingenierie sociale (technologies
  utilisees, sous-traitants, contact DPO).
- Comparer la politique de Juice Shop avec celle d'un site reel
  (Amazon, Wikipedia). Identifier les differences de structure.
- Discussion : pourquoi les politiques de confidentialite sont
  generalement illisibles ? Que dit le RGPD article 12 sur la
  transparence et la lisibilite ?
