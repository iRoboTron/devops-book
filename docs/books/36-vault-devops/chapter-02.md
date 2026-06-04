# Глава 2: Основные концепции — paths, engines, tokens, leases

## Что вы узнаете

- Файловую систему Vault: path и mount point.
- Типы secrets engines и зачем их несколько.
- Что такое токен, TTL, lease.
- Иерархию токенов и отзыв.

---

## 1. Vault как файловая система

Всё в Vault адресуется путями. Если вы умеете работать с файловой системой — вы уже на 50 % понимаете Vault.

```
/
├── secret/                    # Secrets engine: KV v2 (статичные секреты)
│   ├── production/
│   │   └── myapp/database
│   └── staging/
│       └── myapp/database
├── database/                  # Secrets engine: database (динамические пароли)
├── pki/                       # Secrets engine: PKI (сертификаты)
├── transit/                   # Secrets engine: Transit (шифрование)
├── aws/                       # Secrets engine: AWS (IAM credentials)
├── cubbyhole/                 # Личное хранилище токена
├── identity/                  # Identity & groups
├── auth/                      # Auth methods
│   ├── token/
│   ├── approle/
│   ├── userpass/
│   └── ldap/
└── sys/                       # System
    ├── health
    ├── policy/
    ├── audit/
    ├── leases/
    ├── seal
    ├── raft/
    └── init
```

Корень `/` — это **mount point**. Каждый подключенный secrets engine или auth method получает свой путь. Пути уникальны: нельзя повесить KV на `/database` если там уже висит database engine.

```bash
# Посмотреть все подключенные secrets engines
vault secrets list
```

```bash
# Посмотреть все auth methods
vault auth list
```

Вывод `vault secrets list`:

| Path | Type | Accessor | Description |
|------|------|----------|-------------|
| `cubbyhole/` | cubbyhole | — | per-token private storage |
| `secret/` | kv | — | key/value secrets |
| `identity/` | identity | — | identity store |
| `sys/` | system | — | system endpoints |

> **Dev vs Production:** в dev включены только KV v2 (secret/), cubbyhole, identity и sys. В production вы сами подключаете нужные engines: `vault secrets enable database` добавит путь `database/`.

**Mount point** — это имя пути, по которому engine доступен. По умолчанию совпадает с типом engine (`secret/` для kv, `database/` для database), но можно задать любое:

```bash
# Кастомный mount point
vault secrets enable -path=team-a/secrets kv-v2
vault secrets list | grep team-a
```

Это позволяет разграничить доступ: политика для `team-a/secrets/*` не затронет `secret/*`.

---

## 2. Secrets Engines

Secrets engine — это компонент Vault, который умеет хранить, генерировать или шифровать секреты. Каждый engine решает свою задачу.

| Engine | Тип секретов | Static/Dynamic | Когда использовать |
|--------|-------------|----------------|-------------------|
| **KV v2** | произвольные key-value | Static | пароли, токены, конфиги, .env-файлы |
| **database** | credentials к БД | Dynamic | доступ к PostgreSQL, MySQL, MongoDB, MSSQL |
| **PKI** | TLS-сертификаты | Dynamic | внутренние CA, выпуск сертификатов на лету |
| **Transit** | шифрование без хранения | — | encrypt/decrypt как сервис, подпись данных |
| **AWS** | AWS access keys | Dynamic | временные IAM credentials для EC2/S3 |
| **Azure** | Azure service principals | Dynamic | временные credentials для Azure |
| **Consul** | Consul API tokens | Dynamic | доступ к Consul |
| **TOTP** | одноразовые коды | Dynamic | MFA токены |
| **AD / LDAP** | пароли к AD | Dynamic | ротация паролей в Active Directory |

**Static** — секрет хранится в Vault, его значение известно заранее (пароль, API-ключ).

**Dynamic** — Vault генерирует секрет по запросу с заданным TTL. Секрет уникален, временен и отзываем.

```
Static ───────────► Vault ──────► Приложение
    (пароль живёт вечно)

Dynamic ─────────► Vault ──────► Приложение
    (пароль живёт 1 час, сам истекает)
```

> **Dev vs Production:** в dev обычно хватает KV. В production почти всегда используют database + PKI для автоматической генерации и ротации credentials.

---

## 3. KV v1 vs KV v2

| Характеристика | KV v1 | KV v2 |
|----------------|-------|-------|
| Версионирование | Нет | Да (по умолчанию 10 версий) |
| Soft delete | Нет | `vault kv undelete` |
| Hard delete | Есть | `vault kv destroy`, `metadata delete` |
| Metadata | Нет | created_time, version, deletion_time |
| Путь API | `secret/...` | `secret/data/...` |
| Путь CLI | `secret/...` | `secret/...` (CLI сам делает прокси) |
| CAS (check-and-set) | Нет | Да |
| Рекомендация | Не используйте | Всегда |

