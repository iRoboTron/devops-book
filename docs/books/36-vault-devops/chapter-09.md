# Глава 9: Vault в Docker Compose — production-like setup

## Что вы узнаете

- Как запустить Vault с постоянным хранилищем (Raft) в Docker Compose.
- Сравнение storage backends: какой и когда выбирать.
- Инициализация и unseal Vault.
- Настройка TLS для production-окружения.
- Полный пример стека: Vault + приложение + Vault Agent.

---

## 1. Сравнение storage backends

Vault хранит зашифрованные данные в storage backend. Выбор backend определяет, как Vault обеспечивает High Availability (HA), восстанавливается после перезапуска и масштабируется.

| Backend | HA | Простота настройки | Когда использовать |
|---------|----|--------------------|--------------------|
| **Raft** | Да* | Высокая | 1–5 нод, встроенное хранение, нет внешних зависимостей |
| **Consul** | Да | Средняя | >5 нод, уже есть Consul в инфраструктуре |
| **File** | Нет | Высокая | Только dev/testing, нет отказоустойчивости |
| **In-memory** | Нет | Макс | Dev-режим (`-dev`), **НИКОГДА** для production |

> \* Raft требует минимум 3 ноды для HA-кластера (majority). Одна нода — работает, но не HA.

```ascii
Выбор backend по сценариям:

┌─────────────────────────────────────────────────────────────────┐
│                         Vault Storage Backends                   │
├────────────┬───────────┬──────────┬─────────────┬───────────────┤
│            │  Raft     │  Consul  │    File     │   In-memory   │
├────────────┼───────────┼──────────┼─────────────┼───────────────┤
│ Dev/local  │    ✅     │   ❌    │    ✅       │    ✅ (dev)   │
│ Staging    │    ✅     │   ⚠️    │    ❌       │    ❌         │
│ Production │    ✅     │   ✅    │    ❌       │    ❌         │
│ HA         │  ≥3 нод   │   ✅    │    ❌       │    ❌         │
│ DR         │  ≥3 нод   │   ✅    │    ❌       │    ❌         │
└────────────┴───────────┴──────────┴─────────────┴───────────────┘
```

> **Dev vs Production:** в dev используйте `-dev` (in-memory) или File backend для простоты. В production — Raft (нет внешних зависимостей) или Consul (уже есть Consul). Никогда — in-memory или File.

В этой книге используется Raft — встроенное хранилище, не требующее внешних компонентов.

---

## 2. Vault с Raft storage

### 2.1. Конфигурация Vault

```hcl
# vault-config.hcl
ui = true
disable_mlock = true

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

api_addr     = "http://vault:8200"
cluster_addr = "http://vault:8201"
```

| Параметр | Описание |
|----------|----------|
| `ui = true` | Включает веб-интерфейс Vault на порту 8200 |
| `disable_mlock = true` | Отключает mlock (обязательно в Docker, нет доступа к `mlock` syscall) |
| `storage "raft"` | Использует встроенный Raft storage |
| `storage.path` | Директория для хранения Raft-лога и снапшотов |
| `storage.node_id` | Уникальный ID ноды в Raft-кластере |
| `listener` | TCP-слушатель на порту 8200 |
| `api_addr` | Адрес, по которому клиенты обращаются к Vault API |
| `cluster_addr` | Адрес для межнодового взаимодействия Raft |

### 2.2. Docker Compose

```yaml
services:
  vault:
    image: hashicorp/vault:1.17
    ports:
      - "8200:8200"
    volumes:
      - ./vault-config.hcl:/vault/config/vault.hcl:ro
      - vault-data:/vault/data
    cap_add:
      - IPC_LOCK
    command: server -config=/vault/config/vault.hcl
    healthcheck:
      test: ["CMD", "vault", "status"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  vault-data:
```

> ☠️ **Осторожно:** `cap_add: [IPC_LOCK]` необходим в Docker. Без него Vault не сможет заблокировать память для защиты секретов от swap. Если вы видите ошибку `WARNING! mlock is not supported`, добавьте эту capability.

