<script>
  import { onMount } from 'svelte';
  import { currentView, isMobile, selectedItemId, setupAutoRefresh } from './lib/stores/appState.js';
  import Sidebar from './lib/components/Sidebar.svelte';
  import ArticleList from './lib/components/ArticleList.svelte';
  import ReaderView from './lib/components/ReaderView.svelte';
  import AudioPlayer from './lib/components/AudioPlayer.svelte';
  import MobileNav from './lib/components/MobileNav.svelte';
  import DiscoverView from './lib/components/DiscoverView.svelte';
  import SynthesisView from './lib/components/SynthesisView.svelte';
  import PerplexityFeedView from './lib/components/PerplexityFeedView.svelte';
  import PodcastStudioView from './lib/components/PodcastStudioView.svelte';
  import SettingsModal from './lib/components/SettingsModal.svelte';
  import AddFeedModal from './lib/components/AddFeedModal.svelte';
  import FeedManagerModal from './lib/components/FeedManagerModal.svelte';

  onMount(() => {
    setupAutoRefresh();

    const checkMobile = () => {
      $isMobile = window.innerWidth < 1024;
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  });
</script>

<main class="h-screen w-full flex flex-col overflow-hidden bg-gray-50 dark:bg-dark-bg text-gray-900 dark:text-dark-text">
  
  <div class="flex-1 flex overflow-hidden">
    {#if !$isMobile}
      <!-- Desktop Layout: 3 Columns / Views -->
      <Sidebar />
      
      {#if $currentView === 'podcast'}
        <PodcastStudioView />
      {:else if $currentView === 'perplexity'}
        <PerplexityFeedView />
      {:else if $currentView === 'discover'}
        <DiscoverView />
      {:else if $currentView === 'synthesis'}
        <SynthesisView />
      {:else}
        <ArticleList />
        <ReaderView />
      {/if}
      
    {:else}
      <!-- Mobile Layout: Dynamic 1 Column -->
      {#if $currentView === 'podcast'}
        <PodcastStudioView />
      {:else if $currentView === 'perplexity'}
        <PerplexityFeedView />
      {:else if $currentView === 'discover'}
        <DiscoverView />
      {:else if $currentView === 'synthesis'}
        <SynthesisView />
      {:else}
        <div class="flex-1 w-full flex flex-col h-full overflow-hidden pb-16">
          {#if $selectedItemId}
            <ReaderView />
          {:else}
            <ArticleList />
          {/if}
        </div>
      {/if}
    {/if}
  </div>

  <!-- Audio Player (Bottom Desktop / Floating Mobile) -->
  <div class="{$isMobile ? 'fixed bottom-16 left-0 right-0 z-50' : 'w-full z-50 relative'}">
    <AudioPlayer />
  </div>

  <!-- Mobile Bottom Nav -->
  {#if $isMobile}
    <MobileNav />
  {/if}
  
  <!-- Modals -->
  <SettingsModal />
  <AddFeedModal />
  <FeedManagerModal />

</main>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
  }
</style>
