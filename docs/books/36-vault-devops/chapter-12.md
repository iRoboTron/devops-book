# Глава 12: Аудит, диагностика и типичные сценарии

## Что вы узнаете

- Как включить audit log и что в нём хранится.
- Как диагностировать 403 через audit log.
- Типичные сценарии: ротация, отзыв, onboarding нового сервиса.

---

## 1. Audit Log

Audit log — это журнал всех запросов к Vault. Каждый запрос логируется с полной информацией: кто, когда, что запросил и какой получил ответ.

### 1.1. Включение audit log

```bash
# Файловый audit backend (основной)
vault audit enable file \
  file_path=/vault/logs/audit.log

# Syslog audit backend (резервный)
vault audit enable syslog \
  tag=vault \
  facility=AUTH

# Список включённых audit backends
vault audit list

# Отключение audit backend
vault audit disable file/
```

| Параметр | Описание |
|----------|----------|
| `file_path` | Путь к файлу audit log |
| `log_raw` | Логировать raw-запрос (до обработки политиками) |
| `hmac_accessor` | Маскировать token accessor (SHA256-HMAC) |
| `mode` | Права на файл (по умолчанию `0600`) |
| `format` | Формат: `json` (по умолчанию) или `jsonx` |

### 1.2. Структура audit log

```json
{
  "time": "2026-01-15T10:30:00.000000000Z",
  "type": "response",
  "auth": {
    "token_type": "service",
    "policies": ["default", "myapp-policy"],
    "display_name": "myapp",
    "metadata": {
      "role": "myapp",
      "service_account": "myapp",
      "service_account_namespace": "production"
    }
  },
  "request": {
    "id": "abc-123-def",
    "operation": "read",
    "path": "secret/data/production/myapp/database",
    "data": {},
    "remote_address": "10.0.0.42:54321"
  },
  "response": {
    "data": {
      "data": {
        "host": "db.internal",
        "password": "hmac-sha256:abc123..."
      }
    }
  }
}
```

| Поле | Описание |
|------|----------|
| `time` | Время запроса (UTC, RFC3339) |
| `type` | `request` (входящий запрос) или `response` (ответ) |
| `auth.token_type` | `service`, `batch` или `default` |
| `auth.policies` | Список политик, применённых к токену |
| `request.operation` | `read`, `write`, `list`, `delete`, `update` |
| `request.path` | Путь запроса (включая mount path) |
| `response.data` | Данные ответа (значения замаскированы HMAC) |
| `response.error` | Ошибка (если запрос завершился ошибкой) |

### 1.3. HMAC маскировка

По умолчанию Vault маскирует чувствительные данные в audit log через HMAC-SHA256:

```json
{
  "response": {
    "data": {
      "password": "hmac-sha256:abcdef1234567890..."
    }
  }
}
```

```bash
# Отключить HMAC (для отладки — включать на время расследования)
vault audit enable file \
  file_path=/vault/logs/audit-debug.log \
  hmac_accessor=false

# Или для конкретного backend
vault audit tune file/ \
  hmac_accessor=false
```

> ☠️ **Осторожно:** отключение HMAC (`hmac_accessor=false`) записывает реальные секреты в audit log. Включайте только на время расследования, отключайте сразу после. Audit log в этом режиме — критический security risk.

### 1.4. Анализ audit log с jq

```bash
# Найти все обращения к конкретному секрету
cat audit.log | jq \
  'select(.request.path == "secret/data/production/myapp/database")'

# Найти все ошибки (403, 400, 500)
cat audit.log | jq \
  'select(.response.error != null)'

# Найти 403 Forbidden
cat audit.log | jq \
  'select(.response.error != null) | {time: .time, path: .request.path, user: .auth.display_name, error: .response.error}'

# Найти кто читал конкретный секрет
cat audit.log | jq \
  'select(.request.path == "secret/data/production/myapp/api-key" and .type == "response") | {time: .time, user: .auth.display_name, policies: .auth.policies}'

# Статистика по типам операций
cat audit.log | jq -r \
  '.request.operation' | sort | uniq -c | sort -rn

# Найти запросы от конкретного токена
cat audit.log | jq \
  'select(.auth.token_type == "batch" and .response.error != null)'
```

### 1.5. Syslog audit

```bash
# Включение syslog
vault audit enable syslog \
  tag=vault \
  facility=AUTH \
  hmac_accessor=true

# Просмотр syslog audit
journalctl -t vault -f
```

### 1.6. Audit log — важные замечания

