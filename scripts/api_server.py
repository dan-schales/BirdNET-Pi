"""BirdNET-Pi REST API server built with FastAPI."""

import os
import re
import sqlite3
import json
import asyncio
import subprocess
import signal
from contextlib import asynccontextmanager
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from utils.helpers import get_settings, DB_PATH, BASE_PATH

# --- Configuration ---

SETTINGS = get_settings()
USER_HOME = os.path.expanduser("~")
EXTRACTED_DIR = os.path.join(USER_HOME, "BirdSongs", "Extracted")
CHARTS_DIR = os.path.join(EXTRACTED_DIR, "Charts")
BY_DATE_DIR = os.path.join(EXTRACTED_DIR, "By_Date")
FRONTEND_DIST = os.path.join(BASE_PATH, "frontend", "dist")
LABELS_PATH = os.path.join(BASE_PATH, "model", "l18n", "labels_en.json")

# Sensitive config keys to exclude from public API
SENSITIVE_KEYS = {"CADDY_PWD", "FLICKR_API_KEY", "FLICKR_FILTER_EMAIL", "BIRDWEATHER_ID"}
RECORDINGS_DIR = os.path.join(USER_HOME, "BirdSongs", "LivestreamRecordings")
RECORDING_PID_FILE = "/tmp/livestream_recording.pid"
SCHEDULES_FILE = os.path.join(BASE_PATH, "livestream_schedules.json")


# --- Database helpers ---

