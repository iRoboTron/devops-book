# Глава 5: Методы аутентификации — Token, AppRole, UserPass, LDAP

## Что вы узнаете

- Зачем нужны разные методы аутентификации.
- Token auth — базовый, но не для людей.
- AppRole — для приложений и CI/CD.
- Response Wrapping — безопасная передача секретов.
- LDAP — для корпоративных команд.
- UserPass — для людей без LDAP.

---

## 1. Зачем разные методы

Vault не знает, кто стучится в дверь. Метод аутентификации (auth method) — это способ подтвердить личность и получить токен с нужными политиками.

У каждого актора своя природа: человек вводит пароль, сервер предъявляет JWT, CI/CD пайплайн использует role-id + secret-id. Разные методы закрывают разные сценарии.

| Актор | Метод | Причина |
|---|---|---|
| Разработчик | UserPass / LDAP | Логин/пароль или корпоративный аккаунт |
| CI/CD пайплайн | AppRole | rotate-friendly контейнерные credentials |
| Docker-контейнер | AppRole | Аналогично CI/CD |
| Kubernetes Pod | Kubernetes Auth | ServiceAccount JWT |
| Облачная VM | AWS/GCP Auth | IAM-роль |
| Ansible / Terraform | AppRole | Сервис-аккаунт |

> **Dev vs Production:** в dev можно обойтись одним root-токеном. В production каждый тип актора получает свой метод аутентификации со своим TTL, своими политиками и аудитом.

---

## 2. Token Auth — базовый уровень

Token auth — встроенный метод, который нельзя отключить. Это «вход по токену»: вы либо создаёте токен через `vault token create`, либо логинитесь через другой метод и получаете токен.

### 2.1. Создание токена

```bash
# Токен с политикой и именем
vault token create \
  -policy=myapp-policy \
  -ttl=24h \
  -display-name="myapp-production"
```

```
Key                  Value
---                  -----
token                hvs.CAES...
token_accessor       ...
token_duration       24h
token_policies       ["default" "myapp-policy"]
```

### 2.2. Параметры токена

| Параметр | Описание |
|---|---|
| `-policy` | Политики, прикрепляемые к токену |
| `-ttl` | Время жизни (максимум — `max_ttl` роли или системы) |
| `-display-name` | Человеческое имя для аудита |
| `-period` | Токен с автоматическим продлением (Renewable) |
| `-use-limit` | Максимум использований (после — токен недействителен) |

### 2.3. Управление жизненным циклом

```bash
# Продлить TTL
vault token renew hvs.CAES...

# Информация о токене
vault token lookup hvs.CAES...

# По accessor (без раскрытия самого токена)
vault token lookup -accessor ACCESSOR

# Отозвать токен
vault token revoke hvs.CAES...

# Отозвать по accessor
vault token revoke -accessor ACCESSOR
```

### 2.4. Создание токена с orphan

```bash
# Orphan-токен не удаляется при отзыве родителя
vault token create -orphan -policy=myapp-policy
```

> ☠️ **Осторожно:** обычный (дочерний) токен будет отозван вместе с родительским. Если вам нужен токен, живущий независимо, используйте `-orphan`. Но orphan-токены сложнее отслеживать — их нужно отзывать явно.

### 2.5. Настройка max_ttl

Параметр `max_ttl` ограничивает максимальное время жизни токена, независимо от продлений:

```bash
# Токен нельзя продлить дольше 48 часов
vault token create -policy=myapp-policy -ttl=24h -max-ttl=48h
```

---

## 3. AppRole — для приложений и CI/CD

AppRole — метод аутентификации, предназначенный для машин (не людей). Приложение получает `role_id` (публичный идентификатор) и `secret_id` (одноразовый секрет), обменивает их на токен Vault, и работает с этим токеном.

```
  ┌─────────┐          ┌─────────────┐          ┌──────┐
  │  CI/CD  │          │    Vault    │          │ App  │
  └────┬────┘          └──────┬──────┘          └──┬───┘
       │                      │                    │
       │  POST /auth/approle/login                 │
       │  role_id + secret_id │                    │
       ├─────────────────────►│                    │
       │                      │                    │
       │◄─────────────────────┤                    │
       │     token (TTL: 1h)  │                    │
       │                      │                    │
       │  передать token      │                    │
       ├─────────────────────────────────────────►│
       │                      │                    │
       │                      │  GET secret/myapp  │
       │                      │◄───────────────────│
       │                      │                    │
       │                      │───────────────────►│
       │                      │ {"password":"s3cr3t"}
```

