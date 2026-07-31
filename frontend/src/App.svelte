<script>
  import { onMount } from 'svelte';
  import { fade, fly, slide, scale, blur } from 'svelte/transition';
  import { currentView, isMobile, selectedItemId, setupAutoRefresh, showNotifications, showMediaCredentialsModal, transitionType, transitionDuration, mainNavDirection } from './lib/stores/appState.js';
  import Sidebar from './lib/components/Sidebar.svelte';
  import ArticleList from './lib/components/ArticleList.svelte';
  import ReaderView from './lib/components/ReaderView.svelte';
  import AudioPlayer from './lib/components/AudioPlayer.svelte';
  import MobileNav from './lib/components/MobileNav.svelte';
  import DiscoverView from './lib/components/DiscoverView.svelte';
  import SynthesisView from './lib/components/SynthesisView.svelte';
  import ExplorerView from './lib/components/ExplorerView.svelte';
  import PodcastStudioView from './lib/components/PodcastStudioView.svelte';
  import SettingsView from './lib/components/SettingsView.svelte';
  import AddFeedModal from './lib/components/AddFeedModal.svelte';
  import StatisticsView from './lib/components/StatisticsView.svelte';
  import FeedManagerView from './lib/components/FeedManagerView.svelte';
  import OnboardingWizardModal from './lib/components/OnboardingWizardModal.svelte';
  import NotificationPanel from './lib/components/NotificationPanel.svelte';
  import MediaCredentialsModal from './lib/components/MediaCredentialsModal.svelte';
  import WebhookManagerView from './lib/components/WebhookManagerView.svelte';
  
  let showOnboarding = false;

  function customViewTransition(node) {
    const type = $transitionType;
    const duration = $transitionDuration;
    const dir = $mainNavDirection;

    if (type === 'none' || duration <= 0) {
      return { duration: 0 };
    }
    if (type === 'fly') {
      // Directional vertical slide: dir = 1 (moving down) -> y: 40, dir = -1 (moving up) -> y: -40
      return fly(node, { y: dir * 40, duration });
    }
    if (type === 'slide') {
      return slide(node, { duration });
    }
    if (type === 'scale') {
      return scale(node, { start: 0.96, duration });
    }
    if (type === 'blur') {
      return blur(node, { amount: 6, duration });
    }
    return fade(node, { duration });
  }

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

<main class="h-screen w-full flex flex-col overflow-hidden bg-background text-foreground">
  
  <div class="flex-1 flex overflow-hidden relative">
    {#if !$isMobile}
      <!-- Desktop Layout: 3 Columns / Views -->
      <Sidebar />
      
      {#key $currentView}
        <div class="flex-1 flex overflow-hidden w-full h-full" in:customViewTransition>
          {#if $currentView === 'podcast'}
            <PodcastStudioView />
          {:else if $currentView === 'perplexity'}
            <ExplorerView />
          {:else if $currentView === 'webhooks'}
            <WebhookManagerView />
          {:else if $currentView === 'discover'}
            <DiscoverView />
          {:else if $currentView === 'synthesis'}
            <SynthesisView />
          {:else if $currentView === 'settings'}
            <SettingsView />
          {:else if $currentView === 'stats'}
            <StatisticsView />
          {:else if $currentView === 'feeds'}
            <FeedManagerView />
          {:else}
            <ArticleList />
            <ReaderView />
          {/if}
        </div>
      {/key}
      
    {:else}
      <!-- Mobile Layout: Dynamic 1 Column -->
      {#key $currentView}
        <div class="flex-1 w-full flex flex-col h-full overflow-hidden" in:customViewTransition>
          {#if $currentView === 'podcast'}
            <PodcastStudioView />
          {:else if $currentView === 'perplexity'}
            <ExplorerView />
          {:else if $currentView === 'webhooks'}
            <WebhookManagerView />
          {:else if $currentView === 'discover'}
            <DiscoverView />
          {:else if $currentView === 'synthesis'}
            <SynthesisView />
          {:else if $currentView === 'settings'}
            <SettingsView />
          {:else if $currentView === 'stats'}
            <StatisticsView />
          {:else if $currentView === 'feeds'}
            <FeedManagerView />
          {:else}
            <div class="flex-1 w-full flex flex-col h-full overflow-hidden pb-16">
              {#if $selectedItemId}
                <ReaderView />
              {:else}
                <ArticleList />
              {/if}
            </div>
          {/if}
        </div>
      {/key}
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
  <AddFeedModal />
  
  {#if showOnboarding}
    <OnboardingWizardModal />
  {/if}

  {#if $showNotifications}
    <NotificationPanel />
  {/if}

  {#if $showMediaCredentialsModal}
    <MediaCredentialsModal />
  {/if}

</main>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
  }
</style>
