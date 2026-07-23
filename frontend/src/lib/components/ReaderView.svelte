<script>
  import { selectedItemId, articlesList, mistralApiKey, selectedMistralModel, showSettingsModal } from '../stores/appState.js';
  import { playTrack, selectedVoice, sanitizeTextForSpeech } from '../stores/audioStore.js';

  $: selectedArticle = $articlesList.find(a => a.id === $selectedItemId);

  // Summarization states keyed by article ID
  let summaries = {};
  let loadingState = {};
  let errorState = {};
  let audioLoadingState = {};

  async function generateSummary(articleId) {
    if (!articleId) return;

    if (!$mistralApiKey) {
      errorState[articleId] = "Veuillez d'abord configurer votre clé API Mistral dans les Paramètres.";
      return;
    }

    loadingState[articleId] = true;
    errorState[articleId] = null;
    loadingState = { ...loadingState };
    errorState = { ...errorState };

    try {
      const res = await fetch(`/api/articles/${articleId}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: $mistralApiKey,
          model: $selectedMistralModel
        })
      });

      const result = await res.json();

      if (res.ok && result.data) {
        summaries[articleId] = result.data;
        summaries = { ...summaries };
      } else {
        errorState[articleId] = result.detail || "Échec de la génération du résumé par Mistral AI.";
        errorState = { ...errorState };
      }
    } catch (err) {
      errorState[articleId] = "Erreur de connexion avec le serveur backend.";
      errorState = { ...errorState };
    } finally {
      loadingState[articleId] = false;
      loadingState = { ...loadingState };
    }
  }

  async function handleListen(title, summaryText, feedTitle = 'Vos Podcast') {
    if (!selectedArticle) return;

    audioLoadingState[selectedArticle.id] = true;
    audioLoadingState = { ...audioLoadingState };

    const cleanText = sanitizeTextForSpeech(summaryText || selectedArticle.title);
    const textToRead = `${title}. ${cleanText.slice(0, 300)}`;

    try {
      const res = await fetch('/api/audio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToRead,
          voice: $selectedVoice,
          api_key: $mistralApiKey
        })
      });

      const result = await res.json();

      if (res.ok && result.audio_url) {
        playTrack(title, result.audio_url, feedTitle);
      } else {
        alert(result.detail || "Échec de la génération audio.");
      }
    } catch (err) {
      alert("Erreur de connexion avec le service audio.");
    } finally {
      audioLoadingState[selectedArticle.id] = false;
      audioLoadingState = { ...audioLoadingState };
    }
  }

  let copied = false;
  function copySummary(summaryObj) {
    if (!summaryObj) return;
    const text = `${summaryObj.summary}\n\nPoints clés :\n` + (summaryObj.key_points || []).map(p => `• ${p}`).join('\n');
    navigator.clipboard.writeText(text);
    copied = true;
    setTimeout(() => copied = false, 2000);
  }
</script>

<div class="flex-1 h-full bg-white dark:bg-dark-card overflow-y-auto">
  {#if selectedArticle}
    <div class="max-w-3xl mx-auto p-4 sm:p-6 md:p-10 space-y-6 md:space-y-8">
      
      <!-- Mobile Back Button -->
      <button 
        on:click={() => $selectedItemId = null}
        class="lg:hidden px-3.5 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-bold text-xs rounded-xl flex items-center gap-2 border border-gray-200 dark:border-gray-700 shadow-sm"
      >
        <svg class="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
        <span>← Retour à la liste des articles</span>
      </button>

      <!-- Article Header -->
      <div class="border-b border-gray-100 dark:border-gray-800 pb-6">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-primary-500 font-semibold text-xs uppercase tracking-wider">{selectedArticle.feed_title || 'Flux RSS'}</span>
          <span class="text-gray-300 dark:text-gray-700">•</span>
          <span class="text-xs text-gray-400">{selectedArticle.published_date ? new Date(selectedArticle.published_date).toLocaleString('fr-FR') : ''}</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-extrabold leading-tight">{selectedArticle.title}</h1>
        
        <div class="mt-4 flex items-center justify-between">
          <a 
            href={selectedArticle.url} 
            target="_blank" 
            rel="noreferrer"
            class="text-xs text-gray-500 hover:text-primary-500 hover:underline flex items-center gap-1 font-medium"
          >
            <span>Article original sur la source</span>
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
            </svg>
          </a>
        </div>
      </div>

      <!-- VISUAL AI SUMMARY SECTION -->
      <div class="relative overflow-hidden rounded-3xl border border-primary-500/20 bg-gradient-to-br from-primary-500/5 via-indigo-500/5 to-purple-500/5 p-6 shadow-sm">
        
        {#if summaries[selectedArticle.id]}
          <!-- SUMMARY READY CARD -->
          <div class="space-y-4">
            <div class="flex items-center justify-between flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <div class="p-1.5 bg-primary-500 text-white rounded-xl shadow-sm">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-base text-gray-900 dark:text-gray-100">Synthèse IA (Mistral)</h3>
              </div>

              <div class="flex items-center gap-2">
                <button 
                  on:click={() => copySummary(summaries[selectedArticle.id])}
                  class="px-3 py-1.5 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-white/60 dark:hover:bg-gray-800/60 rounded-xl transition-all flex items-center gap-1 border border-gray-200/50 dark:border-gray-700/50"
                  title="Copier le résumé"
                >
                  {#if copied}
                    <span class="text-emerald-500 font-bold">Copié !</span>
                  {:else}
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    <span>Copier</span>
                  {/if}
                </button>

                <button 
                  on:click={() => handleListen(selectedArticle.title, summaries[selectedArticle.id].summary, selectedArticle.feed_title)}
                  disabled={audioLoadingState[selectedArticle.id]}
                  class="px-3.5 py-1.5 bg-primary-500 hover:bg-primary-600 text-white text-xs font-bold rounded-xl shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  {#if audioLoadingState[selectedArticle.id]}
                    <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                    <span>Génération audio...</span>
                  {:else}
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>
                    <span>Écouter le résumé</span>
                  {/if}
                </button>
              </div>
            </div>

            <!-- Summary Paragraph -->
            <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed font-normal">
              {summaries[selectedArticle.id].summary}
            </p>

            <!-- Key Points Bullet List -->
            {#if summaries[selectedArticle.id].key_points && summaries[selectedArticle.id].key_points.length > 0}
              <div class="space-y-2 pt-2 border-t border-primary-500/10">
                <span class="text-xs font-bold text-gray-400 uppercase tracking-wider">Points clés à retenir :</span>
                <ul class="space-y-1.5 text-xs text-gray-600 dark:text-gray-300">
                  {#each summaries[selectedArticle.id].key_points as point}
                    <li class="flex items-start gap-2">
                      <span class="text-primary-500 font-bold mt-0.5">•</span>
                      <span>{point}</span>
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

          </div>
        {:else}
          <!-- INITIAL GENERATE BUTTON -->
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <h3 class="font-bold text-sm text-gray-900 dark:text-gray-100">Synthèse IA Instantanée</h3>
                <span class="text-[10px] bg-primary-100 text-primary-700 dark:bg-primary-950/60 dark:text-primary-400 px-2 py-0.5 rounded-full font-bold">Mistral AI</span>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400">Générez un résumé structuré en 3 points clés avant l'écoute du podcast.</p>
            </div>

            <button 
              on:click={() => generateSummary(selectedArticle.id)}
              disabled={loadingState[selectedArticle.id]}
              class="px-4 py-2 bg-gradient-to-r from-primary-500 to-indigo-600 hover:from-primary-600 hover:to-indigo-700 text-white font-bold text-xs rounded-2xl shadow-md transition-all flex items-center gap-2 shrink-0 disabled:opacity-50"
            >
              {#if loadingState[selectedArticle.id]}
                <svg class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                <span>Analyse par Mistral...</span>
              {:else}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                </svg>
                <span>Résumer cet article</span>
              {/if}
            </button>
          </div>

          {#if errorState[selectedArticle.id]}
            <p class="text-xs text-rose-500 dark:text-rose-400 font-medium mt-3">
              {errorState[selectedArticle.id]}
              {#if errorState[selectedArticle.id].includes("Clé API")}
                <button on:click={() => $showSettingsModal = true} class="underline font-bold ml-1">Ouvrir les Réglages</button>
              {/if}
            </p>
          {/if}

        {/if}

      </div>

      <!-- Article Body Content -->
      <div class="prose dark:prose-invert max-w-none text-base leading-relaxed space-y-4 font-serif">
        {#if selectedArticle.content}
          {@html selectedArticle.content}
        {:else}
          <p class="text-gray-400 italic">Aucun contenu disponible pour cet article.</p>
        {/if}
      </div>

    </div>
  {:else}
    <div class="h-full flex flex-col items-center justify-center text-gray-400 space-y-3 p-6 text-center">
      <svg class="w-12 h-12 stroke-1 text-gray-300 dark:text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
      </svg>
      <p class="text-sm">Sélectionnez un article dans la liste pour le lire ou générer un résumé par l'IA.</p>
    </div>
  {/if}
</div>
