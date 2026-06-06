# Глава 7: От контейнеров к Kubernetes — podman kube

## Что вы узнаете

- как сгенерировать K8s YAML из работающих контейнеров командой `podman kube generate`;
- как запустить K8s YAML локально без кластера через `podman kube play`;
- что такое `kind: Pod` и почему его нужно адаптировать в `Deployment` для продакшна;
- где заканчивается возможности Podman как K8s-симулятора.

---

## Зачем Podman как мост к Kubernetes

Типичная ситуация в команде:

```text
Разработчик                DevOps-инженер
─────────────────          ──────────────────────────
Знает Docker/Podman        Знает Kubernetes
Запускает через compose    Хочет K8s YAML для деплоя
Не знает K8s синтаксис     Не знает детали приложения

Проблема: передать конфигурацию запуска от разработчика к DevOps
```

`podman kube generate` решает это: разработчик настраивает контейнеры как умеет, затем экспортирует конфигурацию в K8s YAML. DevOps дорабатывает YAML для продакшна.

```text
Разработчик:
  podman pod create + podman run × N
      → podman kube generate → pod.yaml (черновик)

DevOps:
  pod.yaml → адаптация в Deployment → добавление ресурсов, probes, ConfigMap
      → kubectl apply (продакшн)

Тестирование (любой):
  podman kube play deployment.yaml  (без кластера K8s!)
```

Podman выступает мостом в обе стороны: `generate` достаёт YAML из работающих контейнеров, `play` запускает YAML обратно без кластера. Между ними — ручная адаптация Pod в Deployment.

```mermaid
flowchart LR
    pod["Работающий Pod\n(podman run × N)"]
    gen(["podman kube generate"])
    draft["pod.yaml\n(kind: Pod, черновик)"]
    adapt["адаптация:\nDeployment, реестр,\nsecrets, probes, resources"]
    deploy["deployment.yaml"]
    play(["podman kube play\n(локальный тест)"])
    kubectl(["kubectl apply\n(продакшн K8s)"])
    pod --> gen --> draft --> adapt --> deploy
    deploy --> play
    deploy --> kubectl
    style pod fill:#2d2d2d,color:#fff
    style draft fill:#7d6608,color:#fff
    style adapt fill:#4a235a,color:#fff
    style deploy fill:#1a5276,color:#fff
    style kubectl fill:#1e8449,color:#fff
```

Шаг «адаптация» здесь не опционален: `generate` всегда выдаёт `kind: Pod`, а в продакшн нужен `Deployment`.

---

## podman kube generate

`podman kube generate` экспортирует Pod или контейнер в K8s-совместимый YAML.

> ⚠️ **Важно:** команда создаёт `kind: Pod`, а **не** `kind: Deployment`.
>
> `Pod` подходит для локального тестирования, но для продакшна в Kubernetes нужен `Deployment`:
> - Deployment поддерживает репликацию (`replicas: 3`)
> - Deployment делает rolling update без даунтайма
> - Deployment автоматически пересоздаёт Pod при падении ноды
>
> После генерации — адаптировать YAML вручную. Пример трансформации в Приложении D.

### Шаг 1: создать Pod с контейнерами

```bash
# Создать pod
podman pod create --name webapp -p 8080:80

# Запустить контейнеры в pod
podman run -d --pod webapp --name nginx-web \
  -e NGINX_ENVSUBST_TEMPLATE_SUFFIX=.tmpl \
  nginx:alpine

podman run -d --pod webapp --name myapp-api \
  -e APP_ENV=production \
  -e LOG_LEVEL=info \
  myapp:latest

# Проверить что всё запустилось
podman pod ps
podman ps --pod
curl http://localhost:8080/health
```

### Шаг 2: сгенерировать YAML

```bash
# Экспортировать Pod в K8s YAML
podman kube generate webapp > webapp-pod.yaml

cat webapp-pod.yaml
```

Посмотрим что получилось:

```yaml
# Сгенерировано: podman kube generate webapp
apiVersion: v1
kind: Pod                        # ← Pod, не Deployment — это важно
metadata:
  creationTimestamp: "2024-05-28T10:00:00Z"
  labels:
    app: webapp
  name: webapp
spec:
  containers:
  - env:
    - name: NGINX_ENVSUBST_TEMPLATE_SUFFIX
      value: .tmpl
    image: docker.io/library/nginx:alpine
    name: nginx-web
    ports:
    - containerPort: 80
      hostPort: 8080             # ← будет убран при адаптации в Deployment
    resources: {}                # ← нужно заполнить
  - env:
    - name: APP_ENV
      value: production
    - name: LOG_LEVEL
      value: info
    image: localhost/myapp:latest  # ← localhost не работает в K8s!
    name: myapp-api
    resources: {}
  restartPolicy: Never           # ← Pod умрёт и не перезапустится
```

