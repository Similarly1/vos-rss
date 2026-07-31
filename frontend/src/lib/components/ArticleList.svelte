<script>
  import { onMount } from 'svelte';
  import { selectedItemId, articlesList, fetchArticles, triggerFeedRefresh, isRefreshingFeeds, showAddFeedModal, subscribedMediaCredentialsList, hidePaywalledWithoutCookie } from '../stores/appState.js';

  $: filteredArticles = $articlesList.filter(item => {
    if ($hidePaywalledWithoutCookie && item.is_paywalled) {
      const hasCookie = $subscribedMediaCredentialsList.some(cred => item.url && item.url.includes(cred.domain));
      if (!hasCookie) return false;
    }
    return true;
  });

  onMount(() => {
    fetchArticles();
  });
</script>

<div class="w-full lg:w-96 h-full bg-background border-r border-gray-200 dark:border-gray-800 overflow-y-auto flex flex-col">
  <div class="p-4 border-b border-gray-200 dark:border-gray-800 bg-card text-card-foreground sticky top-0 z-10 flex justify-between items-center">
    <h2 class="text-xl font-bold">À lire ({filteredArticles.length})</h2>
    
    <button 
      on:click={triggerFeedRefresh}
      disabled={$isRefreshingFeeds}
      class="p-2 text-gray-500 hover:text-primary dark:hover:text-primary-400 rounded-xl hover:bg-gray-100 dark:hover:bg-card transition-all flex items-center gap-1 text-xs font-semibold disabled:opacity-50"
      title="Rafraîchir les flux RSS"
    >
      <svg class="w-4 h-4 {$isRefreshingFeeds ? 'animate-spin text-primary' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
      </svg>
      <span>{$isRefreshingFeeds ? 'Mise à jour...' : 'Actualiser'}</span>
    </button>
  </div>
  
  <div class="flex-1 overflow-y-auto p-2 space-y-2">
    {#if filteredArticles.length === 0}
      <div class="p-6 text-center text-sm text-gray-400 dark:text-dark-muted space-y-3">
        <p>Aucun article disponible pour le moment.</p>
        <button 
          on:click={() => $showAddFeedModal = true}
          class="text-xs bg-primary-50 dark:bg-primary-900/50 text-primary font-semibold px-3 py-2 rounded-xl border border-primary-200 dark:border-primary-800 hover:bg-primary-100 transition-colors"
        >
          + Ajouter votre premier flux RSS
        </button>
      </div>
    {:else}
      {#each filteredArticles as item}
        <button 
          class="w-full text-left p-4 rounded-xl transition-all {$selectedItemId === item.id ? 'bg-card text-card-foreground shadow-sm border-l-4 border-primary-500' : 'hover:bg-white dark:hover:bg-dark-card border-l-4 border-transparent'}"
          on:click={() => $selectedItemId = item.id}
        >
          <div class="text-xs text-gray-500 dark:text-dark-muted mb-1 flex justify-between gap-2">
            <span class="truncate font-medium text-primary">{item.feed_title || 'RSS'}</span>
            <div class="flex items-center gap-2">
              {#if item.is_paywalled !== undefined}
                {#if item.is_paywalled}
                  {#if $subscribedMediaCredentialsList.some(cred => item.url && item.url.includes(cred.domain))}
                    <span class="px-1.5 py-0.5 bg-primary/10 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 text-[10px] font-bold rounded" title="Débloqué avec votre abonnement">🔓 Intégral</span>
                  {:else}
                    <span class="px-1.5 py-0.5 bg-amber-50 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300 text-[10px] font-bold rounded" title="Réservé aux abonnés">🔒 Réservé</span>
                  {/if}
                {:else}
                  <span class="px-1.5 py-0.5 bg-primary/10 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300 text-[10px] font-bold rounded">🔓 Gratuit</span>
                {/if}
              {/if}
              <span class="shrink-0">{item.published_date ? new Date(item.published_date).toLocaleDateString('fr-FR') : ''}</span>
            </div>
          </div>
          <h3 class="font-semibold text-sm line-clamp-2 leading-tight">{item.title}</h3>
        </button>
      {/each}
    {/if}
  </div>
</div>
