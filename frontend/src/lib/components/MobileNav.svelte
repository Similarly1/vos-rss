<script>
  import { currentView, visibleNavTabs, unreadNotificationsCount, showNotifications, navTabsOrder, defaultLandingTab, saveNavPreferences } from '../stores/appState.js';

  let isEditMode = false;

  const ALL_TABS = {
    podcast: { id: 'podcast', view: 'podcast', iconPath: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z', label: 'Podcast', activeClass: 'text-purple-400 font-semibold' },
    perplexity: { id: 'perplexity', view: 'perplexity', iconPath: 'M13 10V3L4 14h7v7l9-11h-7z', label: 'Fil', activeClass: 'text-cyan-400 font-semibold' },
    feeds: { id: 'feeds', view: 'articles', iconPath: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10', label: 'Articles', activeClass: 'text-primary-400 font-semibold' },
    discover: { id: 'discover', view: 'discover', iconPath: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z', label: 'Catalogue', activeClass: 'text-indigo-400 font-semibold' },
    stats: { id: 'stats', view: 'stats', iconPath: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', label: 'Stats', activeClass: 'text-primary-400 font-semibold' },
    settings: { id: 'settings', view: 'settings', iconPath: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z', label: 'Réglages', activeClass: 'text-primary-400 font-semibold' }
  };

  // We only show up to 4 or 5 items on mobile typically, but let's just render what's available
  $: orderedTabs = ($navTabsOrder.length > 0 ? $navTabsOrder : ['podcast', 'perplexity', 'feeds', 'discover', 'stats', 'settings'])
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

<nav class="fixed bottom-0 left-0 right-0 bg-gray-950 border-t border-gray-800 z-40 pb-safe">
  {#if isEditMode}
  <div class="absolute -top-10 left-0 right-0 bg-gray-900 text-white text-xs py-1.5 flex justify-center items-center gap-2 border-t border-gray-800 shadow-lg">
    Glissez pour réorganiser 
    <button on:click={() => isEditMode = false} class="bg-primary-500 px-3 py-1 rounded-full font-bold ml-4 text-white">OK</button>
  </div>
  {/if}

  <div class="flex justify-around items-center h-16 w-full overflow-x-auto">
    
    {#each orderedTabs as tab, idx}
      <button 
        draggable={isEditMode}
        on:dragstart={(e) => handleDragStart(e, idx)}
        on:dragover|preventDefault
        on:drop={(e) => handleDrop(e, idx)}
        class="relative flex flex-col items-center justify-center min-w-[60px] h-full {$currentView === tab.view ? tab.activeClass : 'text-gray-400'} {isEditMode ? 'border border-dashed border-gray-700 m-1 rounded bg-gray-800/50' : ''}" 
        on:click={() => { if (!isEditMode) $currentView = tab.view; }}
      >
        <svg class="w-5 h-5 mb-1 {isEditMode && draggedIdx === idx ? 'opacity-20' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <!-- Split paths by space to support multiple paths for settings icon -->
          {#each tab.iconPath.split(' M') as path, i}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{i > 0 ? 'M' + path : path}"></path>
          {/each}
        </svg>
        <span class="text-[10px]">{tab.label}</span>
        
        {#if isEditMode}
          <span 
            role="button"
            tabindex="0"
            on:click|stopPropagation={() => toggleDefaultTab(tab.view)}
            on:keydown|stopPropagation={(e) => e.key === 'Enter' && toggleDefaultTab(tab.view)}
            class="absolute top-1 right-1 text-xs z-10 cursor-pointer {$defaultLandingTab === tab.view ? 'text-yellow-400' : 'text-gray-500 opacity-50'}"
          >
            ⭐
          </span>
        {/if}
      </button>
    {/each}

    <button class="relative flex flex-col items-center justify-center min-w-[60px] h-full text-gray-400" on:click={() => $showNotifications = true} on:contextmenu|preventDefault={() => isEditMode = !isEditMode}>
      <svg class="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
      <span class="text-[10px]">Notifs</span>
      {#if $unreadNotificationsCount > 0}
        <span class="absolute top-1 right-2 bg-red-500 text-white text-[9px] font-bold px-1 rounded-full">{$unreadNotificationsCount}</span>
      {/if}
    </button>
    
    {#if !isEditMode}
    <button class="flex flex-col items-center justify-center min-w-[50px] h-full text-gray-500" on:click={() => isEditMode = true}>
      <svg class="w-4 h-4 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
      <span class="text-[9px]">Modifier</span>
    </button>
    {/if}

  </div>
</nav>

<style>
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom);
  }
</style>
