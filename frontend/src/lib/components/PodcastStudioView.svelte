<script>
  import { onMount } from 'svelte';
  import { mistralApiKey, showSettingsModal } from '../stores/appState.js';
  import { playTrack, selectedVoice } from '../stores/audioStore.js';

  // Recipe configuration options
  let topicsCount = 5;
  let maxDays = 7;
  let onlyVerified = false;
  let tone = "journal_matinal";
  let voiceKey = $selectedVoice || "Marie - Dynamic";
  let themeInput = "";

  let isGenerating = false;
  let progressStep = "";
  let errorMsg = "";

  let currentPodcast = null;
  let podcastHistory = [];
  let showScript = false;

  // Schedule & Feed states
  let scheduleEnabled = false;
  let scheduleFrequency = "daily"; // 'daily' | 'weekdays' | 'weekly_monday' | 'weekly_friday'
  let scheduleTime = "07:00";
  let scheduleSaving = false;
  let scheduleSuccessMsg = "";
  let feedCopied = false;

  const FEED_URL = `${typeof window !== 'undefined' ? window.location.origin : ''}/api/podcast/feed.xml`;

  async function fetchHistory() {
    try {
      const res = await fetch('/api/podcast/history');
      if (res.ok) {
        const data = await res.json();
        podcastHistory = data.podcasts || [];
        if (podcastHistory.length > 0 && !currentPodcast) {
          currentPodcast = podcastHistory[0];
        }
      }
    } catch (err) {
      console.error("Erreur lors de la récupération de l'historique des podcasts:", err);
    }
  }

  async function fetchSchedule() {
    try {
      const res = await fetch('/api/podcast/schedule');
      if (res.ok) {
        const data = await res.json();
        scheduleEnabled = !!data.enabled;
        scheduleFrequency = data.frequency || "daily";
        scheduleTime = data.time || "07:00";
        if (data.topics_count) topicsCount = data.topics_count;
        if (data.max_days) maxDays = data.max_days;
        if (data.only_verified !== undefined) onlyVerified = data.only_verified;
        if (data.tone) tone = data.tone;
        if (data.voice) voiceKey = data.voice;
        if (data.theme) themeInput = data.theme;
      }
    } catch (err) {
      console.error("Erreur récupération planification:", err);
    }
  }

  async function saveSchedule() {
    scheduleSaving = true;
    scheduleSuccessMsg = "";
    try {
      const res = await fetch('/api/podcast/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: scheduleEnabled,
          frequency: scheduleFrequency,
          time: scheduleTime,
          topics_count: topicsCount,
          max_days: maxDays,
          only_verified: onlyVerified,
          tone: tone,
          voice: voiceKey,
          theme: themeInput
        })
      });
      if (res.ok) {
        scheduleSuccessMsg = "Planification matinale enregistrée ! Vos émissions automatiques utiliseront cette recette.";
        setTimeout(() => scheduleSuccessMsg = "", 4000);
      }
    } catch (err) {
      alert("Erreur lors de l'enregistrement de la planification.");
    } finally {
      scheduleSaving = false;
    }
  }

  function copyFeedUrl() {
    navigator.clipboard.writeText(FEED_URL);
    feedCopied = true;
    setTimeout(() => feedCopied = false, 2500);
  }

  async function handleGeneratePodcast() {
    if (!$mistralApiKey) {
      alert("Veuillez d'abord renseigner votre clé API Mistral dans les Paramètres (icône ⚙️).");
      $showSettingsModal = true;
      return;
    }

    isGenerating = true;
    errorMsg = "";
    progressStep = `1/3 : Sélection et filtrage des ${topicsCount} sujets${themeInput ? ` sur '${themeInput}'` : ''}...`;

    try {
      setTimeout(() => {
        if (isGenerating) progressStep = `2/3 : Rédaction du script multi-émotions par Mistral AI...`;
      }, 2500);

      setTimeout(() => {
        if (isGenerating) progressStep = `3/3 : Synthèse audio Voxtral (Enchaînement d'émotions en 1 MP3)...`;
      }, 7000);

      const res = await fetch('/api/podcast/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topics_count: topicsCount,
          max_days: maxDays,
          only_verified: onlyVerified,
          tone: tone,
          voice: voiceKey,
          theme: themeInput,
          api_key: $mistralApiKey
        })
      });

      const data = await res.json();

      if (res.ok && data.podcast) {
        currentPodcast = data.podcast;
        showScript = false;
        playTrack(currentPodcast.title, currentPodcast.audio_url, `Revue de Presse Vos (${voiceKey})`);
        await fetchHistory();
      } else {
        errorMsg = data.detail || "Échec de la génération du podcast.";
      }
    } catch (err) {
      errorMsg = "Erreur de connexion au serveur.";
    } finally {
      isGenerating = false;
      progressStep = "";
    }
  }

  function playPodcastItem(p) {
    currentPodcast = p;
    playTrack(p.title, p.audio_url, `Revue de Presse Vos (${p.voice || 'Marie'})`);
  }

  async function deletePodcastItem(pId) {
    if (!confirm("Voulez-vous supprimer cette émission de votre historique ?")) return;
    try {
      await fetch(`/api/podcast/${pId}`, { method: 'DELETE' });
      if (currentPodcast && currentPodcast.id === pId) {
        currentPodcast = null;
      }
      await fetchHistory();
    } catch (err) {
      console.error(err);
    }
  }

  onMount(() => {
    fetchHistory();
    fetchSchedule();
  });
