# Глава 9: Итоговый проект

> **Запомни:** Эта глава — не теория. Ты соберёшь всё вместе. Без подсказок, по чеклисту. Как настоящий DevOps.

---

## 9.1 Цель

Развернуть Python-приложение в интернете — **на выбор** через Nginx или Caddy.

**Вариант A (Nginx)** — если хочешь закрепить знания и пройти всё вручную.
**Вариант B (Caddy)** — если хочешь сделать так, как это работает на реальном сервере.

Оба варианта дают одинаковый результат — работающий HTTPS-сервис.

---

### Вариант A (Nginx) — финальная архитектура

Развернуть Python-приложение в интернете с:
- ✅ Nginx как reverse proxy
- ✅ HTTPS через Let's Encrypt
- ✅ Редирект HTTP → HTTPS
- ✅ ufw (открыты только 22, 80, 443)
- ✅ systemd сервис для приложения
- ✅ Автозапуск после перезагрузки
- ✅ Кастомная страница 502
- ✅ Мониторинг-скрипт

### Финальная архитектура

```
Интернет (браузер)
    │  HTTPS (443)
    ▼
┌──────────────────────────────┐
│         ufw                  │
│  Открыты: 22, 80, 443        │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│         Nginx                │
│  :80  → редирект на :443     │
│  :443 → SSL + proxy_pass     │
└──────────────┬───────────────┘
               │  HTTP (8000, localhost)
               ▼
┌──────────────────────────────┐
│   Python-приложение          │
│   systemd сервис             │
│   127.0.0.1:8000             │
└──────────────┬───────────────┘
               ▼
        /var/log/myapp/

[ certbot ] — автопродление SSL
[ monitor.sh ] — проверка что всё живо
```

---

## 9.2 Подготовка

### Требования

| Что | Статус |
|-----|--------|
| Ubuntu Server 22.04/24.04 | ✅ |
| sudo права | ✅ |
| Домен (реальный или через /etc/hosts) | ✅ |
| Публичный IP (для certbot) или self-signed | ✅ |

### Для практики без реального домена

```bash
# Добавь в /etc/hosts
echo "127.0.0.1 myapp.local" | sudo tee -a /etc/hosts
```

### Обновить систему

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 9.3 Шаг 1: Python-приложение

### Создай приложение

