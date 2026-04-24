# Инструкция агенту: улучшение книги 16 «Веб-безопасность для программиста»

## Контекст

Книга находится в директории:
```
/home/adelfos/Documents/lessons/dev-ops/docs/books/16-web-security-devops/
```

Файлы: `chapter-01.md` … `chapter-09.md`, `appendix-a.md`, `appendix-b.md`

Книга структурно лучше книги 15 — есть чёткие trust-boundary объяснения и конкретные grep-команды для поиска уязвимостей в коде. Главная проблема — **проверки описаны словами, а не выводом**. Читатель запускает `curl -I` или `psql \du` и не знает, что он должен увидеть и что считать «плохим» результатом. Вторая проблема — **код в блоках `text` вместо `python`/`nginx`/`bash`**, из-за чего теряется подсветка и структура.

---

## Общее правило качества

Каждая практическая проверка должна содержать:

1. **Команду** — конкретную, запускаемую
2. **Ожидаемый вывод** — хотя бы 3-5 строк реального результата
3. **Что считать проблемой** — конкретная строка или паттерн, который говорит «здесь что-то не так»

Если любой из пунктов отсутствует — раздел нужно дописать.

---

## Что НЕ трогать

- Структуру разделов (нумерацию и названия оставить)
- Чеклисты в конце глав
- Блоки «Типовые ошибки»
- Блок «Lab-only проверка»
- Общий стиль и тон

---

## Технический fix для всех глав: сменить тип блоков кода

Во всех главах код находится в блоках ` ```text `. Это неправильно — замени везде:

- Python-код → ` ```python `
- nginx-конфиги → ` ```nginx `
- bash-команды → ` ```bash `
- SQL → ` ```sql `
- ini/env → ` ```ini `

Это касается всех блоков в разделах «Что строит защитник» (секция с примером кода в каждой главе).

---

## Задачи по каждой главе

---

### Глава 1 (`chapter-01.md`) — Аутентификация, сессии, password reset

**Проблема 1:** Раздел 1.2 перечисляет риски, но не показывает как выглядит `user enumeration` в HTTP-ответе — ключевой момент.

**Что добавить** после перечня рисков в 1.2:

```bash
# Запрос с существующим пользователем
curl -s -o /dev/null -w "%{http_code}" -X POST https://HOST/login \
  -d '{"email":"real@example.com","password":"wrong"}'
# → 401  {"error": "Invalid password"}

# Запрос с несуществующим
curl -s -o /dev/null -w "%{http_code}" -X POST https://HOST/login \
  -d '{"email":"fake@example.com","password":"wrong"}'
# → 401  {"error": "User not found"}   ← ПРОБЛЕМА: разные сообщения = enumeration
```

Правильный вариант: одно и то же сообщение для обоих случаев:
```
{"error": "Invalid credentials"}
```

---

**Проблема 2:** Раздел 1.3 — Python-пример cookie в блоке `text`. Надо сменить на `python` и расширить: показать что именно делает каждый флаг.

Заменить существующий блок на:

```python
# FastAPI / Starlette
response.set_cookie(
    key="session",
    value=session_id,
    httponly=True,    # JS не читает cookie — защита от XSS-кражи
    secure=True,      # только HTTPS — браузер не шлёт по HTTP
    samesite="lax",   # не уходит в cross-site POST — базовая CSRF-защита
    max_age=1800,     # 30 минут — короткий TTL
    path="/",
)
```

---

**Проблема 3:** Раздел 1.4 «Шаг 1» — команды есть, но нет примера что должно быть в ответе.

Добавить после команд пример вывода `curl -vk https://HOST/login`:

```
< HTTP/2 200
< set-cookie: session=abc123; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=1800
```

И что считать проблемой:
```
< set-cookie: session=abc123; Path=/
  ↑ нет HttpOnly, нет Secure, нет SameSite — это плохо
```

---

