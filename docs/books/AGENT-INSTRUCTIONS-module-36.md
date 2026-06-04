# Инструкция для ИИ-агента: Модуль 36 — HashiCorp Vault

> **Роль агента:** Ты — технический писатель и DevOps/Security-инженер с практическим опытом работы с секретами в продакшн-окружениях. Пишешь конкретно, без академизма, с реальными командами и выводами. Объясняешь не только «как», но и «зачем». Честно указываешь когда что-то избыточно для малых команд.

> **Это Модуль 36, книга части 4 "Прочее".**
> Предварительные требования: книга 03 (Docker), книга 10-11 (Kubernetes), книга 34 (Git).
> Читатель уверенно работает с Docker и K8s, разворачивает сервисы, но хранит секреты в `.env`-файлах, переменных окружения или прямо в коде.

---

## Контекст проекта

Читатель — DevOps-инженер у которого секреты «хранятся как-нибудь»:

- Пароли от БД в `docker-compose.yml` или `.env` который случайно попал в Git.
- API-ключи в переменных окружения CI/CD которые видны в логах.
- Сертификаты на серверах которые обновляются вручную раз в год.
- В K8s-манифестах `kind: Secret` с base64 который называется «шифрованием» но им не является.
- При уходе сотрудника непонятно к каким секретам он имел доступ.
- Ротация паролей — это «поменять вручную на 15 серверах».

**Что он хочет после книги:**
Развернуть Vault, положить в него секреты из `.env`-файлов, настроить AppRole для CI/CD и Kubernetes-авторизацию для подов. Понимать dynamic secrets и PKI. Знать как не потерять данные при перезапуске.

---

## Что за книга

**Название:** "HashiCorp Vault: секреты под контролем"

**Каталог:** `36-vault-devops`

**Место в курсе:** Книга 36, часть 4 "Прочее".

**Версии ПО:** Vault 1.17+ (OpenSource / Community Edition). Все примеры работают на бесплатной версии. Платные Enterprise-фичи упоминать только в одном абзаце в конце соответствующей главы с пометкой `[Enterprise]`.

**Объём:** 155–195 страниц.

**Формат файлов:** каждая глава — `chapter-XX.md`, приложения — `appendix-a.md`, `appendix-b.md`, `appendix-c.md`. Оглавление — `book.md`.

**Стиль:**
- Простой язык, без академизма.
- Каждая глава: «Что вы узнаете» → тело → «Типичные ошибки» → «Чек-лист» → «Попробуйте сами».
- Команды — с реальными выводами (обрезанными до сути).
- Mermaid-диаграммы для flows и архитектур, ASCII для топологий.
- Маркировка опасных операций: `> ☠️ **Осторожно:**`.
- Всегда указывать: dev-режим vs production. Dev-режим — для изучения, не для реальных данных.

---

## Правило маркировки опасных операций

```markdown
> ☠️ **Осторожно:** [что именно теряется/ломается и почему нельзя отменить]
```

Применять к:
- `vault operator init` — одноразовая операция, unseal keys нельзя восстановить
- `vault secrets disable path/` — удаляет ВСЕ секреты по этому пути
- `vault token revoke` — немедленный отзыв, приложения потеряют доступ
- потеря unseal keys + root token — Vault становится недоступен навсегда

---

## Антипаттерны подачи

**Плохо:** объяснять все опции команды `vault write` через `--help`.
**Хорошо:** показать конкретный рабочий пример с объяснением каждого флага.

**Плохо:** "Vault очень мощный инструмент с сотнями возможностей".
**Хорошо:** показать 20% возможностей которые покрывают 80% реальных задач.

**Плохо:** упоминать Consul без объяснения зачем он нужен и когда не нужен.
**Хорошо:** для одного сервера — Raft storage достаточно. Consul нужен только в особых случаях.

**Плохо:** давать конфигурацию HA без объяснения что произойдёт при потере ноды.
**Хорошо:** объяснить quorum, seal/unseal процедуру при рестарте.

---

## Правило: визуализация — не опционально

**Вставлять схемы, таблицы, Mermaid-диаграммы и графики везде где они поясняют материал лучше текста.**

- **Mermaid `sequenceDiagram` / `flowchart`** — для алгоритмов (AppRole login, K8s auth, seal/unseal), потоков данных, жизненных циклов.
- **ASCII-схемы** — для архитектуры Vault, топологии HA-кластера, расположения компонентов.
- **Таблицы** — для сравнения: auth methods, secrets engines, storage backends, политик, флагов команд.
- **Одна большая диаграмма** эффективнее двух страниц текста.
- **У каждой схемы — подпись** где разместить (`Разместить: секция "X" в главе Y`).

Схемы из секции «Обязательные схемы» — минимум. Добавлять свои где улучшают понимание.

---

## Обработка ошибок при выполнении команд

Каждая команда в книге должна сопровождаться указанием что делать если:
- Команда не найдена — `sudo apt install vault` / `brew install vault`
- Нет прав (Permission denied) — нужен `sudo` или не тот токен
- Вывод отличается от ожидаемого (другая версия, другая ОС)
- Команда не работает в dev-режиме (например Raft config без init)

Формат:
```markdown
# Если команда не найдена:
sudo apt install -y vault
```

---

## Обязательные схемы

**Схема 1 — Архитектура Vault** (Глава 1):

```text
┌────────────────────────────────────────────────────┐
│                    Vault Server                    │
│                                                    │
│  ┌──────────────┐   ┌──────────────────────────┐  │
│  │  Auth Methods│   │    Secrets Engines        │  │
│  │  - Token     │   │  - KV v2  (static)        │  │
│  │  - AppRole   │   │  - Database (dynamic)     │  │
│  │  - Kubernetes│   │  - PKI (certificates)     │  │
│  │  - LDAP      │   │  - AWS/GCP (cloud creds)  │  │
│  └──────┬───────┘   └──────────────────────────┘  │
│         │                        │                 │
│  ┌──────▼────────────────────────▼──────────────┐  │
│  │              Core (Policies + Audit)          │  │
│  └───────────────────────────────────────────────┘  │
│                        │                            │
│  ┌─────────────────────▼──────────────────────┐    │
│  │           Storage Backend (Raft / Consul)   │    │
│  └────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────┘
```
Разместить: начало главы 1.

**Схема 2 — Жизненный цикл секрета в Vault** (Глава 0):

```text
Без Vault:
секрет → .env файл → Git (случайно) → утечка
секрет → меняем вручную → обновляем 15 серверов → один забыли

С Vault:
секрет → vault kv put secret/app key=value
приложение → vault login → vault read secret/app → секрет в памяти
истёк lease → vault автоматически ротирует → приложение получает новый
уволился сотрудник → vault token revoke → доступ закрыт за секунду
```
Разместить: секция "Что меняет Vault" в главе 0.

**Схема 3 — AppRole flow** (Глава 5):

```mermaid
sequenceDiagram
    participant CI as CI/CD Pipeline
    participant V as Vault
    participant App as Application

    CI->>V: vault write auth/approle/login role_id=X secret_id=Y
    V-->>CI: token (TTL: 1h)
    CI->>App: передать token через env/file

    App->>V: vault kv get -token=TOKEN secret/myapp/db
    V-->>App: {"password": "s3cr3t"}

    Note over App,V: token истёк через 1h
    App->>V: обновить token (vault token renew)
```
Разместить: начало секции "AppRole" в главе 5.

**Схема 4 — Kubernetes Auth flow** (Глава 10):

```mermaid
sequenceDiagram
    participant Pod
    participant VA as Vault Agent (sidecar)
    participant V as Vault
    participant K as Kubernetes API

    Pod->>VA: запуск (init container)
    VA->>V: JWT токен из /var/run/secrets/...
    V->>K: проверить JWT (TokenReview)
    K-->>V: OK, namespace=prod, sa=myapp
    V-->>VA: Vault token (policy: myapp-policy)
    VA->>V: vault kv get secret/myapp
    V-->>VA: секреты
    VA->>Pod: записать в /vault/secrets/config
```
Разместить: начало главы 10.

**Схема 5 — Seal/Unseal** (Глава 11):

```text
Vault запустился / перезагрузился
        │
        ▼
   [SEALED] ← данные зашифрованы, ничего не работает
        │
        │  vault operator unseal <key-1>
        │  vault operator unseal <key-2>
        │  vault operator unseal <key-3>  (нужно threshold из N)
        ▼
  [UNSEALED] ← работает нормально
        │
        │  vault operator seal (вручную)
        │  или: сервер перезагрузился
        ▼
   [SEALED]
```
Разместить: секция "Seal и Unseal" в главе 11.

---

## Структура книги — детальное ТЗ по главам

---

### Глава 0: Зачем нужен Vault — проблема хранения секретов

**Что вы узнаете:**
- какие проблемы создаёт хранение секретов «как-нибудь»;
- что такое секрет и почему его нельзя хранить в Git или переменных окружения CI;
- какие задачи решает Vault и когда он избыточен;
- место Vault в DevOps-стеке.

**Цель:** читатель понимает не «что такое Vault», а «почему без него больно» и «что именно становится лучше».

**Темы:**

Раздел "Что такое секрет":
Перечислить конкретные примеры: пароль от PostgreSQL, API-ключ Stripe, приватный ключ TLS-сертификата, OAuth client secret, SSH-ключ, credentials облачного провайдера. Объяснить: секрет — это всё что при утечке даёт злоумышленнику доступ к системе или данным.

Раздел "Как секреты хранятся сейчас (и почему это плохо)":

Разобрать 4 типичных сценария:

```text
Сценарий 1: секреты в коде
DATABASE_URL = "postgresql://admin:S3cr3t@prod-db:5432/myapp"
→ попал в Git → попал в историю → попал к 10 разработчикам
→ один уволился — надо менять и везде обновлять

Сценарий 2: секреты в .env
.env забыт в .gitignore → git add . → коммит → GitHub
→ публичный репозиторий = немедленная утечка

Сценарий 3: секреты в переменных окружения CI/CD
- видны всем у кого есть доступ к CI-системе
- попадают в логи при ошибке: "Error connecting to postgresql://admin:S3cr3t@..."
- не ротируются: один пароль живёт годами

Сценарий 4: Kubernetes Secrets (base64)
kubectl get secret myapp-secret -o yaml
→ data.password: cGFzc3dvcmQ=  ← это не шифрование, это просто base64
→ base64 -d → "password"
→ любой с доступом к kubectl видит секреты
```

Разместить Схему 2 (жизненный цикл секрета).

Раздел "Что решает Vault":
```text
Проблема                          Решение Vault
────────────────────────────────────────────────────────────────
Секреты в Git                   → централизованное хранилище с шифрованием
Нет аудита кто читал что        → audit log каждого обращения
Ротация вручную                 → dynamic secrets (Vault сам генерирует и ротирует)
Долгоживущие пароли             → lease + автоматическое истечение
Нет контроля доступа            → policies: кто к чему имеет доступ
Уволился сотрудник              → revoke token → немедленный отзыв
TLS-сертификаты вручную         → PKI engine: автогенерация с нужным TTL
```

Раздел "Когда Vault избыточен":
Честно написать: для одного разработчика с одним проектом — Vault overhead. Для команды 2-3 человека с несколькими сервисами — уже полезен. Для CI/CD и K8s — практически обязателен. Альтернативы для маленьких проектов: `.env` + `git-crypt` / `sops`, GitHub/GitLab Secrets, AWS Secrets Manager.

**Типичные ошибки:**
- Vault — не замена `.env` для local development. Для разработки можно оставить `.env`, Vault нужен в staging/prod.
- Vault решает хранение и доступ, но не шифрование данных в БД — это разные задачи.

**Чек-лист для самопроверки:**
- [ ] Могу назвать 5 примеров секретов в типичном веб-приложении
- [ ] Понимаю почему base64 в K8s Secrets — не шифрование
- [ ] Знаю какие задачи решает Vault и в каких случаях он избыточен

**Попробуйте сами:**
1. Найдите в своих проектах (или в открытых репозиториях) `.env.example`. Сколько там секретов? Где сейчас хранятся реальные значения?
2. Запустите `kubectl get secret -n kube-system -o yaml | grep -A2 "data:" | head -20` (если есть K8s). Декодируйте одно из значений через `echo "..." | base64 -d`. Что получилось?
3. Подумайте: если уволится ваш коллега сегодня, сколько времени займёт отзыв всех его доступов к секретам? Где они хранятся?

---

### Глава 1: Установка и первый запуск

**Что вы узнаете:**
- как запустить Vault в dev-режиме для изучения;
- как запустить Vault в Docker и Docker Compose;
- разница между dev-режимом и production;
- основные переменные окружения для работы с Vault CLI.

**Цель:** читатель запускает Vault и делает первую операцию чтения/записи секрета за 5 минут.

**Темы:**

Разместить Схему 1 (архитектура Vault) в начале главы.

Раздел "Dev-режим — только для изучения":

> ☠️ **Осторожно:** dev-режим хранит все данные в памяти. При перезапуске Vault всё потеряется. Никогда не используй dev-режим для реальных секретов.

```bash
# Установка на Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install vault

# Проверить версию
vault version
# Vault v1.17.0 (...)

# Запустить в dev-режиме (хранит всё в памяти, root token = "root")
vault server -dev -dev-root-token-id=root

# В другом терминале — настроить окружение:
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

# Проверить что работает
vault status
```

Разобрать вывод `vault status` построчно:
```text
Key             Value
---             -----
Seal Type       shamir       ← тип seal (shamir = N ключей из M)
Initialized     true         ← инициализирован
Sealed          false        ← не запечатан (sealed=true = не работает)
Total Shares    1            ← в dev: 1 ключ из 1
Threshold       1
Version         1.17.0
HA Enabled      false
```

Раздел "Запуск в Docker":
```bash
# Запустить dev-сервер в Docker
docker run -d \
  --name vault \
  -p 8200:8200 \
  -e VAULT_DEV_ROOT_TOKEN_ID=root \
  -e VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200 \
  hashicorp/vault:1.17

# Проверить
curl -s http://localhost:8200/v1/sys/health | python3 -m json.tool
```

Раздел "Docker Compose для разработки":
```yaml
# docker-compose.yml
version: '3.8'
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
      - IPC_LOCK    # запрет swap для памяти с секретами
    command: server -dev
```

```bash
docker compose up -d
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root'
vault status
```

Раздел "Первые операции":
```bash
# Записать секрет
vault kv put secret/myapp/database \
  username="appuser" \
  password="S3cr3tP@ss"
# Success! Data written to: secret/myapp/database

# Прочитать секрет
vault kv get secret/myapp/database
# ====== Secret Path ======
# secret/data/myapp/database
#
# ======= Metadata =======
# Key                Value
# ---                -----
# created_time       2026-06-04T12:00:00Z
# version            1
#
# ====== Data ======
# Key         Value
# ---         -----
# password    S3cr3tP@ss
# username    appuser

# Только значение поля
vault kv get -field=password secret/myapp/database
# S3cr3tP@ss

# В JSON (удобно для скриптов)
vault kv get -format=json secret/myapp/database | python3 -m json.tool
```

Раздел "Переменные окружения":
```text
Переменная            Значение по умолчанию    Описание
VAULT_ADDR            http://127.0.0.1:8200    адрес Vault-сервера
VAULT_TOKEN           —                        токен аутентификации
VAULT_CACERT          —                        путь к CA-сертификату
VAULT_SKIP_VERIFY     false                    пропустить проверку TLS (только для тестов)
VAULT_NAMESPACE       —                        namespace (Enterprise)
VAULT_FORMAT          table                    формат вывода: table, json, yaml
```

Раздел "Web UI":
Vault имеет встроенный Web UI на `http://localhost:8200/ui`. Войти с root token. Показать скриншот словами что там: список engines, список secrets, форма для чтения/записи. Объяснить что для production UI стоит отключить или ограничить доступ.

**Типичные ошибки:**
- `Error making API request: dial tcp: connection refused` — не установлен `VAULT_ADDR` или Vault не запущен.
- `Code: 403. Errors: permission denied` — не установлен `VAULT_TOKEN` или токен без прав.
- `secret/myapp/database` vs `secret/data/myapp/database` — в KV v2 реальный путь данных включает `/data/`. Vault CLI скрывает это, API — нет.

**Чек-лист для самопроверки:**
- [ ] Запустил Vault в dev-режиме и выполнил `vault status`
- [ ] Записал и прочитал секрет через CLI
- [ ] Понимаю что dev-режим теряет данные при перезапуске
- [ ] Знаю три ключевые переменные окружения: VAULT_ADDR, VAULT_TOKEN, VAULT_CACERT

**Попробуйте сами:**
1. Запустите Vault в dev-режиме. Запишите несколько секретов. Остановите и снова запустите Vault — убедитесь что секреты пропали. Это и есть dev-режим.
2. Запустите Vault через Docker Compose. Откройте Web UI на `http://localhost:8200/ui`. Войдите с root-токеном. Создайте секрет через UI, прочитайте через CLI — и наоборот.
3. Попробуйте `vault kv get secret/myapp/database -format=json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['data']['password'])"`. Так скрипты читают конкретное поле.

---

### Глава 2: Основные концепции — paths, engines, tokens, leases

**Что вы узнаете:**
- файловую систему Vault: что такое path и mount point;
- типы secrets engines и зачем их несколько;
- что такое токен, его TTL и lease;
- иерархию токенов и отзыв.

**Цель:** читатель понимает «карту» Vault: что по какому пути находится и почему.

**Темы:**

Раздел "Vault как файловая система":
Всё в Vault адресуется путями (paths). Это похоже на Unix-файловую систему:
```text
secret/              ← mount point (KV engine)
├── myapp/
│   ├── database     ← секрет
│   └── api-keys     ← секрет
└── infra/
    └── ssh-keys

auth/                ← mount point (auth methods)
├── token/
├── approle/
└── kubernetes/

sys/                 ← системные пути (политики, аудит, здоровье)
├── policy/
├── audit/
└── health
```

```bash
# Посмотреть что смонтировано
vault secrets list
# Path          Type         Description
# ---           ----         -----------
# cubbyhole/    cubbyhole    per-token private secret storage
# identity/     identity     identity store
# secret/       kv           key/value secret storage
# sys/          system       system endpoints used for control

# Посмотреть auth methods
vault auth list
```

Раздел "Secrets Engines":
Объяснить концепцию: engine — это плагин который знает как работать с определённым типом секретов. Разные engines — разные возможности:

```text
Engine      Тип секретов              Static/Dynamic   Когда использовать
kv v2       произвольные key-value    Static           пароли, токены, конфиги
database    credentials к БД          Dynamic          доступ к PostgreSQL, MySQL
pki         TLS-сертификаты           Dynamic          внутренние CA, сервисные сертификаты
aws         AWS access keys           Dynamic          временные IAM credentials
ssh         SSH OTP / certificates    Dynamic          временный SSH-доступ к серверам
transit     шифрование без хранения   —                encrypt/decrypt как сервис
```

Раздел "KV v1 vs KV v2":
```text
KV v1:
- Нет версионирования
- Запись перезаписывает предыдущее значение без следа
- Путь: secret/myapp/key

KV v2:
- Версионирование (хранит N последних версий)
- Soft delete (можно восстановить)
- Metadata (время создания, кто создал)
- Путь данных: secret/data/myapp/key (через CLI прозрачно)
```

