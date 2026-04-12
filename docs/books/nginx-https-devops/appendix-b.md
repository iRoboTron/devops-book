# Приложение B: Готовые конфиги

> Копируй и адаптируй под свой проект. Каждый конфиг проверен и объяснён.

---

## B.1 Минимальный Nginx для статики

```nginx
server {
    listen 80;
    server_name myapp.local;

    root /var/www/myapp;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

**Когда использовать:** Статический сайт, лендинг, документация.

---

## B.2 Nginx reverse proxy для Python (без SSL)

```nginx
server {
    listen 80;
    server_name myapp.local;

    # Логи
    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;

    # Размер загружаемых файлов
    client_max_body_size 10M;

    # Статика — отдаёт Nginx
    location /static/ {
        alias /var/www/myapp/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Всё остальное — Python
    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

**Когда использовать:** Разработка, внутренняя сеть, перед добавлением HTTPS.

---

## B.3 Nginx reverse proxy с SSL (после certbot)

```nginx
# HTTP → HTTPS редирект
server {
    listen 80;
    server_name myapp.ru;

    # Для certbot challenge (не трогай!)
    location ~ /.well-known {
        allow all;
        root /var/www/html;
    }

    # Всё остальное → HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl;
    server_name myapp.ru;

    # SSL-сертификат
    ssl_certificate /etc/letsencrypt/live/myapp.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Логи
    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;

    # Размер загружаемых файлов
    client_max_body_size 10M;

    # Статика
    location /static/ {
        alias /var/www/myapp/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Python-приложение
    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Кастомная страница 502
    error_page 502 /errors/502.html;
    location /errors/ {
        alias /var/www/errors/;
        internal;
    }
}
```

**Когда использовать:** Продакшен с реальным доменом и HTTPS.

---

## B.4 Nginx с self-signed SSL (для тестов)

```nginx
server {
    listen 80;
    server_name myapp.local;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name myapp.local;

    ssl_certificate /etc/ssl/certs/myapp.crt;
    ssl_certificate_key /etc/ssl/private/myapp.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Когда использовать:** Локальная разработка без реального домена.

---

## B.5 ufw для типичного веб-сервера

```bash
#!/bin/bash
# Скрипт настройки фаервола
# Запусти один раз: sudo bash setup-ufw.sh

# Сбросить правила (если были)
sudo ufw --force reset

# Политика по умолчанию
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH
sudo ufw allow OpenSSH

# HTTP и HTTPS
sudo ufw allow 'Nginx Full'

# (Опционально) Доступ к БД только из внутренней сети
# sudo ufw allow from 10.0.0.0/8 to any port 5432

# Логирование
sudo ufw logging on

# Включить
sudo ufw --force enable

# Проверить
sudo ufw status verbose
```

---

## B.6 systemd сервис для Python-приложения

```ini
[Unit]
Description=My Python Application
After=network.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/var/www/myapp
ExecStart=/usr/bin/python3 /var/www/myapp/app.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/myapp/app.log
StandardError=append:/var/log/myapp/app-error.log
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target
```

---

## B.7 Мониторинг-скрипт

```bash
#!/bin/bash
# /usr/local/bin/check-myapp.sh

APP_URL="http://127.0.0.1:8000/health"
NGINX_URL="https://myapp.local"
LOG_FILE="/var/log/myapp/monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Проверка Python
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
    log "❌ Python не отвечает (код: $HTTP_CODE). Перезапуск..."
    sudo systemctl restart myapp
else
    log "✅ Python OK"
fi

# Проверка Nginx
HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "$NGINX_URL" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
    log "❌ Nginx не отвечает (код: $HTTP_CODE)"
else
    log "✅ Nginx OK"
fi

log "---"
```

---

## B.8 Кастомная страница 502



```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Сервис временно недоступен</title>
    <style>
        body {
            font-family: -apple-system, Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #f5f5f5;
            color: #333;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #e74c3c; }
        .retry { color: #7f8c8d; font-size: 14px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚠️ Сервис временно недоступен</h1>
        <p>Мы уже работаем над исправлением.</p>
        <p class="retry">Попробуйте обновить страницу через минуту.</p>
    </div>
</body>
</html>
```

---

## B.9 Минимальный Caddyfile: reverse proxy

```caddy
myapp.ru {
    reverse_proxy localhost:8000
}
```

SSL-сертификат, редирект HTTP→HTTPS и заголовки безопасности — автоматически.

**Для локальной разработки без домена:**

```caddy
:80 {
    reverse_proxy localhost:8000
}
```

---

## B.10 Caddyfile: несколько доменов + статика + редирект

```caddy
{
    servers {
        protocols h1 h2 h3
        trusted_proxies static 192.168.1.1   # IP роутера или вышестоящего прокси
    }
}

# Основное приложение
myapp.ru {
    reverse_proxy localhost:8000
}

# Статический сайт
static.myapp.ru {
    root * /srv/static
    file_server
}

# Редирект старого домена
old.myapp.ru {
    redir https://myapp.ru{uri} permanent
}

# API на другом порту
api.myapp.ru {
    reverse_proxy localhost:8080
}
```

---

## B.11 docker-compose.yml для Caddy

```yaml
services:
  caddy:
    image: caddy:2.10-alpine
    restart: always
    container_name: edge-proxy
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data:/data        # сертификаты — НЕ УДАЛЯТЬ
      - ./config:/config    # кеш конфигурации
      - ./site:/srv         # статические файлы (если нужны)
```

**Управление:**

```bash
# Проверить конфиг
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile

# Применить изменения без даунтайма
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile

# Логи
docker compose logs -f caddy
```
