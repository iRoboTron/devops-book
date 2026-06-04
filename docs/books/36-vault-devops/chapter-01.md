# Глава 1: Установка и первый запуск

## Что вы узнаете

- Как запустить Vault в dev-режиме.
- Как запустить Vault в Docker и Docker Compose.
- Разницу между dev и production.
- Основные переменные окружения.
- Первые операции: записать и прочитать секрет.

---

## Архитектура Vault

Прежде чем запускать, полезно понимать как Vault устроен внутри:

```
┌────────────────────────────────────────────────────────────┐
│                       Vault Server                         │
│  ┌──────────────────────┐   ┌───────────────────────────┐  │
│  │    Auth Methods      │   │     Secrets Engines        │  │
│  │  ┌────────────────┐  │   │  ┌─────────────────────┐  │  │
│  │  │ Token          │  │   │  │ KV v2               │  │  │
│  │  │ AppRole        │  │   │  │ Database (dynamic)   │  │  │
│  │  │ Kubernetes     │  │   │  │ PKI (certificates)   │  │  │
│  │  │ LDAP / OIDC    │  │   │  │ Transit (encryption) │  │  │
│  │  │ GitHub         │  │   │  │ AWS / Azure / GCP    │  │  │
│  │  └──────┬─────────┘  │   │  └──────────┬──────────┘  │  │
│  └─────────┼────────────┘   └─────────────┼────────────┘  │
│  ┌─────────▼──────────────────────────────▼──────────────┐│
│  │                  Core (Policies + Audit)               ││
│  │  ┌─────────────┐  ┌────────────┐  ┌───────────────┐  ││
│  │  │ ACL Policies│  │ Audit Log  │  │  Lease/TTL    │  ││
│  │  └─────────────┘  └────────────┘  └───────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌──────────────────────▼────────────────────────────────┐  │
│  │                   Storage Backend                      │  │
│  │  ┌─────────────────────────────────────────────────┐   │  │
│  │  │              Raft (Integrated)                  │   │  │
│  │  │         Consul / File / Postgres                │   │  │
│  │  └─────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

**Ключевые компоненты:**

| Компонент | Что делает |
|---|---|
| Auth Methods | Проверяют кто пришёл: токен, ldap, k8s service account |
| Secrets Engines | Хранят и генерируют секреты: static (KV), dynamic (DB), PKI |
| Core | Применяет политики, пишет audit log, управляет временем жизни |
| Storage Backend | Где Vault хранит данные: Raft (встроенный), Consul, файл |

---

## 1. Dev-режим

> ☠️ **Осторожно:** dev-режим хранит все данные в памяти. После остановки процесса секреты исчезают. **Никогда не используйте dev-режим для реальных секретов.** Он предназначен исключительно для ознакомления и тестов.

### Установка Vault

Добавьте официальный репозиторий HashiCorp:

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update && sudo apt install vault -y
```

Проверьте установку:

```bash
vault --version
# Vault v1.18.x ...
```

### Запуск dev-сервера

```bash
vault server -dev -dev-root-token-id=root
```

Vault запустится, вы увидите:

```
You may need to set the following environment variables:

    export VAULT_ADDR='http://127.0.0.1:8200'

The unseal key and root token are displayed below in case you want to
seal/unseal the Vault or re-authenticate.

Unseal Key: <key>
Root Token: root
```

### Настроить окружение и проверить

Откройте второй терминал (или экспортируйте в том же):

```bash
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

vault status
```

Вывод `vault status`:

| Поле | В dev-режиме | Значение |
|---|---|---|
| Seal Type | shamir | Тип распечатывания |
| Initialized | true | Хранилище инициализировано |
| Sealed | false | **Распечатано** — можно работать |
| Version | 1.18.x | Версия Vault |
| HA Enabled | true | Режим высокой доступности |
| Cluster Name | vault-cluster-... | Имя кластера |

> **Dev vs Production:** в dev-режиме Vault стартует уже инициализированным и распечатанным. В production вы должны явно выполнить `vault operator init` и `vault operator unseal`. В dev-режиме **нет кластеризации** (HA Enabled, но только один узел).

---

## 2. Запуск в Docker

```bash
docker run -d --name vault -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=root' \
  -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
  hashicorp/vault:1.17
```

Проверьте:

```bash
docker logs vault 2>&1 | grep -i "root token"
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'
docker exec vault vault status
```

> **Dev vs Production:** тот же dev-режим, только в контейнере. Все ограничения сохраняются. Для production используйте `server -config=/vault/config/vault.json` с настроенным storage backend.

---

## 3. Docker Compose для разработки

```yaml
# docker-compose.yml
services:
  vault:
    image: hashicorp/vault:1.17
    container_name: vault
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: root
      VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
    cap_add:
      - IPC_LOCK
    command: server -dev
```

Запуск:

```bash
docker compose up -d
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'
vault status
```

**Зачем `IPC_LOCK`:** Vault использует `mlock()` чтобы страницы памяти с секретами не ушли в swap. Без этого Vault при запуске выдаст предупреждение:

```
WARNING! mlock is not supported on this system!
```

