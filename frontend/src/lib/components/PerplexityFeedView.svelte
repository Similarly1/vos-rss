<script>
  import { onMount, tick } from 'svelte';
  import { mistralApiKey, geminiApiKey, synthesisProvider, selectedMistralDiscoverModel, selectedGeminiDiscoverModel, currentView } from '../stores/appState.js';
  import { playTrack, selectedVoice, sanitizeTextForSpeech } from '../stores/audioStore.js';
  import ProgressiveImage from './ProgressiveImage.svelte';

  // Mode: 'events' (Strict same event) vs 'themes' (Broad thematic digest)
  let perplexityMode = 'events'; // 'events' | 'themes'
  let selectedFilter = 'Tous';
  let onlyVerified = false; // Filter for >= 3 distinct media sources
  const filters = ['Tous', '🇨🇭 Suisse', '🇪🇺 Europe', '🌍 Monde', '💻 Technologie', '🔬 Science', '📈 Économie', '📁 Général'];

  let clusters = [];
  let isLoading = false;
  let audioLoadingState = {};
  
  // Selected Cluster for Detail Overlay / Modal
  let activeCluster = null;
  let modalContainer = null;

  function openCluster(cluster) {
    activeCluster = cluster;
    setTimeout(() => {
      if (modalContainer) {
        modalContainer.scrollTop = 0;
      }
    }, 20);
  }

  let syntheses = {};
  let synthLoading = {};

  const THEME_FALLBACK_IMAGES = {
    'Suisse': 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1200&q=80',
    'Europe': 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1200&q=80',
    'Monde': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    'Technologie': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80',
    'Science': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    'Économie': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
    'Général': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80'
  };

  function getLanguageFlag(lang) {
    if (!lang) return "🇫🇷";
    const l = lang.toLowerCase();
    if (l === "en") return "🇬🇧";
    if (l === "de") return "🇩🇪";
    if (l === "es") return "🇪🇸";
    return "🇫🇷";
  }

  function getDistinctFeedCount(cluster) {
    if (cluster.distinct_feed_count) return cluster.distinct_feed_count;
    const feeds = new Set(cluster.articles.map(a => a.feed_title || 'RSS'));
    return feeds.size;
  }

  function cleanTextBoilerplate(str) {
    if (!str) return '';
    // Strip HTML tags and their inner content for scripts, styles, headers, navs, footers
    let text = str.replace(/<(script|style|header|nav|footer|form|svg)[^>]*>[\s\S]*?<\/\1>/gi, ' ');
    // Strip header navigation noise strings
    text = text.replace(/(?:BBC Homepage|Skip to content|Accessibility Help|Your account|Search BBC|More menu|Close menu)[\s\S]*?(?:News|Sport|Weather|Sounds)/gi, ' ');
    // Strip remaining HTML tags
    text = text.replace(/<[^>]+>/g, ' ');
    // Collapse spaces
    return text.replace(/\s+/g, ' ').trim();
  }

  function renderMarkdownHtml(text) {
    if (!text) return '';
    let html = text;
    // Format bold headers & titles (**Text**) with clean styling
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-black text-cyan-200 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800/40">$1</strong>');
    // Format italic text (*Text*)
    html = html.replace(/\*(.*?)\*/g, '<em class="italic text-gray-300">$1</em>');
    // Format paragraph breaks
    const paragraphs = html.split(/\n\s*\n/);
    return paragraphs.map(p => `<p class="leading-relaxed mb-3">${p.trim()}</p>`).join('');
  }

  function getClusterTitle(cluster) {
    const cId = cluster.cluster_id;
    if (syntheses[cId] && syntheses[cId].synthesis_title) {
      return syntheses[cId].synthesis_title;
    }
    if (cluster.precomputed_synthesis && cluster.precomputed_synthesis.synthesis_title) {
      return cluster.precomputed_synthesis.synthesis_title;
    }
    return cleanTextBoilerplate(cluster.topic_title);
  }

  function isErrorSummary(text) {
    if (!text) return true;
    return text.startsWith('Erreur') || text.includes('génération du résumé');
  }

  function getTeaserSentence(cluster) {
    const cId = cluster.cluster_id;
    const synth = syntheses[cId] || cluster.precomputed_synthesis;
    if (synth && synth.summary && !isErrorSummary(synth.summary)) {
      const parts = synth.summary.split('. ');
      return parts.slice(0, 2).join('. ') + (parts.length > 2 ? '.' : '');
    }
    // Fallback: use first article's content or title
    const raw = cluster.articles[0]?.content || cluster.articles[0]?.description || cluster.articles[0]?.title || '';
    const clean = cleanTextBoilerplate(raw);
    return clean.slice(0, 200) + (clean.length > 200 ? '...' : '');
  }

  function getCategoryFallbackImage(category) {
    const cat = category || 'Général';
    return THEME_FALLBACK_IMAGES[cat] || THEME_FALLBACK_IMAGES['Général'];
  }

  function getClusterImage(cluster) {
    if (cluster.articles[0] && cluster.articles[0].image_url) {
      return cluster.articles[0].image_url;
    }
    return getCategoryFallbackImage(cluster.category);
  }

  async function fetchPerplexityClusters() {
    isLoading = true;
    const threshold = perplexityMode === 'events' ? 0.91 : 0.78;
    try {
      const res = await fetch(`/api/clustering/clusters?threshold=${threshold}&cluster_type=${perplexityMode}`);
      if (res.ok) {
        const data = await res.json();
        clusters = data.clusters || [];

        // Load precomputed syntheses immediately!
        clusters.forEach(c => {
          if (c.precomputed_synthesis) {
            syntheses[c.cluster_id] = c.precomputed_synthesis;
          }
        });
        syntheses = { ...syntheses };

        // Auto-synthesize top clusters in background
        autoSynthesizeClusters(clusters);
      }
    } catch (err) {
      console.error("Erreur lors de la récupération du fil Perplexity:", err);
    } finally {
      isLoading = false;
    }
  }

  function setMode(newMode) {
    if (perplexityMode === newMode) return;
    perplexityMode = newMode;
    fetchPerplexityClusters();
  }

  async function autoSynthesizeClusters(clustersList) {
    for (const cluster of clustersList.slice(0, 10)) {
      const cId = cluster.cluster_id;
      if (syntheses[cId] || cluster.precomputed_synthesis || synthLoading[cId]) continue;

      synthLoading[cId] = true;
      synthLoading = { ...synthLoading };

      try {
        const activeProvider = $synthesisProvider || ($mistralApiKey ? 'mistral' : 'gemini');
        const activeKey = activeProvider === 'gemini' ? $geminiApiKey : $mistralApiKey;
        const activeModel = activeProvider === 'gemini' ? $selectedGeminiDiscoverModel : $selectedMistralDiscoverModel;

        const res = await fetch('/api/clustering/synthesize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            articles: cluster.articles,
            provider: activeProvider,
            api_key: activeKey || null,
            model: activeModel
          })
        });

        const result = await res.json();
        if (res.ok && result.data) {
          syntheses[cId] = result.data;
          syntheses = { ...syntheses };
        }
      } catch (err) {
        console.error(`Erreur synthèse cluster ${cId}:`, err);
      } finally {
        synthLoading[cId] = false;
        synthLoading = { ...synthLoading };
      }
    }
  }

  async function handleListenSummary(clusterId, title, summaryText) {
    audioLoadingState[clusterId] = true;
    audioLoadingState = { ...audioLoadingState };

    const cleanText = sanitizeTextForSpeech(summaryText || title);
    const textToRead = `${title}. ${cleanText}`;

    try {
      const res = await fetch('/api/audio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToRead,
          voice: $selectedVoice || 'marie',
          api_key: $mistralApiKey || null
        })
      });

      const result = await res.json();

      if (res.ok && (result.audio_b64 || result.audio_url)) {
        playTrack(title, result.audio_b64 || result.audio_url, 'Voix Marie (Mistral Studio)');
      } else {
        alert(result.detail || "Échec de la génération de la voix Mistral.");
        if (result.detail && result.detail.includes("Clé API")) {
          $currentView = 'settings';
        }
      }
    } catch (err) {
      alert("Erreur de connexion avec le service audio.");
    } finally {
      audioLoadingState[clusterId] = false;
      audioLoadingState = { ...audioLoadingState };
    }
  }

  $: filteredClusters = clusters.filter(c => {
    const distinctCount = getDistinctFeedCount(c);
    const matchesVerified = !onlyVerified || distinctCount >= 3;

    if (selectedFilter === 'Tous') return matchesVerified;

    const cleanFilter = selectedFilter.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '').trim().toLowerCase();
    const clusterCat = (c.category || '').toLowerCase();
    const matchesCategory = clusterCat.includes(cleanFilter) || c.articles.some(a => (a.category || '').toLowerCase().includes(cleanFilter));

    return matchesCategory && matchesVerified;
  });

  $: relatedClusters = activeCluster 
    ? clusters.filter(c => c.cluster_id !== activeCluster.cluster_id && (c.category === activeCluster.category || getDistinctFeedCount(c) >= 2)).slice(0, 3)
    : [];

  onMount(() => {
    fetchPerplexityClusters();
  });