**Структура директорий проекта:**

```
project/
├── docker-compose.yml
├── vault-config.hcl
└── vault-data/          # создаётся Docker-томом
```

### 2.3. Raft-кластер из трёх нод

```yaml
services:
  vault-1:
    image: hashicorp/vault:1.17
    ports: ["8201:8200"]
    volumes:
      - ./config/vault-1.hcl:/vault/config/vault.hcl:ro
      - raft-1:/vault/data
    cap_add: [IPC_LOCK]
    command: server -config=/vault/config/vault.hcl
    networks:
      - vault-cluster

  vault-2:
    image: hashicorp/vault:1.17
    ports: ["8202:8200"]
    volumes:
      - ./config/vault-2.hcl:/vault/config/vault.hcl:ro
      - raft-2:/vault/data
    cap_add: [IPC_LOCK]
    command: server -config=/vault/config/vault.hcl
    networks:
      - vault-cluster

  vault-3:
    image: hashicorp/vault:1.17
    ports: ["8203:8200"]
    volumes:
      - ./config/vault-3.hcl:/vault/config/vault.hcl:ro
      - raft-3:/vault/data
    cap_add: [IPC_LOCK]
    command: server -config=/vault/config/vault.hcl
    networks:
      - vault-cluster

volumes:
  raft-1: raft-2: raft-3:

networks:
  vault-cluster:
```

Конфиг каждой ноды аналогичен, отличаются только `node_id` и адреса:

```hcl
storage "raft" {
  path    = "/vault/data"
  node_id = "vault-2"  # vault-1, vault-2, vault-3

  retry_join {
    leader_api_addr = "http://vault-1:8200"
  }
  retry_join {
    leader_api_addr = "http://vault-2:8200"
  }
  retry_join {
    leader_api_addr = "http://vault-3:8200"
  }
}
```

```ascii
          ┌─────────────────────────────────────┐
          │         Raft Cluster                 │
          │                                      │
          │  ┌─────────┐  ┌─────────┐  ┌──────┐  │
          │  │ Vault-1 │◄─►│ Vault-2 │◄─►│Vault-3││
          │  │ (leader)│  │(follower)│  │(foll.)│ │
          │  └────┬────┘  └─────────┘  └───────┘  │
          │       │                                │
          │       │  Raft protocol                 │
          │       │  - log replication              │
          │       │  - leader election              │
          └───────┼────────────────────────────────┘
                  │
          ┌───────▼────────┐
          │   Клиенты       │
          │   (api_addr)    │
          └────────────────┘
```

---

## 3. Инициализация и unseal

### 3.1. Запуск Vault

```bash
docker compose up -d
```

После первого запуска Vault находится в состоянии **sealed**. Он не может расшифровать данные, пока не получит unseal keys.

### 3.2. Инициализация

```bash
# Инициализируем Vault, создаём 5 ключей, для unseal нужно минимум 3
vault operator init -key-shares=5 -key-threshold=3
```

Вывод:

```
Unseal Key 1: H7p8...
Unseal Key 2: fK2a...
Unseal Key 3: 9xR1...
Unseal Key 4: mN4v...
Unseal Key 5: wB6z...

Initial Root Token: hvs.2sA...
```

> ☠️ **Осторожно:** unseal keys и root token показываются **ровно один раз**. Если вы потеряете threshold (3 из 5) ключей, данные Vault будут недоступны навсегда. Нет способа восстановить их. Храните ключи в менеджере паролей (1Password, Vault Enterprise), разделите между разными людьми.

### 3.3. Unseal

```bash
# Применяем 3 ключа из 5
vault operator unseal H7p8...
vault operator unseal fK2a...
vault operator unseal 9xR1...

# Проверка статуса
vault status
# Sealed: false
```

