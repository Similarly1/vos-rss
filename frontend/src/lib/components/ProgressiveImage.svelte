<script>
  import smartcrop from 'smartcrop';

  export let src = '';
  export let fallbackSrc = '';
  export let alt = '';
  export let imgClass = 'w-full h-full object-cover';
  export let containerClass = 'w-full h-full relative overflow-hidden';
  export let loading = 'lazy';
  export let defaultPosition = 'center 12%'; // Top-focused framing to keep eyes & head fully in frame

  let isLoaded = false;
  let isError = false;
  let currentSrc = src;
  let objectPosition = defaultPosition;
  let imgElement = null;

  $: if (src) {
    if (currentSrc !== src) {
      currentSrc = src;
      isLoaded = false;
      isError = false;
      objectPosition = defaultPosition;
    }
  }

  async function handleLoad() {
    isLoaded = true;

    // Run smartcrop analysis on load to find face/subject focal point
    if (imgElement && imgElement.naturalWidth && imgElement.naturalHeight) {
      try {
        const result = await smartcrop.crop(imgElement, {
          width: 400,
          height: 250,
          minScale: 1.0,
          ruleOfThirds: true
        });

        if (result && result.topCrop) {
          const crop = result.topCrop;
          const centerX = Math.round(((crop.x + crop.width / 2) / imgElement.naturalWidth) * 100);
          
          // Target top of head / eye line (15% down the crop box)
          const eyeY = crop.y + (crop.height * 0.15);
          let centerY = Math.round((eyeY / imgElement.naturalHeight) * 100);
          
          // Clamp centerY between 5% and 20% so head & eyes are positioned in upper viewport area
          centerY = Math.max(5, Math.min(20, centerY));
          
          objectPosition = `${centerX}% ${centerY}%`;
        }
      } catch (err) {
        // Fallback gracefully to upper-third alignment 'center 12%' if CORS prevents canvas inspection
        objectPosition = defaultPosition;
      }
    }
  }

  function handleError() {
    if (!isError && fallbackSrc && currentSrc !== fallbackSrc) {
      isError = true;
      currentSrc = fallbackSrc;
      objectPosition = defaultPosition;
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

  <!-- Progressive Image with Top-Third Eye-Level SmartCrop & Blur-Up -->
  {#if currentSrc}
    <img
      bind:this={imgElement}
      src={currentSrc}
      {alt}
      {loading}
      on:load={handleLoad}
      on:error={handleError}
      style="object-position: {objectPosition};"
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
