# scripts/ - Backend Code

This directory contains the Python backend, PHP legacy web pages, shell service scripts, and utility modules.

## Key Files

### Python - Core Services

| File | Purpose |
|------|---------|
| `api_server.py` (508 lines) | FastAPI REST API + WebSocket server. Serves v2 endpoints, static frontend, image cache. Port 7007. |
| `birdnet_analysis.py` (151 lines) | Main analysis daemon. inotify watches StreamData/ for new WAVs, runs TFLite inference, queues detections for reporting. |
| `daily_plot.py` (204 lines) | Generates daily matplotlib/seaborn charts (species counts + hourly heatmap). Runs as daemon. |
| `plotly_streamlit.py` (464 lines) | Interactive Streamlit dashboard with Plotly charts. Served at /stats. |
| `species.py` (40 lines) | CLI tool to list species available at configured location via metadata model. |
| `send_test_notification.py` (80 lines) | Tests notification pipeline with mock or recent detection data. |

### Python - utils/ Modules

| Module | Purpose |
|--------|---------|
| `utils/analysis.py` (216 lines) | Audio loading (librosa), chunking (3-sec), TFLite inference, confidence filtering, human privacy filter. Entry: `run_analysis()`. |
| `utils/models.py` (247 lines) | TFLite model wrappers. Supports BirdNET V1, V2.4, Perch V2, BirdNET-Go. Metadata models for geographic/temporal species filtering. |
| `utils/reporting.py` (228 lines) | Post-detection actions: audio extraction (sox), spectrogram generation, SQLite INSERT, CSV logging, Apprise notifications, BirdWeather API POST. |
| `utils/notifications.py` (150 lines) | Apprise notification dispatch with template variables, per-species throttling, include/exclude lists, notification modes. |
| `utils/helpers.py` (117 lines) | Config loading from `/etc/birdnet/birdnet.conf`, language/font selection, model label loading, file discovery. |
| `utils/db.py` (83 lines) | Legacy SQLite read-only helpers (being replaced by api_server.py direct queries). |
| `utils/classes.py` (50 lines) | Data classes: `Detection` (metadata fields), `ParseFileName` (extracts date/time/stream from WAV filename format `YYYY-MM-DD-birdnet-[RTSP_id]-HH:MM:SS.wav`). |
| `utils/maintainer.py` (164 lines) | Language/label management. Wikipedia scraping for bird common names. Translation coverage tracking. |

### API Server Endpoints (api_server.py)

All v2 endpoints prefixed with `/api/v2/`:

```
GET  /summary                    - Total/today/hour/species counts
GET  /detections/today           - Today's detections (filterable)
GET  /detections/latest          - Most recent detection
GET  /detections/history?date=   - Historical detections by date
GET  /detections/hourly?date=    - Hourly aggregation
GET  /species?sort=              - Species list (sort: occurrences/confidence/date/alpha)
GET  /species/{sci_name}         - Species detail
GET  /species/{sci_name}/trend?days= - Detection trend data
GET  /species/{sci_name}/detections  - Paginated species detections
GET  /top-species?limit=         - Top N species today
GET  /charts/daily?date=         - Daily chart PNG
GET  /weekly-report              - Week-over-week comparison
GET  /recordings?date=           - Recording file list by date
GET  /config                     - Settings (sensitive keys filtered out)
GET  /dates                      - Available recording dates
POST /livestream/record/start    - Start recording livestream (ffmpeg from Icecast)
POST /livestream/record/stop     - Stop recording (SIGINT/SIGKILL)
GET  /livestream/record/status   - Recording status (filename, size, duration)
GET  /livestream/recordings      - List saved MP3 recordings
GET  /livestream/recordings/{f}  - Download a recording
DEL  /livestream/recordings/{f}  - Delete a recording
WS   /ws/detections              - Real-time detection stream (polls every 3s)

GET  /api/v1/image/{sci_name}    - Species image URL (Wikipedia/Flickr cache)
```

Static file mounts: `/By_Date/`, `/Charts/`, `/assets/`, frontend dist at `/`.

### Shell Scripts - Services