### 3.1. Включение и настройка роли

```bash
# Включить AppRole auth method
vault auth enable approle

# Создать роль для CI/CD
vault write auth/approle/role/myapp-cicd \
  token_policies="myapp-policy" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=10m \
  secret_id_num_uses=1
```

Параметры роли:

| Параметр | Значение | Смысл |
|---|---|---|
| `token_policies` | `myapp-policy` | Политики, выдаваемые токену |
| `token_ttl` | `1h` | Время жизни токена |
| `token_max_ttl` | `4h` | Максимум после продлений |
| `secret_id_ttl` | `10m` | Время жизни secret_id |
| `secret_id_num_uses` | `1` | Сколько раз можно использовать secret_id |
| `token_bound_cidrs` | `["10.0.0.0/8"]` | Привязка к IP (опционально) |

### 3.2. Получение role_id и secret_id

```bash
# role_id — публичный, можно хранить в CI переменной
vault read auth/approle/role/myapp-cicd/role-id

# secret_id — секретный, генерируется однократно
vault write -f auth/approle/role/myapp-cicd/secret-id
```

```
Key                   Value
---                   -----
secret_id             abcdef12-...
secret_id_accessor    ...
secret_id_ttl         10m
secret_id_num_uses    1
```

### 3.3. Логин через AppRole

```bash
# Обмен role_id + secret_id на токен
vault write auth/approle/login \
  role_id="РОЛЬ_АЙДИ" \
  secret_id="СЕКРЕТ_АЙДИ"
```

```
Key                  Value
---                  -----
token                hvs.CAES...
token_policies       ["default" "myapp-policy"]
token_duration       1h
```

### 3.4. AppRole в CI/CD

```yaml
# .gitlab-ci.yml
variables:
  VAULT_ADDR: https://vault.example.com:8200

job:
  script:
    - apk add vault jq
    # Логин через AppRole
    - export VAULT_TOKEN=$(vault write -field=token auth/approle/login \
        role_id=$ROLE_ID secret_id=$SECRET_ID)
    # Чтение секретов
    - export DB_PASS=$(vault kv get -field=password secret/production/myapp/db)
    - ./deploy.sh
```

> **Dev vs Production:** в dev-стенде `secret_id_ttl` может быть 24h и `secret_id_num_uses=0` (неограниченно). В production `secret_id` живёт 5-10 минут, одноразовый, и генерируется перед каждым пайплайном.

### 3.5. Best practices

- `role_id` **не является секретом**, но не должен быть публичным. Храните в CI variables как `protected` и `masked`.
- `secret_id` генерируйте непосредственно перед использованием через `vault write -f auth/approle/role/.../secret-id`.
- Никогда не храните `secret_id` в коде или в репозитории.
- Используйте `secret_id_bound_cidrs` для привязки к IP-адресам CI/CD-раннера.
- Для Terraform используйте AppRole с `secret_id_num_uses=1` — каждый `terraform plan` получает свежий secret_id.

---

## 4. Response Wrapping — безопасная передача

Response Wrapping позволяет «упаковать» ответ Vault в одноразовый токен. Вместо того чтобы передавать `secret_id` по незащищённому каналу, CI/CD получает **wrapping token**, который можно безопасно передать.

### 4.1. Создание wrapped secret_id

```bash
# Генерируем secret_id и упаковываем в wrapping token
vault write -wrap-ttl=5m -f auth/approle/role/myapp-cicd/secret-id
```

```
Key                              Value
---                              -----
wrapping_token:                  hvs.CAESIL...
wrapping_token_ttl:              5m
wrapping_token_creation_time:    ...
```

### 4.2. Распаковка

```bash
# На целевой машине — распаковываем
VAULT_TOKEN=hvs.CAESIL... vault unwrap
```

```
Key                   Value
---                   -----
secret_id             abcdef12-...
secret_id_accessor    ...
```

### 4.3. Как это работает

