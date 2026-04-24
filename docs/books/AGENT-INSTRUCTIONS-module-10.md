# Инструкция для ИИ-агента: Написание книги по Kubernetes (Основы)

> **Это Модуль 10 курса DevOps 2.0.**
> Предварительные требования: пройдены модули 1–9 (включая Docker, Terraform, Ansible).
> Смотри также:
> - [AGENT-INSTRUCTIONS-module-03.md](AGENT-INSTRUCTIONS-module-03.md) — Модуль 3 (Docker)
> - [AGENT-INSTRUCTIONS-module-09.md](AGENT-INSTRUCTIONS-module-09.md) — Модуль 9 (Ansible)

---

## Контекст проекта

Ученик умеет запускать приложения в Docker-контейнерах и автоматически деплоить их через GitHub Actions.
Он столкнулся с проблемами: контейнер упал — не поднялся сам, нагрузка выросла — нет масштабирования, нужно обновить — есть даунтайм.

**Что он уже умеет** (не повторяй):
- Пишет Dockerfile и docker-compose.yml
- Знает Docker-сети, тома, healthcheck
- Деплоил через GitHub Actions: build → push → ssh → docker-compose up
- Прошёл Terraform и Ansible — понимает декларативное описание состояния
- Умеет читать YAML (Ansible, Docker Compose)

**Что его раздражает прямо сейчас:**
- Контейнер упал в 3 ночи — никто не перезапустил (restart: unless-stopped не всегда спасает)
- Трафик вырос → один контейнер не справляется → нет горизонтального масштабирования
- Обновление приложения = секунды даунтайма
- Нужно поднять ещё один такой же стек для staging — копирую docker-compose вручную

**Что он хочет после этой книги:**
Задеплоить Python-приложение так, чтобы оно само перезапускалось при падении, обновлялось без даунтайма, и его можно было масштабировать одной командой.

---

## Что за книга

**Название:** "Kubernetes: Основы"

**Место в курсе:** Книга 10 из 14

**Целевая аудитория:**
- Уверенно работает с Docker и docker-compose
- Слышал про Kubernetes, пробовал читать — не понял
- Хочет понять зачем K8s, прежде чем учить команды

**Объём:** 150-180 страниц

**Стиль:**
- Простой язык
- Аналогии с Docker (читатель его знает — используй как мост)
- ASCII-схемы для архитектуры
- Много практики на k3s (локально, без облака)
- Без воды

---

## Главная идея, которую должна передать книга

Kubernetes решает три проблемы которые docker-compose не решает:

```
docker-compose:          Kubernetes:
1 хост                   Много хостов (кластер)
Нет авто-восстановления  Упал Pod → поднялся автоматически
Нет масштабирования      Нагрузка выросла → добавь реплики
Обновление = даунтайм    Rolling update → нет даунтайма
```

**Ключевое понимание:**
K8s — это не "большой docker-compose". Это платформа которая следит за желаемым состоянием и постоянно его поддерживает. Объявил "хочу 3 копии" → K8s создал 3 → одна упала → K8s поднял новую.

**Важная честность с читателем:**
K8s сложнее docker-compose. Не нужно скрывать это. Нужно показывать что за каждым усложнением — реальная проблема которую оно решает.

---

## Что читатель построит к концу книги

```
k3s кластер (VirtualBox или VPS)
│
├── Namespace: dev
│   ├── Deployment: myapp (2 реплики)
│   │   └── Pod: myapp-xxx (python:app, порт 8000)
│   │   └── Pod: myapp-yyy (python:app, порт 8000)
│   ├── Service: myapp-svc (ClusterIP, порт 8000)
│   └── ConfigMap: myapp-config
│       Secret: myapp-secrets
│
└── Namespace: prod
    └── Deployment: myapp (1 реплика)
```

- `kubectl apply -f deployment.yaml` → приложение задеплоено
- `kubectl rollout restart` → обновление без даунтайма
- Один Pod упал → новый поднялся автоматически

---

## Структура книги

