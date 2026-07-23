<script>
  import { onMount } from 'svelte';
  import { mistralApiKey, selectedMistralModel, showSettingsModal } from '../stores/appState.js';
  import { playTrack, selectedVoice } from '../stores/audioStore.js';

  let status = { total_articles: 0, vectorized_articles: 0, pending_articles: 0, sqlite_vec_enabled: true };
  let clusters = [];
  let similarityThreshold = 0.90;
  let isLoading = false;
  let isVectorizing = false;
  let isClustering = false;
  let message = '';
  let error = '';

  // Synthesis states per clusterId
  let syntheses = {}; // { [clusterId]: { synthesis_title: '...', summary: '...', key_takeaways: [...] } }
  let synthLoading = {}; // { [clusterId]: boolean }
  let synthAudioLoading = {}; // { [clusterId]: boolean }

  async function fetchStatus() {
    try {
      const res = await fetch('/api/clustering/status');
      if (res.ok) {
        status = await res.json();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function fetchClusters() {
    isClustering = true;
    try {
      const res = await fetch(`/api/clustering/clusters?threshold=${similarityThreshold}`);
      if (res.ok) {
        const data = await res.json();
        clusters = data.clusters || [];
      }
    } catch (err) {
      console.error("Erreur lors de la récupération des clusters:", err);
    } finally {
      isClustering = false;
    }
  }

  async function startVectorization(force = false) {
    if (!$mistralApiKey) {
      error = "Veuillez configurer votre clé API Mistral dans les Paramètres.";
      return;
    }

    isVectorizing = true;
    error = '';
    message = '';

    try {
      const res = await fetch('/api/clustering/vectorize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: $mistralApiKey,
          force_revectorize: force
        })
      });

      const result = await res.json();

      if (res.ok) {
        message = `${result.data.processed_count} article(s) vectorisé(s) avec succès !`;
        await fetchStatus();
        await fetchClusters();
      } else {
        error = result.detail || "Échec de la vectorisation.";
      }
    } catch (err) {
      error = "Erreur de connexion avec le serveur.";
    } finally {
      isVectorizing = false;
    }
  }

  async function generateClusterSynthesis(cluster) {
    if (!$mistralApiKey) {
      error = "Veuillez configurer votre clé API Mistral dans les Paramètres.";
      return;
    }

    const cId = cluster.cluster_id;
    synthLoading[cId] = true;
    synthLoading = { ...synthLoading };

    try {
      const res = await fetch('/api/clustering/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          articles: cluster.articles,
          api_key: $mistralApiKey,
          model: $selectedMistralModel
        })
      });

      const result = await res.json();

      if (res.ok && result.data) {
        syntheses[cId] = result.data;
        syntheses = { ...syntheses };
      } else {
        alert(result.detail || "Erreur de synthèse Mistral.");
      }
    } catch (err) {
      alert("Erreur de communication avec le serveur.");
    } finally {
      synthLoading[cId] = false;
      synthLoading = { ...synthLoading };
    }
  }

  async function playSynthesisAudio(clusterId, title, textToRead) {
    synthAudioLoading[clusterId] = true;
    synthAudioLoading = { ...synthAudioLoading };

    try {
      const res = await fetch('/api/audio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToRead,
          voice: $selectedVoice
        })
      });

      const result = await res.json();

      if (res.ok && result.audio_url) {
        playTrack(title, result.audio_url, 'Podcast Synthèse Vos');
      } else {
        alert(result.detail || "Échec de la génération audio TTS.");
      }
    } catch (err) {
      alert("Erreur de connexion audio.");
    } finally {
      synthAudioLoading[clusterId] = false;
      synthAudioLoading = { ...synthAudioLoading };
    }
  }

  onMount(async () => {
    await fetchStatus();
    await fetchClusters();
  });
</script>

