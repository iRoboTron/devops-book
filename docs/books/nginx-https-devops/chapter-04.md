# Глава 4: Nginx как обратный прокси

> **Запомни:** Статический сайт — это легко. Настоящая мощь — когда Nginx передаёт запросы Python-приложению и возвращает ответ. Это называется reverse proxy.

---

## 4.1 Что такое reverse proxy

**Прокси** — посредник. Ты не общаешься напрямую, а через посредника.

**Reverse proxy** (обратный прокси) — посредник на стороне **сервера**.

```
Браузер ───→ Nginx (reverse proxy) ───→ Python-приложение
              (видит интернет)           (скрыт за Nginx)
```

### Зачем это нужно

```
Без reverse proxy:
Браузер ───→ Python:8000
  ❌ Python должен обрабатывать SSL
  ❌ Python должен кешировать статику
  ❌ Python должен бороться с медленными клиентами
  ❌ Порт 8000 торчит в интернет

С reverse proxy:
Браузер ───→ Nginx:80 ───→ Python:8000
  ✅ Nginx берёт SSL, статику, кеширование
  ✅ Python только бизнес-логика
  ✅ Порт 8000 слушает только localhost (скрыт)
  ✅ Nginx может добавить второй Python-сервер
```

### Схема потока

```
Браузер
  │
  │  GET /users HTTP/1.1
  │  Host: myapp.ru
  │
  ▼
┌─────────────────────────────┐
│  Nginx (порт 80)             │
│                              │
│  location / {                │
│      proxy_pass              │
│      http://127.0.0.1:8000;  │
│  }                           │
└─────────────┬───────────────┘
              │
              │  GET /users HTTP/1.1
              │  (те же заголовки + дополнительные)
              │
              ▼
┌─────────────────────────────┐
│  Python (порт 8000)          │
│  Только localhost!           │
│                              │
│  @app.route("/users")        │
│  def get_users():            │
│      return jsonify([...])   │
└─────────────┬───────────────┘
              │
              │  {"users": [...]}
              │
              ▼
         Nginx → Браузер
```

> **Запомни:** Браузер думает что общается с Nginx.
> Nginx общается с Python. Python не знает про браузер.

---

## 4.2 `proxy_pass` — базовый проброс

Минимальный конфиг для reverse proxy:

```nginx
server {
    listen 80;
    server_name myapp.local;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Что делает `proxy_pass`

```nginx
proxy_pass http://127.0.0.1:8000;
```

**Перевод:** "Всё что пришло на этот `server` — перешли на `127.0.0.1:8000`."

Когда браузер просит `GET /users`:
1. Nginx получает запрос на порт 80
2. Видит `location /` — подходит всем запросам
3. `proxy_pass` — пересылает на `http://127.0.0.1:8000/users`
4. Python обрабатывает `/users`
5. Python возвращает JSON
6. Nginx возвращает JSON браузеру

> **Запомни:** `proxy_pass` не меняет путь.
> Браузер просит `/users` — Python получает `/users`.

---

## 4.3 Директива `location`: как Nginx решает что делать

`location` — это правило "какой URL → что делать".

### Точное совпадение: `=`

```nginx
location = /health {
    return 200 "OK";
}
```

Только `/health` — точно. Не `/health/check`, не `/health/`. Только `/health`.

### Префикс: `/api/`

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
```

Все запросы начинающиеся с `/api/`:
- `/api/users` ✅
- `/api/users/42` ✅
- `/api/v2/data` ✅
- `/about` ❌

### Регулярка: `~`

```nginx
location ~ \.(jpg|png|gif)$ {
    root /var/www/static;
    expires 30d;
}
```

Все запросы заканчивающиеся на `.jpg`, `.png`, `.gif`.

### Порядок проверки

```nginx
server {
    # 1. Сначала точные совпадения (=)
    location = /favicon.ico { ... }

    # 2. Потом префиксы (самый длинный выигрывает)
    location /api/ { ... }
    location / { ... }

    # 3. Потом регулярки (~)
    location ~ \.php$ { ... }
}
```

> **Запомни:** `location /` — это catch-all.
> Если ничего не подошло — сработает он.
> Поэтому он обычно последний в конфиге.

---

## 4.4 Важные заголовки: proxy_set_header

### Проблема

Когда Nginx пересылает запрос Python'у:

```
Nginx → Python:
  GET /users HTTP/1.1
  Host: 127.0.0.1:8000         ← Python видит localhost!
