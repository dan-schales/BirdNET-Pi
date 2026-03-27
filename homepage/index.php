<?php

$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if (strpos($requestUri, '/api/v1/') === 0) {
  if (strpos($requestUri, '/api/v1/livestream/') === 0) {
    include_once 'scripts/livestream_recording.php';
  } else {
    include_once 'scripts/api.php';
  }
  die();
}

if ($requestUri === '/livestream' || $requestUri === '/livestream/') {
  include_once 'livestream.php';
  die();
}

/* Prevent XSS input */
$_GET   = filter_input_array(INPUT_GET, FILTER_SANITIZE_STRING);
$_POST  = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
require_once 'scripts/common.php';
$config = get_config();
$site_name = get_sitename();
$color_scheme = get_color_scheme();
set_timezone();

?>
<!DOCTYPE html>
<html lang="en">
<head>
<title><?php echo $site_name; ?></title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link id="iconLink" rel="shortcut icon" sizes=85x85 href="images/bird.png" />
<link rel="stylesheet" href="<?php echo $color_scheme . '?v=' . date('n.d.y', filemtime($color_scheme)); ?>">
<link rel="stylesheet" type="text/css" href="static/dialog-polyfill.css" />
</head>
<body>
<header class="app-header">
  <div class="header-left">
    <a href="https://github.com/Nachtzuster/BirdNET-Pi.git" target="_blank" class="logo-link">
      <img src="images/bird.png" alt="BirdNET-Pi" class="header-logo">
    </a>
    <a href="/" class="site-title">
      <img class="header-wordmark" src="images/bnp.png" alt="BirdNET-Pi">
      <span class="site-name"><?php echo $site_name; ?></span>
    </a>
  </div>
  <div class="header-right">
<?php
if(isset($_GET['stream'])){
  ensure_authenticated('You cannot listen to the live audio stream');
  echo '<div class="live-audio-player">
    <span class="live-badge">LIVE</span>
    <audio controls autoplay><source src="/stream"></audio>
    <a href="/" class="stop-stream-btn" title="Stop streaming">&#x2715;</a>
  </div>';
} else {
  echo '<form action="index.php" method="GET" class="header-audio-form">
    <button type="submit" name="stream" value="play" class="header-btn live-audio-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
      Live Audio
    </button>
  </form>';
}
?>
  </div>
</header>
<?php
if(isset($_GET['filename'])) {
  $filename = $_GET['filename'];
  echo "<iframe src=\"views.php?view=Recordings&filename=$filename\"></iframe>";
} else {
  echo "<iframe src=\"views.php\"></iframe>";
}
?>
</body>
</html>