### Глава 0: Зачем Kubernetes — честный разговор

**Цель:** читатель понимает проблемы которые решает K8s, и не пытается использовать его там где не нужен.

- Три реальные проблемы docker-compose на одном сервере:
  ```
  Проблема 1: Надёжность
  Сервер упал → всё приложение недоступно
  docker-compose не умеет "поднять на другом сервере"

  Проблема 2: Масштабирование
  Трафик ×10 → нужно больше копий приложения
  docker-compose: scale возможен, но без балансировки и без автоматики

  Проблема 3: Обновления
  docker-compose down → новый up → секунды даунтайма
  Нет встроенного механизма rolling update
  ```
- Когда K8s НЕ нужен:
  - Один маленький сервис, один сервер, один разработчик
  - Стартап на ранней стадии
  - docker-compose справляется
- Когда K8s нужен:
  - Несколько сервисов с разными требованиями к масштабированию
  - Требования к надёжности (uptime 99.9%+)
  - Команда из нескольких разработчиков
- Архитектура кластера (обзорно):
  ```
  Control Plane              Worker Nodes
  ┌─────────────────┐        ┌────────────┐
  │ API Server      │──────→ │ Node 1     │
  │ etcd            │        │ Pods...    │
  │ Scheduler       │──────→ │ Node 2     │
  │ Controller Mgr  │        │ Pods...    │
  └─────────────────┘        └────────────┘
  ```
- Установка k3s: `curl -sfL https://get.k3s.io | sh -`
  - k3s = K8s для одного узла, без облака, без сложности
  - Идеально для обучения
- Проверка: `kubectl get nodes`

> **Честность:** K8s — это сложность. Но как только ты его понял — ты понял инфраструктуру на уровне senior. Большинство компаний из вакансий работают именно с K8s.

---

### Часть 1: Базовые объекты (Главы 1–4)

#### Глава 1: Pod — минимальная единица

**Цель:** читатель понимает что такое Pod, зачем он нужен и почему его не запускают напрямую.

- Аналогия с Docker:
  ```
  Docker:         Kubernetes:
  docker run      kubectl run (редко используется)
  контейнер       Pod (один или несколько контейнеров)
  ```
- Pod = один или несколько контейнеров которые:
  - Делят сеть (один IP на Pod)
  - Делят тома
  - Всегда на одном Node
- Почему несколько контейнеров в одном Pod (sidecar pattern):
  ```
  Pod: myapp
  ├── Container: app (порт 8000)
  └── Container: log-forwarder (читает логи app)
  ```
