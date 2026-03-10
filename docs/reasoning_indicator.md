# Indicateur de Réflexion (Reasoning Mode)

## Description
Amélioration de l'expérience utilisateur (UX) lors des requêtes longues. Le bot envoie un message temporaire "🧠 Réflexion en cours..." pour indiquer qu'il traite la demande, puis le supprime une fois la réponse finale prête.

## Déroulement Technique
1.  **Envoi du message temporaire** : Dans `core/handlers.py` (`handle_message` et `handle_photo`), envoyer un message texte "🧠 Réflexion en cours..." avant d'appeler l'API Ollama.
2.  **Sauvegarde de l'ID** : Conserver l'objet `Message` retourné par Telegram.
3.  **Nettoyage** : Une fois la réponse de l'IA obtenue (ou en cas d'erreur), utiliser `context.bot.delete_message` pour supprimer le message de réflexion.
4.  **Envoi de la réponse** : Procéder à l'envoi normal de la réponse finale.

## Résultat final attendu
L'utilisateur voit visuellement que l'IA "réfléchit" (particulièrement utile pour les modèles lents comme Qwen 397B ou les générations de PDF), puis ce statut disparaît proprement au profit de la vraie réponse.

## Todo-list
- [x] Créer le document de conception (celui-ci)
- [x] Modifier `handle_message` dans `core/handlers.py`
- [x] Modifier `handle_photo` dans `core/handlers.py`
- [x] Test réussi ? (Déploiement en cours)

## Validation
Le message "🧠 Réflexion en cours..." est correctement envoyé au début du traitement de l'IA, et est ensuite supprimé une fois la réponse reçue.
<!-- Implémentation validée et fonctionnelle -->