def get_db():
    """Get a read-only SQLite connection."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def query_all(sql, params=None):
    con = get_db()
    try:
        cur = con.execute(sql, params or {})
        rows = [dict(r) for r in cur.fetchall()]
    except sqlite3.Error:
        rows = []
    finally:
        con.close()
    return rows


def query_one(sql, params=None):
    rows = query_all(sql, params)
    return rows[0] if rows else None


# --- Image provider helpers ---

def _get_image_db_path(provider):
    if provider == "FLICKR":
        return os.path.join(BASE_PATH, "scripts", "flickr.db")
    return os.path.join(BASE_PATH, "scripts", "wikipedia.db")


def get_cached_image(sci_name):
    """Look up cached bird image from the image database."""
    provider = SETTINGS.get("IMAGE_PROVIDER", "WIKIPEDIA")
    db_path = _get_image_db_path(provider)
    if not os.path.exists(db_path):
        return None
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.execute(
            "SELECT sci_name, com_en_name, image_url, title, id, author_url, license_url "
            "FROM images WHERE sci_name = ?",
            (sci_name,),
        )
        row = cur.fetchone()
        con.close()
        if row:
            return dict(row)
    except sqlite3.Error:
        pass
    return None


# --- Labels ---

_labels_en = None

def get_labels_en():
    global _labels_en
    if _labels_en is None:
        try:
            with open(LABELS_PATH) as f:
                _labels_en = json.load(f)
        except Exception:
            _labels_en = {}
    return _labels_en


# --- WebSocket manager ---

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(data)
            except Exception:
                self.active.remove(ws)


ws_manager = ConnectionManager()


# --- Background detection watcher ---

_last_detection_id = None

async def detection_watcher():
    """Poll the database for new detections and broadcast via WebSocket."""
    global _last_detection_id
    while True:
        try:
            latest = query_one(
                "SELECT rowid, * FROM detections ORDER BY Date DESC, Time DESC LIMIT 1"
            )
            if latest and latest.get("rowid") != _last_detection_id:
                _last_detection_id = latest.get("rowid")
                latest.pop("rowid", None)
                await ws_manager.broadcast({"type": "new_detection", "data": latest})
        except Exception:
            pass
        await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    det_task = asyncio.create_task(detection_watcher())
    sched_task = asyncio.create_task(schedule_watcher())
    yield
    det_task.cancel()
    sched_task.cancel()


# --- App ---

app = FastAPI(title="BirdNET-Pi API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Routes ---

@app.get("/api/v2/summary")
def api_summary():
    total = query_one("SELECT COUNT(*) as total_detections FROM detections") or {"total_detections": 0}
    today = query_one("SELECT COUNT(*) as today_count FROM detections WHERE Date = DATE('now','localtime')") or {"today_count": 0}
    hour = query_one(
        "SELECT COUNT(*) as hour_count FROM detections "
        "WHERE Date = DATE('now','localtime') AND Time >= TIME('now','localtime','-1 hour')"
    ) or {"hour_count": 0}
    today_species = query_one(
        "SELECT COUNT(DISTINCT Sci_Name) as today_species FROM detections WHERE Date = DATE('now','localtime')"
    ) or {"today_species": 0}
    total_species = query_one("SELECT COUNT(DISTINCT Sci_Name) as total_species FROM detections") or {"total_species": 0}
    return {**total, **today, **hour, **today_species, **total_species}


@app.get("/api/v2/detections/today")
def api_detections_today(limit: int = Query(200, ge=1, le=1000)):
    rows = query_all(
        "SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name "
        "FROM detections WHERE Date = DATE('now','localtime') "
        "ORDER BY Time DESC LIMIT :limit",
        {"limit": limit},
    )
    return _enrich_detections(rows)


@app.get("/api/v2/detections/latest")
def api_detections_latest():
    row = query_one(
        "SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name "
        "FROM detections ORDER BY Date DESC, Time DESC LIMIT 1"
    )
    if not row:
        return None
    return _enrich_detections([row])[0]


@app.get("/api/v2/detections/history")
def api_detections_history(
    date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    limit: int = Query(500, ge=1, le=2000),
):
    rows = query_all(
        "SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name "
        "FROM detections WHERE Date = :date ORDER BY Time DESC LIMIT :limit",
        {"date": date, "limit": limit},
    )
    return _enrich_detections(rows)


@app.get("/api/v2/detections/hourly")
def api_detections_hourly(date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$")):
    if date is None:
        date_clause = "DATE('now','localtime')"
    else:
        date_clause = f"'{date}'"
    rows = query_all(
        f"SELECT CAST(SUBSTR(Time,1,2) AS INTEGER) as hour, COUNT(*) as count "
        f"FROM detections WHERE Date = {date_clause} GROUP BY hour ORDER BY hour"
    )
    # Fill in missing hours
    hourly = {r["hour"]: r["count"] for r in rows}
    return [{"hour": h, "count": hourly.get(h, 0)} for h in range(24)]


@app.get("/api/v2/species")
def api_species(
    sort: str = Query("occurrences", regex=r"^(occurrences|confidence|date|alpha)$"),
    date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
):
    where = "" if date is None else f'WHERE Date = "{date}"'
    order_map = {
        "occurrences": "COUNT(*) DESC",
        "confidence": "MAX(Confidence) DESC",
        "date": "MAX(Date) DESC, MAX(Time) DESC",
        "alpha": "Com_Name ASC",
    }
    order = order_map[sort]
    rows = query_all(
        f"SELECT Com_Name, Sci_Name, COUNT(*) as count, "
        f"MAX(Confidence) as max_confidence, MAX(Date) as last_date, "
        f"MIN(Date) as first_date "
        f"FROM detections {where} GROUP BY Sci_Name ORDER BY {order}"
    )
    for r in rows:
        image = get_cached_image(r["Sci_Name"])
        r["image_url"] = image["image_url"] if image else None
    return rows


@app.get("/api/v2/species/{sci_name}")
def api_species_detail(sci_name: str):
    sci_name = sci_name.replace("_", " ")
    overview = query_one(
        "SELECT Com_Name, Sci_Name, COUNT(*) as total_count, "
        "MAX(Confidence) as best_confidence "
        "FROM detections WHERE Sci_Name = :sn",
        {"sn": sci_name},
    )
    if not overview or not overview.get("Com_Name"):
        raise HTTPException(404, "Species not found")

    today_count = query_one(
        "SELECT COUNT(*) as today_count FROM detections "
        "WHERE Sci_Name = :sn AND Date = DATE('now','localtime')",
        {"sn": sci_name},
    ) or {"today_count": 0}

    week_count = query_one(
        "SELECT COUNT(*) as week_count FROM detections "
        "WHERE Sci_Name = :sn AND Date >= DATE('now','localtime','-7 days')",
        {"sn": sci_name},
    ) or {"week_count": 0}

    best = query_one(
        "SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name "
        "FROM detections WHERE Sci_Name = :sn ORDER BY Confidence DESC LIMIT 1",
        {"sn": sci_name},
    )

    image = get_cached_image(sci_name)
    labels = get_labels_en()
    info_name = labels.get(sci_name, overview["Com_Name"])

    return {
        **overview,
        **today_count,
        **week_count,
        "image": image,
        "best_recording": _enrich_detections([best])[0] if best else None,
        "info_url": f"https://allaboutbirds.org/guide/{info_name.replace(' ', '_').replace(chr(39), '')}",
    }


@app.get("/api/v2/species/{sci_name}/trend")
def api_species_trend(sci_name: str, days: int = Query(30, ge=1, le=1095)):
    sci_name = sci_name.replace("_", " ")
    rows = query_all(
        "SELECT Date as date, COUNT(*) as count FROM detections "
        "WHERE Sci_Name = :sn AND Date >= DATE('now','localtime', :offset) "
        "GROUP BY Date ORDER BY Date",
        {"sn": sci_name, "offset": f"-{days} days"},
    )
    # Fill missing dates with zeros
    data_map = {r["date"]: r["count"] for r in rows}
    today = datetime.now().date()
    return [
        {"date": (today - timedelta(days=i)).isoformat(), "count": data_map.get((today - timedelta(days=i)).isoformat(), 0)}
        for i in range(days - 1, -1, -1)
    ]


@app.get("/api/v2/species/{sci_name}/detections")
def api_species_detections(
    sci_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    sci_name = sci_name.replace("_", " ")
    rows = query_all(
        "SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name "
        "FROM detections WHERE Sci_Name = :sn ORDER BY Date DESC, Time DESC "
        "LIMIT :limit OFFSET :offset",
        {"sn": sci_name, "limit": limit, "offset": offset},
    )
    total = query_one(
        "SELECT COUNT(*) as total FROM detections WHERE Sci_Name = :sn",
        {"sn": sci_name},
    )
    return {"total": total["total"] if total else 0, "detections": _enrich_detections(rows)}


@app.get("/api/v2/charts/daily")
def api_daily_chart(date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$")):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    chart_file = os.path.join(CHARTS_DIR, f"Combo-{date}.png")
    if not os.path.exists(chart_file):
        raise HTTPException(404, "Chart not found for this date")
    return FileResponse(chart_file, media_type="image/png")


@app.get("/api/v2/weekly-report")
def api_weekly_report():
    this_week = query_all(
        "SELECT Com_Name, Sci_Name, COUNT(*) as count "
        "FROM detections WHERE Date >= DATE('now','localtime','-7 days') "
        "GROUP BY Sci_Name ORDER BY COUNT(*) DESC"
    )
    last_week = query_all(
        "SELECT Com_Name, Sci_Name, COUNT(*) as count "
        "FROM detections WHERE Date >= DATE('now','localtime','-14 days') "
        "AND Date < DATE('now','localtime','-7 days') "
        "GROUP BY Sci_Name ORDER BY COUNT(*) DESC"
    )
    last_week_map = {r["Sci_Name"]: r["count"] for r in last_week}

    report = []
    for r in this_week:
        prev = last_week_map.pop(r["Sci_Name"], 0)
        change = ((r["count"] - prev) / prev * 100) if prev > 0 else None
        report.append({
            "com_name": r["Com_Name"],
            "sci_name": r["Sci_Name"],
            "this_week": r["count"],
            "last_week": prev,
            "change_pct": round(change, 1) if change is not None else None,
            "is_new": prev == 0,
        })
    # Species that were here last week but not this week
    for sci, count in last_week_map.items():
        lw_entry = next((r for r in last_week if r["Sci_Name"] == sci), None)
        if lw_entry:
            report.append({
                "com_name": lw_entry["Com_Name"],
                "sci_name": sci,
                "this_week": 0,
                "last_week": count,
                "change_pct": -100.0,
                "is_new": False,
            })
    return report


@app.get("/api/v2/recordings")
def api_recordings(date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$")):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    date_dir = os.path.join(BY_DATE_DIR, date)
    if not os.path.isdir(date_dir):
        return []
    recordings = []
    for species_dir in sorted(Path(date_dir).iterdir()):
        if not species_dir.is_dir():
            continue
        species_name = species_dir.name.replace("_", " ")
        for audio_file in sorted(species_dir.iterdir(), reverse=True):
            if audio_file.suffix in (".mp3", ".wav", ".ogg", ".flac"):
                recordings.append({
                    "species": species_name,
                    "filename": audio_file.name,
                    "audio_url": f"/By_Date/{date}/{species_dir.name}/{audio_file.name}",
                    "spectrogram_url": f"/By_Date/{date}/{species_dir.name}/{audio_file.name}.png",
                    "date": date,
                })
    return recordings


@app.get("/api/v2/config")
def api_config():
    settings = get_settings(force_reload=True)
    return {k: v for k, v in dict(settings).items() if k not in SENSITIVE_KEYS}


@app.get("/api/v2/top-species")
def api_top_species(limit: int = Query(10, ge=1, le=50)):
    rows = query_all(
        "SELECT Com_Name, Sci_Name, COUNT(*) as count "
        "FROM detections WHERE Date = DATE('now','localtime') "
        "GROUP BY Sci_Name ORDER BY COUNT(*) DESC LIMIT :limit",
        {"limit": limit},
    )
    for r in rows:
        image = get_cached_image(r["Sci_Name"])
        r["image_url"] = image["image_url"] if image else None
    return rows


@app.get("/api/v2/dates")
def api_dates():
    """Return list of dates that have detections, most recent first."""
    rows = query_all(
        "SELECT DISTINCT Date as date, COUNT(*) as count FROM detections "
        "GROUP BY Date ORDER BY Date DESC LIMIT 365"
    )
    return rows


# --- Livestream recording ---

def _format_bytes(size):
    if size == 0:
        return "0 B"
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024:
            return f"{size:.2f} {unit}" if unit != 'B' else f"{size} B"
        size /= 1024
    return f"{size:.2f} TB"


RECORDING_STDERR_FILE = "/tmp/livestream_recording.stderr"

# Active timer-stop tasks keyed by PID file; allows cancellation on manual stop
_recording_timer_tasks = {}


def _is_recording():
    """Check if livestream recording is in progress."""
    if not os.path.exists(RECORDING_PID_FILE):
        return False, None, None, None, None
    try:
        with open(RECORDING_PID_FILE) as f:
            data = f.read().strip().split('\n')
        pid = int(data[0])
        filename = data[1] if len(data) > 1 else 'unknown'
        started = float(data[2]) if len(data) > 2 else 0
        max_duration = int(data[3]) if len(data) > 3 else 0
        os.kill(pid, 0)
        return True, pid, filename, started, max_duration
    except (ProcessLookupError, ValueError, PermissionError, OSError):
        try:
            os.unlink(RECORDING_PID_FILE)
        except OSError:
            pass
        return False, None, None, None, None


def _get_recording_error():
    """Read any ffmpeg stderr output for error reporting."""
    try:
        if os.path.exists(RECORDING_STDERR_FILE):
            with open(RECORDING_STDERR_FILE) as f:
                return f.read().strip()
    except OSError:
        pass
    return ""


def _cleanup_recording_files():
    """Remove PID and stderr files."""
    for path in (RECORDING_PID_FILE, RECORDING_STDERR_FILE):
        try:
            os.unlink(path)
        except OSError:
            pass


async def _auto_stop_recording(duration_seconds):
    """Background task that stops the recording after the timer expires."""
    try:
        await asyncio.sleep(duration_seconds)
        recording, pid, filename, _, _ = _is_recording()
        if not recording:
            return
        try:
            os.kill(pid, signal.SIGINT)
            await asyncio.sleep(1.0)
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass
        _cleanup_recording_files()
    except asyncio.CancelledError:
        pass
    finally:
        _recording_timer_tasks.pop(RECORDING_PID_FILE, None)


def _build_ffmpeg_cmd(duration):
    """Build the ffmpeg command for recording the Icecast stream.

    Re-encodes with libmp3lame rather than copy mode because ffmpeg's
    MP3 muxer doesn't flush data to disk when remuxing an infinite
    Icecast stream with -c:a copy.  Output goes to stdout (pipe:1)
    so that the calling Python process owns the output file handle,
    avoiding permission issues when the recordings directory was
    created by a different user.
    """
    cmd = [
        'ffmpeg', '-nostdin', '-loglevel', 'error',
        '-f', 'mp3', '-i', 'http://localhost:8000/stream',
        '-c:a', 'libmp3lame', '-b:a', '320k',
        '-flush_packets', '1',
    ]
    if duration > 0:
        cmd.extend(['-t', str(duration)])
    cmd.extend(['-f', 'mp3', 'pipe:1'])
    return cmd


def _parse_duration(raw):
    """Parse and clamp a duration value to a non-negative integer."""
    try:
        val = int(raw)
        return max(val, 0)
    except (TypeError, ValueError):
        return 0


@app.post("/api/v2/livestream/record/start")
async def api_livestream_start(request: Request):
    recording, _, _, _, _ = _is_recording()
    if recording:
        raise HTTPException(409, "Recording already in progress")

    try:
        body = await request.json()
    except Exception:
        body = {}
    prefix = re.sub(r'[^a-zA-Z0-9_-]', '', body.get('prefix', '')) or 'livestream'
    duration = _parse_duration(body.get('duration', 0))

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{prefix}_{timestamp}.mp3"
    filepath = os.path.join(RECORDINGS_DIR, filename)
    os.makedirs(RECORDINGS_DIR, mode=0o755, exist_ok=True)
    # Ensure we can write to the directory even if it was created by another user
    if not os.access(RECORDINGS_DIR, os.W_OK):
        raise HTTPException(500, f"No write permission to {RECORDINGS_DIR}")

    ffmpeg_cmd = _build_ffmpeg_cmd(duration)
    stderr_fh = open(RECORDING_STDERR_FILE, 'w')
    # Open output file in Python so the file is owned by the API server
    # user, avoiding permission issues with directories created by root.
    output_fh = open(filepath, 'wb')
    try:
        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=output_fh, stderr=stderr_fh
        )
    except FileNotFoundError:
        output_fh.close()
        stderr_fh.close()
        raise HTTPException(500, "ffmpeg not found on this system")

    # Verify ffmpeg is actually running after a brief delay
    await asyncio.sleep(0.5)
    ret = proc.poll()
    if ret is not None:
        output_fh.close()
        stderr_fh.close()
        error_msg = _get_recording_error()
        _cleanup_recording_files()
        if os.path.exists(filepath):
            try:
                os.unlink(filepath)
            except OSError:
                pass
        detail = f"ffmpeg exited immediately (code {ret})"
        if error_msg:
            detail += f": {error_msg}"
        raise HTTPException(500, detail)

    with open(RECORDING_PID_FILE, 'w') as f:
        f.write(f"{proc.pid}\n{filename}\n{datetime.now().timestamp()}\n{duration}")

    # Schedule auto-stop if timer duration is set (as a server-side backup;
    # ffmpeg -t handles the actual cutoff, but this cleans up the PID file)
    if duration > 0:
        task = asyncio.create_task(_auto_stop_recording(duration + 5))
        _recording_timer_tasks[RECORDING_PID_FILE] = task

    return {"status": "success", "message": "Recording started",
            "data": {"filename": filename, "pid": proc.pid,
                     "duration": duration}}


@app.post("/api/v2/livestream/record/stop")
async def api_livestream_stop():
    recording, pid, filename, _, _ = _is_recording()
    if not recording:
        raise HTTPException(404, "No recording in progress")

    # Cancel any pending timer task
    timer_task = _recording_timer_tasks.pop(RECORDING_PID_FILE, None)
    if timer_task:
        timer_task.cancel()

    try:
        os.kill(pid, signal.SIGINT)
        await asyncio.sleep(1.0)
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except ProcessLookupError:
        pass

    _cleanup_recording_files()

    filepath = os.path.join(RECORDINGS_DIR, filename)
    filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0

    return {"status": "success", "message": "Recording stopped",
            "data": {"filename": filename, "filesize": filesize,
                     "filesize_human": _format_bytes(filesize)}}


@app.get("/api/v2/livestream/record/status")
def api_livestream_status():
    recording, pid, filename, started, max_duration = _is_recording()
    if not recording:
        # Check if ffmpeg exited with errors since last check
        error_msg = _get_recording_error()
        if error_msg:
            _cleanup_recording_files()
            return {"status": "success", "recording": False,
                    "error": error_msg}
        return {"status": "success", "recording": False}

    filepath = os.path.join(RECORDINGS_DIR, filename)
    filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    elapsed = int(datetime.now().timestamp() - started) if started else 0

    data = {
        "filename": filename, "pid": pid, "filesize": filesize,
        "filesize_human": _format_bytes(filesize),
        "duration_seconds": elapsed,
    }
    if max_duration and max_duration > 0:
        data["max_duration"] = max_duration
        data["remaining_seconds"] = max(0, max_duration - elapsed)

    stderr_content = _get_recording_error()
    if stderr_content:
        data["error"] = stderr_content

    return {"status": "success", "recording": True, "data": data}


@app.get("/api/v2/livestream/recordings")
def api_livestream_recordings():
    if not os.path.isdir(RECORDINGS_DIR):
        return {"status": "success", "data": []}
    recs = []
    for f in sorted(Path(RECORDINGS_DIR).glob("*.mp3"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        st = f.stat()
        recs.append({
            "filename": f.name,
            "filesize": st.st_size,
            "filesize_human": _format_bytes(st.st_size),
            "created": datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            "duration_seconds": int(st.st_size / 40000),
        })
    return {"status": "success", "data": recs}


@app.get("/api/v2/livestream/recordings/{filename}")
def api_livestream_download(filename: str):
    if not re.match(r'^[a-zA-Z0-9_.-]+\.mp3$', filename):
        raise HTTPException(400, "Invalid filename")
    filepath = os.path.join(RECORDINGS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Recording not found")
    return FileResponse(filepath, media_type="audio/mpeg", filename=filename)


@app.patch("/api/v2/livestream/recordings/{filename}")
async def api_livestream_rename(filename: str, request: Request):
    if not re.match(r'^[a-zA-Z0-9_.-]+\.mp3$', filename):
        raise HTTPException(400, "Invalid filename")
    filepath = os.path.join(RECORDINGS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Recording not found")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid request body")

    new_name = body.get('filename', '')
    if not new_name:
        raise HTTPException(400, "New filename is required")
    # Ensure .mp3 extension
    if not new_name.endswith('.mp3'):
        new_name += '.mp3'
    if not re.match(r'^[a-zA-Z0-9_.-]+\.mp3$', new_name):
        raise HTTPException(400, "Invalid new filename (alphanumeric, underscore, hyphen, dot only)")

    new_path = os.path.join(RECORDINGS_DIR, new_name)
    if os.path.exists(new_path):
        raise HTTPException(409, "A recording with that name already exists")

    os.rename(filepath, new_path)
    return {"status": "success", "message": "Recording renamed",
            "data": {"old_filename": filename, "new_filename": new_name}}


@app.delete("/api/v2/livestream/recordings/{filename}")
def api_livestream_delete(filename: str):
    if not re.match(r'^[a-zA-Z0-9_.-]+\.mp3$', filename):
        raise HTTPException(400, "Invalid filename")
    filepath = os.path.join(RECORDINGS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Recording not found")
    os.unlink(filepath)
    return {"status": "success", "message": "Recording deleted"}


# --- Livestream schedule ---

def _load_schedules():
    """Load schedules from JSON file."""
    if not os.path.exists(SCHEDULES_FILE):
        return []
    try:
        with open(SCHEDULES_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_schedules(schedules):
    """Persist schedules to JSON file."""
    with open(SCHEDULES_FILE, 'w') as f:
        json.dump(schedules, f, indent=2)


def _validate_time(t):
    """Validate HH:MM format, return normalized string or None."""
    if not t:
        return None
    m = re.match(r'^(\d{1,2}):(\d{2})$', t.strip())
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def _validate_schedule(body):
    """Validate and normalize schedule fields. Returns (data, error)."""
    start_time = _validate_time(body.get('start_time', ''))
    if not start_time:
        return None, "start_time is required (HH:MM)"

    stop_time = _validate_time(body.get('stop_time', ''))
    duration = 0
    if body.get('duration'):
        try:
            duration = int(body['duration'])
            if duration < 1 or duration > 1440:
                return None, "duration must be 1-1440 minutes"
        except (TypeError, ValueError):
            return None, "duration must be an integer (minutes)"

    if not stop_time and not duration:
        return None, "Either stop_time (HH:MM) or duration (minutes) is required"
    if stop_time and duration:
        return None, "Provide stop_time or duration, not both"

    days = body.get('days', [0, 1, 2, 3, 4, 5, 6])
    if not isinstance(days, list) or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
        return None, "days must be a list of integers 0-6 (Mon=0, Sun=6)"
    if not days:
        return None, "At least one day must be selected"

    prefix = re.sub(r'[^a-zA-Z0-9_-]', '', body.get('prefix', '')) or 'scheduled'
    name = body.get('name', '').strip()[:100] or f"{prefix} {start_time}"
    enabled = body.get('enabled', True)

    one_off = body.get('one_off', False)

    data = {
        "start_time": start_time,
        "stop_time": stop_time,
        "duration": duration,
        "days": sorted(set(days)),
        "prefix": prefix,
        "name": name,
        "enabled": bool(enabled),
        "one_off": bool(one_off),
    }
    return data, None


async def _schedule_start_recording(schedule):
    """Start a recording for a triggered schedule."""
    recording, _, _, _, _ = _is_recording()
    if recording:
        return

    prefix = schedule.get('prefix', 'scheduled')
    if schedule.get('stop_time'):
        now = datetime.now()
        sh, sm = map(int, schedule['stop_time'].split(':'))
        stop_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        if stop_dt <= now:
            stop_dt += timedelta(days=1)
        duration = int((stop_dt - now).total_seconds())
    else:
        duration = schedule.get('duration', 0) * 60

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{prefix}_{timestamp}.mp3"
    filepath = os.path.join(RECORDINGS_DIR, filename)
    os.makedirs(RECORDINGS_DIR, mode=0o755, exist_ok=True)

    ffmpeg_cmd = _build_ffmpeg_cmd(duration)
    stderr_fh = open(RECORDING_STDERR_FILE, 'w')
    output_fh = open(filepath, 'wb')
    try:
        proc = subprocess.Popen(ffmpeg_cmd, stdout=output_fh, stderr=stderr_fh)
    except FileNotFoundError:
        output_fh.close()
        stderr_fh.close()
        return

    with open(RECORDING_PID_FILE, 'w') as f:
        f.write(f"{proc.pid}\n{filename}\n{datetime.now().timestamp()}\n{duration}")

    if duration > 0:
        task = asyncio.create_task(_auto_stop_recording(duration + 5))
        _recording_timer_tasks[RECORDING_PID_FILE] = task


async def schedule_watcher():
    """Background task that checks schedules every 30s and triggers recordings."""
    triggered_today = set()
    current_date = datetime.now().date()

    while True:
        try:
            now = datetime.now()
            # Reset triggered set at midnight
            if now.date() != current_date:
                triggered_today.clear()
                current_date = now.date()

            schedules = _load_schedules()
            current_time = now.strftime('%H:%M')
            current_day = now.weekday()

            for sched in schedules:
                if not sched.get('enabled', True):
                    continue
                sid = sched.get('id', '')
                if sid in triggered_today:
                    continue
                if sched.get('start_time') != current_time:
                    continue
                if current_day not in sched.get('days', []):
                    continue

                triggered_today.add(sid)
                await _schedule_start_recording(sched)

                if sched.get('one_off'):
                    all_scheds = _load_schedules()
                    for s in all_scheds:
                        if s.get('id') == sid:
                            s['enabled'] = False
                            break
                    _save_schedules(all_scheds)
        except Exception:
            pass

        await asyncio.sleep(30)


@app.get("/api/v2/livestream/schedules")
def api_schedules_list():
    return {"status": "success", "data": _load_schedules()}


@app.post("/api/v2/livestream/schedules")
async def api_schedules_create(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid request body")

    data, error = _validate_schedule(body)
    if error:
        raise HTTPException(400, error)

    data["id"] = str(uuid.uuid4())[:8]
    data["created"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    schedules = _load_schedules()
    schedules.append(data)
    _save_schedules(schedules)

    return {"status": "success", "message": "Schedule created", "data": data}


@app.put("/api/v2/livestream/schedules/{schedule_id}")
async def api_schedules_update(schedule_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid request body")

    schedules = _load_schedules()
    idx = next((i for i, s in enumerate(schedules) if s.get('id') == schedule_id), None)
    if idx is None:
        raise HTTPException(404, "Schedule not found")

    data, error = _validate_schedule(body)
    if error:
        raise HTTPException(400, error)

    data["id"] = schedule_id
    data["created"] = schedules[idx].get("created", "")
    schedules[idx] = data
    _save_schedules(schedules)

    return {"status": "success", "message": "Schedule updated", "data": data}


@app.patch("/api/v2/livestream/schedules/{schedule_id}")
async def api_schedules_toggle(schedule_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid request body")

    schedules = _load_schedules()
    idx = next((i for i, s in enumerate(schedules) if s.get('id') == schedule_id), None)
    if idx is None:
        raise HTTPException(404, "Schedule not found")

    if 'enabled' in body:
        schedules[idx]['enabled'] = bool(body['enabled'])
    _save_schedules(schedules)

    return {"status": "success", "message": "Schedule updated", "data": schedules[idx]}


@app.delete("/api/v2/livestream/schedules/{schedule_id}")
def api_schedules_delete(schedule_id: str):
    schedules = _load_schedules()
    new_schedules = [s for s in schedules if s.get('id') != schedule_id]
    if len(new_schedules) == len(schedules):
        raise HTTPException(404, "Schedule not found")
    _save_schedules(new_schedules)
    return {"status": "success", "message": "Schedule deleted"}


# --- WebSocket ---

@app.websocket("/api/v2/ws/detections")
async def ws_detections(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# --- Legacy v1 image endpoint ---

@app.get("/api/v1/image/{sci_name:path}")
def api_v1_image(sci_name: str):
    image = get_cached_image(sci_name)
    if not image:
        raise HTTPException(404, "No image found")
    return {"status": "success", "message": "successfully image data from database", "data": image}


# --- Helpers ---

def _enrich_detections(rows):
    """Add audio/spectrogram URLs and format confidence."""
    enriched = []
    for r in rows:
        com_name_safe = r["Com_Name"].replace(" ", "_").replace("'", "")
        enriched.append({
            "com_name": r["Com_Name"],
            "sci_name": r["Sci_Name"],
            "date": r["Date"],
            "time": r["Time"],
            "confidence": round(r["Confidence"], 4) if r["Confidence"] else 0,
            "file_name": r["File_Name"],
            "audio_url": f"/By_Date/{r['Date']}/{com_name_safe}/{r['File_Name']}",
            "spectrogram_url": f"/By_Date/{r['Date']}/{com_name_safe}/{r['File_Name']}.png",
        })
    return enriched


# --- Serve SPA ---

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/")
    @app.get("/{path:path}")
    def serve_spa(path: str = ""):
        # Don't catch API or static file routes
        if path.startswith(("api/", "By_Date/", "Charts/", "stream", "log", "stats", "terminal")):
            raise HTTPException(404)
        file_path = os.path.join(FRONTEND_DIST, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
