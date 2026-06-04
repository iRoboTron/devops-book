# Глава 10: PostgreSQL в Docker и Kubernetes

**Что вы узнаете:**
- правильная конфигурация PostgreSQL-контейнера: секреты, healthcheck, shm_size;
- PostgreSQL в Kubernetes: StatefulSet, PVC, headless service;
- PgBouncer sidecar в K8s: локальный пул на под;
- Terraform-провижининг БД, пользователей, схем;
- CloudNativePG — оператор для production PostgreSQL в K8s;
- cert-manager для SSL-сертификатов в K8s.

**Цель:** читатель запускает PostgreSQL в Kubernetes надёжно: данные переживают рестарт пода, секреты не в plaintext, бэкапы работают.

---

## Docker: production-ready конфигурация

```yaml
# docker-compose.yml — production-ready PostgreSQL
services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_USER: appuser
      POSTGRES_DB: myapp
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.utf8"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./config/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
      -c hba_file=/etc/postgresql/pg_hba.conf
    ports:
      - "127.0.0.1:5432:5432"   # только localhost
    secrets:
      - postgres_password
    shm_size: '256mb'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M

volumes:
  pgdata:

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

```text
secrets/postgres_password.txt:
ProductionPassw0rd!
```

> ☠️ **Осторожно:** `POSTGRES_PASSWORD` в `environment` — пароль виден в `docker inspect` и попадает в shell history. Используй `POSTGRES_PASSWORD_FILE` + Docker secrets для production.

### Ключевые элементы конфигурации

**shm_size: '256mb'**
PostgreSQL использует `/dev/shm` для shared memory (буферы, сортировки, hash join). В Docker по умолчанию `/dev/shm` = 64MB, этого мало. Без увеличения `shm_size` PostgreSQL может падать с ошибкой:
```
ERROR:  could not resize shared memory segment
```
Минимум 256MB, для production — 1GB.

**healthcheck**
`pg_isready` проверяет что PostgreSQL отвечает на порту 5432. Без healthcheck Docker не знает что PostgreSQL "жив" — контейнер работает даже если PostgreSQL упал.

**config files mounted как :ro**
Конфиги монтируются read-only — приложение не может изменить их изнутри контейнера. Изменения конфигурации — только через перемонтирование volume или `ALTER SYSTEM`.

**init-scripts**
Любые `.sql` или `.sh` файлы в `/docker-entrypoint-initdb.d/` выполняются однократно при первом запуске (когда PGDATA пуста). Туда кладут: `CREATE EXTENSION`, `CREATE ROLE`, `GRANT`, создание схем.

---

## Kubernetes: StatefulSet

PostgreSQL в Kubernetes — не Deployment, а StatefulSet. Разница:

```text
Deployment:
  - Под имеет случайное имя (postgres-6f9d7b84c5-ab3cd)
  - PVC не привязан к поду (общий)
  - Масштабирование = копии с одинаковым состоянием
  - Не подходит для stateful приложений

StatefulSet:
  - Под имеет стабильное имя (postgres-0, postgres-1)
  - Каждый под имеет свой PVC (pgdata-postgres-0)
  - Масштабирование = упорядоченное (0, 1, 2...)
  - Гарантирует уникальность и identity
```

### StatefulSet манифест

```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: production
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16.3-alpine      # версия зафиксирована
          ports:
            - containerPort: 5432
              name: postgres
          env:
            - name: POSTGRES_USER
              value: "appuser"
            - name: POSTGRES_DB
              value: "myapp"
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
            - name: postgres-config
              mountPath: /etc/postgresql/postgresql.conf
              subPath: postgresql.conf
              readOnly: true
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1"
          readinessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - appuser
                - -d
                - myapp
            initialDelaySeconds: 15
            periodSeconds: 10
            failureThreshold: 5
          livenessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - appuser
                - -d
                - myapp
            initialDelaySeconds: 60
            periodSeconds: 30
            failureThreshold: 3
      volumes:
        - name: postgres-config
          configMap:
            name: postgres-config
  volumeClaimTemplates:
    - metadata:
        name: pgdata
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
        storageClassName: standard
```

### Headless service

StatefulSet требует headless service (clusterIP: None) для стабильных DNS-имен.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: production
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None     # headless: DNS → pod IP напрямую
```

Без headless service StatefulSet не может гарантировать что `postgres-0.production.svc.cluster.local` всегда указывает на правильный под.

### ConfigMap для конфигурации

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
  namespace: production
data:
  postgresql.conf: |
    shared_buffers = 512MB
    max_connections = 50
    wal_level = replica
    log_min_duration_statement = 1000
    ...
```

### ReadinessProbe vs LivenessProbe

```text
readinessProbe:
  - Проверяет: готов ли под принимать трафик?
  - Если fail → под убирается из Service (не получает запросы)
  - Использует pg_isready — быстрая проверка (1-2 секунды)
  - Начинается через 15 секунд после старта