```

Python думает что запрос пришёл с `127.0.0.1`.
Он не знает:
- Какой реальный домен (`myapp.ru`)
- Какой реальный IP клиента
- Использовал ли клиент HTTPS

### Решение: proxy_set_header

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Разбор каждого заголовка

```nginx
proxy_set_header Host $host;
```
**Что:** Оригинальный домен из запроса браузера.
**Python видит:** `myapp.ru` вместо `127.0.0.1:8000`.
**Зачем:** Приложение может генерировать ссылки. Без этого — ссылки будут `http://127.0.0.1:8000/...`.

```nginx
proxy_set_header X-Real-IP $remote_addr;
```
**Что:** Реальный IP клиента.
**Python видит:** `203.0.113.50` вместо `127.0.0.1`.
**Зачем:** Логирование, геолокация, блокировка IP.

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```
**Что:** Цепочка всех IP через которые прошёл запрос.
**Python видит:** `203.0.113.50, 10.0.0.1` (клиент, прокси).
**Зачем:** Если несколько прокси — видишь всю цепочку.

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```
**Что:** Протокол который использовал клиент (http или https).
**Python видит:** `https` даже если Nginx общается с Python по HTTP.
**Зачем:** Чтобы приложение понимало что соединение безопасное.

### Что будет без этих заголовков

| Без заголовка | Проблема |
|---------------|----------|
| Без `Host` | Ссылки генерируются с `127.0.0.1` |
| Без `X-Real-IP` | Все запросы от `127.0.0.1` |
| Без `X-Forwarded-Proto` | HTTPS-редиректы ломаются |

> **Запомни:** Эти 4 заголовка — стандарт.
> Копируй их в каждый конфиг reverse proxy.
> Без них приложение работает неправильно.

---

## 4.5 Полный конфиг reverse proxy для Python

Вот готовый конфиг который ты будешь использовать:

```nginx
server {
    listen 80;
    server_name myapp.local;

    # Логи
    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;

    # Размер загружаемых файлов (по умолчанию 1МБ)
    client_max_body_size 10M;

    # Статические файлы — отдаёт сам Nginx
    location /static/ {
        alias /var/www/myapp/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Всё остальное — Python-приложению
    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Таймауты
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

### Разбор дополнительных директив

```nginx
client_max_body_size 10M;
```
Максимальный размер загружаемого файла.
По умолчанию 1МБ — мало для большинства приложений.

```nginx
location /static/ {
    alias /var/www/myapp/static/;
    expires 30d;
}
```
Nginx сам отдаёт CSS, JS, картинки.
Python не тратит ресурсы на статику.
`expires 30d` — браузер кеширует на 30 дней.

```nginx
proxy_connect_timeout 60s;
```
Сколько ждать пока Python подключится.

```nginx
proxy_read_timeout 60s;
```
Сколько ждать ответ от Python.
Если приложение долго думает — увеличь.

---

## 4.6 `upstream` — группа бэкендов

Когда один Python-сервер не справляется — добавляешь второй.

```nginx
upstream myapp_backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name myapp.local;

    location / {
        proxy_pass http://myapp_backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Nginx будет распределять запросы между тремя серверами.

> **Запомни:** `upstream` — для когда вырастешь.
> Сейчас используй один сервер на `127.0.0.1:8000`.
> Но знай что масштабирование — это просто добавить ещё один `server`.

---

## 4.7 Таймауты: что делать при 504

**504 Gateway Timeout** — Nginx ждал ответ от Python, но не дождался.

### Типичные причины

| Причина | Решение |
|---------|---------|
| Python завис | Проверь логи приложения |
| Долгий запрос к БД | Оптимизируй запрос |
| Таймаут слишком маленький | Увеличь `proxy_read_timeout` |
| Python упал | `systemctl status myapp` |

### Как увеличить таймаут

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;

    # Стандартно 60 секунд
    proxy_connect_timeout 60s;
    proxy_read_timeout 60s;

    # Для медленных эндпоинтов — больше
    proxy_connect_timeout 120s;
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
}
```

> **Совет:** Если `proxy_read_timeout` маленький — приложение не успевает ответить.
> Если слишком большой — пользователь долго ждёт.
> 60 секунд — золотая середина для большинства задач.

---

## 4.8 Логи upstream для отладки производительности

Добавь в `nginx.conf` (в блок `http {}`):

```nginx
log_format upstream_log '$remote_addr - $request - '
    'upstream: $upstream_addr - '
    'status: $upstream_status - '
    'response time: $upstream_response_time';