- Манифест Pod:
  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: myapp
    labels:
      app: myapp
  spec:
    containers:
    - name: app
      image: python:3.12-slim
      ports:
      - containerPort: 8000
  ```
- `kubectl apply -f pod.yaml` — создать
- `kubectl get pods` — список
- `kubectl get pods -o wide` — с IP и Node
- `kubectl describe pod myapp` — детали
- `kubectl logs myapp` — логи
- `kubectl logs -f myapp` — следить за логами
- `kubectl exec -it myapp -- bash` — зайти внутрь
- `kubectl delete pod myapp` — удалить
- Почему Pod не запускают напрямую:
  - Упал → не поднялся (нет контроллера)
  - Нет обновлений, нет масштабирования
  - Для этого — Deployment

> **Паттерн обучения:** `watch kubectl get pods`
> Открой второй терминал, выполни `watch kubectl get pods`.
> Все изменения — создание, обновление, падение — видны в реальном времени.
> Используй это ВСЕГДА при работе с K8s.

**Упражнения:** создать Pod, зайти внутрь, посмотреть логи, удалить — убедиться что сам не поднялся.

#### Глава 2: Deployment — управление репликами

**Цель:** читатель понимает как Deployment следит за желаемым состоянием.

- Deployment = контроллер который следит за Pods
  ```
  Deployment: myapp (replicas: 3)
  ├── ReplicaSet: myapp-xxx
  │   ├── Pod: myapp-xxx-aaa ✓
  │   ├── Pod: myapp-xxx-bbb ✓
  │   └── Pod: myapp-xxx-ccc ✗ (упал)
  └── Kubernetes замечает: нужно 3, есть 2
      → автоматически создаёт Pod: myapp-xxx-ddd
  ```
- Манифест Deployment:
  ```yaml
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
          image: myapp:1.0
          ports:
          - containerPort: 8000
          resources:
            requests:
              memory: "64Mi"
              cpu: "250m"
            limits:
              memory: "128Mi"
              cpu: "500m"
  ```
- `kubectl apply -f deployment.yaml`
- `kubectl get deployments`
- `kubectl get pods` — видишь 3 Pod'а
- Убить Pod вручную: `kubectl delete pod myapp-xxx-aaa` → наблюдать как поднялся новый
- Масштабирование: `kubectl scale deployment myapp --replicas=5`
- Rolling update: изменить image в манифесте → `kubectl apply` → K8s обновляет Pod по одному без даунтайма
- `kubectl rollout status deployment/myapp` — следить за прогрессом обновления
- `kubectl rollout history deployment/myapp` — история обновлений
- `kubectl rollout undo deployment/myapp` — откат к предыдущей версии

> **Демонстрация которую нельзя пропустить:**
> 1. Задеплоить Deployment с 3 репликами
> 2. Открыть `watch kubectl get pods`
> 3. Удалить один Pod
> 4. Наблюдать как K8s сам поднял новый
> Это и есть самовосстановление. Пусть читатель увидит это своими глазами.

**Упражнения:** создать Deployment, убить Pod и наблюдать восстановление, сделать rolling update, откатить.

#### Глава 3: Service — сетевой доступ

**Цель:** читатель понимает почему нельзя обращаться к Pod'у напрямую по IP.

- Проблема: Pods получают случайные IP, которые меняются при пересоздании
- Service = стабильный адрес для группы Pods
  ```
  Клиент → Service (myapp-svc) → Pod 1
                               → Pod 2
                               → Pod 3
  ```
- Как Service находит Pods: через labels/selector
- Типы Service:
  ```
  ClusterIP    — только внутри кластера (по умолчанию)
  NodePort     — доступен снаружи через порт ноды (для тестов)
  LoadBalancer — внешний балансировщик (облако)
  ```
- Манифест ClusterIP:
  ```yaml
  apiVersion: v1
  kind: Service
  metadata:
    name: myapp-svc
  spec:
    selector:
      app: myapp          # находит Pods с этим label
    ports:
    - port: 80            # порт Service
      targetPort: 8000    # порт контейнера
  ```
- Манифест NodePort (для тестов):
  ```yaml
  spec:
    type: NodePort
    ports:
    - port: 80
      targetPort: 8000
      nodePort: 30080   # 30000-32767
  ```
- `kubectl get services`
- `kubectl describe service myapp-svc`
- DNS внутри кластера: `myapp-svc.default.svc.cluster.local`
- Между Pods: `curl http://myapp-svc:80` (в той же namespace)

**Упражнения:** создать Service, подключиться к приложению через NodePort, проверить что при пересоздании Pod — Service продолжает работать.

#### Глава 4: ConfigMap и Secret

**Цель:** читатель не хардкодит конфигурацию и секреты в образ.

- Аналогия с Docker: `.env` файл, но в Kubernetes
- ConfigMap — несекретная конфигурация:
  ```yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: myapp-config
  data:
    APP_ENV: production
    DB_HOST: postgres-svc
    DB_PORT: "5432"
    nginx.conf: |
      server {
        listen 80;
        ...
      }
  ```