livenessProbe:
  - Проверяет: жив ли процесс?
  - Если fail → под перезапускается
  - Использует pg_isready — но с большим initialDelaySeconds
  - Не должен срабатывать при обычной загрузке
```

> Не использовать `psql -c "SELECT 1"` для liveness — это нагружает базу. `pg_isready` не выполняет запрос, только проверяет сокет.

---

## PgBouncer sidecar в K8s

В Kubernetes PgBouncer можно запустить двумя способами:

### Вариант 1: PgBouncer sidecar (локальный пул)

На каждый под приложения — свой PgBouncer в том же pod. Приложение подключается к localhost:6432.

```yaml
# Pod с PgBouncer sidecar
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: app
          image: myapp:latest
          env:
            - name: DATABASE_URL
              value: "postgresql://appuser:password@localhost:6432/myapp"
          ports:
            - containerPort: 8080

        - name: pgbouncer
          image: edoburu/pgbouncer:latest
          env:
            - name: DATABASE_URL
              value: "postgresql://appuser:password@postgres-service:5432/myapp"
            - name: POOL_MODE
              value: "transaction"
            - name: DEFAULT_POOL_SIZE
              value: "10"
            - name: MAX_CLIENT_CONN
              value: "100"
          ports:
            - containerPort: 6432
              name: pgbouncer
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
```

### Вариант 2: Централизованный PgBouncer

Один PgBouncer (или несколько через Deployment) на весь кластер. Все поды подключаются к нему.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pgbouncer
  template:
    metadata:
      labels:
        app: pgbouncer
    spec:
      containers:
        - name: pgbouncer
          image: edoburu/pgbouncer:latest
          env:
            - name: DATABASE_URL
              value: "postgresql://appuser:password@postgres-service:5432/myapp"
            - name: POOL_MODE
              value: "transaction"
            - name: DEFAULT_POOL_SIZE
              value: "20"
            - name: MAX_CLIENT_CONN
              value: "500"
          ports:
            - containerPort: 6432
---
apiVersion: v1
kind: Service
metadata:
  name: pgbouncer
spec:
  selector:
    app: pgbouncer
  ports:
    - port: 6432
```

### Trade-offs: sidecar vs централизованный

```text
Sidecar (локальный пул):
✓ Минимальная латентность (localhost, нет сетевого hop)
✓ Изоляция: один pod не может исчерпать пул для других
✓ Проще конфигурация (каждый под сам за себя)
✗ Больше ресурсов (N подов × PgBouncer)
✗ Больше соединений к PostgreSQL (N подов × default_pool_size)

Централизованный:
✓ Меньше ресурсов (2 реплики PgBouncer на кластер)
✓ Единая точка конфигурации и мониторинга
✓ Меньше соединений к PostgreSQL
✗ Дополнительная сетевая задержка
✗ Single point of failure (нужны реплики + service)
✗ Один pod может исчерпать пул для всех

Рекомендация:
- < 10 подов → централизованный (проще управлять)
- > 10 подов → sidecar (изоляция и latency)
- Для высоконагруженных сервисов → sidecar
```

---

## Terraform-провижининг PostgreSQL

Terraform может управлять не только инфраструктурой, но и самой PostgreSQL: базы данных, роли, схемы, права. Это IaC для схемы данных.

### Провайдер

```hcl
# providers.tf
terraform {
  required_providers {
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.22"
    }
  }
}

provider "postgresql" {
  host     = var.pg_host
  port     = 5432
  database = "postgres"
  username = var.pg_admin_user
  password = var.pg_admin_password
  sslmode  = "require"
}
```

### Ресурсы

```hcl
# main.tf

# База данных приложения
resource "postgresql_database" "myapp" {
  name  = "myapp"
  owner = postgresql_role.appuser.name
  template = "template0"
  encoding = "UTF8"
  lc_collate = "en_US.UTF-8"
  lc_ctype   = "en_US.UTF-8"

  # Запретить публичные схемы по умолчанию
  allow_connections = true
}

# Роль приложения
resource "postgresql_role" "appuser" {
  name     = "appuser"
  login    = true
  password = var.appuser_password
  connection_limit = 50
}

# Read-only роль для мониторинга
resource "postgresql_role" "monitoring" {
  name     = "monitoring"
  login    = true
  password = var.monitoring_password
}

resource "postgresql_grant_role" "monitoring_pg_monitor" {
  role        = postgresql_role.monitoring.name
  grant_role  = "pg_monitor"
}

# Схема приложения
resource "postgresql_schema" "app" {
  name     = "app"
  database = postgresql_database.myapp.name
  owner    = postgresql_role.appuser.name

  depends_on = [postgresql_database.myapp]
}

# Default privileges — чтобы новые таблицы автоматически получали права
resource "postgresql_default_privileges" "app_tables" {
  database  = postgresql_database.myapp.name
  owner     = postgresql_role.appuser.name
  schema    = postgresql_schema.app.name
  role      = postgresql_role.appuser.name
  object_type = "table"
  privileges = ["SELECT", "INSERT", "UPDATE", "DELETE"]
}

resource "postgresql_default_privileges" "app_sequences" {
  database  = postgresql_database.myapp.name
  owner     = postgresql_role.appuser.name
  schema    = postgresql_schema.app.name
  role      = postgresql_role.appuser.name
  object_type = "sequence"
  privileges = ["USAGE", "SELECT"]
}

# Расширения
resource "postgresql_extension" "pg_stat_statements" {
  database = postgresql_database.myapp.name
  name     = "pg_stat_statements"
  schema   = "public"
}
```

