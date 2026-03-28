<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import SpeciesCard from '../components/SpeciesCard.svelte';

  let species = $state([]);
  let filtered = $state([]);
  let search = $state('');
  let sortBy = $state('occurrences');
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      species = await api.getSpecies(sortBy);
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (search) {
      const q = search.toLowerCase();
      filtered = species.filter(s => s.Com_Name.toLowerCase().includes(q) || s.Sci_Name.toLowerCase().includes(q));
    } else {
      filtered = species;
    }
  });

  $effect(() => {
    // Re-fetch when sort changes
    sortBy;
    load();
  });

  onMount(load);
</script>

<div class="space-y-4">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="text-2xl font-bold">Species</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">{species.length} species detected</p>
    </div>
    <div class="flex gap-2">
      <input
        type="text"
        placeholder="Search..."
        bind:value={search}
        class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none"
      />
      <select bind:value={sortBy} class="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <option value="occurrences">Most Detected</option>
        <option value="confidence">Highest Confidence</option>
        <option value="date">Most Recent</option>
        <option value="alpha">Alphabetical</option>
      </select>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-400">Loading...</div>
  {:else if filtered.length === 0}
    <div class="text-center py-12 text-gray-400">No species found</div>
  {:else}
    <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
      {#each filtered as sp (sp.Sci_Name)}
        <SpeciesCard species={sp} />
      {/each}
    </div>
  {/if}
</div>
