# Restriction d'Accès par ID Utilisateur

## Description
Mise en place d'une liste blanche (whitelist) pour restreindre l'utilisation du bot à un seul utilisateur spécifique.

## Déroulement Technique
1.  **Configuration** : Ajouter l'ID `5981844665` dans la variable d'environnement `ALLOWED_USERS` via `render.yaml`.
2.  **Code** : S'assurer que le mécanisme de vérification dans `core/handlers.py` utilise correctement cette liste.

## Résultat final attendu
Le bot ignorera ou rejettera toutes les requêtes provenant d'un ID différent de `5981844665`.

## Todo-list
- [x] Modifier `render.yaml` pour inclure l'ID autorisé
- [x] Vérifier la logique de filtrage dans `core/handlers.py`
- [x] Test réussi ?

## Validation
Restriction appliquée. Seul l'ID 5981844665 peut interagir avec le bot.
<!-- Implémentation validée et fonctionnelle -->