По умолчанию в dev-режиме монтируется KV v2. В книге везде использовать KV v2.

Раздел "Cubbyhole — личное хранилище токена":
Cubbyhole — это secrets engine который смонтирован по умолчанию. Его особенность: каждый токен видит ТОЛЬКО свой cubbyhole. При отзыве токена — cubbyhole уничтожается. Используется для безопасной передачи секретов между звеньями пайплайна (response wrapping, см. главу 5). Показать:
```bash
# Записать в свой cubbyhole
vault write cubbyhole/tmp/build-key value="abc123"

# Прочитать (только этим токеном!)
vault read cubbyhole/tmp/build-key

# Другой токен cubbyhole не видит — это разные пространства
```

Раздел "Токены":
```bash
# Посмотреть информацию о текущем токене
vault token lookup

# Создать дочерний токен
vault token create -policy=default -ttl=1h
# Key                  Value
# ---                  -----
# token                hvs.CAESIL...
# token_accessor       abc123...
# token_duration       1h
# token_renewable      true

# Обновить TTL токена
vault token renew

# Отозвать токен и все его дочерние
vault token revoke hvs.CAESIL...
```

Объяснить иерархию токенов: каждый токен имеет родителя. При отзыве родительского — все дочерние отзываются автоматически. Root token — вершина иерархии.

Раздел "Leases":
Объяснить что dynamic secrets выдаются с lease — временным «договором аренды». По истечении Vault может отозвать секрет. Для static KV lease не применяется.

```bash
# Посмотреть все активные leases
vault list sys/leases/lookup/database/creds/

# Продлить lease
vault lease renew <lease_id>

# Отозвать конкретный lease
vault lease revoke <lease_id>
```

**Типичные ошибки:**
- Путать `secret/myapp` (CLI, KV v2) и `secret/data/myapp` (API): через CLI можно писать без `/data/`, через API нельзя.
- Root token не должен использоваться приложениями — только для первоначальной настройки. Создавать отдельные токены с минимальными правами.
- Токены без `renewable=true` нельзя обновить — они просто умрут в TTL.

**Чек-лист для самопроверки:**
- [ ] Понимаю что такое mount point и path в Vault
- [ ] Знаю разницу между KV v1 и KV v2
- [ ] Понимаю иерархию токенов и что происходит при отзыве родительского
- [ ] Знаю что такое lease и зачем он нужен для dynamic secrets

**Попробуйте сами:**
1. Запустите `vault secrets list` и `vault auth list`. Запишите какие engines и auth methods смонтированы по умолчанию. Что такое `cubbyhole/`?
2. Создайте токен с TTL 30 секунд: `vault token create -ttl=30s`. Подождите 31 секунду. Попробуйте `vault token lookup <token>` — что произошло?
3. Смонтируйте дополнительный KV engine: `vault secrets enable -path=config kv-v2`. Запишите секрет в `config/app`. Теперь у вас два KV engine: `secret/` и `config/`.

---

### Глава 3: KV Secrets Engine — хранение статических секретов

**Что вы узнаете:**
- полный CRUD для KV v2 секретов;
- версионирование: история, восстановление, удаление;
- metadata секрета;
- организация секретов по структуре путей.

**Цель:** читатель уверенно работает с KV engine как основным инструментом для хранения статических секретов.

**Темы:**

Раздел "Основные операции KV v2":
```bash
# Создать / обновить секрет
vault kv put secret/myapp/database \
  host="prod-db.internal" \
  port="5432" \
  username="appuser" \
  password="S3cr3tP@ss" \
  dbname="myapp_prod"

# Прочитать последнюю версию
vault kv get secret/myapp/database

# Прочитать конкретную версию
vault kv get -version=2 secret/myapp/database

# Прочитать только одно поле
vault kv get -field=password secret/myapp/database

# Получить в JSON (для скриптов)
vault kv get -format=json secret/myapp/database

# Добавить одно поле не затрагивая остальные (patch, KV v2)
vault kv patch secret/myapp/database ssl_mode="require"

# Удалить последнюю версию (soft delete — можно восстановить)
vault kv delete secret/myapp/database

# Восстановить после soft delete
vault kv undelete -versions=3 secret/myapp/database

# Удалить конкретные версии навсегда (destroy)
vault kv destroy -versions=1,2 secret/myapp/database

# Удалить секрет полностью вместе со всеми версиями и metadata
vault kv metadata delete secret/myapp/database
```

> ☠️ **Осторожно:** `vault kv metadata delete` удаляет секрет и ВСЮ историю версий без возможности восстановления.

Раздел "Версионирование":
```bash
# Посмотреть метаданные и список версий
vault kv metadata get secret/myapp/database
# == Metadata ==
# Key                     Value
# ---                     -----
# cas_required            false
# created_time            2026-06-04T10:00:00Z
# current_version         3
# max_versions            0       ← 0 = хранить все версии
# oldest_version          1
# updated_time            2026-06-04T12:00:00Z
#
# ====== Version 1 ======
# Key              Value
# ---              -----
# created_time     2026-06-04T10:00:00Z
# deletion_time    n/a
# destroyed        false

# Ограничить количество хранимых версий
vault kv metadata put -max-versions=5 secret/myapp/database
```

Раздел "Организация секретов":
Рекомендовать структуру путей:
```text
secret/
├── production/
│   ├── myapp/
│   │   ├── database      ← username, password, host
│   │   ├── redis         ← url, password
│   │   └── external-api  ← key, secret
│   └── infra/
│       └── grafana       ← admin_password
├── staging/
│   └── myapp/
│       └── database
└── shared/
    └── tls/
        └── wildcard-cert ← cert, key
```

Объяснить: группировка по окружению (prod/staging) + по сервису. Позволяет давать политики на уровне `secret/production/myapp/*` или `secret/staging/*`.

Раздел "Работа с секретами из скриптов":
```bash
# Достать значение в bash-переменную
DB_PASSWORD=$(vault kv get -field=password secret/production/myapp/database)
export DATABASE_URL="postgresql://appuser:${DB_PASSWORD}@prod-db:5432/myapp"

# Достать несколько полей через jq
eval $(vault kv get -format=json secret/production/myapp/database | \
  jq -r '.data.data | to_entries[] | "export \(.key | ascii_upcase)=\(.value)"')
echo $PASSWORD   # S3cr3tP@ss
echo $USERNAME   # appuser
```

**Типичные ошибки:**
- `vault kv put` перезаписывает ВСЕ поля секрета, а не добавляет к ним. Для добавления/изменения одного поля использовать `vault kv patch`.
- Чувствительные данные попадают в history shell если писать пароль прямо в команде. Использовать stdin или файл: `vault kv put secret/app @credentials.json`.
- Мягкое удаление (`vault kv delete`) не удаляет данные — токены с read-доступом могут читать прошлые версии.

**Чек-лист для самопроверки:**
- [ ] Умею создавать, читать, обновлять и удалять секреты KV v2
- [ ] Знаю разницу между `delete` (soft) и `destroy` (permanent)
- [ ] Умею читать конкретную версию секрета
- [ ] Знаю как использовать `vault kv get -format=json` в скриптах

**Попробуйте сами:**
1. Создайте секрет с 3 полями. Обновите его 3 раза (разные значения). Прочитайте каждую из версий. Мягко удалите последнюю и восстановите её.
2. Напишите bash-скрипт который читает username и password из Vault и выводит connection string в формате `postgresql://USER:PASS@host/db`. Не хардкодь значения.
3. Попробуйте `vault kv put secret/test password=mypass` — пароль видно в истории shell. Теперь сделайте то же через файл: `echo '{"password":"mypass"}' > /tmp/creds.json && vault kv put secret/test @/tmp/creds.json && shred -u /tmp/creds.json`. Безопаснее?

---

### Глава 4: Политики — управление доступом

**Что вы узнаете:**
- что такое политика в Vault и как она работает;
- синтаксис HCL для описания политик;
- возможности: read, write, list, delete, create, update, patch, sudo;
- как создавать, применять и отлаживать политики.

**Цель:** читатель создаёт политики по принципу наименьших привилегий — приложение читает только нужные ему секреты, CI/CD только пишет в свой namespace.

**Темы:**

Раздел "Принцип работы политик":
Vault использует deny-by-default: если нет явного разрешения — запрещено. Политики привязываются к токенам. Токен может иметь несколько политик — права суммируются.

Раздел "Синтаксис HCL":
```hcl
# Политика: приложение читает свои секреты
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}

# Список секретов в директории (для UI и vault kv list)
path "secret/metadata/production/myapp/*" {
  capabilities = ["list"]
}

# CI/CD: запись в staging, только свой namespace
path "secret/data/staging/myapp/*" {
  capabilities = ["create", "update", "patch"]
}

# Оператор: полный доступ к своему namespace
path "secret/data/production/myapp/*" {
  capabilities = ["create", "read", "update", "patch", "delete", "list"]
}

# Запрет явный (можно переопределить разрешение из другой политики)
path "secret/data/production/infra/*" {
  capabilities = ["deny"]
}
```

Таблица capabilities:
```text
Capability    HTTP-метод    Описание
create        POST          создать новый секрет
read          GET           прочитать значение
update        POST          обновить существующий
patch         PATCH         частично обновить (KV v2)
delete        DELETE        удалить
list          LIST          список (vault kv list)
sudo          —             разрешить привилегированные операции
deny          —             явный запрет (приоритет над разрешениями)
```

Раздел "Создание и управление политиками":
```bash
# Создать политику из файла
cat > myapp-policy.hcl << 'EOF'
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}
path "secret/metadata/production/myapp/*" {
  capabilities = ["list"]
}
EOF

vault policy write myapp-policy myapp-policy.hcl
# Success! Uploaded policy: myapp-policy

# Список политик
vault policy list
# default
# myapp-policy
# root

# Прочитать политику
vault policy read myapp-policy

# Удалить политику
vault policy delete myapp-policy
```

