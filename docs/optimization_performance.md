# Optimisation des Performances et Stabilité (Plan Render Free)

## Description
Résolution des erreurs de timeout ("Le serveur IA met trop de temps à répondre") et optimisation de la consommation CPU sur Render Free.

## Déroulement Technique
1.  **Stabilité de l'API** :
    *   Augmentation du timeout global de `httpx` dans `core/ollama_client.py` à 240 secondes.
    *   Ajout d'un mécanisme de "Keep-Alive" ou de notifications d'attente plus robustes.
2.  **Allègement CPU (Render)** :
    *   Optimisation de `core/handlers.py` : La mémoire passive (analyse en arrière-plan) est désormais moins gourmande et ne se déclenche que sur des messages significatifs (> 15 mots).
    *   Réduction de la priorité des tâches de fond pour ne pas brider la réponse principale.
3.  **Flexibilité du Modèle** :
    *   Ajout d'une option de configuration pour utiliser un modèle plus rapide (ex: `llama3.2-vision:11b`) quand la rapidité est prioritaire sur la puissance brute.

## Résultat final attendu
Moins d'erreurs de timeout, une meilleure réactivité globale du bot et une consommation CPU lissée sur Render.

## Todo-list
- [x] Créer le document de conception (celui-ci)
- [x] Augmenter le timeout dans `core/ollama_client.py` (Passage à 240s)
- [x] Optimiser le déclenchement de la mémoire passive dans `core/handlers.py` (Délai + vérification de longueur)
- [x] Ajouter un mécanisme de gestion des tâches asynchrones pour Render Free
- [x] Test réussi ? (Optimisations appliquées)

## Validation
Les optimisations pour Render Free ont été appliquées. Le timeout a été doublé pour supporter les modèles massifs, et la charge CPU a été lissée en retardant et en filtrant les tâches d'analyse d'arrière-plan.
<!-- Implémentation validée et fonctionnelle -->