```ascii
Процесс unseal:

  ┌─────────────┐     ┌──────────────────┐
  │ Vault sealed│────►│  vault operator  │
  │             │     │  unseal KEY_1    │
  └─────────────┘     └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │  vault operator  │
                      │  unseal KEY_2    │
                      └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │  vault operator  │
                      │  unseal KEY_3    │
                      └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │  Sealed: false   │
                      │  Vault готов     │
                      └──────────────────┘
```

### 3.4. Вход в Vault

```bash
vault login hvs.2sA...
```

### 3.5. Автоматизация unseal

Для production автоматизируйте unseal, чтобы при рестарте контейнера Vault автоматически разблокировался:

```bash
#!/bin/sh
# auto-unseal.sh

vault operator unseal $(cat /vault/keys/unseal_key_1)
vault operator unseal $(cat /vault/keys/unseal_key_2)
vault operator unseal $(cat /vault/keys/unseal_key_3)
```

> ☠️ **Осторожно:** хранение unseal keys в том же Docker Compose — **плохая практика**. Если злоумышленник получит доступ к серверу, он найдёт ключи рядом с Vault. В production используйте auto-unseal (Transit, AWS KMS, GCP CKMS).

---

## 4. Auto-unseal через Transit

Auto-unseal — механизм, при котором Vault автоматически расшифровывает свой root key, используя внешний KMS или другой Vault.

```hcl
# vault-config.hcl с auto-unseal через Transit
seal "transit" {
  address            = "http://vault-unsealer:8200"
  token              = "hvs.transit-token..."
  disable_renewal    = "false"

  # Имя ключа в Transit engine (должен быть создан заранее)
  key_name           = "autounseal"
  mount_path         = "transit"
}
```

```hcl
# Альтернатива — AWS KMS
seal "awskms" {
  region    = "us-east-1"
  kms_key_id = "alias/vault-unseal-key"
}
```

```ascii
Сравнение методов unseal:

┌──────────────────────────────────────────────────────────┐
│                   Auto-unseal (Transit)                   │
│                                                          │
│  ┌──────────┐   transit   ┌──────────────────┐          │
│  │  Vault   │────────────►│  Vault Unsealer   │          │
│  │(sealed)  │◄────────────│  (Transit engine) │          │
│  └──────────┘   root key  └──────────────────┘          │
│                 decrypted                                │
│                                                          │
│  Плюс: автоматический unseal при рестарте               │
│  Минус: нужен второй Vault (или внешний KMS)             │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│              Ручной unseal (shamir)                       │
│                                                          │
│  ┌──────────┐   KEY_1   ┌─────┐                         │
│  │  Vault   │◄──────────│Оператор│ (3 из 5)              │
│  │(sealed)  │  KEY_2    └─────┘                         │
│  └──────────┘  KEY_3                                    │
│                                                          │
│  Плюс: не требует внешних сервисов                       │
│  Минус: ручной процесс при каждом рестарте               │
└──────────────────────────────────────────────────────────┘
```

> **Dev vs Production:** в dev используйте ручной unseal (Shamir) — это просто и наглядно. В production — auto-unseal (Transit/AWS KMS), чтобы Vault автоматически разблокировался при рестарте, без участия оператора.

---

## 5. TLS для production

В production Vault должен работать через HTTPS. TLS защищает:
- Конфиденциальность: секреты не передаются в открытом виде.
- Аутентификацию: клиент знает, что подключается к настоящему Vault, а не к MITM.
- Целостность: данные не могут быть изменены в пути.

### 5.1. Сертификат

Сертификат можно получить либо через Vault PKI (Глава 7), либо через внешний CA:

```bash
# Генерация self-signed сертификата для dev/testing
openssl req -x509 -newkey rsa:4096 -keyout vault-key.pem \
  -out vault-cert.pem -days 365 -nodes \
  -subj "/CN=vault.internal.example.com" \
  -addext "subjectAltName = DNS:vault.internal.example.com,DNS:localhost,IP:127.0.0.1"
```

### 5.2. Конфигурация с TLS

```hcl
# vault-config-tls.hcl
ui = true
disable_mlock = true

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/tls/vault-cert.pem"
  tls_key_file  = "/vault/tls/vault-key.pem"
}

api_addr     = "https://vault.internal.example.com:8200"
cluster_addr = "https://vault.internal.example.com:8201"
```