### Применение

```bash
terraform init
terraform plan
terraform apply
```

После `terraform apply`:
- База `myapp` создана.
- Пользователь `appuser` создан с паролем из переменной.
- Схема `app` создана, владелец — `appuser`.
- Default privileges настроены — новые таблицы в схеме `app` будут доступны `appuser`.

> Terraform-провижининг заменяет init-скрипты в `/docker-entrypoint-initdb.d/` и даёт версионирование схемы прав. Изменения в правах — через PR, review, apply.

### Когда Terraform не подходит

```text
Terraform хорош для:
- Создание БД, ролей, схем
- Настройка прав и default privileges
- Управление расширениями

Terraform не для:
- Миграций схемы данных (ALTER TABLE) — это задача миграционных инструментов
- Управления данными — Terraform не должен вставлять/обновлять строки
- Настройки performance параметров — для этого postgresql.conf или ALTER SYSTEM
```

---

## CloudNativePG — оператор PostgreSQL для K8s

CloudNativePG (CNPG) — оператор Kubernetes, который управляет PostgreSQL-кластерами: репликация, бэкапы, failover, восстановление. Всё через Custom Resources (CR).

### Установка

```bash
kubectl apply -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.0.yaml

# Проверить
kubectl get pods -n cnpg-system
# cnpg-controller-manager-...   1/1   Running
```

### Кластер PostgreSQL

```yaml
# cluster.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: myapp-postgres
  namespace: production
spec:
  # 1 primary + 2 replicas
  instances: 3

  imageName: ghcr.io/cloudnative-pg/postgresql:16.3

  # Версия PostgreSQL
  postgresql:
    parameters:
      shared_buffers: "512MB"
      max_connections: "100"
      wal_level: replica
      log_min_duration_statement: "1000"

  # Персистентность
  storage:
    size: 20Gi
    storageClass: standard

  # Суперпользователь
  superuserSecret:
    name: postgres-superuser-secret

  # Ресурсы
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1"

  # Бэкапы в S3
  backup:
    barmanObjectStore:
      destinationPath: "s3://my-bucket/myapp-postgres"
      s3Credentials:
        accessKeyId:
          name: aws-creds
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: aws-creds
          key: ACCESS_SECRET_KEY
      wal:
        compression: gzip
    retentionPolicy: "7d"

  # Scheduled backups
  scheduledBackup:
    - name: daily-backup
      schedule: "0 2 0 0 0"    # каждый день в 2:00
      backupOwnerReference: self
```

### Что делает CNPG автоматически

```text
- Репликация: настраивает streaming replication между подами
- Failover: при падении primary — автоматически promotes реплику
- Бэкапы: WAL archiving + полные бэкапы по расписанию (через barman)
- Восстановление: point-in-time recovery через CR
- Мониторинг: экспорт метрик для Prometheus
- Обновление: rolling update PostgreSQL без downtime

Клиент подключается через headless service:
  postgres://appuser:password@myapp-postgres-rw.production.svc:5432/myapp
  # -rw — read-write endpoint (primary)
  # -ro — read-only endpoint (replicas)
```

### Восстановление из бэкапа

```yaml
# restore.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: restore-test
spec:
  cluster:
    name: myapp-postgres
```

У CNPG есть `recovery` объекты для PITR — восстановление на точный момент времени через CR.

---

## cert-manager для SSL в K8s

В Kubernetes SSL-сертификаты для PostgreSQL можно управлять через cert-manager — автоматическая генерация и ротация.

```yaml
# issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: postgres-selfsigned
spec:
  selfSigned: {}
```

```yaml
# certificate.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: postgres-tls
  namespace: production
spec:
  secretName: postgres-tls-secret
  duration: 2160h   # 90 дней
  renewBefore: 360h  # за 15 дней до истечения
  commonName: postgres.production.svc
  dnsNames:
    - postgres.production.svc
    - "*.production.svc"
  issuerRef:
    name: postgres-selfsigned
    kind: ClusterIssuer
```