> **Dev vs Production:** `IPC_LOCK` обязателен в production. В dev-режиме Vault всё равно работает, но выбрасывает предупреждение. Для production используйте `--cap-add=IPC_LOCK` или настройте `limit: memlock`.

---

## 4. Первые операции

### Записать секрет

```bash
vault kv put secret/myapp/database \
  username="appuser" \
  password="S3cr3tP@ss"
```

Вывод: `Key                Value` — подтверждение записи.

### Прочитать секрет

```bash
vault kv get secret/myapp/database
```

Вывод:

```
====== Data ======
Key         Value
username    appuser
password    S3cr3tP@ss
```

### Прочитать одно поле

```bash
vault kv get -field=password secret/myapp/database
# S3cr3tP@ss
```

Удобно для подстановки в скрипты:

```bash
export DB_PASSWORD=$(vault kv get -field=password secret/myapp/database)
```

### Прочитать в JSON

```bash
vault kv get -format=json secret/myapp/database | python3 -m json.tool
```

```json
{
  "data": {
    "data": {
      "password": "S3cr3tP@ss",
      "username": "appuser"
    }
  }
}
```

### Удалить секрет

```bash
vault kv delete secret/myapp/database
```

> **Dev vs Production:** в dev нет версионирования KV v2 — удалили и всё. В production с KV v2 можно откатить: `vault kv undelete -versions=1 secret/myapp/database`.

---

## 5. Переменные окружения

Vault активно использует переменные окружения — это основной способ конфигурации клиента.

| Переменная | Назначение | Пример |
|---|---|---|
| `VAULT_ADDR` | Адрес Vault-сервера | `http://127.0.0.1:8200` |
| `VAULT_TOKEN` | Токен аутентификации | `root` / `hvs.abc123...` |
| `VAULT_CACERT` | Путь к CA-сертификату (TLS) | `/etc/vault/ca.crt` |
| `VAULT_SKIP_VERIFY` | Отключить проверку TLS (только dev!) | `true` |
| `VAULT_FORMAT` | Формат вывода по умолчанию | `table` / `json` / `yaml` |
| `VAULT_NAMESPACE` | Namespace (Vault Enterprise) | `admin/prod` |
| `VAULT_CLIENT_TIMEOUT` | Таймаут запроса | `30s` |
| `VAULT_MAX_RETRIES` | Число повторов при ошибке | `3` |

```bash
# Пример: всё в одной строке
VAULT_ADDR='http://127.0.0.1:8200' VAULT_TOKEN='root' \
  vault kv get secret/myapp/database
```

> **Dev vs Production:** в production `VAULT_SKIP_VERIFY` никогда не ставьте в `true`. Всегда используйте `VAULT_CACERT` с валидным TLS-сертификатом. В dev HTTP без TLS — это нормально.

---

## 6. Web UI

Vault поставляется со встроенным веб-интерфейсом.

1. Откройте `http://localhost:8200/ui`.
2. Введите Token: `root`.
3. Вы увидите дашборд — список включенных secrets engines.

Из UI можно:
- Создавать, читать, обновлять, удалять секреты.
- Включать/отключать secrets engines.
- Смотреть политики и токены.
- Просматривать audit log (если включён).

> **Dev vs Production:** UI одинаков в dev и production. Разница только в доступе: в production UI обычно скрывают за VPN или SSO.

---

## Типичные ошибки

- ❌ **`connection refused`** — забыли `export VAULT_ADDR`. По умолчанию Vault CLI пытается соединиться с `https://127.0.0.1:8200` (HTTPS!). Dev-режим слушает HTTP. Проверьте: `echo $VAULT_ADDR`.
- ❌ **`Code: 403. Errors: permission denied`** — нет токена или токен недействителен. Проверьте: `echo $VAULT_TOKEN`. Недействителен? Экспортируйте заново.
- ❌ **`Code: 404. Errors: no value found`** — перепутали KV v1 и KV v2. В KV v2 секреты лежат по пути `secret/data/myapp/database`, а не `secret/myapp/database`. CLI сам следит за этим, но в API — разница.
- ❌ **Запустили dev, а секреты «пропали»** — dev-режим хранит всё в памяти. Перезапуск = потеря данных. Это не баг.
- ❌ **Пропустили `IPC_LOCK`** — в production без него секреты могут уйти в swap на диск.

---

## Чек-лист

- [ ] Vault установлен: `vault --version` показывает версию.
- [ ] Dev-сервер запущен: `vault status` показывает `Sealed: false`.
- [ ] Переменные окружения установлены: `echo $VAULT_ADDR` и `echo $VAULT_TOKEN`.
- [ ] Первый секрет записан и прочитан: `vault kv put` → `vault kv get`.

---

## Попробуйте сами

1. **Запустите Vault в Docker Compose** (скопируйте docker-compose.yml выше), запишите секрет и прочитайте его. Остановите `docker compose down`, запустите снова — убедитесь что секрет исчез.
2. **Поэкспериментируйте с форматами вывода:** выполните `vault kv get -format=json` и `vault kv get -format=yaml`. Сравните. Какой из них проще парсить скриптом?
3. **Попробуйте Web UI:** откройте `http://localhost:8200/ui`, войдите с root-токеном, создайте секрет через GUI, потом прочитайте его через CLI. Убедитесь что данные совпадают.