### 5.3. Docker Compose с TLS

```yaml
services:
  vault:
    image: hashicorp/vault:1.17
    ports:
      - "8200:8200"
    volumes:
      - ./vault-config-tls.hcl:/vault/config/vault.hcl:ro
      - vault-data:/vault/data
      - ./tls:/vault/tls:ro
    cap_add:
      - IPC_LOCK
    command: server -config=/vault/config/vault.hcl
    environment:
      VAULT_CACERT: /vault/tls/vault-cert.pem

volumes:
  vault-data:
```

> ☠️ **Осторожно:** никогда не передавайте `tls_disable = true` в production. Это отключает шифрование, и секреты передаются через сеть в открытом виде. TLS обязателен для любого окружения, кроме локального dev.

### 5.4. Настройка клиента для TLS

```bash
# Клиент подключается к Vault с TLS
export VAULT_ADDR="https://vault.internal.example.com:8200"
export VAULT_CACERT="/etc/ssl/certs/ca-chain.crt"

vault status
```

---

## 6. Полный стек: Vault + приложение + Vault Agent

### 6.1. Схема работы

```ascii
┌─────────────────────────────────────────────────────┐
│                 Docker Compose                        │
│                                                      │
│  ┌──────────────┐                                    │
│  │    Vault      │  storage       ┌────────────┐    │
│  │   :8200       │────────────────►  Raft data  │    │
│  └──────┬───────┘                  └────────────┘    │
│         │                                             │
│         │ 1. AppRole login                            │
│         │ 2. Read secrets                             │
│  ┌──────▼────────┐     ┌──────────────────────┐      │
│  │  Vault Agent   │────►│  /shared/secrets/    │      │
│  │  (sidecar)     │read │  database.env (tpl)  │      │
│  └───────┬───────┘     └──────────┬───────────┘      │
│          │                        │                   │
│          │                        │ 4. mount          │
│          │ 3. render template     │                   │
│          └────────────────────────┘                   │
│                                  │                    │
│                         ┌────────▼────────┐           │
│                         │    myapp        │           │
│                         │ (читает файл)   │           │
│                         └─────────────────┘           │
└──────────────────────────────────────────────────────┘
```

### 6.2. Полный docker-compose.yml

```yaml
services:
  vault:
    image: hashicorp/vault:1.17
    ports:
      - "8200:8200"
    volumes:
      - ./vault-config.hcl:/vault/config/vault.hcl:ro
      - vault-data:/vault/data
    cap_add:
      - IPC_LOCK
    command: server -config=/vault/config/vault.hcl
    healthcheck:
      test: ["CMD", "vault", "status"]
      interval: 10s
      timeout: 3s
      retries: 3

  vault-init:
    image: hashicorp/vault:1.17
    depends_on:
      vault:
        condition: service_healthy
    volumes:
      - ./vault-data:/vault/data
      - ./init.sh:/init.sh:ro
    entrypoint: ["sh", "/init.sh"]

  secret-init:
    image: curlimages/curl:latest
    depends_on:
      vault:
        condition: service_healthy
    environment:
      VAULT_ADDR: "http://vault:8200"
      VAULT_TOKEN: "${VAULT_TOKEN}"
    command: >
      sh -c "
        curl -sf -X POST \
          -H \"X-Vault-Token: $$VAULT_TOKEN\" \
          http://vault:8200/v1/auth/approle/role/myapp/role-id \
          | jq -r '.data.role_id' > /shared/role_id &&
        curl -sf -X POST \
          -H \"X-Vault-Token: $$VAULT_TOKEN\" \
          http://vault:8200/v1/auth/approle/role/myapp/secret-id \
          | jq -r '.data.secret_id' > /shared/secret_id
      "
    volumes:
      - shared-secrets:/shared

  vault-agent:
    image: hashicorp/vault:1.17
    depends_on:
      secret-init:
        condition: service_completed_successfully
    volumes:
      - ./vault-agent.hcl:/vault/config/agent.hcl:ro
      - ./templates:/vault/templates:ro
      - shared-secrets:/shared:ro
      - app-secrets:/app/config
    command: agent -config=/vault/config/agent.hcl -log-level=warn

  myapp:
    image: myapp:latest
    depends_on:
      vault-agent:
        condition: service_started
    volumes:
      - app-secrets:/app/config:ro

volumes:
  vault-data:
  shared-secrets:
  app-secrets:
```

