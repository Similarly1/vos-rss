<script>
  import { onMount } from 'svelte';
  import { showFeedManagerModal, feedsList, fetchFeeds, fetchArticles } from '../stores/appState.js';

  let editingFeedId = null;
  let editTitle = '';
  let editCategory = '';
  let editLanguage = 'fr';
  let isLoading = false;
  let message = '';
  let error = '';

  let fileInputRef;
  let isImporting = false;

  onMount(() => {
    fetchFeeds();
  });

  function getLanguageFlag(lang) {
    if (!lang) return "🇫🇷";
    const l = lang.toLowerCase();
    if (l === "en") return "🇬🇧";
    if (l === "de") return "🇩🇪";
    if (l === "es") return "🇪🇸";
    return "🇫🇷";
  }

  function startEdit(feed) {
    editingFeedId = feed.id;
    editTitle = feed.title;
    editCategory = feed.category || 'Général';
    editLanguage = feed.language || 'fr';
  }

  function cancelEdit() {
    editingFeedId = null;
  }

  async function saveEdit(feedId) {
    if (!editTitle.trim()) return;

    isLoading = true;
    error = '';
    message = '';

    try {
      const res = await fetch(`/api/feeds/${feedId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle,
          category: editCategory,
          language: editLanguage,
          is_full_text: true
        })
      });

      if (res.ok) {
        message = "Flux mis à jour avec succès !";
        editingFeedId = null;
        await fetchFeeds();
        await fetchArticles();
      } else {
        error = "Erreur lors de la modification du flux.";
      }
    } catch (err) {
      error = "Erreur de communication avec le serveur.";
    } finally {
      isLoading = false;
    }
  }

  async function deleteFeed(feed) {
    if (!confirm(`Voulez-vous vraiment supprimer le flux "${feed.title}" et tous ses articles associés ?`)) {
      return;
    }

    isLoading = true;
    error = '';
    message = '';

    try {
      const res = await fetch(`/api/feeds/${feed.id}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        message = `Flux "${feed.title}" supprimé avec succès.`;
        await fetchFeeds();
        await fetchArticles();
      } else {
        error = "Échec de la suppression.";
      }
    } catch (err) {
      error = "Erreur de communication avec le serveur.";
    } finally {
      isLoading = false;
    }
  }

  function exportOpml() {
    window.open('/api/feeds/export/opml', '_blank');
  }

  function triggerImport() {
    if (fileInputRef) {
      fileInputRef.click();
    }
  }

  async function handleFileSelected(e) {
    const file = e.target.files[0];
    if (!file) return;

    isImporting = true;
    message = '';
    error = '';

    const reader = new FileReader();
    reader.onload = async (evt) => {
      const content = evt.target.result;
      try {
        const res = await fetch('/api/feeds/import/opml', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          message = `Importation réussie ! ${data.imported_count} flux ajoutés/mis à jour.`;
          await fetchFeeds();
          await fetchArticles();
        } else {
          error = data.detail || "Erreur lors de l'importation du fichier OPML.";
        }
      } catch (err) {
        error = "Erreur réseau lors de l'importation.";
      } finally {
        isImporting = false;
        e.target.value = '';
      }
    };
    reader.readAsText(file);
  }

  function closeModal() {
    $showFeedManagerModal = false;
  }

  $: groupedFeeds = $feedsList.reduce((acc, feed) => {
    const cat = feed.category || 'Général';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(feed);
    return acc;
  }, {});
</script>

<input 
  type="file" 
  accept=".opml,.xml,.json" 
  bind:this={fileInputRef} 
  on:change={handleFileSelected} 
  class="hidden" 
/>

