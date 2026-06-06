# Глава 5: HTTP — запросы, заголовки, коды ответов

## Что вы узнаете

- структуру HTTP-запроса и ответа;
- основные HTTP-методы и коды ответов;
- как использовать `curl` для тестирования API;
- что такое заголовки и зачем они нужны.

**Цель главы:** уверенно использовать `curl` для диагностики, знать коды без гугла.

---

## 5.1 Структура HTTP-запроса

Каждый HTTP-запрос состоит из трёх частей: **стартовая строка**, **заголовки** и **тело** (опционально).

### Запрос (request)

```
GET /api/users HTTP/1.1
Host: api.example.com
User-Agent: curl/7.81.0
Accept: application/json
Authorization: Bearer token123
                                ← пустая строка — разделитель
```
```
POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/json
Content-Length: 34
                                ← пустая строка
{"name": "Alice", "role": "admin"}
```

### Ответ (response)

```
HTTP/1.1 200 OK
Date: Mon, 01 Jan 2026 12:00:00 GMT
Content-Type: application/json
Content-Length: 42
Cache-Control: max-age=3600
                                ← пустая строка
{"users": [{"id": 1, "name": "Alice"}]}
```

### Разбор элементов

```
Метод  URI          Версия HTTP
 │      │            │
GET /api/users HTTP/1.1
│    │              │
│    │              └─ Заголовки (key: value)
│    └─ Тело (через пустую строку)
└─ Стартовая строка
```

```
    Версия   Код  Фраза
    │        │    │
HTTP/1.1 200 OK
    │     │
    │     └─ Стартовая строка
    └─ Заголовки + тело
```

> Пустая строка (`\r\n\r\n`) обязательна. Если её нет — сервер будет ждать заголовки вечно.

---

## 5.2 HTTP-методы

| Метод   | Назначение              | Есть тело | Идемпотентный | Безопасный |
|---------|-------------------------|-----------|---------------|------------|
| GET     | Получить ресурс         | Нет       | Да            | Да         |
| POST    | Создать/отправить данные| Да        | Нет           | Нет        |
| PUT     | Полностью заменить ресурс | Да      | Да            | Нет        |
| PATCH   | Частично изменить ресурс| Да        | Нет           | Нет        |
| DELETE  | Удалить ресурс          | Нет       | Да            | Нет        |
| HEAD    | Получить заголовки (без тела) | Нет | Да          | Да         |
| OPTIONS | Какие методы разрешены  | Нет       | Да            | Да         |

- **Безопасный** (safe) — не меняет состояние сервера.
- **Идемпотентный** — повторный запрос даёт тот же результат.

### Пример: разница POST vs PUT

```bash
# POST — каждый раз создаёт новый ресурс
curl -X POST -d '{"title":"a"}' https://jsonplaceholder.typicode.com/posts
# → {"id": 101, ...}

curl -X POST -d '{"title":"a"}' https://jsonplaceholder.typicode.com/posts
# → {"id": 102, ...}

# PUT — заменяет по ID, повтор даёт то же самое
curl -X PUT -d '{"title":"b"}' https://jsonplaceholder.typicode.com/posts/1
# → {"id": 1, "title": "b", ...}

curl -X PUT -d '{"title":"b"}' https://jsonplaceholder.typicode.com/posts/1
# → {"id": 1, "title": "b", ...}   (тот же результат)
```

---

## 5.3 Коды ответов

### 2xx — Успех

| Код | Фраза           | Когда                                           |
|-----|-----------------|--------------------------------------------------|
| 200 | OK              | GET, PUT, PATCH — всё хорошо                     |
| 201 | Created         | POST — ресурс создан (в Location — его URL)      |
| 204 | No Content      | DELETE — успешно удалён, тело пустое             |

### 3xx — Перенаправление

| Код | Фраза              | Когда                                           |
|-----|---------------------|--------------------------------------------------|
| 301 | Moved Permanently   | Ресурс навсегда переехал (Location)              |
| 302 | Found               | Временный редирект                               |
| 304 | Not Modified        | Ответ не изменился (If-Modified-Since/ETag)      |

### 4xx — Ошибка клиента

| Код | Фраза                 | Когда                                           |
|-----|------------------------|--------------------------------------------------|
| 400 | Bad Request           | Кривой JSON, невалидные параметры                |
| 401 | Unauthorized          | Нет или плохой токен                             |
| 403 | Forbidden             | Токен есть, но прав нет                          |
| 404 | Not Found             | Ресурс не найден                                 |
| 405 | Method Not Allowed    | POST на GET-only endpoint                        |
| 409 | Conflict              | Конфликт версий (напр. параллельное редактирование) |
| 422 | Unprocessable Entity  | Валидация не прошла                              |
| 429 | Too Many Requests     | Rate limit превышен                              |

### 5xx — Ошибка сервера

