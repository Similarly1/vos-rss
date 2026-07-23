<script>
  import { isMobile } from '../stores/appState.js';
  import { currentTrack, isPlaying, playbackTime, duration } from '../stores/audioStore.js';

  let audioElement;
  let loadedAudioUrl = '';
  let isUserSeeking = false;
  let seekInputValue = 0;

  function togglePlay() {
    if (!audioElement) return;
    if ($isPlaying) {
      audioElement.pause();
      $isPlaying = false;
    } else {
      audioElement.play();
      $isPlaying = true;
    }
  }

  function stopPlay() {
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
    $isPlaying = false;
    $currentTrack = null;
    loadedAudioUrl = '';
  }

  function handleTimeUpdate() {
    if (audioElement && !isUserSeeking) {
      $playbackTime = audioElement.currentTime;
      $duration = audioElement.duration || 0;
    }
  }

  function handleSeekStart() {
    isUserSeeking = true;
  }

  function handleSeekInput(e) {
    seekInputValue = parseFloat(e.target.value);
  }

  function handleSeekChange(e) {
    if (audioElement && $duration && !isNaN($duration)) {
      const val = parseFloat(e.target.value);
      const targetTime = (val / 100) * $duration;
      audioElement.currentTime = targetTime;
      $playbackTime = targetTime;
    }
    isUserSeeking = false;
  }

  function skipTime(seconds) {
    if (!audioElement || !$duration) return;
    let newTime = audioElement.currentTime + seconds;
    if (newTime < 0) newTime = 0;
    if (newTime > $duration) newTime = $duration;
    audioElement.currentTime = newTime;
    $playbackTime = newTime;
  }

  function formatTime(secs) {
    if (!secs || isNaN(secs)) return '00:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  $: progressPercent = isUserSeeking 
    ? seekInputValue 
    : ($duration ? ($playbackTime / $duration) * 100 : 0);

  // FIX: Only set audioElement.src when the URL actually changes to a new track
  $: if ($currentTrack && $currentTrack.audioUrl && audioElement) {
    if (loadedAudioUrl !== $currentTrack.audioUrl) {
      loadedAudioUrl = $currentTrack.audioUrl;
      audioElement.src = $currentTrack.audioUrl;
      audioElement.currentTime = 0;
      $playbackTime = 0;
      audioElement.play().then(() => {
        $isPlaying = true;
      }).catch(err => {
        console.error("Playback error:", err);
      });
    }
  }
</script>

<audio 
  bind:this={audioElement}
  on:timeupdate={handleTimeUpdate}
  on:loadedmetadata={handleTimeUpdate}
  on:ended={() => $isPlaying = false}
></audio>

{#if $currentTrack}
  <div class="bg-gray-900 border-t border-gray-800 p-3 md:p-4 shadow-2xl {$isMobile ? 'fixed bottom-16 left-2 right-2 z-50 rounded-2xl border border-gray-800' : 'w-full z-50 relative'}">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3 md:gap-6">
      
      <!-- Top / Left Track Info -->
      <div class="flex items-center justify-between w-full md:w-auto gap-3 flex-1 min-w-0">
        
        <div class="flex items-center gap-3 truncate min-w-0">
          <button 
            on:click={togglePlay}
            class="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-tr from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-2xl flex items-center justify-center shrink-0 shadow-lg transition-all"
            title={$isPlaying ? 'Pause' : 'Lecture'}
          >
            {#if $isPlaying}
              <svg class="w-5 h-5 md:w-6 md:h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            {:else}
              <svg class="w-5 h-5 md:w-6 md:h-6 ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            {/if}
          </button>

          <div class="truncate">
            <h4 class="font-extrabold text-xs md:text-sm truncate leading-snug text-white">{$currentTrack.title}</h4>
            <p class="text-[11px] text-purple-400 font-semibold truncate flex items-center gap-1">
              <span>🎙️</span>
              <span>{$currentTrack.feedTitle || 'Revue de presse Vos'}</span>
            </p>
          </div>
        </div>

        <!-- Mobile controls (Skip -15s / +15s / Close) -->
        {#if $isMobile}
          <div class="flex items-center gap-2 shrink-0">
            <button on:click={() => skipTime(-15)} class="p-1.5 text-gray-400 hover:text-white text-xs font-mono font-bold" title="-15 sec">
              -15s
            </button>
            <button on:click={() => skipTime(15)} class="p-1.5 text-gray-400 hover:text-white text-xs font-mono font-bold" title="+15 sec">
              +15s
            </button>
            <button on:click={stopPlay} class="text-xs text-rose-400 font-bold px-2 py-1 bg-rose-950/40 rounded-lg">
              ✕
            </button>
          </div>
        {/if}

      </div>

      <!-- Center Scrubber & Skip Controls (Desktop & Mobile) -->
      <div class="w-full max-w-xl flex items-center gap-2 md:gap-3">
        
        <!-- Skip Back 15s -->
        <button 
          on:click={() => skipTime(-15)} 
          class="hidden md:flex items-center justify-center p-2 text-gray-400 hover:text-purple-300 transition-colors text-xs font-mono font-bold"
          title="Reculer de 15 secondes"
        >
          -15s
        </button>

        <span class="text-xs font-mono text-gray-400 w-10 text-right shrink-0">{formatTime($playbackTime)}</span>
        
        <!-- SEEKBAR INPUT -->
        <div class="flex-1 relative flex items-center">
          <input 
            type="range" 
            min="0" 
            max="100" 
            step="0.1"
            value={progressPercent}
            on:mousedown={handleSeekStart}
            on:touchstart={handleSeekStart}
            on:input={handleSeekInput}
            on:change={handleSeekChange}
            class="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-500 hover:accent-purple-400"
          />
        </div>

        <span class="text-xs font-mono text-gray-400 w-10 shrink-0">{formatTime($duration)}</span>

        <!-- Skip Forward 15s -->
        <button 
          on:click={() => skipTime(15)} 
          class="hidden md:flex items-center justify-center p-2 text-gray-400 hover:text-purple-300 transition-colors text-xs font-mono font-bold"
          title="Avancer de 15 secondes"
        >
          +15s
        </button>

      </div>

      <!-- Controls Right (Desktop) -->
      <div class="hidden md:flex items-center gap-3 shrink-0">
        <a 
          href={$currentTrack.audioUrl} 
          download="audio_vos.mp3"
          target="_blank"
          rel="noreferrer"
          class="text-xs text-emerald-400 font-bold px-3 py-1.5 bg-emerald-950/60 border border-emerald-800/50 rounded-xl hover:bg-emerald-900/60 transition-all flex items-center gap-1"
          title="Télécharger l'audio"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          <span>MP3</span>
        </a>

        <button 
          on:click={stopPlay}
          class="text-xs text-rose-400 hover:text-rose-300 font-bold px-3 py-1.5 rounded-xl bg-rose-950/40 border border-rose-900/40 transition-all"
          title="Fermer le lecteur"
        >
          Fermer
        </button>
      </div>

    </div>
  </div>
{/if}

<style>
  input[type=range]::-webkit-slider-thumb {
    height: 14px;
    width: 14px;
    border-radius: 50%;
    background: #a855f7;
    cursor: pointer;
    margin-top: -3px;
  }
</style>
