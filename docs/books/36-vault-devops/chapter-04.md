# Глава 4: Политики — управление доступом

## Что вы узнаете

- Что такое политика и deny-by-default.
- Синтаксис HCL для политик.
- Capabilities: read, write, list, delete, create, update, patch, sudo.
- Как создавать, применять и отлаживать политики.

---

## 1. Принцип работы политик

Vault работает по принципу **deny-by-default**: любой запрос к любому пути запрещён, пока его явно не разрешит хотя бы одна политика.

```
   Токен
      │
      ├── Политика A (разрешает secret/data/production/*)
      ├── Политика B (разрешает secret/metadata/production/*)
      │
      ▼
  Объединённые права = A + B
      │
      ▼
  Deny-by-default: всё остальное запрещено
```

Политики привязываются к **токену** при его создании. Один токен может иметь несколько политик — их права **суммируются**. Если политика A даёт `read` на `secret/data/*`, а политика B — `write` на тот же путь, то токен получит оба права.

> ☠️ **Осторожно:** deny имеет приоритет над любыми разрешениями. Если хоть одна политика явно запрещает путь через `capabilities = ["deny"]`, доступ будет заблокирован, даже если другая политика его разрешает.

Политики хранятся в Vault и применяются на стороне сервера. Клиент никогда не может их обойти — решение о доступе принимает Vault при каждом запросе.

> **Dev vs Production:** в dev-окружении часто используют root-токен или политику `* { capabilities = ["admin"] }`. В production каждая группа акторов получает минимально необходимые права — принцип наименьших привилегий.

---

## 2. Синтаксис HCL

Политики пишутся на HCL (HashiCorp Configuration Language). Базовая структура:

```hcl
# Комментарий
path "путь/до/секрета/*" {
  capabilities = ["read", "list"]
  # опционально: allowed_parameters, required_parameters, etc.
}
```

### 2.1. Capabilities

Каждая capability соответствует HTTP-методу к Vault API:

| Capability | HTTP-метод | Описание |
|---|---|---|
| `create` | POST/PUT | Создать новый секрет (без перезаписи) |
| `read` | GET | Прочитать секрет |
| `update` | POST/PUT | Обновить существующий секрет |
| `patch` | PATCH | Частичное обновление |
| `delete` | DELETE | Удалить секрет |
| `list` | LIST | Получить список ключей по пути |
| `sudo` | — | root-уровень доступа (например, `sys/health`) |
| `deny` | — | Явный запрет (перекрывает все разрешения) |

### 2.2. Примеры политик

```hcl
# Приложение читает свои секреты
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}
path "secret/metadata/production/myapp/*" {
  capabilities = ["list"]
}

# CI/CD запись в staging
path "secret/data/staging/myapp/*" {
  capabilities = ["create", "update", "patch"]
}

# Оператор: полный доступ к production
path "secret/data/production/myapp/*" {
  capabilities = ["create", "read", "update", "patch", "delete", "list"]
}

# Явный запрет (приоритетнее разрешений)
path "secret/data/production/infra/*" {
  capabilities = ["deny"]
}
```

### 2.3. Правила работы wildcard `*`

- `secret/data/production/*` — матчит **один** уровень: `secret/data/production/db`, но **НЕ** `secret/data/production/myapp/db`.
- `secret/data/production/**` — в Vault нет `**`. Для вложенности используйте `secret/data/production/myapp/*` или `secret/data/production/+/*`.
- `secret/data/production/myapp/*` — матчит любые пути под `myapp/`.

### 2.4. Параметризованные политики

Можно ограничить не только путь, но и параметры запроса:

```hcl
# Разрешить запись только определённых полей
path "secret/data/staging/myapp/*" {
  capabilities = ["create", "update"]
  allowed_parameters = {
    "host"     = []
    "port"     = []
    "username" = []
  }
  denied_parameters = {
    "password" = []
  }
}
```

---

## 3. Создание и управление

Политики хранятся в HCL-файлах и загружаются в Vault через CLI или API.

### 3.1. Создание политики

Сохраните HCL в файл:

```bash
cat > myapp-policy.hcl << 'EOF'
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}
path "secret/metadata/production/myapp/*" {
  capabilities = ["list"]
}
EOF
```

Загрузите в Vault:

```bash
vault policy write myapp-policy myapp-policy.hcl
```

### 3.2. Просмотр политик

```bash
# Список всех политик
vault policy list

# Чтение содержимого политики
vault policy read myapp-policy

# Вывод в JSON (для парсинга)
vault policy read -format=json myapp-policy
```

### 3.3. Удаление политики

```bash
vault policy delete myapp-policy
```

> ☠️ **Осторожно:** удаление политики не отзывает токены, которые её уже получили. Токен продолжит работать до истечения TTL. Если нужно срочно отозвать доступ — отзывайте токен через `vault token revoke`.

```bash
# Проверить какие токены используют политику
vault list auth/token/accessors
# Затем для каждого accessor:
vault token lookup -accessor ACCESSOR
```

### 3.4. Работа через API

```bash
# Запись политики через curl
curl --header "X-Vault-Token: $VAULT_TOKEN" \
     --request PUT \
     --data '{"policy":"path \"secret/data/*\" { capabilities = [\"read\"] }"}' \
     $VAULT_ADDR/v1/sys/policies/acl/myapp-policy
```

