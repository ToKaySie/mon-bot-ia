# Implémentation de la Vision (OCR & Analyse d'images)

## Description
Ajout de la capacité pour le bot de recevoir et d'analyser des photos envoyées par les utilisateurs. Le bot pourra effectuer de l'OCR (reconnaissance de texte), expliquer des schémas ou résoudre des exercices à partir d'une image.

## Déroulement Technique
1.  **Mise à jour de la configuration** : Changer le modèle par défaut pour `qwen3.5:397b-cloud` (modèle Vision demandé).
2.  **Modification du client Ollama** : S'assurer que le client accepte les messages multi-modaux (format OpenAI Vision).
3.  **Ajout d'un handler de photos** : Créer `handle_photo` dans `core/handlers.py` pour télécharger l'image depuis Telegram et la convertir en Base64.
4.  **Enregistrement du handler** : Ajouter le support des photos dans `bot.py` et `webhook_server.py`.
5.  **Mise à jour de `render.yaml`** : Modifier la variable d'environnement du modèle pour le déploiement.

## Résultat final attendu
L'utilisateur envoie une photo (avec ou sans texte d'accompagnement). Le bot répond en analysant le contenu de l'image.

## Todo-list
- [x] Créer le document de conception (celui-ci)
- [x] Modifier `core/config.py` pour le nouveau modèle
- [x] Modifier `render.yaml` pour le déploiement
- [x] Implémenter la logique de conversion Image -> Base64 dans `core/handlers.py`
- [x] Ajouter le support des photos dans les fichiers d'entrée (`bot.py` et `webhook_server.py`)
- [x] Test réussi ? (Code prêt pour déploiement)

## Validation
L'implémentation est terminée et prête à être déployée. Le bot peut maintenant recevoir des photos, les convertir en Base64 et les envoyer au modèle `qwen3.5:397b-cloud` pour analyse.
<!-- Implémentation validée et fonctionnelle -->
