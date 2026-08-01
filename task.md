# Tâches Frontend - Svelte UI Expert

- [x] **Store Svelte** : Ajout du store `similarityThreshold` (0.85) et exportation dans `appState.js`. Ajout des stores de quotas et limites d'API.
- [x] **Vue Paramètres** : Ajout de la section "⚡ Limites & Cadencement API" avec champs de saisie pour `mistral_quota`, `gemini_quota` (et sélecteurs d'unité) ainsi que `vectorization_batch_limit` (défaut 200). Liaison à l'API de configuration existante.
- [x] **Vue Synthèse IA** : Remplacement de la variable locale `similarityThreshold` par l'import du store global et mise à jour dynamique.
- [x] **Étagères 3D Culture** : Ajout de l'étagère "Cinéma & Séries". Ajout du bouton de gestion des flux avec modale listant 10 flux RSS (avec toggles). Filtrage des articles de l'étagère en fonction des flux actifs et/ou de la catégorie "Étagère Culture".

# Tâches Backend - API & Services
- [x] **Database** : Ajout des requêtes `CREATE INDEX IF NOT EXISTS` dans `backend/app/database.py` (pour category, published_date, created_at sur feeds, articles, podcasts, catalog_feeds).
- [x] **Clustering & IA** : Correction du traitement regex des apostrophes typographiques (' et ’). Contrainte stricte du prompt LLM (Mistral) à 100% en français. Restriction de la classification "Cinéma et séries" aux œuvres scénarisées (exclusion sports, JT, téléréalité, TV).
- [x] **Synthèse Zero-wait** : Implémentation du préchargement et correction du problème de "tuile bloquée en synthèse" en appliquant un fallback sur le titre de la première source avec un statut "pending".
- [x] **Cache Mémoire Onglets** : `ExplorerView.svelte` mis à jour pour cacher les onglets inactifs au lieu de les détruire, supprimant les délais.
- [x] **Étagères 3D Culture** : `Culture3DShelvesView.svelte` corrigé pour le z-index au survol et l'overflow/padding pour éviter les tuiles tronquées aux bords.
- [x] **Carte Géo** : `GeoMapView.svelte` mis à jour pour afficher 100% des prévisualisations et correction du saut de texte / perte d'apostrophe.
