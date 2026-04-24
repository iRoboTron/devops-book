# Инструкция агенту: улучшение книги 18 «Cloud, Docker и Kubernetes Security»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/18-cloud-container-security-devops/
```

Книга: 1221 строка. Структура правильная. Главная проблема: **секреты в Docker-слоях упомянуты как риск, но не показано как именно они туда попадают и как их найти** — это и есть главная магия которую нужно объяснить. Второй блок: `trivy image` упомянут но вывод не показан.

---

## Общее правило для раздела «Типовые слабые места»

Применить тот же принцип что в книге 17: каждый риск → механика → как найти. Это касается разделов X.2 во всех главах.

---

## Задачи по главам

---

### Глава 3 (`chapter-03.md`) — Secrets и конфиденциальные данные

**Проблема:** Написано «секреты baked-in в Docker image» — риск назван, но не показано как это происходит и как найти.

**Добавить** раздел **3.3а «Как секрет попадает в layer»:**

Плохой Dockerfile:
```dockerfile
FROM python:3.12-slim
ENV DATABASE_URL=postgres://user:SuperSecret@db:5432/app   # ← записан в layer
RUN pip install -r requirements.txt
COPY . .
```

```bash
# Собрать образ
docker build -t myapp:bad .

# Посмотреть слои
docker history myapp:bad
```

```
IMAGE          CREATED   CREATED BY                                      SIZE
abc123         5m ago    COPY . . # buildkit                             2.1MB
def456         5m ago    pip install -r requirements.txt                  45MB
ghi789         5m ago    ENV DATABASE_URL=postgres://user:SuperSecret...  0B
                         ↑ секрет виден в метаданных образа
```

```bash
# Найти секрет в образе
docker inspect myapp:bad | grep -i "DATABASE_URL\|SECRET\|PASSWORD"

# Ещё надёжнее — сканировать всё
docker save myapp:bad | tar -xO | strings | grep -i "password\|secret\|token" | head -20
```

Это означает: любой у кого есть доступ к образу в registry — видит этот секрет.

Правильный подход:
```dockerfile
FROM python:3.12-slim
RUN pip install -r requirements.txt
COPY . .
# Без ENV с секретами — переменные передаются в runtime через --env-file
```

```bash
# Запуск с секретами через файл (не в образе)
docker run --env-file .env myapp:prod
```

**Добавить** в раздел 3.4 Шаг 1 команду `trivy` для поиска секретов в образе:

```bash
trivy image --scanners secret myapp:latest
```

```
myapp:latest (debian 12.5)
Total: 2 (SECRET: 2)

┌─────────────────────┬────────────────────┬──────────────────────────────────┐
│ Target              │ Secret Type        │ Match                            │
├─────────────────────┼────────────────────┼──────────────────────────────────┤
│ /app/.env           │ Generic API Key    │ API_KEY=sk-proj-abc123...        │
│ /usr/src/app/config │ AWS Access Key     │ AKIA...                          │
└─────────────────────┴────────────────────┴──────────────────────────────────┘
```

---

### Глава 4 (`chapter-04.md`) — Container runtime security

**Добавить** раздел **4.5 «Запустить контейнер не под root»:**

По умолчанию большинство контейнеров работают от root. Это проблема: если есть побег из контейнера, атакующий получает root на хосте.

```bash
# Проверить от кого работает текущий контейнер
docker run --rm myapp:latest whoami
# root  ← проблема

# Правильный Dockerfile
FROM python:3.12-slim
RUN useradd -r -u 1001 appuser
USER appuser
...
```

```bash
docker run --rm myapp:fixed whoami
# appuser  ← правильно
```

Или запустить с явным запретом root:
```bash
docker run --user 1001:1001 myapp:latest
```

Проверить все контейнеры в системе:
```bash
docker ps -q | xargs -I{} docker inspect {} --format '{{.Name}} {{.Config.User}}' 2>/dev/null
# Пустой User = root — проверить каждый
```

---

### Глава 5 (`chapter-05.md`) — Kubernetes security

**Добавить** в практику проверку что Pod не работает от root:

```bash
# Проверить от кого работают Pod'ы
kubectl get pods -n prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext.runAsUser}{"\n"}{end}'
```

Если `runAsUser` пустой — Pod работает от root (по умолчанию).

Добавить `securityContext` в Deployment:
```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
```

---

### Глава 6 (`chapter-06.md`) — Registry и supply chain

**Проблема:** `trivy image` упомянут без вывода. Нет полного примера сканирования с интерпретацией.

**Добавить** полный пример `trivy scan` в раздел 6.4:

```bash
trivy image --severity HIGH,CRITICAL myapp:latest
```

```
myapp:latest (debian 12.5)
Total: 3 (HIGH: 2, CRITICAL: 1)

┌────────────┬────────────────┬──────────┬──────────────────┬────────────────────┐
│  Library   │ Vulnerability  │ Severity │ Installed Version│  Fixed Version     │
├────────────┼────────────────┼──────────┼──────────────────┼────────────────────┤
│ openssl    │ CVE-2023-5678  │ CRITICAL │ 3.0.2-0ubuntu1   │ 3.0.2-0ubuntu1.12  │
│ libssl3    │ CVE-2024-0727  │ HIGH     │ 3.0.2-0ubuntu1   │ 3.0.2-0ubuntu1.14  │
│ python3.11 │ CVE-2023-6597  │ HIGH     │ 3.11.2           │ 3.11.8             │
└────────────┴────────────────┴──────────┴──────────────────┴────────────────────┘
```

Что делать с результатом:
- `CRITICAL` в base image → обновить `FROM` тег, пересобрать
- `HIGH` в зависимости → обновить пакет в `requirements.txt`/`package.json`
- Не обновлять всё разом — сначала проверить что сломается

**Добавить** в раздел 6.4 проверку что prod использует digest а не `latest`:

```bash
# Плохо — latest может измениться
docker pull myapp:latest

# Правильно — digest неизменен
docker pull myapp@sha256:abc123def456...

# Получить digest текущего образа
docker inspect --format='{{index .RepoDigests 0}}' myapp:latest
# ghcr.io/user/myapp@sha256:abc123...

# Использовать digest в Deployment
# image: ghcr.io/user/myapp@sha256:abc123def456...
```

---

### Глава 7 (`chapter-07.md`) — IAM и минимальные привилегии

**Добавить** в практику проверку IAM policies (для cloud):

```bash
# AWS: посмотреть реальные права текущей роли
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/myapp-role \
  --action-names s3:DeleteBucket s3:PutObject ec2:TerminateInstances \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' \
  --output table
```

```
s3:DeleteBucket    | implicitDeny  ← правильно
s3:PutObject       | allowed       ← нужно приложению
ec2:TerminateInstances | implicitDeny ← правильно
```

Цель — убедиться что роль приложения не может делать то что ей не нужно.

---

## Приоритет

1. Глава 3 — добавить полное объяснение как секрет попадает в Docker layer, `docker history`, `docker save | strings`
2. Глава 6 — полный пример `trivy` вывода с интерпретацией
3. Глава 4 — проверка non-root контейнеров
4. Глава 5 — securityContext для Pod'ов

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-18-improve.md`*
