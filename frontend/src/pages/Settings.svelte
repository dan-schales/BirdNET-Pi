<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';

  let config = $state(null);
  let editedConfig = $state({});
  let loading = $state(true);
  let saving = $state(false);
  let saveResult = $state(null);

  let dirty = $derived(
    config && Object.keys(editedConfig).some(k => String(editedConfig[k]) !== String(config[k]))
  );

  onMount(async () => {
    try {
      config = await api.getConfig();
      editedConfig = { ...config };
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  const FIELD_META = {
    CONFIDENCE:        { type: 'range', min: 0, max: 1, step: 0.05, label: 'Confidence Threshold' },
    SENSITIVITY:       { type: 'range', min: 0.5, max: 2.0, step: 0.05, label: 'Sensitivity' },
    OVERLAP:           { type: 'range', min: 0, max: 3, step: 0.1, label: 'Overlap' },
    PRIVACY_THRESHOLD: { type: 'select', label: 'Privacy Threshold', options: [
      { value: '0', label: 'Off' }, { value: '1', label: '1%' },
      { value: '2', label: '2%' }, { value: '3', label: '3%' },
    ]},
    DETECT_HUMANS:     { type: 'toggle', label: 'Detect Humans',
      description: 'Save human sound detections to the database (excluded from BirdWeather)' },
    RECORDING_LENGTH:  { type: 'number', min: 3, max: 120, step: 1, label: 'Recording Length (s)' },
    EXTRACTION_LENGTH: { type: 'number', min: 3, max: 60, step: 1, label: 'Extraction Length (s)' },
    CHANNELS:          { type: 'number', min: 1, max: 6, step: 1, label: 'Channels' },
    FULL_DISK:         { type: 'select', label: 'Full Disk Action', options: [
      { value: 'purge', label: 'Purge old files' }, { value: 'keep', label: 'Keep all files' },
    ]},
    MAX_FILES_SPECIES: { type: 'number', min: 0, max: 10000, step: 1, label: 'Max Files per Species' },
    PURGE_THRESHOLD:   { type: 'number', min: 50, max: 99, step: 1, label: 'Purge Threshold (%)' },
    SITE_NAME:         { type: 'text', label: 'Site Name' },
    LATITUDE:          { type: 'number', min: -90, max: 90, step: 0.0001, label: 'Latitude' },
    LONGITUDE:         { type: 'number', min: -180, max: 180, step: 0.0001, label: 'Longitude' },
    DATABASE_LANG:     { type: 'text', label: 'Language' },
    COLOR_SCHEME:      { type: 'text', label: 'Color Scheme' },
    APPRISE_NOTIFY_EACH_DETECTION:       { type: 'toggle', label: 'Notify Each Detection' },
    APPRISE_NOTIFY_NEW_SPECIES:          { type: 'toggle', label: 'Notify New Species' },
    APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY: { type: 'toggle', label: 'Notify New Species Each Day' },
    APPRISE_WEEKLY_REPORT:               { type: 'toggle', label: 'Weekly Report' },
  };

  const READ_ONLY_KEYS = new Set([
    'MODEL', 'REC_CARD', 'AUDIOFMT', 'SF_THRESH', 'IMAGE_PROVIDER', 'INFO_SITE',
  ]);

  const sections = [
    { title: 'Location', fields: ['SITE_NAME', 'LATITUDE', 'LONGITUDE'] },
    { title: 'Detection', fields: ['MODEL', 'CONFIDENCE', 'SENSITIVITY', 'OVERLAP', 'SF_THRESH', 'PRIVACY_THRESHOLD', 'DETECT_HUMANS'] },
    { title: 'Recording', fields: ['REC_CARD', 'CHANNELS', 'RECORDING_LENGTH', 'AUDIOFMT', 'EXTRACTION_LENGTH'] },
    { title: 'Display', fields: ['DATABASE_LANG', 'COLOR_SCHEME', 'IMAGE_PROVIDER', 'INFO_SITE'] },
    { title: 'Notifications', fields: ['APPRISE_NOTIFY_EACH_DETECTION', 'APPRISE_NOTIFY_NEW_SPECIES', 'APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY', 'APPRISE_WEEKLY_REPORT'] },
    { title: 'Disk Management', fields: ['FULL_DISK', 'PURGE_THRESHOLD', 'MAX_FILES_SPECIES'] },
  ];

  function formatKey(key) {
    return FIELD_META[key]?.label ?? key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function isEditable(key) {
    return !READ_ONLY_KEYS.has(key) && FIELD_META[key];
  }

  function isToggleOn(value) {
    return String(value) === '1';
  }

  async function saveSettings() {
    saving = true;
    saveResult = null;
    try {
      const changes = {};
      for (const key of Object.keys(editedConfig)) {
        if (String(editedConfig[key]) !== String(config[key]) && !READ_ONLY_KEYS.has(key)) {
          changes[key] = editedConfig[key];
        }
      }
      if (Object.keys(changes).length === 0) return;
      const result = await api.updateConfig(changes);
      config = { ...editedConfig };
      saveResult = { type: 'success', message: `Settings saved. ${result.restart_required ? 'Restart services for changes to take effect.' : ''}` };
    } catch (e) {
      saveResult = { type: 'error', message: e.message || 'Failed to save settings' };
    } finally {
      saving = false;
      setTimeout(() => { saveResult = null; }, 8000);
    }
  }
</script>

<div class="space-y-6 pb-20">
  <div>
    <h1 class="text-2xl font-bold">Settings</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400">BirdNET-Pi configuration</p>
  </div>

  {#if saveResult}
    <div class="rounded-lg px-4 py-3 text-sm {saveResult.type === 'success' ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'}">
      {saveResult.message}
    </div>
  {/if}

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
            {#if editedConfig[field] !== undefined}
              <div class="px-5 py-3 flex items-center justify-between gap-4">
                <div class="min-w-0">
                  <span class="text-sm text-gray-500 dark:text-gray-400">{formatKey(field)}</span>
                  {#if FIELD_META[field]?.description}
                    <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{FIELD_META[field].description}</p>
                  {/if}
                </div>

                {#if !isEditable(field)}
                  <!-- Read-only -->
                  <span class="text-sm font-mono bg-gray-50 dark:bg-gray-800 px-2 py-1 rounded shrink-0">{editedConfig[field]}</span>

                {:else if FIELD_META[field].type === 'toggle'}
                  <!-- Toggle switch -->
                  <button
                    type="button"
                    onclick={() => { editedConfig[field] = isToggleOn(editedConfig[field]) ? '0' : '1'; }}
                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 {isToggleOn(editedConfig[field]) ? 'bg-green-600' : 'bg-gray-300 dark:bg-gray-600'}"
                    role="switch"
                    aria-checked={isToggleOn(editedConfig[field])}
                    aria-label={formatKey(field)}
                  >
                    <span class="pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform duration-200 {isToggleOn(editedConfig[field]) ? 'translate-x-5' : 'translate-x-0'}"></span>
                  </button>

                {:else if FIELD_META[field].type === 'range'}
                  <!-- Range slider -->
                  <div class="flex items-center gap-3 shrink-0">
                    <input
                      type="range"
                      min={FIELD_META[field].min}
                      max={FIELD_META[field].max}
                      step={FIELD_META[field].step}
                      bind:value={editedConfig[field]}
                      class="w-32 accent-green-600"
                    />
                    <span class="text-sm font-mono w-12 text-right">{Number(editedConfig[field]).toFixed(2)}</span>
                  </div>

                {:else if FIELD_META[field].type === 'select'}
                  <!-- Select dropdown -->
                  <select
                    bind:value={editedConfig[field]}
                    class="text-sm bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded px-2 py-1 shrink-0"
                  >
                    {#each FIELD_META[field].options as opt}
                      <option value={opt.value}>{opt.label}</option>
                    {/each}
                  </select>

                {:else if FIELD_META[field].type === 'number'}
                  <!-- Number input -->
                  <input
                    type="number"
                    min={FIELD_META[field].min}
                    max={FIELD_META[field].max}
                    step={FIELD_META[field].step}
                    bind:value={editedConfig[field]}
                    class="text-sm font-mono bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded px-2 py-1 w-28 text-right shrink-0"
                  />

                {:else}
                  <!-- Text input -->
                  <input
                    type="text"
                    bind:value={editedConfig[field]}
                    class="text-sm font-mono bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded px-2 py-1 w-40 shrink-0"
                  />
                {/if}
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

<!-- Sticky save bar -->
{#if dirty}
  <div class="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-5 py-3 flex items-center justify-end gap-4 z-50 shadow-lg">
    <span class="text-sm text-yellow-600 dark:text-yellow-400 mr-auto">You have unsaved changes</span>
    <button
      onclick={() => { editedConfig = { ...config }; }}
      class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
    >
      Discard
    </button>
    <button
      onclick={saveSettings}
      disabled={saving}
      class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
    >
      {saving ? 'Saving...' : 'Save Settings'}
    </button>
  </div>
{/if}
