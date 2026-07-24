<script>
  import { onMount } from 'svelte';
  import { mistralApiKey, showSettingsModal } from '../stores/appState.js';
  import { playTrack, selectedVoice } from '../stores/audioStore.js';

  // Recipe configuration options (for immediate generation)
  let topicsCount = 5;
  let maxDays = 7;
  let onlyVerified = false;
  let tone = "journal_matinal";
  let voiceKey = $selectedVoice || "Marie - Neutral";
  let themeInput = "";

  let isGenerating = false;
  let progressStep = "";
  let errorMsg = "";

  let currentPodcast = null;
  let podcastHistory = [];
  let showScript = false;

  // Schedules Dashboard states
  let schedulesList = [];
  let isFetchingSchedules = false;
  let showProgramModal = false;
  let editingProgramId = null;

  // Modal form inputs
  let formName = "Matinale Quotidienne";
  let formTime = "07:00";
  let formFrequency = "daily";
  let formTone = "journal_matinal";
  let formVoice = "Marie - Neutral";
  let formTheme = "";
  let formTopicsCount = 5;
  let formMaxDays = 7;
  let formOnlyVerified = true;
  let formSaving = false;

  let feedCopied = false;
  let feedToken = "";
  let runMessageMap = {};

  $: feedUrl = `${typeof window !== 'undefined' ? window.location.origin : ''}/api/podcast/feed.xml${feedToken ? `?token=${feedToken}` : ''}`;

  async function fetchFeedToken() {
    try {
      const res = await fetch('/api/podcast/feed-token');
      if (res.ok) {
        const data = await res.json();
        feedToken = data.token || "";
      }
    } catch (err) {
      console.error("Erreur récupération token RSS:", err);
    }
  }

  async function regenerateToken() {
    if (!confirm("Voulez-vous vraiment régénérer la clé secrète du flux RSS ? L'ancienne URL configurée dans AntennaPod ne fonctionnera plus.")) return;
    try {
      const res = await fetch('/api/podcast/feed-token/regenerate', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        feedToken = data.token || "";
        alert("Clé secrète régénérée avec succès ! Pensez à mettre à jour l'URL dans votre application AntennaPod.");
      }
    } catch (err) {
      alert("Erreur lors de la régénération du token RSS.");
    }
  }

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

  async function fetchSchedules() {
    isFetchingSchedules = true;
    try {
      const res = await fetch('/api/podcast/schedules');
      if (res.ok) {
        const data = await res.json();
        schedulesList = data.schedules || [];
      }
    } catch (err) {
      console.error("Erreur récupération programmations:", err);
    } finally {
      isFetchingSchedules = false;
    }
  }

  function openCreateModal() {
    editingProgramId = null;
    formName = "Nouveau Flash Info";
    formTime = "12:30";
    formFrequency = "daily";
    formTone = "journal_matinal";
    formVoice = "Marie - Neutral";
    formTheme = "";
    formTopicsCount = 5;
    formMaxDays = 7;
    formOnlyVerified = true;
    showProgramModal = true;
  }

  function openEditModal(prog) {
    editingProgramId = prog.id;
    formName = prog.name || "Programme Radio";
    formTime = prog.time || "07:00";
    formFrequency = prog.frequency || "daily";
    formTone = prog.tone || "journal_matinal";
    formVoice = prog.voice || "Marie - Neutral";
    formTheme = prog.theme || "";
    formTopicsCount = prog.topics_count || 5;
    formMaxDays = prog.max_days || 7;
    formOnlyVerified = !!prog.only_verified;
    showProgramModal = true;
  }

  async function handleSaveProgram() {
    formSaving = true;
    try {
      const payload = {
        name: formName,
        time: formTime,
        frequency: formFrequency,
        tone: formTone,
        voice: formVoice,
        theme: formTheme,
        topics_count: formTopicsCount,
        max_days: formMaxDays,
        only_verified: formOnlyVerified,
        enabled: true
      };

      let res;
      if (editingProgramId) {
        res = await fetch(`/api/podcast/schedules/${editingProgramId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch('/api/podcast/schedules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (res.ok) {
        showProgramModal = false;
        await fetchSchedules();
      } else {
        alert("Erreur lors de l'enregistrement du programme.");
      }
    } catch (err) {
      alert("Erreur de connexion.");
    } finally {
      formSaving = false;
    }
  }

  async function toggleProgram(progId) {
    try {
      const res = await fetch(`/api/podcast/schedules/${progId}/toggle`, { method: 'POST' });
      if (res.ok) {
        await fetchSchedules();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteProgram(progId, progName) {
    if (!confirm(`Voulez-vous vraiment supprimer le programme '${progName}' ?`)) return;
    try {
      const res = await fetch(`/api/podcast/schedules/${progId}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchSchedules();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function runProgramNow(progId, progName) {
    runMessageMap[progId] = "Lancement...";
    runMessageMap = { ...runMessageMap };
    try {
      const res = await fetch(`/api/podcast/schedules/${progId}/run`, { method: 'POST' });
      if (res.ok) {
        runMessageMap[progId] = "✓ Émission lancée !";
        runMessageMap = { ...runMessageMap };
        setTimeout(() => {
          runMessageMap[progId] = null;
          runMessageMap = { ...runMessageMap };
          fetchHistory();
        }, 4000);
      }
    } catch (err) {
      runMessageMap[progId] = "Erreur";
      runMessageMap = { ...runMessageMap };
    }
  }

  function copyFeedUrl() {
    navigator.clipboard.writeText(feedUrl);
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
    progressStep = `1/3 : Sélection des ${topicsCount} sujets${themeInput ? ` sur '${themeInput}'` : ''}...`;

    try {
      setTimeout(() => {
        if (isGenerating) progressStep = `2/3 : Rédaction du script multi-émotions par Mistral AI...`;
      }, 2500);

      setTimeout(() => {
        if (isGenerating) progressStep = `3/3 : Synthèse audio Voxtral (MP3)...`;
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
    fetchSchedules();
    fetchFeedToken();
  });
</script>

<div class="flex-1 h-full overflow-y-auto bg-gray-950 text-gray-100 p-4 md:p-8 space-y-8">
  <div class="max-w-4xl mx-auto space-y-8">
    
    <!-- Top Header -->
    <div class="space-y-2 pt-2">
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs bg-purple-950/80 text-purple-400 font-extrabold px-3 py-1 rounded-full border border-purple-800/60 uppercase tracking-wider">
          🎙️ Studio Radio Multi-Émotions
        </span>
        <span class="text-xs bg-emerald-950/80 text-emerald-400 font-extrabold px-3 py-1 rounded-full border border-emerald-800/60 uppercase tracking-wider">
          Flux AntennaPod XML (Sécurisé)
        </span>
      </div>
      <h1 class="text-3xl md:text-4xl font-black text-white tracking-tight">Revue de Presse Audio</h1>
      <p class="text-sm text-gray-400">
        Gérez vos programmes radio automatiques, vos horaires de diffusion et écoutez vos émissions sur votre smartphone avec <strong class="text-emerald-400">AntennaPod</strong> !
      </p>
    </div>

    <!-- ANTENNAPOD BANNER & COPY LINK -->
    <div class="bg-gradient-to-r from-emerald-950/40 via-gray-900 to-purple-950/40 border border-emerald-800/50 rounded-3xl p-5 md:p-6 shadow-xl space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="space-y-1 min-w-0">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <span>📡 Flux Podcast AntennaPod (Clé Sécurisée)</span>
          </h2>
          <p class="text-xs text-gray-400">Copiez cette URL avec clé privée dans AntennaPod pour écouter vos émissions sur votre smartphone.</p>
        </div>

        <div class="flex items-center gap-2">
          <button 
            on:click={regenerateToken}
            class="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold text-xs rounded-xl border border-gray-700 transition-all flex items-center gap-1 shrink-0"
            title="Régénérer la clé secrète"
          >
            <span>🔄 Clé Secrète</span>
          </button>

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
      </div>

      <div class="p-3 bg-gray-950/90 rounded-2xl border border-gray-800 flex items-center justify-between gap-3 text-xs font-mono text-emerald-400">
        <span class="truncate">{feedUrl}</span>
        <span class="text-[10px] bg-emerald-950 text-emerald-300 font-sans px-2.5 py-1 rounded-full border border-emerald-800 uppercase font-bold shrink-0">
          RSS 2.0 / iTunes
        </span>
      </div>
    </div>

    <!-- TABLEAU DE BORD DES PROGRAMMATIONS (MULTI-PROGRAMMES) -->
    <div class="bg-gray-900/90 border border-gray-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      <div class="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 pb-4">
        <div class="space-y-1">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <span>📻 Tableau de Bord des Programmations Radio</span>
          </h2>
          <p class="text-xs text-gray-400">Gérez vos rendez-vous audio automatiques et consultez le compte à rebours de la prochaine émission.</p>
        </div>

        <button 
          on:click={openCreateModal}
          class="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-extrabold text-xs rounded-xl shadow-lg transition-all flex items-center gap-1.5 shrink-0"
        >
          <span>+ Créer un programme</span>
        </button>
      </div>

      <!-- PROGRAMMING CARDS GRID -->
      <div class="space-y-4">
        {#if schedulesList.length === 0}
          <div class="p-8 text-center bg-gray-950/50 rounded-2xl border border-gray-800 text-gray-400 text-xs space-y-3">
            <p>Aucun programme radio automatique configuré.</p>
            <button on:click={openCreateModal} class="px-4 py-2 bg-purple-600 text-white font-bold text-xs rounded-xl">
              + Ajouter votre première matinale ou flash info
            </button>
          </div>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {#each schedulesList as prog}
              <div class="bg-gray-950 border border-gray-800 hover:border-purple-800/80 rounded-2xl p-5 space-y-4 transition-all flex flex-col justify-between relative group">
                
                <div class="space-y-3">
                  <!-- Header with status badge -->
                  <div class="flex items-center justify-between gap-2">
                    <span class="font-extrabold text-sm text-white truncate">{prog.name}</span>

                    <button 
                      on:click={() => toggleProgram(prog.id)}
                      class="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full border transition-all shrink-0 {prog.enabled ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800' : 'bg-gray-800 text-gray-400 border-gray-700'}"
                    >
                      {prog.enabled ? '🟢 Actif' : '⚪ Désactivé'}
                    </button>
                  </div>

                  <!-- Next Run Display Countdown -->
                  <div class="p-2.5 bg-gray-900/80 rounded-xl border border-gray-800/80 flex items-center justify-between text-xs">
                    <span class="text-gray-400 font-semibold">Prochaine diffusion :</span>
                    <span class="font-bold text-emerald-400">{prog.next_run_display || 'Désactivé'}</span>
                  </div>

                  <!-- Details Badges -->
                  <div class="flex flex-wrap items-center gap-1.5 text-[11px] text-gray-400">
                    <span class="bg-gray-900 px-2 py-0.5 rounded-lg border border-gray-800">⏰ {prog.time}</span>
                    <span class="bg-gray-900 px-2 py-0.5 rounded-lg border border-gray-800">
                      {prog.frequency === 'daily' ? 'Tous les jours' : prog.frequency === 'weekdays' ? 'Du lun. au ven.' : 'Hebdomadaire'}
                    </span>
                    {#if prog.theme}
                      <span class="bg-purple-950/60 text-purple-300 px-2 py-0.5 rounded-lg border border-purple-800/60 font-bold">🎯 {prog.theme}</span>
                    {/if}
                    <span class="bg-gray-900 px-2 py-0.5 rounded-lg border border-gray-800">📊 {prog.topics_count} sujets</span>
                  </div>
                </div>

                <!-- Action buttons -->
                <div class="pt-3 border-t border-gray-900 flex items-center justify-between gap-2">
                  <button 
                    on:click={() => runProgramNow(prog.id, prog.name)}
                    class="px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600 text-purple-300 hover:text-white font-bold text-xs rounded-xl border border-purple-800/60 transition-all flex items-center gap-1"
                    title="Générer cette émission immédiatement"
                  >
                    <span>⚡ {runMessageMap[prog.id] || 'Lancer'}</span>
                  </button>

                  <div class="flex items-center gap-2">
                    <button 
                      on:click={() => openEditModal(prog)}
                      class="px-2.5 py-1.5 bg-gray-900 hover:bg-gray-800 text-gray-300 font-bold text-xs rounded-xl border border-gray-800 transition-all"
                      title="Modifier les paramètres du programme"
                    >
                      ✏️ Éditer
                    </button>

                    <button 
                      on:click={() => deleteProgram(prog.id, prog.name)}
                      class="px-2.5 py-1.5 bg-rose-950/40 hover:bg-rose-600 text-rose-400 hover:text-white font-bold text-xs rounded-xl border border-rose-800/40 transition-all"
                      title="Supprimer ce programme"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

              </div>
            {/each}
          </div>
        {/if}
      </div>

    </div>

    <!-- CARD 2: IMMEDIATE PODCAST RECIPE GENERATION -->
    <div class="bg-gray-900/90 border border-gray-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      <div class="space-y-1 border-b border-gray-800 pb-3">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <span>⚡ Créer une émission immédiatement (À la demande)</span>
        </h2>
        <p class="text-xs text-purple-400">Configurez votre thème et vos sujets pour produire une émission sur-le-champ !</p>
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

        <!-- MAX DAYS -->
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
            <option value="analyse_profonde">Décryptage Posé</option>
            <option value="express">Flash Express</option>
            <option value="debat">Débat Radio</option>
          </select>
        </div>

        <!-- VOICE SELECTION -->
        <div class="space-y-2">
          <label for="podcast-voice" class="block text-xs font-bold text-gray-300 uppercase tracking-wider">
            🎭 Voix & Multi-Émotions
          </label>
          <select 
            id="podcast-voice"
            bind:value={voiceKey}
            class="w-full bg-gray-950 border border-purple-600 rounded-2xl py-3 px-4 text-xs font-bold text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          >
            <option value="Marie - Neutral">🧘 Marie - Neutral (Calme & Posée)</option>
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

      <!-- GENERATION BUTTON -->
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

    <!-- PLAYER & HISTORIQUE DES ÉMISSIONS -->
    {#if podcastHistory.length > 0}
      <div class="bg-gray-900/90 border border-gray-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
        
        <div class="flex items-center justify-between border-b border-gray-800 pb-3">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <span>🎧 Historique des Émissions Audio ({podcastHistory.length})</span>
          </h2>
        </div>

        <!-- ACTIVE PODCAST PLAYER -->
        {#if currentPodcast}
          <div class="bg-gradient-to-b from-gray-900 to-gray-950 border border-purple-800/60 rounded-3xl p-6 shadow-2xl space-y-4">
            
            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1">
                <span class="text-[10px] uppercase tracking-wider font-extrabold bg-purple-950 text-purple-400 px-2.5 py-1 rounded-full border border-purple-800">
                  Émission sélectionnée
                </span>
                <h3 class="text-xl font-extrabold text-white leading-snug">{currentPodcast.title}</h3>
                <p class="text-xs text-gray-400">Généré le {currentPodcast.created_at || 'récemment'} • Voix: {currentPodcast.voice || 'Marie'}</p>
              </div>

              <button 
                on:click={() => playPodcastItem(currentPodcast)}
                class="p-3 bg-emerald-500 hover:bg-emerald-400 text-gray-950 rounded-2xl shadow-lg transition-all shrink-0 font-bold text-xs flex items-center gap-2"
              >
                <span>▶️ Lancer dans le lecteur</span>
              </button>
            </div>

            <!-- TOGGLE SCRIPT TRANSCRIPTION -->
            <div class="pt-2 border-t border-gray-800 flex justify-between items-center">
              <button 
                on:click={() => showScript = !showScript}
                class="text-xs text-purple-400 hover:underline font-bold"
              >
                {showScript ? 'Masquer la transcription script 📜' : 'Afficher le script intégral rédigé 📜'}
              </button>
            </div>

            {#if showScript}
              <div class="p-4 bg-gray-950 rounded-2xl border border-gray-800 text-xs leading-relaxed text-gray-300 whitespace-pre-wrap max-h-80 overflow-y-auto">
                {currentPodcast.script}
              </div>
            {/if}
          </div>
        {/if}

        <!-- PODCAST HISTORY LIST -->
        <div class="space-y-3">
          {#each podcastHistory as pod}
            <div class="p-4 bg-gray-950 border border-gray-800/80 hover:border-purple-800/60 rounded-2xl flex items-center justify-between gap-4 transition-all group">
              <div class="space-y-1 min-w-0">
                <h4 class="font-bold text-sm text-white truncate">{pod.title}</h4>
                <p class="text-xs text-gray-400">
                  {pod.created_at ? new Date(pod.created_at).toLocaleDateString('fr-FR') : ''} • {pod.topics_count || 5} sujets
                </p>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <button 
                  on:click={() => playPodcastItem(pod)}
                  class="px-3 py-1.5 bg-gray-800 hover:bg-purple-600 text-white font-bold text-xs rounded-xl transition-all"
                >
                  ▶ Écouter
                </button>

                <button 
                  on:click={() => deletePodcastItem(pod.id)}
                  class="p-1.5 text-gray-500 hover:text-rose-400 rounded-lg hover:bg-gray-900 transition-colors"
                  title="Supprimer"
                >
                  🗑️
                </button>
              </div>
            </div>
          {/each}
        </div>

      </div>
    {/if}

  </div>
</div>

<!-- PROGRAM MODAL (AJOUTER / MODIFIER UN PROGRAMME) -->
{#if showProgramModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
    <div class="bg-gray-900 border border-gray-800 w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden">
      
      <!-- Header -->
      <div class="p-6 border-b border-gray-800 flex justify-between items-center bg-gray-950/50">
        <h3 class="text-lg font-bold text-white">
          {editingProgramId ? '✏️ Modifier la programmation' : '➕ Nouveau programme radio'}
        </h3>
        <button on:click={() => showProgramModal = false} class="p-2 text-gray-400 hover:text-white rounded-full">
          ✕
        </button>
      </div>

      <!-- Body Form -->
      <div class="p-6 space-y-4 max-h-[70vh] overflow-y-auto text-xs text-gray-200">
        
        <!-- PROGRAM NAME -->
        <div class="space-y-1.5">
          <label for="form-prog-name" class="block font-bold text-gray-300 uppercase">Nom du programme</label>
          <input 
            id="form-prog-name"
            type="text" 
            bind:value={formName}
            placeholder="Ex: Matinale Suisse & Europe, Flash Tech 12h..."
            class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- TIME -->
          <div class="space-y-1.5">
            <label for="form-prog-time" class="block font-bold text-gray-300 uppercase">Heure de diffusion</label>
            <input 
              id="form-prog-time"
              type="time" 
              bind:value={formTime}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            />
          </div>

          <!-- FREQUENCY -->
          <div class="space-y-1.5">
            <label for="form-prog-freq" class="block font-bold text-gray-300 uppercase">Fréquence</label>
            <select 
              id="form-prog-freq"
              bind:value={formFrequency}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            >
              <option value="daily">Tous les jours (Quotidien)</option>
              <option value="weekdays">Du lundi au vendredi</option>
              <option value="weekly_monday">Chaque Lundi</option>
              <option value="weekly_friday">Chaque Vendredi</option>
            </select>
          </div>
        </div>

        <!-- THEME FILTER -->
        <div class="space-y-1.5">
          <label for="form-prog-theme" class="block font-bold text-gray-300 uppercase">Thème / Mot-clé spécifique (Optionnel)</label>
          <input 
            id="form-prog-theme"
            type="text" 
            bind:value={formTheme}
            placeholder="Ex: Suisse, Tech, IA, Économie..."
            class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- TONE -->
          <div class="space-y-1.5">
            <label for="form-prog-tone" class="block font-bold text-gray-300 uppercase">Style</label>
            <select 
              id="form-prog-tone"
              bind:value={formTone}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            >
              <option value="journal_matinal">Matinal Dynamique</option>
              <option value="analyse_profonde">Décryptage Posé</option>
              <option value="express">Flash Express</option>
              <option value="debat">Débat Radio</option>
            </select>
          </div>

          <!-- VOICE -->
          <div class="space-y-1.5">
            <label for="form-prog-voice" class="block font-bold text-gray-300 uppercase">Voix & Émotion</label>
            <select 
              id="form-prog-voice"
              bind:value={formVoice}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            >
              <option value="Marie - Neutral">🧘 Marie - Neutral</option>
              <option value="Marie - Excited">⚡ Marie - Excited</option>
              <option value="Marie - Happy">😊 Marie - Happy</option>
              <option value="Marie - Sad">💬 Marie - Sad</option>
              <option value="Marie - Curious">🔍 Marie - Curious</option>
              <option value="Marie - Angry">📢 Marie - Angry</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- TOPICS COUNT -->
          <div class="space-y-1.5">
            <label for="form-prog-topics" class="block font-bold text-gray-300 uppercase">Sujets</label>
            <select 
              id="form-prog-topics"
              bind:value={formTopicsCount}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            >
              <option value={3}>3 sujets (Flash)</option>
              <option value={5}>5 sujets (Standard)</option>
              <option value={8}>8 sujets (Complet)</option>
              <option value={10}>10 sujets (Grand tour)</option>
            </select>
          </div>

          <!-- MAX DAYS -->
          <div class="space-y-1.5">
            <label for="form-prog-days" class="block font-bold text-gray-300 uppercase">Ancienneté max</label>
            <select 
              id="form-prog-days"
              bind:value={formMaxDays}
              class="w-full bg-gray-950 border border-gray-800 rounded-xl py-2.5 px-3 text-xs text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            >
              <option value={1}>Dernières 24h</option>
              <option value={3}>3 jours</option>
              <option value={7}>7 jours</option>
              <option value={14}>14 jours</option>
            </select>
          </div>
        </div>

        <!-- ONLY VERIFIED -->
        <div class="flex items-center justify-between p-3 bg-gray-950 rounded-xl border border-gray-800">
          <span class="font-bold text-xs text-gray-300">Sources vérifiées uniquement (3+ médias)</span>
          <input type="checkbox" bind:checked={formOnlyVerified} class="w-4 h-4 accent-purple-500 cursor-pointer" />
        </div>

      </div>

      <!-- Footer Buttons -->
      <div class="p-4 bg-gray-950/50 border-t border-gray-800 flex justify-end gap-2">
        <button 
          on:click={() => showProgramModal = false}
          class="px-4 py-2 text-xs font-bold text-gray-400 hover:text-white"
        >
          Annuler
        </button>
        <button 
          on:click={handleSaveProgram}
          disabled={formSaving}
          class="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white font-extrabold text-xs rounded-xl shadow-md transition-all disabled:opacity-50"
        >
          {formSaving ? 'Enregistrement...' : 'Enregistrer le programme'}
        </button>
      </div>

    </div>
  </div>
{/if}