**Проблема 4:** Раздел 1.4 «Шаг 3» — `sudo tail -f /var/log/nginx/access.log` показан, но не объяснено что искать.

Добавить пример строки при burst-атаке и как её найти:

```bash
sudo awk '$9 == 401' /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head
```

Пример вывода:
```
     47 185.234.X.X    ← 47 ошибок с одного IP — это либо атака, либо баг
      3 192.168.1.10
```

---

### Глава 2 (`chapter-02.md`) — SQLi и безопасная работа с базой

**Проблема 1:** Раздел 2.3 — Python-примеры в блоке `text`. Сменить на `python`.

**Проблема 2:** Раздел 2.4 «Шаг 2» — `psql \du` и `\z` без примера что считать опасным.

Добавить пример вывода `\du`:

```
                                   List of roles
 Role name  |                         Attributes
------------+------------------------------------------------------------
 postgres   | Superuser, Create role, Create DB, Replication, Bypass RLS
 app_user   | (none)
```

Что считать проблемой:
```
 app_user   | Superuser   ← приложение работает как суперпользователь — это опасно
```

Правильный вид: `app_user` без атрибутов, только права на нужные таблицы через `GRANT`.

Добавить команду которая показывает что конкретно может app_user:

```sql
-- В psql
\z users
\z orders
```

Пример безопасного вывода:
```
 Schema | Name  | Type  |   Access privileges
--------+-------+-------+------------------------
 public | users | table | app_user=r/postgres
                         ↑ r = SELECT only, no INSERT/UPDATE/DELETE
```

---

**Проблема 3:** Раздел 2.4 «Шаг 3» — проверяем права, но нет примера как должно выглядеть разделение migration user / runtime user.

Добавить новый подраздел **2.4а «Пример разделения пользователей БД»**:

```sql
-- Создаём отдельных пользователей
CREATE USER app_runtime WITH PASSWORD 'runtime_pass';
CREATE USER app_migration WITH PASSWORD 'migration_pass';

-- Runtime — только SELECT/INSERT/UPDATE/DELETE на нужные таблицы
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime;

-- Migration — полные права на схему, используется только в CI/CD
GRANT ALL PRIVILEGES ON DATABASE myapp TO app_migration;
```

В `.env` приложения:
```ini
DATABASE_URL=postgresql://app_runtime:runtime_pass@localhost:5432/myapp
```

В CI/CD:
```ini
DATABASE_MIGRATION_URL=postgresql://app_migration:migration_pass@localhost:5432/myapp
```

---

**Проблема 4:** Нет примера как выглядит SQL-ошибка в HTTP-ответе (плохо) vs в логах (правильно).

Добавить в раздел 2.4 пример:

```bash
# Плохо — ошибка видна клиенту:
curl -s https://HOST/search?q=\' | head -20
# → {"error": "ERROR:  unterminated quoted string at or near \"'\" LINE 1: SELECT * FROM products WHERE name = '''"}
#              ↑ раскрывает структуру БД и тип ошибки

# Правильно — ошибка скрыта:
curl -s https://HOST/search?q=\' | head -5
# → {"error": "Search failed. Please try again."}
```

Как проверить что ошибка уходит в лог (а не клиенту):

```bash
journalctl -u myapp -n 50 --no-pager | grep -i "error\|exception\|sql"
```

---

### Глава 3 (`chapter-03.md`) — XSS, экранирование, CSP

**Проблема 1:** Раздел 3.3 — CSP header и JS-примеры в блоке `text`. Сменить на `nginx` и `javascript`.

**Проблема 2:** Раздел 3.4 «Шаг 2» — `curl -I https://HOST` без примера что должно быть в ответе.

Добавить пример хорошего и плохого вывода:

```bash
curl -I https://HOST | grep -i "content-security\|x-content\|x-frame"
```

Хороший вывод:
```
content-security-policy: default-src 'self'; script-src 'self'; object-src 'none'
x-content-type-options: nosniff
x-frame-options: SAMEORIGIN
```

