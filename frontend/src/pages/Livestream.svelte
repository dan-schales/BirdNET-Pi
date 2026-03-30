<script>
  import { onMount } from 'svelte';
  import { currentAudio } from '../lib/stores.js';

  let playing = $state(false);
  let audioEl = $state(null);

  // Recording state
  let isRecording = $state(false);
  let recordingFilename = $state('');
  let recordingSize = $state('');
  let elapsed = $state(0);
  let prefix = $state('livestream');
  let starting = $state(false);
  let stopping = $state(false);
  let recordingError = $state('');

  // Timer state
  let timerEnabled = $state(false);
  let timerMinutes = $state(30);
  let maxDuration = $state(0);
  let remainingSeconds = $state(0);

  // Recordings list
  let recordings = $state([]);
  let loading = $state(true);

  // Rename state
  let renamingFile = $state(null);
  let renameValue = $state('');

  let pollTimer;
  let elapsedTimer;

  const TIMER_PRESETS = [5, 10, 15, 30, 60, 120];

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

  function formatDuration(secs) {
    if (secs == null || secs < 0) secs = 0;
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  async function startRecording() {
    starting = true;
    recordingError = '';
    try {
      const body = { prefix: prefix || 'livestream' };
      if (timerEnabled && timerMinutes > 0) {
        body.duration = timerMinutes * 60;
      }
      const res = await fetch('/api/v2/livestream/record/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        isRecording = true;
        recordingFilename = data.data.filename;
        recordingSize = '';
        elapsed = 0;
        maxDuration = data.data.duration || 0;
        remainingSeconds = maxDuration;
        beginPolling();
      } else {
        recordingError = data.detail || data.message || 'Failed to start recording';
      }
    } catch (e) {
      recordingError = 'Network error: could not reach the server';
      console.error('Failed to start recording:', e);
    }
    starting = false;
  }

  async function stopRecording() {
    stopping = true;
    try {
      await fetch('/api/v2/livestream/record/stop', { method: 'POST' });
    } catch (e) {
      console.error('Failed to stop recording:', e);
    }
    endPolling();
    isRecording = false;
    stopping = false;
    maxDuration = 0;
    remainingSeconds = 0;
    loadRecordings();
  }

  function beginPolling() {
    endPolling();
    elapsedTimer = setInterval(() => {
      elapsed += 1;
      if (maxDuration > 0) {
        remainingSeconds = Math.max(0, maxDuration - elapsed);
      }
    }, 1000);
    pollTimer = setInterval(async () => {
      try {
        const res = await fetch('/api/v2/livestream/record/status');
        const data = await res.json();
        if (data.recording && data.data) {
          recordingSize = data.data.filesize_human;
          if (data.data.max_duration) {
            maxDuration = data.data.max_duration;
          }
          if (data.data.remaining_seconds != null) {
            remainingSeconds = data.data.remaining_seconds;
          }
        } else {
          // Recording ended (timer expired or external stop)
          endPolling();
          isRecording = false;
          maxDuration = 0;
          remainingSeconds = 0;
          if (data.error) {
            recordingError = data.error;
          }
          loadRecordings();
        }
      } catch {}
    }, 3000);
  }

  function endPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  }

  async function loadRecordings() {
    try {
      const res = await fetch('/api/v2/livestream/recordings');
      const data = await res.json();
      recordings = data.data || [];
    } catch {
      recordings = [];
    }
    loading = false;
  }

  function playRecording(rec) {
    currentAudio.set({
      url: `/api/v2/livestream/recordings/${encodeURIComponent(rec.filename)}`,
      title: rec.filename
    });
  }

  async function deleteRecording(rec) {
    if (!confirm(`Delete ${rec.filename}?`)) return;
    try {
      await fetch(`/api/v2/livestream/recordings/${encodeURIComponent(rec.filename)}`, {
        method: 'DELETE'
      });
      loadRecordings();
    } catch (e) {
      console.error('Failed to delete recording:', e);
    }
  }

  function startRename(rec) {
    renamingFile = rec.filename;
    renameValue = rec.filename.replace(/\.mp3$/, '');
  }

  function cancelRename() {
    renamingFile = null;
    renameValue = '';
  }

  async function submitRename(oldFilename) {
    const newName = renameValue.trim();
    if (!newName) { cancelRename(); return; }
    try {
      const res = await fetch(`/api/v2/livestream/recordings/${encodeURIComponent(oldFilename)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: newName })
      });
      if (res.ok) {
        loadRecordings();
      } else {
        const data = await res.json();
        alert(data.detail || 'Failed to rename');
      }
    } catch (e) {
      console.error('Failed to rename recording:', e);
    }
    cancelRename();
  }

  function handleRenameKeydown(e, oldFilename) {
    if (e.key === 'Enter') submitRename(oldFilename);
    if (e.key === 'Escape') cancelRename();
  }

  onMount(() => {
    loadRecordings();
    fetch('/api/v2/livestream/record/status')
      .then(r => r.json())
      .then(data => {
        if (data.recording && data.data) {
          isRecording = true;
          recordingFilename = data.data.filename;
          recordingSize = data.data.filesize_human;
          elapsed = data.data.duration_seconds || 0;
          maxDuration = data.data.max_duration || 0;
          remainingSeconds = data.data.remaining_seconds || 0;
          beginPolling();
        }
      })
      .catch(() => {});

    return () => endPolling();
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold">Live Stream</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400">Listen to your microphone feed in real-time</p>
  </div>

  <!-- Audio Player -->
  <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 flex flex-col items-center gap-6">
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

  <!-- Record Stream -->
  <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
    <h2 class="text-lg font-semibold mb-4">Record Stream</h2>

    <!-- Error display -->
    {#if recordingError}
      <div class="mb-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg">
        <div class="flex items-start gap-2">
          <svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd"/></svg>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-red-700 dark:text-red-400">Recording failed</p>
            <p class="text-xs text-red-600/80 dark:text-red-400/70 mt-0.5 break-words">{recordingError}</p>
          </div>
          <button onclick={() => { recordingError = ''; }} class="text-red-400 hover:text-red-600 p-1 flex-shrink-0">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
          </button>
        </div>
      </div>
    {/if}

    {#if isRecording}
      <div class="space-y-4">
        <div class="flex items-center gap-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg p-4">
          <span class="w-3 h-3 bg-red-500 rounded-full animate-pulse flex-shrink-0"></span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-red-700 dark:text-red-400">Recording</p>
            <p class="text-xs text-red-600/70 dark:text-red-400/60 truncate">{recordingFilename}</p>
          </div>
          <div class="text-right flex-shrink-0">
            <p class="text-lg font-mono font-bold text-red-700 dark:text-red-400">{formatDuration(elapsed)}</p>
            {#if recordingSize}
              <p class="text-xs text-red-600/70 dark:text-red-400/60">{recordingSize}</p>
            {/if}
          </div>
        </div>

        <!-- Timer progress bar -->
        {#if maxDuration > 0}
          <div class="space-y-1">
            <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Timer: {formatDuration(maxDuration)}</span>
              <span>{formatDuration(remainingSeconds)} remaining</span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                class="bg-red-500 h-2 rounded-full transition-all duration-1000"
                style="width: {Math.min(100, (elapsed / maxDuration) * 100)}%"
              ></div>
            </div>
          </div>
        {/if}

        <button
          onclick={stopRecording}
          disabled={stopping}
          class="w-full py-2.5 px-4 bg-gray-700 hover:bg-gray-800 dark:bg-gray-600 dark:hover:bg-gray-500 disabled:opacity-50
            text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><rect x="5" y="5" width="10" height="10" rx="1"/></svg>
          {stopping ? 'Stopping...' : 'Stop Recording'}
        </button>
      </div>
    {:else}
      <div class="space-y-3">
        <!-- Prefix + record button -->
        <div class="flex gap-3">
          <input
            type="text"
            bind:value={prefix}
            placeholder="File prefix (default: livestream)"
            maxlength="50"
            class="flex-1 min-w-0 px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700
              bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/40"
          />
          <button
            onclick={startRecording}
            disabled={starting}
            class="px-5 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg
              font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><circle cx="10" cy="10" r="6"/></svg>
            {starting ? 'Starting...' : 'Record'}
          </button>
        </div>

        <!-- Timer toggle + options -->
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={timerEnabled}
              class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-red-600 focus:ring-red-500"
            />
            <span class="text-sm text-gray-600 dark:text-gray-400">Auto-stop after</span>
          </label>
          {#if timerEnabled}
            <div class="flex items-center gap-2 flex-wrap">
              {#each TIMER_PRESETS as mins}
                <button
                  onclick={() => { timerMinutes = mins; }}
                  class="px-2.5 py-1 text-xs rounded-md transition-colors
                    {timerMinutes === mins
                      ? 'bg-red-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
                >
                  {mins >= 60 ? `${mins / 60}h` : `${mins}m`}
                </button>
              {/each}
              <input
                type="number"
                bind:value={timerMinutes}
                min="1"
                max="1440"
                class="w-16 px-2 py-1 text-xs rounded-md border border-gray-300 dark:border-gray-700
                  bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-red-500/40"
              />
              <span class="text-xs text-gray-500 dark:text-gray-400">min</span>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Saved Recordings -->
  {#if !loading && recordings.length > 0}
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <h2 class="text-lg font-semibold mb-4">Saved Recordings ({recordings.length})</h2>
      <div class="space-y-1">
        {#each recordings as rec}
          <div class="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
            <button
              onclick={() => playRecording(rec)}
              class="w-9 h-9 flex-shrink-0 rounded-full bg-green-600 hover:bg-green-700 text-white
                flex items-center justify-center transition-colors"
              title="Play"
            >
              <svg class="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/></svg>
            </button>
            <div class="flex-1 min-w-0">
              {#if renamingFile === rec.filename}
                <div class="flex items-center gap-2">
                  <input
                    type="text"
                    bind:value={renameValue}
                    onkeydown={(e) => handleRenameKeydown(e, rec.filename)}
                    class="flex-1 min-w-0 px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600
                      bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500/40"
                    autofocus
                  />
                  <span class="text-xs text-gray-400">.mp3</span>
                  <button onclick={() => submitRename(rec.filename)} class="text-green-500 hover:text-green-600 p-1" title="Save">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  </button>
                  <button onclick={cancelRename} class="text-gray-400 hover:text-gray-600 p-1" title="Cancel">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                  </button>
                </div>
              {:else}
                <p class="text-sm font-medium truncate">{rec.filename}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  {rec.filesize_human} &middot; {formatDuration(rec.duration_seconds)} &middot; {rec.created}
                </p>
              {/if}
            </div>
            {#if renamingFile !== rec.filename}
              <div class="flex items-center gap-1 flex-shrink-0">
                <button
                  onclick={() => startRename(rec)}
                  class="p-2 text-gray-400 hover:text-yellow-500 transition-colors"
                  title="Rename"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                <a
                  href={`/api/v2/livestream/recordings/${encodeURIComponent(rec.filename)}`}
                  download
                  class="p-2 text-gray-400 hover:text-blue-500 transition-colors"
                  title="Download"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                </a>
                <button
                  onclick={() => deleteRecording(rec)}
                  class="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  title="Delete"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- About -->
  <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
    <h2 class="text-lg font-semibold mb-3">About</h2>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      The live stream broadcasts audio from the BirdNET-Pi microphone via Icecast2.
      Recordings capture the stream as MP3 files that you can download or play back later.
      Use the timer to automatically stop recording after a set duration.
      Detections are processed independently by the analysis service regardless of
      whether anyone is listening to the stream.
    </p>
  </div>
</div>
