# Глава 8: Vault Agent — автоматическое получение секретов

## Что вы узнаете

- Что такое Vault Agent и зачем он нужен.
- Как Agent рендерит шаблоны конфигурации с секретами.
- Автообновление токена и секретов при их ротации.
- Запуск Vault Agent как sidecar в Docker.
- Как приложение не знает о Vault — читает секреты из обычного файла, а Agent ведёт всю работу.

---

## 1. Проблема прямой интеграции

Без Vault Agent каждое приложение должно:

1. Аутентифицироваться в Vault (AppRole, Kubernetes, JWT...).
2. Получить токен.
3. Периодически продлевать токен (renew).
4. Читать секреты.
5. Следить за изменениями секретов (watch/re-read).
6. Обрабатывать ошибки Vault (unavailable, reconnection).

Это десятки строк кода в каждом микросервисе — дублирование, которое сложно поддерживать.

| Аспект | Без Agent | С Agent |
|---|---|---|
| Интеграция | Каждое приложение использует Vault API | Приложение ничего не знает о Vault |
| Аутентификация | В коде приложения (AppRole login) | В конфиге Agent (один раз) |
| Renew token | В коде (фоновый поток) | Agent делает автоматически |
| Чтение секретов | `client.read("secret/data/...")` | Consul-template рендерит файл |
| Обновление при изменении | Watch + callback в коде | Agent отправляет SIGHUP |
| Ошибки Vault | Retry/logic в приложении | Agent retry встроен |
| Тестирование | Нужен Vault в тестах | Мокаем файл конфигурации |

```
Без Agent:

  ┌─────────────────────┐
  │      myapp          │
  │  ┌───────────────┐  │
  │  │ vault login   │  │
  │  │ token renew   │  │     ┌─────┐
  │  │ read secrets  │──┼────►│Vault│
  │  │ watch changes │  │     └─────┘
  │  │ error retry   │  │
  │  └───────────────┘  │
  └─────────────────────┘

  Приложение = бизнес-логика + Vault-логика (дублируется везде)

С Agent:

  ┌─────────┐   render   ┌──────────────┐   read    ┌──────┐
  │  Agent  │───────────►│  config file  │◄──────────│myapp │
  │ (sidecar)│           │ database.env  │           │      │
  └────┬────┘           └──────────────┘           └──────┘
       │                                                   │
       │  auth/login                                       │
       │  token renew     ┌─────┐                          │
       └─────────────────►│Vault│                          │
                          └─────┘                          │
       Приложение читает обычный файл, ничего не знает о Vault
```

> **Dev vs Production:** в dev можно запускать Agent с `-log-level=debug` и `remove_secret_id_file_after_reading=false` для отладки. В production Agent должен быть minimal — только конфиг, никакого интерактива.

---

## 2. Конфигурация Vault Agent

### 2.1. Базовая конфигурация

```hcl
# vault-agent.hcl
vault {
  address = "http://vault:8200"
}
```

### 2.2. Автоматическая аутентификация (auto_auth)

```hcl
auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/vault/role_id"
      secret_id_file_path = "/vault/secret_id"
      remove_secret_id_file_after_reading = true
    }
  }

  sink "file" {
    config = {
      path = "/vault/token"
    }
  }
}
```

| Параметр | Описание |
|---|---|
| `role_id_file_path` | Путь к файлу с Role ID |
| `secret_id_file_path` | Путь к файлу с Secret ID |
| `remove_secret_id_file_after_reading` | Удалить Secret ID после первого чтения (безопасность) |
| `sink` | Куда сохранять полученный токен |

```
Процесс аутентификации:

  1. Agent читает role_id из /vault/role_id
  2. Agent читает secret_id из /vault/secret_id
  3. Agent выполняет AppRole login:
       vault write auth/approle/login \
         role_id="..." secret_id="..."
  4. Получает token → сохраняет в /vault/token (sink)
  5. Удаляет secret_id файл (если включено)
  6. Периодически renew токен (автоматически)
```

