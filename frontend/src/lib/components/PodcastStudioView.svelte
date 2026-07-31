<script>
  import { onMount } from 'svelte';
  import { mistralApiKey, geminiApiKey, synthesisProvider, selectedMistralPodcastModel, selectedGeminiPodcastModel, currentView } from '../stores/appState.js';
  import { playTrack, selectedVoice } from '../stores/audioStore.js';

  // Recipe configuration options (for immediate generation)
  let topicsCount = 5;
  let maxDays = 7;
  let onlyVerified = false;
  let tone = "journal_matinal";
  let voiceKey = $selectedVoice || "Marie - Dynamic";
  let themeInput = "";

  let isGenerating = false;
  let progressStep = "";
  let errorMsg = "";

  let generationLogs = [];
  let logContainer = null;
  let logsCopied = false;

  $: if (logContainer && generationLogs.length) {
    setTimeout(() => {
      if (logContainer) logContainer.scrollTop = logContainer.scrollHeight;
    }, 50);
  }

  function copyLogs() {
    const text = generationLogs.join('\n');
    navigator.clipboard.writeText(text);
    logsCopied = true;
    setTimeout(() => logsCopied = false, 2500);
  }

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
  let formVoice = "Marie - Dynamic";
  let formTheme = "";
  let formTopicsCount = 5;
  let formMaxDays = 7;
  let formOnlyVerified = true;
  let formSaving = false;

  let feedCopied = false;
  let feedToken = "";
  let runMessageMap = {};

  let podcastSystemPrompt = "";
  let podcastJingleFilename = "whoosh_default.mp3";

  async function fetchPodcastSettings() {
    try {
      const res = await fetch('/api/podcast/settings');
      if (res.ok) {
        const data = await res.json();
        podcastSystemPrompt = data.podcast_system_prompt || "";
        podcastJingleFilename = data.podcast_jingle_filename || "whoosh_default.mp3";
      }
    } catch (e) {}
  }

  async function saveSettings() {
    try {
      await fetch('/api/podcast/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          podcast_system_prompt: podcastSystemPrompt,
          podcast_jingle_filename: podcastJingleFilename
        })
      });
      alert('Paramètres enregistrés !');
    } catch (e) {}
  }

  async function resetSystemPrompt() {
    try {
      await fetch('/api/podcast/settings/reset-prompt', { method: 'POST' });
      await fetchPodcastSettings();
    } catch (e) {}
  }

  async function resetJingle() {
    try {
      await fetch('/api/podcast/settings/reset-jingle', { method: 'POST' });
      await fetchPodcastSettings();
    } catch (e) {}
  }

  let isUploadingJingle = false;

  async function handleJingleUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.mp3')) {
      alert("Seuls les fichiers MP3 sont autorisés.");
      return;
    }
    
    isUploadingJingle = true;
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const res = await fetch('/api/podcast/settings/upload-jingle', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        podcastJingleFilename = data.filename || "whoosh_custom.mp3";
        alert("Nouveau jingle MP3 téléversé et configuré avec succès !");
      } else {
        const err = await res.json();
        alert(`Erreur : ${err.detail || "Échec de l'envoi"}`);
      }
    } catch (e) {
      alert(`Erreur : ${e.message}`);
    } finally {
      isUploadingJingle = false;
    }
  }

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
      const contentType = res.headers.get('content-type') || '';
      if (res.ok && contentType.includes('application/json')) {
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
      const contentType = res.headers.get('content-type') || '';
      if (res.ok && contentType.includes('application/json')) {
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
    if (!$mistralApiKey && !$geminiApiKey) {
      alert("Veuillez d'abord renseigner une clé API (Mistral AI ou Gemini) dans les Paramètres (icône ⚙️).");
      $currentView = 'settings';
      return;
    }

    isGenerating = true;
    errorMsg = "";
    generationLogs = [];

    try {
      const res = await fetch('/api/podcast/generate-stream', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topics_count: topicsCount,
          max_days: maxDays,
          only_verified: onlyVerified,
          tone: tone,
          voice: voiceKey,
          theme: themeInput,
          provider: $synthesisProvider,
          mistral_model: $selectedMistralPodcastModel,
          gemini_model: $selectedGeminiPodcastModel,
          api_key: $mistralApiKey || $geminiApiKey
        })
      });

      if (!res.ok) {
        throw new Error(`Erreur HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const payload = JSON.parse(trimmed.slice(6));
              if (payload.type === 'log') {
                generationLogs = [...generationLogs, payload.message];
              } else if (payload.type === 'result' && payload.podcast) {
                currentPodcast = payload.podcast;
                showScript = false;
                playTrack(currentPodcast.title, currentPodcast.audio_url, `Revue de Presse Vos (${voiceKey})`, currentPodcast.image_url);
                await fetchHistory();
              } else if (payload.type === 'error') {
                errorMsg = payload.message;
                generationLogs = [...generationLogs, `❌ Erreur : ${payload.message}`];
              }
            } catch (e) {
              console.warn("Parse SSE error:", e);
            }
          }
        }
      }
    } catch (err) {
      console.warn("Connexion interrompue ou timeout. Vérification de l'historique...", err);
      await new Promise(r => setTimeout(r, 2000));
      await fetchHistory();
      if (podcastHistory.length > 0) {
        currentPodcast = podcastHistory[0];
        showScript = false;
        playTrack(currentPodcast.title, currentPodcast.audio_url, `Revue de Presse Vos (${voiceKey})`, currentPodcast.image_url);
        errorMsg = "";
      }
    } finally {
      isGenerating = false;
    }
  }

  function playPodcastItem(p) {
    currentPodcast = p;
    playTrack(p.title, p.audio_url, `Revue de Presse Vos (${p.voice || 'Marie'})`, p.image_url);
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
    fetchPodcastSettings();
  });
</script>

<div class="flex-1 h-full overflow-y-auto bg-background text-foreground p-4 md:p-8 space-y-8">
  <div class="max-w-4xl mx-auto space-y-8">
    
    <!-- Top Header -->
    <div class="space-y-2 pt-2">
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs bg-primary/20 text-primary font-extrabold px-3 py-1 rounded-full border border-primary/40 uppercase tracking-wider">
          🎙️ Studio Radio Multi-Émotions
        </span>
        <span class="text-xs bg-primary/10 text-primary font-extrabold px-3 py-1 rounded-full border border-primary/30 uppercase tracking-wider">
          Flux AntennaPod XML (Sécurisé)
        </span>
      </div>
      <h1 class="text-3xl md:text-4xl font-black text-foreground tracking-tight">Revue de Presse Audio</h1>
      <p class="text-sm text-muted-foreground">
        Gérez vos programmes radio automatiques, vos horaires de diffusion et écoutez vos émissions sur votre smartphone avec <strong class="text-primary">AntennaPod</strong> !
      </p>
    </div>

    <!-- ANTENNAPOD BANNER & COPY LINK -->
    <div class="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-xl space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="space-y-1 min-w-0">
          <h2 class="text-base font-bold text-foreground flex items-center gap-2">
            <span>📡 Flux Podcast AntennaPod (Clé Sécurisée)</span>
          </h2>
          <p class="text-xs text-muted-foreground">Copiez cette URL avec clé privée dans AntennaPod pour écouter vos émissions sur votre smartphone.</p>
        </div>

        <div class="flex items-center gap-2">
          <button 
            on:click={regenerateToken}
            class="px-3 py-2 bg-background hover:bg-accent text-foreground font-bold text-xs rounded-xl border border-border transition-all flex items-center gap-1 shrink-0"
            title="Régénérer la clé secrète"
          >
            <span>🔄 Clé Secrète</span>
          </button>

          <button 
            on:click={copyFeedUrl}
            class="px-4 py-2 bg-primary text-primary-foreground font-black text-xs rounded-xl shadow-md transition-all flex items-center gap-2 shrink-0"
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

      <div class="p-3 bg-background rounded-2xl border border-border flex items-center justify-between gap-3 text-xs font-mono text-primary">
        <span class="truncate">{feedUrl}</span>
        <span class="text-[10px] bg-primary/20 text-primary font-sans px-2.5 py-1 rounded-full border border-primary/40 uppercase font-bold shrink-0">
          RSS 2.0 / iTunes
        </span>
      </div>
    </div>

    <!-- TABLEAU DE BORD DES PROGRAMMATIONS (MULTI-PROGRAMMES) -->
    <div class="bg-card border border-border rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      <div class="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div class="space-y-1">
          <h2 class="text-lg font-bold text-foreground flex items-center gap-2">
            <span>📻 Tableau de Bord des Programmations Radio</span>
          </h2>
          <p class="text-xs text-muted-foreground">Gérez vos rendez-vous audio automatiques et consultez le compte à rebours de la prochaine émission.</p>
        </div>

        <button 
          on:click={openCreateModal}
          class="px-4 py-2.5 bg-primary text-primary-foreground font-extrabold text-xs rounded-xl shadow-lg transition-all flex items-center gap-1.5 shrink-0"
        >
          <span>+ Créer un programme</span>
        </button>
      </div>

      <!-- PROGRAMMING CARDS GRID -->
      <div class="space-y-4">
        {#if schedulesList.length === 0}
          <div class="p-8 text-center bg-background rounded-2xl border border-border text-muted-foreground text-xs space-y-3">
            <p>Aucun programme radio automatique configuré.</p>
            <button on:click={openCreateModal} class="px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-xl">
              + Ajouter votre première matinale ou flash info
            </button>
          </div>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {#each schedulesList as prog}
              <div class="bg-background border border-border hover:border-primary/60 rounded-2xl p-5 space-y-4 transition-all flex flex-col justify-between relative group">
                
                <div class="space-y-3">
                  <!-- Header with status badge -->
                  <div class="flex items-center justify-between gap-2">
                    <span class="font-extrabold text-sm text-foreground truncate">{prog.name}</span>

                    <button 
                      on:click={() => toggleProgram(prog.id)}
                      class="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full border transition-all shrink-0 {prog.enabled ? 'bg-primary/20 text-primary border-primary/60' : 'bg-card text-muted-foreground border-border'}"
                    >
                      {prog.enabled ? '🟢 Actif' : '⚪ Désactivé'}
                    </button>
                  </div>

                  <!-- Next Run Display Countdown -->
                  <div class="p-2.5 bg-card rounded-xl border border-border flex items-center justify-between text-xs">
                    <span class="text-muted-foreground font-semibold">Prochaine diffusion :</span>
                    <span class="font-bold text-primary">{prog.next_run_display || 'Désactivé'}</span>
                  </div>

                  <!-- Details Badges -->
                  <div class="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                    <span class="bg-card px-2 py-0.5 rounded-lg border border-border">⏰ {prog.time}</span>
                    <span class="bg-card px-2 py-0.5 rounded-lg border border-border">
                      {prog.frequency === 'daily' ? 'Tous les jours' : prog.frequency === 'weekdays' ? 'Du lun. au ven.' : 'Hebdomadaire'}
                    </span>
                    {#if prog.theme}
                      <span class="bg-primary/20 text-primary px-2 py-0.5 rounded-lg border border-primary/40 font-bold">🎯 {prog.theme}</span>
                    {/if}
                    <span class="bg-card px-2 py-0.5 rounded-lg border border-border">📊 {prog.topics_count} sujets</span>
                  </div>
                </div>

                <!-- Action buttons -->
                <div class="pt-3 border-t border-border flex items-center justify-between gap-2">
                  <button 
                    on:click={() => runProgramNow(prog.id, prog.name)}
                    class="px-3 py-1.5 bg-primary/20 hover:bg-primary text-primary hover:text-primary-foreground font-bold text-xs rounded-xl border border-primary/40 transition-all flex items-center gap-1"
                    title="Générer cette émission immédiatement"
                  >
                    <span>⚡ {runMessageMap[prog.id] || 'Lancer'}</span>
                  </button>

                  <div class="flex items-center gap-2">
                    <button 
                      on:click={() => openEditModal(prog)}
                      class="px-2.5 py-1.5 bg-card hover:bg-accent text-foreground font-bold text-xs rounded-xl border border-border transition-all"
                      title="Modifier les paramètres du programme"
                    >
                      ✏️ Éditer
                    </button>

                    <button 
                      on:click={() => deleteProgram(prog.id, prog.name)}
                      class="px-2.5 py-1.5 bg-destructive/10 hover:bg-destructive text-destructive hover:text-destructive-foreground font-bold text-xs rounded-xl border border-destructive/30 transition-all"
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
    <div class="bg-card border border-border rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      <div class="space-y-1 border-b border-border pb-3">
        <h2 class="text-lg font-bold text-foreground flex items-center gap-2">
          <span>⚡ Créer une émission immédiatement (À la demande)</span>
        </h2>
        <p class="text-xs text-primary">Configurez votre thème et vos sujets pour produire une émission sur-le-champ !</p>
      </div>

      <!-- KEYWORD / THEME FOCUS INPUT -->
      <div class="space-y-2">
        <label for="theme-input" class="block text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
          <span>🎯 Axer l'émission sur un thème / mot-clé précis (Optionnel)</span>
        </label>
        <div class="relative">
          <input 
            id="theme-input"
            type="text"
            placeholder="Ex: Intelligence Artificielle, Suisse, Économie, Climat..."
            bind:value={themeInput}
            class="w-full bg-background border border-border focus:border-primary rounded-2xl py-3 pl-4 pr-10 text-xs font-semibold text-foreground focus:ring-2 focus:ring-primary focus:outline-none transition-all placeholder:text-muted-foreground"
          />
          {#if themeInput}
            <button 
              on:click={() => themeInput = ''} 
              class="absolute right-3 top-3 text-muted-foreground hover:text-foreground text-xs font-bold"
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
          <label for="topics-count" class="block text-xs font-bold text-foreground uppercase tracking-wider">
            📊 Nombre de sujets
          </label>
          <select 
            id="topics-count"
            bind:value={topicsCount}
            class="w-full bg-background border border-border rounded-2xl py-3 px-4 text-xs font-bold text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
          >
            <option value={3}>3 sujets (Flash)</option>
            <option value={5}>5 sujets (Recommandé)</option>
            <option value={8}>8 sujets (Revue complète)</option>
            <option value={10}>10 sujets (Grand tour)</option>
          </select>
        </div>

        <!-- MAX DAYS -->
        <div class="space-y-2">
          <label for="max-days" class="block text-xs font-bold text-foreground uppercase tracking-wider">
            📅 Récence des articles
          </label>
          <select 
            id="max-days"
            bind:value={maxDays}
            class="w-full bg-background border border-border rounded-2xl py-3 px-4 text-xs font-bold text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
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
          <label for="podcast-tone" class="block text-xs font-bold text-foreground uppercase tracking-wider">
            📻 Style de présentation
          </label>
          <select 
            id="podcast-tone"
            bind:value={tone}
            class="w-full bg-background border border-border rounded-2xl py-3 px-4 text-xs font-bold text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
          >
            <option value="journal_matinal">Matinal Dynamique</option>
            <option value="analyse_profonde">Décryptage Posé</option>
            <option value="express">Flash Express</option>
            <option value="debat">Débat Radio</option>
          </select>
        </div>

        <!-- VOICE SELECTION -->
        <div class="space-y-2">
          <label for="podcast-voice" class="block text-xs font-bold text-foreground uppercase tracking-wider">
            🎭 Voix & Multi-Émotions
          </label>
          <select 
            id="podcast-voice"
            bind:value={voiceKey}
            class="w-full bg-background border border-primary/60 rounded-2xl py-3 px-4 text-xs font-bold text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
          >
            <option value="Marie - Dynamic">🎭 Auto (Changement d'intonation automatique)</option>
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
      <div class="flex items-center justify-between p-4 bg-background rounded-2xl border border-border">
        <div class="flex items-center gap-3">
          <span class="text-xl">🛡️</span>
          <div>
            <span class="block text-xs font-bold text-foreground">
              Informations Vérifiées uniquement (3+ médias distants)
            </span>
            <span class="text-[11px] text-muted-foreground">Ne retenir que les actualités confirmées par au moins 3 sources différentes</span>
          </div>
        </div>
        <input 
          type="checkbox" 
          bind:checked={onlyVerified}
          class="w-5 h-5 accent-primary rounded cursor-pointer"
        />
      </div>

      <!-- GENERATION BUTTON -->
      <button 
        on:click={handleGeneratePodcast}
        disabled={isGenerating}
        class="w-full py-3.5 bg-primary text-primary-foreground font-extrabold text-sm rounded-2xl shadow-xl transition-all disabled:opacity-50 flex items-center justify-center gap-3"
      >
        {#if isGenerating}
          <svg class="w-5 h-5 animate-spin text-primary-foreground" fill="none" viewBox="0 0 24 24">
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
        <p class="text-xs text-destructive font-medium text-center">{errorMsg}</p>
      {/if}

      <!-- TERMINAL LOGS CONSOLE UI -->
      {#if isGenerating || generationLogs.length > 0}
        <div class="bg-background border border-primary/60 rounded-3xl p-5 shadow-2xl space-y-3 font-mono text-xs">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-destructive inline-block"></span>
              <span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
              <span class="w-3 h-3 rounded-full bg-primary text-primary-foreground inline-block"></span>
              <span class="text-foreground font-bold ml-2">Console d'exécution du Podcast (SSE Temps Réel)</span>
            </div>

            {#if generationLogs.length > 0}
              <button 
                on:click={copyLogs}
                class="px-3.5 py-1.5 bg-card hover:bg-accent text-primary font-bold text-xs rounded-xl border border-border transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>{logsCopied ? '✓ Logs Copiés !' : '📋 Copier les logs'}</span>
              </button>
            {/if}
          </div>

          <div bind:this={logContainer} class="max-h-96 overflow-y-auto space-y-1.5 pr-2 text-foreground select-text leading-relaxed font-mono">
            {#each generationLogs as log}
              <div class="font-mono text-[11px] leading-relaxed whitespace-pre-wrap">{log}</div>
            {/each}
            {#if isGenerating}
              <div class="text-primary animate-pulse font-bold pt-1 text-xs">
                ⚡ {generationLogs.length ? generationLogs[generationLogs.length - 1] : "Initialisation de l'émission..."}
              </div>
            {/if}
          </div>
        </div>
      {/if}

    </div>

    <!-- CARD 3: PERSONNALISATION -->
    <div class="bg-card border border-border rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      <div class="space-y-1 border-b border-border pb-3">
        <h2 class="text-lg font-bold text-foreground flex items-center gap-2">
          <span>⚙️ Personnalisation du Podcast</span>
        </h2>
        <p class="text-xs text-muted-foreground">Modifiez le prompt système de l'IA et l'audio de transition.</p>
      </div>

      <!-- SYSTEM PROMPT -->
      <div class="space-y-2">
        <div class="flex justify-between items-center">
          <label class="block text-xs font-bold text-foreground uppercase tracking-wider">Prompt Système (IA)</label>
          <button on:click={resetSystemPrompt} class="text-xs text-destructive hover:underline font-bold">Réinitialiser</button>
        </div>
        <textarea
          bind:value={podcastSystemPrompt}
          rows="5"
          placeholder="Laissez vide pour utiliser le prompt par défaut..."
          class="w-full bg-background border border-border rounded-2xl py-3 px-4 text-xs font-semibold text-foreground focus:ring-2 focus:ring-primary focus:outline-none transition-all"
        ></textarea>
        <button on:click={saveSettings} class="px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-xl shadow-md transition-all">Enregistrer le prompt</button>
      </div>

      <!-- CUSTOM JINGLE -->
      <div class="space-y-3">
        <div class="flex justify-between items-center">
          <label class="block text-xs font-bold text-foreground uppercase tracking-wider">Jingle de transition</label>
          <button on:click={resetJingle} class="text-xs text-destructive hover:underline font-bold">Réinitialiser</button>
        </div>
        
        <p class="text-[10px] text-muted-foreground">
          Fichier de transition actif : <span class="text-primary font-extrabold">{podcastJingleFilename}</span>
        </p>

        <div class="flex items-center gap-3">
          <input 
            type="file" 
            accept="audio/mpeg" 
            on:change={handleJingleUpload} 
            class="hidden" 
            id="jingle-upload-input" 
          />
          <label 
            for="jingle-upload-input" 
            class="px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-xl shadow-md cursor-pointer transition-all flex items-center gap-1.5"
          >
            📂 Téléverser un fichier MP3 (jingle court)
          </label>
          
          {#if isUploadingJingle}
            <span class="text-[10px] text-primary animate-pulse font-bold">Envoi...</span>
          {/if}
        </div>
      </div>
    </div>

    <!-- PLAYER & HISTORIQUE DES ÉMISSIONS -->
    {#if podcastHistory.length > 0}
      <div class="bg-card border border-border rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
        
        <div class="flex items-center justify-between border-b border-border pb-3">
          <h2 class="text-lg font-bold text-foreground flex items-center gap-2">
            <span>🎧 Historique des Émissions Audio ({podcastHistory.length})</span>
          </h2>
        </div>

        <!-- ACTIVE PODCAST PLAYER -->
        {#if currentPodcast}
          <div class="bg-background border border-primary/60 rounded-3xl p-6 shadow-2xl space-y-4">
            
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-center gap-4 min-w-0">
                {#if currentPodcast.image_url}
                  <div class="w-16 h-16 md:w-20 md:h-20 rounded-2xl overflow-hidden shrink-0 border border-border shadow-md">
                    <img src={currentPodcast.image_url} alt="Cover" style="width: 100%; height: 100%; object-fit: cover; aspect-ratio: 1 / 1;" />
                  </div>
                {/if}
                <div class="space-y-1 min-w-0">
                  <span class="text-[10px] uppercase tracking-wider font-extrabold bg-primary/20 text-primary px-2.5 py-1 rounded-full border border-primary/40">
                    Émission sélectionnée
                  </span>
                  <h3 class="text-xl font-extrabold text-foreground leading-snug truncate">{currentPodcast.title}</h3>
                  <p class="text-xs text-muted-foreground">Généré le {currentPodcast.created_at || 'récemment'} • Voix: {currentPodcast.voice || 'Marie'}</p>
                </div>
              </div>

              <button 
                on:click={() => playPodcastItem(currentPodcast)}
                class="p-3 bg-primary text-primary-foreground rounded-2xl shadow-lg transition-all shrink-0 font-bold text-xs flex items-center gap-2"
              >
                <span>▶️ Lancer dans le lecteur</span>
              </button>
            </div>

            <!-- TOGGLE SCRIPT TRANSCRIPTION -->
            <div class="pt-2 border-t border-border flex justify-between items-center">
              <button 
                on:click={() => showScript = !showScript}
                class="text-xs text-primary hover:underline font-bold"
              >
                {showScript ? 'Masquer la transcription script 📜' : 'Afficher le script intégral rédigé 📜'}
              </button>
            </div>

            {#if showScript}
              <div class="p-4 bg-card rounded-2xl border border-border text-xs leading-relaxed text-foreground whitespace-pre-wrap max-h-80 overflow-y-auto">
                {currentPodcast.script}
              </div>
            {/if}
          </div>
        {/if}

        <!-- PODCAST HISTORY LIST -->
        <div class="space-y-3">
          {#each podcastHistory as pod}
            <div class="p-4 bg-background border border-border hover:border-primary/60 rounded-2xl flex items-center justify-between gap-4 transition-all group">
              <div class="flex items-center gap-4 min-w-0">
                {#if pod.image_url}
                  <div class="w-12 h-12 rounded-xl overflow-hidden shrink-0 border border-border shadow-sm">
                    <img src={pod.image_url} alt="Cover" style="width: 100%; height: 100%; object-fit: cover; aspect-ratio: 1 / 1;" />
                  </div>
                {/if}
                <div class="space-y-1 min-w-0">
                  <h4 class="font-bold text-sm text-foreground truncate">{pod.title}</h4>
                  <p class="text-xs text-muted-foreground">
                    {pod.created_at ? new Date(pod.created_at).toLocaleDateString('fr-FR') : ''} • {pod.topics_count || 5} sujets
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <button 
                  on:click={() => playPodcastItem(pod)}
                  class="px-3 py-1.5 bg-card hover:bg-primary hover:text-primary-foreground text-foreground font-bold text-xs rounded-xl border border-border transition-all"
                >
                  ▶ Écouter
                </button>

                <button 
                  on:click={() => deletePodcastItem(pod.id)}
                  class="p-1.5 text-muted-foreground hover:text-destructive rounded-lg hover:bg-card transition-colors"
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
    <div class="bg-card text-card-foreground border border-border w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden">
      
      <!-- Header -->
      <div class="p-6 border-b border-border flex justify-between items-center bg-background">
        <h3 class="text-lg font-bold text-foreground">
          {editingProgramId ? '✏️ Modifier la programmation' : '➕ Nouveau programme radio'}
        </h3>
        <button on:click={() => showProgramModal = false} class="p-2 text-muted-foreground hover:text-foreground rounded-full">
          ✕
        </button>
      </div>

      <!-- Body Form -->
      <div class="p-6 space-y-4 max-h-[70vh] overflow-y-auto text-xs text-foreground">
        
        <!-- PROGRAM NAME -->
        <div class="space-y-1.5">
          <label for="form-prog-name" class="block font-bold text-foreground uppercase">Nom du programme</label>
          <input 
            id="form-prog-name"
            type="text" 
            bind:value={formName}
            placeholder="Ex: Matinale Suisse & Europe, Flash Tech 12h..."
            class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- TIME -->
          <div class="space-y-1.5">
            <label for="form-prog-time" class="block font-bold text-foreground uppercase">Heure de diffusion</label>
            <input 
              id="form-prog-time"
              type="time" 
              bind:value={formTime}
              class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <!-- FREQUENCY -->
          <div class="space-y-1.5">
            <label for="form-prog-freq" class="block font-bold text-foreground uppercase">Fréquence</label>
            <select 
              id="form-prog-freq"
              bind:value={formFrequency}
              class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
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
          <label for="form-prog-theme" class="block font-bold text-foreground uppercase">Thème / Mot-clé spécifique (Optionnel)</label>
          <input 
            id="form-prog-theme"
            type="text" 
            bind:value={formTheme}
            placeholder="Ex: Suisse, Tech, IA, Économie..."
            class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- TONE -->
          <div class="space-y-1.5">
            <label for="form-prog-tone" class="block font-bold text-foreground uppercase">Style</label>
            <select 
              id="form-prog-tone"
              bind:value={formTone}
              class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="journal_matinal">Matinal Dynamique</option>
              <option value="analyse_profonde">Décryptage Posé</option>
              <option value="express">Flash Express</option>
              <option value="debat">Débat Radio</option>
            </select>
          </div>

          <!-- VOICE -->
          <div class="space-y-1.5">
            <label for="form-prog-voice" class="block font-bold text-foreground uppercase">Voix & Émotion</label>
            <select 
              id="form-prog-voice"
              bind:value={formVoice}
              class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="Marie - Dynamic">🎭 Auto (Intonation automatique)</option>
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
            <label for="form-prog-topics" class="block font-bold text-foreground uppercase">Sujets</label>
            <select 
              id="form-prog-topics"
              bind:value={formTopicsCount}
              class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value={3}>3 sujets (Flash)</option>
              <option value={5}>5 sujets (Standard)</option>
              <option value={8}>8 sujets (Complet)</option>
              <option value={10}>10 sujets (Grand tour)</option>
            </select>
          </div>

          <!-- MAX DAYS -->
          <div class="space-y-1.5">
            <label for="form-prog-days" class="block font-bold text-foreground uppercase">Ancienneté max</label>
            <select 
              id="form-prog-days"
              bind:value={formMaxDays}
              class="w-full bg-background border border-border rounded-xl py-2.5 px-3 text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value={1}>Dernières 24h</option>
              <option value={3}>3 jours</option>
              <option value={7}>7 jours</option>
              <option value={14}>14 jours</option>
            </select>
          </div>
        </div>

        <!-- ONLY VERIFIED -->
        <div class="flex items-center justify-between p-3 bg-background rounded-xl border border-border">
          <span class="font-bold text-xs text-foreground">Sources vérifiées uniquement (3+ médias)</span>
          <input type="checkbox" bind:checked={formOnlyVerified} class="w-4 h-4 accent-primary cursor-pointer" />
        </div>

      </div>

      <!-- Footer Buttons -->
      <div class="p-4 bg-background border-t border-border flex justify-end gap-2">
        <button 
          on:click={() => showProgramModal = false}
          class="px-4 py-2 text-xs font-bold text-muted-foreground hover:text-foreground"
        >
          Annuler
        </button>
        <button 
          on:click={handleSaveProgram}
          disabled={formSaving}
          class="px-5 py-2 bg-primary text-primary-foreground font-extrabold text-xs rounded-xl shadow-md transition-all disabled:opacity-50"
        >
          {formSaving ? 'Enregistrement...' : 'Enregistrer le programme'}
        </button>
      </div>

    </div>
  </div>
{/if}
