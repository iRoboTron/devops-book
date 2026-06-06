# Глава 6: Dynamic Secrets — пароли от баз данных

## Что вы узнаете

- Что такое dynamic secrets и чем они лучше статических.
- Как настроить database engine для PostgreSQL.
- Как приложение получает временные credentials.
- Ротация и отзыв динамических учётных записей.

---

## 1. Проблема статических паролей

Статический пароль — это строка, которая живёт годами. Её вписали в `config.py` пять лет назад, и она до сих пор работает. Если она утечёт — злоумышленник получит доступ к БД до следующей ручной ротации.

Dynamic secrets решают эту проблему кардинально: **пароль не хранится вообще**. Приложение запрашивает credentials у Vault, получает временного пользователя БД с TTL в 1 час, работает, а после истечения lease пользователь удаляется.

| Характеристика | Статические пароли | Dynamic Secrets |
|---|---|---|
| Срок жизни | Месяцы / годы | Часы (TTL) |
| Хранение | В коде, .env, CI variables | В Vault, в памяти приложения |
| Утечка пароля | Компрометация навсегда | Компрометация на срок TTL |
| Ротация | Ручная (или скрипт) | Автоматическая при каждом запросе |
| Кто видит пароль | Все, у кого есть файл конфига | Только приложение, запросившее credentials |
| Уникальность | Один пароль на много приложений | Каждому запросу — свой пользователь |
| Revocation | Нужно менять везде | `vault lease revoke` — пользователь удалён |

```
Static:
  Пароль "P@ssw0rd" → config.py → 10 микросервисов
  Утечка одного → скомпрометированы все 10

Dynamic:
  App A → запрос → vault read database/creds/myapp-ro → user_A_3f2b (TTL: 1h)
  App B → запрос → vault read database/creds/myapp-ro → user_B_9a1c (TTL: 1h)
  Утечка user_A_3f2b → через час он мёртв, и это только SELECT-доступ
```

> **Dev vs Production:** в dev-стенде можно использовать статического vault_admin для всех операций. В production **каждое приложение** получает свою роль с минимальными правами (SELECT, INSERT, и т.д.) и коротким TTL.

---

## 2. Настройка Database Engine для PostgreSQL

Database engine — это secrets engine, который умеет создавать и удалять учётные записи в поддерживаемых базах данных. Vault подключается к БД как администратор и от его имени создаёт временных пользователей.

### 2.1. Включение engine

```bash
vault secrets enable database
```

После включения пути `database/` становятся доступны:

```
database/config/*       — конфигурации подключения к БД
database/roles/*        — роли (шаблоны пользователей)
database/creds/<role>   — получение credentials
database/static-roles/* — статические роли (опционально)
```

### 2.2. Конфигурация подключения

Vault должен знать, как подключиться к PostgreSQL. Для этого нужно создать конфигурацию с credentials администратора (пользователя, у которого есть `CREATEROLE`).

```bash
vault write database/config/myapp-postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/myapp?sslmode=disable" \
  allowed_roles="myapp-readonly,myapp-readwrite" \
  username="vault_admin" \
  password="VaultAdminPass"
```

Параметры:

| Параметр | Описание |
|---|---|
| `plugin_name` | Тип БД: `postgresql-database-plugin`, `mysql-database-plugin`, `mssql-database-plugin` и т.д. |
| `connection_url` | Строка подключения с `{{username}}` и `{{password}}` — макросы, которые Vault заменит на свои credentials |
| `allowed_roles` | Список ролей, которым разрешено использовать эту конфигурацию |
| `username` / `password` | Учётка администратора БД (vault_admin) |

> ☠️ **Осторожно:** строка подключения содержит имя пользователя и пароль **администратора БД**. Если кто-то получит доступ к этому конфигу через Vault, он сможет управлять пользователями в PostgreSQL. Ограничьте доступ к `database/config/*` политиками.

### 2.3. Ротация root-credentials

После настройки стоит немедленно сменить пароль администратора — так Vault станет единственным владельцем учётки:

```bash
vault write -force database/config/myapp-postgres/rotate-root
```

> ☠️ **Осторожно:** после `rotate-root` старый пароль vault_admin перестаёт работать. Даже вы не сможете подключиться к PostgreSQL с тем паролем, который указали в конфиге. Единственный способ получить новый пароль — прочитать его из Vault:

```bash
vault read database/config/myapp-postgres
```

После ротации Vault будет использовать сгенерированный пароль при каждом создании нового пользователя — макросы `{{password}}` в `connection_url` подставят актуальные credentials.

```
До rotate-root:      vault_admin / VaultAdminPass (известен вам)
После rotate-root:   vault_admin / 8f9a2b... (знает только Vault)
```

### 2.4. Проверка конфигурации

```bash
vault read database/config/myapp-postgres
```