> ☠️ **Осторожно:** `remove_secret_id_file_after_reading=true` — это безопасно, но если контейнер перезапустится, Agent не сможет залогиниться снова, потому что secret_id файла больше нет. В таком случае нужно:
> - Либо перевыпускать secret_id через Vault API при старте контейнера.
> - Либо использовать wrapping token (`-wrap-ttl`) — однократный токен для login.
> - Либо не удалять файл (но это риск безопасности).

### 2.3. Кэширование

```hcl
cache {
  use_auto_auth_token = true
}
```

Agent может работать как прокси-кэш: приложения обращаются к Agent вместо Vault, Agent отдаёт закэшированные секреты или шлёт запрос в Vault.

```hcl
listener "tcp" {
  address = "127.0.0.1:8007"
  tls_disable = true
}
```

Теперь приложения могут обращаться к `http://127.0.0.1:8007` вместо `http://vault:8200`. Agent автоматически подставляет токен.

```
┌─────────────────┐
│    Pod/Host     │
│                 │
│  ┌─────────┐   │  read secret   ┌──────┐
│  │  Agent  │◄──┼───────────────►│myapp │
│  │:8007    │   │                │      │
│  └────┬────┘   │                └──────┘
│       │        │
│       │ proxy  │
│  ┌────▼────┐   │
│  │ Vault   │   │
│  │:8200    │   │
│  └─────────┘   │
└─────────────────┘
```

### 2.4. Template rendering (Consul-Template)

```hcl
template {
  source = "/vault/templates/app-config.tpl"
  destination = "/app/config/database.env"
  perms = "0640"

  exec {
    command = ["sh", "-c", "pkill -HUP myapp || true"]
  }
}
```

| Параметр | Описание |
|---|---|
| `source` | Путь к шаблону (Consul Template format) |
| `destination` | Выходной файл — туда Agent запишет результат |
| `perms` | Права на выходной файл |
| `exec` | Команда, которая выполняется после рендера (обычно — перезагрузка приложения) |

```
Жизненный цикл шаблона:

  1. Agent запускается, логинится в Vault
  2. Читает secret по пути из шаблона
  3. Рендерит шаблон → записывает в destination
  4. Запускает exec (если указан)
  5. Периодически перечитывает секрет:
       - Если изменился → ререндер + exec
       - Если не изменился → ничего
  6. При завершении Agent: файл остаётся (последняя версия)
```

### 2.5. Полная конфигурация Agent

```hcl
# vault-agent.hcl
vault {
  address = "http://vault:8200"
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/vault/role_id"
      secret_id_file_path = "/vault/secret_id"
      remove_secret_id_file_after_reading = true
    }
  }

  sink "file" {
    config = {
      path = "/vault/token"
    }
  }
}

cache {
  use_auto_auth_token = true
}

listener "tcp" {
  address = "127.0.0.1:8007"
  tls_disable = true
}

template {
  source = "/vault/templates/app-config.tpl"
  destination = "/app/config/database.env"
  perms = "0640"

  exec {
    command = ["sh", "-c", "pkill -HUP myapp || true"]
  }
}

template {
  source = "/vault/templates/tls.tpl"
  destination = "/etc/ssl/certs/myapp.crt"
  perms = "0644"

  exec {
    command = ["sh", "-c", "nginx -s reload || true"]
  }
}

# Шаблон без exec — просто файл с конфигом
template {
  source = "/vault/templates/features.tpl"
  destination = "/app/config/features.yaml"
  perms = "0644"
}
```

> **Dev vs Production:** в dev можно использовать `remove_secret_id_file_after_reading=false` для упрощения рестартов. В production — `true` + wrapping token или init-контейнер для подготовки secret_id.

---

## 3. Шаблоны Consul-Template

### 3.1. Базовый шаблон KV v2