Что сразу видно что нужно исправить:
- `kind: Pod` → нужен `Deployment` для продакшна
- `localhost/myapp:latest` → нужен реальный реестр
- `resources: {}` → нужно заполнить requests/limits
- `restartPolicy: Never` → нужно `Always` или убрать
- Нет liveness/readiness probes

### Шаг 3: сгенерировать для отдельного контейнера

Можно также сгенерировать YAML для контейнера без Pod:

```bash
# Запустить контейнер
podman run -d --name single-nginx \
  -p 8080:80 \
  -e NGINX_HOST=example.com \
  nginx:alpine

# Экспортировать
podman kube generate single-nginx > single-pod.yaml
```

Но при запуске в K8s это всё равно будет Pod с одним контейнером. Без Pod-обёртки Podman создаёт Pod автоматически.

---

## podman kube play — запустить K8s YAML локально

`podman kube play` — это локальный «K8s-симулятор». Запускает K8s YAML без реального кластера. Отлично для тестирования конфигурации перед деплоем.

```bash
# Запустить из YAML
podman kube play webapp-pod.yaml

# Проверить
podman pod ps
podman ps

# Проверить работу
curl http://localhost:8080/

# Остановить и удалить всё что создал YAML
podman kube down webapp-pod.yaml
```

### Что поддерживает podman kube play

```text
Поддерживается:
  ✅ kind: Pod
  ✅ kind: Deployment (создаёт один Pod, репликация не работает)
  ✅ kind: PersistentVolumeClaim (создаёт named volume)
  ✅ env, envFrom, configMapKeyRef (если ConfigMap тоже в файле)
  ✅ volumes: hostPath, persistentVolumeClaim, emptyDir
  ✅ resources.limits/requests (применяется через cgroups)
  ✅ securityContext на уровне контейнера и Pod

Не поддерживается:
  ❌ kind: Service (LoadBalancer, ClusterIP — игнорируется)
  ❌ kind: Ingress
  ❌ kind: StatefulSet
  ❌ kind: DaemonSet
  ❌ replicas > 1 (создаётся только один Pod)
  ❌ init containers (частично)
  ❌ ServiceAccount, RBAC
```

### Несколько ресурсов в одном файле

```bash
# Можно передать файл с несколькими ресурсами через ---
cat > full-stack.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
---
apiVersion: v1
kind: Pod
metadata:
  name: webapp
spec:
  containers:
  - name: app
    image: myapp:latest
    envFrom:
    - configMapRef:
        name: app-config
EOF

podman kube play full-stack.yaml
```

---

## Рабочий процесс: от dev к K8s

Вот как это выглядит в реальной команде:

```text
День 1: разработка
─────────────────────────────────────────────────────
Разработчик:
  podman pod create --name myapp -p 8080:80
  podman run -d --pod myapp --name api myapp:dev
  podman run -d --pod myapp --name cache redis:alpine

  # Всё работает локально
  curl http://localhost:8080/api/status
  # {"status": "ok"}

День 2: генерация черновика
─────────────────────────────────────────────────────
  podman kube generate myapp > myapp-pod.yaml
  # Передать DevOps-инженеру

День 3: адаптация для K8s (DevOps)
─────────────────────────────────────────────────────
  # Трансформировать Pod → Deployment
  # Добавить: replicas, resources, probes, ConfigMap
  # Заменить localhost/ → registry.example.com/

  # Протестировать локально:
  podman kube play myapp-deployment.yaml
  curl http://localhost:8080/api/status

  # Деплоить:
  kubectl apply -f myapp-deployment.yaml
```

---

## Пример: полный цикл

Разберём на реальном примере с PostgreSQL и Python-приложением.

### Создать Pod

```bash
podman pod create --name pgapp \
  -p 5432:5432 \
  -p 8000:8000

podman run -d --pod pgapp --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=myapp \
  -e POSTGRES_USER=myapp \
  postgres:16-alpine

podman run -d --pod pgapp --name api \
  -e DATABASE_URL=postgresql://myapp:secret@localhost:5432/myapp \
  myapp:latest

# Проверить
podman pod ps
curl http://localhost:8000/health
```

### Сгенерировать YAML

```bash
podman kube generate pgapp > pgapp-pod.yaml
```

### Что получится и что нужно исправить

