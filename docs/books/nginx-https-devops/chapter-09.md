# Глава 9: Итоговый проект

> **Запомни:** эта глава проходится как отдельный проект с чистого сервера. Не предполагается, что у тебя уже стоит Python, Nginx, pip-библиотеки или готовое приложение из первой книги.

---

## 9.1 Цель

Развернуть минимальное Python-приложение в интернете через Nginx.

В этой главе ты делаешь полный путь:

- чистая Ubuntu Server 22.04/24.04;
- вход на сервер по SSH;
- установка системных пакетов;
- отдельный Linux-пользователь для приложения;
- Python virtualenv;
- `requirements.txt` со списком Python-библиотек;
- установка зависимостей через `pip`;
- запуск приложения через `systemd`;
- Nginx как reverse proxy;
- HTTPS через Let's Encrypt или self-signed сертификат;
- ufw, открыты только 22/80/443;
- кастомная 502-страница;
- простой мониторинг-скрипт.

Caddy остаётся альтернативой в конце главы, но основной учебный проект — Nginx. Так ты вручную проходишь все слои: HTTP, reverse proxy, TLS, фаервол и диагностику.

---

### Финальная архитектура

Развернуть Python-приложение в интернете с:
- ✅ Nginx как reverse proxy
- ✅ HTTPS через Let's Encrypt
- ✅ Редирект HTTP → HTTPS
- ✅ ufw (открыты только 22, 80, 443)
- ✅ systemd сервис для приложения
- ✅ Автозапуск после перезагрузки
- ✅ Кастомная страница 502
- ✅ Мониторинг-скрипт

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

## 9.2 Подготовка с чистой Ubuntu

Мы начинаем с нуля.

### Что уже должно быть

| Что | Нужно |
|-----|-------|
| Сервер | Ubuntu Server 22.04 или 24.04 |
| Пользователь | обычный пользователь с `sudo` |
| Доступ | SSH с твоего компьютера на сервер |
| Домен | реальный домен или локальное имя `myapp.local` |
| IP | публичный IP для Let's Encrypt или локальный IP для тренировки |

Если SSH ещё не настроен, сначала сделай это.

На сервере:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
systemctl status ssh
```

На своём компьютере:

```bash
ssh your_user@SERVER_IP
```

Если используешь SSH-ключи:

```bash
ssh-keygen -t ed25519
ssh-copy-id your_user@SERVER_IP
ssh your_user@SERVER_IP
```

> **Важно:** когда будешь включать `ufw`, держи второе SSH-окно открытым. Если ошибёшься с правилами фаервола, первое окно может оборваться.

### Установить системные пакеты

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  nginx \
  ufw \
  curl \
  dnsutils \
  openssl \
  ca-certificates \
  netcat-openbsd
```

Проверь:

```bash
python3 --version
python3 -m pip --version
nginx -v
curl --version
dig -v
```

Запусти Nginx:

```bash
sudo systemctl enable --now nginx
systemctl status nginx
curl -I http://localhost
```

Если видишь `HTTP/1.1 200 OK` или `HTTP/1.1 200`, Nginx отвечает.

### Для практики без реального домена

Если ты работаешь в виртуалке или локальной сети, используй `myapp.local`.

На компьютере, с которого открываешь сайт в браузере, добавь в `/etc/hosts`:

```text
SERVER_IP myapp.local
```

Пример:

```text
192.168.1.50 myapp.local
```

Если проверяешь прямо с самого сервера, можно добавить:

```bash
echo "127.0.0.1 myapp.local" | sudo tee -a /etc/hosts
```

> **Важно:** `127.0.0.1 myapp.local` на сервере работает только для самого сервера. Если браузер открыт на твоём ноутбуке, в `/etc/hosts` ноутбука должен быть IP сервера, а не `127.0.0.1`.

---

## 9.3 Шаг 1: Python-проект с зависимостями

### Создай пользователя и директории

Приложение не должно работать от `root`. Создадим отдельного системного пользователя `myapp`.

```bash
sudo useradd --system --user-group --home-dir /var/www/myapp --shell /usr/sbin/nologin myapp
```

Если пользователь уже есть, команда напишет `user already exists`. Это не страшно.

Создай директории:

```bash
sudo mkdir -p /var/www/myapp
sudo mkdir -p /var/log/myapp
sudo chown -R myapp:myapp /var/www/myapp /var/log/myapp
```

Проверь:

```bash
ls -ld /var/www/myapp /var/log/myapp
```

Владельцем должен быть `myapp`.

### Создай `requirements.txt`

`requirements.txt` — это список Python-библиотек проекта. Без него непонятно, какие пакеты нужно поставить на новом сервере.

В этом проекте приложение будет на Flask, а запускать его в production-стиле будет Gunicorn.

Открой файл в редакторе. Если файла ещё нет, `nano` создаст его при сохранении:

```bash
sudo -u myapp nano /var/www/myapp/requirements.txt
```

Вставь в файл ровно эти строки:

```text
Flask>=3.0,<4
gunicorn>=22,<24
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

Проверь:

```bash
cat /var/www/myapp/requirements.txt
```

Почему так:

- `Flask` — библиотека для HTTP-приложения;
- `gunicorn` — WSGI-сервер, через него приложение будет слушать `127.0.0.1:8000`;
- версии ограничены, чтобы случайно не поставить несовместимую будущую major-версию.

### Создай virtualenv и установи библиотеки

```bash
sudo -u myapp python3 -m venv /var/www/myapp/.venv
sudo -u myapp /var/www/myapp/.venv/bin/python -m pip install --no-cache-dir --upgrade pip
sudo -u myapp /var/www/myapp/.venv/bin/pip install --no-cache-dir -r /var/www/myapp/requirements.txt
```

Проверь:

```bash
sudo -u myapp /var/www/myapp/.venv/bin/pip list
```

В списке должны быть `Flask` и `gunicorn`.

> **Запомни:** системный `pip` и `pip` внутри `.venv` — разные вещи. Для этого проекта всегда используй `/var/www/myapp/.venv/bin/pip`.

### Создай приложение

```bash
sudo tee /var/www/myapp/app.py > /dev/null <<'EOF'
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/")
def index():
    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    forwarded_proto = request.headers.get("X-Forwarded-Proto", request.scheme)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""
    <!doctype html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>My DevOps App</title>
    </head>
    <body>
        <h1>My DevOps App работает</h1>
        <p>Время сервера: {now}</p>
        <p>IP клиента по мнению приложения: {client_ip}</p>
        <p>Протокол по мнению приложения: {forwarded_proto}</p>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return jsonify(status="ok", service="myapp")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
EOF
```

Верни правильного владельца:

```bash
sudo chown myapp:myapp /var/www/myapp/app.py /var/www/myapp/requirements.txt
```

Проверь синтаксис:

```bash
sudo -u myapp /var/www/myapp/.venv/bin/python -m py_compile /var/www/myapp/app.py
```

Запусти вручную для теста:

```bash
cd /var/www/myapp
sudo -u myapp /var/www/myapp/.venv/bin/gunicorn --bind 127.0.0.1:8000 app:app
```

Открой второе SSH-окно и проверь:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

Ожидаешь HTML и JSON:

```json
{"service":"myapp","status":"ok"}
```

Останови ручной запуск в первом окне через `Ctrl+C`.

---

## 9.4 Шаг 2: systemd сервис

### Создай сервис

```bash
sudo tee /etc/systemd/system/myapp.service > /dev/null <<'EOF'
[Unit]
Description=My DevOps Python Application
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/var/www/myapp
Environment=PYTHONUNBUFFERED=1
ExecStart=/var/www/myapp/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=5
StandardOutput=append:/var/log/myapp/app.log
StandardError=append:/var/log/myapp/app-error.log
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target
EOF
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

Должен вернуть HTML и JSON. Также проверь, что приложение слушает только localhost:

```bash
ss -tlnp | grep 8000
```

Правильно:

```text
127.0.0.1:8000
```

Неправильно:

```text
0.0.0.0:8000
```

Если приложение слушает `0.0.0.0:8000`, его можно открыть напрямую, минуя Nginx. В этом проекте так быть не должно.

---

## 9.5 Шаг 3: Nginx как reverse proxy

### Создай конфиг

```bash
sudo tee /etc/nginx/sites-available/myapp.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name myapp.local;

    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;

    client_max_body_size 10M;

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
EOF
```

Если используешь реальный домен, замени `myapp.local`:

```bash
sudo sed -i 's/myapp.local/myapp.example.com/g' /etc/nginx/sites-available/myapp.conf
```

### Включи сайт

```bash
sudo ln -sf /etc/nginx/sites-available/myapp.conf /etc/nginx/sites-enabled/myapp.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Проверь

```bash
curl http://myapp.local/
curl http://myapp.local/health
```

Должен вернуть HTML и JSON от Python-приложения.

---

## 9.6 Шаг 4: HTTPS

### Вариант A: Реальный домен + certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d myapp.example.com
```

Certbot сам:
- Получит сертификат
- Изменит конфиг Nginx
- Настроит редирект HTTP → HTTPS
- Включит автопродление

Проверь:

```bash
curl -I https://myapp.example.com
systemctl status certbot.timer
sudo certbot renew --dry-run
```

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
sudo tee /etc/nginx/sites-available/myapp.conf > /dev/null <<'EOF'
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

    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;

    client_max_body_size 10M;

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
EOF
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Проверь HTTPS

```bash
curl -kI https://myapp.local
curl -k https://myapp.local/health
```

`-k` = не проверять self-signed сертификат.

---

## 9.7 Шаг 5: ufw

Порядок важен: сначала разрешить SSH, потом включать фаервол.

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

Проверь, что порт приложения не открыт наружу:

```bash
ss -tlnp | grep 8000
```

Правильно видеть `127.0.0.1:8000`, а не `0.0.0.0:8000`.

---

## 9.8 Шаг 6: Кастомная страница 502

Когда Python упадёт — пользователи увидят уродливую 502.
Сделай красивую страницу.

### Создай HTML

```bash
sudo mkdir -p /var/www/errors
sudo tee /var/www/errors/502.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head><title>Сервис временно недоступен</title></head>
<body style="font-family: Arial; text-align: center; padding: 50px;">
    <h1>502 Bad Gateway</h1>
    <p>Сервис временно недоступен.</p>
    <p>Мы уже работаем над исправлением.</p>
    <p><small>Попробуйте обновить страницу через минуту.</small></p>
</body>
</html>
EOF
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
curl -k https://myapp.local/
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
sudo tee /usr/local/bin/check-myapp.sh > /dev/null <<'EOF'
#!/bin/bash
set -u

# Настройки
APP_URL="http://127.0.0.1:8000/health"
NGINX_URL="https://myapp.local/health"
LOG_FILE="/var/log/myapp/monitor.log"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Проверка Python
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" 2>/dev/null || true)
if [ "$HTTP_CODE" != "200" ]; then
    log "[FAIL] Python не отвечает (код: $HTTP_CODE)"
    log "[INFO] Перезапуск myapp"
    systemctl restart myapp
    sleep 2
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" 2>/dev/null || true)
    if [ "$HTTP_CODE" != "200" ]; then
        log "[FAIL] Перезапуск не помог, код: $HTTP_CODE"
    else
        log "[OK] Перезапуск помог"
    fi
else
    log "[OK] Python"
fi

# Проверка Nginx
HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "$NGINX_URL" 2>/dev/null || true)
if [ "$HTTP_CODE" != "200" ]; then
    log "[FAIL] Nginx не отвечает (код: $HTTP_CODE)"
else
    log "[OK] Nginx"
fi

# Проверка SSL сертификата (если certbot)
if command -v certbot &>/dev/null; then
    EXPIRY=$(certbot certificates 2>/dev/null | grep "Expiry" | head -1 | awk -F': ' '{print $2}')
    if [ -n "$EXPIRY" ]; then
        log "[INFO] Сертификат истекает: $EXPIRY"
    fi
fi

log "---"
EOF
```

### Сделай выполняемым

```bash
sudo chmod +x /usr/local/bin/check-myapp.sh
```

### Запусти вручную

```bash
sudo /usr/local/bin/check-myapp.sh
sudo tail -n 20 /var/log/myapp/monitor.log
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

## 9.10 Альтернатива: Caddy вместо Nginx

Основной проект выше специально сделан через Nginx: так ты вручную проходишь reverse proxy, TLS, редирект и диагностику.

Caddy можно поставить вместо Nginx, но Python-часть не меняется. Приложение, `requirements.txt`, `.venv` и `systemd` остаются из разделов 9.3-9.4.

### Важное правило

Не запускай приложение ручной командой в фоне. Это временный тестовый запуск, а не серверный режим. В итоговом проекте приложение должно работать так:

```bash
systemctl status myapp
```

### Минимальный Caddyfile

Для локальной тренировки без HTTPS:

```caddy
:80 {
    reverse_proxy 127.0.0.1:8000
}
```

Для реального домена:

```caddy
myapp.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy автоматически получит SSL-сертификат и настроит редирект, если:

- домен указывает на IP сервера;
- порты 80 и 443 открыты;
- Caddy реально слушает 80/443;
- Nginx остановлен или не занимает те же порты.

### Проверки

```bash
curl http://127.0.0.1:8000/health
curl http://myapp.local/health
systemctl status myapp
sudo ufw status verbose
```

Если Caddy запущен через Docker из главы 8, фаервол всё равно должен разрешать только SSH, HTTP и HTTPS:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
```

---

## 9.11 Финальный чеклист

Пройди по всем пунктам:

```
□ SSH на сервер работает
□ python3, python3-venv, python3-pip установлены
□ nginx установлен и отвечает на localhost
□ /var/www/myapp/requirements.txt существует
□ /var/www/myapp/.venv существует
□ pip install -r requirements.txt выполнен
□ pip list показывает Flask и gunicorn
□ systemctl status myapp           → active (running)
□ ss -tlnp | grep 8000             → 127.0.0.1:8000
□ curl http://127.0.0.1:8000/health → {"service":"myapp","status":"ok"}
□ systemctl status nginx           → active (running)
□ nginx -t                         → syntax is ok
□ curl http://myapp.local/health   → ответ от Python через Nginx
□ curl -k https://myapp.local/health → 200 OK
□ curl -v http://myapp.local/      → 301 -> https://
□ ufw status                       → только 22, 80, 443
□ systemctl status certbot.timer   → active (если certbot)
□ sudo reboot                      → после перезагрузки всё работает
□ journalctl -u myapp -n 20        → нет ошибок
□ tail /var/log/nginx/myapp-error.log → нет ошибок
□ /usr/local/bin/check-myapp.sh    → пишет лог в /var/log/myapp/monitor.log
```

### Если что-то не работает

Иди по алгоритму из Главы 7, но в этом порядке:

1. SSH жив?
2. DNS или `/etc/hosts` указывает на правильный IP?
3. `ufw` разрешает 80/443?
4. Nginx запущен?
5. `nginx -t` проходит?
6. `myapp` запущен?
7. Python слушает `127.0.0.1:8000`?
8. `curl http://127.0.0.1:8000/health` работает?
9. `curl http://myapp.local/health` работает?
10. `curl -k https://myapp.local/health` работает?
11. Что в `journalctl -u myapp`?
12. Что в `/var/log/nginx/myapp-error.log`?

Команды:

```bash
systemctl status nginx
systemctl status myapp
sudo nginx -t
ss -tlnp
sudo ufw status verbose
curl -v http://127.0.0.1:8000/health
curl -v http://myapp.local/health
curl -vk https://myapp.local/health
journalctl -u myapp -n 50 --no-pager
tail -n 50 /var/log/nginx/myapp-error.log
```

---

## 9.12 Что дальше

Ты прошёл Модуль 2. Вот что ты теперь умеешь:

- начинать сетевой проект с чистой Ubuntu;
- безопасно заходить по SSH;
- ставить нужные системные пакеты;
- оформлять Python-зависимости через `requirements.txt`;
- ставить зависимости в virtualenv через `pip`;
- запускать Python-приложение как `systemd`-сервис;
- прятать приложение за Nginx;
- добавлять HTTPS;
- закрывать лишние порты через ufw;
- диагностировать проблемы по слоям: DNS -> порт -> Nginx -> Python -> логи.

### Следующий модуль: Docker

В Модуле 3 ты узнаешь:
- Что такое контейнеры и чем отличаются от VM
- Как написать Dockerfile для Python-приложения
- Как использовать docker-compose
- Как Nginx и Caddy работают в Docker-сети

Там ты упакуешь похожее приложение в контейнер и перестанешь вручную ставить Python-библиотеки на хост.

---

> **Итог:** это уже не набор отдельных упражнений. Это полный путь от чистого сервера до работающего HTTPS-сервиса.