```yaml
# StatefulSet — монтируем сертификаты
spec:
  template:
    spec:
      containers:
        - name: postgres
          volumeMounts:
            - name: tls
              mountPath: /etc/postgresql/tls
              readOnly: true
      volumes:
        - name: tls
          secret:
            secretName: postgres-tls-secret
```

```ini
# postgresql.conf (в ConfigMap)
ssl = on
ssl_cert_file = '/etc/postgresql/tls/tls.crt'
ssl_key_file = '/etc/postgresql/tls/tls.key'
ssl_ca_file = '/etc/postgresql/tls/ca.crt'
```

```text
Что даёт cert-manager:
- Автоматическая генерация сертификатов при создании
- Ротация до истечения (renewBefore)
- Хранение в Kubernetes Secret (не монтировать секреты как ConfigMap)
- Поддержка Let's Encrypt для публичных сертификатов
```

---

## Памятка: PostgreSQL в K8s — ключевые правила

```text
1. Всегда StatefulSet, не Deployment
   — PVC привязан к поду, стабильное DNS-имя

2. Всегда PVC с ReadWriteOnce
   — emptyDir = потеря данных при рестарте

3. Всегда фиксировать версию образа
   — postgres:16.3-alpine, не postgres:latest
   — latest при следующем deploy может обновиться до 17

4. Всегда shm_size ≥ 256MB
   — без этого PostgreSQL крашится под нагрузкой

5. Всегда readinessProbe + livenessProbe
   — pg_isready, не SELECT 1

6. Всегда пароль через Secret, не в env
   — PostgreSQL: POSTGRES_PASSWORD_FILE + Docker secrets

7. Для production — CloudNativePG
   — репликация, бэкапы, failover из коробки
```

---

## Типичные ошибки

- **Хранить данные PostgreSQL в `emptyDir`** — при рестарте пода все данные теряются. Только PVC с `ReadWriteOnce`.
- **Запускать PostgreSQL как `Deployment`** — нет гарантий уникальности пода и стабильного DNS. После пересоздания — новый под с новым именем, данные из старого PVC не подключатся.
- **`shm_size` не указан** — `/dev/shm` всего 64MB. PostgreSQL использует shared memory для буферов и сортировки. Без увеличения — ошибки "could not resize shared memory segment" под нагрузкой.
- **Использовать `latest` тег образа** — обновление произойдёт неожиданно при следующем pull. `latest` привязан к дате pull, не к версии.
- **Не настроен cert-manager** — ручное управление SSL-сертификатами не масштабируется. Автоматическая ротация через cert-manager обязательна для production.
- **Terraform для миграций схемы** — Terraform управляет БД, ролями, правами. Миграции таблиц — это expand/contract (Глава 11).
- **PgBouncer sidecar без лимитов** — не указать resources для PgBouncer — он может отнять память у основного контейнера.
- **CloudNativePG с `instances: 1`** — одного instance недостаточно для failover. Минимум 3 для production (primary + 2 replicas).

---

## Чек-лист для самопроверки

- [ ] Знаю почему PostgreSQL в K8s должен быть StatefulSet, не Deployment
- [ ] Умею настроить PVC для персистентности данных
- [ ] Понимаю зачем нужен `shm_size` в Docker
- [ ] Умею запустить PgBouncer sidecar и знаю trade-offs vs централизованный
- [ ] Знаю как настроить Terraform-провайдер для PostgreSQL и создать базу, роль, схему
- [ ] Умею установить CloudNativePG и создать кластер с бэкапами в S3
- [ ] Понимаю зачем нужен cert-manager для SSL в K8s
- [ ] Знаю разницу между readinessProbe и livenessProbe

---

## Попробуйте сами

1. Запустите PostgreSQL в K8s как StatefulSet. Запишите данные (`CREATE TABLE test (id int); INSERT INTO test VALUES (1);`). Удалите под (`kubectl delete pod postgres-0`). Дождитесь пересоздания. Данные сохранились?

2. Посмотрите через `kubectl describe pvc` — какой StorageClass используется? Что произойдёт с данными при удалении PVC?

3. Добавьте PgBouncer sidecar к поду приложения. Проверьте что приложение подключается к `localhost:6432`. Посмотрите логи PgBouncer — видно подключения?

4. Напишите Terraform-конфигурацию: провайдер postgresql → база `myapp` → роль `appuser` → схема `app` → default privileges. Примените. Проверьте что база создана.

5. Установите CloudNativePG в K8s (kind/minikube). Создайте кластер с 3 instance. Проверьте `kubectl get pods` — 3 пода PostgreSQL. Удалите primary под — наблюдайте failover.