- Secret — чувствительные данные (base64):
  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: myapp-secrets
  type: Opaque
  data:
    DB_PASSWORD: cGFzc3dvcmQ=   # base64("password")
    SECRET_KEY: c2VjcmV0        # base64("secret")
  ```
- `echo -n "password" | base64` — кодировать
- `echo "cGFzc3dvcmQ=" | base64 -d` — декодировать
- Использование в Deployment:
  ```yaml
  spec:
    containers:
    - name: app
      envFrom:
      - configMapRef:
          name: myapp-config
      - secretRef:
          name: myapp-secrets
  ```
- Монтирование файлом (для конфигов):
  ```yaml
  volumes:
  - name: config
    configMap:
      name: myapp-config
  containers:
  - volumeMounts:
    - name: config
      mountPath: /etc/myapp
  ```
- `kubectl create secret generic myapp-secrets --from-literal=DB_PASSWORD=pass`
- `kubectl get secrets`
- `kubectl describe secret myapp-secrets` — значения скрыты
- Secret в K8s — base64, не шифрование. Для реального шифрования: Sealed Secrets, Vault.

> **Важно:** base64 — не безопасность. Secret в K8s хранится в etcd в base64. Кто имеет доступ к кластеру — видит значения. Правило: никогда не коммитить Secret-манифесты в git.

**Упражнения:** вынести все env-переменные в ConfigMap и Secret, применить к Deployment.

---

### Часть 2: Данные и организация (Главы 5–7)

#### Глава 5: Volume и PersistentVolume

**Цель:** читатель решает проблему потери данных при пересоздании Pod.

- Проблема: данные внутри Pod = данные внутри контейнера → при пересоздании Pod теряются
- Аналогия с Docker: volumes, но сложнее
- emptyDir — временный том который живёт пока жив Pod:
  ```yaml
  volumes:
  - name: tmp
    emptyDir: {}
  ```
- PersistentVolume (PV) и PersistentVolumeClaim (PVC):
  ```
  PV = диск (создаёт администратор или провайдер облака)
  PVC = заявка на диск (создаёт разработчик)

  Разработчик не знает где физически диск — просто запрашивает нужный размер
  ```
- PersistentVolumeClaim:
  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: pgdata
  spec:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 1Gi
  ```
- Использование в Pod:
  ```yaml
  volumes:
  - name: pgdata
    persistentVolumeClaim:
      claimName: pgdata
  containers:
  - volumeMounts:
    - name: pgdata
      mountPath: /var/lib/postgresql/data
  ```
- `kubectl get pv` — список PersistentVolume
- `kubectl get pvc` — список заявок
- StorageClass: как PVC превращается в PV (provisioner)
- В k3s: встроенный local-path provisioner — автоматически создаёт PV на ноде

**Упражнения:** запустить PostgreSQL в K8s с PVC, наполнить данными, удалить Pod, создать новый — данные сохранились.

#### Глава 6: Namespace — изоляция окружений

**Цель:** читатель разделяет dev и prod в одном кластере.

- Namespace = виртуальный кластер внутри кластера
- По умолчанию: `default`, `kube-system`, `kube-public`
- Создание namespace:
  ```bash
  kubectl create namespace dev
  kubectl create namespace prod
  ```
- Или из манифеста:
  ```yaml
  apiVersion: v1
  kind: Namespace
  metadata:
    name: dev
  ```
- Работа с namespace:
  ```bash
  kubectl get pods -n dev
  kubectl apply -f deployment.yaml -n dev
  kubectl get all -n prod
  ```
- Установить namespace по умолчанию:
  ```bash
  kubectl config set-context --current --namespace=dev
  ```
- Изоляция: ресурсы в разных namespace не видят друг друга по короткому имени
  - dev: `myapp-svc` → `myapp-svc.dev.svc.cluster.local`
  - prod: `myapp-svc` → `myapp-svc.prod.svc.cluster.local`
- Квоты по namespace: ResourceQuota (упомянуть, детали в Модуле 11)
- kubens — удобный инструмент для переключения namespace

**Упражнения:** задеплоить приложение в namespace dev и prod с разными конфигами, убедиться что изолированы.

#### Глава 7: Деплой реального Python-приложения

**Цель:** читатель деплоит своё Python-приложение в k3s с нуля.

