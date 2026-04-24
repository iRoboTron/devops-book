# Глава 2: Nginx — продвинутая настройка

> **Запомни:** В Модуле 2 ты научился запускать Nginx. Теперь настраиваешь его правильно — с заголовками безопасности, rate limiting и правильными логами.

---

## 2.1 Заголовки безопасности

Nginx может добавить HTTP-заголовки которые защищают браузер пользователя.

### X-Content-Type-Options

```nginx
add_header X-Content-Type-Options nosniff always;
```

**Что делает:** Запрещает браузеру "угадывать" тип файла.

**Без этого:**
```
Файл: upload.jpg (на самом деле вредоносный JavaScript)
Браузер: "Хм, это похоже на JS... выполню как JS"
```

**С этим:**
```
Браузер: "Сервер сказал что это image/jpeg. Выполню как картинку."
```

---

### X-Frame-Options

```nginx
add_header X-Frame-Options DENY always;
```

**Что делает:** Запрещает встраивать сайт в `<iframe>`.

**Без этого:**
```
Хакерский сайт:
<iframe src="https://myapp.ru/login" style="opacity:0">
</iframe>
<!-- Пользователь думает что кликает на хакерском сайте,
     а на самом деле вводит пароль в myapp.ru -->
```

Это называется **clickjacking**.

---

### Referrer-Policy

```nginx
add_header Referrer-Policy strict-origin-when-cross-origin always;
```

**Что делает:** Контролирует сколько информации передаётся при переходе на другой сайт.

| Значение | Что передаётся |
|----------|---------------|
| `no-referrer` | Ничего |
| `strict-origin-when-cross-origin` | Только домен при переходе на другой сайт |
| `unsafe-url` | Полный URL всегда (не используй) |

---

### Strict-Transport-Security (HSTS)

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

**Что делает:** Говорит браузеру: "Всегда используй HTTPS для этого сайта."

**Без этого:**
```
Пользователь вводит: myapp.ru
Браузер: → http://myapp.ru (HTTP)
Хакер в кафе: перехватывает HTTP
```

**С HSTS (после первого визита):**
```
Пользователь вводит: myapp.ru
Браузер: → https://myapp.ru (HTTPS, помнит HSTS)
```

`max-age=31536000` = 1 год. Браузер запомнит.

> **Запомни:** HSTS — улица с односторонним движением.
> Раз включил — год будет HTTPS. Нельзя откатить.
> Но ты уже на HTTPS, так что это правильно.

---

### Полный блок заголовков

```nginx
server {
    listen 443 ssl;
    server_name myapp.ru;

    # Заголовки безопасности
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # ... остальной конфиг
}
```

### Проверить через curl

```bash
curl -I https://myapp.ru
HTTP/2 200
x-content-type-options: nosniff
x-frame-options: DENY
strict-transport-security: max-age=31536000; includeSubDomains
```

---

## 2.2 Rate Limiting — защита от брутфорса и DDoS

**Rate limiting** — ограничение количества запросов от одного IP.

### Как работает

```nginx
# В http {} блоке (nginx.conf)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

| Часть | Значение |
|-------|----------|
| `$binary_remote_addr` | IP клиента (бинарный формат, экономит память) |
| `zone=api:10m` | Зона "api", 10МБ памяти (~160 000 IP) |
| `rate=10r/s` | 10 запросов в секунду |

### Применить

```nginx
server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://app:8000;
    }
}
```

| Параметр | Значение |
|----------|----------|
| `burst=20` | Разрешить 20 запросов сверх лимита (очередь) |
| `nodelay` | Не ждать, обрабатывать сразу (но считать) |

### Что происходит

```
IP 1.2.3.4:
  Запрос 1-10: ✅ OK (в лимите)
  Запрос 11-30: ✅ OK (burst, nodelay)
  Запрос 31+:  ❌ 503 Service Unavailable
```

> **Совет:** Rate limiting — не панацея от DDoS.
> Но защищает от брутфорса паролей и простых атак.

### Для логина — строже

```nginx
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

server {
    location /login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://app:8000;
    }
}
```

5 запросов в минуту. Брутфорс невозможен.

---

## 2.3 Таймауты

```nginx
proxy_connect_timeout 10s;   # Сколько ждать подключения к backend
proxy_read_timeout 60s;      # Сколько ждать ответ от backend
proxy_send_timeout 60s;      # Сколько ждать отправки запроса
send_timeout 60s;            # Сколько ждать ответа от клиента
```

### Почему важны

| Таймаут | Слишком маленький | Слишком большой |
|---------|------------------|-----------------|
| `connect` | 502 даже когда app работает | Долго ждёшь мёртвый сервис |
| `read` | 504 на долгих запросах | Контейнеры "висят" и едят память |

### Для разных эндпоинтов — разные таймауты

```nginx
# Обычные запросы — быстро
location / {
    proxy_read_timeout 30s;
    proxy_pass http://app:8000;
}

# Загрузка файлов — дольше
location /upload {
    proxy_read_timeout 300s;    # 5 минут
    client_max_body_size 50M;
    proxy_pass http://app:8000;
}

# Экспорт данных — ещё дольше
location /export {
    proxy_read_timeout 600s;    # 10 минут
    proxy_pass http://app:8000;
}
```

---

## 2.4 Gzip компрессия

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types
    text/plain
    text/css
    text/xml
    application/json
    application/javascript
    application/xml
    image/svg+xml;
```

**Что делает:** Сжимает ответы перед отправкой.