Плохой (нет CSP вообще или опасная):
```
content-security-policy: default-src *; script-src 'unsafe-inline' 'unsafe-eval'
                                     ↑ разрешает всё — CSP бессмысленна
```

---

**Проблема 3:** Раздел 3.4 «Шаг 3» — «введи строку со спецсимволами» — слишком абстрактно. Не сказано какую строку и что именно проверять.

Добавить конкретную тестовую строку и ожидаемый результат:

Безопасная тестовая строка для lab:
```
<b>тест</b> & "кавычки" 'одинарные'
```

Ожидаемое поведение в браузере:
- если видишь буквально `<b>тест</b>` — ввод экранирован правильно (отображается как текст)
- если слово **тест** выделено жирным — ввод попал в DOM как HTML (XSS-риск)

Добавить: как смотреть CSP violations в DevTools:

```
DevTools → Console → ищи сообщения вида:
Refused to execute inline script because it violates the following Content Security Policy directive: "script-src 'self'"
```

Если нет нарушений — CSP работает. Если их слишком много на нормальных страницах — CSP сломана или бессмысленна (unsafe-inline).

---

### Глава 4 (`chapter-04.md`) — CSRF, CORS, browser trust

**Проблема 1:** Раздел 4.3 — код proxy в блоке `text`. Сменить: nginx → `nginx`, Python → `python`.

**Проблема 2:** Раздел 4.4 «Шаг 2» — curl с разными Origin хороший пример, но нет ожидаемых ответов.

Добавить что должно быть в ответе:

```bash
# Разрешённый origin
curl -I -H 'Origin: https://app.example.com' https://HOST/api/me
```

Ожидаемый вывод (CORS работает правильно):
```
access-control-allow-origin: https://app.example.com
access-control-allow-credentials: true
```

```bash
# Неразрешённый origin
curl -I -H 'Origin: https://evil.example' https://HOST/api/me
```

Ожидаемый вывод (запрос отклонён):
```
HTTP/2 200
# Нет заголовка access-control-allow-origin → браузер не даст читать ответ
```

Что считать проблемой:
```
access-control-allow-origin: *
                             ↑ вместе с куки и авторизацией — это уязвимость
```

---

**Проблема 3:** Раздел 4.4 «Шаг 3» — `sudo nginx -T | sed -n '1,220p'` — странная команда. Число 220 случайное, `sed` не нужен. Заменить на осмысленную:

```bash
# Найти всё что связано с forwarded headers и proxy_set_header в конфиге
sudo nginx -T | grep -E 'proxy_set_header|X-Forwarded|X-Real|trusted|real_ip'
```

Ожидаемый хороший вывод:
```
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP $remote_addr;
```

Что считать проблемой — если backend доверяет этим заголовкам не от nginx, а от кого угодно. Добавить как проверить что nginx реально единственная точка входа:

```bash
# Убедиться что backend порт не доступен напрямую снаружи
nmap -Pn -p 8000 SERVER_IP
# Должно быть: filtered или closed — не open
```

---

### Глава 5 (`chapter-05.md`) — SSRF, file upload

**Проблема 1:** Раздел 5.3 — Python-код в блоке `text`. Сменить на `python`.

**Проблема 2:** Раздел 5.4 «Шаг 3» — показывает команду grep в nginx-конфиге, но не показывает как должен выглядеть правильный nginx-блок с ограничениями upload.

Добавить пример конфига:

```nginx
# Nginx: ограничить размер тела запроса глобально и для upload endpoint
client_max_body_size 5m;

location /upload {
    client_max_body_size 10m;  # переопределить для этого endpoint
    proxy_pass http://127.0.0.1:8000;
    proxy_request_buffering on;
}
```

---

**Проблема 3:** Нет примера как выглядит заблокированный SSRF-запрос — что отдаёт приложение когда попытка идёт на внутренний адрес.

