<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { currentAudio } from '../lib/stores.js';

  let selectedDate = $state(new Date().toISOString().split('T')[0]);
  let recordings = $state([]);
  let loading = $state(true);
  let groupBySpecies = $state(true);

  async function load(date) {
    loading = true;
    try {
      recordings = await api.getRecordings(date);
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  function onDateChange(e) {
    selectedDate = e.target.value;
    load(selectedDate);
  }

  onMount(() => load(selectedDate));

  let grouped = $derived.by(() => {
    if (!groupBySpecies) return { 'All Recordings': recordings };
    const g = {};
    for (const r of recordings) {
      if (!g[r.species]) g[r.species] = [];
      g[r.species].push(r);
    }
    return g;
  });

  function play(rec) {
    currentAudio.set({
      url: rec.audio_url,
      title: rec.species,
      subtitle: `${rec.filename} — ${rec.date}`,
    });
  }
</script>

<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="text-2xl font-bold">Recordings</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">{recordings.length} recording{recordings.length !== 1 ? 's' : ''}</p>
    </div>
    <div class="flex gap-2">
      <input
        type="date"
        value={selectedDate}
        onchange={onDateChange}
        max={new Date().toISOString().split('T')[0]}
        class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
      />
      <button
        onclick={() => groupBySpecies = !groupBySpecies}
        class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800"
      >
        {groupBySpecies ? 'Flat View' : 'By Species'}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-400">Loading...</div>
  {:else if recordings.length === 0}
    <div class="text-center py-12 text-gray-400">No recordings for this date</div>
  {:else}
    {#each Object.entries(grouped) as [species, recs]}
      <div class="space-y-2">
        {#if groupBySpecies}
          <h2 class="text-lg font-semibold">{species} <span class="text-sm text-gray-400 font-normal">({recs.length})</span></h2>
        {/if}
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800">
          {#each recs as rec}
            <div class="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50">
              <button onclick={() => play(rec)} class="shrink-0 w-12 h-12 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 relative group cursor-pointer">
                <img src={rec.spectrogram_url} alt="" class="w-full h-full object-cover" onerror={(e) => e.target.style.display='none'} />
                <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/></svg>
                </div>
              </button>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">{rec.filename}</p>
                {#if !groupBySpecies}
                  <p class="text-xs text-gray-400">{rec.species}</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>