```
{{ with secret "secret/data/production/myapp/database" }}
DATABASE_HOST={{ .Data.data.host }}
DATABASE_USER={{ .Data.data.username }}
DATABASE_PASS={{ .Data.data.password }}
{{ end }}
```

После рендера (destination = `/app/config/database.env`):

```
DATABASE_HOST=postgres-primary.internal
DATABASE_USER=myapp_user
DATABASE_PASS=8f9a2b3c...
```

### 3.2. Шаблон с PKI-сертификатом

```
{{ with secret "pki_int/issue/internal-services" "common_name=myapp.internal.example.com" "ttl=24h" }}
{{ .Data.certificate }}

{{ .Data.issuing_ca }}

{{ .Data.private_key }}
{{ end }}
```

### 3.3. Шаблон с Dynamic Secrets

```
{{ with secret "database/creds/myapp-readonly" }}
DATABASE_USER={{ .Data.username }}
DATABASE_PASS={{ .Data.password }}
{{ end }}
```

### 3.4. Шаблон с JSON

```json
{{ with secret "secret/data/production/myapp/config" }}
{
  "host": "{{ .Data.data.host }}",
  "port": {{ .Data.data.port }},
  "debug": {{ .Data.data.debug | toJSON }},
  "features": {{ .Data.data.features | toJSONPretty }}
}
{{ end }}
```

### 3.5. Шаблон с несколькими секретами

```
{{ with secret "secret/data/production/myapp/database" }}
DATABASE_HOST={{ .Data.data.host }}
DATABASE_NAME={{ .Data.data.name }}
{{ end }}
{{ with secret "secret/data/production/myapp/redis" }}
REDIS_HOST={{ .Data.data.host }}
REDIS_PORT={{ .Data.data.port }}
{{ end }}
```

### 3.6. Условные шаблоны

```
{{ with secret "secret/data/production/myapp/features" }}
{{ if .Data.data.enable_payments }}
PAYMENTS_API_KEY={{ with secret "secret/data/production/payments/api-key" }}{{ .Data.data.key }}{{ end }}
PAYMENTS_ENABLED=true
{{ else }}
PAYMENTS_ENABLED=false
{{ end }}
{{ end }}
```

### 3.7. Запуск Agent

```bash
vault agent -config=vault-agent.hcl
```

Для production:

```bash
vault agent -config=vault-agent.hcl -log-level=warn
```

### 3.8. Проверка рендера

Если Agent запущен, но файл не появился:

```bash
# Проверить логи Agent
journalctl -u vault-agent --no-pager | tail -20

# Проверить права на секрет
vault token capabilities secret/data/production/myapp/database

# Проверить, что шаблон валидный
vault agent -config=vault-agent.hcl -log-level=debug 2>&1 | grep -i template
```

---

## 4. Vault Agent в Docker

### 4.1. Docker Compose с Agent sidecar

```yaml
services:
  vault-agent:
    image: hashicorp/vault:1.17
    command: agent -config=/vault/config/agent.hcl -log-level=warn
    volumes:
      - ./vault-agent.hcl:/vault/config/agent.hcl:ro
      - ./role_id:/vault/role_id:ro
      - ./secret_id:/vault/secret_id:ro
      - ./templates:/vault/templates:ro
      - secrets-vol:/app/config
    restart: unless-stopped
    depends_on:
      vault:
        condition: service_healthy

  myapp:
    image: myapp:latest
    volumes:
      - secrets-vol:/app/config:ro
    depends_on:
      vault-agent:
        condition: service_started

volumes:
  secrets-vol:
```

### 4.2. Структура директорий

```
project/
├── docker-compose.yml
├── vault-agent.hcl          # конфиг Agent
├── role_id                  # role_id для AppRole (генеруется)
├── secret_id                # secret_id для AppRole (генеруется)
├── templates/
│   ├── app-config.tpl       # шаблон конфига
│   └── tls.tpl              # шаблон TLS-сертификата
└── vault/
    └── config/
        └── vault-config.hcl # конфиг самого Vault
```

