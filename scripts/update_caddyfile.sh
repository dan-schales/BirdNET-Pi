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
  # API server (matched first — most specific)
  handle /api/* {
    reverse_proxy localhost:7007
  }

  # Static bird data files
  handle /By_Date/* {
    root * ${EXTRACTED}
    file_server browse
  }
  handle /Charts/* {
    root * ${EXTRACTED}
    file_server browse
  }

  # Authenticated routes
  handle /Processed* {
    basicauth {
      birdnet ${HASHWORD}
    }
    root * ${EXTRACTED}
    file_server browse
  }
  handle /scripts* {
    basicauth {
      birdnet ${HASHWORD}
    }
    root * ${EXTRACTED}
    php_fastcgi unix//run/php/php-fpm.sock
  }
  handle /phpsysinfo* {
    basicauth {
      birdnet ${HASHWORD}
    }
    root * ${EXTRACTED}
    file_server browse
  }
  handle /terminal* {
    basicauth {
      birdnet ${HASHWORD}
    }
    reverse_proxy localhost:8888
  }

  # Proxied services
  handle /stream {
    basicauth {
      birdnet ${HASHWORD}
    }
    reverse_proxy localhost:8000
  }
  handle /log* {
    reverse_proxy localhost:8080
  }
  handle /stats* {
    reverse_proxy localhost:8501
  }

  # Legacy PHP (views.php, etc.)
  handle /views.php* {
    root * ${EXTRACTED}
    php_fastcgi unix//run/php/php-fpm.sock
  }

  # SPA frontend — catch-all (must be last)
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
  handle /api/* {
    reverse_proxy localhost:7007
  }

  # Static bird data files
  handle /By_Date/* {
    root * ${EXTRACTED}
    file_server browse
  }
  handle /Charts/* {
    root * ${EXTRACTED}
    file_server browse
  }

  # Proxied services
  handle /stream {
    reverse_proxy localhost:8000
  }
  handle /log* {
    reverse_proxy localhost:8080
  }
  handle /stats* {
    reverse_proxy localhost:8501
  }
  handle /terminal* {
    reverse_proxy localhost:8888
  }

  # Legacy PHP
  handle /views.php* {
    root * ${EXTRACTED}
    php_fastcgi unix//run/php/php-fpm.sock
  }

  # SPA frontend — catch-all (must be last)
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
