<?php
require_once 'scripts/common.php';
$config = get_config();
$site_name = get_sitename();
$color_scheme = get_color_scheme();
set_timezone();
$authenticated = is_authenticated();
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?php echo $site_name; ?> - Livestream</title>
<link rel="shortcut icon" sizes="85x85" href="images/bird.png" />
<link rel="stylesheet" href="<?php echo $color_scheme . '?v=' . date('n.d.y', filemtime($color_scheme)); ?>">
<style>
  .ls-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
  }
  .ls-header {
    text-align: center;
    margin-bottom: 24px;
  }
  .ls-header a { text-decoration: none; }
  .ls-header img { height: 50px; vertical-align: middle; margin-right: 10px; }
  .ls-header h1 { display: inline; font-size: 1.4em; vertical-align: middle; }
  .ls-back { display: inline-block; margin-top: 8px; font-size: 0.9em; }

  .ls-card {
    background: rgba(255,255,255,0.85);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  .ls-card h2 {
    margin: 0 0 16px 0;
    font-size: 1.1em;
    border-bottom: 2px solid rgba(0,0,0,0.1);
    padding-bottom: 8px;
  }

  .ls-player audio {
    width: 100%;
    margin-bottom: 8px;
  }
  .ls-status {
    font-size: 0.85em;
    color: #666;
    text-align: center;
  }

  .ls-rec-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }
  .ls-rec-controls input[type="text"] {
    flex: 1;
    min-width: 120px;
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 0.95em;
  }

  .ls-btn {
    padding: 8px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.95em;
    font-weight: bold;
    transition: opacity 0.2s;
  }
  .ls-btn:hover { opacity: 0.85; }
  .ls-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .ls-btn-record { background: #d32f2f; color: white; }
  .ls-btn-stop { background: #555; color: white; }
  .ls-btn-download { background: #1976d2; color: white; padding: 4px 12px; font-size: 0.85em; }
  .ls-btn-delete { background: #b71c1c; color: white; padding: 4px 12px; font-size: 0.85em; }

  .ls-recording-indicator {
    display: none;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: #ffebee;
    border-radius: 4px;
    margin-top: 12px;
    font-size: 0.9em;
  }
  .ls-recording-indicator.active { display: flex; }
  .ls-rec-dot {
    width: 12px; height: 12px;
    background: #d32f2f;
    border-radius: 50%;
    animation: ls-blink 1s infinite;
  }
  @keyframes ls-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .ls-files-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
  }
  .ls-files-table th, .ls-files-table td {
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid #eee;
    background: transparent;
  }
  .ls-files-table th {
    font-weight: bold;
    border-bottom: 2px solid #ccc;
  }
  .ls-files-table tr:hover td {
    background: rgba(0,0,0,0.03);
  }
  .ls-actions { white-space: nowrap; }
  .ls-actions .ls-btn { margin-left: 4px; }
  .ls-empty { text-align: center; color: #999; padding: 20px; }
  .ls-auth-note { text-align: center; color: #999; font-size: 0.85em; padding: 8px; }

  @media (max-width: 600px) {
    .ls-container { padding: 10px; }
    .ls-rec-controls { flex-direction: column; }
    .ls-rec-controls input[type="text"] { width: 100%; }
    .ls-files-table { font-size: 0.8em; }
    .ls-files-table th:nth-child(3), .ls-files-table td:nth-child(3) { display: none; }
  }
</style>
</head>
<body>
<div class="ls-container">

  <div class="ls-header">
    <a href="/">
      <img src="images/bird.png" alt="BirdNET-Pi">
      <h1><?php echo $site_name; ?></h1>
    </a>
    <br>
    <a class="ls-back" href="/">&larr; Back to Dashboard</a>
  </div>

  <!-- Live Audio Player -->
  <div class="ls-card">
    <h2>Live Audio Stream</h2>
    <div class="ls-player">
      <audio id="ls-audio" controls preload="none">
        <source src="/stream" type="audio/mpeg">
        Your browser does not support the audio element.
      </audio>
      <div class="ls-status" id="ls-stream-status">Click play to start listening</div>
    </div>
  </div>

  <!-- Recording Controls -->
  <div class="ls-card">
    <h2>Record Livestream</h2>
    <?php if ($authenticated): ?>
    <div class="ls-rec-controls">
      <input type="text" id="ls-prefix" placeholder="File prefix (default: livestream)" maxlength="50">
      <button class="ls-btn ls-btn-record" id="ls-rec-start" onclick="startRecording()">Start Recording</button>
      <button class="ls-btn ls-btn-stop" id="ls-rec-stop" onclick="stopRecording()" disabled>Stop Recording</button>
    </div>
    <div class="ls-recording-indicator" id="ls-rec-indicator">
      <div class="ls-rec-dot"></div>
      <span>Recording: <strong id="ls-rec-filename"></strong></span>
      <span id="ls-rec-size"></span>
      <span id="ls-rec-duration"></span>
    </div>
    <?php else: ?>
    <div class="ls-auth-note">Log in to enable recording controls.</div>
    <?php endif; ?>
  </div>

  <!-- Saved Recordings -->
  <div class="ls-card">
    <h2>Saved Recordings</h2>
    <div id="ls-recordings-list">
      <div class="ls-empty">Loading...</div>
    </div>
  </div>

</div>

<script>
var recordingPollTimer = null;
var authenticated = <?php echo $authenticated ? 'true' : 'false'; ?>;

// --- Audio player status ---
var audio = document.getElementById('ls-audio');
var statusEl = document.getElementById('ls-stream-status');
if (audio) {
  audio.addEventListener('playing', function() { statusEl.textContent = 'Streaming live audio...'; });
  audio.addEventListener('pause', function() { statusEl.textContent = 'Paused'; });
  audio.addEventListener('error', function() { statusEl.textContent = 'Stream unavailable - is the livestream service running?'; });
  audio.addEventListener('waiting', function() { statusEl.textContent = 'Buffering...'; });
}

// --- Recording controls ---
function startRecording() {
  var prefix = document.getElementById('ls-prefix').value.trim() || 'livestream';
  var btn = document.getElementById('ls-rec-start');
  btn.disabled = true;
  btn.textContent = 'Starting...';

  fetch('/api/v1/livestream/record/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({prefix: prefix})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.status === 'success') {
      setRecordingUI(true, data.data.filename);
      pollRecordingStatus();
    } else {
      alert(data.message || 'Failed to start recording');
      btn.disabled = false;
      btn.textContent = 'Start Recording';
    }
  })
  .catch(function(err) {
    alert('Error: ' + err.message);
    btn.disabled = false;
    btn.textContent = 'Start Recording';
  });
}

function stopRecording() {
  var btn = document.getElementById('ls-rec-stop');
  btn.disabled = true;
  btn.textContent = 'Stopping...';

  fetch('/api/v1/livestream/record/stop', {
    method: 'POST'
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    setRecordingUI(false);
    loadRecordings();
  })
  .catch(function(err) {
    alert('Error: ' + err.message);
  });
}

function setRecordingUI(recording, filename) {
  var startBtn = document.getElementById('ls-rec-start');
  var stopBtn = document.getElementById('ls-rec-stop');
  var indicator = document.getElementById('ls-rec-indicator');

  if (recording) {
    startBtn.disabled = true;
    startBtn.textContent = 'Recording...';
    stopBtn.disabled = false;
    stopBtn.textContent = 'Stop Recording';
    indicator.classList.add('active');
    if (filename) document.getElementById('ls-rec-filename').textContent = filename;
  } else {
    startBtn.disabled = false;
    startBtn.textContent = 'Start Recording';
    stopBtn.disabled = true;
    stopBtn.textContent = 'Stop Recording';
    indicator.classList.remove('active');
    if (recordingPollTimer) {
      clearInterval(recordingPollTimer);
      recordingPollTimer = null;
    }
  }
}

function pollRecordingStatus() {
  if (recordingPollTimer) clearInterval(recordingPollTimer);
  recordingPollTimer = setInterval(function() {
    fetch('/api/v1/livestream/record/status')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.recording) {
        document.getElementById('ls-rec-size').textContent = '(' + data.data.filesize_human + ')';
        var mins = Math.floor(data.data.duration_seconds / 60);
        var secs = data.data.duration_seconds % 60;
        document.getElementById('ls-rec-duration').textContent =
          mins + ':' + (secs < 10 ? '0' : '') + secs;
      } else {
        setRecordingUI(false);
        loadRecordings();
      }
    });
  }, 3000);
}