```
Key                      Value
---                      -----
allowed_roles            [myapp-readonly myapp-readwrite]
connection_details       map[connection_url:... username:vault_admin]
plugin_name              postgresql-database-plugin
root_credentials_rotated true
```

---

## 3. Создание роли

Роль — это шаблон, по которому Vault создаёт пользователя в БД. Она содержит SQL-запросы для создания и удаления учётной записи.

### 3.1. Read-only роль

```bash
vault write database/roles/myapp-readonly \
  db_name=myapp-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl=1h \
  max_ttl=24h
```

| Параметр | Описание |
|---|---|
| `db_name` | Имя конфигурации подключения (из шага 2.2) |
| `creation_statements` | SQL для создания пользователя |
| `revocation_statements` | SQL для удаления пользователя |
| `default_ttl` | Время жизни credentials по умолчанию |
| `max_ttl` | Максимальное время жизни (при продлении) |

Макросы в `creation_statements`:

| Макрос | Что подставляет Vault |
|---|---|
| `{{name}}` | Уникальное имя пользователя (например, `v-token-myapp-3f2b1a`) |
| `{{password}}` | Сгенерированный пароль (64 символа, буквы + цифры) |
| `{{expiration}}` | ISO-дата истечения (например, `2026-06-04T16:00:00Z`) |

> ☠️ **Осторожно:** без `VALID UNTIL '{{expiration}}'` пользователь PostgreSQL будет жить вечно — если Vault по какой-то причине не выполнит revocation, учётная запись останется в БД. Всегда используйте `VALID UNTIL` как страховку.

### 3.2. Read-write роль

```bash
vault write database/roles/myapp-readwrite \
  db_name=myapp-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl=30m \
  max_ttl=2h
```

### 3.3. Роль для конкретной таблицы

```bash
vault write database/roles/myapp-orders-only \
  db_name=myapp-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT ON orders TO \"{{name}}\";" \
  revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl=10m
```

### 3.4. Проверка созданных ролей

```bash
# Список ролей
vault list database/roles

# Детали роли
vault read database/roles/myapp-readonly
```

---

## 4. Получение credentials

### 4.1. Команда получения

```bash
vault read database/creds/myapp-readonly
```

Ответ:

```
Key                Value
---                -----
lease_id           database/creds/myapp-readonly/MjRjNjg...
lease_duration     1h
lease_renewable    true
password           aB7dE3fG9hK2mN4pQ6rS8tU0vW2xY4z
username           v-token-myapp-readonly-3f2b1a9c
```

Каждый вызов `vault read database/creds/<role>` создаёт **нового пользователя** в PostgreSQL с **уникальным паролем**. Два последовательных вызова дадут двух разных пользователей.

### 4.2. Lease

Lease — это контракт: Vault обещает, что credentials будут жить `lease_duration`. После истечения Vault отзовёт lease и выполнит `revocation_statements` — пользователь будет удалён из БД.

```
  ┌─────┐
  │ T=0 │  vault read database/creds/myapp-readonly
  │     │  → user_3f2b создан
  └──┬──┘
     │ lease_duration = 1h
  ┌──▼──┐
  │T=30m│  vault lease renew lease_id
  │     │  → user_3f2b живёт ещё 1h
  └─────┘
     │
  ┌──▼──┐
  │T=1h │  Lease истёк (не продлён)
  │     │  → DROP ROLE user_3f2b (revocation)
  └─────┘
```

### 4.3. Продление lease

```bash
vault lease renew database/creds/myapp-readonly/MjRjNjg...
```

### 4.4. Отзыв lease (досрочное удаление пользователя)

```bash
vault lease revoke database/creds/myapp-readonly/MjRjNjg...
```

После отзыва пользователь немедленно удаляется из PostgreSQL. Подключения с этим пользователем будут разорваны при следующем обращении к БД.

### 4.5. Отзыв всех lease по префиксу

```bash
# Отозвать все credentials для роли myapp-readonly
vault lease revoke -prefix database/creds/myapp-readonly
```

Это удалит **всех** активных пользователей, созданных этой ролью. Полезно при ротации глобального пароля или при подозрении на утечку.

---

## 5. Интеграция с приложением

### 5.1. Python (hvac)

```python
import os
import hvac
import psycopg2

client = hvac.Client(
    url='http://vault:8200',
    token=os.environ['VAULT_TOKEN']
)

# Получаем временные credentials
creds = client.secrets.database.generate_credentials(
    name='myapp-readonly'
)

username = creds['data']['username']
password = creds['data']['password']

# Подключаемся к БД (учётка живёт max_ttl)
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    user=username,
    password=password,
    dbname='myapp'
)

# Работаем...
cursor = conn.cursor()
cursor.execute("SELECT * FROM orders LIMIT 10")
rows = cursor.fetchall()
```

### 5.2. Go

