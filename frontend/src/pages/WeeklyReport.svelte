<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { speciesSlug } from '../lib/utils.js';

  let report = $state([]);
  let loading = $state(true);
  let sortBy = $state('this_week');

  async function load() {
    try {
      report = await api.getWeeklyReport();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  let sorted = $derived.by(() => {
    let list = [...report];
    if (sortBy === 'this_week') list.sort((a, b) => b.this_week - a.this_week);
    else if (sortBy === 'change') list.sort((a, b) => (b.change_pct ?? -200) - (a.change_pct ?? -200));
    else if (sortBy === 'alpha') list.sort((a, b) => a.com_name.localeCompare(b.com_name));
    return list;
  });

  let totalThis = $derived(report.reduce((s, r) => s + r.this_week, 0));
  let totalLast = $derived(report.reduce((s, r) => s + r.last_week, 0));
  let newSpecies = $derived(report.filter(r => r.is_new).length);

  onMount(load);
</script>

<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="text-2xl font-bold">Weekly Report</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">This week vs. last week comparison</p>
    </div>
    <select bind:value={sortBy} class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <option value="this_week">Most Detected</option>
      <option value="change">Biggest Change</option>
      <option value="alpha">Alphabetical</option>
    </select>
  </div>

  <!-- Summary cards -->
  <div class="grid grid-cols-3 gap-4">
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 text-center">
      <p class="text-sm text-gray-500 dark:text-gray-400">This Week</p>
      <p class="text-2xl font-bold text-green-600 dark:text-green-400">{totalThis.toLocaleString()}</p>
    </div>
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 text-center">
      <p class="text-sm text-gray-500 dark:text-gray-400">Last Week</p>
      <p class="text-2xl font-bold">{totalLast.toLocaleString()}</p>
    </div>
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 text-center">
      <p class="text-sm text-gray-500 dark:text-gray-400">New Species</p>
      <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">{newSpecies}</p>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-400">Loading...</div>
  {:else}
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-100 dark:border-gray-800 text-left">
            <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Species</th>
            <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400 text-right">This Week</th>
            <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400 text-right">Last Week</th>
            <th class="px-4 py-3 font-medium text-gray-500 dark:text-gray-400 text-right">Change</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 dark:divide-gray-800">
          {#each sorted as row}
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50">
              <td class="px-4 py-2.5">
                <a href="#/species/{speciesSlug(row.sci_name)}" class="hover:text-green-600 dark:hover:text-green-400">
                  {row.com_name}
                  {#if row.is_new}
                    <span class="ml-2 px-1.5 py-0.5 text-[10px] font-bold uppercase bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">New</span>
                  {/if}
                </a>
              </td>
              <td class="px-4 py-2.5 text-right font-medium">{row.this_week}</td>
              <td class="px-4 py-2.5 text-right text-gray-500">{row.last_week}</td>
              <td class="px-4 py-2.5 text-right font-medium">
                {#if row.change_pct === null}
                  <span class="text-blue-500">New</span>
                {:else if row.change_pct > 0}
                  <span class="text-green-600 dark:text-green-400">+{row.change_pct}%</span>
                {:else if row.change_pct < 0}
                  <span class="text-red-500">{row.change_pct}%</span>
                {:else}
                  <span class="text-gray-400">0%</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