### 4.3. Init-контейнер для secret_id

Проблема: `remove_secret_id_file_after_reading=true` — при рестарте нужен новый secret_id. Решение — init-контейнер, который создаёт secret_id через Vault API:

```yaml
services:
  secret-init:
    image: curlimages/curl:latest
    command: >
      sh -c "
        secret_id=\$(curl -sf --header \"X-Vault-Token: \$VAULT_ADMIN_TOKEN\" \
          --request POST \
          http://vault:8200/v1/auth/approle/role/myapp/secret-id \
          | jq -r '.data.secret_id') &&
        echo \"\$secret_id\" > /vault/secret_id
      "
    volumes:
      - secrets-vol:/vault
    environment:
      VAULT_ADMIN_TOKEN: "${VAULT_ADMIN_TOKEN}"
    depends_on:
      vault:
        condition: service_healthy

  vault-agent:
    image: hashicorp/vault:1.17
    command: agent -config=/vault/config/agent.hcl
    volumes:
      - ./vault-agent.hcl:/vault/config/agent.hcl:ro
      - ./role_id:/vault/role_id:ro
      - secrets-vol:/vault/secret_id:ro  # от init-контейнера
      - ./templates:/vault/templates:ro
      - secrets-vol:/app/config
    depends_on:
      secret-init:
        condition: service_completed_successfully
```

> ☠️ **Осторожно:** если secret_id истекает (TTL), Agent не сможет перелогиниться. Настройте `secret_id_ttl` в AppRole на достаточный срок (или `0` для бесконечного) в production:

```bash
vault write auth/approle/role/myapp \
  secret_id_ttl=0 \
  token_ttl=1h \
  token_max_ttl=24h
```

### 4.4. Dockerfile с Agent в одном контейнере

Для простых случаев Agent можно запустить в том же контейнере, что и приложение:

```dockerfile
FROM hashicorp/vault:1.17 AS vault
FROM myapp:latest AS app

COPY --from=vault /bin/vault /usr/local/bin/vault
COPY vault-agent.hcl /etc/vault-agent.hcl
COPY templates/ /vault/templates/

CMD ["sh", "-c", "vault agent -config=/etc/vault-agent.hcl & exec myapp"]
```

Но лучше — отдельный sidecar. Так приложение можно обновлять независимо от Agent.

> **Dev vs Production:** dev — можно запускать Agent в том же контейнере для простоты. Production — всегда sidecar (отдельный контейнер), чтобы не смешивать логику обновления.

---

## 5. Vault Agent с Kubernetes (Sidecar)

### 5.1. Sidecar через annotations

С Vault Agent Injector — mutating webhook, который автоматически добавляет Agent в pod:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: myapp
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "myapp"
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/production/myapp/database"
        vault.hashicorp.com/agent-inject-template-config: |
          {{- with secret "secret/data/production/myapp/database" -}}
          DATABASE_HOST={{ .Data.data.host }}
          DATABASE_USER={{ .Data.data.username }}
          DATABASE_PASS={{ .Data.data.password }}
          {{- end -}}
    spec:
      containers:
        - name: myapp
          image: myapp:latest
          volumeMounts:
            - name: secrets
              mountPath: /vault/secrets
      volumes:
        - name: secrets
          emptyDir: {}
