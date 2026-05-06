# Глава 3: HTTP security headers

> **Цель:** понять заголовки безопасности и не сломать приложение строгой настройкой.

---

## 3.1 Проверка curl

```bash
curl -s -D - https://yourdomain.com -o /dev/null \
  | tee audits/2026-05-06/headers.txt
```

Флаг `-D -` выводит заголовки ответа в stdout. `-o /dev/null` отбрасывает тело страницы.

**Пример «плохого» вывода (нет security headers):**

```
# Пример вывода — отсутствуют security headers:
HTTP/2 200
server: nginx/1.24.0
date: Tue, 06 May 2026 14:35:22 GMT
content-type: text/html; charset=utf-8
content-length: 4821
x-powered-by: PHP/8.1.0
```

Что здесь плохо:

- `x-powered-by: PHP/8.1.0` — сервер раскрывает технологию и версию PHP. Атакующий знает, что искать в CVE-базах. Легко скрыть.
- Нет `x-frame-options` — возможен clickjacking.
- Нет `x-content-type-options` — браузер может угадывать тип контента.
- Нет `strict-transport-security` — HSTS не настроен.
- Нет `content-security-policy` — нет ограничений источников скриптов.
- `server: nginx/1.24.0` — раскрывает версию nginx. Можно скрыть через `server_tokens off;`.

**Пример «хорошего» вывода (все заголовки есть):**

```
# Пример вывода — security headers настроены:
HTTP/2 200
server: nginx
date: Tue, 06 May 2026 14:35:22 GMT
content-type: text/html; charset=utf-8
content-length: 4821
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
strict-transport-security: max-age=31536000; includeSubDomains
content-security-policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```

Что здесь хорошо:

- `server: nginx` — версия скрыта (`server_tokens off;` в Nginx).
- `x-powered-by` — отсутствует (убрали через `fastcgi_hide_header X-Powered-By;`).
- `x-frame-options: SAMEORIGIN` — iframe разрешены только с того же домена.
- `x-content-type-options: nosniff` — браузер не угадывает MIME-тип.
- `strict-transport-security` — браузер запомнит: только HTTPS на год.

---

## 3.2 Разница: заголовок отсутствует vs неправильно настроен

**Заголовок отсутствует** — его нет в ответе совсем. curl не покажет эту строку. Это исправляется добавлением `add_header` в Nginx.

**Заголовок неправильно настроен** — присутствует, но значение некорректное. Пример:

```
# Пример неправильно настроенного заголовка:
strict-transport-security: max-age=60
```

`max-age=60` — HSTS запомнен только на 60 секунд. Рекомендуется минимум `max-age=31536000` (1 год). Инструменты типа securityheaders.com часто дают низкую оценку именно за слишком короткий `max-age`.

Другой пример:

```
# Пример неправильного CSP:
content-security-policy: default-src *
```

`default-src *` разрешает загрузку ресурсов с любого домена — это не защита, а заглушка. Заголовок есть, но бесполезен.

---

## 3.3 Основные заголовки

| Заголовок | Зачем | Осторожность |
|---|---|---|
| `X-Frame-Options` | clickjacking | может мешать embed |
| `X-Content-Type-Options` | MIME sniffing | обычно безопасен |
| `Referrer-Policy` | меньше утечек URL | выбрать режим |
| `Strict-Transport-Security` | принудительный HTTPS | осторожно на тестах |
| `Content-Security-Policy` | ограничить источники | легко ломает UI |

`X-XSS-Protection` устарел — современные браузеры его игнорируют. Если nikto или другой инструмент предупреждает об отсутствии этого заголовка, это **low priority** и не является реальной проблемой.

---

## 3.4 Пример Nginx

```nginx
# Скрыть версию
server_tokens off;

# Скрыть X-Powered-By (если PHP через FastCGI)
fastcgi_hide_header X-Powered-By;

add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

CSP для Nextcloud, Grafana и других сложных приложений не копируй вслепую. Сначала тестируй.

---

## 3.5 Практика

Сравни headers до и после изменения. Проверка: сайт открывается, интерфейс не сломан, а нужные заголовки появились.