**init.sh** — скрипт, который инициализирует Vault, создаёт AppRole, секреты:

```bash
#!/bin/sh
set -e

# Проверяем, инициализирован ли Vault
STATUS=$(vault status -format=json 2>/dev/null || echo '{"initialized":false}')
INITIALIZED=$(echo "$STATUS" | jq -r '.initialized')

if [ "$INITIALIZED" != "true" ]; then
  # Инициализируем
  vault operator init -key-shares=5 -key-threshold=3 \
    -format=json > /vault/data/init.json

  # Извлекаем root token
  ROOT_TOKEN=$(cat /vault/data/init.json | jq -r '.root_token')

  # Распечатываем
  for i in $(seq 1 5); do
    KEY=$(cat /vault/data/init.json | jq -r ".unseal_keys_b64[$((i-1))]")
    echo "Unseal Key $i: $KEY"
  done
  echo "Root Token: $ROOT_TOKEN"

  # Unseal
  for i in $(seq 1 3); do
    KEY=$(cat /vault/data/init.json | jq -r ".unseal_keys_b64[$((i-1))]")
    vault operator unseal "$KEY"
  done

  # Login
  vault login "$ROOT_TOKEN"

  # Включаем KV v2
  vault secrets enable -path=secret kv-v2

  # Создаём секрет
  vault kv put secret/production/myapp/database \
    host="postgres-primary.internal" \
    username="myapp_user" \
    password="$(openssl rand -base64 32)"

  # Включаем AppRole
  vault auth enable approle

  # Создаём роль
  vault write auth/approle/role/myapp \
    secret_id_ttl=0 \
    token_ttl=1h \
    token_max_ttl=24h \
    policies=myapp-policy

  # Политика
  vault policy write myapp-policy - <<EOF
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}
EOF

  echo "Init complete"
else
  echo "Vault already initialized"

  # Unseal если засилился
  SEALED=$(vault status -format=json | jq -r '.sealed')
  if [ "$SEALED" = "true" ]; then
    for i in $(seq 1 3); do
      KEY=$(cat /vault/data/init.json | jq -r ".unseal_keys_b64[$((i-1))]")
      vault operator unseal "$KEY"
    done
  fi
fi
```

> **Dev vs Production:** скрипт `init.sh` выше — **только для dev/демо**. В production:
> - Инициализация и unseal делаются отдельно (не в Compose).
> - Unseal keys хранятся в менеджере паролей, а не в томе `vault-data`.
> - Auto-unseal (Transit/AWS KMS) вместо ручного unseal.
> - AppRole secret_id генерируется через wrapping token, а не передаётся в открытом виде.

---

## 7. Проверка работоспособности

### 7.1. Healthcheck

```bash
# Статус Vault
docker compose exec vault vault status

# Проверка storage
docker compose exec vault vault operator raft list-peers

# Чтение секретов через Agent
docker compose exec myapp cat /app/config/database.env
```

### 7.2. Логи

```bash
# Vault
docker compose logs vault -f

# Vault Agent
docker compose logs vault-agent -f

# Проверка, что Agent получил токен
docker compose exec vault-agent cat /vault/token
```

### 7.3. Резервное копирование Raft

```bash
# Создание снапшота Raft
docker compose exec vault vault operator raft snapshot save /tmp/vault.snap
docker compose cp vault:/tmp/vault.snap ./backup/

# Восстановление из снапшота
docker compose cp ./backup/vault.snap vault:/tmp/vault.snap
docker compose exec vault vault operator raft snapshot restore /tmp/vault.snap
```