{#if $showFeedManagerModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-white dark:bg-dark-card w-full max-w-2xl rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-gray-800">
      
      <!-- Header -->
      <div class="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-dark-bg/50">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-primary-50 dark:bg-primary-900/50 text-primary-500 rounded-2xl">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-bold">Gestion des Flux RSS ({$feedsList.length})</h3>
            <p class="text-xs text-gray-500">Importation, exportation OPML, langues et catégories</p>
          </div>
        </div>

        <button on:click={closeModal} class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- EXPORT & IMPORT ACTION BAR -->
      <div class="px-6 pt-4 pb-2 flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50/30 dark:bg-dark-bg/30">
        <span class="text-xs font-bold text-gray-500">Sauvegarde & Migration OPML :</span>
        
        <div class="flex items-center gap-2">
          <!-- EXPORT BUTTON -->
          <button 
            on:click={exportOpml}
            class="px-3.5 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-bold text-xs rounded-xl transition-all flex items-center gap-1.5"
            title="Exporter mes abonnements au format universel OPML 2.0"
          >
            <svg class="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            <span>Exporter mes flux (OPML)</span>
          </button>

          <!-- IMPORT BUTTON -->
          <button 
            on:click={triggerImport}
            disabled={isImporting}
            class="px-3.5 py-1.5 bg-primary-500 hover:bg-primary-600 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
            title="Importer des flux depuis un fichier OPML ou JSON"
          >
            {#if isImporting}
              <span>Importation en cours...</span>
            {:else}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
              <span>Importer des flux (OPML / JSON)</span>
            {/if}
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
        
        {#if message}
          <div class="p-3 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 rounded-xl text-xs font-medium">
            {message}
          </div>
        {/if}

        {#if error}
          <div class="p-3 bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 rounded-xl text-xs font-medium">
            {error}
          </div>
        {/if}

        {#if $feedsList.length === 0}
          <div class="text-center py-8 text-gray-400 text-sm">
            Aucun flux RSS enregistré. Utilisez le bouton ci-dessus pour importer votre fichier OPML !
          </div>
        {:else}
          {#each Object.entries(groupedFeeds) as [categoryName, categoryFeeds]}
            <div class="space-y-3">
              <div class="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
                <svg class="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                <span>Dossier : {categoryName} ({categoryFeeds.length})</span>
              </div>

              <div class="space-y-2">
                {#each categoryFeeds as feed}
                  <div class="bg-gray-50 dark:bg-dark-bg p-4 rounded-2xl border border-gray-100 dark:border-gray-800 transition-all">
                    
                    {#if editingFeedId === feed.id}
                      <!-- EDIT MODE -->
                      <div class="space-y-3">
                        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          <input 
                            type="text" 
                            bind:value={editTitle}
                            placeholder="Nom du flux" 
                            class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-primary-500"
                          />
                          <input 
                            type="text" 
                            bind:value={editCategory}
                            placeholder="Dossier" 
                            class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-primary-500"
                          />
                          <select 
                            bind:value={editLanguage}
                            class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="fr">🇫🇷 Français</option>
                            <option value="en">🇬🇧 Anglais</option>
                            <option value="de">🇩🇪 Allemand</option>
                            <option value="es">🇪🇸 Espagnol</option>
                          </select>
                        </div>

                        <div class="flex justify-end gap-2">
                          <button 
                            on:click={cancelEdit}
                            class="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 rounded-lg"
                          >
                            Annuler
                          </button>
                          <button 
                            on:click={() => saveEdit(feed.id)}
                            disabled={isLoading}
                            class="px-4 py-1.5 text-xs bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg shadow-sm"
                          >
                            Enregistrer
                          </button>
                        </div>
                      </div>
                    {:else}
                      <!-- NORMAL MODE -->
                      <div class="flex items-center justify-between gap-4">
                        <div class="min-w-0 space-y-1">
                          <div class="flex items-center gap-2">
                            <span class="text-base">{getLanguageFlag(feed.language)}</span>
                            <h4 class="font-bold text-sm truncate text-gray-800 dark:text-gray-200">{feed.title}</h4>
                            <span class="text-[10px] bg-cyan-50 dark:bg-cyan-950/40 text-cyan-600 dark:text-cyan-400 px-2 py-0.5 rounded-md font-bold">
                              Enrichi par Web Scraper (Article Complet)
                            </span>
                          </div>
                          <p class="text-xs text-gray-400 truncate">{feed.url}</p>
                        </div>

                        <div class="flex items-center gap-2 shrink-0">
                          <button 
                            on:click={() => startEdit(feed)}
                            class="p-2 text-gray-400 hover:text-primary-500 hover:bg-white dark:hover:bg-dark-card rounded-xl transition-all"
                            title="Renommer, changer la langue ou de dossier"
                          >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                          </button>

                          <button 
                            on:click={() => deleteFeed(feed)}
                            class="p-2 text-gray-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition-all"
                            title="Supprimer ce flux"
                          >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                          </button>
                        </div>
                      </div>
                    {/if}

                  </div>
                {/each}
              </div>
            </div>
          {/each}
        {/if}

      </div>

      <!-- Footer -->
      <div class="p-4 bg-gray-50/50 dark:bg-dark-bg/50 border-t border-gray-100 dark:border-gray-800 flex justify-end">
        <button 
          type="button" 
          on:click={closeModal}
          class="px-5 py-2.5 text-xs font-semibold text-white bg-primary-500 hover:bg-primary-600 rounded-xl shadow-sm transition-all"
        >
          Fermer
        </button>
      </div>

    </div>
  </div>
{/if}
