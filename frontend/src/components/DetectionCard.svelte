<script>
  import { formatConfidence, confidenceBarColor, formatTime, relativeTime, speciesSlug } from '../lib/utils.js';
  import { currentAudio } from '../lib/stores.js';

  let { detection } = $props();

  function playAudio() {
    currentAudio.set({
      url: detection.audio_url,
      title: detection.com_name,
      subtitle: `${formatTime(detection.time)} - ${formatConfidence(detection.confidence)}`,
    });
  }
</script>

<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex gap-4 hover:border-green-300 dark:hover:border-green-700 transition-colors">
  <!-- Spectrogram thumbnail -->
  <button onclick={playAudio} class="shrink-0 w-20 h-20 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 relative group cursor-pointer">
    <img
      src={detection.spectrogram_url}
      alt=""
      class="w-full h-full object-cover"
      onerror={(e) => e.target.style.display = 'none'}
    />
    <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
      <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
        <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/>
      </svg>
    </div>
  </button>

  <!-- Info -->
  <div class="flex-1 min-w-0">
    <div class="flex items-start justify-between gap-2">
      <a href="#/species/{speciesSlug(detection.sci_name)}" class="font-semibold text-gray-900 dark:text-gray-100 hover:text-green-600 dark:hover:text-green-400 truncate">
        {detection.com_name}
      </a>
      <span class="text-xs text-gray-400 dark:text-gray-500 shrink-0">
        {relativeTime(detection.date, detection.time)}
      </span>
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400 italic">{detection.sci_name}</p>
    <!-- Confidence bar -->
    <div class="mt-2 flex items-center gap-2">
      <div class="flex-1 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          class="h-full rounded-full {confidenceBarColor(detection.confidence)} transition-all"
          style="width: {detection.confidence * 100}%"
        ></div>
      </div>
      <span class="text-xs font-medium {detection.confidence >= 0.9 ? 'text-green-600 dark:text-green-400' : detection.confidence >= 0.7 ? 'text-yellow-600 dark:text-yellow-400' : 'text-orange-500'}">
        {formatConfidence(detection.confidence)}
      </span>
    </div>
  </div>
</div>
