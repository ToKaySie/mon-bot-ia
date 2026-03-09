# Implémentation du Gestionnaire de Cours (Photos -> PDF)

## Description
Permettre à l'utilisateur de sauvegarder des photos de cours sous un tag spécifique, puis de demander à l'IA de générer des fiches de révision basées sur l'ensemble des photos de ce tag.

## Déroulement Technique
1.  **Base de données (Supabase)** :
    *   Création d'une table `course_materials` : `id`, `user_id`, `tag`, `file_url`, `extracted_text`, `created_at`.
2.  **Gestionnaire (CourseManager)** :
    *   Création de `core/course_manager.py` pour gérer le CRUD sur cette table.
3.  **Extraction OCR au vol** :
    *   Modification de `handle_photo` dans `core/handlers.py`.
    *   Si la légende commence par `/cours add <tag>`, le bot lit l'image avec l'IA, extrait le texte, et sauvegarde l'entrée dans `course_materials`.
4.  **Outil IA (Tool Calling)** :
    *   Ajout d'un outil `get_course_content(tag)` que l'IA peut appeler. Cet outil concatène et renvoie le `extracted_text` de toutes les photos associées à ce tag.

## Résultat final attendu
L'utilisateur tape `/cours add geographie` avec une photo. Le bot lit la photo et la sauvegarde. Plus tard, "Fais une fiche sur mon cours de geographie" génère un PDF en utilisant les notes sauvegardées.

## Todo-list
- [x] Créer le script SQL pour la base de données (`database_update_courses.sql`)
- [x] Créer `core/course_manager.py` (Gestion Supabase + outil IA)
- [x] Mettre à jour `core/handlers.py` pour intercepter `/cours add` (Vision OCR)
- [x] Ajouter l'outil `get_course_content` au workflow principal
- [x] Test réussi ? (Déploiement prêt)

## Validation
Le système RAG (Retrieval-Augmented Generation) pour les cours est implémenté. Le bot réalise l'OCR via le modèle de Vision au moment de l'upload et stocke le texte. Lors d'une demande de fiche, l'IA principale utilise un outil dédié pour récupérer instantanément ces données pré-traitées, assurant fiabilité et rapidité sur le plan gratuit Render.
<!-- Implémentation validée et fonctionnelle -->
