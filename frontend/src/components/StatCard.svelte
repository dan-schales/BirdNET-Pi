<script>
  let { label, value, icon = '', subtext = '' } = $props();
</script>

<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 flex items-start gap-4">
  {#if icon}
    <div class="p-2.5 rounded-lg bg-green-50 dark:bg-green-950 text-green-600 dark:text-green-400 shrink-0">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d={icon}/>
      </svg>
    </div>
  {/if}
  <div class="min-w-0">
    <p class="text-sm text-gray-500 dark:text-gray-400">{label}</p>
    <p class="text-2xl font-bold mt-0.5">{value ?? '...'}</p>
    {#if subtext}
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtext}</p>
    {/if}
  </div>
</div>
