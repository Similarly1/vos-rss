<script>
  import { onMount } from 'svelte';
  import { 
    mistralApiKey, selectedMistralModel, 
    geminiApiKey, selectedGeminiModel,
    langsearchApiKey,
    selectedMistralArticleModel, selectedGeminiArticleModel,
    selectedMistralDiscoverModel, selectedGeminiDiscoverModel,
    selectedMistralPodcastModel, selectedGeminiPodcastModel,
    synthesisProvider, vectorizationProvider, synthesisFallbackProvider, vectorizationFallbackProvider, mistralEmbedModel, geminiEmbedModel,
    refreshIntervalMinutes, articleLanguageFilter, fullTextOnlyFilter, articleRetentionDays, 
    saveSettings, runArticlesCleanup, fetchVpsSettings,
    userTheme, setAppTheme, visibleNavTabs, webhookModel,
    showMediaCredentialsModal, subscribedMediaCredentialsList, hidePaywalledWithoutCookie
  } from '../stores/appState.js';
  import { selectedVoice, saveVoiceSetting } from '../stores/audioStore.js';

  let settingsMode = 'debutant'; // 'debutant' | 'expert'
  let activeTab = 'apparence'; // 'apparence' | 'api' | 'abonnements' | 'aide' | 'danger'

  let mistralKeyInput = $mistralApiKey;
  let mistralModelInput = $selectedMistralModel;
  let mistralArticleInput = $selectedMistralArticleModel;
  let mistralDiscoverInput = $selectedMistralDiscoverModel;
  let mistralPodcastInput = $selectedMistralPodcastModel;

  let geminiKeyInput = $geminiApiKey;
  let geminiModelInput = $selectedGeminiModel;
  let geminiArticleInput = $selectedGeminiArticleModel;
  let geminiDiscoverInput = $selectedGeminiDiscoverModel;
  let geminiPodcastInput = $selectedGeminiPodcastModel;
  let webhookModelInput = $webhookModel || 'mistral-large-latest';
  
  let langsearchKeyInput = $langsearchApiKey;

  let synthProvInput = $synthesisProvider;
  let vectProvInput = $vectorizationProvider;
  let synthFallbackInput = $synthesisFallbackProvider;
  let vectFallbackInput = $vectorizationFallbackProvider;
  let mistralEmbedInput = $mistralEmbedModel;
  let geminiEmbedInput = $geminiEmbedModel;

  let voiceInput = $selectedVoice || 'Marie - Neutral';
  let refreshInput = $refreshIntervalMinutes;
  let langInput = $articleLanguageFilter;
  let fullTextInput = $fullTextOnlyFilter;
  let retentionInput = $articleRetentionDays;

  let showMistralPassword = false;
  let showGeminiPassword = false;
  let showLangsearchPassword = false;
  let saveStatus = '';
  let envSaveStatus = '';
  let cleanupStatus = '';
  let isTestingMistral = false;
  let isTestingGemini = false;
  let isTestingLangsearch = false;
  let isSavingEnv = false;
  let isCleaning = false;
  let testResultMistral = null;
  let testResultGemini = null;
  let testResultLangsearch = null;

  let categoryImages = [];
  let isUploadingCategory = false;

  async function loadCategoryImages() {
    try {
      const res = await fetch('/api/settings/categories');
      if (res.ok) {
        const json = await res.json();
        categoryImages = json.data;
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function uploadCategoryImage(category, file) {
    if (!file) return;
    isUploadingCategory = true;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`/api/settings/categories/${encodeURIComponent(category)}`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        await loadCategoryImages();
      }
    } catch (e) {
      console.error(e);
    } finally {
      isUploadingCategory = false;
    }
  }

  async function resetCategoryImage(category) {
    isUploadingCategory = true;
    try {
      const res = await fetch(`/api/settings/categories/${encodeURIComponent(category)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await loadCategoryImages();
      }
    } catch (e) {
      console.error(e);
    } finally {
      isUploadingCategory = false;
    }
  }

  onMount(async () => {
    const vpsKeys = await fetchVpsSettings();
    if (vpsKeys) {
      mistralKeyInput = vpsKeys.mistral_key || '';
      geminiKeyInput = vpsKeys.gemini_key || '';
      langsearchKeyInput = vpsKeys.langsearch_key || '';
      synthProvInput = vpsKeys.synthesis_provider || 'mistral';
      vectProvInput = vpsKeys.vectorization_provider || 'mistral';
      mistralModelInput = vpsKeys.mistral_model || 'mistral-small-latest';
      geminiModelInput = vpsKeys.gemini_model || 'gemini-1.5-flash';
      mistralArticleInput = vpsKeys.mistral_article_model || 'mistral-small-latest';
      geminiArticleInput = vpsKeys.gemini_article_model || 'gemini-1.5-flash';
      mistralDiscoverInput = vpsKeys.mistral_discover_model || 'mistral-small-latest';
      geminiDiscoverInput = vpsKeys.gemini_discover_model || 'gemini-1.5-flash';
      mistralPodcastInput = vpsKeys.mistral_podcast_model || 'mistral-large-latest';
      geminiPodcastInput = vpsKeys.gemini_podcast_model || 'gemini-1.5-pro';
      webhookModelInput = vpsKeys.webhook_model || 'mistral-large-latest';
      synthFallbackInput = vpsKeys.synthesis_fallback_provider || 'gemini';
      vectFallbackInput = vpsKeys.vectorization_fallback_provider || 'gemini';
      mistralEmbedInput = vpsKeys.mistral_embed_model || 'mistral-embed';
      geminiEmbedInput = vpsKeys.gemini_embed_model || 'text-embedding-004';
      refreshInput = vpsKeys.refresh_interval_minutes || 30;
      langInput = vpsKeys.article_language || 'fr';
      fullTextInput = vpsKeys.full_text_only || false;
      retentionInput = vpsKeys.article_retention_days || 14;
    }
    loadCategoryImages();
  });

  async function handleSave() {
    isSavingEnv = true;
    saveStatus = '';
    await saveSettings(
      mistralKeyInput, mistralModelInput, 
      geminiKeyInput, geminiModelInput,
      mistralArticleInput, geminiArticleInput,
      mistralDiscoverInput, geminiDiscoverInput,
      mistralPodcastInput, geminiPodcastInput,
      webhookModelInput,
      synthProvInput, vectProvInput, synthFallbackInput, vectFallbackInput,
      mistralEmbedInput, geminiEmbedInput,
      refreshInput, langInput, fullTextInput, retentionInput,
      langsearchKeyInput
    );
    saveVoiceSetting(voiceInput);
    isSavingEnv = false;
    saveStatus = 'Paramètres synchronisés avec le serveur (.env) !';
    setTimeout(() => {
      saveStatus = '';
    }, 3000);
  }

  async function triggerCleanupNow() {
    isCleaning = true;
    cleanupStatus = '';
    const res = await runArticlesCleanup(retentionInput);
    isCleaning = false;
    if (res && res.data) {
      cleanupStatus = `✓ Nettoyage effectué ! ${res.data.deleted_articles || 0} anciens articles supprimés.`;
    } else {
      cleanupStatus = '✓ Aucun ancien article à supprimer.';
    }
  }


  async function testMistralConnection() {
    if (!mistralKeyInput) {
      testResultMistral = { success: false, message: 'Veuillez saisir une clé API Mistral.' };
      return;
    }
    isTestingMistral = true;
    testResultMistral = null;
    try {
      const res = await fetch('/api/feeds/test-mistral', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: mistralKeyInput })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        testResultMistral = { success: true, message: data.message };
      } else {
        testResultMistral = { success: false, message: data.message || 'Clé API invalide ou accès refusé.' };
      }
    } catch (err) {
      testResultMistral = { success: false, message: 'Erreur réseau lors du test.' };
    } finally {
      isTestingMistral = false;
    }
  }

  async function testGeminiConnection() {
    if (!geminiKeyInput) {
      testResultGemini = { success: false, message: 'Veuillez saisir une clé API Gemini.' };
      return;
    }
    isTestingGemini = true;
    testResultGemini = null;
    try {
      const res = await fetch('/api/feeds/test-gemini', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: geminiKeyInput })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        testResultGemini = { success: true, message: data.message };
      } else {
        testResultGemini = { success: false, message: data.message || 'Clé API invalide ou accès refusé.' };
      }
    } catch (err) {
      testResultGemini = { success: false, message: 'Erreur réseau lors du test.' };
    } finally {
      isTestingGemini = false;
    }
  }

  async function testLangsearchConnection() {
    if (!langsearchKeyInput) {
      testResultLangsearch = { success: false, message: 'Veuillez saisir une clé API LangSearch.' };
      return;
    }
    isTestingLangsearch = true;
    testResultLangsearch = null;
    try {
      const res = await fetch('/api/feeds/test-langsearch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: langsearchKeyInput })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        testResultLangsearch = { success: true, message: data.message };
      } else {
        testResultLangsearch = { success: false, message: data.message || 'Clé API invalide ou accès refusé.' };
      }
    } catch (err) {
      testResultLangsearch = { success: false, message: 'Erreur réseau lors du test.' };
    } finally {
      isTestingLangsearch = false;
    }
  }
</script>

<div class="h-full flex flex-col bg-white dark:bg-dark-card overflow-hidden">
  
  <div class="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-dark-bg/50">
    <div class="flex items-center gap-3">
      <div class="p-2.5 bg-primary-50 dark:bg-primary-900/50 text-primary-500 rounded-2xl">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
        </svg>
      </div>
      <div>
        <h2 class="text-2xl font-bold">Paramètres Globaux</h2>
        <p class="text-sm text-gray-500">Intelligence Artificielle, Modèles par Fonctionnalité & Stockage</p>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <div class="bg-gray-200 dark:bg-gray-800 rounded-xl p-1 flex items-center">
        <button on:click={() => settingsMode = 'debutant'} class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {settingsMode === 'debutant' ? 'bg-white dark:bg-dark-card text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}">Débutant</button>
        <button on:click={() => settingsMode = 'expert'} class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {settingsMode === 'expert' ? 'bg-white dark:bg-dark-card text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}">Expert</button>
      </div>
      <button 
        type="button" 
        on:click={handleSave}
        disabled={isSavingEnv}
        class="px-5 py-2.5 text-sm font-semibold text-white bg-primary-500 hover:bg-primary-600 rounded-xl shadow-sm transition-all disabled:opacity-50"
      >
        {isSavingEnv ? 'Enregistrement...' : 'Enregistrer'}
      </button>
    </div>
  </div>

  <!-- Internal Tabs -->
  <div class="px-6 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-dark-bg/50">
    <div class="flex gap-6 overflow-x-auto scrollbar-hide">
      <button on:click={() => activeTab = 'apparence'} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'apparence' ? 'border-primary-500 text-primary-500' : 'border-transparent text-gray-500 hover:text-gray-700'}">🎨 Apparence & Navigation</button>
      <button on:click={() => activeTab = 'api'} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'api' ? 'border-primary-500 text-primary-500' : 'border-transparent text-gray-500 hover:text-gray-700'}">🔑 Clés API & Modèles</button>
      <button on:click={() => activeTab = 'abonnements'} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'abonnements' ? 'border-primary-500 text-primary-500' : 'border-transparent text-gray-500 hover:text-gray-700'}">🔑 Abonnements Médias</button>
      <button on:click={() => activeTab = 'aide'} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'aide' ? 'border-primary-500 text-primary-500' : 'border-transparent text-gray-500 hover:text-gray-700'}">📖 Aide & Tutoriels</button>
      <button on:click={() => activeTab = 'danger'} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'danger' ? 'border-rose-500 text-rose-500' : 'border-transparent text-gray-500 hover:text-rose-400'}">⚠️ Zone de Danger</button>
    </div>
  </div>

  <div class="flex-1 overflow-y-auto p-6 lg:p-10 bg-gray-50 dark:bg-dark-bg">
    <div class="max-w-4xl mx-auto space-y-10">
      
      {#if saveStatus}
        <div class="p-4 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 rounded-xl font-medium shadow-sm flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
          {saveStatus}
        </div>
      {/if}

      {#if activeTab === 'apparence'}
      <!-- Section: Apparence & Navigation -->
      <section class="bg-white dark:bg-dark-card rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 dark:border-gray-800">
        <h3 class="text-lg font-bold mb-6 border-b border-gray-100 dark:border-gray-800 pb-4 text-primary-500">🎨 Apparence & Navigation</h3>
        <div class="space-y-6">
          <p class="text-sm text-gray-500">Configuration de l'interface et personnalisation des onglets.</p>
          
          <div class="bg-gray-50/70 dark:bg-dark-bg/50 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Thème de l'application</label>
            <div class="flex items-center gap-4">
              <button on:click={() => setAppTheme('light')} class="px-4 py-2 text-sm font-medium rounded-xl border {$userTheme === 'light' ? 'border-primary-500 bg-primary-50 text-primary-600' : 'border-gray-200 dark:border-gray-700'}">Clair</button>
              <button on:click={() => setAppTheme('dark')} class="px-4 py-2 text-sm font-medium rounded-xl border {$userTheme === 'dark' ? 'border-primary-500 bg-primary-50 text-primary-600' : 'border-gray-200 dark:border-gray-700'}">Sombre</button>
              <button on:click={() => setAppTheme('auto')} class="px-4 py-2 text-sm font-medium rounded-xl border {$userTheme === 'auto' ? 'border-primary-500 bg-primary-50 text-primary-600' : 'border-gray-200 dark:border-gray-700'}">Système</button>
            </div>
          </div>

          <div class="bg-gray-50/70 dark:bg-dark-bg/50 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Onglets Visibles (Menu)</label>
            <div class="grid grid-cols-2 gap-3">
              {#each [
                { id: 'podcast', label: '🎙️ Studio Podcast' },
                { id: 'perplexity', label: '⚡ Fil Perplexity' },
                { id: 'feeds', label: '📰 Flux & Articles' },
                { id: 'synthesis', label: '🧪 Synthèses IA' },
                { id: 'discover', label: '🧭 Catalogue' },
                { id: 'stats', label: '📊 Statistiques' },
                { id: 'settings', label: '⚙️ Paramètres' }
              ] as tab}
                <label class="flex items-center gap-3 p-3 bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-gray-700 cursor-pointer hover:border-primary-300 transition-colors">
                  <input type="checkbox" checked={$visibleNavTabs.includes(tab.id)} on:change={(e) => {
                    if (e.target.checked) {
                      $visibleNavTabs = [...$visibleNavTabs, tab.id];
                    } else {
                      $visibleNavTabs = $visibleNavTabs.filter(id => id !== tab.id);
                    }
                  }} class="w-4 h-4 accent-primary-500" />
                  <span class="text-sm font-semibold text-gray-800 dark:text-gray-200">{tab.label}</span>
                </label>
              {/each}
            </div>
          </div>

          <!-- Category Images Section -->
          <div class="bg-gray-50/70 dark:bg-dark-bg/50 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">🖼️ Images des Catégories (Catalogue & Synthèses)</label>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {#each categoryImages as cat (cat.category)}
                <div class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden flex flex-col">
                  <div class="h-24 w-full bg-gray-200 dark:bg-gray-800 relative">
                    <img src={cat.image_url} alt={cat.category} class="w-full h-full object-cover" />
                    {#if cat.is_custom}
                      <span class="absolute top-1 right-1 bg-primary-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded">Personnalisé</span>
                    {/if}
                  </div>
                  <div class="p-3">
                    <h5 class="text-xs font-bold text-gray-900 dark:text-white mb-2">{cat.category}</h5>
                    <div class="flex gap-2">
                      <label class="flex-1 text-center bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-[10px] font-bold py-1.5 rounded cursor-pointer transition-colors">
                        {isUploadingCategory ? '...' : 'Modifier'}
                        <input type="file" accept="image/*" class="hidden" on:change={(e) => uploadCategoryImage(cat.category, e.target.files[0])} disabled={isUploadingCategory} />
                      </label>
                      <button 
                        on:click={() => resetCategoryImage(cat.category)} 
                        disabled={!cat.is_custom || isUploadingCategory}
                        class="px-2 bg-rose-50 text-rose-500 hover:bg-rose-100 disabled:opacity-30 disabled:cursor-not-allowed rounded transition-colors text-[10px] font-bold"
                        title="Réinitialiser"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </section>
      {/if}

      {#if activeTab === 'api'}
      <!-- Section: Intelligence Artificielle & Fournisseurs -->
      <section class="bg-white dark:bg-dark-card rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 dark:border-gray-800">
        <h3 class="text-lg font-bold mb-6 border-b border-gray-100 dark:border-gray-800 pb-4 text-primary-500">🧠 Choix des Modèles IA par Fonctionnalité</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <!-- Bloc Mistral AI -->
          <div class="space-y-4">
            <h4 class="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-orange-400"></span> Mistral AI
            </h4>
            <div class="space-y-3 bg-gray-50/70 dark:bg-dark-bg/50 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
              <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400">Clé API Mistral</label>
              <div class="relative">
                <input type={showMistralPassword ? 'text' : 'password'} bind:value={mistralKeyInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 pl-4 pr-16 text-sm focus:ring-2 focus:ring-primary-500" placeholder="Ex: api_key_..."/>
                <button on:click={() => showMistralPassword = !showMistralPassword} class="absolute right-3 top-2.5 text-gray-400 text-xs">
                  {showMistralPassword ? 'Cacher' : 'Voir'}
                </button>
              </div>

              <div class="pt-2 space-y-3">
                {#if settingsMode === 'expert'}
                <div>
                  <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">📰 Résumés d'articles (Mistral)</label>
                  <select bind:value={mistralArticleInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary-500">
                    <option value="mistral-small-latest">Mistral Small (Rapide & Économique)</option>
                    <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
                    <option value="mistral-large-latest">Mistral Large (Précis & Détaillé)</option>
                    <option value="ministral-8b-latest">Ministral 8B</option>
                    <option value="codestral-latest">Codestral</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">🧭 Tuiles Découvrir & Synthèses (Mistral)</label>
                  <select bind:value={mistralDiscoverInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary-500">
                    <option value="mistral-small-latest">Mistral Small (Rapide)</option>
                    <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
                    <option value="mistral-large-latest">Mistral Large (Haute Qualité)</option>
                    <option value="ministral-8b-latest">Ministral 8B</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-semibold text-purple-600 dark:text-purple-400 mb-1 font-bold">🎙️ Studio Podcast (Mistral)</label>
                  <select bind:value={mistralPodcastInput} class="w-full bg-white dark:bg-dark-card border border-purple-300 dark:border-purple-800 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-purple-500 font-medium">
                    <option value="mistral-large-latest">Mistral Large (Recommandé - Haute Qualité Script)</option>
                    <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
                    <option value="mistral-small-latest">Mistral Small (Rapide)</option>
                    <option value="codestral-latest">Codestral</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Modèle par défaut / fallback</label>
                  <select bind:value={mistralModelInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-1.5 px-3 text-xs text-gray-600">
                    <option value="mistral-small-latest">Mistral Small</option>
                    <option value="mistral-medium-latest">Mistral Medium</option>
                    <option value="mistral-large-latest">Mistral Large</option>
                  </select>
                </div>
                {/if}
              </div>

              <button on:click={testMistralConnection} disabled={isTestingMistral} class="text-xs font-semibold px-3 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 rounded-lg w-full mt-2">
                {isTestingMistral ? 'Test en cours...' : 'Tester la connexion Mistral'}
              </button>
              {#if testResultMistral}
                <div class="text-xs font-medium mt-1 {testResultMistral.success ? 'text-emerald-500' : 'text-rose-500'}">{testResultMistral.message}</div>
              {/if}
            </div>
          </div>

          <!-- Bloc Google Gemini -->
          <div class="space-y-4">
            <h4 class="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-blue-500"></span> Google Gemini
            </h4>
            <div class="space-y-3 bg-gray-50/70 dark:bg-dark-bg/50 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
              <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400">Clé API Gemini</label>
              <div class="relative">
                <input type={showGeminiPassword ? 'text' : 'password'} bind:value={geminiKeyInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 pl-4 pr-16 text-sm focus:ring-2 focus:ring-primary-500" placeholder="Ex: AIzaSy..."/>
                <button on:click={() => showGeminiPassword = !showGeminiPassword} class="absolute right-3 top-2.5 text-gray-400 text-xs">
                  {showGeminiPassword ? 'Cacher' : 'Voir'}
                </button>
              </div>

              <div class="pt-2 space-y-3">
                {#if settingsMode === 'expert'}
                <div>
                  <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">📰 Résumés d'articles (Gemini)</label>
                  <select bind:value={geminiArticleInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary-500">
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash (Rapide)</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">🧭 Tuiles Découvrir & Synthèses (Gemini)</label>
                  <select bind:value={geminiDiscoverInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary-500">
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-semibold text-purple-600 dark:text-purple-400 mb-1 font-bold">🎙️ Studio Podcast (Gemini)</label>
                  <select bind:value={geminiPodcastInput} class="w-full bg-white dark:bg-dark-card border border-purple-300 dark:border-purple-800 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-purple-500 font-medium">
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro (Recommandé - Haute Précision)</option>
                    <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Modèle par défaut / fallback</label>
                  <select bind:value={geminiModelInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-1.5 px-3 text-xs text-gray-600">
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  </select>
                </div>
                {/if}
              </div>
            
            <div class="mt-6 bg-gray-50/70 dark:bg-dark-bg/50 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">📝 Modèle d'Extraction IA (Webhooks)</label>
              <select bind:value={webhookModelInput} class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary-500">
                <option value="mistral-large-latest">Mistral Large (Précis & Détaillé)</option>
                <option value="codestral-latest">Codestral (Performant sur le code/JSON)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Excellente Extraction)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash (Rapide)</option>
              </select>
            </div>

            <button on:click={testGeminiConnection} disabled={isTestingGemini} class="text-xs font-semibold px-3 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 rounded-lg w-full mt-2">
                {isTestingGemini ? 'Test en cours...' : 'Tester la connexion Gemini'}
              </button>
              {#if testResultGemini}
                <div class="text-xs font-medium mt-1 {testResultGemini.success ? 'text-emerald-500' : 'text-rose-500'}">{testResultGemini.message}</div>
              {/if}
            </div>
          </div>

          <!-- LANGSEARCH CARD -->
          <div class="p-6 bg-gray-50 dark:bg-dark-bg rounded-2xl border border-gray-100 dark:border-gray-800 space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xl">🔎</span>
                <div>
                  <h4 class="font-bold text-gray-900 dark:text-white text-sm">LangSearch API (Recherche de Médias Locaux)</h4>
                  <p class="text-xs text-gray-500 dark:text-gray-400">Découverte automatique de journaux et actualités régionales</p>
                </div>
              </div>
              <span class="text-xs font-semibold px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded-lg">Web Search API</span>
            </div>

            <div class="space-y-2">
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300">Clé API LangSearch</label>
              <div class="relative">
                <input 
                  type={showLangsearchPassword ? 'text' : 'password'} 
                  bind:value={langsearchKeyInput} 
                  placeholder="Saisissez votre clé API LangSearch (ex: ls_...)"
                  class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary-500 pr-10"
                />
                <button 
                  on:click={() => showLangsearchPassword = !showLangsearchPassword}
                  class="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 text-xs"
                >
                  {showLangsearchPassword ? '👁️‍🗨️' : '👁️'}
                </button>
              </div>

              <button on:click={testLangsearchConnection} disabled={isTestingLangsearch} class="text-xs font-semibold px-3 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 rounded-lg w-full mt-2">
                {isTestingLangsearch ? 'Test en cours...' : 'Tester la connexion LangSearch'}
              </button>
              {#if testResultLangsearch}
                <div class="text-xs font-medium mt-1 {testResultLangsearch.success ? 'text-emerald-500' : 'text-rose-500'}">{testResultLangsearch.message}</div>
              {/if}
            </div>
          </div>
        </div>

      </section>

      <!-- Section: Stratégie d'Utilisation -->
      <section class="bg-white dark:bg-dark-card rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 dark:border-gray-800">
        <h3 class="text-lg font-bold mb-6 border-b border-gray-100 dark:border-gray-800 pb-4 text-primary-500">⚙️ Rôles & Stratégie Multi-LLM</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-3">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Fournisseur Principal pour la Synthèse</label>
            <select bind:value={synthProvInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="mistral">Mistral AI (Recommandé)</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>

          <div class="space-y-3">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Fournisseur de Secours (Fallback) pour la Synthèse</label>
            <select bind:value={synthFallbackInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="aucun">Aucun (Désactivé)</option>
              <option value="mistral">Mistral AI</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>

          <div class="space-y-3 mt-4">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Fournisseur Principal pour la Vectorisation</label>
            <select bind:value={vectProvInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="mistral">Mistral AI</option>
              <option value="gemini">Google Gemini</option>
            </select>
            <p class="text-[10px] text-gray-500 dark:text-gray-400 font-medium mt-1">Note : Les articles sont conservés par fournisseur dans des tables séparées pour éviter la re-vectorisation totale.</p>
          </div>

          <div class="space-y-3 mt-4">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Fournisseur de Secours (Fallback) pour la Vectorisation</label>
            <select bind:value={vectFallbackInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="aucun">Aucun (Désactivé)</option>
              <option value="mistral">Mistral AI</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>
          
          <div class="space-y-3 mt-4">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Modèle d'Embedding Mistral</label>
            <select bind:value={mistralEmbedInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="mistral-embed">mistral-embed (1024 dims)</option>
            </select>
          </div>

          <div class="space-y-3 mt-4">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Modèle d'Embedding Gemini</label>
            <select bind:value={geminiEmbedInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="gemini-embedding-001">gemini-embedding-001 (Gemini Embedding v1)</option>
              <option value="gemini-embedding-002">gemini-embedding-002 (Gemini Embedding v2)</option>
              <option value="text-embedding-004">text-embedding-004 (Gecko - 768 dims)</option>
              <option value="text-embedding-005">text-embedding-005 (Gecko 005 - 768 dims)</option>
              <option value="text-multilingual-embedding-002">text-multilingual-embedding-002 (Cross-lingue)</option>
            </select>
          </div>
        </div>
      </section>
      {/if}

      {#if activeTab === 'aide'}
      <!-- Section: Aide & Tutoriels -->
      <section class="bg-white dark:bg-dark-card rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 dark:border-gray-800">
        <h3 class="text-lg font-bold mb-6 border-b border-gray-100 dark:border-gray-800 pb-4 text-primary-500">📖 Aide & Tutoriels</h3>
        <p class="text-sm text-gray-500">Guides explicatifs pour l'utilisation de la plateforme.</p>
      </section>
      {/if}

      {#if activeTab === 'abonnements'}
      <!-- Section: Abonnements Médias Payants -->
      <section class="bg-white dark:bg-dark-card rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 dark:border-gray-800">
        <div class="flex justify-between items-center mb-6 border-b border-gray-100 dark:border-gray-800 pb-4">
          <h3 class="text-lg font-bold text-primary-500">🔑 Abonnements Médias Payants</h3>
          <button on:click={() => $showMediaCredentialsModal = true} class="px-4 py-2 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 font-bold rounded-xl text-sm transition-colors">
            + Ajouter un accès
          </button>
        </div>
        
        <div class="space-y-6">
          <p class="text-sm text-gray-500">Configurez vos cookies de session pour lire l'intégralité des articles payants (Le Monde, NZZ, etc.).</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {#if $subscribedMediaCredentialsList.length === 0}
              <div class="col-span-full p-6 text-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-2xl text-gray-400 text-sm">
                🔴 Non configuré. Vous n'avez ajouté aucun cookie pour le moment.
              </div>
            {:else}
              {#each $subscribedMediaCredentialsList as media}
                <div class="p-4 bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl flex justify-between items-center">
                  <div>
                    <h4 class="font-bold text-sm">{media.name}</h4>
                    <p class="text-xs text-gray-500">{media.domain}</p>
                  </div>
                  <span class="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-lg flex items-center gap-1">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span> 100% Intégral
                  </span>
                </div>
              {/each}
            {/if}
          </div>

          <div class="mt-6 p-4 bg-gray-50 dark:bg-dark-bg rounded-2xl flex items-center justify-between border border-gray-200 dark:border-gray-700">
            <div>
              <span class="block text-sm font-semibold text-gray-800 dark:text-gray-200">Masquer automatiquement les articles payants sans abonnement</span>
              <span class="text-xs text-gray-500">N'afficher que les articles gratuits ou pour lesquels vous avez fourni un cookie.</span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" bind:checked={$hidePaywalledWithoutCookie} class="sr-only peer">
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-500"></div>
            </label>
          </div>
        </div>
      </section>
      {/if}

      {#if activeTab === 'danger'}
      <!-- Section: Préférences de Flux & Application -->
      <section class="bg-white dark:bg-dark-card rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 dark:border-gray-800">
        <h3 class="text-lg font-bold mb-6 border-b border-gray-100 dark:border-gray-800 pb-4 text-primary-500">📰 Flux, Articles & Stockage</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-3">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Langue du fil d'articles</label>
            <select bind:value={langInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="fr">🇫🇷 Français uniquement</option>
              <option value="en">🇬🇧 Anglais uniquement</option>
              <option value="all">🌍 Toutes les langues</option>
            </select>
          </div>

          <div class="space-y-3">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Fréquence d'actualisation RSS</label>
            <select bind:value={refreshInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value={15}>15 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={60}>1 heure</option>
              <option value={0}>Manuel uniquement</option>
            </select>
          </div>

          <div class="space-y-3">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Rétention des articles (Nettoyage)</label>
            <div class="flex items-center gap-2">
              <select bind:value={retentionInput} class="flex-1 bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
                <option value={7}>7 jours</option>
                <option value={14}>14 jours</option>
                <option value={30}>30 jours</option>
              </select>
              <button on:click={triggerCleanupNow} disabled={isCleaning} class="px-4 py-3 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-xl text-sm font-bold transition-colors">
                {isCleaning ? '...' : 'Purger'}
              </button>
            </div>
            {#if cleanupStatus}
              <p class="text-xs text-emerald-500 font-bold">{cleanupStatus}</p>
            {/if}
          </div>

          <div class="space-y-3">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">Voix du Studio Podcast</label>
            <select bind:value={voiceInput} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500">
              <option value="Marie - Dynamic">Auto (Changement d'intonation automatique)</option>
              <option value="Marie - Neutral">Marie - Neutral</option>
              <option value="Marie - Excited">Marie - Excited</option>
              <option value="Marie - Happy">Marie - Happy</option>
              <option value="Marie - Sad">Marie - Sad</option>
              <option value="Marie - Curious">Marie - Curious</option>
              <option value="Marie - Angry">Marie - Angry</option>
            </select>
          </div>
        </div>

        <div class="mt-6 p-4 bg-gray-50 dark:bg-dark-bg rounded-2xl flex items-center justify-between border border-gray-200 dark:border-gray-700">
          <div>
            <span class="block text-sm font-semibold text-gray-800 dark:text-gray-200">Afficher uniquement les articles complets</span>
            <span class="text-xs text-gray-500">Masquer les articles qui n'ont qu'un court extrait.</span>
          </div>
          <input type="checkbox" bind:checked={fullTextInput} class="w-5 h-5 accent-primary-500 rounded cursor-pointer" />
        </div>
      </section>
      {/if}

    </div>
  </div>
</div>
