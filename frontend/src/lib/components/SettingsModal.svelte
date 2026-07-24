<script>
  import { onMount } from 'svelte';
  import { showSettingsModal, mistralApiKey, selectedMistralModel, refreshIntervalMinutes, articleLanguageFilter, fullTextOnlyFilter, articleRetentionDays, saveSettings, runArticlesCleanup, fetchVpsApiKey } from '../stores/appState.js';
  import { selectedVoice, saveVoiceSetting } from '../stores/audioStore.js';

  let apiKeyInput = $mistralApiKey;
  let modelInput = $selectedMistralModel;
  let voiceInput = $selectedVoice || 'Marie - Neutral';
  let refreshInput = $refreshIntervalMinutes;
  let langInput = $articleLanguageFilter;
  let fullTextInput = $fullTextOnlyFilter;
  let retentionInput = $articleRetentionDays;

  let showPassword = false;
  let saveStatus = '';
  let envSaveStatus = '';
  let cleanupStatus = '';
  let isTesting = false;
  let isSavingEnv = false;
  let isCleaning = false;
  let testResult = null;

  onMount(async () => {
    if (!apiKeyInput) {
      const vpsKey = await fetchVpsApiKey();
      if (vpsKey) {
        apiKeyInput = vpsKey;
        envSaveStatus = '✓ Clé API chargée automatiquement depuis le serveur VPS !';
      }
    }
  });

  $: if ($showSettingsModal && !apiKeyInput) {
    fetchVpsApiKey().then(vpsKey => {
      if (vpsKey) {
        apiKeyInput = vpsKey;
        envSaveStatus = '✓ Clé API chargée automatiquement depuis le serveur VPS !';
      }
    });
  }

  function handleSave() {
    saveSettings(apiKeyInput, modelInput, refreshInput, langInput, fullTextInput, retentionInput);
    saveVoiceSetting(voiceInput);
    saveStatus = 'Paramètres enregistrés avec succès !';
    setTimeout(() => {
      saveStatus = '';
      $showSettingsModal = false;
    }, 1200);
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

  async function saveKeyToVpsEnv() {
    if (!apiKeyInput) {
      alert("Veuillez d'abord saisir une clé API.");
      return;
    }
    isSavingEnv = true;
    envSaveStatus = '';

    try {
      const res = await fetch('/api/feeds/save-env-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKeyInput })
      });
      const data = await res.json();
      if (res.ok) {
        envSaveStatus = '✓ Clé enregistrée dans le fichier .env du serveur VPS !';
        saveSettings(apiKeyInput, modelInput, refreshInput, langInput, fullTextInput, retentionInput);
      } else {
        alert(data.detail || "Erreur lors de l'enregistrement sur le serveur.");
      }
    } catch (err) {
      alert("Erreur de connexion au serveur.");
    } finally {
      isSavingEnv = false;
    }
  }

  async function testConnection() {
    if (!apiKeyInput) {
      testResult = { success: false, message: 'Veuillez saisir une clé API.' };
      return;
    }
    isTesting = true;
    testResult = null;

    try {
      const res = await fetch('https://api.mistral.ai/v1/models', {
        headers: {
          'Authorization': `Bearer ${apiKeyInput}`
        }
      });

      if (res.ok) {
        testResult = { success: true, message: 'Connexion réussie à l\'API Mistral AI !' };
      } else {
        const errorData = await res.json().catch(() => ({}));
        testResult = { success: false, message: errorData.message || 'Clé API invalide ou accès refusé.' };
      }
    } catch (err) {
      testResult = { success: false, message: 'Erreur réseau lors du test de connexion.' };
    } finally {
      isTesting = false;
    }
  }

  function closeModal() {
    $showSettingsModal = false;
  }
</script>

