<script>
  import { speciesSlug } from '../lib/utils.js';

  let { species } = $props();
  let imgError = $state(false);
</script>

<a
  href="#/species/{speciesSlug(species.Sci_Name)}"
  class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden hover:border-green-300 dark:hover:border-green-700 hover:shadow-md transition-all group"
>
  <div class="aspect-[4/3] bg-gray-100 dark:bg-gray-800 relative overflow-hidden">
    {#if species.image_url && !imgError}
      <img
        src={species.image_url}
        alt={species.Com_Name}
        class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        onerror={() => imgError = true}
        loading="lazy"
      />
    {:else}
      <div class="w-full h-full flex items-center justify-center text-gray-300 dark:text-gray-600">
        <svg class="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
      </div>
    {/if}
    <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3 pt-8">
      <p class="text-white font-semibold text-sm truncate">{species.Com_Name}</p>
      <p class="text-white/70 text-xs italic truncate">{species.Sci_Name}</p>
    </div>
  </div>
  <div class="p-3 flex items-center justify-between">
    <span class="text-xs text-gray-500 dark:text-gray-400">{species.count} detection{species.count !== 1 ? 's' : ''}</span>
    <span class="text-xs font-medium {species.max_confidence >= 0.9 ? 'text-green-600 dark:text-green-400' : species.max_confidence >= 0.7 ? 'text-yellow-600 dark:text-yellow-400' : 'text-orange-500'}">
      Best: {Math.round(species.max_confidence * 100)}%
    </span>
  </div>
</a>
