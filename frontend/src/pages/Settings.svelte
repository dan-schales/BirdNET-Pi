<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';

  let config = $state(null);
  let loading = $state(true);

  onMount(async () => {
    try {
      config = await api.getConfig();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  const sections = [
    {
      title: 'Location',
      fields: ['SITE_NAME', 'LATITUDE', 'LONGITUDE'],
    },
    {
      title: 'Detection',
      fields: ['MODEL', 'CONFIDENCE', 'SENSITIVITY', 'OVERLAP', 'SF_THRESH'],
    },
    {
      title: 'Recording',
      fields: ['REC_CARD', 'CHANNELS', 'RECORDING_LENGTH', 'AUDIOFMT', 'EXTRACTION_LENGTH'],
    },
    {
      title: 'Display',
      fields: ['DATABASE_LANG', 'COLOR_SCHEME', 'IMAGE_PROVIDER', 'INFO_SITE'],
    },
    {
      title: 'Notifications',
      fields: ['APPRISE_NOTIFY_EACH_DETECTION', 'APPRISE_NOTIFY_NEW_SPECIES', 'APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY', 'APPRISE_WEEKLY_REPORT'],
    },
    {
      title: 'Disk Management',
      fields: ['FULL_DISK', 'PURGE_THRESHOLD', 'MAX_FILES_SPECIES'],
    },
  ];

  function getField(key) {
    return config?.[key] ?? '';
  }

  function formatKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold">Settings</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400">Current BirdNET-Pi configuration (read-only view)</p>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-400">Loading...</div>
  {:else if !config}
    <div class="text-center py-12 text-gray-400">Could not load configuration</div>
  {:else}
    {#each sections as section}
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 dark:border-gray-800">
          <h2 class="font-semibold">{section.title}</h2>
        </div>
        <div class="divide-y divide-gray-50 dark:divide-gray-800">
          {#each section.fields as field}
            {#if config[field] !== undefined}
              <div class="px-5 py-3 flex items-center justify-between gap-4">
                <span class="text-sm text-gray-500 dark:text-gray-400">{formatKey(field)}</span>
                <span class="text-sm font-mono bg-gray-50 dark:bg-gray-800 px-2 py-1 rounded">{getField(field)}</span>
              </div>
            {/if}
          {/each}
        </div>
      </div>
    {/each}

    <!-- External tools links -->
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h2 class="font-semibold mb-3">System Tools</h2>
      <div class="grid sm:grid-cols-2 gap-3">
        <a href="/stats" target="_blank" class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700 transition-colors">
          <svg class="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          <div>
            <p class="text-sm font-medium">Advanced Statistics</p>
            <p class="text-xs text-gray-400">Streamlit analytics dashboard</p>
          </div>
        </a>
        <a href="/log" target="_blank" class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700 transition-colors">
          <svg class="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <div>
            <p class="text-sm font-medium">View Logs</p>
            <p class="text-xs text-gray-400">System log viewer</p>
          </div>
        </a>
        <a href="/terminal" target="_blank" class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700 transition-colors">
          <svg class="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          <div>
            <p class="text-sm font-medium">Web Terminal</p>
            <p class="text-xs text-gray-400">SSH-like terminal access</p>
          </div>
        </a>
        <a href="/phpsysinfo/" target="_blank" class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700 transition-colors">
          <svg class="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          <div>
            <p class="text-sm font-medium">System Info</p>
            <p class="text-xs text-gray-400">Hardware and OS details</p>
          </div>
        </a>
      </div>
    </div>
  {/if}
</div>
