# Tâches Frontend - Svelte UI Expert

- [x] **Store Svelte** : Ajout du store `similarityThreshold` (0.85) et exportation dans `appState.js`. Ajout des stores de quotas et limites d'API.
- [x] **Vue Paramètres** : Ajout de la section "⚡ Limites & Cadencement API" avec champs de saisie pour `mistral_quota`, `gemini_quota` (et sélecteurs d'unité) ainsi que `vectorization_batch_limit` (défaut 200). Liaison à l'API de configuration existante.
- [x] **Vue Synthèse IA** : Remplacement de la variable locale `similarityThreshold` par l'import du store global et mise à jour dynamique.
- [x] **Étagères 3D Culture** : Ajout de l'étagère "Cinéma & Séries". Ajout du bouton de gestion des flux avec modale listant 10 flux RSS (avec toggles). Filtrage des articles de l'étagère en fonction des flux actifs et/ou de la catégorie "Étagère Culture".
