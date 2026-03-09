# Implémentation du Générateur de Planning Intelligent (Coach IA)

## Description
Un système avancé permettant à l'utilisateur de déclarer un examen à venir. L'IA génère un programme de révision détaillé semaine par semaine, produit un tableau de bord PDF, et programme des rappels proactifs via Telegram.

## Déroulement Technique
1.  **Base de données (Supabase)** :
    *   Création des tables `exams` (id, user_id, subject, date, goal) et `revision_sessions` (id, exam_id, date, topic, is_done, notified).
2.  **Logique Métier (`core/planner.py`)** :
    *   `PlannerManager` pour gérer le CRUD des examens et des sessions.
    *   Outil IA `generate_smart_plan` : L'IA reçoit l'objectif, calcule les semaines restantes, et appelle cet outil avec un JSON structuré du planning.
3.  **Rendu PDF Spécialisé** :
    *   Ajout d'une méthode `create_planning_dashboard` dans `PDFManager` pour générer un PDF visuel (Timeline, checklist par semaine).
4.  **Système de Rappels (Telegram JobQueue)** :
    *   Configuration de `app.job_queue` dans `bot.py` et `webhook_server.py`.
    *   Une tâche asynchrone qui tourne toutes les heures pour vérifier s'il y a des sessions de révision prévues aujourd'hui et envoyer un message push à l'utilisateur.

## Résultat final attendu
- "J'ai mon bac de français le 15 juin".
- L'IA répond, crée la base de données, génère un PDF "Roadmap Bac Français" avec le détail par semaine, et Telegram vous envoie un message le matin de chaque session prévue.

## Todo-list
- [x] Script SQL pour les tables `exams` et `revision_sessions` (`database_planner.sql`).
- [x] Créer `core/planner.py` (Manager + Définition de l'outil IA).
- [x] Intégrer l'outil IA dans `core/handlers.py` et gérer la création automatique de PDF.
- [x] Mettre à jour la logique PDF pour accepter les tableaux de bord.
- [x] Activer et configurer `JobQueue` dans les fichiers de démarrage pour les notifications proactives.
- [x] Test réussi ? (Prêt à être déployé)

## Validation
Le générateur de planning intelligent a été complètement intégré. L'IA a désormais la capacité de créer des calendriers de révision structurés, de les sauvegarder en base de données, et de générer une "roadmap" PDF. De plus, un système de tâche asynchrone (`JobQueue`) tourne en toile de fond pour relancer l'utilisateur les jours de session.
<!-- Implémentation validée et fonctionnelle -->
