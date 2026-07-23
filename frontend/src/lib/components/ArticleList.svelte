<script>
  import { onMount } from 'svelte';
  import { selectedItemId, articlesList, fetchArticles, showAddFeedModal } from '../stores/appState.js';

  onMount(() => {
    fetchArticles();
  });
</script>

<div class="w-full lg:w-96 h-full bg-gray-50 dark:bg-dark-bg border-r border-gray-200 dark:border-gray-800 overflow-y-auto flex flex-col">
  <div class="p-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-dark-card sticky top-0 z-10 flex justify-between items-center">
    <h2 class="text-xl font-bold">À lire ({$articlesList.length})</h2>
    <button 
      on:click={fetchArticles}
      class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      title="Rafraîchir"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
      </svg>
    </button>
  </div>
  
  <div class="flex-1 overflow-y-auto p-2 space-y-2">
    {#if $articlesList.length === 0}
      <div class="p-6 text-center text-sm text-gray-400 dark:text-dark-muted space-y-3">
        <p>Aucun article disponible pour le moment.</p>
        <button 
          on:click={() => $showAddFeedModal = true}
          class="text-xs bg-primary-50 dark:bg-primary-900/50 text-primary-500 font-semibold px-3 py-2 rounded-xl border border-primary-200 dark:border-primary-800 hover:bg-primary-100 transition-colors"
        >
          + Ajouter votre premier flux RSS
        </button>
      </div>
    {:else}
      {#each $articlesList as item}
        <button 
          class="w-full text-left p-4 rounded-xl transition-all {$selectedItemId === item.id ? 'bg-white dark:bg-dark-card shadow-sm border-l-4 border-primary-500' : 'hover:bg-white dark:hover:bg-dark-card border-l-4 border-transparent'}"
          on:click={() => $selectedItemId = item.id}
        >
          <div class="text-xs text-gray-500 dark:text-dark-muted mb-1 flex justify-between gap-2">
            <span class="truncate font-medium text-primary-500">{item.feed_title || 'RSS'}</span>
            <span class="shrink-0">{item.published_date ? new Date(item.published_date).toLocaleDateString('fr-FR') : ''}</span>
          </div>
          <h3 class="font-semibold text-sm line-clamp-2 leading-tight">{item.title}</h3>
        </button>
      {/each}
    {/if}
  </div>
</div>
