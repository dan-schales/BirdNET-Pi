<?php
/**
 * Livestream Recording API
 *
 * Endpoints:
 *   POST /api/v1/livestream/record/start  - Start recording the livestream
 *   POST /api/v1/livestream/record/stop   - Stop recording
 *   GET  /api/v1/livestream/record/status - Get recording status
 *   GET  /api/v1/livestream/recordings    - List saved recordings
 *   GET  /api/v1/livestream/recordings/{filename} - Download a recording
 *   DELETE /api/v1/livestream/recordings/{filename} - Delete a recording
 */

define('__ROOT__', dirname(dirname(__FILE__)));
require_once(__ROOT__ . '/scripts/common.php');

$config = get_config();
$home = get_home();
$recordings_dir = $home . '/BirdSongs/LivestreamRecordings';
$pidfile = '/tmp/livestream_recording.pid';

// Ensure recordings directory exists
if (!is_dir($recordings_dir)) {
    mkdir($recordings_dir, 0775, true);
}

$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$requestMethod = $_SERVER['REQUEST_METHOD'];

// Route: POST /api/v1/livestream/record/start
if ($requestMethod === 'POST' && $requestUri === '/api/v1/livestream/record/start') {
    ensure_authenticated('You must be authenticated to start recording');

    if (is_recording($pidfile)) {
        json_response(409, ['status' => 'error', 'message' => 'Recording is already in progress']);
        exit;
    }

    // Get optional filename prefix from POST body
    $input = json_decode(file_get_contents('php://input'), true);
    $prefix = isset($input['prefix']) ? preg_replace('/[^a-zA-Z0-9_-]/', '', $input['prefix']) : 'livestream';

    $timestamp = date('Y-m-d_H-i-s');
    $filename = "{$prefix}_{$timestamp}.mp3";
    $filepath = "{$recordings_dir}/{$filename}";

    // Record from the Icecast stream using ffmpeg
    $ice_pwd = isset($config['ICE_PWD']) ? $config['ICE_PWD'] : 'birdnetpi';
    $cmd = "ffmpeg -nostdin -loglevel error -i http://source:{$ice_pwd}@localhost:8000/stream -acodec copy \"{$filepath}\" > /dev/null 2>&1 & echo $!";
    $pid = trim(shell_exec($cmd));

    if ($pid) {
        file_put_contents($pidfile, $pid . "\n" . $filename);
        json_response(200, [
            'status' => 'success',
            'message' => 'Recording started',
            'data' => ['filename' => $filename, 'pid' => (int)$pid]
        ]);
    } else {
        json_response(500, ['status' => 'error', 'message' => 'Failed to start recording']);
    }
    exit;
}

// Route: POST /api/v1/livestream/record/stop
if ($requestMethod === 'POST' && $requestUri === '/api/v1/livestream/record/stop') {
    ensure_authenticated('You must be authenticated to stop recording');

    if (!is_recording($pidfile)) {
        json_response(404, ['status' => 'error', 'message' => 'No recording in progress']);
        exit;
    }

    $piddata = explode("\n", trim(file_get_contents($pidfile)));
    $pid = $piddata[0];
    $filename = isset($piddata[1]) ? $piddata[1] : 'unknown';

    // Send SIGINT for clean ffmpeg shutdown
    posix_kill((int)$pid, 2); // SIGINT
    usleep(500000); // wait 500ms for clean shutdown

    // If still running, force kill
    if (posix_kill((int)$pid, 0)) {
        posix_kill((int)$pid, 9); // SIGKILL
    }

    unlink($pidfile);

    $filepath = "{$recordings_dir}/{$filename}";
    $filesize = file_exists($filepath) ? filesize($filepath) : 0;

    json_response(200, [
        'status' => 'success',
        'message' => 'Recording stopped',
        'data' => [
            'filename' => $filename,
            'filesize' => $filesize,
            'filesize_human' => format_bytes($filesize)
        ]
    ]);
    exit;
}