```yaml
# Что сгенерировал Podman (annotations убраны для краткости):
apiVersion: v1
kind: Pod
metadata:
  name: pgapp
spec:
  containers:
  - env:
    - name: POSTGRES_DB
      value: myapp
    - name: POSTGRES_PASSWORD
      value: secret          # ⚠️ секрет в открытом виде!
    - name: POSTGRES_USER
      value: myapp
    image: docker.io/library/postgres:16-alpine
    name: postgres
    ports:
    - containerPort: 5432
      hostPort: 5432
    resources: {}
    volumeMounts: []
  - env:
    - name: DATABASE_URL
      value: postgresql://myapp:secret@localhost:5432/myapp  # ⚠️ секрет!
    image: localhost/myapp:latest   # ⚠️ localhost не работает в K8s
    name: api
    ports:
    - containerPort: 8000
      hostPort: 8000
    resources: {}
  restartPolicy: Never
```

**Что нужно исправить перед деплоем в K8s:**

1. `kind: Pod` → `kind: Deployment` (см. Приложение D)
2. Пароли вынести в `kind: Secret` и использовать `secretKeyRef`
3. `localhost/myapp:latest` → `registry.example.com/myapp:v1.2.3`
4. Заполнить `resources.requests/limits`
5. Добавить `readinessProbe` и `livenessProbe`
6. Убрать `hostPort` (для K8s используется `Service`)
7. Добавить `PersistentVolumeClaim` для данных PostgreSQL

### Тест через podman kube play

```bash
# Сначала остановить текущий pod
podman kube down pgapp-pod.yaml

# После адаптации (или прямо черновик):
podman kube play pgapp-pod.yaml

# Проверить
podman pod ps
curl http://localhost:8000/health

# Убрать
podman kube down pgapp-pod.yaml
```

---

## Secrets в K8s YAML

Когда адаптируете Pod в Deployment — вынесите секреты в `kind: Secret`:

```yaml
# secrets.yaml (не коммитить в git!)
apiVersion: v1
kind: Secret
metadata:
  name: pgapp-secrets
type: Opaque
stringData:
  POSTGRES_PASSWORD: secret
  DATABASE_URL: postgresql://myapp:secret@postgres:5432/myapp
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: registry.example.com/myapp:v1.2.3
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: pgapp-secrets
              key: DATABASE_URL
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## Типичные ошибки

**Задеплоить Pod YAML в K8s продакшн без изменений**
Pod без Deployment не перезапустится при падении ноды. Не масштабируется. Не делает rolling update. Обязательно адаптировать.

**`localhost/myapp:latest` в сгенерированном YAML**
Kubernetes не может скачать образ с `localhost`. Перед деплоем:
```bash
podman tag myapp:latest registry.example.com/myapp:v1.0.0
podman push registry.example.com/myapp:v1.0.0
# Затем в YAML заменить:
# image: registry.example.com/myapp:v1.0.0
```

**Пароли в сгенерированном YAML**
`podman kube generate` честно экспортирует переменные окружения — включая пароли. Никогда не коммитьте такой YAML в git. Перед коммитом заменить значения на ссылки на Secret.

**`podman kube play` создаёт Pod, не Deployment**
Если передать `kind: Deployment` — Podman создаст Pod (один экземпляр, без реальной репликации). Это нормально для локального теста, в реальном K8s всё работает как ожидается.

---

## Чек-лист для самопроверки

- [ ] Создал Pod с двумя контейнерами и сгенерировал K8s YAML через `podman kube generate`
- [ ] Запустил сгенерированный YAML через `podman kube play` и проверил работу
- [ ] Понимаю разницу между `kind: Pod` и `kind: Deployment` и почему Pod не подходит для продакшна
- [ ] Знаю что нужно исправить в YAML перед деплоем в реальный K8s (реестр, секреты, resources, probes)
- [ ] Остановил тестовый запуск через `podman kube down`

## Попробуйте сами

1. Создайте Pod с nginx и выполните полный цикл:
   ```bash
   podman pod create --name nginx-pod -p 8080:80
   podman run -d --pod nginx-pod --name web nginx:alpine
   podman kube generate nginx-pod > nginx-pod.yaml
   cat nginx-pod.yaml  # изучите что сгенерировалось
   podman kube down nginx-pod.yaml
   podman kube play nginx-pod.yaml
   curl http://localhost:8080
   podman kube down nginx-pod.yaml
   ```

2. Откройте сгенерированный `nginx-pod.yaml` и найдите:
   - Какой `kind`?
   - Есть ли `resources`?
   - Есть ли `readinessProbe`?
   - Какой `image` указан — полный путь или сокращённый?

3. Откройте Приложение D и попробуйте вручную адаптировать ваш `nginx-pod.yaml` в `Deployment`. Запустите результат через `podman kube play` и проверьте что работает.
