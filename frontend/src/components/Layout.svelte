<script>
  import Navbar from './Navbar.svelte';
  import Sidebar from './Sidebar.svelte';
  import AudioPlayerBar from './AudioPlayerBar.svelte';
  import { sidebarOpen } from '../lib/stores.js';
</script>

<div class="min-h-screen flex flex-col">
  <Navbar />
  <div class="flex flex-1 pt-16">
    <Sidebar />
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    {#if $sidebarOpen}
      <div
        class="fixed inset-0 bg-black/30 z-20 lg:hidden"
        onclick={() => sidebarOpen.set(false)}
      ></div>
    {/if}
    <main class="flex-1 lg:ml-64 p-4 md:p-6 pb-24 min-w-0">
      <slot />
    </main>
  </div>
  <AudioPlayerBar />
</div>