| Script | Purpose |
|--------|---------|
| `birdnet_recording.sh` | Audio capture via ffmpeg (RTSP) or arecord (local mic). Outputs 15-sec WAV chunks. |
| `livestream.sh` | Pipes audio to Icecast2 as MP3 stream. Optional frequency shift. |
| `spectrogram.sh` | inotify on `analyzing_now.txt`, generates live spectrograms via sox. |
| `birdnet_log.sh` | journalctl wrapper for formatted service log streaming. |

### Shell Scripts - Installation

| Script | Purpose |
|--------|---------|
| `install_birdnet.sh` (1662 lines) | Main installer: venv, deps, language labels, timezone. |
| `install_config.sh` (11200 lines) | Generates `/etc/birdnet/birdnet.conf` with interactive or scripted setup. |
| `install_services.sh` (13812 lines) | Installs system deps (Caddy, PHP, FFmpeg, sox, Icecast2), creates systemd units, generates Caddyfile, sets up DB. |
| `setup_frontend.sh` (59 lines) | Builds Svelte frontend and installs birdnet_api systemd service. |

### Shell Scripts - Maintenance

| Script | Purpose |
|--------|---------|
| `update_birdnet.sh` | Git pull + service restart. Auto-update support. |
| `backup_data.sh` (5838 lines) | Backup/restore of database + extracted audio. |
| `disk_check.sh` | Disk usage monitoring + auto-purge. |
| `disk_species_clean.sh` | Remove low-confidence extracted files. |
| `clear_all_data.sh` | Factory reset (deletes all data). |
| `cleanup.sh` | Remove transient files, keep only recent recordings. |
| `restart_services.sh` | Restart all BirdNET services. |
| `createdb.sh` | Initialize empty birds.db with schema + indexes. |

### PHP Files (Legacy Web Interface)

Large monolithic files - new features should NOT go here. Use the Svelte frontend + FastAPI instead.

| File | Purpose | Size |
|------|---------|------|
| `config.php` | Settings management UI | 31K lines |
| `play.php` | Audio playback interface | 28K lines |
| `todays_detections.php` | Daily detection list | 23K lines |
| `overview.php` | Dashboard overview | 27K lines |
| `spectrogram.php` | Spectrogram viewer | 19K lines |
| `species_tools.php` | Species management | 17K lines |
| `common.php` | Shared PHP utilities | 18K lines |
| `livestream_recording.php` | Livestream interface | 7K lines |
| `ebird.php` | eBird integration data | 247K lines |

## Analysis Pipeline Detail

```python
# birdnet_analysis.py main loop:
1. load_global_model()                    # Load TFLite model once
2. inotify watch ~/BirdSongs/StreamData/  # Watch for IN_CLOSE_WRITE
3. For each new .wav file:
   a. Write path to analyzing_now.txt     # Signal to spectrogram viewer
   b. run_analysis(file)                  # utils/analysis.py
      - readAudioData() via librosa at model's sample rate
      - splitSignal() into 3-sec chunks (with configurable overlap)
      - Model inference on each chunk → species + confidence scores
      - filter_humans() removes human speech within 3-sec window
      - Apply confidence threshold, species include/exclude lists
      - Geographic/temporal filtering via metadata model
   c. Queue detections for reporting thread
4. Reporting thread (handle_reporting_queue):
   - extract_detection() → sox trim + spectrogram PNG
   - write_to_db() → SQLite INSERT with retry
   - write_to_file() → CSV append
   - apprise() → notifications
   - bird_weather() → API POST with FLAC
   - Delete processed WAV
```

## Configuration Access Pattern

```python
from utils.helpers import get_settings
settings = get_settings()  # Cached, reads /etc/birdnet/birdnet.conf
# Returns dict with string values, PHP-style quotes stripped
# Access: settings['CONFIDENCE'], settings['LATITUDE'], etc.
```

## Notification Template Variables

Available in `body.txt` and notification title:
`$sciname`, `$comname`, `$confidencepct`, `$confidence`, `$date`, `$time`, `$week`, `$latitude`, `$longitude`, `$listenurl`, `$friendlyurl`, `$image`, `$flickrimage`, `$cutoff`, `$sens`, `$overlap`, `$reason`