```
  CI/CD                                Vault
    │                                    │
    │  vault write -wrap-ttl=5m ...      │
    │───────────────────────────────────►│
    │◄───────────────────────────────────│
    │  wrapping_token (hvs.CAES...)      │
    │  (secret_id спрятан внутри)        │
    │                                    │
    │  передать wrapping_token           │
    │  (по HTTP, через переменную...)    │
    │                                    │
  App                                    │
    │  vault unwrap                      │
    │───────────────────────────────────►│
    │◄───────────────────────────────────│
    │  secret_id (abcdef12-...)          │
    │                                    │
    │  vault write auth/approle/login    │
    │───────────────────────────────────►│
    │◄───────────────────────────────────│
    │  token (hvs...)                    │
```

> ☠️ **Осторожно:** wrapping token можно перехватить при передаче, но без целевого токена (`VAULT_TOKEN`) он бесполезен. Тем не менее, wrapping token сам по себе — секрет. Передавайте его по TLS, не пишите в логи, не сохраняйте на диск.

### 4.4. Использование в CI/CD

```bash
# Этап 1: генерируем wrapped secret_id (на CI/CD сервере)
WRAPPED=$(vault write -wrap-ttl=5m -f -field=wrapping_token \
  auth/approle/role/myapp-cicd/secret-id)

# Передаём WRAPPED в переменную окружения следующего этапа

# Этап 2: распаковываем (на раннере)
SECRET_ID=$(VAULT_TOKEN="$WRAPPED" vault unwrap -field=secret_id)

# Этап 3: логинимся
VAULT_TOKEN=$(vault write -field=token auth/approle/login \
  role_id="$ROLE_ID" secret_id="$SECRET_ID")

# Этап 4: используем
vault kv get secret/production/myapp/db
```

---

## 5. LDAP — для корпоративных команд

Если в компании уже есть LDAP/Active Directory — не надо заводить отдельные пароли в Vault. LDAP auth method проксирует аутентификацию на корпоративный LDAP-сервер.

### 5.1. Настройка LDAP

```bash
# Включить LDAP auth
vault auth enable ldap

# Настройка подключения к LDAP-серверу
vault write auth/ldap/config \
  url="ldap://ldap.internal.company.com" \
  userdn="ou=users,dc=company,dc=com" \
  groupdn="ou=groups,dc=company,dc=com" \
  binddn="cn=vault-reader,dc=company,dc=com" \
  bindpass="ServiceAccountPass" \
  userattr="uid"
```

Параметры конфигурации:

| Параметр | Описание |
|---|---|
| `url` | Адрес LDAP-сервера (`ldap://` или `ldaps://`) |
| `userdn` | Базовый DN для поиска пользователей |
| `groupdn` | Базовый DN для поиска групп |
| `binddn` | Сервисный аккаунт для поиска в LDAP (read-only) |
| `bindpass` | Пароль сервисного аккаунта |
| `userattr` | Атрибут идентификации пользователя (`uid`, `cn`, `sAMAccountName`) |
| `certificate` | TLS-сертификат (для LDAPS) |

### 5.2. Привязка LDAP-групп к политикам Vault

```bash
# Группа devops-team получает политики admin и default
vault write auth/ldap/groups/devops-team \
  policies="admin-policy,default"

# Группа developers — только myapp-policy
vault write auth/ldap/groups/developers \
  policies="myapp-policy,default"

# Можно также привязать отдельного пользователя
vault write auth/ldap/users/ivan \
  policies="myapp-policy,default"
```

### 5.3. Логин через LDAP

```bash
# Интерактивный ввод пароля
vault login -method=ldap username=ivan
Password (will be hidden): *****

# В одну строку (небезопасно — пароль в истории)
vault login -method=ldap username=ivan password="MyPassword"
```

```
Key                  Value
---                  -----
token                hvs.CAES...
token_policies       ["default" "admin-policy"]
token_duration       768h
```

> ☠️ **Осторожно:** передача пароля через `password=` оставляет его в shell history. Всегда используйте интерактивный режим или переменную окружения `VAULT_LDAP_PASSWORD`.

### 5.4. Привязка пользователей без группы

Если у пользователя нет LDAP-группы, но есть прямая запись `auth/ldap/users/<username>`:

```bash
vault write auth/ldap/users/ivan policies="myapp-policy"
```

Приоритет: пользовательские политики `users/<username>` + групповые политики из LDAP.

---

## 6. UserPass — для людей

UserPass — простейший метод для людей, когда корпоративного LDAP нет. Пользователь вводит логин и пароль, Vault проверяет локально и выдаёт токен.

### 6.1. Настройка

