<script>
  import { currentAudio } from '../lib/stores.js';

  let audioEl = $state(null);
  let playing = $state(false);
  let progress = $state(0);
  let duration = $state(0);

  $effect(() => {
    if ($currentAudio && audioEl) {
      audioEl.src = $currentAudio.url;
      audioEl.play().catch(() => {});
    }
  });

  function togglePlay() {
    if (!audioEl) return;
    if (playing) audioEl.pause();
    else audioEl.play().catch(() => {});
  }

  function seek(e) {
    if (!audioEl || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audioEl.currentTime = pct * duration;
  }

  function close() {
    if (audioEl) { audioEl.pause(); audioEl.src = ''; }
    currentAudio.set(null);
  }

  function formatSec(s) {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }
</script>

{#if $currentAudio}
<div class="fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-4 py-3 lg:ml-64">
  <audio
    bind:this={audioEl}
    onplay={() => playing = true}
    onpause={() => playing = false}
    ontimeupdate={() => progress = audioEl?.currentTime || 0}
    onloadedmetadata={() => duration = audioEl?.duration || 0}
    onended={() => playing = false}
  ></audio>

  <div class="flex items-center gap-4 max-w-4xl mx-auto">
    <!-- Play/Pause -->
    <button onclick={togglePlay} class="p-2 rounded-full bg-green-600 text-white hover:bg-green-700 transition-colors shrink-0">
      {#if playing}
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
      {:else}
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/></svg>
      {/if}
    </button>

    <!-- Track info -->
    <div class="min-w-0 flex-shrink">
      <p class="text-sm font-medium truncate">{$currentAudio.title}</p>
      <p class="text-xs text-gray-400 truncate">{$currentAudio.subtitle || ''}</p>
    </div>

    <!-- Progress bar -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="flex-1 flex items-center gap-2 cursor-pointer" onclick={seek}>
      <span class="text-xs text-gray-400 w-8 text-right">{formatSec(progress)}</span>
      <div class="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div class="h-full bg-green-500 rounded-full transition-[width]" style="width: {duration ? (progress / duration) * 100 : 0}%"></div>
      </div>
      <span class="text-xs text-gray-400 w-8">{formatSec(duration)}</span>
    </div>

    <!-- Close -->
    <button onclick={close} class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 shrink-0" aria-label="Close player">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
    </button>
  </div>
</div>
{/if}
