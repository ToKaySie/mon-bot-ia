# Implémentation du Rendu Académique V2 (Math & Tableaux)

## Description
Amélioration majeure du générateur de PDF pour supporter l'affichage réel des formules mathématiques (LaTeX) et le rendu propre des tableaux Markdown.

## Déroulement Technique
1.  **Système de Formules** :
    *   Détection des balises `$$ ... $$` (bloc) et `$ ... $` (en ligne).
    *   Utilisation de l'API de rendu LaTeX (Codecogs/MathJax) pour obtenir des images PNG/SVG.
    *   Intégration de ces images directement dans le flux du PDF.
2.  **Système de Tableaux** :
    *   Détection des blocs de tableaux Markdown (`| col1 | col2 |`).
    *   Parsing des données et utilisation de `pdf.table()` de `fpdf2` pour un rendu avec bordures et alignements.
3.  **Gestion du cache** : Stockage temporaire des images de formules pour éviter des requêtes redondantes.
4.  **Mise à jour du Prompt** : Informer l'IA qu'elle peut désormais utiliser du LaTeX complexe et des tableaux pour ses fiches.

## Résultat final attendu
Un PDF académique parfait où les équations (ex: intégrales, fractions, matrices) sont proprement dessinées et les tableaux sont lisibles et bien formatés.

## Todo-list
- [x] Créer le document de conception (celui-ci)
- [x] Implémenter le parser de tableaux dans `core/pdf_manager.py`
- [x] Implémenter le moteur de rendu de formules (Image-based LaTeX)
- [x] Mettre à jour `_markdown_to_pdf` pour intégrer ces nouveaux éléments
- [x] Ajuster le `SYSTEM_PROMPT` dans `core/config.py` pour encourager l'usage du LaTeX
- [x] Test réussi ? (Déploiement prêt)

## Validation
Le système de rendu PDF a été mis à niveau vers la V2. Il supporte désormais les formules mathématiques complexes via l'API CodeCogs et les tableaux Markdown via la fonction native de fpdf2. Le prompt système a été mis à jour pour que l'IA exploite ces nouvelles capacités.
<!-- Implémentation validée et fonctionnelle -->