access_log /var/log/nginx/upstream.log upstream_log;
```

Теперь в логе будет:

```
192.168.1.50 - GET /api/users - upstream: 127.0.0.1:8000 - status: 200 - response time: 0.234
```

| Поле | Значение |
|------|----------|
| `upstream_addr` | Какой бэкенд обработал |
| `upstream_status` | Статус от бэкенда |
| `upstream_response_time` | Сколько секунд думал |

> **Совет:** Если `upstream_response_time` > 1 секунды — приложение тормозит.
> Если `upstream_status` = 502 — приложение упало.

---

## 📝 Упражнения

### Упражнение 4.1: Простой reverse proxy
**Задача:**
1. Создай простое Python-приложение:
   ```bash
   mkdir -p /var/www/myapp
   nano /var/www/myapp/app.py
   ```
   ```python
   from http.server import HTTPServer, BaseHTTPRequestHandler
   import json

   class Handler(BaseHTTPRequestHandler):
       def do_GET(self):
           self.send_response(200)
           self.send_header('Content-Type', 'application/json')
           self.end_headers()
           response = {"path": self.path, "message": "Hello from Python!"}
           self.wfile.write(json.dumps(response).encode())

       def log_message(self, format, *args):
           pass  # Тихо

   if __name__ == '__main__':
       server = HTTPServer(('127.0.0.1', 8000), Handler)
       print("Running on http://127.0.0.1:8000")
       server.serve_forever()
   ```
2. Запусти: `python3 /var/www/myapp/app.py &`
3. Проверь напрямую: `curl http://127.0.0.1:8000/users`
4. Создай Nginx конфиг (как в разделе 4.5, без статики)
5. Включи сайт, проверь конфиг, перезагрузи Nginx
6. Проверь через Nginx: `curl http://myapp.local/users`

### Упражнение 4.2: Заголовки передаются
**Задача:**
1. Измени Python-приложение чтобы печатал заголовки:
   ```python
   def do_GET(self):
       headers = dict(self.headers)
       self.send_response(200)
       self.send_header('Content-Type', 'application/json')
       self.end_headers()
       self.wfile.write(json.dumps(headers).encode())
   ```
2. Проверь что `Host` = `myapp.local` (не `127.0.0.1:8000`)
3. Проверь что `X-Real-IP` есть в заголовках
4. Убери `proxy_set_header` из конфига — что изменилось?
5. Верни заголовки обратно

### Упражнение 4.3: Статика через Nginx
**Задача:**
1. Создай статический файл:
   ```bash
   mkdir -p /var/www/myapp/static
   nano /var/www/myapp/static/test.html
   ```
   Вставь в файл:
   ```html
   <h1>Static!</h1>
   ```
   Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.
2. Добавь `location /static/` в конфиг (как в 4.5)
3. Проверь: `curl http://myapp.local/static/test.html`
4. Проверь что динамика тоже работает: `curl http://myapp.local/api`

### Упражнение 4.4: Таймауты и 504
**Задача:**
1. Создай медленный эндпоинт в Python:
   ```python
   import time
   # В Handler:
   def do_GET(self):
       if self.path == '/slow':
           time.sleep(5)  # Ждём 5 секунд
       self.send_response(200)
       self.end_headers()
       self.wfile.write(b"done")
   ```
2. Поставь `proxy_read_timeout 2s;` в Nginx
3. Запроси: `curl http://myapp.local/slow`
4. Получишь 504? Посмотри error.log
5. Увеличь таймаут до 10s — попробуй снова

### Упражнение 4.5: DevOps Think
**Задача:** «Пользователь получает 502 Bad Gateway. Диагностируй»

Подсказки:
1. Что значит 502? (Nginx не получил ответ от бэкенда)
2. Запущено ли Python-приложение? `systemctl status myapp` или `ps aux | grep python`
3. Слушает ли оно порт 8000? `ss -tlnp | grep 8000`
4. Правильный ли `proxy_pass`? `grep proxy_pass /etc/nginx/sites-enabled/`
5. Что в error.log Nginx? `tail /var/log/nginx/myapp-error.log`
6. Что в логах приложения? `journalctl -u myapp -n 50`

---

## 📋 Чеклист главы 4

- [ ] Я понимаю что такое reverse proxy и зачем он нужен
- [ ] Я могу объяснить `proxy_pass` простыми словами
- [ ] Я понимаю как работает `location` (=, префикс, регулярка)
- [ ] Я знаю 4 обязательных `proxy_set_header` и зачем каждый
- [ ] Я могу написать полный конфиг reverse proxy для Python
- [ ] Я понимаю что такое `upstream` и когда его использовать
- [ ] Я понимаю что делать при 504 (таймауты)
- [ ] Я знаю как добавить upstream-логи для отладки
- [ ] Я понимаю что `client_max_body_size` влияет на загрузку файлов

**Всё отметил?** Переходи к Главе 5 — HTTPS с Let's Encrypt.