```bash
# KV v2: путь данных идёт через data/
# CLI скрывает это, но если дёргать API напрямую:
curl $VAULT_ADDR/v1/secret/data/myapp/database  # v2 — data/
curl $VAULT_ADDR/v1/secret/myapp/database        # v1 — напрямую

# Проверить какая версия:
vault secrets list -detailed | grep secret/
```

**Почему KV v2 по умолчанию:** начиная с Vault 1.0 `vault secrets enable kv` включает именно KV v2. Если нужна v1 — используйте `vault secrets enable kv-v1`.

```bash
# Явно включить KV v1 (не рекомендуется)
vault secrets enable -path=kv-v1 kv-v1
```

![mermaid-seq](/assets/36-vault-devops/kv-versions.png)
```
Последовательность версий в KV v2:

write v1 ──► write v2 ──► delete v3 ──► undelete v3
   │            │             │              │
   ▼            ▼             ▼              ▼
┌──────┐   ┌──────┐     ┌──────┐        ┌──────┐
│ v1   │   │ v2   │     │ v3   │        │ v3   │
│ live │   │ live │     │ del  │        │ live │
└──────┘   └──────┘     └──────┘        └──────┘

destroy v1 ──► v1 навсегда удалён
```

> **Dev vs Production:** и там, и там — KV v2. Разница только в количестве хранимых версий: в dev часто хватает 3–5, в production можно увеличить до 10–20 через `max-versions`.

---

## 4. Cubbyhole — личное хранилище токена

**Cubbyhole** — это secrets engine, который привязан к текущему токену. Каждый токен видит **только свой** cubbyhole. Другие токены (даже root) не могут прочитать чужой cubbyhole.

```
Токен A ──► cubbyhole/ ──► видит только /cubbyhole/A
Токен B ──► cubbyhole/ ──► видит только /cubbyhole/B
Root     ──► cubbyhole/ ──► видит только /cubbyhole/root
```

```bash
# Записать секрет в cubbyhole
vault write cubbyhole/tmp/build-key value="abc123"
vault read cubbyhole/tmp/build-key

# Попробовать из другого токена — ошибка
vault token create -policy=default -ttl=10m
# (переключиться на новый токен)
vault read cubbyhole/tmp/build-key
# Code: 403. Permission denied
```

**Когда пригодится:** передача временных ключей внутри одной сессии, хранение промежуточных данных в пайплайнах CI/CD.

> ☠️ **Осторожно:** при отзыве токена cubbyhole уничтожается **безвозвратно**. Не храните ничего важного в cubbyhole дольше жизни токена.

> **Dev vs Production:** cubbyhole работает везде одинаково. Разница — в production время жизни токена короче, так что и cubbyhole живёт недолго.

---

## 5. Токены

Токен — это основной способ аутентификации в Vault. Даже если вы залогинились через LDAP или Kubernetes — Vault всё равно создаёт токен для сессии.

```
                   ┌─────────────┐
                   │  Root Token │  ← бессрочный, всё может
                   └──────┬──────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │ Token  │ │ Token  │ │ Token  │  ← дочерние токены
         │  (app) │ │ (user) │ │ (CI)   │
         └──┬─────┘ └──┬─────┘ └──┬─────┘
            │          │          │
            ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │ Token  │ │ Token  │ │ Token  │  ← внуки
         └────────┘ └────────┘ └────────┘
```

Каждый токен (кроме root) имеет **родителя**. Если отозвать родителя — все дочерние токены тоже отзываются (каскадный отзыв).

```bash
# Создать дочерний токен
vault token create -policy=default -ttl=1h
# Key                Value
# ---                -----
# token              hvs.CA...
# token_accessor     ...
# token_duration     1h
# token_renewable    true

# Посмотреть информацию о текущем токене
vault token lookup
# Key                 Value
# ---                 -----
# id                  hvs...
# policies            [root]
# path                auth/token/root
# ttl                 0s   ← root бессрочный
# renewable           false
# orphan              true

# Продлить токен
vault token renew

# Создать orphan-токен (без родителя)
vault token create -orphan -policy=default -ttl=30m

# Отозвать токен
vault token revoke hvs.CA...

# Отозвать все токены, созданные через определённый auth path
vault token revoke -mode=path auth/token/create
```

**Свойства токена:**

| Свойство | Описание |
|----------|----------|
| `id` | Строка вида `hvs.xxx...` |
| `policies` | Список привязанных политик |
| `ttl` | Оставшееся время жизни |
| `renewable` | Можно ли продлить (`true`/`false`) |
| `orphan` | Нет родителя — отзыв родителя не затронет этот токен |
| `path` | По какому пути был создан |
| `accessor` | Идентификатор для операций без знания самого токена |