> ☠️ **Осторожно:** если Vault не может писать audit log (диск полон, файловая система недоступна) — **он перестаёт обрабатывать запросы**. Все операции чтения/записи блокируются до тех пор, пока audit log снова не станет доступен.

```bash
# Рекомендация: минимум 2 audit backend
# 1. file — для истории (ротация через logrotate)
vault audit enable file file_path=/vault/logs/audit.log
# 2. syslog — резервный (на другой сервер через rsyslog)
vault audit enable syslog tag=vault facility=AUTH
```

```text
Схема работы audit log:

      Запрос от клиента
           │
           ▼
   ┌───────────────┐
   │  Vault Core    │
   └───────┬───────┘
           │
    ┌──────▼───────┐
    │ Audit Broker  │ ← если один backend не отвечает,
    └──┬────────┬──┘   запрос всё равно идёт
       │        │
  ┌────▼──┐ ┌──▼────┐
  │ file  │ │ syslog│
  │audit  │ │ audit │
  └───────┘ └───────┘

    Если оба backend недоступны → Vault BLOCKING
```

> **Dev vs Production:** в dev достаточно одного `file` audit backend. В production — минимум два (file + syslog), настроена ротация audit.log через logrotate, аудит в централизованную систему (ELK, Loki, Splunk).

---

## 2. Onboarding нового сервиса

Типовой процесс подключения нового приложения к Vault.

### 2.1. 4 команды для подключения

```bash
# Шаг 1: Создать секрет
vault kv put secret/production/newservice/database \
  host="db.internal" \
  password="$(pwgen 32 1)" \
  username="newservice"

# Шаг 2: Создать политику
vault policy write newservice-policy - <<'EOF'
path "secret/data/production/newservice/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/production/newservice/*" {
  capabilities = ["list"]
}
EOF

# Шаг 3: Создать AppRole
vault write auth/approle/role/newservice \
  token_policies="newservice-policy" \
  secret_id_ttl=10m \
  secret_id_num_uses=1 \
  token_ttl=1h \
  token_max_ttl=24h

# Шаг 4: Получить Role ID и отдать разработчикам
vault read -field=role_id auth/approle/role/newservice/role-id
```

```text
Onboarding pipeline:

   Разработчик       ───→  Администратор Vault
   просит доступ              │
                              ├── 1. vault kv put secret/... 
                              ├── 2. vault policy write <policy>
                              ├── 3. vault write auth/approle/role/...
                              └── 4. vault read ...role-id
                                   │
                                   ▼
                            Разработчик
                            получает role_id
```

### 2.2. AppRole параметры

| Параметр | Описание | Dev | Production |
|----------|----------|-----|------------|
| `secret_id_ttl` | Время жизни Secret ID | `0` (бесконечно) | `10m` |
| `secret_id_num_uses` | Сколько раз можно использовать Secret ID | `0` (без лимита) | `1` |
| `token_ttl` | Время жизни Vault token | `24h` | `1h` |
| `token_max_ttl` | Максимальное время жизни | `72h` | `24h` |
| `token_policies` | Политики для токена | одна политика | минимум, read-only |
| `bind_secret_id` | Обязателен ли Secret ID | `true` | `true` |

> **Dev vs Production:** в dev можно использовать `secret_id_ttl=0` и `secret_id_num_uses=0` для упрощения. В production — `secret_id_ttl=10m`, `secret_id_num_uses=1` и короткий `token_ttl=1h`.

### 2.3. AppRole login из приложения

```bash
# В приложении
ROLE_ID=$(cat /etc/vault/role-id)
SECRET_ID=$(vault write -field=secret_id \
  auth/approle/role/newservice/secret-id)

# Login
vault write auth/approle/login \
  role_id="$ROLE_ID" \
  secret_id="$SECRET_ID"

# → Получаем Vault token
```

---

## 3. Ротация пароля

### 3.1. Ручная ротация

```bash
# Изменить пароль
vault kv patch secret/production/myapp/database \
  password="NewP@ssw0rd2026"

# Проверить новую версию
vault kv get secret/production/myapp/database

# История версий
vault kv metadata get secret/production/myapp/database
```

### 3.2. Vault Agent — автоматическое обновление

Если приложение использует Vault Agent, он автоматически обновит секреты:

```hcl
# agent-config.hcl
vault {
  address = "http://vault:8200"
}

template {
  source      = "/etc/vault/templates/database.ctmpl"
  destination = "/etc/config/database.env"
}
```