> ☠️ **Осторожно:** восстановление снапшота **перезаписывает** всё состояние Vault. Убедитесь, что вы восстанавливаете правильный снапшот, и у вас есть backup текущего состояния перед восстановлением.

---

## Типичные ошибки

- ❌ **`vault operator init` дважды** — Vault уже инициализирован, команда вернёт ошибку. Проверяйте статус перед инициализацией: `vault status | grep Initialized`.

- ❌ **Хранение unseal keys в том же Docker Compose** — если злоумышленник получит доступ к серверу, он найдёт ключи рядом с Vault. Храните ключи в отдельном менеджере паролей (1Password, Vault Enterprise), разделите между разными людьми.

- ❌ **`disable_mlock = true` отсутствует** — в Docker контейнер не имеет доступа к `mlock` syscall, Vault упадёт с ошибкой `seal: failed to lock memory`. Всегда добавляйте `disable_mlock = true` в конфиг для Docker.

- ❌ **Не настроен healthcheck** — сервисы, зависящие от Vault, могут стартовать до того, как Vault готов. Используйте healthcheck с `depends_on: condition: service_healthy`.

- ❌ **Порт 8200 доступен извне без TLS** — в production Vault должен быть доступен только через HTTPS. Используйте reverse proxy (nginx, Traefik) или настройте TLS напрямую в Vault.

- ❌ **Raft cluster из одной ноды без HA** — при падении контейнера или сервера Vault будет недоступен до восстановления. Для production используйте 3 или 5 нод Raft.

- ❌ **Забыли `cap_add: [IPC_LOCK]`** — Vault не сможет защитить память от swap. Добавьте capability, иначе предупреждение `WARNING! mlock is not supported`.

- ❌ **Игнорирование `api_addr` и `cluster_addr`** — в Docker Compose Vault не знает свой внешний адрес. Без этих параметров Raft кластер не сможет корректно общаться между нодами.

---

## Чек-лист

- [ ] Storage backend настроен на Raft с указанием `path`, `node_id` и (для кластера) `retry_join`. Vault переживает перезапуск контейнера.
- [ ] Unseal keys и root token сохранены в надёжном месте (менеджер паролей, не в томе Docker Compose). Выполнен unseal (ручной или auto-unseal).
- [ ] В Docker Compose настроен healthcheck для Vault, другие сервисы используют `depends_on: condition: service_healthy`.
- [ ] В production настроен TLS (сертификат и ключ монтируются, `tls_disable` отсутствует), настроен auto-unseal вместо ручного.

---

## Попробуйте сами

1. **Запустите Vault с Raft storage в Docker Compose.** Напишите `vault-config.hcl` с Raft backend (path `/vault/data`, node_id `vault-1`) и `docker-compose.yml` с одним сервисом vault. Запустите, выполните `vault operator init` и unseal тремя ключами. Убедитесь, что `vault status` показывает `Sealed: false`. Выключите контейнер (`docker compose down`) и поднимите снова — данные должны сохраниться.

2. **Настройте кластер из трёх нод Raft.** Создайте конфиги для трёх нод Vault (vault-1, vault-2, vault-3) с разными `node_id` и `retry_join`, указывающими на всех членов кластера. Запустите все три ноды в Docker Compose. Инициализируйте vault-1, выполните unseal трёх нод. Подключите vault-2 и vault-3 к кластеру: `vault operator raft join http://vault-1:8200`. Проверьте: `vault operator raft list-peers`.

3. **Добавьте Vault Agent в стек.** Дополните docker-compose.yml файл из задания 1 сервисами `secret-init` (генерирует role_id и secret_id), `vault-agent` (рендерит шаблон с секретом) и `myapp` (читает файл из общего volume). Напишите скрипт `init.sh`, который инициализирует Vault, включает AppRole, создаёт политику и секреты. Убедитесь, что после `docker compose up` приложение получает рабочую конфигурацию из Vault без хранения credentials.