- Полный стек манифестов:
  - Namespace
  - ConfigMap: не-секретные переменные
  - Secret: пароль от БД
  - PersistentVolumeClaim: для PostgreSQL
  - Deployment: PostgreSQL
  - Service: PostgreSQL (ClusterIP)
  - Deployment: Python-приложение
  - Service: Python-приложение (NodePort для доступа)
- Порядок apply: `kubectl apply -f ./k8s/` — всё из директории
- readinessProbe и livenessProbe:
  ```yaml
  livenessProbe:
    httpGet:
      path: /health
      port: 8000
    initialDelaySeconds: 30
    periodSeconds: 10
  readinessProbe:
    httpGet:
      path: /ready
      port: 8000
  ```
- `imagePullPolicy: Always` — для dev; `IfNotPresent` — для prod с конкретным тегом
- Почему никогда `latest` в prod
- **Мост от Docker Compose:**
  ```
  docker-compose.yml         →  K8s manifests
  ├── services:app:          →  ├── deployment.yaml
  ├── services:db:           →  ├── postgres.yaml
  ├── volumes:pgdata:        →  ├── pvc.yaml
  └── environment:           →  ├── configmap.yaml
                                └── secret.yaml
  ```
  Показать как каждый блок docker-compose переводится в K8s манифест.

#### Глава 8: kubectl — полная шпаргалка

**Цель:** читатель уверенно использует kubectl — главный инструмент работы с K8s.

> **Эта глава — справочник.** Не читать подряд, обращаться по необходимости.

- Структура команды: `kubectl [verb] [resource] [name] [flags]`
- Основные глаголы: `get`, `describe`, `apply`, `delete`, `logs`, `exec`, `port-forward`
- `kubectl get` для разных ресурсов
- Форматы вывода: `-o wide`, `-o yaml`, `-o json`
- `kubectl describe`: полная информация + события (Events)
- `kubectl apply` vs `kubectl create`: всегда `apply`
- `kubectl port-forward`: пробросить порт Pod на локальную машину
- `kubectl top pods` — CPU/RAM Pod'ов
- `kubectl rollout`: status, history, undo
- kubeconfig: `~/.kube/config` — как kubectl знает к какому кластеру подключаться
- Контексты: несколько кластеров в одном kubeconfig
- kubens: удобное переключение namespace

---

### Часть 3: Практика (Главы 9–10)

#### Глава 9: Rolling update и откат

**Цель:** читатель обновляет приложение без даунтайма и откатывается при проблеме.

- Rolling update: как работает
  ```
  Текущий Deployment: 3 Pod'а с image: myapp:1.0

  kubectl set image deployment/myapp app=myapp:2.0
  # или kubectl apply -f deployment.yaml (с новым image)

  K8s делает:
  1. Создаёт Pod с image:2.0
  2. Ждёт readinessProbe
  3. Удаляет один Pod с image:1.0
  4. Повторяет
  ```
- `maxSurge` и `maxUnavailable` в strategy
- `kubectl rollout status/history/undo`
- Аннотация для истории

#### Глава 10: Ресурсы — limits, requests, quotas

**Цель:** читатель ограничивает ресурсы Pod'ов и понимает что будет при нехватке.

- `resources.requests` — сколько зарезервировать (для Scheduler)
- `resources.limits` — максимум (при превышении — OOM kill)
- Как K8s решает где запустить Pod: Scheduler и ресурсы
- `kubectl top pods` — реальное потребление
- ResourceQuota — ограничение на namespace
- LimitRange — дефолтные limits для всех Pod'ов в namespace
- Что происходит при OOM: Pod перезапускается с restartPolicy
- Vertical Pod Autoscaler (упомянуть, детали в Модуле 11)

**Упражнения:** выставить limits для app и db, создать Pod с limits > доступных → наблюдать Pending, создать Pod который ест больше limits → наблюдать OOM kill.

---

### Мини-проекты

#### Мини-проект 1: Python-приложение с PostgreSQL в k3s