// Route: GET /api/v1/livestream/record/status
if ($requestMethod === 'GET' && $requestUri === '/api/v1/livestream/record/status') {
    if (is_recording($pidfile)) {
        $piddata = explode("\n", trim(file_get_contents($pidfile)));
        $pid = $piddata[0];
        $filename = isset($piddata[1]) ? $piddata[1] : 'unknown';
        $filepath = "{$recordings_dir}/{$filename}";
        $filesize = file_exists($filepath) ? filesize($filepath) : 0;
        $started = file_exists($filepath) ? filemtime($filepath) : time();

        json_response(200, [
            'status' => 'success',
            'recording' => true,
            'data' => [
                'filename' => $filename,
                'pid' => (int)$pid,
                'filesize' => $filesize,
                'filesize_human' => format_bytes($filesize),
                'duration_seconds' => time() - $started
            ]
        ]);
    } else {
        json_response(200, ['status' => 'success', 'recording' => false]);
    }
    exit;
}

// Route: GET /api/v1/livestream/recordings
if ($requestMethod === 'GET' && $requestUri === '/api/v1/livestream/recordings') {
    $files = glob("{$recordings_dir}/*.mp3");
    $recordings = [];
    foreach ($files as $file) {
        $recordings[] = [
            'filename' => basename($file),
            'filesize' => filesize($file),
            'filesize_human' => format_bytes(filesize($file)),
            'created' => date('Y-m-d H:i:s', filemtime($file)),
            'duration_seconds' => get_mp3_duration($file)
        ];
    }
    // Sort by newest first
    usort($recordings, function($a, $b) {
        return strcmp($b['created'], $a['created']);
    });

    json_response(200, ['status' => 'success', 'data' => $recordings]);
    exit;
}

// Route: GET /api/v1/livestream/recordings/{filename}
if ($requestMethod === 'GET' && preg_match('#^/api/v1/livestream/recordings/([a-zA-Z0-9_.-]+\.mp3)$#', $requestUri, $matches)) {
    $filename = $matches[1];
    $filepath = "{$recordings_dir}/{$filename}";

    if (!file_exists($filepath)) {
        json_response(404, ['status' => 'error', 'message' => 'File not found']);
        exit;
    }

    header('Content-Type: audio/mpeg');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    header('Content-Length: ' . filesize($filepath));
    readfile($filepath);
    exit;
}

// Route: DELETE /api/v1/livestream/recordings/{filename}
if ($requestMethod === 'DELETE' && preg_match('#^/api/v1/livestream/recordings/([a-zA-Z0-9_.-]+\.mp3)$#', $requestUri, $matches)) {
    ensure_authenticated('You must be authenticated to delete recordings');
    $filename = $matches[1];
    $filepath = "{$recordings_dir}/{$filename}";

    if (!file_exists($filepath)) {
        json_response(404, ['status' => 'error', 'message' => 'File not found']);
        exit;
    }

    unlink($filepath);
    json_response(200, ['status' => 'success', 'message' => 'Recording deleted']);
    exit;
}

// No route matched
json_response(404, ['status' => 'error', 'message' => 'Endpoint not found']);

// --- Helper functions ---

function is_recording($pidfile) {
    if (!file_exists($pidfile)) return false;
    $piddata = explode("\n", trim(file_get_contents($pidfile)));
    $pid = (int)$piddata[0];
    // Check if the process is actually running
    if ($pid > 0 && posix_kill($pid, 0)) {
        return true;
    }
    // Stale pidfile - clean up
    unlink($pidfile);
    return false;
}

function json_response($code, $data) {
    http_response_code($code);
    header('Content-Type: application/json');
    echo json_encode($data);
}

function format_bytes($bytes) {
    if ($bytes >= 1073741824) return round($bytes / 1073741824, 2) . ' GB';
    if ($bytes >= 1048576) return round($bytes / 1048576, 2) . ' MB';
    if ($bytes >= 1024) return round($bytes / 1024, 2) . ' KB';
    return $bytes . ' B';
}

function get_mp3_duration($filepath) {
    $size = filesize($filepath);
    // Estimate duration: 320kbps MP3 = 40KB/s
    return (int)round($size / 40000);
}
