<script>
  export let src = '';
  export let fallbackSrc = '';
  export let alt = '';
  export let imgClass = 'w-full h-full object-cover';
  export let containerClass = 'w-full h-full relative overflow-hidden';
  export let loading = 'lazy';

  let isLoaded = false;
  let isError = false;
  let currentSrc = src;

  $: if (src) {
    if (currentSrc !== src) {
      currentSrc = src;
      isLoaded = false;
      isError = false;
    }
  }

  function handleLoad() {
    isLoaded = true;
  }

  function handleError() {
    if (!isError && fallbackSrc && currentSrc !== fallbackSrc) {
      isError = true;
      currentSrc = fallbackSrc;
    } else {
      isError = true;
      isLoaded = true;
    }
  }
</script>

<div class={containerClass}>
  <!-- Skeleton Shimmer Background -->
  {#if !isLoaded}
    <div class="absolute inset-0 bg-gray-900 animate-pulse flex items-center justify-center">
      <div class="w-full h-full bg-gradient-to-r from-gray-900 via-gray-800/80 to-gray-900 bg-[length:200%_100%] animate-shimmer"></div>
    </div>
  {/if}

  <!-- Progressive Image with Blur-Up & Fade-In -->
  {#if currentSrc}
    <img
      src={currentSrc}
      {alt}
      {loading}
      on:load={handleLoad}
      on:error={handleError}
      class="{imgClass} transition-all duration-700 ease-out {isLoaded ? 'opacity-100 scale-100 blur-0' : 'opacity-0 scale-105 blur-sm'}"
    />
  {/if}
</div>

<style>
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  .animate-shimmer {
    animation: shimmer 1.8s infinite linear;
  }
</style>