{#if $showSettingsModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-white dark:bg-dark-card w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-gray-800">
      
      <!-- Header -->
      <div class="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-dark-bg/50">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-primary-50 dark:bg-primary-900/50 text-primary-500 rounded-2xl">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-bold">Paramètres Globaux</h3>
            <p class="text-xs text-gray-500">API Mistral, Langues, Rétention & Voix</p>
          </div>
        </div>

        <button on:click={closeModal} class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
        
        <!-- READER LANGUAGE FILTER -->
        <div class="space-y-2">
          <label for="reader-language" class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
            🌐 Langue du fil d'articles bruts (Lecteur)
          </label>
          <select 
            id="reader-language"
            bind:value={langInput}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            <option value="fr">🇫🇷 Français uniquement (Par défaut)</option>
            <option value="en">🇬🇧 Anglais uniquement</option>
            <option value="de">🇩🇪 Allemand uniquement</option>
            <option value="es">🇪🇸 Espagnol uniquement</option>
            <option value="all">🌍 Toutes les langues (Multilingue)</option>
          </select>
        </div>

        <!-- FULL TEXT ARTICLES TOGGLE -->
        <div class="flex items-center justify-between p-3.5 bg-gray-50 dark:bg-dark-bg rounded-2xl border border-gray-200 dark:border-gray-700">
          <div>
            <span class="block text-sm font-semibold text-gray-800 dark:text-gray-200">
              📄 Articles complets uniquement
            </span>
            <span class="text-xs text-gray-400">Masquer les articles avec extraits courts</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={fullTextInput} 
            class="w-5 h-5 accent-primary-500 rounded cursor-pointer"
          />
        </div>

        <!-- ARTICLE RETENTION & PURGE OPTION -->
        <div class="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
          <div class="flex items-center justify-between">
            <label for="article-retention" class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
              🗑️ Rétention des articles (Nettoyage auto)
            </label>

            <button 
              type="button" 
              on:click={triggerCleanupNow}
              disabled={isCleaning}
              class="text-[11px] text-rose-500 hover:text-rose-600 font-bold hover:underline"
              title="Supprime immédiatement tous les articles plus anciens que la durée choisie"
            >
              {isCleaning ? 'Nettoyage...' : '🧹 Nettoyer maintenant'}
            </button>
          </div>

          <select 
            id="article-retention"
            bind:value={retentionInput}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            <option value={7}>7 jours (Recommandé - Requis pour légèreté DB)</option>
            <option value={14}>14 jours (2 semaines - Par défaut)</option>
            <option value={30}>30 jours (1 mois)</option>
            <option value={90}>90 jours (3 mois)</option>
            <option value={0}>Conserver indéfiniment (Jamais supprimer)</option>
          </select>

          {#if cleanupStatus}
            <p class="text-xs text-emerald-500 font-bold">{cleanupStatus}</p>
          {/if}
        </div>

        <!-- AUTO REFRESH FREQUENCY -->
        <div class="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
          <label for="refresh-frequency" class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
            🔄 Fréquence de mise à jour des flux RSS
          </label>
          <select 
            id="refresh-frequency"
            bind:value={refreshInput}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            <option value={15}>Toutes les 15 minutes</option>
            <option value={30}>Toutes les 30 minutes (Recommandé)</option>
            <option value={60}>Toutes les 1 heures</option>
            <option value={180}>Toutes les 3 heures</option>
            <option value={0}>Manuel uniquement</option>
          </select>
        </div>

        <!-- Mistral API Key -->
        <div class="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
          <div class="flex items-center justify-between">
            <label for="mistral-key" class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
              Clé API Mistral AI
            </label>
            
            <button 
              type="button" 
              on:click={saveKeyToVpsEnv}
              disabled={isSavingEnv}
              class="text-[11px] text-purple-600 dark:text-purple-400 hover:underline font-bold"
              title="Écrit directement la clé API dans le fichier .env de votre serveur VPS"
            >
              {isSavingEnv ? 'Sauvegarde...' : '💾 Enregistrer dans le .env du VPS'}
            </button>
          </div>

          <div class="relative">
            <input 
              id="mistral-key"
              type={showPassword ? 'text' : 'password'}
              placeholder="Ex: api_key_xxxxxxxx" 
              bind:value={apiKeyInput}
              class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 pl-4 pr-12 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none transition-all"
            />
            <button 
              type="button"
              on:click={() => showPassword = !showPassword}
              class="absolute right-3 top-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xs font-medium"
            >
              {showPassword ? 'Masquer' : 'Afficher'}
            </button>
          </div>

          {#if envSaveStatus}
            <p class="text-xs text-emerald-500 font-bold">{envSaveStatus}</p>
          {/if}
        </div>

        <!-- Model selection -->
        <div class="space-y-2">
          <label for="mistral-model" class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
            Modèle Mistral par défaut
          </label>
          <select 
            id="mistral-model"
            bind:value={modelInput}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            <option value="mistral-small-latest">Mistral Small (Rapide & Économique)</option>
            <option value="mistral-medium-latest">Mistral Medium (Équilibré)</option>
            <option value="mistral-large-latest">Mistral Large (Haute précision)</option>
          </select>
        </div>

        <!-- MISTRAL STUDIO VOICE & EMOTION SELECTION -->
        <div class="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
          <label for="podcast-voice" class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
            🎙️ Voix & Émotion par défaut (Mistral Studio)
          </label>
          <select 
            id="podcast-voice"
            bind:value={voiceInput}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            <option value="Marie - Neutral">🧘 Marie - Neutral (Calme & Posée)</option>
            <option value="Marie - Excited">⚡ Marie - Excited (Enthousiaste & Excité)</option>
            <option value="Marie - Happy">😊 Marie - Happy (Joyeuse)</option>
            <option value="Marie - Sad">💬 Marie - Sad (Triste / Grave)</option>
            <option value="Marie - Curious">🔍 Marie - Curious (Curieuse)</option>
            <option value="Marie - Angry">📢 Marie - Angry (Indignée)</option>
          </select>
        </div>

        <!-- Test feedback -->
        {#if testResult}
          <div class="p-3 rounded-xl text-xs font-medium flex items-center gap-2 {testResult.success ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400' : 'bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400'}">
            <span>{testResult.message}</span>
          </div>
        {/if}

        {#if saveStatus}
          <div class="p-3 bg-primary-50 text-primary-600 dark:bg-primary-950/40 dark:text-primary-400 rounded-xl text-xs font-medium">
            {saveStatus}
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="p-4 bg-gray-50/50 dark:bg-dark-bg/50 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between gap-3">
        <button 
          type="button" 
          on:click={testConnection}
          disabled={isTesting}
          class="px-4 py-2.5 text-xs font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-all disabled:opacity-50"
        >
          {isTesting ? 'Test...' : 'Tester la clé'}
        </button>

        <div class="flex gap-2">
          <button 
            type="button" 
            on:click={closeModal}
            class="px-4 py-2.5 text-xs font-semibold text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-xl"
          >
            Annuler
          </button>
          <button 
            type="button" 
            on:click={handleSave}
            class="px-5 py-2.5 text-xs font-semibold text-white bg-primary-500 hover:bg-primary-600 rounded-xl shadow-sm transition-all"
          >
            Enregistrer
          </button>
        </div>
      </div>

    </div>
  </div>
{/if}