// --- Recordings list ---
function loadRecordings() {
  fetch('/api/v1/livestream/recordings')
  .then(function(r) { return r.json(); })
  .then(function(data) {
    var container = document.getElementById('ls-recordings-list');
    if (!data.data || data.data.length === 0) {
      container.innerHTML = '<div class="ls-empty">No recordings yet</div>';
      return;
    }
    var html = '<table class="ls-files-table"><thead><tr>' +
      '<th>Filename</th><th>Size</th><th>Duration</th><th>Date</th><th>Actions</th>' +
      '</tr></thead><tbody>';
    data.data.forEach(function(rec) {
      var mins = Math.floor(rec.duration_seconds / 60);
      var secs = rec.duration_seconds % 60;
      var duration = mins + ':' + (secs < 10 ? '0' : '') + secs;
      html += '<tr>' +
        '<td>' + escapeHtml(rec.filename) + '</td>' +
        '<td>' + rec.filesize_human + '</td>' +
        '<td>' + duration + '</td>' +
        '<td>' + rec.created + '</td>' +
        '<td class="ls-actions">' +
          '<a class="ls-btn ls-btn-download" href="/api/v1/livestream/recordings/' +
            encodeURIComponent(rec.filename) + '">Download</a>';
      if (authenticated) {
        html += ' <button class="ls-btn ls-btn-delete" onclick="deleteRecording(\'' +
          escapeHtml(rec.filename) + '\')">Delete</button>';
      }
      html += '</td></tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  })
  .catch(function() {
    document.getElementById('ls-recordings-list').innerHTML =
      '<div class="ls-empty">Failed to load recordings</div>';
  });
}

function deleteRecording(filename) {
  if (!confirm('Delete ' + filename + '?')) return;
  fetch('/api/v1/livestream/recordings/' + encodeURIComponent(filename), {
    method: 'DELETE'
  })
  .then(function(r) { return r.json(); })
  .then(function() { loadRecordings(); })
  .catch(function(err) { alert('Error: ' + err.message); });
}

function escapeHtml(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// --- Init ---
loadRecordings();

// Check if there's already a recording in progress
if (authenticated) {
  fetch('/api/v1/livestream/record/status')
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.recording) {
      setRecordingUI(true, data.data.filename);
      pollRecordingStatus();
    }
  });
}
</script>
</body>
</html>