Раздел "Тестирование политики":
```bash
# Создать токен с конкретной политикой
vault token create -policy=myapp-policy -ttl=1h

# Проверить что токен имеет нужные права
# Сменить VAULT_TOKEN на новый токен и попробовать операции

# Утилита для проверки прав без реального выполнения
vault token capabilities hvs.TOKEN secret/data/production/myapp/database
# read

vault token capabilities hvs.TOKEN secret/data/production/infra/ssh
# deny
```

Раздел "Встроенные политики":
- `root` — полный доступ, только для root token
- `default` — минимальные права: обновить себя, посмотреть свой токен

**Типичные ошибки:**
- Забыть добавить `list` на `secret/metadata/*` — `vault kv list` не работает даже при наличии `read` на данные.
- Политика на `secret/data/myapp/*` не покрывает `secret/metadata/myapp/*` — это разные пути в KV v2.
- Wildcard `*` матчит только один уровень. `secret/data/myapp/*` не матчит `secret/data/myapp/db/passwords`. Для рекурсии использовать `+` или полный путь.

**Чек-лист для самопроверки:**
- [ ] Понимаю deny-by-default: всё запрещено если нет явного разрешения
- [ ] Знаю синтаксис HCL и все capabilities
- [ ] Умею создать, применить и проверить политику
- [ ] Понимаю разницу путей `secret/data/*` vs `secret/metadata/*` в KV v2

**Попробуйте сами:**
1. Создайте политику которая разрешает только `read` к `secret/data/production/myapp/*`. Создайте токен с этой политикой. Попробуйте прочитать секрет — работает. Попробуйте записать — `Code: 403`.
2. Создайте политику для CI/CD: `create` и `update` к `secret/data/staging/myapp/*`, но без `read`. CI может класть секреты, но не читать их (например, чтобы не утекали в логи).
3. Используйте `vault token capabilities` чтобы проверить права токена на нескольких путях. Убедитесь что политика работает как задумано.

---

### Глава 5: Методы аутентификации — Token, AppRole, UserPass

**Что вы узнаете:**
- зачем нужны разные методы аутентификации;
- как работает Token auth (базовый);
- AppRole: для приложений и CI/CD;
- UserPass: для людей без LDAP;
- как привязать политику к методу аутентификации.

**Цель:** читатель знает какой метод аутентификации использовать для каждого актора: человек, CI/CD пайплайн, приложение.

**Темы:**

Раздел "Зачем разные методы":
```text
Актор             Метод            Причина
────────────────────────────────────────────────────────────────
Разработчик       UserPass / LDAP  У человека есть логин/пароль или корп. аккаунт
CI/CD пайплайн    AppRole          Нет интерактивного входа, нужны rotate-friendly credentials
Docker-контейнер  AppRole          Аналогично CI/CD
K8s Pod           Kubernetes Auth  Pod имеет ServiceAccount JWT — нет нужды в паролях
Облачная VM       AWS/GCP Auth     VM имеет IAM-роль — аутентификация без секретов
```

Раздел "Token Auth":
Базовый метод. Уже использовался в предыдущих главах.

```bash
# Создать токен с политикой и TTL
vault token create \
  -policy=myapp-policy \
  -ttl=24h \
  -display-name="myapp-production"

# Обновить токен (продлить TTL)
vault token renew

# Отозвать токен
vault token revoke hvs.TOKEN

# Посмотреть информацию о токене (accessor, policies, TTL)
vault token lookup hvs.TOKEN
```

Раздел "AppRole — для приложений и CI/CD":

Разместить Схему 3 (AppRole flow).

AppRole использует два секрета: `role_id` (полупубличный, как username) и `secret_id` (одноразовый или с TTL, как password).

```bash
# Включить AppRole auth method
vault auth enable approle

# Создать роль для CI/CD пайплайна
vault write auth/approle/role/myapp-cicd \
  token_policies="myapp-policy" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=10m \     # secret_id живёт 10 минут
  secret_id_num_uses=1    # secret_id одноразовый

# Получить role_id (можно хранить в CI/CD как несекретную переменную)
vault read auth/approle/role/myapp-cicd/role-id
# Key        Value
# ---        -----
# role_id    12345678-1234-1234-1234-123456789012

# Получить одноразовый secret_id (генерировать перед каждым использованием)
vault write -f auth/approle/role/myapp-cicd/secret-id
# Key                   Value
# ---                   -----
# secret_id             abcdef12-...
# secret_id_accessor    xyz789...
# secret_id_num_uses    1
# secret_id_ttl         10m

# Приложение/CI: обменять role_id + secret_id на токен
vault write auth/approle/login \
  role_id=12345678-1234-1234-1234-123456789012 \
  secret_id=abcdef12-...
# Key                     Value
# ---                     -----
# token                   hvs.CAESIL...
# token_policies          [myapp-policy]
# token_ttl               1h
```

Рекомендации по AppRole:
- `role_id` — не секрет, можно хранить в env CI/CD как обычную переменную
- `secret_id` — секрет, генерировать непосредственно перед использованием (не хранить)
- `secret_id_num_uses=1` — одноразовый secret_id не может быть переиспользован при утечке

Раздел "Response Wrapping — безопасная передача секретов":
Проблема: secret_id нужно передать из Vault в CI/CD. Если передавать plaintext — любой кто читает логи CI/CD видит secret_id. Response wrapping решает это: Vault упаковывает ответ в «коробку» (wrapped token), которая открывается только целевым токеном.
```bash
# Запросить wrapped secret_id (Vault не показывает само значение)
vault write -wrap-ttl=5m -f auth/approle/role/myapp-cicd/secret-id
# Key                  Value
# ---                  -----
# wrapping_token:      hvs.CAESIL...    ← токен-«коробка»
# wrapping_accessor:   ...
# wrapping_ttl:        5m

# Целевая система (CI/CD runner) открывает коробку
VAULT_TOKEN=hvs.CAESIL... vault unwrap
# Key                   Value
# ---                   -----
# secret_id             abcdef12-...    ← появился только при unwrap
```
Объяснить: wrapped token может быть перехвачен, но без целевого токена — бесполезен. Использовать для: передачи secret_id в CI/CD, передачи root token администратору, передачи credentials между шагами пайплайна.

Раздел "LDAP — для корпоративных команд":
```bash
# Включить LDAP auth
vault auth enable ldap

# Настроить подключение к AD/OpenLDAP
vault write auth/ldap/config \
  url="ldap://ldap.internal.company.com" \
  userdn="ou=users,dc=company,dc=com" \
  groupdn="ou=groups,dc=company,dc=com" \
  binddn="cn=vault-reader,ou=service-accounts,dc=company,dc=com" \
  bindpass="ServiceAccountPass" \
  userattr="uid"

# Политика по группе
vault write auth/ldap/groups/devops-team policies="admin-policy,default"
vault write auth/ldap/groups/developers policies="myapp-readonly,default"

# Войти
vault login -method=ldap username=ivan
```
Указать: для production LDAP обязателен — токен живёт пока сессия активна, ротация пароля сотрудника автоматически отзывает доступ.

Раздел "UserPass — для людей":
```bash
# Включить
vault auth enable userpass

# Создать пользователя
vault write auth/userpass/users/ivan \
  password="SecurePass123" \
  policies="myapp-policy,default"

# Войти
vault login -method=userpass username=ivan
# Password (will be hidden):
# Token: hvs.CAESIL...

# Изменить пароль
vault write auth/userpass/users/ivan password="NewPass456"
```

**Типичные ошибки:**
- `secret_id_num_uses=1` + повторная попытка входа = `Code: 400. Errors: invalid secret_id`. secret_id исчерпан, нужно генерировать новый.
- Хранить `secret_id` в переменной окружения CI/CD как постоянную переменную — это сводит на нет защиту. secret_id должен генерироваться перед каждым pipeline run.
- UserPass для приложений — не стоит. Приложение не может «ввести пароль» интерактивно, используй AppRole.

**Чек-лист для самопроверки:**
- [ ] Понимаю какой метод аутентификации использовать для каждого актора
- [ ] Умею настроить AppRole и выполнить login flow: role_id + secret_id → token
- [ ] Знаю разницу между role_id (несекретный) и secret_id (одноразовый)
- [ ] Умею создать UserPass-пользователя с нужными политиками

**Попробуйте сами:**
1. Включите AppRole, создайте роль с политикой из главы 4. Получите role_id и secret_id. Выполните login — получите токен. Используйте этот токен для чтения секрета.
2. Сгенерируйте secret_id с `num_uses=1`. Попробуйте использовать его дважды — второй раз должна быть ошибка.
3. Напишите скрипт который: получает secret_id, авторизуется в Vault через AppRole, читает секрет, выводит его. Скрипт должен работать без хардкода токена.

---

### Глава 6: Dynamic Secrets — пароли от баз данных

**Что вы узнаете:**
- что такое dynamic secrets и чем они лучше статических;
- как настроить database engine для PostgreSQL;
- как приложение получает временные credentials;
- ротация и отзыв dynamic secrets.

**Цель:** читатель настраивает Vault так, что PostgreSQL-пароль никогда не хранится постоянно — только временные credentials с TTL.

**Темы:**

Раздел "Проблема статических паролей от БД":
```text
Статические credentials:
- один пароль → несколько приложений → утечка одного = компрометация всех
- пароль живёт годами → чем дольше, тем выше риск
- ротация = остановка сервиса для обновления конфига
- нет аудита: кто и когда использовал credentials

Dynamic credentials:
- каждому приложению/запросу — уникальный пользователь с уникальным паролем
- TTL: 1 час → автоматически истекает и отзывается
- ротация = просто подождать TTL, без изменения конфига
- в audit log: vault создал user-abc123 для pod-xyz в 14:32
```