</script>

<!-- SCROLL CONTAINER WITH MANDATORY CSS SNAP -->
<div class="flex-1 h-full overflow-y-auto snap-y snap-proximity scroll-smooth bg-gray-950 text-gray-100 p-4 md:p-8">
  <div class="max-w-3xl mx-auto space-y-6">
    
    <!-- Top Header Bar -->
    <div class="flex items-center justify-between pt-2">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-black text-white text-xs shadow-lg">
          P
        </div>
        <h1 class="text-xl font-black tracking-tight text-white">Fil Perplexity (Croisement IA)</h1>
      </div>

      <button 
        on:click={fetchPerplexityClusters} 
        disabled={isLoading}
        class="p-2 bg-gray-900 hover:bg-gray-800 text-gray-300 rounded-full border border-gray-800 transition-all text-xs font-bold flex items-center gap-1.5 px-3"
      >
        <svg class="w-3.5 h-3.5 {isLoading ? 'animate-spin text-cyan-400' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
        <span>Rafraîchir</span>
      </button>
    </div>

    <!-- TAB SELECTOR: STRICT EVENTS vs BROAD THEMES -->
    <div class="bg-gray-900/90 p-1.5 rounded-2xl border border-gray-800 grid grid-cols-2 gap-1.5 shadow-xl">
      <button 
        on:click={() => setMode('events')}
        class="py-3 px-4 rounded-xl text-xs font-extrabold transition-all flex items-center justify-center gap-2 {perplexityMode === 'events' ? 'bg-cyan-500 text-gray-950 shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800/60'}"
      >
        <span>🎯 Événements Précis (Croisement Strict)</span>
      </button>

      <button 
        on:click={() => setMode('themes')}
        class="py-3 px-4 rounded-xl text-xs font-extrabold transition-all flex items-center justify-center gap-2 {perplexityMode === 'themes' ? 'bg-purple-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800/60'}"
      >
        <span>📰 Revues Thématiques (Regroupement Général)</span>
      </button>
    </div>

    <!-- Category Filter Pills & Only Verified Filter Toggle -->
    <div class="space-y-3">
      <div class="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
        {#each filters as filter}
          <button 
            on:click={() => selectedFilter = filter}
            class="px-3.5 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all {selectedFilter === filter ? 'bg-white text-gray-950 shadow-md' : 'bg-gray-900/80 text-gray-400 hover:text-white border border-gray-800'}"
          >
            {filter}
          </button>
        {/each}
      </div>

      <!-- FILTER ONLY VERIFIED SOURCES TOGGLE -->
      <div class="flex items-center justify-between p-3.5 bg-gray-900/60 rounded-2xl border border-gray-800/80">
        <div class="flex items-center gap-2 text-xs">
          <span class="text-emerald-400 font-bold">🛡️ Sources vérifiées uniquement</span>
          <span class="text-gray-500 text-[11px]">(au moins 3 médias distincts)</span>
        </div>
        <input 
          type="checkbox" 
          bind:checked={onlyVerified}
          class="w-4 h-4 accent-emerald-500 rounded cursor-pointer"
        />
      </div>
    </div>

    <!-- CLUSTERS FEED LIST (MAGNETIC TILES) -->
    {#if isLoading}
      <div class="text-center py-16 space-y-3">
        <svg class="w-8 h-8 animate-spin text-cyan-400 mx-auto" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <p class="text-xs text-gray-400">Chargement instantané des tuiles Perplexity...</p>
      </div>
    {:else if filteredClusters.length === 0}
      <div class="bg-gray-900/40 border border-gray-800 rounded-3xl p-8 text-center text-gray-400 space-y-2">
        <p class="text-sm font-semibold">Aucun événement ne correspond aux filtres sélectionnés.</p>
        <p class="text-xs text-gray-500">Essayez de décocher 'Sources vérifiées' ou de changer de catégorie.</p>
      </div>
    {:else}
      <div class="space-y-6">
        {#each filteredClusters as cluster, idx}
          {@const distinctFeeds = getDistinctFeedCount(cluster)}
          {@const isVerified = distinctFeeds >= 3}
          {@const coverImg = getClusterImage(cluster)}
          {@const titleText = getClusterTitle(cluster)}
          {@const teaserText = getTeaserSentence(cluster)}

          <!-- COMPACT TILE CARD (SNAP-START MAGNET) -->
          <div 
            on:click={() => openCluster(cluster)}
            class="snap-start scroll-mt-4 sm:scroll-mt-6 bg-gradient-to-b from-gray-900 to-gray-950 border border-gray-800/80 hover:border-cyan-500/60 rounded-3xl overflow-hidden shadow-2xl transition-all cursor-pointer group space-y-0 relative"
          >
            
            <!-- Cover Image Preview -->
            <div class="w-full h-44 sm:h-52 overflow-hidden relative">
              <ProgressiveImage 
                src={coverImg} 
                fallbackSrc={getCategoryFallbackImage(cluster.category)}
                alt={titleText} 
                imgClass="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div class="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/40 to-transparent pointer-events-none"></div>
              
              <!-- Badges on top of Image -->
              <div class="absolute top-4 left-4 flex items-center gap-2">
                <span class="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-gray-950/90 text-cyan-400 border border-cyan-800/60 backdrop-blur-md">
                  {cluster.category || 'Général'}
                </span>

                {#if isVerified}
                  <span class="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-950/90 text-emerald-400 border border-emerald-700/80 backdrop-blur-md flex items-center gap-1 shadow-lg">
                    <span>🛡️ Vérifié ({distinctFeeds} médias)</span>
                  </span>
                {/if}
              </div>
            </div>

            <!-- Tile Body: Title + Short Teaser -->
            <div class="p-5 sm:p-6 space-y-3">
              
              <h2 class="text-xl sm:text-2xl font-black text-white group-hover:text-cyan-400 transition-colors leading-snug">
                {titleText}
              </h2>

              <p class="text-sm text-gray-300 font-normal leading-relaxed line-clamp-2">
                {teaserText}
              </p>

              <!-- Media badges & Click Prompt -->
              <div class="pt-2 border-t border-gray-900 flex items-center justify-between gap-2">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-[11px] font-bold text-gray-500">Recoupé par :</span>
                  {#each cluster.articles.slice(0, 3) as art}
                    <span class="text-[10px] font-bold bg-gray-900 text-purple-300 px-2 py-0.5 rounded-md border border-gray-800">
                      {getLanguageFlag(art.language)} {art.feed_title || 'RSS'}
                    </span>
                  {/each}
                  {#if cluster.articles.length > 3}
                    <span class="text-[10px] text-gray-500 font-bold">+{cluster.articles.length - 3}</span>
                  {/if}
                </div>

                <span class="text-xs font-bold text-cyan-400 group-hover:underline flex items-center gap-1 shrink-0">
                  <span>Tout voir</span>
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                </span>
              </div>

            </div>

          </div>
        {/each}
      </div>
    {/if}

  </div>
</div>

<!-- FULL DETAIL VIEW / MODAL (PARALLAX HERO HEADER & FULL SUMMARY) -->
{#if activeCluster}
  {@const activeImg = getClusterImage(activeCluster)}
  {@const activeTitle = getClusterTitle(activeCluster)}
  {@const activeFeedsCount = getDistinctFeedCount(activeCluster)}
  {@const activeIsVerified = activeFeedsCount >= 3}
  {@const activeSynth = syntheses[activeCluster.cluster_id] || activeCluster.precomputed_synthesis}

  <div class="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-0 sm:p-4 bg-black/85 backdrop-blur-md overflow-hidden">
    
    <div 
      bind:this={modalContainer}
      class="bg-gray-950 w-full max-w-4xl h-[100dvh] sm:h-auto sm:max-h-[90vh] rounded-none sm:rounded-3xl shadow-2xl overflow-y-auto border-0 sm:border border-gray-800 relative flex flex-col pt-12 sm:pt-0 pb-24 sm:pb-8"
    >
      
      <!-- Sticky Close Button -->
      <button 
        on:click={() => activeCluster = null}
        class="fixed sm:absolute top-3 right-3 sm:top-5 sm:right-5 z-50 p-2.5 sm:p-3 bg-gray-950/90 hover:bg-gray-900 text-white rounded-full border border-gray-700 backdrop-blur-md shadow-2xl transition-all"
        title="Fermer la vue détaillée"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>

      <!-- HERO IMAGE HEADER WITH PARALLAX EFFECT -->
      <div class="w-full h-64 sm:h-80 relative overflow-hidden shrink-0">
        <ProgressiveImage 
          src={activeImg} 
          fallbackSrc={getCategoryFallbackImage(activeCluster.category)}
          alt={activeTitle}
          imgClass="w-full h-full object-cover scale-105 transform transition-transform duration-700"
        />
        <div class="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/60 to-transparent pointer-events-none"></div>

        <!-- Foreground Header Info -->
        <div class="absolute bottom-6 left-6 right-6 space-y-3">
          <div class="flex items-center gap-2">
            <span class="text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full bg-gray-950/90 text-cyan-400 border border-cyan-800/80 backdrop-blur-md">
              {activeCluster.category || 'Général'}
            </span>
            {#if activeIsVerified}
              <span class="text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-950/90 text-emerald-400 border border-emerald-700/80 backdrop-blur-md">
                🛡️ Information Vérifiée ({activeFeedsCount} médias)
              </span>
            {/if}
          </div>

          <h1 class="text-2xl sm:text-3xl md:text-4xl font-black text-white leading-tight drop-shadow-md">
            {activeTitle}
          </h1>
        </div>
      </div>

      <!-- MAIN DETAIL CONTENT -->
      <div class="p-6 sm:p-8 space-y-8 flex-1">
        
        <!-- AI SYNTHESIS & AUDIO PLAYER SECTION -->
        <div class="bg-gray-900/90 border border-gray-800 rounded-3xl p-6 space-y-5 shadow-xl">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-800 pb-4">
            <div class="flex items-center gap-2">
              <span class="text-xs font-black uppercase tracking-wider text-cyan-400">
                ✨ Synthèse Croisée Complète par Mistral AI (en français)
              </span>
            </div>

            {#if activeSynth}
              <button 
                on:click={() => handleListenSummary(activeCluster.cluster_id, activeTitle, activeSynth.summary)}
                disabled={audioLoadingState[activeCluster.cluster_id]}
                class="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-extrabold text-xs rounded-xl shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {#if audioLoadingState[activeCluster.cluster_id]}
                  <svg class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                  <span>Génération audio...</span>
                {:else}
                  <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>
                  <span>Écouter la synthèse (Voix Marie)</span>
                {/if}
              </button>
            {/if}
          </div>

          {#if synthLoading[activeCluster.cluster_id]}
            <div class="flex items-center gap-3 text-xs text-gray-400 py-4 animate-pulse">
              <svg class="w-5 h-5 animate-spin text-cyan-400" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              <span>Traduction et synthèse des sources par Mistral AI...</span>
            </div>
          {:else if activeSynth}
            <div class="space-y-4">
              <div class="text-base text-gray-200 leading-relaxed font-sans space-y-3">
                {@html renderMarkdownHtml(activeSynth.summary)}
              </div>

              {#if (activeSynth.key_takeaways && activeSynth.key_takeaways.length > 0) || (activeSynth.key_points && activeSynth.key_points.length > 0)}
                {@const takeaways = activeSynth.key_takeaways || activeSynth.key_points}
                <div class="space-y-2 pt-4 border-t border-gray-800">
                  <span class="text-xs font-bold text-cyan-400 uppercase tracking-wider block mb-2">Points clés à retenir :</span>
                  <ul class="space-y-2.5 text-xs sm:text-sm text-gray-300">
                    {#each takeaways as point}
                      <li class="flex items-start gap-2.5 bg-gray-950/60 p-2.5 rounded-xl border border-gray-800/80">
                        <span class="text-cyan-400 font-bold text-base mt-0.5">•</span>
                        <span class="leading-snug">{@html renderMarkdownHtml(point)}</span>
                      </li>
                    {/each}
                  </ul>
                </div>
              {/if}
            </div>
          {:else}
            <p class="text-sm text-gray-300 leading-relaxed italic">
              {activeCluster.articles[0].content || activeCluster.articles[0].title}
            </p>
          {/if}
        </div>

        <!-- FULL SOURCES LIST WITH CLICKABLE LINKS -->
        <div class="space-y-4">
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <span>📰 Sources d'information recoupées ({activeCluster.articles.length})</span>
          </h3>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {#each activeCluster.articles as art}
              <a 
                href={art.url} 
                target="_blank" 
                rel="noreferrer"
                class="p-4 bg-gray-900 hover:bg-gray-850 border border-gray-800 hover:border-purple-500/60 rounded-2xl transition-all space-y-2 group block"
              >
                <div class="flex items-center justify-between text-xs">
                  <span class="font-extrabold text-purple-400 flex items-center gap-1">
                    <span>{getLanguageFlag(art.language)}</span>
                    <span>{art.feed_title || 'RSS'}</span>
                  </span>
                  <span class="text-[10px] text-gray-500">{art.published_date}</span>
                </div>
                <h4 class="font-bold text-sm text-gray-200 group-hover:text-cyan-400 transition-colors leading-snug line-clamp-2">
                  {art.title}
                </h4>
                <span class="text-[11px] text-cyan-400 hover:underline flex items-center gap-1 font-semibold pt-1">
                  <span>Lire l'article original</span>
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                </span>
              </a>
            {/each}
          </div>
        </div>

        <!-- RELATED NEWS TILES ("TUILES EN LIEN") -->
        {#if relatedClusters.length > 0}
          <div class="space-y-4 pt-4 border-t border-gray-900">
            <h3 class="text-base font-bold text-white flex items-center gap-2">
              <span>🔗 Actualités en lien sur ce sujet</span>
            </h3>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {#each relatedClusters as rel}
                {@const relImg = getClusterImage(rel)}
                {@const relTitle = getClusterTitle(rel)}
                <div 
                  on:click={() => openCluster(rel)}
                  class="bg-gray-900 hover:bg-gray-850 border border-gray-800 hover:border-cyan-500/60 rounded-2xl p-3.5 transition-all cursor-pointer space-y-2 group"
                >
                  <div class="w-full h-28 rounded-xl overflow-hidden relative">
                    <ProgressiveImage 
                      src={relImg} 
                      fallbackSrc={getCategoryFallbackImage(rel.category)}
                      alt={relTitle} 
                      imgClass="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <span class="text-[10px] font-bold text-cyan-400 uppercase tracking-wider block">{rel.category || 'Général'}</span>
                  <h4 class="font-bold text-xs text-white group-hover:text-cyan-400 line-clamp-2 leading-snug">
                    {relTitle}
                  </h4>
                </div>
              {/each}
            </div>
          </div>
        {/if}

      </div>

    </div>

  </div>
{/if}