| Код | Фраза                | Когда                                           |
|-----|-----------------------|--------------------------------------------------|
| 500 | Internal Server Error | Паника в коде приложения                         |
| 502 | Bad Gateway           | Балансировщик не дождался ответа от бэкенда      |
| 503 | Service Unavailable   | Сервер перегружен, отключён на обслуживание       |
| 504 | Gateway Timeout       | Бэкенд не ответил за таймаут балансировщика      |

### Быстрая памятка

```
1xx — информация (редко видите)
2xx — всё ок
3xx — иди туда
4xx — ты дурак
5xx — я дурак (или сервер сломался)
```

---

## 5.4 curl — диагностика HTTP

`curl` — швейцарский нож для HTTP. Установка, если нет:

> ☠️ **Осторожно:** Если команда не найдена:

```bash
sudo apt install curl
```

### Базовые запросы

```bash
# Простой GET
curl https://httpbin.org/get

# Только заголовки ответа (HEAD)
curl -I https://httpbin.org/get

# Подробный вывод — вся структура запроса и ответа
curl -v https://httpbin.org/get
```

### Работа с методами и телом

```bash
# POST с JSON
curl -X POST -H "Content-Type: application/json" \
     -d '{"name":"test"}' https://httpbin.org/post

# PUT
curl -X PUT -H "Content-Type: application/json" \
     -d '{"name":"updated"}' https://httpbin.org/put

# DELETE
curl -X DELETE https://httpbin.org/delete
```

### Аутентификация и заголовки

```bash
# Bearer-токен
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
     https://api.example.com/users

# Basic Auth
curl -u admin:password https://httpbin.org/basic-auth/admin/password
```

### Редиректы

```bash
# curl НЕ следует редиректам по умолчанию
curl -I https://bit.ly/example

# С флагом -L — следует
curl -L https://bit.ly/example
```

### Сохранение в файл

```bash
# Сохранить тело ответа
curl -o output.json https://api.example.com/data

# Сохранить под оригинальным именем (-O)
curl -O https://example.com/file.zip
```

### Таймауты

```bash
# --connect-timeout — время на установку соединения
# --max-time — полное время запроса (включая передачу данных)
curl --connect-timeout 5 --max-time 30 https://api.example.com
```

### Измерение времени ответа

```bash
# -w — вывести кастомные данные после запроса
curl -w "\n┌────────────────────┬────────────┐
│ time_namelookup    │ %{time_namelookup}s │
│ time_connect       │ %{time_connect}s │
│ time_appconnect    │ %{time_appconnect}s │
│ time_pretransfer   │ %{time_pretransfer}s │
│ time_starttransfer │ %{time_starttransfer}s │
│ time_total         │ %{time_total}s │
└────────────────────┴────────────┘\n" \
     -o /dev/null -s https://example.com
```

```
┌────────────────────┬────────────┐
│ time_namelookup    │ 0.012s     │  ← DNS
│ time_connect       │ 0.025s     │  ← TCP handshake
│ time_appconnect    │ 0.089s     │  ← TLS handshake
│ time_pretransfer   │ 0.089s     │
│ time_starttransfer │ 0.134s     │  ← первый байт ответа
│ time_total         │ 0.135s     │  ← всё
└────────────────────┴────────────┘
```

### Проверка здоровья (healthcheck)

```bash
# -f — считать 4xx/5xx ошибкой (возвращает код 22)
curl -f -s https://api.example.com/health && echo "OK" || echo "FAIL"
```

### Self-signed сертификаты

> ☠️ **Осторожно:** Никогда не используйте `-k` в production — это отключает проверку сертификата!

```bash
curl -k https://self-signed.example.com
```

Для самоподписанного сертификата правильнее указать CA-файл:

```bash
curl --cacert /path/to/ca.crt https://self-signed.example.com
```

### Полный профилировочный запрос

```bash
curl -w "@curl-format.txt" -o /dev/null -s https://example.com
```

Где `curl-format.txt`:

```
    time_namelookup:  %{time_namelookup}s\n
       time_connect:  %{time_connect}s\n
    time_appconnect:  %{time_appconnect}s\n
   time_pretransfer:  %{time_pretransfer}s\n
 time_starttransfer:  %{time_starttransfer}s\n
--------------------\n
        time_total:  %{time_total}s\n
  http_code: %{http_code}\n
  size_download: %{size_download} bytes\n
```

---

## 5.5 Важные HTTP-заголовки

### Заголовки запроса (клиент → сервер)

| Заголовок         | Назначение                               | Пример                                     |
|-------------------|------------------------------------------|--------------------------------------------|
| `Host`            | Обязательный — какой виртуальный хост    | `Host: api.example.com`                    |
| `Authorization`   | Передача токена или учётных данных       | `Authorization: Bearer <token>`            |
| `Content-Type`    | Тип тела запроса                         | `Content-Type: application/json`           |
| `Accept`          | Какой формат ответа клиент понимает      | `Accept: application/json`                 |
| `User-Agent`      | Идентификация клиента                    | `User-Agent: curl/7.81.0`                  |
| `Cookie`          | Передача кук                             | `Cookie: session_id=abc123`                |
| `Referer`         | Откуда пришёл клиент                     | `Referer: https://example.com/page1`       |
| `X-Request-ID`    | Идентификатор запроса для трейсинга      | `X-Request-ID: 550e8400-e29b-...`          |