```text
При изменении секрета в Vault:

1. Админ: vault kv patch secret/... password="..."
                  │
                  ▼
2. Vault Agent обнаруживает изменение (watch)
                  │
                  ▼
3. Agent перечитывает секрет
                  │
                  ▼
4. Agent рендерит новый шаблон
                  │
                  ▼
5. Файл /etc/config/database.env обновлён
6. Agent отправляет SIGHUP приложению (если настроено)
```

### 3.3. Vault Secrets Operator — синхронизация K8s Secret

```bash
# В Vault:
vault kv patch secret/production/myapp/database \
  password="RotatedPass123"

# VSO обновит K8s Secret автоматически (через refreshAfter)
```

### 3.4. Плановая ротация

```text
Процесс ротации:

1. Создать новый пароль → vault kv patch
2. Перезапустить приложения (с новым паролем)
3. Убедиться, что старый пароль не используется
4. Удалить старый пароль → vault kv destroy (версия)
5. Обновить документацию / wiki
6. Записать в audit: кто, когда, зачем
```

> **Dev vs Production:** в dev можно ротировать когда угодно. В production — только через change management, с уведомлением команд, в окно изменений.

---

## 4. Отзыв доступа

### 4.1. Отзыв токена

```bash
# Отозвать конкретный токен
vault token revoke -accessor ACCESSOR

# Отозвать токен по ID (если известен)
vault token revoke hvs.xxx...

# Отозвать все токены по пути создания
vault token revoke -path auth/approle/role/myapp

# Отозвать все токены по политике
vault token revoke -policy myapp-policy
```

### 4.2. Каскадный отзыв

```text
При отзыве токена Vault также отзывает:

  Parent Token
      │
      ├── Child Token 1
      ├── Child Token 2
      └── Child Token 3
              │
              ├── Grandchild Token 1
              └── Grandchild Token 2

  Отзыв Parent → все дочерние токены тоже отозваны
```

### 4.3. Отзыв AppRole Secret ID

```bash
# Найти все Secret ID для роли
vault list auth/approle/role/myapp/secret-id

# Отозвать конкретный Secret ID
vault write auth/approle/role/myapp/secret-id-accessor/lookup \
  secret_id_accessor=ACCESSOR

# После отзыва — все токены, созданные с этим Secret ID,
# будут отозваны (если ещё не истекли)
```

### 4.4. Прекращение доступа сервиса

```bash
# 1. Отозвать все токены сервиса
vault token revoke -path auth/approle/role/old-service

# 2. Удалить AppRole
vault delete auth/approle/role/old-service

# 3. Удалить политику
vault policy delete old-service-policy

# 4. Удалить секреты
vault kv metadata delete secret/production/old-service

# 5. Проверить в audit log, что токены не используются
cat audit.log | jq \
  'select(.auth.policies | index("old-service-policy"))' | tail -5
```

---

## 5. Диагностика 403

### 5.1. Пошаговая диагностика

```bash
# Шаг 1: Проверить токен
vault token lookup TOKEN
# Ошибка: "bad token" — токен истёк или невалиден

# Шаг 2: Проверить политики токена
vault token lookup TOKEN | grep policies
# token_policies    ["default", "myapp-policy"]

# Шаг 3: Прочитать политику
vault policy read myapp-policy

# Шаг 4: Проверить capabilities для конкретного пути
vault token capabilities TOKEN \
  secret/data/production/myapp/database
# → [read, list]  — OK
# → [deny]       — нет прав
# → []           — путь не существует или нет доступа

# Шаг 5: Поискать в audit log
cat audit.log | jq \
  'select(.request.path == "secret/data/production/myapp/database" and .response.error != null)'

# Шаг 6: Проверить KV v2 — путь должен начинаться с secret/data/
vault token capabilities TOKEN \
  secret/production/myapp/database
# → [deny]  — потому что нужно secret/data/... а не secret/...
```

### 5.2. Все причины 403

| Симптом | Диагноз | Решение |
|---------|---------|---------|
| `permission denied` | Нет политики на путь | Добавить `path "secret/data/..." { capabilities = ["read"] }` |
| `permission denied` (KV v2) | Путь без `/data/` | Используй `secret/data/myapp/...`, а не `secret/myapp/...` |
| `bad token` | Токен истёк | Renew token или получить новый |
| `no handler` | Путь не существует | Проверить mount path (`vault secrets list`) |
| `unsupported path` | Опечатка в пути | Проверить path в политике |
| `permission denied` | `deny` раньше чем `read` | Порядок правил в политике имеет значение |
| `token not found` | Токен отозван | Получить новый токен |