Задеплоить полный стек:
- Namespace `myapp`
- PostgreSQL с PVC (данные сохраняются при пересоздании Pod)
- Python-приложение (собственный Docker-образ из Модуля 3)
- ConfigMap + Secret для переменных
- Service NodePort для доступа
- livenessProbe + readinessProbe

Проверка:
- `kubectl delete pod <postgres-pod>` → данные сохранились
- `kubectl delete pod <app-pod>` → Pod поднялся сам
- `curl http://node:30080/health` → 200

#### Мини-проект 2: Rolling update без даунтайма

1. Задеплоить app:v1 с 3 репликами
2. В отдельном терминале: `while true; do curl -s http://node:30080; sleep 0.5; done`
3. Обновить до app:v2: `kubectl set image deployment/myapp app=myapp:v2`
4. Наблюдать через `kubectl rollout status` что запросы не прерывались
5. Откатиться до v1: `kubectl rollout undo deployment/myapp`
6. Проверить что v1 снова работает без прерываний

#### Мини-проект 3: Dev и prod namespace + CI/CD

1. Namespace `dev` — 1 реплика, image с тегом `dev`, ресурсы меньше
2. Namespace `prod` — 3 реплики, image с тегом `1.0`, ресурсы больше
3. Разные ConfigMap (DEBUG=true/false, разные лог-уровни)
4. CI/CD: `kubectl apply` из GitHub Actions при push в main
5. Docker-образ из ghcr.io (связь с Модулем 3 и 4)

Проверка:
- Dev и prod изолированы (не мешают друг другу)
- Push в main → CI собирает образ → CD деплоит в prod
- `kubectl rollout history` показывает историю обновлений

---

### Приложения

#### Приложение A: Шпаргалка kubectl

| Команда | Назначение |
|---------|-----------|
| `kubectl get pods` | Список Pod'ов |
| `kubectl describe pod NAME` | Детали Pod |
| `kubectl logs NAME` | Логи |
| `kubectl exec -it NAME -- bash` | Войти внутрь |
| `kubectl apply -f FILE` | Применить манифест |
| `kubectl delete -f FILE` | Удалить по манифесту |
| `kubectl get all -n NS` | Всё в namespace |
| `kubectl port-forward pod/NAME 8080:8000` | Пробросить порт |
| `kubectl rollout undo deploy/NAME` | Откат |
| `kubectl scale deploy NAME --replicas=5` | Масштабировать |

#### Приложение B: Готовые манифесты
- Минимальный Deployment + Service
- Deployment + ConfigMap + Secret
- PostgreSQL с PVC
- Полный стек: app + db + сервисы

#### Приложение C: Диагностика
- `CrashLoopBackOff` → `kubectl logs pod/NAME --previous`, проверить команду запуска
- `ImagePullBackOff` → проверить имя образа, доступ к registry
- Pod в `Pending` → `kubectl describe pod NAME`, Events → нет ресурсов или нет PV
- Service не отвечает → проверить selector labels совпадают с Pod labels
- `Error: ErrImagePull` → образ не существует или нет доступа

---

## Принципы написания

### 1. Аналогии с Docker — мост для понимания

Читатель знает Docker. Используй это:

| Docker | Kubernetes |
|--------|-----------|
| `docker run` | Pod |
| `docker-compose.yml` | YAML-манифест |
| `docker restart` | Контроллер |
| `docker network` | Service |
| `docker volume` | PersistentVolume |
| `.env` | ConfigMap + Secret |

Но сразу показывай где аналогия ломается: Pod ≠ контейнер (Pod может содержать несколько), Service ≠ просто сеть (это service discovery и балансировка).

### 2. `watch kubectl get pods` — в каждом практическом разделе

С первой главы учить: открой второй терминал, запусти `watch kubectl get pods`.
Это делает K8s "живым" — читатель видит как объекты появляются и исчезают.

### 3. Показывай Events в describe

`kubectl describe` выдаёт Events — это где K8s объясняет что делал:
```
Events:
  Normal   Scheduled  default-scheduler assigned myapp-xxx to node1
  Normal   Pulled     Image "myapp:1.0" pulled
  Normal   Created    Created container app
  Normal   Started    Started container app
  Warning  BackOff    Back-off restarting failed container
```
Учи читателя читать Events — они объясняют 90% проблем.

