<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { speciesSlug, formatDate } from '../lib/utils.js';

  let data = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let sortBy = $state('default');
  let minDetections = $state(25);
  let minDetectionsInput = $state(25);
  let minDetectionsTimer = null;
  let minConfidencePct = $state(75);          // applied (sent to API)
  let minConfidenceInput = $state(75);        // text-input-bound
  let minConfidenceTimer = null;
  // Multi-select status filter. Empty set means "ALL" (show everything).
  let selectedStatuses = $state(new Set());

  const STATUS_META = {
    present:           { label: 'Present',         badge: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300' },
    expected_now:      { label: 'Expected Now',    badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' },
    coming_soon:       { label: 'Coming Soon',     badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' },
    overdue:           { label: 'Overdue',         badge: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300' },
    late_season:       { label: 'Late Season',     badge: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300' },
    out_of_season:     { label: 'Out of Season',   badge: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400' },
    insufficient_data: { label: 'Not Enough Data', badge: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500' },
  };

  const FILTERS = [
    { id: 'expected_now',      label: 'Expected Now',
      desc: 'Historically detected within ±1 week of the current week, but not seen in the last 30 days.' },
    { id: 'coming_soon',       label: 'Coming Soon',
      desc: 'No history right around now, but past years show detections coming up in the next 2–8 weeks.' },
    { id: 'overdue',           label: 'Overdue',
      desc: 'Was around 2–6 weeks ago in past years but hasn’t been detected yet this year.' },
    { id: 'late_season',       label: 'Late Season',
      desc: 'Still around recently, but historically the active window is winding down.' },
    { id: 'present',           label: 'Present',
      desc: 'Detected within the last 14 days.' },
    { id: 'out_of_season',     label: 'Out of Season',
      desc: 'No nearby historical detections, and none expected for several weeks.' },
    { id: 'insufficient_data', label: 'Not Enough Data',
      desc: 'Too little recorded history to make a reliable seasonal call yet.' },
  ];

  const ALL_DESC = 'Show every species, regardless of seasonal status.';

  async function load() {
    loading = true;
    error = null;
    try {
      data = await api.getPredictions(minDetections, minConfidencePct / 100);
    } catch (e) {
      error = e.message || 'Failed to load predictions';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  // Debounce min-detections typing so we don't refetch on every keystroke.
  function applyMinDetections() {
    clearTimeout(minDetectionsTimer);
    minDetectionsTimer = setTimeout(() => {
      const n = parseInt(minDetectionsInput, 10);
      if (Number.isFinite(n) && n >= 1 && n !== minDetections) {
        minDetections = n;
        load();
      }
    }, 350);
  }

  function setMinPreset(n) {
    clearTimeout(minDetectionsTimer);
    minDetectionsInput = n;
    if (n !== minDetections) {
      minDetections = n;
      load();
    }
  }

  function applyMinConfidence() {
    clearTimeout(minConfidenceTimer);
    minConfidenceTimer = setTimeout(() => {
      let n = parseInt(minConfidenceInput, 10);
      if (!Number.isFinite(n)) return;
      n = Math.max(0, Math.min(100, n));
      if (n !== minConfidencePct) {
        minConfidencePct = n;
        load();
      }
    }, 350);
  }

  function setConfPreset(n) {
    clearTimeout(minConfidenceTimer);
    minConfidenceInput = n;
    if (n !== minConfidencePct) {
      minConfidencePct = n;
      load();
    }
  }

  function toggleStatus(status) {
    const next = new Set(selectedStatuses);
    if (next.has(status)) next.delete(status);
    else next.add(status);
    selectedStatuses = next;
  }

  function selectAll() {
    // Empty set means "show everything" — same effect as having every pill on.
    selectedStatuses = new Set();
  }

  function weekToMonth(week) {
    if (week === null || week === undefined) return '—';
    const d = new Date(2024, 0, 1 + week * 7);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  let species = $derived(data?.species ?? []);

  let allSelected = $derived(selectedStatuses.size === 0);

  let filtered = $derived.by(() => {
    if (!species.length) return [];
    if (allSelected) return species;
    return species.filter(s => selectedStatuses.has(s.status));
  });

  let sorted = $derived.by(() => {
    let list = [...filtered];
    if (sortBy === 'arrival') {
      list.sort((a, b) => (a.arrival_week ?? 99) - (b.arrival_week ?? 99));
    } else if (sortBy === 'peak') {
      list.sort((a, b) => (a.peak_week ?? 99) - (b.peak_week ?? 99));
    } else if (sortBy === 'last_seen') {
      list.sort((a, b) => (a.days_since_last_seen ?? 9999) - (b.days_since_last_seen ?? 9999));
    } else if (sortBy === 'alpha') {
      list.sort((a, b) => a.com_name.localeCompare(b.com_name));
    } else if (sortBy === 'years') {
      list.sort((a, b) => b.years_observed - a.years_observed);
    }
    return list;
  });

  let counts = $derived.by(() => {
    const c = { all: species.length };
    for (const s of species) c[s.status] = (c[s.status] ?? 0) + 1;
    c.actionable = (c.expected_now ?? 0) + (c.coming_soon ?? 0) + (c.overdue ?? 0);
    return c;
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
    <div>
      <h1 class="text-2xl font-bold">Seasonal Predictions</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        When species typically appear, based on your local detection history.
      </p>
    </div>
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div class="flex items-center gap-2"
           title="Hide species with fewer than this many qualifying detections.">
        <label class="text-xs text-gray-500 dark:text-gray-400" for="pred-min-det">Min detections</label>
        <input
          id="pred-min-det"
          type="number"
          min="1"
          max="100000"
          bind:value={minDetectionsInput}
          oninput={applyMinDetections}
          class="w-20 px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900" />
        <div class="flex gap-1">
          {#each [5, 25, 100, 500] as preset}
            <button type="button" onclick={() => setMinPreset(preset)}
                    class="px-2 py-1 text-[11px] rounded border transition-colors
                      {minDetections === preset
                        ? 'bg-green-600 text-white border-green-600'
                        : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}">
              {preset}
            </button>
          {/each}
        </div>
      </div>
      <div class="flex items-center gap-2"
           title="Exclude detections below this confidence from the seasonal model. Useful for ignoring noisy old recordings.">
        <label class="text-xs text-gray-500 dark:text-gray-400" for="pred-min-conf">Min confidence</label>
        <div class="relative">
          <input
            id="pred-min-conf"
            type="number"
            min="0"
            max="100"
            step="5"
            bind:value={minConfidenceInput}
            oninput={applyMinConfidence}
            class="w-20 pl-2 pr-6 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900" />
          <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">%</span>
        </div>
        <div class="flex gap-1">
          {#each [50, 75, 90] as preset}
            <button type="button" onclick={() => setConfPreset(preset)}
                    class="px-2 py-1 text-[11px] rounded border transition-colors
                      {minConfidencePct === preset
                        ? 'bg-green-600 text-white border-green-600'
                        : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}">
              {preset}%
            </button>
          {/each}
        </div>
      </div>
      <select bind:value={sortBy}
              class="px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <option value="default">Default Order</option>
        <option value="arrival">Arrival Week</option>
        <option value="peak">Peak Week</option>
        <option value="last_seen">Most Recent</option>
        <option value="years">Years Observed</option>
        <option value="alpha">Alphabetical</option>
      </select>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-400">Loading predictions...</div>
  {:else if error}
    <div class="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30 p-4 text-sm text-red-700 dark:text-red-300">
      {error}
    </div>
  {:else if data}
    <!-- Context strip -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-3">
        <p class="text-xs text-gray-500 dark:text-gray-400">Current Week</p>
        <p class="text-lg font-bold">Week {data.current_week}</p>
        <p class="text-[11px] text-gray-400">{weekToMonth(data.current_week)}</p>
      </div>
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-3">
        <p class="text-xs text-gray-500 dark:text-gray-400">Years of Data</p>
        <p class="text-lg font-bold">{data.years_in_data}</p>
        {#if data.years_in_data < 2}
          <p class="text-[11px] text-amber-600 dark:text-amber-400">Predictions improve with more years</p>
        {/if}
      </div>
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-3">
        <p class="text-xs text-gray-500 dark:text-gray-400">Tracked Species</p>
        <p class="text-lg font-bold">{species.length}</p>
      </div>
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-3">
        <p class="text-xs text-gray-500 dark:text-gray-400">Actionable</p>
        <p class="text-lg font-bold text-amber-600 dark:text-amber-400">{counts.actionable ?? 0}</p>
      </div>
    </div>

    <!-- Filter pills (multi-select). Empty selection = ALL behind the scenes. -->
    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onclick={selectAll}
        title={ALL_DESC}
        class="relative group px-3 py-1.5 text-xs font-medium rounded-full border transition-colors
          {allSelected
            ? 'bg-green-600 text-white border-green-600'
            : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}">
        All
        <span class="ml-1 opacity-70">{counts.all ?? 0}</span>
        <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 max-w-[80vw]
                     px-2.5 py-1.5 rounded bg-gray-900 dark:bg-gray-700 text-white text-[11px] leading-snug
                     opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity
                     z-20 shadow-lg whitespace-normal text-left font-normal">
          {ALL_DESC}
        </span>
      </button>
      {#each FILTERS as f}
        {@const active = selectedStatuses.has(f.id)}
        <button
          type="button"
          onclick={() => toggleStatus(f.id)}
          aria-pressed={active}
          title={f.desc}
          class="relative group px-3 py-1.5 text-xs font-medium rounded-full border transition-colors
            {active
              ? 'bg-green-600 text-white border-green-600'
              : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}">
          {f.label}
          <span class="ml-1 opacity-70">{counts[f.id] ?? 0}</span>
          <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 max-w-[80vw]
                       px-2.5 py-1.5 rounded bg-gray-900 dark:bg-gray-700 text-white text-[11px] leading-snug
                       opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity
                       z-20 shadow-lg whitespace-normal text-left font-normal">
            {f.desc}
          </span>
        </button>
      {/each}
      {#if !allSelected}
        <button type="button" onclick={selectAll}
                class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 underline-offset-2 hover:underline">
          Clear
        </button>
      {/if}
    </div>

    {#if sorted.length === 0}
      <div class="text-center py-12 text-gray-400 text-sm">
        No species in this category.
      </div>
    {:else}
      <!-- Predictions table -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-100 dark:border-gray-800 text-left">
                <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Species</th>
                <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Status</th>
                <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Arrival</th>
                <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Peak</th>
                <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Last Seen</th>
                <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400 hidden md:table-cell">Year-Round Pattern</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-800">
              {#each sorted as row (row.sci_name)}
                {@const meta = STATUS_META[row.status] ?? STATUS_META.out_of_season}
                <tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50 align-top"
                    style="content-visibility: auto; contain-intrinsic-size: auto 72px;">
                  <td class="px-4 py-3">
                    <a href="#/species/{speciesSlug(row.sci_name)}"
                       class="font-medium hover:text-green-600 dark:hover:text-green-400">
                      {row.com_name}
                    </a>
                    <div class="text-[11px] italic text-gray-400">{row.sci_name}</div>
                    <div class="text-[11px] text-gray-400 mt-0.5"
                         title="Detections counted at >= {minConfidencePct}% confidence">
                      {row.years_observed}y · {row.total_detections.toLocaleString()} detections @ {minConfidencePct}%+
                    </div>
                  </td>
                  <td class="px-4 py-3">
                    <span class="inline-block px-2 py-0.5 text-[11px] font-medium rounded {meta.badge}">
                      {meta.label}
                    </span>
                    {#if row.status === 'coming_soon' && row.weeks_until_expected}
                      <div class="text-[11px] text-gray-500 mt-1">in ~{row.weeks_until_expected}w</div>
                    {/if}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <div class="font-medium">Wk {row.arrival_week ?? '—'}</div>
                    <div class="text-[11px] text-gray-400">{weekToMonth(row.arrival_week)}</div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <div class="font-medium">Wk {row.peak_week ?? '—'}</div>
                    <div class="text-[11px] text-gray-400">{weekToMonth(row.peak_week)}</div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    {#if row.last_seen}
                      <div class="text-[12px]">{formatDate(row.last_seen.slice(0, 10))}</div>
                      <div class="text-[11px] text-gray-400">
                        {row.days_since_last_seen === 0 ? 'today'
                         : row.days_since_last_seen === 1 ? '1 day ago'
                         : `${row.days_since_last_seen}d ago`}
                      </div>
                    {:else}
                      <span class="text-gray-400">—</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 hidden md:table-cell w-[280px]">
                    <div class="relative flex gap-px items-end w-full h-7 bg-gray-50 dark:bg-gray-800/40 rounded px-0.5"
                         title="Detection frequency by week of year">
                      {#each row.frequency_by_week as v, i}
                        <div class="flex-1 flex flex-col justify-end h-full" title="Week {i}: {Math.round(v * 100)}% of years detected">
                          <div
                            class="{v > 0 ? 'bg-green-500 dark:bg-green-400' : 'bg-gray-300 dark:bg-gray-700'}"
                            style="height: {v > 0 ? Math.max(v * 100, 25) : 6}%">
                          </div>
                        </div>
                      {/each}
                      <!-- Faint band showing the +/- 1 week comparison window used by the classifier -->
                      <div class="absolute top-0 bottom-0 bg-amber-500/20 pointer-events-none rounded"
                           style="left: {((data.current_week - 1) / 53) * 100}%; width: {(3 / 53) * 100}%">
                      </div>
                      <!-- Solid line at the current week -->
                      <div class="absolute top-0 bottom-0 w-[2px] bg-amber-500 dark:bg-amber-400 pointer-events-none"
                           style="left: calc({((data.current_week + 0.5) / 53) * 100}% - 1px)"
                           title="Current week ({data.current_week})">
                      </div>
                    </div>
                    <div class="flex justify-between text-[10px] text-gray-400 mt-1 w-full px-0.5">
                      <span>Jan</span><span>Apr</span><span>Jul</span><span>Oct</span><span>Dec</span>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>

      <p class="text-[11px] text-gray-400">
        Predictions use only this BirdNET-Pi's detection history — no external
        datasets — and classify each species by whether it was historically
        recorded within ±2 weeks of the current week. Accuracy improves with
        more years of data; a future version may cross-reference Cornell's
        eBird data.
      </p>
    {/if}
  {/if}
</div>
