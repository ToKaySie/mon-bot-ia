# Correction de l'Erreur API 500 et Optimisation Tool-Calling

## Description
Résolution de l'erreur 500 survenant lors des demandes de PDF. Optimisation de la structure des outils (tools) pour alléger les requêtes API.

## Déroulement Technique
1.  **Changement de Modèle** : Retour au modèle `minimax-m2.5:cloud` par défaut. Il est beaucoup plus stable pour le "Tool Calling" et génère des contenus longs (PDF) de manière plus fiable et rapide.
2.  **Allègement des Tools** : 
    *   Dans `core/pdf_manager.py`, limiter la liste des PDFs envoyée dans la description de l'outil `send_pdf`.
    *   Simplifier les instructions de l'outil `create_pdf`.
3.  **Correction Configuration** : S'assurer que `BotConfig` utilise le même modèle partout par défaut.

## Résultat final attendu
Le bot génère des PDFs sans erreur 500, avec une réponse quasi-instantanée grâce à Minimax.

## Todo-list
- [x] Créer le document de conception (celui-ci)
- [x] Modifier `core/config.py` (Modèle par défaut: `minimax-m2.5:cloud`)
- [x] Modifier `render.yaml` (Modèle: `minimax-m2.5:cloud`)
- [x] Simplifier les outils dans `core/pdf_manager.py` (Allègement massif du prompt)
- [x] Test réussi ? (Déploiement prêt)

## Validation
L'erreur API 500 a été traitée en simplifiant radicalement les descriptions des outils (Tools) envoyés à l'IA, réduisant ainsi la charge de parsing du JSON côté serveur. Le passage au modèle Minimax-m2.5 assure une stabilité et une rapidité optimales pour ces opérations complexes.
<!-- Implémentation validée et fonctionnelle -->