### 4. Сначала один ресурс — потом в составе стека

Каждый новый ресурс:
1. Объяснить зачем нужен
2. Показать минимальный манифест
3. `kubectl apply` + `kubectl get` + `kubectl describe`
4. Сломать — наблюдать поведение
5. Добавить в полный стек

### 5. Мост от Docker Compose — явно

В Главе 7 показать как каждый блок docker-compose.yml переводится в K8s манифест:
```
docker-compose.yml          K8s
─────────────────          ─────
services: app        →     Deployment + Service
environment:         →     ConfigMap + Secret
volumes: pgdata      →     PersistentVolumeClaim
restart: always      →     restartPolicy: Always
```
Это критически важно. Читатель знает docker-compose — используй как мост.

### 6. Resources limits — не опция

Каждый Deployment в книге должен иметь `resources.requests` и `resources.limits`.
Без limits Pod может съесть всю ноду.
Формируй привычку с первого Deployment.

### 7. Никакой воды

- Без истории Google Borg и как K8s появился
- Без сравнения K8s vs Docker Swarm vs Nomad
- Без облачных провайдеров (EKS, GKE, AKS) — в этой книге только k3s
- Без Ingress — это Модуль 11
- Без Helm — это Модуль 11

---

## Что НЕ надо делать

- ❌ Не использовать `kubectl create` — только `kubectl apply`
- ❌ Не деплоить с тегом `latest` в prod примерах
- ❌ Не объяснять Helm в этой книге — только упомянуть что существует
- ❌ Не коммитить Secret-манифесты в git в примерах
- ❌ Не пугать сложностью — объяснять каждый шаг
- ❌ Не пропускать `watch kubectl get pods` в практических заданиях
- ❌ Не делать главу-шпаргалку основной — это справочник, не учебный материал
- ❌ Не пропускать мост от docker-compose — читатель должен видеть связь
- ❌ Не игнорировать resources limits — Pod без limits съест всю ноду

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-10.md      # Этот файл
└── 10-kubernetes-basics/                   # Книга 10 (создать)
    ├── book.md
    ├── chapter-00.md                    # Зачем K8s, честный разговор
    ├── chapter-01.md                    # Pod
    ├── chapter-02.md                    # Deployment
    ├── chapter-03.md                    # Service
    ├── chapter-04.md                    # ConfigMap и Secret
    ├── chapter-05.md                    # Volume и PVC
    ├── chapter-06.md                    # Namespace
    ├── chapter-07.md                    # Деплой Python-приложения + docker-compose мост
    ├── chapter-08.md                    # kubectl шпаргалка (справочник)
    ├── chapter-09.md                    # Rolling update и откат
    ├── chapter-10.md                    # Ресурсы (limits, requests, quotas)
    ├── appendix-a.md
    ├── appendix-b.md
    └── appendix-c.md
```

---

## Связь с другими модулями

**Что нужно из Модуля 3 (Docker):**
- Dockerfile — образы для Pod'ов
- docker-compose — ментальная модель для понимания K8s манифестов
- Docker Hub / registry — откуда K8s берёт образы

**Что нужно из Модуля 9 (Ansible):**
- Декларативность (задаём желаемое состояние)
- YAML синтаксис
- Концепция идемпотентности

**Что даёт Модулю 11 (K8s продвинутый):**
- Все базовые объекты — Deployment, Service, ConfigMap, PVC — будут использоваться постоянно
- Namespace — основа для Helm (каждый release в namespace)
- Rolling update понимание — нужно для HPA и Ingress

---

*Эта инструкция — для ИИ-агента, который будет писать десятую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Предыдущая: AGENT-INSTRUCTIONS-module-09.md (Ansible)*
*Следующая: AGENT-INSTRUCTIONS-module-11.md (Kubernetes продвинутый + Helm)*
