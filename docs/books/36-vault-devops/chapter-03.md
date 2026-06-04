# Глава 3: KV Secrets Engine — хранение статических секретов

## Что вы узнаете

- Полный CRUD для KV v2.
- Версионирование: история, восстановление, удаление.
- Metadata секрета.
- Организацию секретов по структуре путей.

---

## 1. Основные операции KV v2

KV v2 — основной engine для хранения статических секретов. Он поддерживает версионирование, soft-delete и metadata. Все операции выполняются через команду `vault kv`.

### 1.1. Запись секрета

Ключи и значения передаются парами `key="value"`. Значения с пробелами и спецсимволами — в кавычках.

```bash
vault kv put secret/myapp/database \
    host="prod-db.example.com" \
    port="5432" \
    username="appuser" \
    password="S3cr3tP@ss"
```

Также можно прочитать значения из stdin или файла:

```bash
# Из JSON-файла
vault kv put secret/myapp/database @creds.json
```

```json
{
  "host": "prod-db.example.com",
  "port": "5432",
  "username": "appuser",
  "password": "S3cr3tP@ss"
}
```

### 1.2. Чтение секрета

```bash
# Полный вывод
vault kv get secret/myapp/database
```

```
====== Data ======
Key         Value
host        prod-db.example.com
port        5432
username    appuser
password    S3cr3tP@ss

====== Metadata ======
Key              Value
---              -----
created_time     2026-06-04T10:00:00Z
version          2
deletion_time    n/a
destroyed        false
```

```bash
# Конкретная версия
vault kv get -version=2 secret/myapp/database

# Только одно поле
vault kv get -field=password secret/myapp/database
# S3cr3tP@ss

# В JSON (для парсинга)
vault kv get -format=json secret/myapp/database
```

```json
{
  "data": {
    "data": {
      "host": "prod-db.example.com",
      "password": "S3cr3tP@ss",
      "port": "5432",
      "username": "appuser"
    },
    "metadata": {
      "created_time": "2026-06-04T10:00:00Z",
      "version": 2
    }
  }
}
```

### 1.3. Частичное обновление (patch)

`vault kv put` **перезаписывает весь секрет**. Чтобы добавить или изменить одно поле, не трогая остальные, используйте `kv patch`:

```bash
# Добавить поле ssl_mode, остальные поля не меняются
vault kv patch secret/myapp/database ssl_mode="require"

# Результат: host, port, username, password остались, добавился ssl_mode
```

> ☠️ **Осторожно:** `vault kv put` перезаписывает секрет целиком. Если нужно изменить одно поле из десяти — используйте `patch`. Иначе потеряете значения, которые не указали в `put`.

### 1.4. Удаление (soft delete)

```bash
# Мягкое удаление — последняя версия помечается как deleted
vault kv delete secret/myapp/database

# Проверка — версия 3 помечена как удалённая
vault kv get secret/myapp/database
# Code: 404. Но метаданные живы
vault kv metadata get secret/myapp/database
```

### 1.5. Восстановление (undelete)

```bash
# Вернуть версию 3 к жизни
vault kv undelete -versions=3 secret/myapp/database

# Проверка
vault kv get secret/myapp/database
```

### 1.6. Полное уничтожение (destroy)

```bash
# Версия 1 и 2 уничтожены навсегда — данные недоступны
vault kv destroy -versions=1,2 secret/myapp/database

# Проверка
vault kv get -version=1 secret/myapp/database
# Code: 404. Errors: key doesn't support this operations
vault kv metadata get secret/myapp/database
# Destroyed: true для версий 1,2
```

### 1.7. Удаление метаданных (metadata delete)

> ☠️ **Осторожно:** `vault kv metadata delete secret/myapp/database` удаляет все версии и метаданные **навсегда**. Восстановление невозможно. Это как `rm -rf` — без корзины.

```bash
# Полное, фатальное удаление
vault kv metadata delete secret/myapp/database
# Всё. Путь больше не существует.
```

```
Схема уровней удаления:

                        ┌──────────────────────┐
                        │   Секрет жив (write)  │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Soft delete (delete) │ ◄── можно undelete
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Destroy (destroy)    │ ◄── данные стёрты,
                        │  версия = номер+пусто │     metadata живы
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  metadata delete      │ ◄── пути нет вообще
                        │  (metadata delete)    │     ничего не осталось
                        └──────────────────────┘
```

> **Dev vs Production:** в dev вам вряд ли понадобится `metadata delete` — разве что для отладки. В production эту операцию обычно **запрещают политиками**, чтобы случайно не удалить production credentials.

---

## 2. Версионирование