<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg p-6 md:p-10 space-y-8">
  
  <div class="max-w-4xl mx-auto space-y-8">
    
    <!-- Title & Header -->
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <span class="text-xs bg-primary-100 dark:bg-primary-900/50 text-primary-600 font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider">
          Moteur Vectoriel & Recoupement
        </span>
      </div>
      <h1 class="text-3xl font-extrabold">Synthèses Croisées & Clustering IA</h1>
      <p class="text-sm text-gray-500">
        Grâce aux embeddings et au calcul de distance cosinus, l'application identifie automatiquement les articles qui traitent du même sujet afin de générer des synthèses croisées uniques pour le podcast.
      </p>
    </div>

    <!-- Vector Dashboard Card -->
    <div class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm space-y-6">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-gray-800 pb-6">
        <div>
          <h3 class="text-lg font-bold">État de la Base Vectorielle</h3>
          <p class="text-xs text-gray-400">Progression des embeddings Mistral AI</p>
        </div>

        <div class="flex flex-wrap gap-2">
          <button 
            on:click={fetchClusters}
            class="px-4 py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 text-gray-700 dark:text-gray-300 font-semibold text-xs rounded-2xl transition-all flex items-center gap-1.5"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            <span>Recalculer</span>
          </button>

          <button 
            on:click={() => startVectorization(true)}
            disabled={isVectorizing}
            class="px-4 py-2.5 bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 text-indigo-600 dark:text-indigo-400 font-semibold text-xs rounded-2xl transition-all flex items-center gap-1.5"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
            <span>Ré-analyser proprement</span>
          </button>

          {#if status.pending_articles > 0}
            <button 
              on:click={() => startVectorization(false)}
              disabled={isVectorizing}
              class="px-5 py-2.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold text-xs rounded-2xl shadow-sm transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {#if isVectorizing}
                <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                <span>Vectorisation...</span>
              {:else}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                <span>Vectoriser ({status.pending_articles})</span>
              {/if}
            </button>
          {/if}
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="p-4 bg-gray-50 dark:bg-dark-bg rounded-2xl">
          <span class="text-xs font-semibold text-gray-400 block mb-1">Total Articles</span>
          <span class="text-2xl font-black">{status.total_articles}</span>
        </div>

        <div class="p-4 bg-emerald-50 dark:bg-emerald-950/30 rounded-2xl">
          <span class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 block mb-1">Vectorisés</span>
          <span class="text-2xl font-black text-emerald-600 dark:text-emerald-400">{status.vectorized_articles}</span>
        </div>

        <div class="p-4 bg-purple-50 dark:bg-purple-950/30 rounded-2xl">
          <span class="text-xs font-semibold text-purple-600 dark:text-purple-400 block mb-1">Grappes Détectées</span>
          <span class="text-2xl font-black text-purple-600 dark:text-purple-400">{clusters.length}</span>
        </div>
      </div>

      <!-- Threshold Sensitivity Controller -->
      <div class="pt-4 border-t border-gray-100 dark:border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <label for="threshold-slider" class="text-xs font-bold text-gray-700 dark:text-gray-300 block">
            Sensibilité de recoupement (Seuil : {similarityThreshold})
          </label>
          <p class="text-[11px] text-gray-400">Un seuil élevé (0.90) exige un sujet très spécifique pour former un groupe.</p>
        </div>

        <div class="flex items-center gap-3">
          <input 
            id="threshold-slider"
            type="range" 
            min="0.75" 
            max="0.95" 
            step="0.01" 
            bind:value={similarityThreshold}
            on:change={fetchClusters}
            class="w-36 accent-primary-500 cursor-pointer"
          />
          <button 
            on:click={fetchClusters}
            class="text-xs font-semibold bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 px-3 py-1.5 rounded-xl transition-all"
          >
            Appliquer
          </button>
        </div>
      </div>

      {#if message}
        <div class="p-3 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 rounded-xl text-xs font-medium">
          {message}
        </div>
      {/if}

      {#if error}
        <div class="p-3 bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 rounded-xl text-xs font-medium flex justify-between items-center">
          <span>{error}</span>
          {#if error.includes("Paramètres")}
            <button on:click={() => $showSettingsModal = true} class="underline font-bold">Paramètres</button>
          {/if}
        </div>
      {/if}
    </div>

    <!-- CLUSTERS LIST SECTION -->
    <div class="space-y-6">
      <div class="flex justify-between items-center">
        <h3 class="text-xl font-bold">Grappes d'Actualités ({clusters.length})</h3>
        <span class="text-xs text-gray-400">Seuil : {similarityThreshold}</span>
      </div>

      {#if isClustering}
        <div class="p-12 text-center text-gray-400 space-y-3">
          <div class="w-8 h-8 border-2 border-primary-500 border-t-transparent animate-spin rounded-full mx-auto"></div>
          <p class="text-xs font-medium">Calcul des distances vectorielles et regroupement des sujets...</p>
        </div>
      {:else if clusters.length === 0}
        <div class="p-8 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-3xl text-center space-y-2 text-gray-400">
          <p class="text-sm">Aucune grappe trouvée avec ce seuil.</p>
        </div>
      {:else}
        <div class="space-y-6">
          {#each clusters as cluster}
            <div class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm space-y-4">
              
              <!-- Cluster Header -->
              <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-gray-800 pb-4">
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    {#if cluster.article_count > 1}
                      <span class="text-[10px] bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400 font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                        🔥 Sujet Croisé ({cluster.article_count} sources)
                      </span>
                    {:else}
                      <span class="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium px-2 py-0.5 rounded-full">
                        Sujet individuel
                      </span>
                    {/if}
                  </div>
                  <h4 class="font-extrabold text-base md:text-lg">{cluster.topic_title}</h4>
                </div>

                <button 
                  on:click={() => generateClusterSynthesis(cluster)}
                  disabled={synthLoading[cluster.cluster_id]}
                  class="px-4 py-2 bg-gradient-to-r from-primary-500 to-indigo-600 hover:from-primary-600 hover:to-indigo-700 text-white font-medium text-xs rounded-xl shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5 shrink-0"
                >
                  {#if synthLoading[cluster.cluster_id]}
                    <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    <span>Synthèse...</span>
                  {:else}
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>
                    <span>{cluster.article_count > 1 ? 'Créer la synthèse croisée IA' : 'Résumer'}</span>
                  {/if}
                </button>
              </div>

              <!-- AI SYNTHESIS RESULT CARD IF GENERATED -->
              {#if syntheses[cluster.cluster_id]}
                <div class="p-5 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-500/30 space-y-4">
                  <div class="flex items-center justify-between flex-wrap gap-2">
                    <span class="text-xs font-bold text-primary-500">✨ Synthèse Croisée Sans Doublons</span>

                    <!-- LISTEN BUTTON FOR SYNTHESIS -->
                    <button 
                      on:click={() => playSynthesisAudio(cluster.cluster_id, syntheses[cluster.cluster_id].synthesis_title || cluster.topic_title, syntheses[cluster.cluster_id].summary)}
                      disabled={synthAudioLoading[cluster.cluster_id]}
                      class="text-xs bg-primary-500 hover:bg-primary-600 text-white font-semibold px-3 py-1.5 rounded-xl shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {#if synthAudioLoading[cluster.cluster_id]}
                        <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                        </svg>
                        <span>Génération audio...</span>
                      {:else}
                        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path></svg>
                        <span>🎧 Écouter le podcast</span>
                      {/if}
                    </button>
                  </div>

                  <h5 class="font-extrabold text-base text-gray-900 dark:text-gray-100">
                    {syntheses[cluster.cluster_id].synthesis_title || cluster.topic_title}
                  </h5>
                  <p class="text-sm leading-relaxed text-gray-800 dark:text-gray-200">
                    {syntheses[cluster.cluster_id].summary}
                  </p>
                  
                  {#if syntheses[cluster.cluster_id].key_takeaways}
                    <div class="pt-2 border-t border-gray-200/50 dark:border-gray-700/50">
                      <span class="text-xs font-bold text-gray-400 block mb-1">Points clés :</span>
                      <ul class="space-y-1">
                        {#each syntheses[cluster.cluster_id].key_takeaways as point}
                          <li class="text-xs text-gray-700 dark:text-gray-300 flex items-start gap-1.5">
                            <span class="text-primary-500">•</span>
                            <span>{point}</span>
                          </li>
                        {/each}
                      </ul>
                    </div>
                  {/if}
                </div>
              {/if}

              <!-- Articles in cluster -->
              <div class="space-y-2">
                <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Articles ({cluster.articles.length}) :</span>
                <div class="grid grid-cols-1 gap-2">
                  {#each cluster.articles as art}
                    <div class="p-3 bg-gray-50 dark:bg-dark-bg rounded-xl flex items-center justify-between text-xs gap-3">
                      <div class="flex items-center gap-2 truncate">
                        <span class="font-bold text-primary-500 shrink-0">{art.feed_title || 'RSS'}</span>
                        <span class="truncate text-gray-700 dark:text-gray-300">{art.title}</span>
                      </div>
                      <a href={art.url} target="_blank" rel="noreferrer" class="text-gray-400 hover:text-primary-500 shrink-0">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                      </a>
                    </div>
                  {/each}
                </div>
              </div>

            </div>
          {/each}
        </div>
      {/if}
    </div>

  </div>

</div>