### Заголовки ответа (сервер → клиент)

| Заголовок            | Назначение                                      |
|----------------------|-------------------------------------------------|
| `Content-Type`       | Тип тела ответа (`application/json`, `text/html`)|
| `Content-Length`     | Размер тела в байтах                            |
| `Cache-Control`      | Политика кэширования (`max-age=3600`, `no-cache`)|
| `Location`           | URL для редиректа (301, 302)                    |
| `Set-Cookie`         | Установить куку у клиента                       |
| `WWW-Authenticate`   | Запрос аутентификации (401)                     |
| `X-Request-ID`       | Тот же ID, что клиент передал                   |
| `Retry-After`        | Через сколько повторять (429, 503)              |

### Пример: трейсинг запроса

```bash
# Клиент передаёт ID
curl -v -H "X-Request-ID: $(uuidgen)" https://httpbin.org/headers
```

```
> GET /headers HTTP/1.1
> Host: httpbin.org
> X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

Сервер (если настроен) вернёт тот же ID в ответе — это позволяет связать запрос и ответ в логах.

---

## Типичные ошибки

### 1. 502 = смотреть логи приложения

502 Bad Gateway — сервер (nginx, haproxy) не получил ответ от бэкенда за таймаут. **Не лезьте в сеть — лезьте в логи приложения.**

```
nginx → прокси → app (port 3000)
                   └── таймаут / упал → 502
```

```bash
# Проверить, жив ли бэкенд
curl -f -s http://localhost:3000/health
```

### 2. curl: (7) Failed to connect

```
curl: (7) Failed to connect to api.example.com port 443: Connection refused
```

- Сервер не слушает порт (не запущен, не тот порт, firewall);
- DNS отдаёт не тот IP;
- До сервера нет маршрута.

```bash
# Проверка
ss -tlnp | grep 443        # слушает ли процесс
curl -v http://api.example.com:443  # или https?
curl --connect-timeout 3 http://api.example.com:3000  # может, порт другой?
```

### 3. curl: (60) SSL certificate problem

```
curl: (60) SSL certificate problem: self-signed certificate in certificate chain
```

- Самоподписанный сертификат → `--cacert` (не `-k` в production);
- Истёкший сертификат;
- Неправильное имя в сертификате (SAN не совпадает с Host);

```bash
# Диагностика
echo | openssl s_client -connect api.example.com:443 -servername api.example.com 2>/dev/null | openssl x509 -noout -dates
```

### 4. 404 ≠ сервис не работает

404 — это корректный ответ сервера. Сервис жив, но ресурса нет. Проверьте:
- есть ли опечатка в URL;
- не переехал ли ресурс (301/308);
- правильный ли метод.

### 5. HTTPS vs HTTP

Не путайте порты: HTTPS = 443, HTTP = 80. `curl` сам выберет порт по схеме, но если сервер слушает HTTPS на 8080 — укажите явно:

```bash
curl -k https://api.example.com:8080/health
```

---

## Чек-лист

- [ ] `curl -v <url>` — заголовки запроса и ответа + тайминги;
- [ ] `curl -I <url>` — только заголовки (быстрая проверка);
- [ ] `curl -w "%{http_code}" -o /dev/null -s <url>` — код ответа;
- [ ] `curl --connect-timeout 5 --max-time 30 <url>` — таймауты.

---

## Попробуйте сами

**Задание 1. Разбор curl -v**

```bash
curl -v https://httpbin.org/get
```

Найдите в выводе:
- TLS handshake (`* TLSv1.3 (IN), TLS handshake, ...`);
- заголовки запроса (строки с `>`);
- заголовки ответа (строки с `<`);
- код ответа и тело.

**Задание 2. Профилирование с -w**

Сравните тайминги для трёх сайтов:

```bash
curl -w "time_total: %{time_total}s\n" -o /dev/null -s https://google.com
curl -w "time_total: %{time_total}s\n" -o /dev/null -s https://httpbin.org
curl -w "time_total: %{time_total}s\n" -o /dev/null -s https://github.com
```

Какой быстрее? Почему? Добавьте `-w` с разбивкой по этапам (DNS, TCP, TLS, первый байт).

**Задание 3. Коды ответов**

Попробуйте получить разные коды:

```bash
# 200 — успех
curl -s -w "%{http_code}\n" -o /dev/null https://httpbin.org/get

# 404 — не найдено
curl -s -w "%{http_code}\n" -o /dev/null https://httpbin.org/status/404

# 500 — ошибка сервера
curl -s -w "%{http_code}\n" -o /dev/null https://httpbin.org/status/500

# 429 — rate limit
for i in $(seq 1 20); do
  curl -s -w " %{http_code}\n" -o /dev/null https://httpbin.org/status/429
done | sort | uniq -c
```

Можете ли вы по коду определить, проблема на стороне клиента или сервера?