```bash
# Включить userpass
vault auth enable userpass

# Создать пользователя
vault write auth/userpass/users/ivan \
  password="SecurePass123" \
  policies="myapp-policy,default"
```

### 6.2. Логин

```bash
# Интерактивный
vault login -method=userpass username=ivan
Password (will be hidden): *****

# В скрипте (небезопасно)
vault login -method=userpass username=ivan password="SecurePass123"
```

### 6.3. Дополнительные параметры

```bash
# Пользователь с ограниченным TTL
vault write auth/userpass/users/ivan \
  password="SecurePass123" \
  policies="myapp-policy,default" \
  token_ttl=2h \
  token_max_ttl=8h

# Пользователь с привязкой к CIDR
vault write auth/userpass/users/ivan \
  password="SecurePass123" \
  token_bound_cidrs="10.0.0.0/8"

# Смена пароля самим пользователем
vault write auth/userpass/users/ivan/password \
  password="NewPass456" \
  new_password="EvenNewerPass789"
```

### 6.4. Обновление и удаление

```bash
# Обновить политики пользователя
vault write auth/userpass/users/ivan \
  policies="admin-policy,default"

# Удалить пользователя
vault delete auth/userpass/users/ivan
```

> **Dev vs Production:** UserPass удобен для dev-стенда, где нет LDAP, но в production стоит заменить его на LDAP, OIDC или другой корпоративный метод. UserPass не поддерживает MFA, SSO, и пароли хранятся в storage Vault, что создаёт дополнительную поверхность атаки.

---

## Типичные ошибки

- ❌ **`secret_id_num_uses=1` и повторная попытка** — приложение попыталось переиспользовать secret_id, получило ошибку. После одного использования secret_id уничтожается. Генерируйте новый secret_id на каждый логин.
- ❌ **Хранить secret_id в CI как постоянную переменную** — secret_id должен быть короткоживущим (10 минут). Хранить его неделями — дыра в безопасности. Генерируйте при каждом запуске пайплайна.
- ❌ **UserPass для приложений** — UserPass не предназначен для машин: пароль сложно ротировать, нет поддержки CIDR-bound credentials, аудит привязан к конкретному пользователю. Для приложений — AppRole.
- ❌ **Пароль в командной строке** — любая команда `vault login -method=ldap password=...` или `vault login -method=userpass password=...` оставляет пароль в истории shell. Используйте интерактивный ввод.
- ❌ **Wrapping token без TTL** — wrapping token без TTL будет висеть вечно. Всегда ставьте `-wrap-ttl=5m`. Он нужен ровно на время передачи между системами.

---

## Чек-лист

- [ ] Я выбрал метод аутентификации под каждого актора: AppRole для CI/CD, LDAP/UserPass для людей, OIDC/K8s для облачных сценариев.
- [ ] Для AppRole я настроил разумные TTL: `token_ttl=1h`, `secret_id_ttl=10m`, `secret_id_num_uses=1`.
- [ ] Я не храню `secret_id` в коде или конфигах — генерирую перед каждым использованием, передаю через Response Wrapping.
- [ ] Я настроил LDAP с `ldaps://`, сертификатом и сервисным аккаунтом с минимальными правами (read-only).

---

## Попробуйте сами

1. **Настройте AppRole для CI/CD.** Включите approle. Создайте роль `myapp-cicd` с `token_policies="myapp-policy"`, `token_ttl=30m`, `secret_id_num_uses=1`. Получите `role_id` и `secret_id`. Выполните логин через `vault write auth/approle/login`. Убедитесь, что полученный токен имеет политику `myapp-policy`. Попробуйте переиспользовать `secret_id` — убедитесь, что второй запрос падает с ошибкой.

2. **Response Wrapping на практике.** Сгенерируйте `secret_id` с wrapping TTL 5 минут. Передайте wrapping token через переменную окружения. Распакуйте его на другой «машине» (той же сессии, но с очищенным `VAULT_TOKEN`). Выполните логин. Попробуйте распаковать тот же wrapping token повторно — убедитесь, что он одноразовый.

3. **UserPass + разные политики.** Включите userpass. Создайте двух пользователей: `ivan` с `myapp-policy` и `petro` с `admin-policy`. Залогиньтесь как `ivan` — проверьте что `kv get` работает, а `sys/health` — нет. Залогиньтесь как `petro` — проверьте что `sys/health` доступен.