Раздел "Настройка Database Engine для PostgreSQL":
```bash
# Включить database engine
vault secrets enable database

# Настроить соединение с PostgreSQL
# (vault должен иметь права на создание пользователей)
vault write database/config/myapp-postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/myapp?sslmode=disable" \
  allowed_roles="myapp-readonly,myapp-readwrite" \
  username="vault_admin" \
  password="VaultAdminPass"

# Ротировать пароль vault_admin (Vault сам обновит его в PostgreSQL и сохранит)
vault write -force database/config/myapp-postgres/rotate-root
```

> ☠️ **Осторожно:** после `rotate-root` Vault меняет пароль vault_admin в PostgreSQL и запоминает новый. Старый пароль перестаёт работать. Если Vault потеряет данные (dev-режим) — доступ к PostgreSQL через vault_admin будет потерян навсегда.

Раздел "Создание роли для dynamic credentials":
```bash
# Роль для read-only доступа
vault write database/roles/myapp-readonly \
  db_name=myapp-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";
    GRANT USAGE ON SCHEMA public TO \"{{name}}\";" \
  revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl=1h \
  max_ttl=24h

# Роль для read-write доступа
vault write database/roles/myapp-readwrite \
  db_name=myapp-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\";
    GRANT USAGE ON SCHEMA public TO \"{{name}}\";" \
  revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl=1h \
  max_ttl=24h
```

Раздел "Получение временных credentials":
```bash
# Приложение запрашивает credentials
vault read database/creds/myapp-readonly
# Key                Value
# ---                -----
# lease_id           database/creds/myapp-readonly/abc123...
# lease_duration     1h
# lease_renewable    true
# password           A1b-Xyz-...   ← уникальный для этого запроса
# username           v-approle-readonly-AbCdEf123  ← уникальный пользователь

# В PostgreSQL после этого появится пользователь v-approle-readonly-AbCdEf123

# Продлить lease (продлить жизнь credentials)
vault lease renew database/creds/myapp-readonly/abc123...

# Отозвать credentials досрочно
vault lease revoke database/creds/myapp-readonly/abc123...
# PostgreSQL роль будет удалена немедленно
```

Раздел "Интеграция с приложением":
Показать как приложение должно работать с dynamic secrets:
```python
# Пример (Python, псевдокод)
import hvac  # pip install hvac

client = hvac.Client(url='http://vault:8200', token=os.environ['VAULT_TOKEN'])

# Получить временные credentials
creds = client.secrets.database.generate_credentials(name='myapp-readonly')
db_username = creds['data']['username']
db_password = creds['data']['password']
lease_id = creds['lease_id']
lease_duration = creds['lease_duration']  # в секундах

# Подключиться к БД
conn = psycopg2.connect(host='postgres', user=db_username, password=db_password, dbname='myapp')

# Перед истечением lease — продлить
# client.sys.renew_self_token()  или renew lease
```

**Типичные ошибки:**
- Vault Admin (vault_admin) должен иметь права `CREATEROLE` в PostgreSQL. Без этого creation_statements упадут с ошибкой.
- `VALID UNTIL '{{expiration}}'` в creation_statements — обязательно. Без этого пользователь в PostgreSQL не истечёт даже после revoke lease.
- `DROP ROLE IF EXISTS` в revocation_statements — нужен `IF EXISTS`. Если роль уже удалена вручную — revocation не должен падать.

**Чек-лист для самопроверки:**
- [ ] Понимаю чем dynamic secrets лучше статических
- [ ] Умею настроить database engine для PostgreSQL
- [ ] Умею получить временные credentials через `vault read database/creds/...`
- [ ] Знаю как продлить и досрочно отозвать lease

**Попробуйте сами:**
1. Запустите PostgreSQL в Docker (`docker run -e POSTGRES_PASSWORD=admin -p 5432:5432 postgres:16`). Настройте database engine. Получите dynamic credentials. Подключитесь к PostgreSQL с ними через `psql`.
2. Получите два набора credentials для одной роли — убедитесь что username и password уникальны для каждого. Проверьте в PostgreSQL (`SELECT usename FROM pg_user`).
3. Отзовите lease: `vault lease revoke <lease_id>`. Попробуйте подключиться к PostgreSQL со старыми credentials — убедитесь что `psql` выдаёт ошибку аутентификации.

---

### Глава 7: PKI Engine — генерация сертификатов

**Что вы узнаете:**
- как настроить Vault как внутренний Certificate Authority (CA);
- как выпускать TLS-сертификаты для внутренних сервисов;
- автоматическое обновление сертификатов;
- зачем нужен промежуточный CA.

**Цель:** читатель настраивает внутренний CA и выпускает сертификаты для сервисов с TTL в часах/днях вместо ручного обновления раз в год.

**Темы:**

Раздел "Зачем PKI Engine":
```text
Без Vault PKI:
- самоподписанные сертификаты с сроком 10 лет
- браузер / curl ругается на self-signed
- Let's Encrypt только для публичных доменов
- ручное обновление → кто-то забыл → продакшн упал

С Vault PKI:
- внутренний CA, которому доверяют все сервисы в инфраструктуре
- короткоживущие сертификаты (1 день, 1 неделя) — меньше окно атаки
- автовыпуск через Vault Agent или cert-manager
- полный аудит: кто и когда запросил сертификат
```

Раздел "Настройка Root CA":
```bash
# Включить PKI engine
vault secrets enable pki

# Установить максимальный TTL (10 лет для Root CA)
vault secrets tune -max-lease-ttl=87600h pki

# Сгенерировать root certificate
vault write -field=certificate pki/root/generate/internal \
  common_name="My Internal Root CA" \
  issuer_name="root-2026" \
  ttl=87600h \
  > /tmp/root-ca.pem

# Настроить CRL и issuer URLs
vault write pki/config/urls \
  issuing_certificates="http://vault:8200/v1/pki/ca" \
  crl_distribution_points="http://vault:8200/v1/pki/crl"
```

Раздел "Промежуточный CA (рекомендуется для production)":
```bash
# Включить второй PKI mount для intermediate CA
vault secrets enable -path=pki_int pki
vault secrets tune -max-lease-ttl=43800h pki_int

# Сгенерировать CSR для intermediate CA
vault write -format=json pki_int/intermediate/generate/internal \
  common_name="My Internal Intermediate CA" | \
  jq -r '.data.csr' > /tmp/int-ca.csr

# Подписать CSR через root CA
vault write -format=json pki/root/sign-intermediate \
  csr=@/tmp/int-ca.csr \
  format=pem_bundle \
  ttl=43800h | \
  jq -r '.data.certificate' > /tmp/int-ca.pem

# Загрузить подписанный сертификат в intermediate CA
vault write pki_int/intermediate/set-signed certificate=@/tmp/int-ca.pem

vault write pki_int/config/urls \
  issuing_certificates="http://vault:8200/v1/pki_int/ca" \
  crl_distribution_points="http://vault:8200/v1/pki_int/crl"
```

Раздел "Создание роли и выпуск сертификатов":
```bash
# Создать роль для выпуска сертификатов
vault write pki_int/roles/internal-services \
  allowed_domains="internal.example.com,svc.cluster.local" \
  allow_subdomains=true \
  allow_bare_domains=false \
  max_ttl=720h        # максимум 30 дней

# Выпустить сертификат для сервиса
vault write pki_int/issue/internal-services \
  common_name="myapp.internal.example.com" \
  ttl=24h \
  alt_names="myapp.svc.cluster.local,localhost" \
  ip_sans="10.0.0.1,127.0.0.1"
# Вывод: certificate, issuing_ca, ca_chain, private_key, serial_number
```

Раздел "Политика для PKI":
```hcl
# Политика: сервис может выпускать только свои сертификаты
path "pki_int/issue/internal-services" {
  capabilities = ["create", "update"]
}
```

**Типичные ошибки:**
- Использовать root CA для прямого выпуска сертификатов (без intermediate) — компрометация root CA = смена всей инфраструктуры. Intermediate CA можно заменить, root — нельзя.
- Слишком длинный TTL для выпускаемых сертификатов — теряется смысл PKI engine. 1-30 дней — разумный диапазон.
- Не настроить CRL URL — клиенты не смогут проверить отозванные сертификаты.

**Чек-лист для самопроверки:**
- [ ] Понимаю зачем нужен промежуточный CA (intermediate)
- [ ] Умею настроить root CA и intermediate CA в Vault
- [ ] Умею выпустить сертификат с нужным CN, SANs и TTL
- [ ] Знаю как настроить политику для выпуска сертификатов

**Попробуйте сами:**
1. Настройте root CA и intermediate CA. Выпустите сертификат для `test.internal.example.com`. Сохраните в файл и проверьте через `openssl x509 -in cert.pem -noout -text | grep -A5 "Subject\|DNS\|Not After"`.
2. Настройте `nginx` с выпущенным сертификатом. Попробуйте `curl -cacert /tmp/root-ca.pem https://test.internal.example.com` — должен работать без `-k`.
3. Выпустите сертификат с TTL 1 минута. Подождите 2 минуты. Попробуйте использовать — сертификат истёк. Выпустите новый. Это и есть короткоживущие сертификаты.

---

### Глава 7b (бонус): Transit Engine — шифрование как сервис

**Что вы узнаете:**
- как использовать Vault для шифрования данных без их хранения;
- разница между encryption в покое (Vault хранит) и encryption как сервис (Transit);
- шифрование/дешифрование через API.

**Цель:** приложение шифрует PII-данные через Vault не имея доступа к ключам.

**Темы:**