</script>

<div class="flex-1 h-full overflow-y-auto bg-gray-950 text-gray-100 p-4 md:p-8 space-y-8">
  <div class="max-w-4xl mx-auto space-y-8">
    
    <!-- Top Header -->
    <div class="space-y-2 pt-2">
      <div class="flex items-center gap-2">
        <span class="text-xs bg-purple-950/80 text-purple-400 font-extrabold px-3 py-1 rounded-full border border-purple-800/60 uppercase tracking-wider">
          🎙️ Studio Radio Multi-Émotions
        </span>
        <span class="text-xs bg-emerald-950/80 text-emerald-400 font-extrabold px-3 py-1 rounded-full border border-emerald-800/60 uppercase tracking-wider">
          Flux AntennaPod XML
        </span>
      </div>
      <h1 class="text-3xl md:text-4xl font-black text-white tracking-tight">Revue de Presse Audio</h1>
      <p class="text-sm text-gray-400">
        Créez votre recette d'émission, lancez-la à la demande ou automatisez sa publication dans <strong class="text-emerald-400">AntennaPod</strong> avec visuels HD et sources de presse !
      </p>
    </div>

    <!-- ANTENNAPOD BANNER & COPY LINK -->
    <div class="bg-gradient-to-r from-emerald-950/40 via-gray-900 to-purple-950/40 border border-emerald-800/50 rounded-3xl p-5 md:p-6 shadow-xl space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="space-y-1 min-w-0">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <span>📡 Flux Podcast AntennaPod / Apple Podcasts / Spotify</span>
          </h2>
          <p class="text-xs text-gray-400">Copiez cette URL dans AntennaPod pour télécharger vos émissions automatiquement sur votre smartphone.</p>
        </div>

        <button 
          on:click={copyFeedUrl}
          class="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-black text-xs rounded-xl shadow-md transition-all flex items-center gap-2 shrink-0"
        >
          {#if feedCopied}
            <span>✓ URL Copiée !</span>
          {:else}
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
            <span>Copier l'URL du Flux AntennaPod</span>
          {/if}
        </button>
      </div>

      <div class="p-3 bg-gray-950/90 rounded-2xl border border-gray-800 flex items-center justify-between gap-3 text-xs font-mono text-emerald-400">
        <span class="truncate">{FEED_URL}</span>
        <span class="text-[10px] bg-emerald-950 text-emerald-300 font-sans px-2.5 py-1 rounded-full border border-emerald-800 uppercase font-bold shrink-0">
          RSS 2.0 / iTunes
        </span>
      </div>
    </div>

    <!-- CARD 1: THE PODCAST RECIPE / CONFIGURATION -->
    <div class="bg-gray-900/90 border border-gray-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      <div class="space-y-1 border-b border-gray-800 pb-3">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <span>1. Recette de votre Émission Radio (Contenu & Voix)</span>
        </h2>
        <p class="text-xs text-purple-400">Cette recette définit le contenu et le style de vos émissions, qu'elles soient générées à la demande ou automatiquement !</p>
      </div>

      <!-- KEYWORD / THEME FOCUS INPUT -->
      <div class="space-y-2">
        <label for="theme-input" class="block text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
          <span>🎯 Axer l'émission sur un thème / mot-clé précis (Optionnel)</span>
        </label>
        <div class="relative">
          <input 
            id="theme-input"
            type="text"
            placeholder="Ex: Intelligence Artificielle, Suisse, Économie, Climat..."
            bind:value={themeInput}
            class="w-full bg-gray-950 border border-purple-800/60 focus:border-purple-500 rounded-2xl py-3 pl-4 pr-10 text-xs font-semibold text-white focus:ring-2 focus:ring-purple-500 focus:outline-none transition-all placeholder:text-gray-600"
          />
          {#if themeInput}
            <button 
              on:click={() => themeInput = ''} 
              class="absolute right-3 top-3 text-gray-400 hover:text-white text-xs font-bold"
              title="Effacer le thème"
            >
              ✕
            </button>
          {/if}
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <!-- TOPICS COUNT -->
        <div class="space-y-2">
          <label for="topics-count" class="block text-xs font-bold text-gray-300 uppercase tracking-wider">
            📊 Nombre de sujets
          </label>
          <select 
            id="topics-count"
            bind:value={topicsCount}
            class="w-full bg-gray-950 border border-gray-800 rounded-2xl py-3 px-4 text-xs font-bold text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          >
            <option value={3}>3 sujets (Flash)</option>
            <option value={5}>5 sujets (Recommandé)</option>
            <option value={8}>8 sujets (Revue complète)</option>
            <option value={10}>10 sujets (Grand tour)</option>
          </select>
        </div>

        <!-- MAX DAYS / ANCIENNETÉ MAXIMAL -->
        <div class="space-y-2">
          <label for="max-days" class="block text-xs font-bold text-gray-300 uppercase tracking-wider">
            📅 Récence des articles
          </label>
          <select 
            id="max-days"
            bind:value={maxDays}
            class="w-full bg-gray-950 border border-gray-800 rounded-2xl py-3 px-4 text-xs font-bold text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          >
            <option value={1}>Dernières 24h</option>
            <option value={3}>3 derniers jours</option>
            <option value={7}>7 derniers jours (1 sem.)</option>
            <option value={14}>14 derniers jours</option>
            <option value={0}>Aucune limite de date</option>
          </select>
        </div>

        <!-- TONE / STYLE -->
        <div class="space-y-2">
          <label for="podcast-tone" class="block text-xs font-bold text-gray-300 uppercase tracking-wider">
            📻 Style de présentation
          </label>
          <select 
            id="podcast-tone"
            bind:value={tone}
            class="w-full bg-gray-950 border border-gray-800 rounded-2xl py-3 px-4 text-xs font-bold text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          >
            <option value="journal_matinal">Matinal Dynamique</option>
            <option value="decryptage">Décryptage Posé</option>
            <option value="flash_express">Flash Info Express</option>
          </select>
        </div>

        <!-- MARIE VOICE EMOTION & MULTI-VOICE SELECTION -->
        <div class="space-y-2">
          <label for="podcast-voice" class="block text-xs font-bold text-gray-300 uppercase tracking-wider">
            🎭 Voix & Multi-Émotions
          </label>
          <select 
            id="podcast-voice"
            bind:value={voiceKey}
            class="w-full bg-gray-950 border border-purple-600 rounded-2xl py-3 px-4 text-xs font-bold text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          >
            <option value="Marie - Dynamic">🎭 Marie - Dynamic Multi-Émotions (Automatique)</option>
            <option value="Marie - Neutral">🧘 Marie - Neutral (Calme & Neutre)</option>
            <option value="Marie - Excited">⚡ Marie - Excited (Enthousiaste)</option>
            <option value="Marie - Happy">😊 Marie - Happy (Joyeuse)</option>
            <option value="Marie - Sad">💬 Marie - Sad (Grave & Posée)</option>
            <option value="Marie - Curious">🔍 Marie - Curious (Curieuse)</option>
            <option value="Marie - Angry">📢 Marie - Angry (Indignée)</option>
          </select>
        </div>

      </div>

      <!-- FILTER ONLY VERIFIED SOURCES TOGGLE -->
      <div class="flex items-center justify-between p-4 bg-gray-950/60 rounded-2xl border border-gray-800">
        <div class="flex items-center gap-3">
          <span class="text-xl">🛡️</span>
          <div>
            <span class="block text-xs font-bold text-white">
              Informations Vérifiées uniquement (3+ médias distants)
            </span>
            <span class="text-[11px] text-gray-400">Ne retenir que les actualités confirmées par au moins 3 sources différentes</span>
          </div>
        </div>
        <input 
          type="checkbox" 
          bind:checked={onlyVerified}
          class="w-5 h-5 accent-purple-500 rounded cursor-pointer"
        />
      </div>

    </div>

    <!-- CARD 2: PRODUCTION MODES (IMMEDIATE vs AUTOMATED SCHEDULER) -->
    <div class="bg-gray-900/90 border border-gray-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      <div class="space-y-1 border-b border-gray-800 pb-3">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <span>2. Déclenchement : À la demande ou Automatisation (Cron)</span>
        </h2>
        <p class="text-xs text-gray-400">Choisissez de lancer votre émission sur-le-champ ou de programmer sa publication régulière dans AntennaPod.</p>
      </div>

      <!-- IMMEDIATE GENERATION BUTTON -->
      <div class="space-y-3 p-4 bg-purple-950/30 border border-purple-800/40 rounded-2xl">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-purple-300">⚡ Option A : Génération Immédiate (À la demande)</span>
          <span class="text-[10px] text-gray-400">Production en 1 clic</span>
        </div>
        
        <button 
          on:click={handleGeneratePodcast}
          disabled={isGenerating}
          class="w-full py-3.5 bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-extrabold text-sm rounded-2xl shadow-xl transition-all disabled:opacity-50 flex items-center justify-center gap-3"
        >
          {#if isGenerating}
            <svg class="w-5 h-5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <span>{progressStep || 'Génération en cours...'}</span>
          {:else}
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
            <span>Générer ma Revue Radio Maintenant {themeInput ? `(sur '${themeInput}')` : ''}</span>
          {/if}
        </button>

        {#if errorMsg}
          <p class="text-xs text-rose-400 font-medium text-center">{errorMsg}</p>
        {/if}
      </div>

      <!-- AUTOMATED SCHEDULER (CRON) CONTROLS -->
      <div class="space-y-4 p-4 bg-emerald-950/30 border border-emerald-800/40 rounded-2xl">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-emerald-300">⏰ Option B : Programmation Automatique (AntennaPod Cron)</span>
          <span class="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full font-bold">
            {scheduleEnabled ? 'ACTIVÉ' : 'DESACTIVÉ'}
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- ENABLE TOGGLE -->
          <div class="flex items-center gap-3 p-3 bg-gray-950/80 rounded-xl border border-gray-800">
            <input 
              type="checkbox" 
              bind:checked={scheduleEnabled}
              class="w-5 h-5 accent-emerald-500 rounded cursor-pointer"
            />
            <div>
              <span class="block text-xs font-bold text-white">Activer le Cron</span>
              <span class="text-[10px] text-gray-400">Publication automatique</span>
            </div>
          </div>

          <!-- FREQUENCY SELECTOR -->
          <div class="space-y-1">
            <label for="schedule-freq" class="block text-[11px] font-bold text-gray-300 uppercase">Fréquence d'émission</label>
            <select 
              id="schedule-freq"
              bind:value={scheduleFrequency}
              disabled={!scheduleEnabled}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs font-bold text-white disabled:opacity-40"
            >
              <option value="daily">📅 Quotidienne (Tous les jours)</option>
              <option value="weekdays">💼 Du Lundi au Vendredi (Jours ouvrés)</option>
              <option value="weekly_monday">🗓️ Hebdomadaire (Chaque Lundi)</option>
              <option value="weekly_friday">🎉 Hebdomadaire (Chaque Vendredi)</option>
            </select>
          </div>

          <!-- TIME SELECTOR -->
          <div class="space-y-1">
            <label for="schedule-time" class="block text-[11px] font-bold text-gray-300 uppercase">Heure de publication</label>
            <select 
              id="schedule-time"
              bind:value={scheduleTime}
              disabled={!scheduleEnabled}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs font-bold text-white disabled:opacity-40"
            >
              <option value="06:00">06h00 du matin</option>
              <option value="07:00">07h00 du matin (Recommandé)</option>
              <option value="08:00">08h00 du matin</option>
              <option value="12:00">12h00 (Édition du midi)</option>
              <option value="19:00">19h00 (Édition du soir)</option>
            </select>
          </div>

        </div>

        <button 
          on:click={saveSchedule}
          disabled={scheduleSaving}
          class="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-gray-950 font-extrabold text-xs rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
        >
          <span>{scheduleSaving ? 'Enregistrement...' : '💾 Enregistrer la Programmation Automatique'}</span>
        </button>

        {#if scheduleSuccessMsg}
          <p class="text-xs text-emerald-400 font-bold text-center animate-pulse">{scheduleSuccessMsg}</p>
        {/if}
      </div>

    </div>

    <!-- CURRENT/LATEST PODCAST DISPLAY CARD -->
    {#if currentPodcast}
      <div class="bg-gradient-to-b from-gray-900 to-gray-950 border border-purple-900/40 rounded-3xl p-6 md:p-8 space-y-6 shadow-2xl relative overflow-hidden">
        
        <!-- Background Accent Glow -->
        <div class="absolute -right-20 -top-20 w-64 h-64 bg-purple-600/10 rounded-full blur-3xl pointer-events-none"></div>

        <!-- Header info -->
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 pb-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="text-[10px] bg-purple-500/20 text-purple-400 font-bold px-2.5 py-0.5 rounded-full border border-purple-500/30">
                Émission {currentPodcast.topics_count} sujets
              </span>
              <span class="text-[10px] bg-cyan-500/20 text-cyan-400 font-bold px-2 py-0.5 rounded-full border border-cyan-500/30">
                {currentPodcast.voice || 'Marie - Dynamic'}
              </span>
              <span class="text-xs text-gray-500 font-medium">{currentPodcast.created_at}</span>
            </div>
            <h3 class="text-2xl font-black text-white">{currentPodcast.title}</h3>
          </div>

          <!-- DOWNLOAD MP3 BUTTON -->
          <a 
            href={currentPodcast.audio_url} 
            download={`revue_de_presse_${currentPodcast.id}.mp3`}
            target="_blank"
            rel="noreferrer"
            class="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-black text-xs rounded-2xl shadow-lg transition-all flex items-center gap-2 shrink-0"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            <span>Télécharger MP3</span>
          </a>
        </div>

        <!-- PLAYER & SCRIPT CONTROLS -->
        <div class="flex flex-wrap items-center justify-between gap-4 bg-gray-950 p-4 rounded-2xl border border-gray-800">
          <button 
            on:click={() => playPodcastItem(currentPodcast)}
            class="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-extrabold text-xs rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>
            <span>Écouter dans le lecteur</span>
          </button>

          <button 
            on:click={() => showScript = !showScript}
            class="text-xs font-bold text-purple-400 hover:underline flex items-center gap-1"
          >
            <span>{showScript ? 'Masquer le script radio' : 'Afficher le script radio multi-émotions'}</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
          </button>
        </div>

        <!-- TRANSCRIPT DISPLAY -->
        {#if showScript}
          <div class="bg-gray-950/80 p-5 rounded-2xl border border-gray-800/80 text-sm text-gray-300 leading-relaxed font-mono whitespace-pre-line space-y-2 max-h-96 overflow-y-auto">
            <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">Script radio produit ({currentPodcast.topics_count} sujets) :</p>
            <p>{currentPodcast.script}</p>
          </div>
        {/if}

      </div>
    {/if}

    <!-- PODCAST HISTORY LIST -->
    {#if podcastHistory.length > 0}
      <div class="space-y-4 pt-4 border-t border-gray-900">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <span>📜 Historique de vos émissions ({podcastHistory.length})</span>
        </h3>

        <div class="space-y-3">
          {#each podcastHistory as podcast}
            <div class="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 transition-all hover:border-gray-700">
              
              <div class="space-y-1 min-w-0">
                <h4 class="font-bold text-sm text-white truncate">{podcast.title}</h4>
                <p class="text-xs text-gray-500">{podcast.created_at} • {podcast.topics_count} sujets • Voix: {podcast.voice || 'Marie - Dynamic'}</p>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <button 
                  on:click={() => playPodcastItem(podcast)}
                  class="px-3.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-purple-300 font-bold text-xs rounded-xl transition-all flex items-center gap-1.5"
                >
                  <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>
                  <span>Écouter</span>
                </button>

                <a 
                  href={podcast.audio_url} 
                  download={`revue_de_presse_${podcast.id}.mp3`}
                  target="_blank"
                  rel="noreferrer"
                  class="px-3 py-1.5 bg-emerald-950/60 text-emerald-400 hover:bg-emerald-900/60 border border-emerald-800/50 font-bold text-xs rounded-xl transition-all flex items-center gap-1"
                  title="Télécharger MP3"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  <span>MP3</span>
                </a>

                <button 
                  on:click={() => deletePodcastItem(podcast.id)}
                  class="p-2 text-gray-500 hover:text-rose-400 hover:bg-rose-950/40 rounded-xl transition-all"
                  title="Supprimer"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
              </div>

            </div>
          {/each}
        </div>
      </div>
    {/if}

  </div>
</div>