| Тип контента | Без gzip | С gzip | Экономия |
|-------------|----------|--------|----------|
| JSON API | 100 КБ | 15 КБ | 85% |
| HTML | 50 КБ | 12 КБ | 76% |
| CSS | 30 КБ | 6 КБ | 80% |

> **Совет:** Не сжимай уже сжатые файлы (JPEG, PNG, MP4).
> gzip_types не включает их — правильно.

---

## 2.5 Кастомные страницы ошибок

```nginx
server {
    error_page 404 /errors/404.html;
    error_page 500 502 503 504 /errors/50x.html;

    location /errors/ {
        alias /var/www/errors/;
        internal;
    }
}
```

`internal` = пользователь не может запросить `/errors/50x.html` напрямую.

### 502 страница

```html
<!DOCTYPE html>
<html>
<head><title>Сервис недоступен</title></head>
<body style="font-family: system-ui; text-align: center; padding: 60px;">
    <h1>⚠️ Сервис временно недоступен</h1>
    <p>Мы работаем над исправлением.</p>
    <p><small>Попробуйте обновить страницу через минуту.</small></p>
</body>
</html>
```

---

## 2.6 Разделение конфигов

Вместо одного длинного конфига — include:

```nginx
server {
    listen 443 ssl;
    server_name myapp.ru;

    # SSL настройки
    include snippets/ssl.conf;

    # Заголовки безопасности
    include snippets/security-headers.conf;

    # Gzip
    include snippets/gzip.conf;

    # ... основной конфиг
}
```

### snippets/ssl.conf

```nginx
ssl_certificate /etc/letsencrypt/live/myapp.ru/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/myapp.ru/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

### snippets/security-headers.conf

```nginx
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy strict-origin-when-cross-origin always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

> **Совет:** Сниппеты переиспользуются между сайтами.
> Один файл поменял — все сайты обновились.

---

## 2.7 JSON-логи для парсинга

Стандартные логи Nginx сложно парсить. JSON — легко.

```nginx
log_format json escape=json
    '{"time":"$time_iso8601",'
    '"remote_addr":"$remote_addr",'
    '"request":"$request",'
    '"status":$status,'
    '"body_bytes_sent":$body_bytes_sent,'
    '"http_referer":"$http_referer",'
    '"http_user_agent":"$http_user_agent",'
    '"request_time":$request_time}';

access_log /var/log/nginx/myapp-access-json.log json;
```

Результат:

```json
{"time":"2026-04-11T14:30:00+00:00","remote_addr":"203.0.113.50","request":"GET /api/users HTTP/1.1","status":200,"body_bytes_sent":1234,"http_referer":"-","http_user_agent":"Mozilla/5.0","request_time":0.045}
```

> **Запомни:** JSON-логи нужны для Модуля 6 (мониторинг).
> Настрой сейчас — потом подключишь алертинг.

---

## 2.8 Привычка: `nginx -t && reload`

Добавь в `~/.bashrc`:

```bash
alias nx='sudo nginx -t && sudo systemctl reload nginx'
```

Теперь:

```bash
nx
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

> **Запомни:** Никогда не reload без `nginx -t`.
> Сломанный конфиг = все сайты упали.

---

## 📝 Упражнения

### Упражнение 2.1: Заголовки безопасности
**Задача:**
1. Добавь security headers в конфиг Nginx
2. Перезагрузи: `nginx -t && systemctl reload nginx`
3. Проверь: `curl -I https://myapp.ru`
4. Все заголовки на месте?

### Упражнение 2.2: Rate Limiting
**Задача:**
1. Добавь `limit_req_zone` в `http {}` блок
2. Добавь `limit_req` в `location /login`
3. Протестируй:
   ```bash
   for i in {1..15}; do curl -s -o /dev/null -w "%{http_code} " http://myapp.ru/login; done
   ```
4. Первые запросы 200, потом 503?

### Упражнение 2.3: Gzip
**Задача:**
1. Включи gzip для JSON и CSS
2. Проверь: `curl -H "Accept-Encoding: gzip" -I https://myapp.ru/api/users`
3. Есть ли заголовок `Content-Encoding: gzip`?

### Упражнение 2.4: JSON-логи
**Задача:**
1. Добавь `log_format json` в nginx.conf
2. Настрой access_log для сайта
3. Сделай несколько запросов
4. Проверь: `tail /var/log/nginx/myapp-access-json.log`
5. Формат JSON?

### Упражнение 2.5: DevOps Think
**Задача:** «Rate limiting блокирует легитимных пользователей. Как исправить?»

Подсказки:
1. burst слишком маленький? Увеличь
2. Rate слишком строгий? `5r/m` для логина — нормально, для API — нет
3. Один IP за несколькими пользователями (NAT, офис)? Увеличь лимит
4. Может whitelist для доверенных IP? `limit_req zone=api burst=100 nodelay;` внутри `location`

---

## 📋 Чеклист главы 2

- [ ] Добавлены заголовки безопасности (nosniff, DENY, HSTS)
- [ ] Проверил заголовки через `curl -I`
- [ ] Настроен rate limiting для API и/или логина
- [ ] Настроены правильные таймауты
- [ ] Включен gzip для текстовых форматов
- [ ] Настроены кастомные страницы ошибок
- [ ] Конфиги разделены через `include` (сниппеты)
- [ ] JSON-логи настроены
- [ ] Алиас `nx` для `nginx -t && reload`

**Всё отметил?** Переходи к Главе 3 — правильная настройка PostgreSQL.