Раздел "Transit vs KV — разница":
```text
KV v2:         Vault хранит зашифрованные данные → ключ у Vault
Transit:       приложение шлёт plaintext → Vault возвращает ciphertext
               приложение хранит ciphertext → Vault расшифровывает по запросу
               ключ НИКОГДА не покидает Vault
```

Раздел "Настройка Transit":
```bash
# Включить
vault secrets enable transit

# Создать ключ шифрования (тип: aes256-gcm96 по умолчанию)
vault write -f transit/keys/myapp-encryption-key

# Зашифровать данные
vault write transit/encrypt/myapp-encryption-key plaintext=$(echo "s3ns1t1v3-data" | base64)
# Key           Value
# ---           -----
# ciphertext    vault:v1:abc123...

# Расшифровать
vault write transit/decrypt/myapp-encryption-key ciphertext="vault:v1:abc123..."
# Key           Value
# ---           -----
# plaintext     czNuczF0MXYzLWRhdGE=
```
Объяснить: `plaintext` всегда base64. Ключ в Vault, приложение работает с ciphertext. Ротация ключа: `vault write -f transit/keys/myapp-encryption-key/rotate` — старые данные остаются читаемыми, новые шифруются новым ключом (key derivation).

**Типичные ошибки:**
- Передавать plaintext без base64 — Vault вернёт ошибку.
- Transit не шифрует данные в покое — он шифрует на лету. Для шифрования в покое используйте KV v2.
- Ротация ключа не перешифровывает старые данные — нужно читать ciphertext, расшифровывать старым ключом, зашифровывать новым.

**Чек-лист:** 3 пункта.

**Попробуйте сами:** 1. Зашифруйте строку, расшифруйте. 2. Выполните rotate, зашифруйте ещё раз — ключ новый? 3. Интегрируйте Transit в Python-скрипт через hvac.

---

### Глава 8: Vault Agent — автоматическое получение секретов

**Что вы узнаете:**
- что такое Vault Agent и зачем он нужен;
- как Vault Agent рендерит шаблоны конфигурации с секретами;
- автообновление токена и секретов;
- запуск Vault Agent как sidecar.

**Цель:** приложение не знает о Vault — оно читает секреты из обычного файла или переменных окружения. Vault Agent ведёт всю работу с Vault.

**Темы:**

Раздел "Проблема прямой интеграции":
```text
Без Vault Agent:
приложение само:
- аутентифицируется в Vault
- обновляет токен
- читает секреты при старте и при их истечении
→ каждое приложение должно знать про Vault

С Vault Agent:
sidecar/service рядом с приложением:
- аутентифицируется в Vault (AppRole, Kubernetes auth)
- рендерит шаблоны с секретами в файлы
- обновляет файлы при ротации секретов
- рестартует приложение при обновлении (опционально)
→ приложение читает обычный файл, не знает про Vault
```

Раздел "Конфигурация Vault Agent":
```hcl
# vault-agent.hcl
vault {
  address = "http://vault:8200"
}

# Аутентификация через AppRole
auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path   = "/vault/role_id"
      secret_id_file_path = "/vault/secret_id"
      remove_secret_id_file_after_reading = true  # безопаснее
    }
  }

  sink "file" {
    config = {
      path = "/vault/token"  # токен сохраняется сюда
    }
  }
}

# Кэш (проксирование запросов к Vault)
cache {
  use_auto_auth_token = true
}

listener "tcp" {
  address     = "127.0.0.1:8007"
  tls_disable = true
}

# Шаблоны — рендерить конфиг с секретами
template {
  source      = "/vault/templates/app-config.tpl"
  destination = "/app/config/database.env"
  perms       = "0640"

  # Перезапустить приложение при обновлении секрета
  exec {
    command = ["sh", "-c", "pkill -HUP myapp || true"]
  }
}
```

Раздел "Шаблоны Consul-template":
```
{{/* /vault/templates/app-config.tpl */}}
{{ with secret "secret/data/production/myapp/database" }}
DATABASE_HOST={{ .Data.data.host }}
DATABASE_PORT={{ .Data.data.port }}
DATABASE_USER={{ .Data.data.username }}
DATABASE_PASS={{ .Data.data.password }}
DATABASE_NAME={{ .Data.data.dbname }}
{{ end }}
```

```bash
# Запуск агента
vault agent -config=vault-agent.hcl
```

Раздел "Vault Agent в Docker":
```yaml
# docker-compose.yml
services:
  vault-agent:
    image: hashicorp/vault:1.17
    command: agent -config=/vault/config/agent.hcl
    volumes:
      - ./vault-agent.hcl:/vault/config/agent.hcl:ro
      - ./role_id:/vault/role_id:ro
      - ./templates:/vault/templates:ro
      - secrets-vol:/app/config  # шаред volume с приложением

  myapp:
    image: myapp:latest
    volumes:
      - secrets-vol:/app/config:ro  # читает из этого volume
    depends_on:
      - vault-agent

volumes:
  secrets-vol:
```

**Типичные ошибки:**
- Vault Agent не имеет прав читать секрет → шаблон не рендерится, файл не создаётся → приложение стартует с пустым конфигом. Всегда проверять логи агента.
- `remove_secret_id_file_after_reading = true` — файл с secret_id удалится после первого чтения. Если агент рестартует — нужно положить новый secret_id.
- Если шаблон не изменился — exec не запустится. Используй `error_on_missing_key = true` чтобы не рендерить шаблон с отсутствующими ключами.

**Чек-лист для самопроверки:**
- [ ] Понимаю идею Vault Agent: приложение читает файл, агент ведёт работу с Vault
- [ ] Умею написать конфиг vault-agent.hcl с auto_auth и template
- [ ] Знаю синтаксис Consul-template для рендеринга секретов в файл
- [ ] Умею запустить Vault Agent рядом с приложением в Docker Compose

**Попробуйте сами:**
1. Настройте Vault Agent с AppRole auth. Создайте шаблон который рендерит `database.env` из секретов в Vault. Запустите агент и убедитесь что файл создан с правильными значениями.
2. Обновите секрет в Vault (`vault kv patch ...`). Подождите 30-60 секунд. Проверьте файл — он обновился автоматически.
3. Добавьте `exec` в template-блок который при обновлении выводит `echo "secrets updated"`. Убедитесь что команда выполняется при изменении секрета.

---

### Глава 9: Vault в Docker Compose — production-like setup

**Что вы узнаете:**
- запуск Vault с постоянным хранилищем (Raft);
- инициализация и unseal;
- настройка TLS для production;
- полный пример стека: Vault + приложение + Vault Agent.

**Цель:** читатель запускает Vault который переживает перезапуск и хранит данные на диске.

**Темы:**

Раздел "Сравнение storage backends":
```text
Backend    HA      Простота    Когда использовать
── ───────────────────────────────────────────────────────────
Raft       Да*    Высокая     1-5 нод, встроенный, не требует внешних зависимостей
Consul     Да     Средняя     >5 нод, уже есть Consul в инфраструктуре
File       Нет    Высокая     Только dev/testing, данные на диске одной ноды
In-memory  Нет    Макс        Dev-режим, данные теряются при рестарте; НИКОГДА для production
```
`*` Raft — встроенный consensus. Для HA нужно 3 или 5 нод. Потеря >50% нод = полная недоступность.

В этой книге используется Raft — оптимальный выбор для 80% команд (1-3 ноды, без внешнего Consul).

Раздел "Vault с Raft storage (данные на диске)":
```hcl
# vault-config.hcl
ui            = true
disable_mlock = true    # нужно в Docker без IPC_LOCK

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = true    # для dev/staging; в prod — настроить TLS
}

api_addr     = "http://vault:8200"
cluster_addr = "http://vault:8201"
```

```yaml
# docker-compose.yml
services:
  vault:
    image: hashicorp/vault:1.17
    container_name: vault
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
      retries: 5

volumes:
  vault-data:
```

Раздел "Инициализация и первый unseal":
```bash
export VAULT_ADDR='http://localhost:8200'

# Инициализация (только один раз!)
vault operator init -key-shares=5 -key-threshold=3
```

> ☠️ **Осторожно:** вывод `vault operator init` содержит 5 unseal keys и initial root token. Это единственный раз когда они показываются. Если потеряешь threshold ключей (3 из 5) — данные в Vault недоступны навсегда. Сохрани ключи в надёжном месте (не в том же Vault!).

```text
Unseal Key 1: abc123...
Unseal Key 2: def456...
Unseal Key 3: ghi789...
Unseal Key 4: jkl012...
Unseal Key 5: mno345...

Initial Root Token: hvs.XXXXXX
```

```bash
# Unseal (3 ключа из 5 в любом порядке)
vault operator unseal abc123...
vault operator unseal def456...
vault operator unseal ghi789...
# Sealed: false  ← готово

# Войти с root token (только для начальной настройки!)
vault login hvs.XXXXXX
```

Раздел "Auto-unseal через Vault Transit":
Упомянуть что ручной unseal неудобен при автоперезапуске. Auto-unseal: Vault использует внешний KMS (AWS KMS, GCP KMS, Transit секрет другого Vault) для автоматического unsealing. Настройка через `seal "transit" {}` или `seal "awskms" {}` блок в конфиге. Для homelab — Transit seal через второй Vault.

**Типичные ошибки:**
- Запускать `vault operator init` дважды — второй раз выдаст ошибку "Vault is already initialized". Это нормально.
- Хранить unseal keys в переменных окружения того же Docker Compose — при компрометации теряется смысл. Хранить отдельно (менеджер паролей, физически разнесённые носители).
- `disable_mlock = true` нужен в Docker/контейнерах. Без него Vault выдаёт warning или не стартует.

**Чек-лист для самопроверки:**
- [ ] Умею запустить Vault с Raft storage через Docker Compose
- [ ] Понимаю процедуру init: одноразовая операция, сохранить ключи
- [ ] Умею выполнить unseal после рестарта
- [ ] Знаю что такое auto-unseal и зачем он нужен

