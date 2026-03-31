const BASE = '';

async function fetchJson(url) {
  const res = await fetch(BASE + url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function putJson(url, data) {
  const res = await fetch(BASE + url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getSummary: () => fetchJson('/api/v2/summary'),
  getDetectionsToday: (limit = 200) => fetchJson(`/api/v2/detections/today?limit=${limit}`),
  getLatestDetection: () => fetchJson('/api/v2/detections/latest'),
  getDetectionsHistory: (date, limit = 500) => fetchJson(`/api/v2/detections/history?date=${date}&limit=${limit}`),
  getDetectionsHourly: (date = null) => fetchJson(`/api/v2/detections/hourly${date ? `?date=${date}` : ''}`),
  getSpecies: (sort = 'occurrences', date = null) => fetchJson(`/api/v2/species?sort=${sort}${date ? `&date=${date}` : ''}`),
  getSpeciesDetail: (sciName) => fetchJson(`/api/v2/species/${encodeURIComponent(sciName)}`),
  getSpeciesTrend: (sciName, days = 30) => fetchJson(`/api/v2/species/${encodeURIComponent(sciName)}/trend?days=${days}`),
  getSpeciesDetections: (sciName, limit = 100, offset = 0) => fetchJson(`/api/v2/species/${encodeURIComponent(sciName)}/detections?limit=${limit}&offset=${offset}`),
  getTopSpecies: (limit = 10) => fetchJson(`/api/v2/top-species?limit=${limit}`),
  getDailyChart: (date = null) => `/api/v2/charts/daily${date ? `?date=${date}` : ''}`,
  getWeeklyReport: () => fetchJson('/api/v2/weekly-report'),
  getRecordings: (date = null) => fetchJson(`/api/v2/recordings${date ? `?date=${date}` : ''}`),
  getConfig: () => fetchJson('/api/v2/config'),
  updateConfig: (updates) => putJson('/api/v2/config', updates),
  getDates: () => fetchJson('/api/v2/dates'),
  getImageUrl: (sciName) => fetchJson(`/api/v1/image/${encodeURIComponent(sciName)}`),
};

export function connectWebSocket(onMessage) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/api/v2/ws/detections`);
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onMessage(data);
    } catch {}
  };
  ws.onclose = () => {
    setTimeout(() => connectWebSocket(onMessage), 5000);
  };
  return ws;
}
