# Implémentation du Rendu Académique V3 (Roboto Slab & Tableaux Riches)

## Description
Amélioration esthétique et technique du générateur de PDF. Passage à la police Roboto Slab et support complet des formules LaTeX à l'intérieur des tableaux.

## Déroulement Technique
1.  **Gestion des Polices** :
    *   Téléchargement des fichiers `.ttf` de **Roboto Slab** depuis les serveurs Google Fonts.
    *   Mise à jour de `AcademicPDF` pour utiliser Roboto Slab comme police principale.
2.  **Moteur de Tableaux V2** :
    *   Remplacement de `pdf.table()` par un système de rendu manuel basé sur `multi_cell`.
    *   Intégration de `_write_rich_line` dans le rendu des cellules pour supporter le LaTeX `$ ... $`.
3.  **Optimisation du Rendu Math** :
    *   Ajustement de la taille des images LaTeX pour qu'elles s'intègrent mieux dans les lignes de texte des tableaux.

## Résultat final attendu
Un PDF avec une typographie Roboto Slab élégante, où toutes les formules mathématiques sont correctement rendues, y compris lorsqu'elles sont à l'intérieur de tableaux complexes.

## Todo-list
- [x] Créer le document de conception (celui-ci)
- [x] Télécharger les polices Roboto Slab dans le dossier `fonts/` (Automatisé dans le code)
- [x] Mettre à jour `AcademicPDF` dans `core/pdf_manager.py` (Usage de Roboto Slab)
- [x] Réimplémenter le parser de tableaux pour supporter le texte riche (LaTeX)
- [x] Ajuster le `SYSTEM_PROMPT` (Consignes conservées)
- [x] Test réussi ? (Déploiement prêt)

## Validation
Le rendu PDF est désormais passé en V3. La police **Roboto Slab** est utilisée pour un aspect plus académique et moderne. Les tableaux supportent maintenant le texte riche, y compris les formules LaTeX `$ ... $` à l'intérieur de n'importe quelle cellule, grâce à un nouveau moteur de rendu de tableaux sur mesure.
<!-- Implémentation validée et fonctionnelle -->
