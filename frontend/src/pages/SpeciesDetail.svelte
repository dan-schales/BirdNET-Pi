<script>
  import { onMount } from 'svelte';
  import Chart from 'chart.js/auto';
  import { api } from '../lib/api.js';
  import { formatConfidence, formatTime, formatDate, confidenceBarColor } from '../lib/utils.js';
  import { currentAudio } from '../lib/stores.js';

  let { params = {} } = $props();
  let detail = $state(null);
  let trend = $state([]);
  let detections = $state({ total: 0, detections: [] });
  let trendDays = $state(30);
  let loading = $state(true);
  let chartCanvas = $state(null);
  let chartInstance = $state(null);
  let page = $state(0);

  $effect(() => {
    if (params.sciName) loadAll();
  });

  async function loadAll() {
    loading = true;
    const sciName = decodeURIComponent(params.sciName);
    try {
      const [d, t, det] = await Promise.all([
        api.getSpeciesDetail(sciName),
        api.getSpeciesTrend(sciName, trendDays),
        api.getSpeciesDetections(sciName, 50, 0),
      ]);
      detail = d;
      trend = t;
      detections = det;
      page = 0;
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  async function loadTrend() {
    const sciName = decodeURIComponent(params.sciName);
    trend = await api.getSpeciesTrend(sciName, trendDays);
  }

  async function loadMore() {
    const sciName = decodeURIComponent(params.sciName);
    const next = await api.getSpeciesDetections(sciName, 50, detections.detections.length);
    detections = { total: next.total, detections: [...detections.detections, ...next.detections] };
  }

  function renderChart() {
    if (!chartCanvas || !trend.length) return;
    const ctx = chartCanvas.getContext('2d');
    const isDark = document.documentElement.classList.contains('dark');
    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: trend.map(t => t.date),
        datasets: [{
          label: 'Detections',
          data: trend.map(t => t.count),
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: trend.length > 60 ? 0 : 3,
          pointHoverRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? '#1f2937' : '#fff',
            titleColor: isDark ? '#f3f4f6' : '#111827',
            bodyColor: isDark ? '#d1d5db' : '#4b5563',
            borderColor: isDark ? '#374151' : '#e5e7eb',
            borderWidth: 1,
            cornerRadius: 8,
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: isDark ? '#9ca3af' : '#6b7280',
              maxTicksLimit: 8,
              maxRotation: 0,
            },
          },
          y: {
            beginAtZero: true,
            grid: { color: isDark ? '#1f2937' : '#f3f4f6' },
            ticks: { color: isDark ? '#9ca3af' : '#6b7280', precision: 0 },
          },
        },
      },
    });
  }

  $effect(() => { if (trend.length && chartCanvas) renderChart(); });

  function play(det) {
    currentAudio.set({
      url: det.audio_url,
      title: det.com_name,
      subtitle: `${formatDate(det.date)} ${formatTime(det.time)} - ${formatConfidence(det.confidence)}`,
    });
  }
</script>

{#if loading}
  <div class="text-center py-12 text-gray-400">Loading...</div>
{:else if !detail}
  <div class="text-center py-12 text-gray-400">Species not found</div>
{:else}
  <div class="space-y-6">
    <!-- Hero -->
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
      <div class="md:flex">
        {#if detail.image}
          <div class="md:w-72 h-56 md:h-auto shrink-0">
            <img src={detail.image.image_url} alt={detail.Com_Name} class="w-full h-full object-cover"/>
          </div>
        {/if}
        <div class="p-6 flex-1">
          <h1 class="text-2xl font-bold">{detail.Com_Name}</h1>
          <p class="text-gray-500 dark:text-gray-400 italic">{detail.Sci_Name}</p>
          <a href={detail.info_url} target="_blank" rel="noopener" class="text-sm text-green-600 dark:text-green-400 hover:underline mt-1 inline-block">
            Learn more
          </a>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
            <div>
              <p class="text-xs text-gray-400 uppercase">Total</p>
              <p class="text-xl font-bold">{detail.total_count?.toLocaleString()}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase">Today</p>
              <p class="text-xl font-bold">{detail.today_count}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase">This Week</p>
              <p class="text-xl font-bold">{detail.week_count}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 uppercase">Best Confidence</p>
              <p class="text-xl font-bold">{formatConfidence(detail.best_confidence)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Trend chart -->
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">Detection Trend</h2>
        <div class="flex gap-1">
          {#each [30, 90, 180, 365] as d}
            <button
              class="px-3 py-1 text-xs rounded-md transition-colors {trendDays === d ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 font-medium' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'}"
              onclick={() => { trendDays = d; loadTrend(); }}
            >{d}d</button>
          {/each}
        </div>
      </div>
      <div class="h-56">
        <canvas bind:this={chartCanvas}></canvas>
      </div>
    </div>

    <!-- Detection list -->
    <div class="space-y-3">
      <h2 class="text-lg font-semibold">All Detections ({detections.total})</h2>
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100 dark:border-gray-800 text-left">
              <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Date</th>
              <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Time</th>
              <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Confidence</th>
              <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400 w-10"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-800">
            {#each detections.detections as det}
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td class="px-4 py-2.5">{formatDate(det.date)}</td>
                <td class="px-4 py-2.5">{formatTime(det.time)}</td>
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <div class="w-16 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <div class="h-full rounded-full {confidenceBarColor(det.confidence)}" style="width:{det.confidence*100}%"></div>
                    </div>
                    <span>{formatConfidence(det.confidence)}</span>
                  </div>
                </td>
                <td class="px-4 py-2.5">
                  <button onclick={() => play(det)} class="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900 text-green-600 dark:text-green-400" aria-label="Play recording">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/></svg>
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if detections.detections.length < detections.total}
        <div class="text-center">
          <button onclick={loadMore} class="px-4 py-2 text-sm rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors">
            Load More
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
