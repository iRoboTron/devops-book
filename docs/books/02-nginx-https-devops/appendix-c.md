# Приложение C: Частые ошибки

> Когда что-то не работает — скорее всего это уже было. Вот решения.

---

## C.1 Порт 80 закрыт → certbot не работает

### Симптом

```
Problem: The connection to myapp.ru:80 timed out
```

### Причина

Фаервол (ufw) блокирует порт 80. Certbot не может пройти ACME challenge.

### Решение

```bash
# Открой порт 80
sudo ufw allow 80

# Попробуй снова
sudo certbot --nginx -d myapp.ru
```

### Профилактика

Всегда открывай порт 80 **перед** запуском certbot.

---

## C.2 Забыл `nginx -t` → сломан конфиг

### Симптом

```bash
sudo systemctl reload nginx
Job for nginx.service failed because the control process exited with error code.
```

Все сайты на сервере упали.

### Причина

Ты перезагрузил Nginx со сломанным конфигом.

### Решение

```bash
# Найди ошибку
sudo nginx -t

# Исправь
sudo nano /etc/nginx/sites-available/myapp.conf

# Проверь снова
sudo nginx -t

# Перезагрузи
sudo systemctl reload nginx
```

### Профилактика

> **Запомни:** ВСЕГДА `nginx -t` ПЕРЕД `reload`.
> Без исключений. Выработай привычку.

---

## C.3 `ufw enable` без правила для 22 → потерял SSH

### Симптом

SSH-подключение разорвалось. Не можешь зайти на сервер.

### Причина

`ufw enable` без `ufw allow 22` заблокировал все входящие, включая SSH.

### Решение

1. Открой консоль сервера (VirtualBox / VNC провайдера)
2. Выключи ufw:
   ```bash
   sudo ufw disable
   ```
3. Добавь правило:
   ```bash
   sudo ufw allow 22
   ```
4. Включи снова:
   ```bash
   sudo ufw enable
   ```

### Профилактика

> **Порядок важен:**
> 1. `ufw allow 22` ← ВСЕГДА первым
> 2. `ufw allow 80`
> 3. `ufw allow 443`
> 4. `ufw enable` ← ТОЛЬКО после правил

---

## C.4 Неправильный `proxy_pass` → 502

### Симптом

```
curl http://myapp.ru
HTTP/1.1 502 Bad Gateway
```

### Причина

Nginx не может подключиться к Python. Wrong port или Python не запущен.

### Решение

```bash
# 1. Проверь что Python слушает порт
ss -tlnp | grep 8000

# 2. Проверь proxy_pass в конфиге
grep proxy_pass /etc/nginx/sites-enabled/myapp.conf

# 3. Попробуй напрямую
curl http://127.0.0.1:8000

# 4. Если Python не запущен
systemctl status myapp
sudo systemctl start myapp
```

### Частые ошибки

| proxy_pass | Проблема |
|------------|----------|
| `http://localhost:8000` | Работает, но лучше `127.0.0.1` |
| `http://127.0.0.1:8080` | Неправильный порт |
| `http://myapp.ru:8000` | Идёт наружу, не на localhost |
| `127.0.0.1:8000` | Забыл `http://` |

---

## C.5 DNS-изменения применились не сразу

### Симптом

Ты поменял A-запись. `dig` показывает новый IP. Но браузер идёт на старый.

### Причина

DNS кешируется на всех уровнях:
- Браузер
- Операционная система
- ISP резолвер
- Промежуточные DNS-серверы

### Решение

**Подожди.** TTL определяет сколько ждать.

```bash
# Проверить TTL
dig myapp.ru | grep "ANSWER SECTION" -A1

# Обычно TTL = 300-3600 секунд (5 минут - 1 час)
```

### Ускорить

**На будущее:** перед миграцией уменьши TTL:

```
За день до миграции:
  TTL 3600 → TTL 300

Миграция:
  Поменяй IP → все увидят через 5 минут

Через день:
  TTL 300 → TTL 3600
```

---

## C.6 ERR_SSL_PROTOCOL_ERROR

### Симптом (браузер)

```
ERR_SSL_PROTOCOL_ERROR
```

### Причина

Браузер пытается установить HTTPS соединение, но сервер не понимает TLS.

Возможные причины:
- Nginx слушает HTTP на порту 443
- SSL-сертификат не настроен
- `ssl_certificate` указывает на неправильный файл

### Решение