KV v2 хранит до N последних версий секрета (по умолчанию 10). Можно смотреть историю, восстанавливать старые версии и контролировать `max-versions`.

### Просмотр метаданных

```bash
vault kv metadata get secret/myapp/database
```

```
====== Metadata ======
Key              Value
---              -----
created_time     2026-06-04T09:00:00Z
current_version  5
max_versions     10
oldest_version   1

====== Version 1 ======
Key              Value
---              -----
created_time     2026-06-04T09:00:00Z
deletion_time    n/a
destroyed        false

====== Version 2 ======
Key              Value
---              -----
created_time     2026-06-04T10:00:00Z
deletion_time    n/a
destroyed        false
...
```

### Настройка max-versions

```bash
# Ограничить до 5 версий
vault kv metadata put -max-versions=5 secret/myapp/database

# После 5-й записи — самая старая версия удаляется автоматически
vault kv put secret/myapp/database host="new-host"
# Старая версия 1 ушла, теперь версии 2-6
```

### CAS (Check-And-Set)

CAS гарантирует, что запись произойдёт только если текущая версия совпадает с ожидаемой. Защита от race condition.

```bash
# Включить CAS на уровне metadata
vault kv metadata put -cas-required=true secret/myapp/database

# Запись без номера версии — ошибка
vault kv put secret/myapp/database host="x"  # ошибка!

# Запись с указанием версии
vault kv put -cas=5 secret/myapp/database host="x"
# Ок, только если текущая версия == 5
```

```
CAS в действии:

Процесс A: читает версию 5
Процесс B: читает версию 5
Процесс A: пишет с cas=5  ──► OK, версия стала 6
Процесс B: пишет с cas=5  ──► FAIL, версия уже 6
```

### Когда пригодится версионирование

- **Откат после ошибки:** обновили секрет с неверным паролем → `vault kv undelete -versions=3` → всё снова работает.
- **Аудит:** `vault kv metadata get` показывает кто и когда менял (через audit log).
- **История изменений:** можно посмотреть любой снимок секрета по версии.

> **Dev vs Production:** в dev `max-versions=5` достаточно. В production настройте разумное значение — слишком много версий = рост хранилища. Для секретов с частой сменой (пароли ротации) — 10–20 версий. Для статичных конфигов — 3–5.

---

## 3. Организация секретов

Структура путей — это единственный способ группировки секретов в Vault. Нет папок, нет тегов, нет ярлыков. Только путь. Поэтому к выбору структуры нужно подойти осознанно.

### Рекомендуемая структура

```
secret/
├── production/
│   ├── myapp/
│   │   ├── database
│   │   ├── api-key
│   │   └── redis
│   └── monitoring/
│       └── grafana-admin
├── staging/
│   └── myapp/
│       ├── database
│       └── api-key
├── shared/
│   ├── tls/
│   │   └── wildcard-cert
│   └── mailgun/
│       └── api-key
└── infrastructure/
    ├── consul-token
    └── nomad-token
```

**Принципы:**

1. **Окружение → Сервис → Имя секрета** — `secret/{env}/{service}/{secret-name}`.
2. **Общие секреты** — `secret/shared/...` для TLS-сертификатов, общих API-ключей.
3. **Инфраструктурные** — `secret/infrastructure/...` для токенов Consul, Nomad.

### Как это помогает с политиками

Структура путей напрямую диктует политики доступа. Правильно построенный путь = тонкая настройка доступа без дублирования.

```hcl
# Только production, только myapp
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}

# staging — только read, никаких write
path "secret/data/staging/*" {
  capabilities = ["read"]
}

# dev-команды могут писать в staging
path "secret/data/staging/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

```
Структура путей → Политики:

secret/production/myapp/*   ──►   team-myapp-prod (read only)
secret/staging/myapp/*      ──►   team-myapp-dev  (read/write)
secret/production/*         ──►   platform-admins (full access)
```

### Flat vs вложенная структура

| Flat | Вложенная |
|------|-----------|
| `secret/prod-db` | `secret/production/myapp/database` |
| `secret/staging-db` | `secret/staging/myapp/database` |
| Легко запутаться | Понятная иерархия |
| Политики — на каждый секрет | Политики — на маску пути |
| Не масштабируется | Масштабируется |

> **Dev vs Production:** структура должна быть одинаковой. Разница только в содержимом и политиках: в dev — полный доступ, в production — строгий read-only для приложений.

---

## 4. Работа из скриптов

KV v2 отлично интегрируется с bash-скриптами, CI/CD и инструментами вроде jq.

### Получение одного поля

```bash
DB_PASSWORD=$(vault kv get -field=password secret/production/myapp/database)
psql "host=prod-db port=5432 user=appuser password=$DB_PASSWORD"
```

### Экспорт всего секрета в переменные окружения

```bash
eval "$(vault kv get -format=json secret/production/myapp/database | \
  jq -r '.data.data | to_entries[] | "export \(.key)=\(.value)"')"
```

После выполнения:
```bash
echo $DB_HOST
# prod-db.example.com
```

### Bulk-экспорт нескольких секретов

```bash
#!/bin/bash
# load-vault-env.sh — экспорт секретов проекта

PROJECT=$1
ENV=${2:-production}

vault kv get -format=json "secret/${ENV}/${PROJECT}/database" | \
  jq -r '.data.data | to_entries[] | "export \(.key)=\(.value)"'
```

Использование:
```bash
eval "$(./load-vault-env.sh myapp staging)"
```

### Запись секрета из скрипта

```bash
# Сгенерировать пароль и записать
NEW_PASS=$(openssl rand -base64 32)
vault kv patch secret/myapp/database password="$NEW_PASS"
```

> ☠️ **Осторожно:** запись секретов напрямую в командной строке оставляет их в shell history (`.bash_history`, `~/.zsh_history`). Всегда используйте файл или переменную:

```bash
# Безопасный способ
vault kv put secret/myapp/database @creds.json && shred creds.json
```

```bash
# Ещё безопаснее — через pipe, нет файла на диске
echo '{"password":"super-secret"}' | vault kv put secret/myapp/database -
```

### CI/CD интеграция

```yaml
# .gitlab-ci.yml (пример)
variables:
  VAULT_ADDR: https://vault.example.com:8200

job:
  script:
    - apk add vault jq
    - export VAULT_TOKEN=$(vault login -method=approle -token-only role-id=$ROLE_ID secret-id=$SECRET_ID)
    - export DB_URL=$(vault kv get -field=url secret/production/myapp/database)
    - migrate -database "$DB_URL" up
```

> **Dev vs Production:** в dev скрипты используют root-токен (`VAULT_TOKEN=root`). В production — AppRole или Kubernetes Service Account. Никогда не хардкодьте токены в скриптах.

---

## Типичные ошибки

- ❌ **`kv put` перезаписывает всё** — если у вас секрет с 10 полями, а вы написали `vault kv put secret/app key=val`, 9 полей пропадут. Используйте `vault kv patch` для частичного обновления.
- ❌ **Пароль остался в shell history** — команда `vault kv put secret/app password="supersecret"` попала в `.bash_history`. Используйте `@файл` или pipe из переменной.
- ❌ **Забыли про `/data` в API** — при работе через `curl` пишите `/v1/secret/data/...`. Без `/data/` — 404 или работа с v1.
- ❌ **Секрет «исчез» — на самом деле удалённая версия** — `vault kv get` показывает последнюю живую версию. Если версия удалена, команда вернёт 404. Проверьте `vault kv metadata get` — версия будет помечена как `deletion_time: ...`.
- ❌ **Слишком много версий** — каждая версия занимает место в storage. Если секрет меняется каждую минуту, `max-versions=10` приведёт к быстрому росту хранилища. Настройте разумный лимит.

---

## Чек-лист

- [ ] Я выполнил полный CRUD: `put`, `get`, `patch`, `delete`, `undelete`, `destroy`.
- [ ] Я понимаю разницу между мягким удалением (`delete`), уничтожением (`destroy`) и удалением метаданных (`metadata delete`).
- [ ] Я настроил `max-versions` и знаю зачем это нужно.
- [ ] Я организовал секреты по структуре `{env}/{service}/{name}` и понимаю как это влияет на политики.

---

## Попробуйте сами

1. **CRUD с версионированием.** Запишите секрет с полями `host`, `port`, `password`. Прочитайте. Измените `password` через `patch`. Прочитайте — убедитесь что остальные поля целы. Удалите через `delete`. Прочитайте — 404. Выполните `undelete`. Прочитайте — секрет снова жив. Выполните `destroy` — версия уничтожена.
2. **Настройте max-versions.** Создайте секрет, поставьте `max-versions=3`. Запишите 4 разные версии (просто меняйте одно поле). Проверьте метаданные — версии 4,3,2 живы, версии 1 нет.
3. **Скрипт загрузки в окружение.** Напишите bash-скрипт, который получает секрет из Vault в формате JSON и экспортирует все ключи как переменные окружения (используйте `jq`). Затем добавьте `vault kv patch` для обновления одного поля. Проверьте на dev-сервере.