**Попробуйте сами:**
1. Запустите Vault с Raft storage. Выполните `vault operator init`. Сохраните ключи в файл (не забудь!). Выполните unseal тремя ключами. Запишите секрет. Остановите контейнер и запустите снова — выполните unseal. Секрет сохранился?
2. Попробуйте остановить Vault без unseal и обратиться к секрету — `vault status` покажет `Sealed: true`. Это и есть защита от несанкционированного доступа к диску.
3. Сохраните unseal keys в Vaultwarden/1Password/KeePass. Удалите файл с ключами. Убедитесь что помнишь откуда их достать. Unseal keys должны быть доступны даже если сервер сгорел.

---

### Глава 10: Интеграция с Kubernetes

**Что вы узнаете:**
- Kubernetes Auth Method: поды авторизуются через ServiceAccount JWT;
- Vault Agent Injector: автоматическая инъекция секретов в поды;
- Vault Secrets Operator (VSO): нативный K8s способ;
- политики для K8s namespace и ServiceAccount.

**Цель:** поды в K8s получают секреты из Vault без хранения credentials — только через ServiceAccount JWT.

**Темы:**

Разместить Схему 4 (Kubernetes Auth flow).

Раздел "Kubernetes Auth Method":
```bash
# Включить Kubernetes auth
vault auth enable kubernetes

# Настроить (запускать изнутри кластера или с kubeconfig)
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Создать роль: namespace=production, serviceaccount=myapp → политика myapp-policy
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=myapp \
  bound_service_account_namespaces=production \
  policies=myapp-policy \
  ttl=1h
```

Раздел "Vault Agent Injector":
Injector — это mutating webhook в K8s. При создании пода с аннотациями — Injector автоматически добавляет init container и sidecar с Vault Agent.

```bash
# Установить через Helm
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --set "server.enabled=false" \
  --set "injector.enabled=true" \
  --set "injector.externalVaultAddr=http://vault.vault.svc:8200"
```

```yaml
# deployment.yaml с аннотациями для инъекции
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "myapp"
        # Инжектировать секрет в файл /vault/secrets/database.env
        vault.hashicorp.com/agent-inject-secret-database.env: "secret/data/production/myapp/database"
        # Шаблон для формата файла
        vault.hashicorp.com/agent-inject-template-database.env: |
          {{ with secret "secret/data/production/myapp/database" -}}
          DB_HOST={{ .Data.data.host }}
          DB_USER={{ .Data.data.username }}
          DB_PASS={{ .Data.data.password }}
          {{- end }}
    spec:
      serviceAccountName: myapp
      containers:
        - name: myapp
          image: myapp:latest
          # Секреты будут в /vault/secrets/database.env
          command: ["sh", "-c", "source /vault/secrets/database.env && ./myapp"]
```

Раздел "Политика для K8s":
```hcl
# myapp-policy.hcl
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}
path "secret/metadata/production/myapp/*" {
  capabilities = ["list"]
}
```

Раздел "Vault Secrets Operator (VSO) — современный подход":
Упомянуть как альтернативу: VSO синхронизирует секреты из Vault в нативные K8s Secrets. Приложение работает с обычными K8s Secrets, не зная о Vault. Настройка через CRD `VaultStaticSecret`, `VaultDynamicSecret`. Плюс: совместим с любым приложением без изменений. Минус: секреты всё равно попадают в etcd.

**Типичные ошибки:**
- `permission denied` при Kubernetes auth — проверить `bound_service_account_namespaces` в роли Vault. Он должен совпадать с namespace пода.
- Pod не получил init container с Vault Agent — проверить что аннотация `vault.hashicorp.com/agent-inject: "true"` добавлена в `spec.template.metadata.annotations`, не в `metadata.annotations` Deployment.
- Vault Agent Injector не установлен — `helm install vault` без нужных флагов не ставит injector.

**Чек-лист для самопроверки:**
- [ ] Понимаю flow: Pod → JWT → Vault → token → секрет в файле
- [ ] Умею настроить Kubernetes Auth Method в Vault
- [ ] Знаю как добавить аннотации для Vault Agent Injector
- [ ] Понимаю разницу между Injector и VSO

**Попробуйте сами:**
1. Если есть кластер Kubernetes: включите Kubernetes Auth Method. Создайте ServiceAccount `myapp` в namespace `production`. Создайте роль в Vault. Запустите тестовый pod и выполните внутри `vault login -method=kubernetes role=myapp` — должен получить токен.
2. Установите Vault Agent Injector через Helm. Создайте Deployment с аннотациями. Проверьте что init container добавился: `kubectl describe pod myapp-xxx | grep vault`.
3. Прочитайте секрет из файла `/vault/secrets/database.env` внутри пода: `kubectl exec -it myapp-xxx -- cat /vault/secrets/database.env`.

---

### Глава 11: Production — Raft HA, Seal/Unseal, Backup

**Что вы узнаете:**
- Raft HA cluster: несколько нод для отказоустойчивости;
- автоматический unseal при перезапуске;
- резервное копирование и восстановление;
- мониторинг Vault.

**Цель:** читатель понимает что нужно для production-Vault который переживёт потерю одной ноды и умеет делать backup.

**Темы:**

Разместить Схему 5 (Seal/Unseal).

Раздел "Raft HA":
Объяснить что Raft — встроенное consensus-based хранилище. Для HA нужно нечётное число нод: 3 (переживает 1 сбой) или 5 (переживает 2 сбоя). Выбор leader автоматический.

```text
vault-1 (leader)  ← запросы идут сюда
vault-2 (standby) ← реплицирует данные
vault-3 (standby) ← реплицирует данные

Потеря vault-1 → vault-2 или vault-3 становится leader (автоматически)
Потеря 2 нод → quorum потерян, кластер не работает
```

```bash
# Добавить ноду в кластер
vault operator raft join http://vault-1:8200

# Посмотреть состояние кластера
vault operator raft list-peers
# Node       Address             State     Voter
# ----       -------             -----     -----
# vault-1    vault-1:8201        leader    true
# vault-2    vault-2:8201        follower  true
# vault-3    vault-3:8201        follower  true
```

Раздел "Backup и Restore":
```bash
# Snapshot Raft storage (полный бэкап)
vault operator raft snapshot save /tmp/vault-backup-$(date +%Y%m%d).snap

# Восстановить из snapshot
vault operator raft snapshot restore -force /tmp/vault-backup-20260601.snap
```

> ☠️ **Осторожно:** `snapshot restore -force` заменяет все текущие данные в Vault данными из snapshot. Все изменения после снапшота будут потеряны.

Раздел "Auto-unseal через Transit":
```hcl
# vault-config.hcl для второй ноды с auto-unseal
seal "transit" {
  address    = "http://vault-primary:8200"
  token      = "hvs.SERVICE_TOKEN"
  mount_path = "transit"
  key_name   = "autounseal-key"
}
```

Раздел "Recovery: generate-root (если потерян root token)":
Если root token утерян (а это случается), его можно восстановить через `generate-root` с unseal keys:
```bash
# Инициировать процесс восстановления
vault operator generate-root -init -otp
# One-Time Password (OTP): 3Fv8... ← показывается один раз

# Каждый ключ-холдер по очереди вводит unseal key
vault operator generate-root -otp=3Fv8... -nonce=abc123...
# Unseal Key 1 (will be hidden):
# Encoded Root Token: AbCdEf...

# Когда набран threshold (3 из 5) — собрать части
vault operator generate-root -otp=3Fv8... -nonce=abc123... -decode=AbCdEf...
# Root Token: hvs.XXXXXX
```
> ☠️ **Осторожно:** `generate-root` — единственный способ восстановить root token. Храни unseal keys в безопасном месте, разнесённом физически.

Раздел "Rekey — смена unseal keys":
Если unseal key holder уволился или ключи скомпрометированы:
```bash
# Начать rekey (5 новых ключей, порог 3)
vault operator rekey -init -key-shares=5 -key-threshold=3

# Каждый ключ-холдер вводит старый unseal key
vault operator rekey -nonce=abc123...
# Unseal Key 1 (will be hidden):
# Progress: 1/3

# После набора threshold — Vault выдаёт НОВЫЕ unseal keys
# Старые ключи перестают работать
```
Объяснить: rekey не перешифровывает данные — он меняет ключ шифрования master key. Все секреты остаются доступными. Процесс требует `threshold` старых ключей.

Раздел "DR: перенос Vault на другой сервер":
```bash
# 1. Сделать snapshot на старом сервере
vault operator raft snapshot save /tmp/vault-backup.snap

# 2. Скопировать snapshot на новый сервер
scp /tmp/vault-backup.snap new-server:/tmp/

# 3. На новом сервере: установить Vault, настроить такой же raft storage
# 4. Запустить Vault (он будет sealed — это нормально)
# 5. Восстановить из snapshot
vault operator raft snapshot restore -force /tmp/vault-backup.snap

# 6. Инициализировать (если нужно) и unseal с теми же ключами
# Если unseal keys утеряны вместе со старым сервером — данные недоступны.
# Вот почему unseal keys хранятся отдельно от Vault.
```
Указать: snapshot включает все секреты, политики, auth methods, leases. После restore нужен unseal с оригинальными ключами.

Раздел "Мониторинг":
```bash
# Встроенные метрики (Prometheus формат)
curl http://vault:8200/v1/sys/metrics?format=prometheus

# Ключевые метрики:
# vault_core_unsealed             = 1  (0 = sealed!)
# vault_runtime_num_goroutines    — активность
# vault_expire_num_leases         — количество активных leases
# vault_audit_log_request_failure — ошибки audit log (критично!)
```