Добавить в раздел 5.5 (lab-only проверка) пример controlled теста:

```bash
# На своём стенде: попытка SSRF к localhost через параметр URL
curl -s "https://HOST/fetch?url=http://127.0.0.1:5432"
```

Ожидаемые варианты ответа:
- Правильно: `{"error": "URL not allowed"}` — allowlist сработал
- Неправильно: подвисает на несколько секунд, потом таймаут — backend реально пытается подключиться

Дополнить: как проверить что backend не уходит на metadata endpoint (если VPS в AWS/GCP):

```bash
# В своей lab: проверить не уходит ли запрос на 169.254.169.254
curl -s "https://HOST/fetch?url=http://169.254.169.254/latest/meta-data/"
# Ожидаемо: {"error": "URL not allowed"} или 400
```

---

### Глава 6 (`chapter-06.md`) — Секреты, .env, reverse proxy

**Проблема:** Самая слабая глава. Раздел 6.3 — чистый список из 5 пунктов без единого объяснения механики. Раздел 6.4 «Шаг 1» — показывает `nano .env.example` (просто открыть файл), не объясняет что должно быть внутри.

**Что добавить — полностью переписать разделы 6.3 и 6.4:**

**6.3 — заменить список на конкретные примеры:**

Плохой `.env.example` (реальные секреты в шаблоне):
```ini
APP_ENV=production
DATABASE_URL=postgresql://myapp:SuperSecret123@db:5432/myapp
SECRET_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ123456
STRIPE_SECRET_KEY=sk_live_AbCdEfGhIjKlMnOpQrStUv
```

Правильный `.env.example` (только шаблон):
```ini
APP_ENV=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
SECRET_KEY=REPLACE_WITH_RANDOM_64_CHARS
STRIPE_SECRET_KEY=REPLACE_WITH_STRIPE_KEY
```

Как проверить что реальный `.env` не попал в git (выполнить сейчас):
```bash
# Проверить текущее состояние
git status .env 2>/dev/null || echo "not a git repo or .env not tracked"
cat .gitignore | grep ".env"

# Проверить историю — не был ли .env в коммитах раньше
git log --all --full-history -- '*.env' | head -5
# Если вывод не пустой — секреты уже в истории, надо чистить
```

Проверить права на файл:
```bash
ls -la .env
# Должно быть: -rw------- (600), владелец = app user
# Плохо: -rw-r--r-- (644) — читают все пользователи системы
```

Исправить права:
```bash
chmod 600 .env
chown app:app .env
```

---

**6.4 «Шаг 2» — проверка reverse proxy boundary:**

Убрать `sudo nginx -T | sed -n '1,240p'` (бессмысленный диапазон). Заменить на целевые проверки:

```bash
# Проверить redirect HTTP → HTTPS
curl -I http://HOST
# Ожидаемо: 301 или 302 с Location: https://

# Проверить HSTS в ответе
curl -sI https://HOST | grep -i strict
# Ожидаемо: strict-transport-security: max-age=31536000

# Проверить что X-Forwarded-For передаётся корректно
curl -sI https://HOST/api/me | head -10
# В логах приложения должен быть реальный IP, а не 127.0.0.1
```

---

**6.4 «Шаг 3» — поиск утечек секретов:**

Расширить. Добавить поиск не только в коде но и в git-истории:

```bash
# Поиск в текущем коде
rg -n "SECRET|TOKEN|PASSWORD|API_KEY|DATABASE_URL" . --type py --type js

# Поиск в логах старта — не печатает ли приложение окружение
journalctl -u myapp -n 50 --no-pager | grep -i "secret\|token\|password\|key"

# Поиск в git-истории (выполнить один раз обязательно)
git log --all -p | grep -E "SECRET_KEY|API_KEY|PASSWORD" | head -20
```

Если последняя команда нашла что-то — секрет уже в истории. Это отдельная проблема (нужно rotate ключи и чистить историю).

---

