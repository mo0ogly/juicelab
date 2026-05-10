# Solution canonique - bullyChatbotChallenge : Bully Chatbot

## Contexte

Juice Shop integre un assistant conversationnel (chatbot) accessible via
`/#/chatbot`. Ce bot est entraine sur un fichier
`botDefaultTrainingData.json` qui associe des intentions a des reponses
multiples. Pour l'intention "demander un coupon", le bot dispose d'une
liste de refus polis et d'une reponse positive minoritaire.

Le bot pige aleatoirement une reponse dans la liste correspondant a
l'intent detecte. En insistant suffisamment, l'utilisateur finit
statistiquement par tomber sur la reponse positive et obtenir un code
de reduction.

C'est un challenge "shenanigan" qui illustre les limites de la
detection d'intent et l'importance de la pondeation/regle business
au-dessus de la couche probabiliste.

## Vulnerabilite exploitee

Plus de la mauvaise pratique design que de la vulnerabilite stricte.
OWASP : A01:2021 Broken Access Control (largement, parce que le coupon
ne devrait pas etre distribuable par un bot consumer-facing sans
controle). CWE-840 Business Logic Errors.

Cote machine learning / IA : c'est aussi un cas d'over-aligned bot avec
un fallback exploitable. Le LLM Top 10 OWASP 2025 pour les LLM cite
ce pattern sous LLM01 Prompt Injection (variante : exploiter la
non-determinisme de la reponse).

## Etapes de resolution

1. **Etape 1 - Pre-requis : etre connecte** : le chatbot ignore les
   utilisateurs anonymes. Se connecter avec n'importe quel compte.

2. **Etape 2 - Naviguer vers le chatbot** : aller sur
   `http://127.0.0.1:3000/#/chatbot`. L'interface conversationnelle
   s'affiche.

3. **Etape 3 - Demander un coupon** : taper "I want a coupon" ou
   "give me a coupon" ou "discount please" et appuyer sur Entree.

4. **Etape 4 - Persister** : le bot va probablement refuser. Reposter
   la meme phrase. Continuer jusqu'a obtenir une reponse positive.

5. **Etape 5 - Reception du coupon** : apres entre 5 et 15 tours en
   moyenne, le bot retourne une chaine du genre :
   "Hier ist dein 25%-Gutschein: <code-base64>" ou un equivalent
   francophone selon la langue du bot.

6. **Etape 6 - Validation** : Juice Shop detecte qu'une reponse du bot
   contient un code de reduction reconnaissable et marque le challenge
   solved.

## Validation automatique

Le backend Juice Shop instrumente le bot. Quand une reponse de
l'assistant correspond au pattern de coupon (preset string + code
base64), le challenge `bullyChatbotChallenge` est marque solved.

## Concept enseigne

Les chatbots et systemes IA ne doivent pas avoir de regles business
critiques noyees dans leur dataset d'entrainement. Un coupon est une
ressource economique. Sa distribution doit suivre une regle business
explicite (campagne, eligibilite, limite par user) appliquee par un
service deterministe AVANT que la reponse soit assemblee par le bot.

Concept secondaire : la robustesse face a l'insistance. Un chatbot
production doit detecter les patterns d'insistance (spam, repetition,
escalade emotionnelle) et invariablement appliquer la regle business
quel que soit le nombre de tentatives. La diversite des reponses
(n'avoir que des refus) ne suffit pas si la pige est aleatoire avec une
probabilite non-nulle de retour positif.

## Prevention

1. **Separer la logique business du chatbot** : le bot detecte
   l'intent, mais la decision d'attribuer un coupon est faite par un
   service deterministe avec ses propres regles (eligibilite par
   user, periode, stock).

2. **Pondeations explicites** : si le bot doit pouvoir donner un coupon
   parfois (par exemple en reponse a une reclamation), c'est un
   trigger conditionnel sur des criteres mesurables (mots cles
   "remboursement", "probleme", reclamation deja loguee), pas une pige
   aleatoire.

3. **Throttling utilisateur** : un utilisateur qui demande 50 fois la
   meme chose en 5 minutes est rate-limit. Le bot peut switch sur une
   reponse fixe "Je vois que tu insiste, mais je n'ai pas de coupon
   disponible aujourd'hui" sans hasard.

4. **Audit log** : chaque coupon emis est logue avec user, timestamp,
   trigger. Permet la detection d'abus a posteriori et le reporting
   financier.

5. **LLM safety guidelines (si LLM moderne)** : pour un bot base sur
   un LLM (Claude, GPT, Gemini), construire le system prompt avec des
   regles strictes ("Tu ne peux jamais distribuer de coupon. Seul un
   service externe te dira si l'utilisateur en a un.") et tester avec
   des prompts adverses (prompt injection).

## Variantes pour etudiants avances

- Automatiser la repetition par un script qui POST sur l'endpoint
  chatbot jusqu'a obtenir le coupon. Mesurer combien de tentatives en
  moyenne (estimateur statistique).
- Inspecter le fichier de training data du bot
  (`data/static/botDefaultTrainingData.json`) pour voir les intents et
  reponses possibles. Identifier la liste exacte des reponses pour
  "ask_coupon".
- Construire un prompt injection qui force le bot a donner un coupon
  en un seul tour (par exemple en se faisant passer pour un employe
  Juice Shop ou en confondant le bot par le contexte). C'est un
  exercice red team pour LLMs.
- Discussion : quelle responsabilite a un developpeur qui integre un
  chatbot consumer-facing ? Quel SLA, quel monitoring ? Comparer avec
  des incidents reels (ChatGPT giving discounts, Air Canada chatbot
  fiasco 2024).