> **Dev vs Production:** в dev можно хранить HCL-файлы в репозитории. В production политики должны быть частью Infrastructure as Code (Terraform, Ansible) и проходить code review перед применением.

---

## 4. Тестирование политики

Прежде чем выдавать политику пользователям, её нужно протестировать.

### 4.1. Создание тестового токена

```bash
vault token create -policy=myapp-policy -ttl=1h
```

```
Key                  Value
---                  -----
token                hvs.CAESIHk...
token_accessor       fg7Jk...
token_duration       1h
token_policies       ["default" "myapp-policy"]
```

### 4.2. Проверка capabilities

```bash
# Какие операции разрешены на конкретном пути
vault token capabilities hvs.CAESIHk... secret/data/production/myapp/database
# read

vault token capabilities hvs.CAESIHk... secret/metadata/production/myapp/database
# list

vault token capabilities hvs.CAESIHk... secret/data/staging/myapp/database
# deny (нет такой политики)
```

### 4.3. Проверка с реальным запросом

```bash
# Экспортируем тестовый токен
export VAULT_TOKEN=hvs.CAESIHk...

# Должно сработать
vault kv get secret/production/myapp/database

# Должно упасть с 403
vault kv get secret/staging/myapp/database

# Должно упасть с 403
vault kv put secret/production/myapp/database key=val
```

### 4.4. Просмотр действующих политик токена

```bash
# Детальная информация по токену
vault token lookup hvs.CAESIHk...
```

```
Key                  Value
---                  -----
policies             ["default" "myapp-policy"]
identity_policies    []
...
```

### 4.5. ACL simulator (Vault Enterprise)

В Vault Enterprise есть встроенный ACL Simulator в UI. Позволяет ввести политику и путь и сразу увидеть разрешённые операции без создания токена.

---

## 5. Встроенные политики

Vault поставляется с двумя встроенными политиками:

### root

- Полный доступ ко всем путям и операциям.
- Нельзя изменить или удалить.
- Используется только для начальной настройки.
- root-токен нужно отозвать сразу после настройки политик и методов аутентификации.

> ☠️ **Осторожно:** никогда не используйте root-токен в повседневной работе. root-токен не подчиняется политикам — он может всё. Если он скомпрометирован, злоумышленник получит полный контроль над Vault.

### default

- Прикрепляется к **каждому** токену автоматически.
- По умолчанию пустая — не даёт никаких прав, кроме `sys/capabilities` и `sys/tools/random` (самопроверка).
- Можно расширить, перезаписав политику `default`.

```bash
# Просмотр политики default
vault policy read default

# Расширение default — например, разрешить всем читать
# определённый путь (осторожно!)
vault policy write default default-policy.hcl
```

---

## Типичные ошибки

- ❌ **Забыли `list` на `secret/metadata/*`** — без `list` на `metadata` команда `vault kv list secret/production/myapp` вернёт 403, хотя `read` на `data` работает. Для `list` нужна capability `list` на `secret/metadata/*`.
- ❌ **Пути `secret/data/*` ≠ `secret/metadata/*`** — политики привязаны к конкретному пути. Разрешение на `secret/data/production/*` не даёт доступа к `secret/metadata/production/*`. Нужны две разные записи.
- ❌ **Wildcard `*` матчит один уровень** — `secret/data/production/*` не даст доступ к `secret/data/production/myapp/database`. Нужно `secret/data/production/myapp/*` или секция для каждого уровня.
- ❌ **Политика удалена, а токен жив** — токен продолжает работать до истечения TTL даже после удаления политики. Всегда отзывайте токены при смене политик.
- ❌ **Слишком широкая политика** — `path "secret/*"` даёт доступ ко всем секретам всех окружений. Используйте вложенность: `secret/data/{env}/{service}/*`.
- ❌ **Забыли deny для критичных путей** — если одна политика даёт `read` на `secret/data/*`, а другая этого не запрещает — доступ есть. Явно запрещайте через `deny` там, где нужно.

---

## Чек-лист

- [ ] Я создал отдельные политики для каждой роли: приложение, CI/CD, оператор, разработчик.
- [ ] Я дал каждой роли минимально необходимые capabilities (принцип наименьших привилегий).
- [ ] Я протестировал каждую политику через `vault token capabilities` и реальными запросами.
- [ ] Я убедился, что root-токен не используется в日常工作 (повседневной работе), а файлы политик хранятся в репозитории как код.

---

## Попробуйте сами

1. **Напишите политику для CI/CD.** Создайте HCL-файл, который даёт `create`, `update`, `patch` на `secret/data/staging/*` и `list` на `secret/metadata/staging/*`. Загрузите политику через `vault policy write`. Создайте тестовый токен с этой политикой. Проверьте что `kv put` работает, а `kv delete` возвращает 403.

2. **Проверьте deny-приоритет.** Создайте две политики: первая даёт `read` на `secret/data/production/*`, вторая — `deny` на `secret/data/production/infra/*`. Создайте токен с обеими политиками. Проверьте что `secret/data/production/myapp/db` читается, а `secret/data/production/infra/db` — нет. Это защита от «случайного» перекрытия прав.

3. **Параметризованная политика.** Напишите политику, которая разрешает `create` и `update` на `secret/data/staging/myapp/*`, но только с полями `host`, `port`, `username`. Запретите поле `password`. Загрузите политику, создайте токен и убедитесь, что запись с `password` отклоняется.