**Добавить новый раздел 6.4а «Проверка backup-файлов»:**

Боты постоянно сканируют типичные имена:

```bash
# Проверить на своём стенде что эти файлы недоступны
for f in .env .env.bak .env.old config.php.bak database.yml.bak; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://HOST/$f")
  echo "$code $f"
done
```

Ожидаемый вывод (правильно):
```
404 .env
404 .env.bak
404 .env.old
```

Если любой вернул `200` — веб-сервер отдаёт конфигурационный файл напрямую. Исправить: в nginx добавить:

```nginx
location ~* \.(env|bak|old|orig|backup)$ {
    deny all;
    return 404;
}
```

---

### Глава 7 (`chapter-07.md`) — Зависимости и supply chain

**Проблема:** Раздел 7.3 просто перечисляет три инструмента (`pip-audit`, `npm audit`, `trivy`) без вывода. Читатель не знает как выглядит находка и что с ней делать.

**Что добавить** в раздел 7.4 после каждой команды — пример вывода и что из него делать:

```bash
pip-audit
```

Пример вывода с находкой:
```
Name        Version  ID                  Fix Versions
----------- -------- ------------------- ------------
Pillow      9.0.0    GHSA-4fx9-vc88-q2xc 9.0.1
cryptography 3.4.7   GHSA-x9w5-v3q2-3rhw 38.0.3
```

Что делать: не обновлять всё сразу. Сначала:
1. Прочитать GHSA-ссылку: что именно уязвимо и при каких условиях
2. Проверить, используется ли уязвимая функция в проекте
3. Если да — обновить и прогнать тесты
4. Если нет — зафиксировать в KNOWN_ISSUES с объяснением почему не критично

```bash
npm audit --production
```

Пример вывода:
```
# npm audit report
lodash  <4.17.21
Severity: high
Prototype Pollution in lodash - https://npmjs.com/advisories/1523
Dependents: webpack > loader-utils > lodash
fix available via `npm audit fix`
```

Что делать: `npm audit fix` — только после проверки что fix не ломает API.

```bash
trivy image myapp:latest
```

Пример вывода:
```
myapp:latest (ubuntu 22.04)
Total: 3 (HIGH: 1, MEDIUM: 2)

│ Library      │ Vulnerability   │ Severity │ Installed │ Fixed  │
│ openssl      │ CVE-2023-XXXXX  │ HIGH     │ 3.0.2     │ 3.0.7  │
```

Что делать: если HIGH в base image — обновить base image (`FROM ubuntu:22.04` → актуальная) и пересобрать.

---

**Проблема 2:** Раздел 7.4 «Шаг 3» — поиск `latest` в Dockerfile. Добавить пример как pinned-версия выглядит правильно:

Плохо:
```dockerfile
FROM python:latest
```

Лучше (pinned tag):
```dockerfile
FROM python:3.12-slim
```

Ещё лучше (pinned digest — не изменится никогда):
```dockerfile
FROM python:3.12-slim@sha256:abc123def456...
```

Получить digest текущего образа:
```bash
docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
```

---

### Глава 8 (`chapter-08.md`) — Практика безопасной проверки

**Проблема:** Глава описывает «что проверять», но почти нет «как выглядит результат». Раздел 8.3 — чистый список вопросов без команд.

**Что добавить:**

**8.3 «Проверка cookie»** — добавить конкретную команду и вывод:

```bash
curl -sI https://HOST/login -X POST \
  -d 'username=test&password=test' | grep -i set-cookie
```

Пример хорошего вывода:
```
set-cookie: session=xyz; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=1800
```

Чек-лист для каждого cookie:
- `HttpOnly` — есть?
- `Secure` — есть?
- `SameSite` — Lax или Strict (не None)?
- `Max-Age` или `Expires` — разумный TTL?

---

**8.3 «Проверка SSRF/file upload»** — добавить конкретную последовательность:

```bash
# 1. Проверить максимальный размер файла
curl -s -w "\n%{http_code}" -F "file=@/dev/urandom" https://HOST/upload | tail -1
# Ожидаемо: 413 (слишком большой) если client_max_body_size настроен

# 2. Проверить что Content-Type проверяется на сервере
curl -s -X POST https://HOST/upload \
  -F "file=@shell.php;type=image/jpeg" | head
# Ожидаемо: {"error": "Invalid file type"} — если проверка по MIME работает
# Плохо: 200 + файл загружен — только extension-проверка, MIME подделан
```

---

**8.4 «Сценарий 1: Логин и reset»** — добавить конкретные команды:

```bash
# Проверить user enumeration
curl -s -X POST https://HOST/login -H 'Content-Type: application/json' \
  -d '{"email":"exists@example.com","password":"wrong"}' | jq .error
curl -s -X POST https://HOST/login -H 'Content-Type: application/json' \
  -d '{"email":"notexists@example.com","password":"wrong"}' | jq .error

# Правильно: оба ответа одинаковые
# "Invalid credentials"
# "Invalid credentials"

# Неправильно: разные ответы
# "Invalid password"
# "User not found"
```

---

### Глава 9 (`chapter-09.md`) — Итоговый проект

**Проблема:** Нет ожидаемого результата для каждой фазы — читатель не знает прошёл ли он фазу.

**Что добавить** — в каждую фазу раздела 9.3 добавить блок «Как понять что фаза пройдена»:

**Фаза 1 — пройдена если:**
```bash
# Все trust boundaries записаны, каждый endpoint проверен
# Можешь ответить на вопросы:
# - Сколько форм принимают внешний ввод? (назвать)
# - Какие cookie выдаёт приложение? (перечислить с флагами)
# - Где хранятся секреты? (путь к .env и права)
```

**Фаза 2 — пройдена если:**
```bash
curl -sI https://HOST | grep -c "content-security-policy\|x-content-type\|x-frame"
# Должно быть: 3 (все три заголовка присутствуют)

curl -sI https://HOST | grep "set-cookie" | grep -c "HttpOnly"
# Должно быть: >= 1 (все auth cookie имеют HttpOnly)
```

**Фаза 4 — пройдена если:**
```bash
# Можешь показать документацию каждой проверки:
# - дата проверки
# - что проверялось
# - ожидаемый результат
# - реальный результат
# - ссылка на лог или скриншот DevTools
```

---

### Приложение B (`appendix-b.md`) — Лаборатория и паттерны

**Проверить содержимое. Если нет — добавить:**

- Готовый nginx-блок: TLS + security headers + rate limiting + запрет .env файлов
- Шпаргалка: curl-команды для проверки основных заголовков (одна на глазах)
- Рекомендация учебного приложения для lab: `DVWA` или `Juice Shop` в Docker

```bash
# Juice Shop — намеренно уязвимое приложение для lab
docker run --rm -p 3000:3000 bkimminich/juice-shop
# Открыть http://localhost:3000
# Все проверки глав 1-8 можно делать только здесь, в своём контейнере
```

---

## Формат изменений

- Дописывай в существующие файлы, не создавай новые
- Не меняй нумерацию разделов — добавляй подразделы (6.4а, 8.3а и т.д.)
- Все блоки кода с правильным языком: `python`, `bash`, `nginx`, `sql`, `ini`
- Примеры «плохо/хорошо» — всегда рядом, чтобы можно было сравнить

---

## Приоритет

1. Глава 6 (секреты) — самая слабая, замена списка на конкретные примеры
2. Технический fix: сменить ` ```text ` на правильные языки во всех главах
3. Главы 1, 4 (auth/CORS) — добавить ожидаемый вывод curl
4. Глава 7 (зависимости) — добавить пример вывода pip-audit/trivy
5. Глава 9 (проект) — добавить «как понять что фаза пройдена»

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-16-improve.md`*
*Проект: dev-ops / книга 16*
