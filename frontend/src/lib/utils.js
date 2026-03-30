export function formatConfidence(val) {
  return `${Math.round(val * 100)}%`;
}

export function confidenceColor(val) {
  if (val >= 0.9) return 'text-green-600 dark:text-green-400';
  if (val >= 0.7) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-orange-600 dark:text-orange-400';
}

export function confidenceBarColor(val) {
  if (val >= 0.9) return 'bg-green-500';
  if (val >= 0.7) return 'bg-yellow-500';
  return 'bg-orange-500';
}

export function formatTime(timeStr) {
  if (!timeStr) return '';
  const [h, m] = timeStr.split(':');
  const hour = parseInt(h);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const h12 = hour % 12 || 12;
  return `${h12}:${m} ${ampm}`;
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

export function relativeTime(dateStr, timeStr) {
  if (!dateStr || !timeStr) return '';
  const then = new Date(`${dateStr}T${timeStr}`);
  const now = new Date();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return formatDate(dateStr);
}

export function speciesSlug(sciName) {
  return encodeURIComponent(sciName.replace(/ /g, '_'));
}
