<script>
  import { onMount } from 'svelte';
  import { fade, fly, slide, scale, blur } from 'svelte/transition';
  import { 
    currentView,
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
    showMediaCredentialsModal, subscribedMediaCredentialsList, hidePaywalledWithoutCookie,
    mistralQuota, mistralQuotaUnit, geminiQuota, geminiQuotaUnit, vectorizationBatchLimit,
    transitionType, transitionDuration, setTransitionType, setTransitionDuration
  } from '../stores/appState.js';
  import { selectedVoice, saveVoiceSetting } from '../stores/audioStore.js';

  let settingsMode = 'debutant'; // 'debutant' | 'expert'
  const settingsTabOrder = ['apparence', 'api', 'webhooks', 'aide', 'danger'];
  let activeTab = 'apparence';
  let subNavDirection = 1;

  function switchTab(newTab) {
    if (newTab === activeTab) return;
    const prevIdx = settingsTabOrder.indexOf(activeTab);
    const newIdx = settingsTabOrder.indexOf(newTab);
    subNavDirection = newIdx > prevIdx ? 1 : -1;
    activeTab = newTab;
  }

  function customSubTransition(node) {
    const type = $transitionType;
    const duration = $transitionDuration;

    if (type === 'none' || duration <= 0) {
      return { duration: 0 };
    }
    if (type === 'fly') {
      return fly(node, { x: subNavDirection * 80, duration });
    }
    if (type === 'slide') {
      return slide(node, { duration });
    }
    if (type === 'scale') {
      return scale(node, { start: 0.96, duration });
    }
    if (type === 'blur') {
      return blur(node, { amount: 6, duration });
    }
    return fade(node, { duration });
  }

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

  let mistralQuotaInput = $mistralQuota;
  let mistralQuotaUnitInput = $mistralQuotaUnit;
  let geminiQuotaInput = $geminiQuota;
  let geminiQuotaUnitInput = $geminiQuotaUnit;
  let vectorizationBatchLimitInput = $vectorizationBatchLimit;

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
      mistralQuotaInput = vpsKeys.mistral_quota || 0;
      mistralQuotaUnitInput = vpsKeys.mistral_quota_unit || 'req/min';
      geminiQuotaInput = vpsKeys.gemini_quota || 0;
      geminiQuotaUnitInput = vpsKeys.gemini_quota_unit || 'req/min';
      vectorizationBatchLimitInput = vpsKeys.vectorization_batch_limit !== undefined ? vpsKeys.vectorization_batch_limit : 200;
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
      langsearchKeyInput,
      mistralQuotaInput, mistralQuotaUnitInput,
      geminiQuotaInput, geminiQuotaUnitInput,
      vectorizationBatchLimitInput
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

