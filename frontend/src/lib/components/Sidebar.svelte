<script>
  import { currentView, showAddFeedModal, showFeedManagerModal, visibleNavTabs, unreadNotificationsCount, showNotifications, navTabsOrder, defaultLandingTab, saveNavPreferences } from '../stores/appState.js';

  let isEditMode = false;

  const ALL_TABS = {
    podcast: { id: 'podcast', view: 'podcast', icon: '🎙️', label: 'Studio Podcast', extra: '<span class="text-[9px] bg-purple-500 text-white font-black px-1.5 py-0.5 rounded-full uppercase">Émission</span>', activeClass: 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md' },
    perplexity: { id: 'perplexity', view: 'perplexity', icon: '⚡', label: 'Fil Perplexity', activeClass: 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-500' },
    feeds: { id: 'feeds', view: 'articles', icon: '📰', label: 'Articles', activeClass: 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' },
    synthesis: { id: 'synthesis', view: 'synthesis', icon: '🧪', label: 'Synthèses IA', activeClass: 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' },
    discover: { id: 'discover', view: 'discover', icon: '🧭', label: 'Catalogue', activeClass: 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' },
    stats: { id: 'stats', view: 'stats', icon: '📊', label: 'Statistiques', activeClass: 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' }
  };

  $: orderedTabs = ($navTabsOrder.length > 0 ? $navTabsOrder : ['podcast', 'perplexity', 'feeds', 'synthesis', 'discover', 'stats'])
    .filter(id => $visibleNavTabs.includes(id))
    .map(id => ALL_TABS[id])
    .filter(Boolean);

  let draggedIdx = null;

  function handleDragStart(e, idx) {
    if (!isEditMode) return;
    draggedIdx = idx;
    e.dataTransfer.effectAllowed = 'move';
  }

  function handleDrop(e, idx) {
    e.preventDefault();
    if (!isEditMode || draggedIdx === null || draggedIdx === idx) return;
    let newOrder = [...orderedTabs.map(t => t.id)];
    const [movedItem] = newOrder.splice(draggedIdx, 1);
    newOrder.splice(idx, 0, movedItem);
    $navTabsOrder = newOrder;
    saveNavPreferences();
    draggedIdx = null;
  }

  function toggleDefaultTab(view) {
    if (!isEditMode) return;
    $defaultLandingTab = view;
    saveNavPreferences();
  }
</script>

<aside class="w-64 h-full bg-white dark:bg-dark-card border-r border-gray-200 dark:border-gray-800 flex flex-col p-4">
  <div class="text-2xl font-bold text-primary-500 mb-6 flex items-center gap-2">
    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
    Vos
  </div>
  
  <div class="space-y-2 mb-6">
    <button 
      on:click={() => $showAddFeedModal = true}
      class="w-full bg-primary-500 hover:bg-primary-600 text-white font-medium py-2.5 px-4 rounded-xl shadow-sm transition-all flex items-center justify-center gap-2 text-xs"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
      Ajouter un flux RSS
    </button>

    <button 
      on:click={() => $currentView = 'feeds'}
      class="w-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium py-2 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-xs"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
      Mes Flux & Audit
    </button>
  </div>

  <div class="flex items-center justify-between px-2 mb-2">
    <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Menu</span>
    <button on:click={() => isEditMode = !isEditMode} class="text-xs text-primary-500 hover:underline">
      {isEditMode ? 'Terminer' : 'Modifier'}
    </button>
  </div>

  <nav class="space-y-1.5 flex-1 overflow-y-auto overflow-x-hidden p-1 -m-1">
    {#each orderedTabs as tab, idx}
      <div
        draggable={isEditMode}
        on:dragstart={(e) => handleDragStart(e, idx)}
        on:dragover|preventDefault
        on:drop={(e) => handleDrop(e, idx)}
        class="flex items-center gap-1 group {isEditMode ? 'cursor-move' : ''}"
      >
        {#if isEditMode}
          <div class="text-gray-400 opacity-50 cursor-move">⋮⋮</div>
        {/if}
        <button 
          class="flex-1 text-left px-3 py-2.5 rounded-xl flex items-center gap-2.5 text-xs font-semibold 
                 {$currentView === tab.view ? tab.activeClass : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}
                 {isEditMode ? 'border border-dashed border-gray-300 dark:border-gray-700' : ''}" 
          on:click={() => !isEditMode && ($currentView = tab.view)}
        >
          <span>{tab.icon}</span>
          <span class="flex-1">{tab.label}</span>
          {#if tab.extra}
            {@html tab.extra}
          {/if}
          
          {#if isEditMode}
            <button 
              on:click|stopPropagation={() => toggleDefaultTab(tab.view)}
              class="ml-auto text-lg hover:scale-125 transition-transform {$defaultLandingTab === tab.view ? 'text-yellow-400' : 'text-gray-300 grayscale opacity-30 hover:opacity-100 hover:grayscale-0'}"
              title="Définir comme page d'accueil par défaut"
            >
              ⭐
            </button>
          {/if}
        </button>
      </div>
    {/each}
  </nav>

  <div class="mt-auto pt-4 border-t border-gray-200 dark:border-gray-800">
    {#if $visibleNavTabs.includes('settings')}
    <button 
      class="w-full text-left px-4 py-2 rounded-lg {$currentView === 'settings' ? 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'} flex items-center gap-2 text-xs"
      on:click={() => $currentView = 'settings'}
    >
      <svg class="w-5 h-5 {$currentView === 'settings' ? 'text-primary-500' : 'text-gray-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
      </svg>
      Paramètres
    </button>
    {/if}

    <button 
      class="w-full mt-2 text-left px-4 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 flex items-center justify-between text-xs transition-colors"
      on:click={() => $showNotifications = true}
    >
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
        Notifications
      </div>
      {#if $unreadNotificationsCount > 0}
        <span class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">{$unreadNotificationsCount}</span>
      {/if}
    </button>
  </div>
</aside>
