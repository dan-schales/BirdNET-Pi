<script>
  import { theme, sidebarOpen } from '../lib/stores.js';
  import ThemeToggle from './ThemeToggle.svelte';
</script>

<header class="fixed top-0 left-0 right-0 z-30 h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center px-4 gap-3">
  <button
    class="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
    onclick={() => sidebarOpen.update(v => !v)}
    aria-label="Toggle menu"
  >
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
    </svg>
  </button>

  <a href="#/" class="flex items-center gap-2 font-semibold text-lg text-green-700 dark:text-green-400">
    <svg class="w-7 h-7" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
    </svg>
    BirdNET-Pi
  </a>

  <div class="flex-1"></div>

  <ThemeToggle />
</header>
