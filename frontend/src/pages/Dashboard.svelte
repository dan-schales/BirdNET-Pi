<script>
  import { onMount, onDestroy } from 'svelte';
  import { api, connectWebSocket } from '../lib/api.js';
  import StatCard from '../components/StatCard.svelte';
  import HourlyChart from '../components/HourlyChart.svelte';
  import DetectionCard from '../components/DetectionCard.svelte';
  import { speciesSlug } from '../lib/utils.js';

  let summary = $state(null);
  let hourlyData = $state([]);
  let recentDetections = $state([]);
  let topSpecies = $state([]);
  let ws = $state(null);
  let refreshInterval;

  async function loadData() {
    try {
      const [s, h, d, t] = await Promise.all([
        api.getSummary(),
        api.getDetectionsHourly(),
        api.getDetectionsToday(15),
        api.getTopSpecies(8),
      ]);
      summary = s;
      hourlyData = h;
      recentDetections = d;
      topSpecies = t;
    } catch (e) {
      console.error('Dashboard load error:', e);
    }
  }

  onMount(() => {
    loadData();
    refreshInterval = setInterval(loadData, 30000);
    ws = connectWebSocket((msg) => {
      if (msg.type === 'new_detection') {
        loadData();
      }
    });
  });

  onDestroy(() => {
    clearInterval(refreshInterval);
    if (ws) ws.close();
  });
</script>

<div class="space-y-6">
  <!-- Page header -->
  <div>
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Real-time bird detection overview</p>
  </div>

  <!-- Stat cards -->
  <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
    <StatCard
      label="Today's Detections"
      value={summary?.today_count ?? '...'}
      icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
    />
    <StatCard
      label="Species Today"
      value={summary?.today_species ?? '...'}
      icon="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
    />
    <StatCard
      label="Last Hour"
      value={summary?.hour_count ?? '...'}
      icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
    />
    <StatCard
      label="Total Detections"
      value={summary?.total_detections?.toLocaleString() ?? '...'}
      icon="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7c-2 0-3 1-3 3z"
    />
    <StatCard
      label="Total Species"
      value={summary?.total_species ?? '...'}
      icon="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064"
    />
  </div>

  <!-- Hourly chart -->
  <HourlyChart data={hourlyData} />

  <!-- Bottom: Recent detections + Top species -->
  <div class="grid lg:grid-cols-3 gap-6">
    <!-- Recent detections -->
    <div class="lg:col-span-2 space-y-3">
      <h2 class="text-lg font-semibold">Latest Detections</h2>
      {#if recentDetections.length === 0}
        <p class="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">No detections today yet</p>
      {:else}
        <div class="space-y-3">
          {#each recentDetections as detection (detection.file_name)}
            <DetectionCard {detection} />
          {/each}
        </div>
      {/if}
    </div>

    <!-- Top species sidebar -->
    <div class="space-y-3">
      <h2 class="text-lg font-semibold">Top Species Today</h2>
      {#if topSpecies.length === 0}
        <p class="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">No species detected today</p>
      {:else}
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800">
          {#each topSpecies as species, i}
            <a
              href="#/species/{speciesSlug(species.Sci_Name)}"
              class="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              <span class="text-sm font-bold text-gray-300 dark:text-gray-600 w-5 text-center">{i + 1}</span>
              {#if species.image_url}
                <img src={species.image_url} alt="" class="w-9 h-9 rounded-full object-cover shrink-0" loading="lazy" />
              {:else}
                <div class="w-9 h-9 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center shrink-0">
                  <span class="text-green-700 dark:text-green-300 text-xs font-bold">{species.Com_Name[0]}</span>
                </div>
              {/if}
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">{species.Com_Name}</p>
              </div>
              <span class="text-sm font-semibold text-green-600 dark:text-green-400">{species.count}</span>
            </a>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>
