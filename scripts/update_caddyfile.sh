#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf
my_dir=$HOME/BirdNET-Pi/scripts
FRONTEND_DIR=$HOME/BirdNET-Pi/frontend/dist
set -x
[ -d /etc/caddy ] || mkdir /etc/caddy
if [ -f /etc/caddy/Caddyfile ];then
  cp /etc/caddy/Caddyfile{,.original}
fi
if ! [ -z ${CADDY_PWD} ];then
HASHWORD=$(caddy hash-password --plaintext ${CADDY_PWD})
cat << EOF > /etc/caddy/Caddyfile
http:// ${BIRDNETPI_URL} {
  # New SPA frontend
  handle / {
    root * ${FRONTEND_DIR}
    try_files {path} /index.html
    file_server
  }
  handle /assets/* {
    root * ${FRONTEND_DIR}
    file_server
  }

  # API server
  handle /api/* {
    reverse_proxy localhost:7007
  }

  # WebSocket support for API
  handle /api/v2/ws/* {
    reverse_proxy localhost:7007
  }

  # Static bird data files
  root * ${EXTRACTED}
  file_server browse
  handle /By_Date/* {
    file_server browse
  }
  handle /Charts/* {
    file_server browse
  }
  basicauth /Processed* {
    birdnet ${HASHWORD}
  }
  basicauth /scripts* {
    birdnet ${HASHWORD}
  }
  basicauth /stream {
    birdnet ${HASHWORD}
  }
  basicauth /phpsysinfo* {
    birdnet ${HASHWORD}
  }
  basicauth /terminal* {
    birdnet ${HASHWORD}
  }
  reverse_proxy /stream localhost:8000
  php_fastcgi unix//run/php/php-fpm.sock
  reverse_proxy /log* localhost:8080
  reverse_proxy /stats* localhost:8501
  reverse_proxy /terminal* localhost:8888
}
EOF
else
  cat << EOF > /etc/caddy/Caddyfile
http:// ${BIRDNETPI_URL} {
  # New SPA frontend
  handle / {
    root * ${FRONTEND_DIR}
    try_files {path} /index.html
    file_server
  }
  handle /assets/* {
    root * ${FRONTEND_DIR}
    file_server
  }

  # API server
  handle /api/* {
    reverse_proxy localhost:7007
  }

  # WebSocket support for API
  handle /api/v2/ws/* {
    reverse_proxy localhost:7007
  }

  # Static bird data files
  root * ${EXTRACTED}
  file_server browse
  handle /By_Date/* {
    file_server browse
  }
  handle /Charts/* {
    file_server browse
  }
  reverse_proxy /stream localhost:8000
  php_fastcgi unix//run/php/php-fpm.sock
  reverse_proxy /log* localhost:8080
  reverse_proxy /stats* localhost:8501
  reverse_proxy /terminal* localhost:8888
}
EOF
fi

sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo systemctl reload caddy
