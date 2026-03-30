# frontend/ - Svelte 5 SPA

Modern single-page application replacing the legacy PHP UI. Uses Svelte 5 (runes syntax), Vite, Tailwind CSS 4, and Chart.js.

## Stack

- **Framework**: Svelte 5.25.3 (runes: `$state()`, `$derived`, `$effect()`)
- **Build**: Vite 6.3.1
- **CSS**: Tailwind CSS 4.1.3 (v4 - no tailwind.config.js, uses CSS-based config)
- **Charts**: Chart.js 4.4.8
- **Router**: svelte-spa-router 4.0.1 (hash-based: `#/path`)
- **No TypeScript** - plain JS with Svelte

## Directory Structure

```
frontend/
├── src/
│   ├── main.js              # Entry: mounts App to #app
│   ├── App.svelte           # Router with 9 routes
│   ├── app.css              # Global styles, Tailwind theme, dark mode
│   ├── components/
│   │   ├── Layout.svelte        # Page wrapper (navbar + sidebar + content + audio player)
│   │   ├── Navbar.svelte        # Top bar with logo, theme toggle
│   │   ├── Sidebar.svelte       # Nav menu, responsive collapse
│   │   ├── DetectionCard.svelte # Detection row: spectrogram, confidence bar, species link
│   │   ├── SpeciesCard.svelte   # Grid card: image, name, count
│   │   ├── StatCard.svelte      # Metric display: icon, label, value
│   │   ├── HourlyChart.svelte   # Chart.js bar chart, hour-by-hour
│   │   ├── AudioPlayerBar.svelte # Fixed bottom player: play/pause, progress, close
│   │   └── ThemeToggle.svelte   # Sun/moon icon button
│   ├── pages/
│   │   ├── Dashboard.svelte     # Overview: stat cards, hourly chart, latest detections, top species
│   │   ├── Detections.svelte    # Today's detections: search, filter, sort, real-time updates
│   │   ├── Species.svelte       # Species grid: search, sort by occurrences/confidence/date/alpha
│   │   ├── SpeciesDetail.svelte # Species page: hero, trend chart (30-365d), paginated detections
│   │   ├── History.svelte       # Date picker, hourly chart + detection list for selected date
│   │   ├── WeeklyReport.svelte  # This week vs last week comparison table
│   │   ├── Recordings.svelte    # Date-based recording list, group by species toggle
│   │   ├── Livestream.svelte    # Icecast2 audio player + stream recording (start/stop/list/download/delete)
│   │   └── Settings.svelte      # Read-only config display, links to external tools
│   └── lib/
│       ├── api.js               # REST client (26 endpoints) + WebSocket connection
│       ├── stores.js            # Svelte stores: theme, sidebarOpen, currentAudio
│       └── utils.js             # formatConfidence, confidenceColor, formatTime, relativeTime, speciesSlug
├── dist/                        # Production build output (served by Caddy)
├── index.html                   # SPA entry: <div id="app">
├── vite.config.js               # Svelte + Tailwind plugins, dev proxy config
├── svelte.config.js             # Vite preprocessor
├── postcss.config.js            # Empty (Tailwind v4 self-configures)
├── package.json                 # Dependencies and scripts
└── package-lock.json
```

## Routes

```
#/              → Dashboard
#/detections    → Detections (today)
#/species       → Species grid
#/species/:sciName → SpeciesDetail (URL-encoded scientific name)
#/history       → History (date picker)
#/weekly        → WeeklyReport
#/recordings    → Recordings
#/livestream    → Livestream
#/settings      → Settings
```

## Dev Proxy Configuration (vite.config.js)

```
/api      → http://localhost:7007  (FastAPI backend)
/By_Date  → http://localhost:7007  (extracted audio files)
/Charts   → http://localhost:7007  (daily chart PNGs)
/stream   → http://localhost:8000  (Icecast2 livestream)
```

## API Client (lib/api.js)

All functions return promises. Base URL is relative (empty string).

```javascript
// Summary & stats
fetchSummary()                    // GET /api/v2/summary
fetchTopSpecies(limit)            // GET /api/v2/top-species?limit=

// Detections
fetchTodayDetections()            // GET /api/v2/detections/today
fetchLatestDetection()            // GET /api/v2/detections/latest
fetchDetectionHistory(date)       // GET /api/v2/detections/history?date=
fetchHourlyDetections(date)       // GET /api/v2/detections/hourly?date=

// Species
fetchSpecies(sort)                // GET /api/v2/species?sort=
fetchSpeciesDetail(sciName)       // GET /api/v2/species/{sciName}
fetchSpeciesTrend(sciName, days)  // GET /api/v2/species/{sciName}/trend?days=
fetchSpeciesDetections(sciName, page, perPage) // GET /api/v2/species/{sciName}/detections

// Other
fetchWeeklyReport()               // GET /api/v2/weekly-report
fetchRecordings(date)             // GET /api/v2/recordings?date=
fetchAvailableDates()             // GET /api/v2/dates
fetchConfig()                     // GET /api/v2/config
fetchDailyChart(date)             // GET /api/v2/charts/daily?date=
getImageUrl(sciName)              // Returns /api/v1/image/{sciName} URL string

// WebSocket
connectDetectionWebSocket(onMessage) // WS /api/v2/ws/detections (auto-reconnect 5s)
```

## Stores (lib/stores.js)

```javascript
theme         // writable('dark') - persisted to localStorage, toggles document class
sidebarOpen   // writable(false) - mobile sidebar state
currentAudio  // writable(null) - { url, title } of playing track
```

## Styling Conventions

- Tailwind utility classes throughout (no custom CSS classes except in app.css)
- Dark mode via `dark:` prefix (class-based, toggled by theme store)
- Brand color: `--color-green-brand: #166534` (green-800 equivalent)
- Font: Inter, Segoe UI, system-ui fallback
- Backgrounds: gray-50 (light) / gray-950 (dark)
- Text: gray-900 (light) / gray-100 (dark)
- Accents: green-600 (light) / green-400 (dark)

## Key Patterns

- **Auto-refresh**: Dashboard polls every 30 seconds + WebSocket for immediate updates
- **WebSocket reconnect**: Auto-reconnects on close with 5-second delay
- **Lazy images**: Species images loaded from `/api/v1/image/{sciName}` with fallback
- **URL encoding**: Scientific names URL-encoded for route params (`speciesSlug()` in utils.js)
- **Confidence colors**: Green (>=75%), yellow (>=50%), red (<50%) via `confidenceColor()`
- **Audio player**: Global bottom bar, plays extracted clips, controlled via `currentAudio` store

## Development

```bash
npm install       # Install dependencies
npm run dev       # Dev server at localhost:5173 with API proxy
npm run build     # Production build to dist/
npm run preview   # Preview production build
```

## Known Gotchas

- Svelte 5 runes (`$state`, `$derived`, `$effect`) can cause `effect_update_depth_exceeded` if chart variables are reactive - keep Chart.js instances as plain variables, not `$state()`.
- Router is hash-based (`#/path`), not history-based. All internal links use hash format.
- Tailwind v4 uses CSS-based configuration (in app.css `@theme`), not `tailwind.config.js`.
- The frontend must be built (`npm run build`) for production; Caddy serves from `dist/`.
