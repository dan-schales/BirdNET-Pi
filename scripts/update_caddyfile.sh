#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf
BIRDNET_HOME=$(getent passwd "${BIRDNET_USER}" | cut -d: -f6)
my_dir=${BIRDNET_HOME}/BirdNET-Pi/scripts
FRONTEND_DIR=${BIRDNET_HOME}/BirdNET-Pi/frontend/dist
set -x
[ -d /etc/caddy ] || mkdir /etc/caddy
if [ -f /etc/caddy/Caddyfile ];then
  cp /etc/caddy/Caddyfile{,.original}
fi
if ! [ -z ${CADDY_PWD} ];then
HASHWORD=$(caddy hash-password --plaintext ${CADDY_PWD})
cat << EOF > /etc/caddy/Caddyfile
http:// ${BIRDNETPI_URL} {
  # API server
  @api path /api/*
  handle @api {
    reverse_proxy localhost:7007
  }

  # Static bird data files
  @bydate path /By_Date/*
  handle @bydate {
    root * ${EXTRACTED}
    file_server browse
  }
  @charts path /Charts/*
  handle @charts {
    root * ${EXTRACTED}
    file_server browse
  }

  # Authenticated routes
  @processed path /Processed*
  handle @processed {
    basicauth {
      birdnet ${HASHWORD}
    }
    root * ${EXTRACTED}
    file_server browse
  }
  @adminscripts path /scripts*
  handle @adminscripts {
    basicauth {
      birdnet ${HASHWORD}
    }
    root * ${EXTRACTED}
    php_fastcgi unix//run/php/php-fpm.sock
  }
  @sysinfo path /phpsysinfo*
  handle @sysinfo {
    basicauth {
      birdnet ${HASHWORD}
    }
    root * ${EXTRACTED}
    file_server browse
  }
  @terminal path /terminal*
  handle @terminal {
    basicauth {
      birdnet ${HASHWORD}
    }
    reverse_proxy localhost:8888
  }
  @stream path /stream
  handle @stream {
    basicauth {
      birdnet ${HASHWORD}
    }
    reverse_proxy localhost:8000
  }

  # Proxied services
  @log path /log*
  handle @log {
    reverse_proxy localhost:8080
  }
  @stats path /stats*
  handle @stats {
    reverse_proxy localhost:8501
  }

  # Legacy PHP
  @legacyphp path /views.php*
  handle @legacyphp {
    root * ${EXTRACTED}
    php_fastcgi unix//run/php/php-fpm.sock
  }

  # SPA frontend — catch-all fallback
  handle {
    root * ${FRONTEND_DIR}
    try_files {path} /index.html
    file_server
  }
}
EOF
else
  cat << EOF > /etc/caddy/Caddyfile
http:// ${BIRDNETPI_URL} {
  # API server
  @api path /api/*
  handle @api {
    reverse_proxy localhost:7007
  }

  # Static bird data files
  @bydate path /By_Date/*
  handle @bydate {
    root * ${EXTRACTED}
    file_server browse
  }
  @charts path /Charts/*
  handle @charts {
    root * ${EXTRACTED}
    file_server browse
  }

  # Proxied services
  @stream path /stream
  handle @stream {
    reverse_proxy localhost:8000
  }
  @log path /log*
  handle @log {
    reverse_proxy localhost:8080
  }
  @stats path /stats*
  handle @stats {
    reverse_proxy localhost:8501
  }
  @terminal path /terminal*
  handle @terminal {
    reverse_proxy localhost:8888
  }

  # Legacy PHP
  @legacyphp path /views.php*
  handle @legacyphp {
    root * ${EXTRACTED}
    php_fastcgi unix//run/php/php-fpm.sock
  }

  # SPA frontend — catch-all fallback
  handle {
    root * ${FRONTEND_DIR}
    try_files {path} /index.html
    file_server
  }
}
EOF
fi

sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo systemctl reload caddy