Пример Prometheus scrape config:
```yaml
scrape_configs:
  - job_name: vault
    metrics_path: /v1/sys/metrics
    params:
      format: ['prometheus']
    bearer_token: "VAULT_TOKEN"
    static_configs:
      - targets: ['vault:8200']
```

**Типичные ошибки:**
- Не настроить backup — единственная нода с данными → потеря сервера = потеря всех секретов.
- Хранить единственную копию unseal keys на самом сервере — компрометация/потеря сервера = потеря unseal keys = Vault недоступен.
- Не мониторить `vault_core_unsealed` — Vault после рестарта sealed и приложения падают, а алертов нет.

**Чек-лист для самопроверки:**
- [ ] Понимаю Raft quorum: 3 ноды переживают потерю 1, 5 — потерю 2
- [ ] Умею сделать snapshot и восстановить из него
- [ ] Знаю что происходит с Vault при перезапуске (sealed) и как это решить
- [ ] Знаю ключевые метрики для мониторинга

**Попробуйте сами:**
1. Запустите Vault с Raft storage. Сделайте snapshot: `vault operator raft snapshot save backup.snap`. Запишите новый секрет. Восстановите из snapshot. Новый секрет исчез? (Так и должно быть — snapshot был до записи.)
2. Настройте Prometheus scraping метрик Vault. Найдите в Grafana или через `curl` значение `vault_core_unsealed`. Остановите Vault — метрика должна исчезнуть (или стать 0).
3. Настройте алерт в Alertmanager: если `vault_core_unsealed == 0` больше 2 минут — отправить уведомление. Протестируйте: остановите Vault и убедитесь что алерт сработал.

---

### Глава 12: Аудит, диагностика и типичные сценарии

**Что вы узнаете:**
- как включить audit log и что в нём хранится;
- как диагностировать ошибки доступа через audit log;
- типичные сценарии: ротация секрета, отзыв доступа, onboarding нового сервиса.

**Цель:** читатель умеет расследовать «почему приложение не получает секрет» и «кто читал этот секрет».

**Темы:**

Раздел "Audit Log":
```bash
# Включить audit log в файл
vault audit enable file file_path=/vault/logs/audit.log

# Включить audit log в syslog
vault audit enable syslog tag=vault facility=AUTH

# Список активных audit devices
vault audit list

# Отключить
vault audit disable file/
```

> ☠️ **Осторожно:** если Vault не может писать в audit log (диск полон, нет прав) — он перестаёт обрабатывать запросы. Настраивай минимум 2 audit backend. Мониторь место на диске для audit log.

Формат audit log (JSON):
```json
{
  "time": "2026-06-04T12:00:00Z",
  "type": "request",
  "auth": {
    "token_type": "service",
    "policies": ["myapp-policy", "default"],
    "display_name": "approle-myapp"
  },
  "request": {
    "id": "abc123",
    "operation": "read",
    "path": "secret/data/production/myapp/database",
    "remote_address": "10.0.0.5"
  }
}
```

Объяснить: request (входящий) и response (ответ, без значений секретов по умолчанию). `auth.display_name` — кто обратился. `request.path` — к чему. `request.operation` — что делал.

По умолчанию Vault хэширует (HMAC) чувствительные поля в audit log — display_name, policies. Для отладки можно отключить:
```bash
# Отключить HMAC для конкретного audit device (только для отладки!)
vault audit enable file file_path=/vault/logs/audit_raw.log hmac_accessor=false
```
> ☠️ **Осторожно:** `hmac_accessor=false` пишет display_name и token accessor в plaintext. Включать только на время расследования, отключать после.

```bash
# Найти все обращения к конкретному секрету
cat /vault/logs/audit.log | jq '. | select(.request.path == "secret/data/production/myapp/database")'

# Найти все 403 ошибки
cat /vault/logs/audit.log | jq '. | select(.response.error != null)'
```

Раздел "Типовые сценарии":

**Сценарий: onboarding нового сервиса**
```bash
# 1. Создать путь для секретов сервиса
vault kv put secret/production/newservice/database \
  host="db.internal" username="newservice_user" password="$(pwgen -s 32 1)"

# 2. Создать политику
vault policy write newservice-policy - << 'EOF'
path "secret/data/production/newservice/*" {
  capabilities = ["read"]
}
path "secret/metadata/production/newservice/*" {
  capabilities = ["list"]
}
EOF

# 3. Создать AppRole
vault write auth/approle/role/newservice \
  token_policies="newservice-policy" \
  token_ttl=1h \
  secret_id_ttl=10m \
  secret_id_num_uses=1

# 4. Передать role_id команде (не секрет)
vault read -field=role_id auth/approle/role/newservice/role-id
```

**Сценарий: ротация пароля**
```bash
# Обновить секрет (новая версия)
vault kv patch secret/production/myapp/database password="NewS3cr3tP@ss"

# Если сервис использует Vault Agent — он получит новый пароль автоматически
# Если читает напрямую — нужен рестарт или реализация ротации в приложении
```

**Сценарий: отзыв доступа уволившегося сотрудника**
```bash
# Найти accessor токена по display_name в audit log
vault list auth/token/accessors | xargs -I{} vault token lookup -accessor {}

# Отозвать по accessor (не нужен сам токен)
vault token revoke -accessor abc123xyz
# Все дочерние токены тоже отозваны
```

Раздел "Диагностика 403 Forbidden":
```text
Алгоритм:
1. Проверить что токен активен: vault token lookup
2. Проверить политики токена: vault token lookup | grep policies
3. Прочитать политику: vault policy read <name>
4. Проверить capabilities: vault token capabilities <token> <path>
5. Поискать в audit log: path + error
6. Проверить KV v2: путь должен быть secret/data/... не secret/...
```

**Типичные ошибки:**
- Audit log не включён — невозможно расследовать инциденты задним числом. Включить в первый день.
- `vault token capabilities` показывает права только для одного пути за раз. Для отладки нескольких — цикл.
- Политика написана для `secret/myapp/*` но KV v2 требует `secret/data/myapp/*` — права есть на неправильный путь.

**Чек-лист для самопроверки:**
- [ ] Включил audit log, знаю где он хранится
- [ ] Умею искать в audit log кто и когда обращался к секрету
- [ ] Знаю алгоритм диагностики 403: lookup → policy → capabilities → audit
- [ ] Умею выполнить onboarding нового сервиса за 4 команды

**Попробуйте сами:**
1. Включите audit log. Выполните несколько операций чтения и одну с ошибкой (доступ к пути без прав). Найдите в логе успешные и неуспешные запросы. Кто обращался, к чему, в какое время?
2. Создайте токен с политикой. Попробуйте обратиться к пути к которому нет доступа. Найдите ошибку в audit log. Исправьте политику. Убедитесь что теперь работает.
3. Найдите в audit log все обращения к конкретному секрету за последние 10 минут. Напишите jq-команду которая выводит: время, display_name, operation.

---

## Приложения

### Приложение A: Шпаргалка команд

Разделы: Базовые операции, KV v2, Политики, Auth Methods, AppRole, Kubernetes Auth, Database Engine, PKI Engine, Vault Agent, HA/Operator, Audit. Формат: комментарий + команда. Компактно — максимум 2 страницы.

### Приложение B: Типичные ошибки и диагноз

Таблица: симптом → вероятная причина → команда для проверки → решение. Включить минимум: 403, sealed vault, token expired, lease expired, database credentials rejected, K8s auth failed, agent не рендерит шаблон.

### Приложение C: Шаблоны HCL

Готовые шаблоны политик для типовых сценариев:
1. Read-only для одного сервиса (production)
2. Read-write для CI/CD (staging)
3. PKI: выпуск сертификатов для сервиса
4. Database: получение dynamic credentials
5. Admin: управление одним namespace

---

## Что читатель получит к концу книги

- Работающий Vault с Raft storage, переживающий перезапуск
- Секреты структурированы по окружениям и сервисам
- AppRole для CI/CD, Kubernetes Auth для K8s-подов
- Dynamic secrets для PostgreSQL: временные credentials с TTL
- PKI Engine: внутренний CA, автовыпуск сертификатов
- Vault Agent: приложение читает файл, не знает о Vault
- Audit log включён, знает как расследовать инциденты
- Понимание что делать при потере ключей, sealed vault, 403

---

## Чек-лист самопроверки агента перед сдачей главы

**Команды:**
- [ ] Каждая команда запущена — вывод реален, не вымышлен
- [ ] Если команды может не быть — показана установка (`sudo apt install vault` / `docker pull hashicorp/vault`)
- [ ] Dev-режим vs production явно указан для каждого примера
- [ ] Опасные операции (init, unseal, revoke, metadata delete) обёрнуты в `☠️ **Осторожно:**`

**Структура:**
- [ ] Глава начинается с «Что вы узнаете:» (список)
- [ ] Есть «Цель:» после списка
- [ ] Есть «Типичные ошибки»
- [ ] Есть «Чек-лист для самопроверки» (чекбоксы `- [ ]`)
- [ ] Есть «Попробуйте сами» (минимум 3 задания)

**Визуализация:**
- [ ] Хотя бы одна Mermaid-диаграмма или ASCII-схема
- [ ] Хотя бы одна таблица
- [ ] У схем есть подпись где разместить
- [ ] Mermaid-синтаксис корректен

**Безопасность:**
- [ ] Все `☠️ **Осторожно:**` на месте (особенно init, unseal, revoke, metadata delete)
- [ ] Dev-режим маркирован как «не для продакшна»
- [ ] Сценарий потери unseal keys описан в соответствующей главе

**Стиль:**
- [ ] Нет академизма — «покажи на примере», не «расскажи теорию»
- [ ] Нет Enterprise-фич без пометки `[Enterprise]`
- [ ] Vault не предлагается как решение для .env в local development (это избыточно)
- [ ] Каждый блок кода снабжён комментарием на русском