```bash
# 1. Проверь что Nginx настроен для SSL
grep -E "listen|ssl_certificate" /etc/nginx/sites-enabled/myapp.conf

# Должно быть:
# listen 443 ssl;
# ssl_certificate /path/to/fullchain.pem;
# ssl_certificate_key /path/to/privkey.pem;

# 2. Проверь что файлы сертификата существуют
ls -la /etc/letsencrypt/live/myapp.ru/fullchain.pem
ls -la /etc/letsencrypt/live/myapp.ru/privkey.pem

# 3. Проверь конфиг
sudo nginx -t
sudo systemctl reload nginx
```

---

## C.7 504 Gateway Timeout

### Симптом

```
HTTP/1.1 504 Gateway Timeout
```

### Причина

Nginx ждал ответ от Python, но не дождался.

### Решение

```bash
# 1. Проверь что Python запущен
systemctl status myapp

# 2. Проверь логи приложения
journalctl -u myapp -n 50

# 3. Проверь нагрузку CPU/RAM
htop

# 4. Увеличь таймаут (временно)
# В /etc/nginx/sites-enabled/myapp.conf:
proxy_read_timeout 120s;

sudo nginx -t
sudo systemctl reload nginx
```

---

## C.8 Приложение доступно с внешнего IP (опасно!)

### Симптом

```bash
ss -tlnp | grep 8000
LISTEN  0  511  0.0.0.0:8000  0.0.0.0:*  users:(("gunicorn",pid=890))
```

Python доступен напрямую из интернета, минуя Nginx.

### Причина

Приложение слушает `0.0.0.0` вместо `127.0.0.1`.

### Решение

В конфиге приложения:

```python
# Было (опасно):
server = HTTPServer(('0.0.0.0', 8000), Handler)

# Стало (правильно):
server = HTTPServer(('127.0.0.1', 8000), Handler)
```

Или закрой порт в ufw:
```bash
sudo ufw deny 8000
```

---

## C.9 Certbot: "Challenge failed for domain"

### Симптом

```
Challenge failed for domain myapp.ru
http-01 challenge for myapp.ru
```

### Возможные причины

| Причина | Решение |
|---------|---------|
| Nginx не запущен | `sudo systemctl start nginx` |
| server_name неправильный | Проверь `grep server_name /etc/nginx/sites-enabled/` |
| DNS не настроен | `dig myapp.ru +short` — должен вернуть IP сервера |
| Порт 80 закрыт | `sudo ufw allow 80` |
| Nginx не отдаёт challenge | `curl http://myapp.ru/.well-known/acme-challenge/test` — должен вернуть что-то |

### Диагностика

```bash
# Проверь DNS
dig myapp.ru +short

# Проверь Nginx
systemctl status nginx

# Проверь доступность challenge
curl http://myapp.ru/.well-known/acme-challenge/test-file

# Попробуй в dry-run режиме
sudo certbot renew --dry-run
```

---

## C.10 Caddy: сертификат не получается

### Симптом

```bash
docker compose logs caddy | grep -i error
# ...obtaining certificate: ...
# ...solving challenge: ...
```

### Причины и решения

| Причина | Симптом в логах | Решение |
|---------|----------------|---------|
| DNS не настроен | `no such host` | `dig myapp.ru +short` → должен вернуть IP сервера |
| Порт 80 закрыт | `connection refused` | `sudo ufw allow 80` |
| Превышен лимит Let's Encrypt | `too many certificates already issued` | Подожди 7 дней или используй staging |

### Проверка

```bash
# Порт 80 открыт?
sudo ufw status | grep 80

# DNS указывает на этот сервер?
dig myapp.ru +short
curl ifconfig.me   # внешний IP сервера — должны совпадать
```

---

## C.11 Caddy: сломан Caddyfile после reload

### Симптом

```bash
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
# Error: ...
```

### Причина

Синтаксическая ошибка в Caddyfile. Caddy не применил изменения и остался на старом конфиге.

### Решение

```bash
# Найти ошибку
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile

# Исправить
nano ./Caddyfile

# Проверить снова
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile

# Применить
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

> **Запомни:** ВСЕГДА `caddy validate` ПЕРЕД `caddy reload`. Как `nginx -t` перед `reload nginx`.

---

## C.12 Caddy: сертификат не обновился после docker compose down -v

### Симптом

После `docker compose down -v` Caddy запрашивает новый сертификат и получает ошибку:

```
too many certificates already issued for this domain
```

### Причина

`-v` удалил том `./data`, где хранились сертификаты. Caddy пытается получить новый, но превышен лимит Let's Encrypt (5 сертификатов на домен в неделю).

### Решение

Подожди до сброса лимита. В будущем:

```bash
# Остановить без удаления томов
docker compose down

# Удалять тома только осознанно
docker compose down -v   # ТОЛЬКО если точно нужно
```

### Профилактика

Бэкапить том `./data` перед любыми операциями с Caddy:

```bash
cp -r ./data ./data.backup.$(date +%Y%m%d)
```