### 5.3. Иерархия политик (порядок имеет значение)

```hcl
# НЕПРАВИЛЬНО: deny перекрывает всё
path "*" {
  capabilities = ["deny"]
}
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}

# ПРАВИЛЬНО: deny после разрешающих правил
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}
path "*" {
  capabilities = ["deny"]
}
```

### 5.4. Проверка политики через test

```bash
# Vault CLI может симулировать проверку политики
vault policy test -policy myapp-policy \
  -path "secret/data/production/myapp/database"
# → read, list
```

### 5.5. Типовой сценарий расследования

```text
Сценарий: разраб говорит «Vault выдаёт 403»

1. vault token lookup <token>
   → Токен активен, policies: ["default", "myapp-policy"]

2. vault policy read myapp-policy
   → path "secret/production/myapp/*" { capabilities = ["read"] }

3. vault token capabilities <token> secret/production/myapp/database
   → [deny]

   Диагноз: отсутствует /data/ в пути.
   Политика на "secret/..." а должен быть "secret/data/..."

4. Исправление: 
   path "secret/data/production/myapp/*" { capabilities = ["read"] }
```

---

## Типичные ошибки

- ❌ **Audit log не включён** — при инциденте невозможно определить, кто, когда и что делал. Audit log должен быть включён с первого дня.

- ❌ **`token capabilities` проверяет только один путь** — разработчик проверяет `token capabilities` для `secret/data/myapp/database`, получает `read`, но приложение делает `list` на `secret/metadata/myapp/` — и падает с 403. Проверяйте все пути и операции, которые использует приложение.

- ❌ **Политика на `secret/myapp/` вместо `secret/data/myapp/`** — KV v2 требует `secret/data/...` для чтения и `secret/metadata/...` для listing. Это самая частая причина 403. Если видишь `deny` на существующем пути — проверь, есть ли `/data/` в пути политики.

- ❌ **Audit backend единственный, и он упал** — при недоступности audit backend Vault блокирует все запросы. Всегда настраивайте минимум 2 audit backend (file + syslog).

- ❌ **HMAC accessor не отключают при расследовании** — если нужно узнать, какой именно токен обращался к секрету, а HMAC включён — token accessor замаскирован и бесполезен. На время расследования включите новый audit backend с `hmac_accessor=false`, а после — отключите.

- ❌ **Не проверяют порядок правил в политике** — `deny` на `*` раньше read-правил блокирует все запросы. Политики обрабатываются сверху вниз: первое совпадение побеждает.

---

## Чек-лист

- [ ] Audit log включён (минимум 1 backend, в production — 2+). Audit log ротируется (logrotate) и отправляется в централизованную систему (ELK, Loki, Splunk). Права на файл audit.log — 0600.
- [ ] Для каждого сервиса создана отдельная политика с минимальными правами (read на конкретный путь, deny на всё остальное). Токены сервисов имеют TTL и renewable.
- [ ] Onboarding нового сервиса автоматизирован (скрипт или CI/CD pipeline). Включает: создание секрета, политики, AppRole, передачу role_id разработчикам.
- [ ] При отзыве доступа (увольнение, выключение сервиса) выполнены все шаги: отзыв токенов, удаление AppRole, удаление политики, удаление секретов. Проверено по audit log, что токены больше не используются.

---

## Попробуйте сами

1. **Включите audit log и проанализируйте.** Включите файловый audit backend. Выполните несколько операций: `vault kv put`, `vault kv get` (с разными токенами), `vault token create`. Прочитайте audit log через `jq`. Найдите: запросы с ошибкой, обращения к конкретному пути, статистику по типам операций. Попробуйте отключить HMAC (`hmac_accessor=false`) и увидеть реальные значения секретов в логе.

2. **Проведите onboarding нового сервиса.** Создайте секрет `secret/production/payments/database` с полями `host`, `password`, `username`. Напишите политику `payments-policy` с read-доступом к `secret/data/production/payments/*`. Создайте AppRole `payments` с этой политикой. Получите role_id. Выполните `vault write auth/approle/login role_id=... secret_id=...` и получите Vault token. Проверьте, что токен может прочитать секрет, но не может записать.

3. **Диагностируйте 403.** Создайте политику с ошибкой: `path "secret/production/payments/*" { capabilities = ["read"] }` (без `/data/`). Получите токен с этой политикой. Попробуйте прочитать `secret/data/production/payments/database` — получите 403. Используйте `vault token capabilities` для диагностики. Исправьте политику, добавив `/data/` в путь. Убедитесь, что 403 исчез.
