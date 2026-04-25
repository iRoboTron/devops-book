# Глава 4: CSRF, CORS и browser trust boundaries

> **Запомни:** браузер сам по себе становится частью security-модели, и ошибки доверия между origin, cookies и заголовками быстро превращаются в дыры.

---

## 4.1 Контекст и границы

CSRF и CORS часто путают, хотя это разные механизмы. CSRF касается доверия к уже аутентифицированному браузеру, а CORS регулирует, кто может читать ответы браузером.

Неправильная комбинация cookies, SameSite=None, широкого CORS и доверия к proxy headers может ослабить даже нормально написанное приложение.

Эта глава особенно полезна для frontend/backend/API разработчиков и тех, кто прячет backend за reverse proxy.

---

## 4.2 Как выглядит риск

Типовые слабые места:
- state-changing endpoints принимают только cookie и не требуют CSRF protection;
- Access-Control-Allow-Origin: * используется рядом с cookie-based auth;
- приложение доверяет X-Forwarded-* без контроля proxy chain;
- внутренний admin API случайно доступен из браузера как cross-origin ресурс;
- предзапросы OPTIONS настроены бессмысленно широко.

### Где особенно важно
- SPA + API
- legacy server-rendered apps
- internal panels
- BFF architectures

---

## 4.3 Что строит защитник

- CSRF tokens или same-site стратегия для state-changing requests;
- точный allowlist origin для CORS;
- разделение public и private API;
- осторожная обработка X-Forwarded-Proto, X-Forwarded-For и Host;
- аудит POST, PUT, PATCH и DELETE.

### Практический результат главы
- ты различаешь CSRF-защиту и CORS policy;
- можешь объяснить, что реально делает SameSite;
- знаешь, как проверить reverse proxy trust boundary.

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP $remote_addr;
```

```python
ALLOWED_ORIGINS = {
    "https://app.example.com",
    "https://admin.example.com",
}
```

---

## 4.4 Практика

### Шаг 1: Проверь методы, которые меняют состояние
- перечисли endpoints, где происходит изменение данных;
- посмотри, какой механизм защищает их от чужого origin.

```bash
rg -n "POST|PUT|PATCH|DELETE|@router\.(post|put|patch|delete)" app/ src/
```

### Шаг 2: Проверь CORS руками
- сделай запросы с разными Origin и сравни ответы;
- зафиксируй, что именно разрешено читать браузеру.

```bash
curl -I -H 'Origin: https://app.example.com' https://HOST/api/me
curl -I -H 'Origin: https://evil.example' https://HOST/api/me
```

Ожидаемый ответ для разрешённого origin:

```
access-control-allow-origin: https://app.example.com
access-control-allow-credentials: true
```

Ожидаемый ответ для неразрешённого origin:

```
HTTP/2 200
```

Здесь не должно быть `access-control-allow-origin`, иначе браузер даст постороннему сайту читать ответ.

Что считать явной проблемой:

```
access-control-allow-origin: *
```

Если рядом используются cookie или другая браузерная аутентификация, такой ответ слишком широк.

### Шаг 3: Проверь reverse proxy trust
- убедись, что backend знает, от каких прокси он принимает forwarded headers;
- сравни generated absolute URLs, redirect на HTTPS и логи IP-адресов.

```bash
sudo nginx -T | grep -E 'proxy_set_header|X-Forwarded|X-Real|trusted|real_ip'
nmap -Pn -p 8000 SERVER_IP
```

Хороший результат для proxy boundary:

```
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP $remote_addr;
```

А внешний `nmap` должен показывать для backend-порта `closed` или `filtered`, но не `open`.

### Что нужно явно показать
- конкретный список state-changing endpoints;
- какая CORS policy стоит на API;
- как backend получает реальный client IP;
- есть ли CSRF token или эквивалентная защита.

---

## 4.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- на своем стенде отправь запрос с разрешенного и неразрешенного Origin и сравни заголовки ответа;
- проверь, что запросы, меняющие данные, нельзя отправить за счет одной cookie без дополнительной защиты;
- убедись, что absolute redirect не ломается под прокси и не уводит в HTTP.

---

## 4.6 Типовые ошибки

- лечить CSRF через CORS;
- разрешать * для origin по привычке;
- доверять forwarded headers откуда угодно;
- не разделять браузерный и machine-to-machine API.

---

## 4.7 Чеклист главы

- [ ] Я различаю задачи CSRF и CORS
- [ ] Я проверил все state-changing endpoints
- [ ] У меня есть точный allowlist origin
- [ ] Backend корректно работает за reverse proxy
