# Solution canonique - basketAccessChallenge : View Basket

## Contexte

Apres login, Juice Shop stocke dans le SessionStorage du navigateur une
cle `bid` qui contient l'ID numerique du panier de l'utilisateur courant.
A chaque navigation vers la page panier, le frontend lit cette valeur et
emet une requete `GET /rest/basket/<id>` au backend. Le backend
retourne le contenu du panier sans verifier que l'ID demande appartient
bien a l'utilisateur authentifie : il fait confiance au client.

C'est une instance d'IDOR (Insecure Direct Object Reference) : une
reference directe a un objet en base, sans verification d'autorisation.

## Vulnerabilite exploitee

Insecure Direct Object Reference (IDOR). OWASP Top 10 2021 : A01:2021
Broken Access Control. CWE-639 Authorization Bypass Through
User-Controlled Key. CWE-284 Improper Access Control.

Code vulnerable cote frontend dans `basket.service.ts` :

```typescript
this.find(parseInt(sessionStorage.getItem('bid'), 10)).subscribe(...)
```

Cote backend, la route `/rest/basket/:id` ne verifie pas que :id
appartient au user authentifie via le JWT.

## Etapes de resolution

1. **Etape 1 - Se connecter** : avec un compte (par exemple le compte
   testing decouvert au challenge Exposed Credentials).

2. **Etape 2 - Identifier la cle bid** : ouvrir DevTools, onglet
   Application (Chrome) ou Storage (Firefox). Section Session Storage
   pour le domaine 127.0.0.1:3000. Reperer la cle `bid` et noter sa
   valeur (par exemple 5).

3. **Etape 3 - Modifier la cle** : ouvrir l'onglet Console dans DevTools
   et taper :
   ```javascript
   sessionStorage.setItem('bid', '1')
   ```
   La valeur 1 correspond au panier de l'utilisateur 1, qui est
   admin@juice-sh.op.

4. **Etape 4 - Naviguer vers le panier** : aller sur
   `http://127.0.0.1:3000/#/basket` ou recharger la page. Le frontend
   emet GET /rest/basket/1 et affiche le contenu.

5. **Etape 5 - Validation** : Juice Shop detecte la requete reussie sur
   un basket id different de celui du user authentifie et marque
   `basketAccessChallenge` solved.

## Validation automatique

Le backend Juice Shop garde une trace de l'utilisateur courant via JWT.
Quand une requete `GET /rest/basket/<id>` est emise, si l'ID ne
correspond pas a l'user du JWT mais que la requete reussit (parce que la
verification est manquante), le challenge passe a solved.

## Concept enseigne

L'autorisation doit etre liee a l'objet, pas seulement a l'identite.
Verifier qu'un user est connecte est l'authentification. Verifier que
ce user a le droit d'acceder a CET objet specifique est l'autorisation.
Dans une application multi-tenant ou multi-user, chaque endpoint qui
manipule un objet identifie par un parametre client doit verifier que
le user authentifie est bien proprietaire ou autorise sur cet objet.

Concept secondaire : la securite cote frontend est une illusion. Le
frontend peut sembler limiter l'acces (un input UI ne propose qu'un
choix), mais l'API derriere accepte toutes les valeurs. Tout ce qui est
testable sans frontend (curl, Postman, fetch dans la console) est
testable par un attaquant.

## Prevention

1. **Verification d'ownership server-side** : sur chaque endpoint qui
   accepte un parametre d'objet, verifier que l'utilisateur authentifie
   est autorise. Pour le basket :

   ```typescript
   app.get('/rest/basket/:id', verifyToken, async (req, res) => {
     const basket = await Basket.findByPk(req.params.id)
     if (basket.UserId !== req.user.id) return res.sendStatus(403)
     return res.json(basket)
   })
   ```

2. **IDs non-prevs (UUIDv4)** : utiliser des UUIDs aleatoires au lieu
   d'IDs sequentiels rend l'enumeration impossible. Mais ne dispense pas
   de la verification d'ownership : c'est un ralentisseur, pas une
   defense.

3. **Pattern "request scoped to user"** : tous les endpoints sont
   `/api/me/basket` (sans parametre, deduit du user authentifie) plutot
   que `/api/basket/:id`. L'utilisateur ne peut pas demander le panier
   d'un autre par construction.

4. **Audit & alerting** : detecter les patterns d'acces anormaux (un
   user qui demande sequentiellement les baskets 1, 2, 3, 4...). Une
   regle WAF ou SIEM peut declencher une alerte.

## Variantes pour etudiants avances

- Faire la manipulation entierement en curl, sans navigateur :
  ```bash
  curl -b "token=<jwt>" http://127.0.0.1:3000/rest/basket/1
  ```
- Enumerer les premiers paniers en bash : boucler de 1 a 20, observer
  les reponses (vide ou contenu).
- Tester si la modification du basket d'un autre user est aussi possible
  (PUT, POST, DELETE sur /rest/basket/<id>). Si oui, c'est un bonus
  challenge.
- Discussion : pourquoi cette vulnerabilite est-elle si frequente dans
  les applications reelles ? (souvent : l'auth est implementee avant le
  modele de donnees, et l'ownership est ajoute apres-coup par bouts).