```go
import (
    "fmt"
    "os"
    vault "github.com/hashicorp/vault/api"
    "database/sql"
    _ "github.com/lib/pq"
)

client, _ := vault.NewClient(&vault.Config{
    Address: "http://vault:8200",
})
client.SetToken(os.Getenv("VAULT_TOKEN"))

secret, _ := client.Logical().Read("database/creds/myapp-readonly")

username := secret.Data["username"].(string)
password := secret.Data["password"].(string)

psqlInfo := fmt.Sprintf(
    "host=postgres port=5432 user=%s password=%s dbname=myapp sslmode=disable",
    username, password,
)
db, _ := sql.Open("postgres", psqlInfo)
defer db.Close()
```

### 5.3. Shell-скрипт (CI/CD)

```bash
#!/bin/sh
# Получаем credentials
eval $(vault read -format=json database/creds/myapp-readonly | jq -r '.data | to_entries | .[] | "export \(.key)=\(.value)"')

# Используем в команде
PGPASSWORD="$password" psql -h postgres -U "$username" -d myapp -c "SELECT count(*) FROM orders"
```

### 5.4. Важный паттерн: renew в фоне

Приложение должно фоново продлевать lease или перезапрашивать credentials до истечения TTL:

```python
import threading
import time

lease_duration = creds['lease_duration']  # в секундах
renew_before = lease_duration * 0.75     # продлеваем за 75% времени

def renew_lease():
    while True:
        time.sleep(renew_before)
        client.sys.renew_lease(
            lease_id=creds['lease_id'],
            increment=lease_duration
        )

threading.Thread(target=renew_lease, daemon=True).start()
```

> **Dev vs Production:** для dev-стенда TTL можно выставить в 24h, чтобы не заниматься продлением. В production TTL — 15-60 минут + обязательный background-renew. При падении приложения credentials сами истекут, не оставив мёртвых учёток.

---

## Типичные ошибки

- ❌ **vault_admin без `CREATEROLE`** — Vault не сможет создавать пользователей в PostgreSQL. Проверьте: `ALTER ROLE vault_admin WITH CREATEROLE;` Перед настройкой database engine убедитесь, что vault_admin имеет `CREATEROLE` и `LOGIN`.

- ❌ **Забыли `VALID UNTIL '{{expiration}}'`** — если revocation не сработает (Vault упал, network issue), пользователь останется в БД навсегда. `VALID UNTIL` — страховка: даже без revocation учётка умрёт сама.

- ❌ **Забыли `IF EXISTS` в revocation** — повторный отзыв того же lease упадёт с ошибкой, если пользователь уже удалён. `DROP ROLE IF EXISTS` — идемпотентность.

- ❌ **Включили `sslmode=disable` в production** — пароли передаются в открытом виде между Vault и PostgreSQL. Настройте TLS для обоих.

- ❌ **Один vault_admin для всех БД** — vault_admin должен быть только для целей Vault. Создайте отдельного администратора для database engine, не используйте `postgres` или существующего админа.

- ❌ **Не ограничили `max_ttl`** — если `max_ttl` не задан, роль может выпустить пользователя на неопределённо долгий срок (вплоть до `max_lease_ttl` engine). Всегда ставьте разумный `max_ttl`.

- ❌ **Приложение не продлевает lease** — если credentials истекут во время работы приложения, следующее обращение к БД упадёт с ошибкой аутентификации. Всегда ставьте background-renew или перезапрашивайте credentials.

---

## Чек-лист

- [ ] Я создал отдельную роль database engine для каждого приложения с минимальными SQL-привилегиями (read-only для чтения, конкретные таблицы для записи).
- [ ] Я выполнил `rotate-root`, и теперь vault_admin известен только Vault.
- [ ] Я проверил, что роль использует `VALID UNTIL '{{expiration}}'` и `IF EXISTS` в revocation.
- [ ] Приложение реализует renew lease или перезапрашивает credentials до истечения TTL.

---

## Попробуйте сами

1. **Настройте database engine для PostgreSQL.** Запустите PostgreSQL (локально или через Docker). Включите database engine. Создайте конфигурацию `myapp-postgres` с пользователем-vault_admin. Выполните `rotate-root`. Убедитесь, что старый пароль перестал работать, а Vault всё ещё может создавать пользователей.

2. **Создайте read-only и read-write роли.** Создайте `myapp-readonly` (SELECT) и `myapp-readwrite` (SELECT, INSERT, UPDATE, DELETE). Получите credentials для каждой роли через `vault read database/creds/<role>`. Подключитесь к PostgreSQL с полученными credentials: убедитесь, что read-only не может вставлять данные, а read-write — может.

3. **Проверьте revocation.** Получите credentials, подключитесь к БД — проверьте что connection работает. Выполните `vault lease revoke <lease_id>`. Повторите запрос из приложения — убедитесь, что connection упал с ошибкой аутентификации. Проверьте в `psql` что пользователь действительно удалён: `\du`.
