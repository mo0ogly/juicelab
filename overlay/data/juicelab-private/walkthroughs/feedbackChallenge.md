# Solution canonique - feedbackChallenge : Five-Star Feedback

## Contexte

Le challenge demande de supprimer tous les feedbacks 5 etoiles existants.
Cela suppose un acces administrateur (challenge Login Admin) et la
decouverte de la section admin (challenge Admin Section). Une fois sur
la page Administration, la liste des feedbacks affiche un bouton de
suppression pour chaque entree. Le challenge se valide quand le compteur
de feedbacks dont rating = 5 atteint zero.

## Vulnerabilite exploitee

Composition de Broken Access Control + SQL Injection. OWASP Top 10
2021 : A01:2021 Broken Access Control + A03:2021 Injection. C'est la
chaine de challenges qui constitue le scenario realiste : un attaquant
n'a generalement pas une vulnerabilite isolee, il en compose plusieurs.

CWE-862 Missing Authorization (la session admin obtenue par SQLi
contourne l'autorisation feedback). CWE-89 SQL Injection (le moyen
d'obtenir le JWT admin).

## Etapes de resolution

1. **Etape 1 - Pre-requis** : etre connecte avec un compte admin.
   - Se rendre sur /#/login.
   - Email : `' OR true--`
   - Password : n'importe quoi.
   - Cliquer Log in. Le JWT contient maintenant role=admin.

2. **Etape 2 - Acceder a la section admin** :
   - Taper `http://127.0.0.1:3000/#/administration` dans la barre
     d'adresse.
   - La page Administration affiche la liste des feedbacks et users.

3. **Etape 3 - Identifier les feedbacks 5 etoiles** : dans la table des
   feedbacks, repere les lignes dont la colonne Rating affiche 5
   etoiles.

4. **Etape 4 - Supprimer chaque feedback 5 etoiles** : cliquer sur
   l'icone poubelle dans la colonne Actions de chaque ligne 5 etoiles.
   Confirmer la suppression. Repeter pour toutes les entrees 5 etoiles.

5. **Etape 5 - Validation** : Juice Shop detecte que le compteur
   `count(rating=5)` est tombe a 0 et marque le challenge solved.

   Si le bouton UI est desactive cote frontend, l'API DELETE est
   utilisable directement :
   ```bash
   curl -X DELETE -H "Authorization: Bearer <jwt>" \
     http://127.0.0.1:3000/api/Feedbacks/<id>
   ```

## Validation automatique

Voir `routes/verify.ts` lignes 219-227 :

```typescript
function feedbackChallenge () {
  FeedbackModel.findAndCountAll({ where: { rating: 5 } }).then(
    ({ count }: { count: number }) => {
      if (count === 0) {
        challengeUtils.solve(challenges.feedbackChallenge)
      }
    }
  )
}
```

Le challenge est appele a chaque verification periodique (route
/rest/continue-code). Quand le count tombe a zero, il est marque solved.

## Concept enseigne

Composer plusieurs vulnerabilites pour construire une attaque realiste.
Une SQLi seule, sans la decouverte de la route admin, donne un JWT mais
pas de cible visible. Une route admin sans JWT admin donne 401. La
combinaison des deux + l'absence de verification d'autorisation par
operation specifique (DELETE feedback) ouvre la porte au sabotage.

Concept secondaire : la suppression est une attaque souvent oubliee
quand on parle de securite. On pense a "voler" des donnees, on pense
moins a "supprimer" des donnees, qui peut avoir des consequences
juridiques (preuves comptables, traces d'audit) ou commerciales (avis
clients).

## Prevention

1. **Autorisation par operation, pas seulement par section** : etre
   admin n'autorise pas a supprimer n'importe quoi. Une matrice
   action/role definit precisement qui peut deleter quoi. Par exemple,
   la suppression de feedbacks pourrait necessiter un role distinct
   `feedback_moderator` ou un workflow d'approbation.

2. **Soft delete + journal d'audit** : la suppression definitive est
   remplacee par un flag `deleted_at`. Toute suppression est logue avec
   user, timestamp, raison. Permet la restauration et la detection
   d'abus.

3. **MFA pour actions destructrices** : avant suppression definitive,
   demander une re-authentification ou un second facteur. Ralentit
   significativement les abus opportunistes.

4. **Throttling/Rate limiting** : limite le nombre de DELETE par
   minute. Un admin legitime n'a pas besoin de supprimer 50 feedbacks
   en 5 secondes.

5. **Defense en profondeur** : chaque vulnerabilite individuelle doit
   etre fixee. Bloquer la SQLi (requetes parametrees) empeche l'auth
   admin frauduleuse en amont. Bloquer l'IDOR sur les feedbacks (valider
   ownership ou role specifique) empeche la suppression.

## Variantes pour etudiants avances

- Faire la suppression entierement via curl :
  ```bash
  # 1. Login admin via SQLi
  curl -X POST http://127.0.0.1:3000/rest/user/login \
    -H "Content-Type: application/json" \
    -d '{"email":"'\''  OR true--","password":"x"}'
  # 2. Lister les feedbacks
  curl -b "token=<jwt>" http://127.0.0.1:3000/api/Feedbacks/
  # 3. Supprimer chaque feedback 5 etoiles
  curl -X DELETE -b "token=<jwt>" http://127.0.0.1:3000/api/Feedbacks/<id>
  ```
- Discussion : pourquoi le frontend cache-t-il parfois des actions qui
  sont quand meme accessibles par l'API ? (souvent : developpement
  decentralise, frontend "secrete" inconnu de l'API team).
- Activite : ecrire un script qui detecte tous les endpoints
  accessibles par DELETE qu'un user normal peut atteindre (audit
  d'autorisation par sondage).
- Discussion : comment un blue team peut-il detecter cette attaque
  apres coup ? (audit log feedbacks supprimes en bloc, alerte SIEM sur
  pattern de suppression).
