<?php
/**
 * Livestream view - embedded version for views.php navigation
 * This renders the livestream content within the main app layout
 */
$authenticated = is_authenticated();
?>
<div class="livestream-view">

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
var lsAudio = document.getElementById('ls-audio');
var statusEl = document.getElementById('ls-stream-status');
if (lsAudio) {
  lsAudio.addEventListener('playing', function() { statusEl.textContent = 'Streaming live audio...'; });
  lsAudio.addEventListener('pause', function() { statusEl.textContent = 'Paused'; });
  lsAudio.addEventListener('error', function() { statusEl.textContent = 'Stream unavailable - is the livestream service running?'; });
  lsAudio.addEventListener('waiting', function() { statusEl.textContent = 'Buffering...'; });
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
