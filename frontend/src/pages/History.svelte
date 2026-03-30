<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import HourlyChart from '../components/HourlyChart.svelte';
  import DetectionCard from '../components/DetectionCard.svelte';

  let selectedDate = $state(new Date().toISOString().split('T')[0]);
  let hourlyData = $state([]);
  let detections = $state([]);
  let dates = $state([]);
  let loading = $state(true);

  async function load(date) {
    loading = true;
    try {
      const [h, d] = await Promise.all([
        api.getDetectionsHourly(date),
        api.getDetectionsHistory(date, 300),
      ]);
      hourlyData = h;
      detections = d;
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    load(selectedDate);
    dates = await api.getDates();
  });

  function onDateChange(e) {
    selectedDate = e.target.value;
    load(selectedDate);
  }

  function prevDay() {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    selectedDate = d.toISOString().split('T')[0];
    load(selectedDate);
  }

  function nextDay() {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    const today = new Date().toISOString().split('T')[0];
    const next = d.toISOString().split('T')[0];
    if (next <= today) {
      selectedDate = next;
      load(selectedDate);
    }
  }

  function totalForDay() {
    return hourlyData.reduce((sum, h) => sum + h.count, 0);
  }
</script>

<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="text-2xl font-bold">History</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">{totalForDay()} detections on {selectedDate}</p>
    </div>
    <div class="flex items-center gap-2">
      <button onclick={prevDay} class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Previous day">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
      </button>
      <input
        type="date"
        value={selectedDate}
        onchange={onDateChange}
        max={new Date().toISOString().split('T')[0]}
        class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
      />
      <button onclick={nextDay} class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Next day">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
      </button>
    </div>
  </div>

  <HourlyChart data={hourlyData} title="Detections by Hour — {selectedDate}" />

  {#if loading}
    <div class="text-center py-8 text-gray-400">Loading...</div>
  {:else}
    <div class="space-y-3">
      <h2 class="text-lg font-semibold">Detections</h2>
      {#if detections.length === 0}
        <p class="text-center py-8 text-gray-400">No detections on this date</p>
      {:else}
        {#each detections as detection (detection.file_name)}
          <DetectionCard {detection} />
        {/each}
      {/if}
    </div>
  {/if}
</div>
