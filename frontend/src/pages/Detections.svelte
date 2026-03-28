<script>
  import { onMount, onDestroy } from 'svelte';
  import { api, connectWebSocket } from '../lib/api.js';
  import DetectionCard from '../components/DetectionCard.svelte';

  let detections = $state([]);
  let search = $state('');
  let sortBy = $state('time');
  let loading = $state(true);
  let ws;

  async function load() {
    try {
      detections = await api.getDetectionsToday(500);
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  let filtered = $derived.by(() => {
    let list = detections;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(d => d.com_name.toLowerCase().includes(q) || d.sci_name.toLowerCase().includes(q));
    }
    if (sortBy === 'confidence') {
      list = [...list].sort((a, b) => b.confidence - a.confidence);
    } else if (sortBy === 'species') {
      list = [...list].sort((a, b) => a.com_name.localeCompare(b.com_name));
    }
    return list;
  });

  onMount(() => {
    load();
    ws = connectWebSocket((msg) => {
      if (msg.type === 'new_detection') load();
    });
  });

  onDestroy(() => { if (ws) ws.close(); });
</script>

<div class="space-y-4">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="text-2xl font-bold">Today's Detections</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">{detections.length} detection{detections.length !== 1 ? 's' : ''} so far</p>
    </div>
    <div class="flex gap-2">
      <input
        type="text"
        placeholder="Search species..."
        bind:value={search}
        class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none"
      />
      <select bind:value={sortBy} class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <option value="time">Latest</option>
        <option value="confidence">Confidence</option>
        <option value="species">Species</option>
      </select>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-400">Loading...</div>
  {:else if filtered.length === 0}
    <div class="text-center py-12 text-gray-400">No detections found</div>
  {:else}
    <div class="space-y-3">
      {#each filtered as detection (detection.file_name)}
        <DetectionCard {detection} />
      {/each}
    </div>
  {/if}
</div>
