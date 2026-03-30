import { writable } from 'svelte/store';

function createThemeStore() {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : null;
  const prefersDark = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const initial = stored || (prefersDark ? 'dark' : 'light');

  const { subscribe, set, update } = writable(initial);

  function applyTheme(theme) {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', theme === 'dark');
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('theme', theme);
    }
  }

  // Apply on init
  applyTheme(initial);

  return {
    subscribe,
    toggle: () => update(t => {
      const next = t === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      return next;
    }),
    set: (v) => {
      applyTheme(v);
      set(v);
    },
  };
}

export const theme = createThemeStore();
export const sidebarOpen = writable(false);
export const currentAudio = writable(null);
