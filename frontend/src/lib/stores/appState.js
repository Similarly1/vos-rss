import { writable, get } from 'svelte/store';

// 'feeds' | 'discover' | 'synthesis' | 'perplexity' | 'podcast'
export const currentView = writable('feeds');

// Responsive state
export const isMobile = writable(false);

// Selected article or cluster ID
export const selectedItemId = writable(null);

// Modals
export const showAddFeedModal = writable(false);
export const showFeedManagerModal = writable(false);

// Refreshing state indicator
export const isRefreshingFeeds = writable(false);

// Settings state
export const mistralApiKey = writable('');
export const selectedMistralModel = writable('mistral-small-latest');
export const geminiApiKey = writable('');
export const selectedGeminiModel = writable('gemini-1.5-flash');

export const synthesisProvider = writable('mistral');
export const vectorizationProvider = writable('mistral');
export const fallbackEnabled = writable(true);

export const refreshIntervalMinutes = writable(30);
export const articleRetentionDays = writable(14);

// Reader Language & Full Text filter preferences
export const articleLanguageFilter = writable('fr');
export const fullTextOnlyFilter = writable(false);

// Articles & Feeds stores
export const articlesList = writable([]);
export const feedsList = writable([]);

export async function fetchVpsSettings() {
  try {
    const res = await fetch('/api/feeds/settings');
    if (res.ok) {
      const result = await res.json();
      const data = result.data;
      
      if (data.mistral_key) mistralApiKey.set(data.mistral_key);
      if (data.gemini_key) geminiApiKey.set(data.gemini_key);
      if (data.synthesis_provider) synthesisProvider.set(data.synthesis_provider);
      if (data.vectorization_provider) vectorizationProvider.set(data.vectorization_provider);
      if (data.mistral_model) selectedMistralModel.set(data.mistral_model);
      if (data.gemini_model) selectedGeminiModel.set(data.gemini_model);
      if (data.fallback_enabled !== undefined) fallbackEnabled.set(data.fallback_enabled);
      if (data.refresh_interval_minutes) refreshIntervalMinutes.set(data.refresh_interval_minutes);
      if (data.article_retention_days) articleRetentionDays.set(data.article_retention_days);
      if (data.article_language) articleLanguageFilter.set(data.article_language);
      if (data.full_text_only !== undefined) fullTextOnlyFilter.set(data.full_text_only);
      
      return data;
    }
  } catch (err) {
    console.error("Erreur synchro paramètres VPS:", err);
  }
  return null;
}

export async function saveSettings(mistralKey, mistralModel, geminiKey, geminiModel, synthProv, vectProv, fallback, refreshMinutes = 30, langFilter = 'fr', fullTextOnly = false, retentionDays = 14) {
  mistralApiKey.set(mistralKey);
  selectedMistralModel.set(mistralModel);
  geminiApiKey.set(geminiKey);
  selectedGeminiModel.set(geminiModel);
  synthesisProvider.set(synthProv);
  vectorizationProvider.set(vectProv);
  fallbackEnabled.set(fallback);

  refreshIntervalMinutes.set(refreshMinutes);
  articleLanguageFilter.set(langFilter);
  fullTextOnlyFilter.set(fullTextOnly);
  articleRetentionDays.set(retentionDays);

  try {
    const res = await fetch('/api/feeds/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mistral_key: mistralKey,
        gemini_key: geminiKey,
        synthesis_provider: synthProv,
        vectorization_provider: vectProv,
        mistral_model: mistralModel,
        gemini_model: geminiModel,
        fallback_enabled: fallback,
        refresh_interval_minutes: refreshMinutes,
        article_retention_days: retentionDays,
        article_language: langFilter,
        full_text_only: fullTextOnly
      })
    });
    if (!res.ok) {
      console.error("Erreur d'enregistrement sur le serveur.");
    }
  } catch (err) {
    console.error("Erreur réseau:", err);
  }

  runArticlesCleanup(retentionDays);
  setupAutoRefresh();
  fetchArticles();
}

export async function runArticlesCleanup(days) {
  try {
    const res = await fetch('/api/feeds/cleanup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ retention_days: days })
    });
    if (res.ok) {
      await fetchArticles();
      return await res.json();
    }
  } catch (err) {
    console.error("Erreur nettoyage des articles:", err);
  }
  return null;
}

export async function fetchArticles() {
  try {
    const lang = get(articleLanguageFilter);
    const fullText = get(fullTextOnlyFilter);

    let url = `/api/articles?lang=${lang}`;
    if (fullText) {
      url += `&full_text_only=true`;
    }

    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      articlesList.set(data);
    }
  } catch (err) {
    console.error("Erreur lors de la récupération des articles:", err);
  }
}

export async function fetchFeeds() {
  try {
    const res = await fetch('/api/feeds');
    if (res.ok) {
      const data = await res.json();
      feedsList.set(data);
    }
  } catch (err) {
    console.error("Erreur lors de la récupération des flux:", err);
  }
}

export async function triggerFeedRefresh() {
  isRefreshingFeeds.set(true);
  const apiKey = get(mistralApiKey);
  try {
    const res = await fetch('/api/feeds/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey })
    });
    if (res.ok) {
      setTimeout(async () => {
        await fetchArticles();
        await fetchFeeds();
        isRefreshingFeeds.set(false);
      }, 2500);
      return true;
    }
  } catch (err) {
    console.error("Erreur rafraîchissement des flux:", err);
  } finally {
    setTimeout(() => isRefreshingFeeds.set(false), 3500);
  }
  return false;
}

let autoRefreshTimer = null;
export function setupAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }

  const minutes = get(refreshIntervalMinutes);
  if (minutes > 0) {
    const ms = minutes * 60 * 1000;
    autoRefreshTimer = setInterval(() => {
      console.log(`[Auto-Refresh & Auto-Vectorize] Rafraîchissement automatique (${minutes} min)...`);
      triggerFeedRefresh();
    }, ms);
  }
}

// Auto setup timer and sync VPS keys on load
fetchVpsSettings();
setupAutoRefresh();

