<script>
  let playing = $state(false);
  let audioEl = $state(null);

  function toggle() {
    if (!audioEl) return;
    if (playing) {
      audioEl.pause();
      audioEl.src = '';
      playing = false;
    } else {
      audioEl.src = '/stream';
      audioEl.play().catch(() => {});
      playing = true;
    }
  }
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold">Live Stream</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400">Listen to your microphone feed in real-time</p>
  </div>

  <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 flex flex-col items-center gap-6">
    <!-- Large play button -->
    <button
      onclick={toggle}
      class="w-24 h-24 rounded-full flex items-center justify-center transition-all
        {playing ? 'bg-red-500 hover:bg-red-600 animate-pulse' : 'bg-green-600 hover:bg-green-700'} text-white shadow-lg"
    >
      {#if playing}
        <svg class="w-10 h-10" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
      {:else}
        <svg class="w-10 h-10 ml-1" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/></svg>
      {/if}
    </button>

    <p class="text-sm text-gray-500 dark:text-gray-400">
      {playing ? 'Streaming live audio...' : 'Click to start listening'}
    </p>

    {#if playing}
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
        <span class="text-sm font-medium text-red-500">LIVE</span>
      </div>
    {/if}

    <audio bind:this={audioEl} class="hidden"></audio>
  </div>

  <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
    <h2 class="text-lg font-semibold mb-3">About</h2>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      The live stream broadcasts audio from the BirdNET-Pi microphone via Icecast2.
      Detections are processed independently by the analysis service regardless of
      whether anyone is listening to the stream.
    </p>
  </div>
</div>