> ☠️ **Осторожно:** root-токен — это ключ от всех дверей. Никогда не используйте root для приложений. Создайте root, выполните `vault operator init`, запечатайте root в сейф и используйте только для экстренных операций.

> **Dev vs Production:** в dev вы всё делаете с root-токеном — это нормально для обучения. В production root-токен после инициализации используется один раз для настройки политик и методов аутентификации, а затем блокируется (`vault token revoke root` не сработает, но его можно пересоздать через unseal keys).

---

## 6. Leases

**Lease** — это контракт на время жизни dynamic секрета. Когда Vault генерирует динамический секрет (пароль к БД, сертификат, AWS key), он выдаёт его **на время** — это и есть lease.

```
Запрос ──► Vault ──► lease_id + secret
                     │
                     │ TTL ───────────► просрочка = отзыв
                     │
                     └── renewable ──► продление
```

```bash
# Создать динамический секрет (например, пароль к БД)
vault read database/creds/my-role
# Key                Value
# ---                -----
# lease_id           database/creds/my-role/abc123...
# lease_duration     1h
# lease_renewable    true
# username           v-root-my-role-abc123
# password           AbCxYz123...

# Посмотреть активные lease
vault list sys/leases/lookup/database/creds/my-role

# Информация о lease
vault lease lookup database/creds/my-role/abc123...

# Продлить lease
vault lease renew database/creds/my-role/abc123...

# Явно отозвать lease (немедленно, без ожидания TTL)
vault lease revoke database/creds/my-role/abc123...
```

**Жизненный цикл lease:**

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Создание │───►│  TTL     │───►│ Renewal  │───►│  Revoke  │
│ секрета  │    │  (живёт) │    │ (опция)  │    │(явный/по │
│          │    │          │    │          │    │ TTL)     │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
```

**Что происходит при отзыве:**
1. Vault сообщает database engine, что credentials больше не действительны.
2. База данных удаляет пользователя или меняет пароль.
3. Любое приложение, использующее эти credentials, теряет доступ.

> **Dev vs Production:** lease в dev и production работают одинаково. Разница — в production пароль к БД, сгенерированный Vault, **реально меняется в базе данных**. В dev (если база не настроена) — только имитация.

---

## Типичные ошибки

- ❌ **`secret/data/` vs `secret/`** — в API KV v2 секреты лежат на `/v1/secret/data/...`, а не `/v1/secret/...`. CLI (`vault kv get`) сам подставляет `data/`, но `curl` — нет. Если получили 404 — проверьте путь.
- ❌ **Root-токен в CI/CD** — если кто-то украдёт root-токен, весь Vault скомпрометирован. Для приложений используйте AppRole, для людей — UserPass/OIDC, для CI — AppRole или Kubernetes auth.
- ❌ **Токен без `renewable=true` умрёт** — если приложение не может продлить токен, ровно через TTL оно потеряет доступ. Всегда проверяйте `renewable` при создании.
- ❌ **Забыли про lease для dynamic secrets** — пароль к БД, который не продлили, перестанет работать через TTL. Если приложение держит соединение — оно упадёт. Настройте Vault Agent или renew в коде.
- ❌ **Отзыв родительского токена убивает всех детей** — если вы отозвали токен админа, все дочерние токены тоже отозваны. Используйте `-orphan` для критичных токенов.

---

## Чек-лист

- [ ] Я понимаю структуру путей: `secret/production/myapp/database` — путь к секрету.
- [ ] Я знаю разницу KV v1 и KV v2, и что `secret/data/` — внутренний путь v2.
- [ ] Я создавал и отзывал токены, проверял их TTL и `renewable`.
- [ ] Я знаком с понятием lease: dynamic secret живёт не вечно, его нужно продлевать.

---

## Попробуйте сами

1. **Карта путей.** Запустите Vault в dev-режиме. Выполните `vault secrets list -detailed` и `vault auth list`. Нарисуйте от руки дерево путей. Сравните с картой из раздела 1 — какие engines есть, а каких нет?
2. **Иерархия токенов.** Создайте токен A, от него токен B, от B — токен C. Проверьте: `vault token lookup` на каждом. Отзовите токен B. Проверьте, жив ли токен C. (Спойлер: нет.) Затем создайте orphan-токен и повторите — он выживет.
3. **Lease в действии** (если есть database engine). Настройте database engine к тестовой PostgreSQL (или используйте mock). Создайте роль с `ttl=5m`. Получите credentials, проверьте что можете подключиться к БД. Подождите 5 минут — подключиться не получится. Продлите lease — всё снова работает.