<div class="h-full flex flex-col bg-background text-foreground overflow-hidden w-full">
  
  <div class="p-6 border-b border-border flex justify-between items-center bg-card">
    <div class="flex items-center gap-3">
      <div class="p-2.5 bg-primary/20 text-primary rounded-2xl border border-primary/30">
        <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
        </svg>
      </div>
      <div>
        <h2 class="text-2xl font-bold text-foreground">Paramètres Globaux</h2>
        <p class="text-xs text-muted-foreground">Intelligence Artificielle, Modèles par Fonctionnalité & Stockage</p>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <div class="bg-background border border-border rounded-xl p-1 flex items-center">
        <button on:click={() => settingsMode = 'debutant'} class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {settingsMode === 'debutant' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}">Débutant</button>
        <button on:click={() => settingsMode = 'expert'} class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {settingsMode === 'expert' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}">Expert</button>
      </div>
      <button 
        type="button" 
        on:click={handleSave}
        disabled={isSavingEnv}
        class="px-5 py-2.5 text-sm font-semibold bg-primary text-primary-foreground hover:opacity-90 rounded-xl shadow-sm transition-all disabled:opacity-50"
      >
        {isSavingEnv ? 'Enregistrement...' : 'Enregistrer'}
      </button>
    </div>
  </div>

  <!-- Internal Tabs -->
  <div class="px-6 border-b border-border bg-card">
    <div class="flex gap-6 overflow-x-auto scrollbar-hide pt-2">
      <button on:click={() => switchTab('apparence')} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'apparence' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}">🎨 Apparence & Navigation</button>
      <button on:click={() => switchTab('api')} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'api' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}">🔑 Clés API & Modèles</button>
      <button on:click={() => switchTab('webhooks')} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'webhooks' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}">🔌 Webhooks & Ingestion</button>
      <button on:click={() => switchTab('aide')} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'aide' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}">📖 Aide & Tutoriels</button>
      <button on:click={() => switchTab('danger')} class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'danger' ? 'border-destructive text-destructive' : 'border-transparent text-muted-foreground hover:text-destructive'}">⚠️ Zone de Danger</button>
    </div>
  </div>

  <div class="flex-1 overflow-y-auto overflow-x-hidden p-6 lg:p-10 bg-background w-full relative">
    {#key activeTab}
      <div in:customSubTransition class="w-full space-y-10">
        
        {#if saveStatus}
          <div class="p-4 bg-primary/20 text-primary rounded-xl font-medium shadow-sm flex items-center gap-2 border border-primary/30">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            {saveStatus}
          </div>
        {/if}

      {#if activeTab === 'apparence'}
      <!-- Section: Apparence & Navigation -->
      <section class="bg-card text-card-foreground rounded-3xl p-6 md:p-8 shadow-sm border border-border">
        <h3 class="text-lg font-bold mb-6 border-b border-border pb-4 text-primary">🎨 Apparence & Navigation</h3>
        <div class="space-y-6">
          <p class="text-xs text-muted-foreground">Configuration de l'interface et personnalisation des onglets.</p>
          
          <div class="bg-background p-5 rounded-2xl border border-border space-y-3">
            <label class="block text-sm font-bold text-foreground">Thème de l'application</label>
            <div class="flex items-center gap-4">
              <button on:click={() => setAppTheme('light')} class="px-4 py-2 text-xs font-semibold rounded-xl border {$userTheme === 'light' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card text-foreground'}">Clair</button>
              <button on:click={() => setAppTheme('dark')} class="px-4 py-2 text-xs font-semibold rounded-xl border {$userTheme === 'dark' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card text-foreground'}">Sombre</button>
              <button on:click={() => setAppTheme('auto')} class="px-4 py-2 text-xs font-semibold rounded-xl border {$userTheme === 'auto' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card text-foreground'}">Système</button>
            </div>
          </div>

          <!-- Transitions & Animations Settings (LocalStorage) -->
          <div class="bg-background p-5 rounded-2xl border border-border space-y-5">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <label class="block text-sm font-bold text-foreground">✨ Transitions & Animations de Navigation</label>
                <p class="text-xs text-muted-foreground mt-0.5">Personnalisez le style et la vitesse des effets de transition lors du changement d'onglet.</p>
              </div>
              <span class="text-[10px] font-bold px-2.5 py-1 bg-primary/20 text-primary border border-primary/30 rounded-full w-fit">
                💾 Stockage Local (localStorage)
              </span>
            </div>

            <!-- Type Selector -->
            <div class="space-y-2">
              <label class="block text-xs font-bold text-foreground">Type de Transition :</label>
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                {#each [
                  { id: 'fade', label: 'Fondu (Fade)', icon: '🌫️' },
                  { id: 'fly', label: 'Glissement (Fly)', icon: '🚀' },
                  { id: 'slide', label: 'Déroulement', icon: '📜' },
                  { id: 'scale', label: 'Zoom (Scale)', icon: '🔍' },
                  { id: 'blur', label: 'Flou (Blur)', icon: '✨' },
                  { id: 'none', label: 'Désactivé', icon: '⚡' }
                ] as t}
                  <button 
                    type="button"
                    on:click={() => setTransitionType(t.id)} 
                    class="p-2.5 text-center rounded-xl border text-xs font-bold transition-all flex flex-col items-center gap-1 cursor-pointer {$transitionType === t.id ? 'border-primary bg-primary text-primary-foreground shadow-sm' : 'border-border bg-card text-foreground hover:border-primary/50'}"
                  >
                    <span class="text-base">{t.icon}</span>
                    <span class="truncate w-full">{t.label}</span>
                  </button>
                {/each}
              </div>
            </div>

            <!-- Duration Slider & Presets -->
            <div class="space-y-3 pt-3 border-t border-border">
              <div class="flex items-center justify-between">
                <label class="block text-xs font-bold text-foreground">Longueur / Durée de la transition :</label>
                <span class="text-xs font-mono font-bold px-2.5 py-1 bg-card border border-border text-primary rounded-lg">
                  {$transitionDuration} ms
                </span>
              </div>

              <div class="flex items-center gap-4">
                <input 
                  type="range" 
                  min="0" 
                  max="1000" 
                  step="50"
                  value={$transitionDuration} 
                  on:input={(e) => setTransitionDuration(e.target.value)}
                  class="flex-1 accent-primary cursor-pointer h-2 bg-card rounded-lg border border-border"
                />
              </div>

              <!-- Presets -->
              <div class="flex items-center gap-2 flex-wrap pt-1">
                <span class="text-[11px] font-semibold text-muted-foreground">Raccourcis :</span>
                {#each [
                  { label: 'Instant (0ms)', val: 0 },
                  { label: 'Très rapide (100ms)', val: 100 },
                  { label: 'Normal (150ms)', val: 150 },
                  { label: 'Fluide (300ms)', val: 300 },
                  { label: 'Lente (500ms)', val: 500 }
                ] as preset}
                  <button 
                    type="button"
                    on:click={() => setTransitionDuration(preset.val)}
                    class="px-2.5 py-1 text-[11px] font-bold rounded-lg border transition-all {$transitionDuration === preset.val ? 'bg-primary text-primary-foreground border-primary' : 'bg-card border-border text-muted-foreground hover:text-foreground'}"
                  >
                    {preset.label}
                  </button>
                {/each}
              </div>
            </div>
          </div>

          <div class="bg-background p-5 rounded-2xl border border-border space-y-3">
            <label class="block text-sm font-bold text-foreground">📖 Préférences de Lecture & Filtres</label>
            <label class="flex items-center gap-3 p-4 bg-card text-card-foreground rounded-xl border border-border cursor-pointer hover:border-primary/50 transition-colors">
              <input 
                type="checkbox" 
                bind:checked={$hidePaywalledWithoutCookie} 
                on:change={handleSave}
                class="w-5 h-5 accent-primary rounded" 
              />
              <div>
                <span class="text-sm font-bold text-foreground">Masquer les contenus payants / tronqués</span>
                <p class="text-xs text-muted-foreground mt-0.5">Filtre automatiquement les extraits d'articles payants si vous ne possédez pas d'abonnement actif dans Vos.</p>
              </div>
            </label>
          </div>

          <div class="bg-background p-5 rounded-2xl border border-border space-y-3">
            <label class="block text-sm font-bold text-foreground">Onglets Visibles (Menu)</label>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {#each [
                { id: 'podcast', label: '🎙️ Studio Podcast' },
                { id: 'perplexity', label: '⚡ Fil Perplexity' },
                { id: 'feeds', label: '📰 Flux & Articles' },
                { id: 'webhooks', label: '🔌 Webhooks' },
                { id: 'synthesis', label: '🧪 Synthèses IA' },
                { id: 'discover', label: '🧭 Catalogue' },
                { id: 'stats', label: '📊 Statistiques' },
                { id: 'settings', label: '⚙️ Paramètres' }
              ] as tab}
                <label class="flex items-center gap-3 p-3.5 bg-card text-card-foreground rounded-xl border border-border cursor-pointer hover:border-primary/50 transition-colors">
                  <input type="checkbox" checked={$visibleNavTabs.includes(tab.id)} on:change={(e) => {
                    if (e.target.checked) {
                      $visibleNavTabs = [...$visibleNavTabs, tab.id];
                    } else {
                      $visibleNavTabs = $visibleNavTabs.filter(id => id !== tab.id);
                    }
                  }} class="w-4 h-4 accent-primary" />
                  <span class="text-xs font-bold text-foreground">{tab.label}</span>
                </label>
              {/each}
            </div>
          </div>

          <!-- Category Images Section -->
          <div class="bg-background p-5 rounded-2xl border border-border space-y-3">
            <label class="block text-sm font-bold text-foreground">🖼️ Images des Catégories (Catalogue & Synthèses)</label>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {#each categoryImages as cat (cat.category)}
                <div class="bg-card text-card-foreground border border-border rounded-xl overflow-hidden flex flex-col">
                  <div class="h-24 w-full bg-background relative">
                    <img src={cat.image_url} alt={cat.category} class="w-full h-full object-cover" />
                    {#if cat.is_custom}
                      <span class="absolute top-1 right-1 bg-primary text-primary-foreground text-[9px] font-bold px-1.5 py-0.5 rounded">Personnalisé</span>
                    {/if}
                  </div>
                  <div class="p-3">
                    <h5 class="text-xs font-bold text-foreground mb-2">{cat.category}</h5>
                    <div class="flex gap-2">
                      <label class="flex-1 text-center bg-background hover:bg-accent text-foreground text-[10px] font-bold py-1.5 rounded border border-border cursor-pointer transition-colors">
                        {isUploadingCategory ? '...' : 'Modifier'}
                        <input type="file" accept="image/*" class="hidden" on:change={(e) => uploadCategoryImage(cat.category, e.target.files[0])} disabled={isUploadingCategory} />
                      </label>
                      <button 
                        on:click={() => resetCategoryImage(cat.category)} 
                        disabled={!cat.is_custom || isUploadingCategory}
                        class="px-2 bg-destructive/10 text-destructive hover:bg-destructive/20 disabled:opacity-30 disabled:cursor-not-allowed rounded transition-colors text-[10px] font-bold"
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
      <section class="bg-card text-card-foreground rounded-3xl p-6 md:p-8 shadow-sm border border-border">
        <h3 class="text-lg font-bold mb-6 border-b border-border pb-4 text-primary">🧠 Choix des Modèles IA par Fonctionnalité</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <!-- Bloc Mistral AI -->
          <div class="space-y-4">
            <h4 class="font-bold text-foreground flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-primary"></span> Mistral AI
            </h4>
            <div class="space-y-3 bg-background p-5 rounded-2xl border border-border">
              <label class="block text-xs font-bold text-foreground">Clé API Mistral</label>
              <div class="relative">
                <input type={showMistralPassword ? 'text' : 'password'} bind:value={mistralKeyInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2.5 pl-4 pr-16 text-xs text-foreground focus:ring-2 focus:ring-primary" placeholder="Ex: api_key_..."/>
                <button on:click={() => showMistralPassword = !showMistralPassword} class="absolute right-3 top-2.5 text-muted-foreground text-xs font-bold">
                  {showMistralPassword ? 'Cacher' : 'Voir'}
                </button>
              </div>

              <div class="pt-2 space-y-3">
                {#if settingsMode === 'expert'}
                <div>
                  <label class="block text-xs font-bold text-foreground mb-1">📰 Résumés d'articles (Mistral)</label>
                  <select bind:value={mistralArticleInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary">
                    <option value="mistral-small-latest">Mistral Small (Rapide & Économique)</option>
                    <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
                    <option value="mistral-large-latest">Mistral Large (Précis & Détaillé)</option>
                    <option value="ministral-8b-latest">Ministral 8B</option>
                    <option value="codestral-latest">Codestral</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-bold text-foreground mb-1">🧭 Tuiles Découvrir & Synthèses (Mistral)</label>
                  <select bind:value={mistralDiscoverInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary">
                    <option value="mistral-small-latest">Mistral Small (Rapide)</option>
                    <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
                    <option value="mistral-large-latest">Mistral Large (Haute Qualité)</option>
                    <option value="ministral-8b-latest">Ministral 8B</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-bold text-primary mb-1">🎙️ Studio Podcast (Mistral)</label>
                  <select bind:value={mistralPodcastInput} class="w-full bg-card text-card-foreground border border-primary/50 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary font-medium">
                    <option value="mistral-large-latest">Mistral Large (Recommandé - Haute Qualité Script)</option>
                    <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
                    <option value="mistral-small-latest">Mistral Small (Rapide)</option>
                    <option value="codestral-latest">Codestral</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-bold text-muted-foreground mb-1">Modèle par défaut / fallback</label>
                  <select bind:value={mistralModelInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-1.5 px-3 text-xs">
                    <option value="mistral-small-latest">Mistral Small</option>
                    <option value="mistral-medium-latest">Mistral Medium</option>
                    <option value="mistral-large-latest">Mistral Large</option>
                  </select>
                </div>
                {/if}
              </div>

              <button on:click={testMistralConnection} disabled={isTestingMistral} class="text-xs font-bold px-3 py-2 bg-card border border-border hover:bg-accent text-foreground rounded-xl w-full mt-2">
                {isTestingMistral ? 'Test en cours...' : 'Tester la connexion Mistral'}
              </button>
              {#if testResultMistral}
                <div class="text-xs font-bold mt-1 {testResultMistral.success ? 'text-primary' : 'text-destructive'}">{testResultMistral.message}</div>
              {/if}
            </div>
          </div>

          <!-- Bloc Google Gemini -->
          <div class="space-y-4">
            <h4 class="font-bold text-foreground flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-primary"></span> Google Gemini
            </h4>
            <div class="space-y-3 bg-background p-5 rounded-2xl border border-border">
              <label class="block text-xs font-bold text-foreground">Clé API Gemini</label>
              <div class="relative">
                <input type={showGeminiPassword ? 'text' : 'password'} bind:value={geminiKeyInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2.5 pl-4 pr-16 text-xs text-foreground focus:ring-2 focus:ring-primary" placeholder="Ex: AIzaSy..."/>
                <button on:click={() => showGeminiPassword = !showGeminiPassword} class="absolute right-3 top-2.5 text-muted-foreground text-xs font-bold">
                  {showGeminiPassword ? 'Cacher' : 'Voir'}
                </button>
              </div>

              <div class="pt-2 space-y-3">
                {#if settingsMode === 'expert'}
                <div>
                  <label class="block text-xs font-bold text-foreground mb-1">📰 Résumés d'articles (Gemini)</label>
                  <select bind:value={geminiArticleInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary">
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash (Rapide)</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-bold text-foreground mb-1">🧭 Tuiles Découvrir & Synthèses (Gemini)</label>
                  <select bind:value={geminiDiscoverInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary">
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-bold text-primary mb-1">🎙️ Studio Podcast (Gemini)</label>
                  <select bind:value={geminiPodcastInput} class="w-full bg-card text-card-foreground border border-primary/50 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-primary font-medium">
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro (Recommandé - Haute Précision)</option>
                    <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </select>
                </div>

                <div>
                  <label class="block text-xs font-bold text-muted-foreground mb-1">Modèle par défaut / fallback</label>
                  <select bind:value={geminiModelInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-1.5 px-3 text-xs">
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  </select>
                </div>
                {/if}
              </div>
            
              <div class="mt-4 p-4 bg-card rounded-2xl border border-border">
                <label class="block text-xs font-bold text-foreground mb-1">📝 Modèle d'Extraction IA (Webhooks)</label>
                <select bind:value={webhookModelInput} class="w-full bg-background border border-border rounded-xl py-2 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary">
                  <option value="mistral-large-latest">Mistral Large (Précis & Détaillé)</option>
                  <option value="codestral-latest">Codestral (Performant sur le code/JSON)</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro (Excellente Extraction)</option>
                  <option value="gemini-1.5-flash">Gemini 1.5 Flash (Rapide)</option>
                </select>
              </div>

              <button on:click={testGeminiConnection} disabled={isTestingGemini} class="text-xs font-bold px-3 py-2 bg-card border border-border hover:bg-accent text-foreground rounded-xl w-full mt-2">
                {isTestingGemini ? 'Test en cours...' : 'Tester la connexion Gemini'}
              </button>
              {#if testResultGemini}
                <div class="text-xs font-bold mt-1 {testResultGemini.success ? 'text-primary' : 'text-destructive'}">{testResultGemini.message}</div>
              {/if}
            </div>
          </div>

          <!-- LANGSEARCH CARD -->
          <div class="p-6 bg-background rounded-2xl border border-border space-y-4 md:col-span-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xl">🔎</span>
                <div>
                  <h4 class="font-bold text-foreground text-sm">LangSearch API (Recherche de Médias Locaux)</h4>
                  <p class="text-xs text-muted-foreground">Découverte automatique de journaux et actualités régionales</p>
                </div>
              </div>
              <span class="text-xs font-bold px-3 py-1 bg-primary text-primary-foreground rounded-lg">Web Search API</span>
            </div>

            <div class="space-y-2">
              <label class="block text-xs font-bold text-foreground">Clé API LangSearch</label>
              <div class="relative">
                <input 
                  type={showLangsearchPassword ? 'text' : 'password'} 
                  bind:value={langsearchKeyInput} 
                  placeholder="Saisissez votre clé API LangSearch (ex: ls_...)"
                  class="w-full bg-card text-card-foreground border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary pr-10"
                />
                <button 
                  on:click={() => showLangsearchPassword = !showLangsearchPassword}
                  class="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground text-xs font-bold"
                >
                  {showLangsearchPassword ? '👁️‍🗨️' : '👁️'}
                </button>
              </div>

              <button on:click={testLangsearchConnection} disabled={isTestingLangsearch} class="text-xs font-bold px-3 py-2 bg-card border border-border hover:bg-accent text-foreground rounded-xl w-full mt-2">
                {isTestingLangsearch ? 'Test en cours...' : 'Tester la connexion LangSearch'}
              </button>
              {#if testResultLangsearch}
                <div class="text-xs font-bold mt-1 {testResultLangsearch.success ? 'text-primary' : 'text-destructive'}">{testResultLangsearch.message}</div>
              {/if}
            </div>
          </div>
        </div>
        
        <h3 class="text-lg font-bold mt-10 mb-6 border-b border-border pb-4 text-primary">⚡ Limites & Cadencement API</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-4">
            <h4 class="font-bold text-foreground">Limites Mistral</h4>
            <div class="space-y-3 bg-background p-5 rounded-2xl border border-border">
              <label class="block text-xs font-bold text-foreground">Quota (0 = illimité)</label>
              <div class="flex gap-2">
                <input type="number" bind:value={mistralQuotaInput} class="flex-1 bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary" min="0" />
                <select bind:value={mistralQuotaUnitInput} class="w-32 bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary">
                  <option value="req/sec">req/sec</option>
                  <option value="req/min">req/min</option>
                </select>
              </div>
            </div>
          </div>
          <div class="space-y-4">
            <h4 class="font-bold text-foreground">Limites Gemini</h4>
            <div class="space-y-3 bg-background p-5 rounded-2xl border border-border">
              <label class="block text-xs font-bold text-foreground">Quota (0 = illimité)</label>
              <div class="flex gap-2">
                <input type="number" bind:value={geminiQuotaInput} class="flex-1 bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary" min="0" />
                <select bind:value={geminiQuotaUnitInput} class="w-32 bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary">
                  <option value="req/sec">req/sec</option>
                  <option value="req/min">req/min</option>
                </select>
              </div>
            </div>
          </div>
          <div class="space-y-4 md:col-span-2">
            <h4 class="font-bold text-foreground">Vectorisation</h4>
            <div class="space-y-3 bg-background p-5 rounded-2xl border border-border">
              <label class="block text-xs font-bold text-foreground">Nombre d'articles récents à vectoriser par lot</label>
              <input type="number" bind:value={vectorizationBatchLimitInput} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary" min="1" />
            </div>
          </div>
        </div>

      </section>
      {/if}

      {#if activeTab === 'api'}
      <!-- Section: Stratégie d'Utilisation -->
      <section class="bg-card text-card-foreground rounded-3xl p-6 md:p-8 shadow-sm border border-border">
        <h3 class="text-lg font-bold mb-6 border-b border-border pb-4 text-primary">⚙️ Rôles & Stratégie Multi-LLM</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-3">
            <label class="block text-xs font-bold text-foreground">Fournisseur Principal pour la Synthèse</label>
            <select bind:value={synthProvInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value="mistral">Mistral AI (Recommandé)</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>

          <div class="space-y-3">
            <label class="block text-xs font-bold text-foreground">Fournisseur de Secours (Fallback) pour la Synthèse</label>
            <select bind:value={synthFallbackInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value="aucun">Aucun (Désactivé)</option>
              <option value="mistral">Mistral AI</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>

          <div class="space-y-3 mt-4">
            <label class="block text-xs font-bold text-foreground">Fournisseur Principal pour la Vectorisation</label>
            <select bind:value={vectProvInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value="mistral">Mistral AI</option>
              <option value="gemini">Google Gemini</option>
            </select>
            <p class="text-[10px] text-muted-foreground font-medium mt-1">Note : Les articles sont conservés par fournisseur dans des tables séparées pour éviter la re-vectorisation totale.</p>
          </div>

          <div class="space-y-3 mt-4">
            <label class="block text-xs font-bold text-foreground">Fournisseur de Secours (Fallback) pour la Vectorisation</label>
            <select bind:value={vectFallbackInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value="aucun">Aucun (Désactivé)</option>
              <option value="mistral">Mistral AI</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>
          
          <div class="space-y-3 mt-4">
            <label class="block text-xs font-bold text-foreground">Modèle d'Embedding Mistral</label>
            <select bind:value={mistralEmbedInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value="mistral-embed">mistral-embed (1024 dims)</option>
            </select>
          </div>

          <div class="space-y-3 mt-4">
            <label class="block text-xs font-bold text-foreground">Modèle d'Embedding Gemini</label>
            <select bind:value={geminiEmbedInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
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

      {#if activeTab === 'webhooks'}
      <!-- Section: Webhooks & Ingestion Universelle -->
      <section class="bg-card text-card-foreground rounded-3xl p-6 md:p-8 shadow-sm border border-border space-y-6">
        <div class="flex justify-between items-center border-b border-border pb-4">
          <div>
            <h3 class="text-lg font-bold text-primary">🔌 Webhooks & Ingestion Universelle</h3>
            <p class="text-xs text-muted-foreground mt-1">Port d'entrée HTTP unique pour newsletters, Make, n8n, Mailhooks et contenus externes.</p>
          </div>
          <button on:click={() => $currentView = 'webhooks'} class="px-5 py-2.5 bg-primary text-primary-foreground font-bold rounded-xl text-xs shadow-md transition-all">
            🚀 Ouvrir l'Assistant Webhook
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-5 bg-background border border-border rounded-2xl space-y-2">
            <span class="text-2xl">📧</span>
            <h4 class="font-bold text-sm text-foreground">Mailhooks & Newsletters</h4>
            <p class="text-xs text-muted-foreground">Ingérez automatiquement vos emails d'abonnés et newsletters via Mailhooks.dev ou Zapier sans aucun scraping HTML.</p>
          </div>

          <div class="p-5 bg-background border border-border rounded-2xl space-y-2">
            <span class="text-2xl">🌐</span>
            <h4 class="font-bold text-sm text-foreground">Scraping & Autre (Clic & Valide)</h4>
            <p class="text-xs text-muted-foreground">Pour les pages HTML brutes, l'assistant découpe visuellement les blocs et enregistre les sélecteurs sans code.</p>
          </div>
        </div>
      </section>
      {/if}

      {#if activeTab === 'danger'}
      <!-- Section: Préférences de Flux & Application -->
      <section class="bg-card text-card-foreground rounded-3xl p-6 md:p-8 shadow-sm border border-border">
        <h3 class="text-lg font-bold mb-6 border-b border-border pb-4 text-primary">📰 Flux, Articles & Stockage</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-3">
            <label class="block text-xs font-bold text-foreground">Langue du fil d'articles</label>
            <select bind:value={langInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value="fr">🇫🇷 Français uniquement</option>
              <option value="en">🇬🇧 Anglais uniquement</option>
              <option value="all">🌍 Toutes les langues</option>
            </select>
          </div>

          <div class="space-y-3">
            <label class="block text-xs font-bold text-foreground">Fréquence d'actualisation RSS</label>
            <select bind:value={refreshInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
              <option value={15}>15 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={60}>1 heure</option>
              <option value={0}>Manuel uniquement</option>
            </select>
          </div>

          <div class="space-y-3">
            <label class="block text-xs font-bold text-foreground">Rétention des articles (Nettoyage)</label>
            <div class="flex items-center gap-2">
              <select bind:value={retentionInput} class="flex-1 bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
                <option value={7}>7 jours</option>
                <option value={14}>14 jours</option>
                <option value={30}>30 jours</option>
              </select>
              <button on:click={triggerCleanupNow} disabled={isCleaning} class="px-4 py-2.5 bg-destructive/10 text-destructive hover:bg-destructive/20 border border-destructive/30 rounded-xl text-xs font-bold transition-colors">
                {isCleaning ? '...' : 'Purger'}
              </button>
            </div>
            {#if cleanupStatus}
              <p class="text-xs text-primary font-bold">{cleanupStatus}</p>
            {/if}
          </div>

          <div class="space-y-3">
            <label class="block text-xs font-bold text-foreground">Voix du Studio Podcast</label>
            <select bind:value={voiceInput} class="w-full bg-background border border-border rounded-xl py-2.5 px-4 text-xs text-foreground focus:ring-2 focus:ring-primary">
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

        <div class="mt-6 p-4 bg-background rounded-2xl flex items-center justify-between border border-border">
          <div>
            <span class="block text-sm font-bold text-foreground">Afficher uniquement les articles complets</span>
            <span class="text-xs text-muted-foreground">Masquer les articles qui n'ont qu'un court extrait.</span>
          </div>
          <input type="checkbox" bind:checked={fullTextInput} class="w-5 h-5 accent-primary rounded cursor-pointer" />
        </div>
      </section>
      {/if}
      </div>
    {/key}
  </div>
</div>