```bash
sudo mkdir -p /var/www/myapp
sudo nano /var/www/myapp/app.py
```

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>My App</title></head>
            <body>
                <h1>Hello from DevOps!</h1>
                <p>Сервер работает.</p>
                <p>Время: {time}</p>
            </body>
            </html>
            """.format(time=datetime.datetime.now().strftime("%H:%M:%S"))
            self.wfile.write(html.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8000), MyHandler)
    print("Running on http://127.0.0.1:8000")
    server.serve_forever()
```

### Создай пользователя для приложения

```bash
sudo useradd -r -s /usr/sbin/nologin myapp
sudo chown -R myapp:myapp /var/www/myapp
```

### Создай директорию логов

```bash
sudo mkdir -p /var/log/myapp
sudo chown myapp:myapp /var/log/myapp
```

---

## 9.4 Шаг 2: systemd сервис

### Создай сервис

```bash
sudo nano /etc/systemd/system/myapp.service
```

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

### Запусти

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
systemctl status myapp
```

### Проверь

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

Должен вернуть HTML и JSON.

---

## 9.5 Шаг 3: Nginx как reverse proxy

### Создай конфиг

```bash
sudo nano /etc/nginx/sites-available/myapp.conf
```

```nginx
server {
    listen 80;
    server_name myapp.local;  # Поменяй на свой домен

    # Редирект HTTP → HTTPS (будет работать после certbot)
    # return 301 https://$host$request_uri;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;
}
```

### Включи сайт

```bash
sudo ln -s /etc/nginx/sites-available/myapp.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Проверь

```bash
curl http://myapp.local/
```

Должен вернуть HTML от Python-приложения.

---

## 9.6 Шаг 4: HTTPS

### Вариант A: Реальный домен + certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d myapp.ru
```

Certbot сам:
- Получит сертификат
- Изменит конфиг Nginx
- Настроит редирект HTTP → HTTPS

### Вариант B: Self-signed для тестов

```bash
sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/myapp.key \
  -out /etc/ssl/certs/myapp.crt \
  -subj "/CN=myapp.local"
```

Добавь SSL в конфиг Nginx:

```bash
sudo nano /etc/nginx/sites-available/myapp.conf
```

```nginx
# HTTP — редирект
server {
    listen 80;
    server_name myapp.local;
    return 301 https://$host$request_uri;
}

# HTTPS
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

    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Проверь HTTPS

```bash
curl -kI https://myapp.local
```

`-k` = не проверять self-signed сертификат.

---

## 9.7 Шаг 5: ufw

```bash
# Политика
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Разрешить нужное
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'

# Включить
sudo ufw enable

# Проверить
sudo ufw status verbose
```

---

## 9.8 Шаг 6: Кастомная страница 502

Когда Python упадёт — пользователи увидят уродливую 502.
Сделай красивую страницу.

### Создай HTML

```bash
sudo mkdir -p /var/www/errors
sudo nano /var/www/errors/502.html
```

```html
<!DOCTYPE html>
<html>
<head><title>Сервис временно недоступен</title></head>
<body style="font-family: Arial; text-align: center; padding: 50px;">
    <h1>⚠️ 502 Bad Gateway</h1>
    <p>Сервис временно недоступен.</p>
    <p>Мы уже работаем над исправлением.</p>
    <p><small>Попробуйте обновить страницу через минуту.</small></p>
</body>
</html>
```

### Добавь в конфиг Nginx

```nginx
server {
    # ... остальной конфиг ...

    error_page 502 /errors/502.html;
    location /errors/ {
        alias /var/www/errors/;
        internal;
    }
}
```

### Проверь

```bash
sudo nginx -t
sudo systemctl reload nginx

# Останови приложение
sudo systemctl stop myapp

# Проверь
curl http://myapp.local/
```

Должен вернуть твою красивую 502 страницу.

```bash
# Запусти обратно
sudo systemctl start myapp
```

---

## 9.9 Шаг 7: Мониторинг-скрипт

Скрипт который проверяет что всё живо.

### Создай скрипт

```bash
sudo nano /usr/local/bin/check-myapp.sh
```

```bash
#!/bin/bash

# Настройки
APP_URL="http://127.0.0.1:8000/health"
NGINX_URL="https://myapp.local"
LOG_FILE="/var/log/myapp/monitor.log"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Проверка Python
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
    log "❌ Python не отвечает (код: $HTTP_CODE)"
    log "   Перезапуск..."
    sudo systemctl restart myapp
    sleep 2
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" 2>/dev/null)
    if [ "$HTTP_CODE" != "200" ]; then
        log "   ❌ Перезапуск не помог!"
    else
        log "   ✅ Перезапуск помог"
    fi
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

# Проверка SSL сертификата (если certbot)
if command -v certbot &>/dev/null; then
    EXPIRY=$(sudo certbot certificates 2>/dev/null | grep "Expiry" | head -1 | awk -F': ' '{print $2}')
    if [ -n "$EXPIRY" ]; then
        log "📜 Сертификат истекает: $EXPIRY"
    fi
fi

log "---"
```

### Сделай выполняемым

```bash
sudo chmod +x /usr/local/bin/check-myapp.sh
```

### Запусти вручную

```bash
sudo /usr/local/bin/check-myapp.sh
cat /var/log/myapp/monitor.log
```

### Добавь в cron (каждые 5 минут)

```bash
sudo crontab -e
```

Добавь:
```
*/5 * * * * /usr/local/bin/check-myapp.sh
```

Теперь каждые 5 минут скрипт проверяет сервисы.

---

## 9.10 Вариант B: Caddy

Тот же результат — HTTPS + reverse proxy — но через Caddy.

### Структура

```
~/myapp-caddy/
├── docker-compose.yml
├── Caddyfile
├── app.py           ← Python-приложение из раздела 9.3
├── data/            ← сертификаты (том Docker)
└── config/          ← кеш конфигурации
```

### Создай директорию

```bash
mkdir -p ~/myapp-caddy && cd ~/myapp-caddy
```

### Запусти Python-приложение

Скопируй `app.py` из раздела 9.3, запусти через systemd (раздел 9.4) или прямо в терминале для теста:

```bash
python3 app.py &
```

### Создай Caddyfile

```bash
nano Caddyfile
```

**Для локальной разработки (без домена):**

```caddy
:80 {
    reverse_proxy localhost:8000
}
```

**Для реального домена:**

```caddy
myapp.ru {
    reverse_proxy localhost:8000
}
```

Caddy автоматически получит SSL-сертификат и настроит редирект.

### Создай docker-compose.yml

```yaml
services:
  caddy:
    image: caddy:2.10-alpine
    restart: always
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data:/data
      - ./config:/config
```

### Запусти

```bash
docker compose up -d
docker compose logs -f caddy
```

Для реального домена в логах появится:

```
... successfully obtained certificate
... serving
```

### Настрой ufw

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Проверь

```bash
# С реальным доменом
curl -v https://myapp.ru

# Локально
curl http://localhost
```

### Чеклист Вариант B

```
□ docker compose ps        → caddy Up
□ docker compose logs caddy → нет errors
□ curl http://localhost     → ответ от Python
□ curl https://myapp.ru    → 200 (если реальный домен)
□ ufw status               → только 22, 80, 443
□ После reboot             → всё поднялось само (restart: always)
```

---

## 9.11 Финальный чеклист

Пройди по всем пунктам:

```
□ curl -v https://myapp.local/     → 200 OK
□ curl -v http://myapp.local/      → 301 → https://
□ curl http://127.0.0.1:8000/health → {"status": "ok"}
□ ufw status                       → только 22, 80, 443
□ systemctl status myapp           → active (running)
□ systemctl status nginx           → active (running)
□ systemctl status certbot.timer   → active (если certbot)
□ sudo reboot                      → после перезагрузки всё работает
□ journalctl -u myapp -n 20        → нет ошибок
□ tail /var/log/nginx/error.log    → нет ошибок
□ /usr/local/bin/check-myapp.sh    → всё OK
```

### Если что-то не работает

Иди по алгоритму из Главы 7:

1. `ping` — сервер доступен?
2. `nc -zv` — порты открыты?
3. `ss -tlnp` — сервисы слушают?
4. `systemctl status` — сервисы запущены?
5. `nginx -t` — конфиг валидный?
6. `curl -v` — что отвечает?
7. Логи — что в error.log?

---

## 9.12 Что дальше

Ты прошёл Модуль 2. Вот что ты теперь умеешь:

- ✅ Настраивать Nginx как reverse proxy
- ✅ Получать SSL-сертификаты через Let's Encrypt и certbot
- ✅ Настраивать фаервол через ufw
- ✅ Диагностировать сетевые проблемы
- ✅ Работать с Caddy — автоматический SSL, reload без даунтайма
- ✅ Развернуть полноценный веб-сервис двумя способами

### Следующий модуль: Docker

В Модуле 3 ты узнаешь:
- Что такое контейнеры и чем отличаются от VM
- Как написать Dockerfile для Python-приложения
- Как использовать docker-compose
- Как Nginx и Caddy работают в Docker-сети

Кстати, Caddy в Модуле 3 ты уже запускал в Docker — это не случайно.

---

> **Поздравляю!** Ты построил полноценный веб-сервис с нуля.
> Без магии, без copy-paste — понимая каждый шаг.
> Это то что делает настоящий DevOps.