```

### 5.2. Что делает injector

```
1. Пользователь создаёт Deployment с аннотациями
2. MutatingWebhookInjector перехватывает создание pod
3. Добавляет init-контейнер vault-agent-injector — логинится в Vault
4. Добавляет sidecar vault-agent — рендерит шаблоны
5. Монтирует emptyDir с секретами в оба контейнера
6. Приложение читает /vault/secrets/* как обычные файлы
```

---

## 6. Vault Agent Systemd (хост)

Для bare-metal / VM — Agent как systemd service:

```ini
# /etc/systemd/system/vault-agent.service
[Unit]
Description=Vault Agent
Requires=vault.service
After=vault.service

[Service]
ExecStart=/usr/bin/vault agent -config=/etc/vault-agent.d/agent.hcl
Restart=always
RestartSec=10
User=vault
Group=vault

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable vault-agent
sudo systemctl start vault-agent
sudo journalctl -u vault-agent -f
```

---

## Типичные ошибки

- ❌ **Agent без прав на секрет** — шаблон не рендерится, Agent пишет ошибку `permission denied` в лог. Проверьте политику AppRole: роль должна иметь read-доступ к пути из шаблона.

- ❌ **`remove_secret_id_file_after_reading=true` и рестарт** — при рестарте контейнера secret_id файла больше нет, Agent не может залогиниться. Решение: init-контейнер или wrapping token, или `secret_id_ttl=0` + хранение файла (меньшая безопасность).

- ❌ **Шаблон не изменился — exec не запускается** — это **фича**, а не баг. Agent выполняет `exec` только когда содержимое destination изменилось. Если нужно принудительно перезапускать приложение при каждом рендере — добавьте таймстемп в шаблон.

- ❌ **Agent не может подключиться к Vault** — если Vault недоступен при старте Agent, он будет retry, но destination файл не появится. Убедитесь, что Vault доступен по `address` из конфига и health-чек проходит.

- ❌ **Не настроен `sink`** — токен аутентификации не сохраняется, Agent не может использовать `use_auto_auth_token`. Всегда указывайте `sink "file"` для сохранения токена.

- ❌ **Agent и приложение на разных машинах** — если Agent работает sidecar (в Kubernetes или Docker Compose), секреты передаются через volume. Если на разных машинах — нужно использовать общее файловое хранилище (NFS, EFS) или Agent Proxy с listener.

- ❌ **Permission denied на destination файл** — Agent пишет с правами `perms`, но директория может быть недоступна для пользователя vault. Убедитесь, что пользователь vault (или root) имеет права на запись в destination-директорию.

- ❌ **Один Agent на несколько приложений** — если разные приложения используют один Agent, они получают один и тот же token. Приложение A может прочитать секреты приложения B. В production — каждому приложению свой Agent со своей AppRole и политикой.

---

## Чек-лист

- [ ] Я настроил AppRole с политикой, которая даёт доступ только к необходимым секретам для конкретного приложения.
- [ ] Vault Agent использует `sink` для сохранения токена и `use_auto_auth_token` для последующих запросов.
- [ ] Все шаблоны Consul-Template проверены: `vault agent -config=... -log-level=debug` показывает `template rendered successfully`.
- [ ] В production настроен init-контейнер для генерации secret_id или используется wrapping token — при рестарте контейнера аутентификация не ломается.

---

## Попробуйте сами

1. **Запустите Vault Agent с AppRole.** Создайте AppRole `myapp` с политикой на чтение `secret/data/production/myapp/database`. Напишите `vault-agent.hcl` с `auto_auth` (метод `approle`), `sink` и одним шаблоном. Запустите Agent. Убедитесь, что destination файл создался с правильными данными из Vault.

2. **Протестируйте автообновление при изменении секрета.** Используя конфигурацию из шага 1, измените значение секрета в Vault (`vault put secret/data/production/myapp/database password=newpass`). Дождитесь, пока Agent перечитает секрет (по умолчанию — каждые 10 секунд). Проверьте, что destination файл обновился. Если в шаблоне указан `exec` с перезагрузкой приложения — убедитесь, что процесс получил SIGHUP.

3. **Запустите Vault Agent как sidecar в Docker Compose.** Напишите `docker-compose.yml` с сервисами `vault`, `vault-agent` (sidecar) и `myapp`. Agent аутентифицируется через AppRole, рендерит файл конфигурации в общий volume. `myapp` читает конфиг из volume. Убедитесь, что при рестарте `vault-agent` контейнера секреты пересоздаются, а `myapp` продолжает работать без перезапуска.
