# Инструкция для ИИ-агента: Написание книги по Kubernetes (Продвинутый + Helm)

> **Это Модуль 11 курса DevOps 2.0.**
> Предварительные требования: пройдены модули 1–10 (включая K8s основы).
> Смотри также:
> - [AGENT-INSTRUCTIONS-module-10.md](AGENT-INSTRUCTIONS-module-10.md) — Модуль 10 (K8s основы)

---

## Контекст проекта

Ученик прошёл K8s основы. Он умеет деплоить Deployment + Service + ConfigMap.
Но у него нет внешнего доступа (только NodePort), нет автомасштабирования, нет баз данных в K8s, нет удобного способа управлять несколькими приложениями.

**Что он уже умеет** (не повторяй):
- Создаёт Pod, Deployment, Service, ConfigMap, Secret, PVC
- Делает rolling update и откат
- Работает с namespace
- Уверенно использует kubectl

**Что его раздражает прямо сейчас:**
- NodePort с портом 30080 — не для продакшна
- Писать одно и то же YAML для каждого окружения (dev/staging/prod)
- Не знает как запустить PostgreSQL "по-человечески" в K8s (StatefulSet)
- 20 YAML-файлов на одно приложение — хаос

**Что он хочет после этой книги:**
Получить реальный продакшн-стек: HTTPS по домену через Ingress, база данных через StatefulSet, конфиги управляются через Helm chart.

---

## Что за книга

**Название:** "Kubernetes: Продвинутый уровень и Helm"

**Место в курсе:** Книга 11 из 14

**Объём:** 160-200 страниц

**Стиль:**
- Строится на знаниях Модуля 10
- Каждая новая концепция — решение конкретной проблемы
- ASCII-схемы для Ingress, HPA, StatefulSet
- Практика на реальных примерах

---

## Главная идея, которую должна передать книга

Модуль 10 дал базу. Модуль 11 делает из неё production-ready стек.

Три главных перехода:
```
Модуль 10:              Модуль 11:
NodePort :30080    →    Ingress (HTTPS по домену)
1 реплика всегда   →    HPA (автомасштабирование)
20 yaml файлов     →    Helm chart (один пакет)
```

**Ключевая идея про Helm:**
> Сначала пишем raw YAML вручную — только потом видим как Helm это оборачивает.
> Никогда не `helm install` до того как написал то же самое руками.
> Helm — не магия. Это шаблонизатор поверх YAML который ты уже знаешь.

---

## Что читатель построит к концу книги

```
Интернет
    │ HTTPS (myapp.ru)
    ▼
[ Ingress Controller (NGINX) ]
    │ routing по hostname/path
    ├──→ [ Service: myapp ]
    │        └──→ [ Deployment: myapp (2-5 реплик, HPA) ]
    │
    └──→ [ Service: api ]
             └──→ [ Deployment: api ]

[ StatefulSet: postgres ]
    └──→ [ PVC: pgdata-0 ]

Всё это — один Helm chart:
helm install myapp ./charts/myapp -f values.prod.yaml
```

---

## Структура книги

### Глава 0: Что будем строить

**Цель:** показать итоговую архитектуру, объяснить путь.

- Схема финального стека
- Что нового в этой книге: Ingress, HPA, StatefulSet, RBAC, Helm
- Почему NodePort не подходит для продакшна
- Разница между "сделано" (работает) и "production-ready" (надёжно, управляемо, безопасно)

---

### Часть 1: Продвинутые объекты (Главы 1–4)

#### Глава 1: Ingress — HTTP-роутинг в кластере

**Цель:** читатель получает внешний HTTPS-доступ к приложению по домену.

- Проблема NodePort:
  ```
  NodePort:            Ingress:
  порт 30080           домен myapp.ru
  только HTTP          HTTPS автоматически
  один сервис/порт     много сервисов на одном порту
  не для продакшна     для продакшна
  ```
- Ingress = правила роутинга
- Ingress Controller = тот кто эти правила применяет (nginx, traefik)
  ```
  Ingress (правила)                Ingress Controller
  ┌─────────────────────┐          ┌──────────────────┐
  │ host: myapp.ru      │──────→   │ NGINX Pod         │
  │ path: /api → api    │          │ (читает Ingress   │
  │ path: / → frontend  │          │  и маршрутизирует)│
  └─────────────────────┘          └──────────────────┘
  ```
- Установка Ingress NGINX Controller в k3s:
  ```bash
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/...
  ```
- Манифест Ingress:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: myapp-ingress
    annotations:
      nginx.ingress.kubernetes.io/rewrite-target: /
  spec:
    ingressClassName: nginx
    rules:
    - host: myapp.local
      http:
        paths:
        - path: /
          pathType: Prefix
          backend:
            service:
              name: myapp-svc
              port:
                number: 80
        - path: /api
          pathType: Prefix
          backend:
            service:
              name: api-svc
              port:
                number: 80
  ```
- TLS через cert-manager:
  - Установка cert-manager
  - ClusterIssuer для Let's Encrypt
  - Аннотация `cert-manager.io/cluster-issuer: letsencrypt` в Ingress
- `/etc/hosts` для локального тестирования без домена:
  ```
  127.0.0.1 myapp.local
  ```
- `kubectl get ingress` — посмотреть правила

**Упражнения:** настроить Ingress для двух сервисов по разным path, добавить TLS для реального домена.

#### Глава 2: HPA — горизонтальное масштабирование

**Цель:** читатель настраивает автоматическое масштабирование по нагрузке.

- HorizontalPodAutoscaler следит за CPU/RAM и добавляет/убирает реплики:
  ```
  CPU > 70%:  2 реплики → 4 реплики (автоматически)
  CPU < 30%:  4 реплики → 2 реплики (через 5 минут)
  ```
- Требования: metrics-server должен быть установлен
  ```bash
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/...
  kubectl top pods   # должно работать
  ```
- Манифест HPA:
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: myapp-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: myapp
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  ```
- Обязательно: `resources.requests` в Deployment (без этого HPA не работает)
- `kubectl get hpa` — статус и текущее значение метрики
- `kubectl describe hpa myapp-hpa` — детали и события
- Нагрузочный тест для демонстрации:
  ```bash
  # В отдельном терминале:
  kubectl run loadgen --image=busybox --restart=Never -- \
    /bin/sh -c "while true; do wget -q -O- http://myapp-svc/; done"
  ```
- Наблюдать как реплики растут: `watch kubectl get hpa`

**Упражнения:** настроить HPA, создать нагрузку, наблюдать масштабирование, убрать нагрузку — наблюдать сокращение.

#### Глава 3: ResourceRequests и Limits

**Цель:** читатель понимает зачем нужны лимиты и как их правильно выставить.

- Без requests/limits: Pod может забрать всю память ноды → другие Pod'ы убиты OOMKiller
- Requests = сколько K8s резервирует для Scheduler
- Limits = сколько Pod может максимально использовать
  ```
  Node: 4 CPU, 8Gi RAM

  Pod A: requests: 1 CPU, 512Mi → Scheduler резервирует
  Pod B: requests: 2 CPU, 2Gi   → Scheduler резервирует
  Pod C: requests: 1 CPU, 1Gi   → Scheduler резервирует

  Scheduler: всего зарезервировано 4 CPU, 3.5Gi — можно разместить
  ```
- CPU: `250m` = 0.25 CPU (milliCPU)
- Memory: `128Mi`, `1Gi`
- Если Pod превышает memory limit → OOMKilled
- Если Pod превышает CPU limit → throttled (замедление, не убийство)
- LimitRange: default limits для namespace:
  ```yaml
  apiVersion: v1
  kind: LimitRange
  metadata:
    name: default-limits
  spec:
    limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "256Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
  ```
- ResourceQuota: ограничить ресурсы для namespace
- Как выбрать значения:
  - Запустить без limits, посмотреть через `kubectl top pods`
  - Выставить limits = 2× наблюдаемое среднее
  - Requests = 50-70% limits

**Упражнения:** выставить limits, симулировать OOMKilled, наблюдать поведение, настроить LimitRange для namespace.

#### Глава 4: StatefulSet — базы данных в K8s

**Цель:** читатель понимает разницу между Deployment и StatefulSet, запускает PostgreSQL.

- Проблема Deployment для БД:
  ```
  Deployment: Pod'ы взаимозаменяемы, случайные имена
  myapp-xxx-aaa, myapp-xxx-bbb — одинаковые
  Пересоздан Pod → другой IP, другое имя

  StatefulSet: Pod'ы имеют стабильные имена и тома
  postgres-0, postgres-1, postgres-2 — всегда одни и те же имена
  Пересоздан postgres-0 → тот же PVC pgdata-0
  ```
- Когда нужен StatefulSet:
  - Базы данных (PostgreSQL, MySQL, MongoDB)
  - Любой сервис с персистентным состоянием
  - Кластерные приложения где каждый узел имеет роль
- Манифест StatefulSet для PostgreSQL:
  ```yaml
  apiVersion: apps/v1
  kind: StatefulSet
  metadata:
    name: postgres
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
          image: postgres:16
          envFrom:
          - secretRef:
              name: postgres-secrets
          volumeMounts:
          - name: pgdata
            mountPath: /var/lib/postgresql/data
    volumeClaimTemplates:        # Каждый Pod получает свой PVC
    - metadata:
        name: pgdata
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
  ```
- Headless Service для StatefulSet:
  ```yaml
  spec:
    clusterIP: None    # headless — даёт DNS имена отдельным Pod'ам
    selector:
      app: postgres
  ```
- DNS имена Pod'ов: `postgres-0.postgres.default.svc.cluster.local`
- `kubectl get statefulset`
- `kubectl exec -it postgres-0 -- psql -U postgres`

**Упражнения:** запустить PostgreSQL в StatefulSet, подключить приложение, пересоздать Pod — убедиться что данные сохранились.

---

### Часть 2: Безопасность и сети (Главы 5–6)

#### Глава 5: NetworkPolicy — изоляция Pod'ов

**Цель:** читатель понимает что по умолчанию все Pod'ы видят друг друга и умеет это ограничивать.

- Проблема: в K8s по умолчанию любой Pod может обратиться к любому Pod:
  ```
  Pod в namespace default → Pod в namespace prod → PostgreSQL
  Любой Pod → Redis → чтение всех данных сессий
  ```
- NetworkPolicy = фаервол для Pod'ов:
  ```
  До NetworkPolicy:          После NetworkPolicy:
  Pod A ──→ Pod B            Pod A ──→ Pod B (разрешено)
  Pod C ──→ Pod B            Pod C ──/  Pod B (заблокировано)
  ```
- Манифест NetworkPolicy:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: deny-all
    namespace: prod
  spec:
    podSelector: {}        # все Pod'ы
    policyTypes:
    - Ingress              # блокируем входящие
    - Egress               # блокируем исходящие
  ```
- Разрешить трафик только от конкретного Pod:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: allow-from-api
    namespace: prod
  spec:
    podSelector:
      matchLabels:
        app: postgres       # разрешить доступ к postgres
    policyTypes:
    - Ingress
    ingress:
    - from:
      - podSelector:
          matchLabels:
            app: api        # только от api Pod
      ports:
      - port: 5432
  ```
- CNI плагин должен поддерживать NetworkPolicy: Calico, Cilium (k3s по умолчанию — Flannel — НЕ поддерживает)
  ```bash
  # Для k3s: установить с Calico
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --flannel-backend=none --disable-network-policy" sh -
  curl -fsSL https://docs.projectcalico.org/manifests/tigera-operator.yaml | kubectl apply -f -
  ```
- `kubectl get networkpolicy` — список политик
- Тестирование: запустить busybox Pod и проверить что доступ заблокирован

**Упражнения:** установить CNI с поддержкой NetworkPolicy, создать deny-all policy, разрешить только нужный трафик, проверить что остальной заблокирован.

#### Глава 6: RBAC — права доступа в K8s

**Цель:** читатель разграничивает кто и что может делать в кластере.

- Проблема: все разработчики с одним kubeconfig могут всё
- RBAC: Role-Based Access Control
  ```
  ServiceAccount (кто)
         │
       RoleBinding
         │
       Role (что может делать)
  ```
- Основные объекты:
  - `ServiceAccount` — идентификатор Pod'а или человека
  - `Role` — набор прав в namespace
  - `ClusterRole` — набор прав на весь кластер
  - `RoleBinding` — связать ServiceAccount с Role
  - `ClusterRoleBinding` — связать с ClusterRole
- Пример: Pod который может читать ConfigMap:
  ```yaml
  # ServiceAccount для приложения
  apiVersion: v1
  kind: ServiceAccount
  metadata:
    name: myapp-sa

  ---
  # Role: только чтение ConfigMap
  apiVersion: rbac.authorization.k8s.io/v1
  kind: Role
  metadata:
    name: configmap-reader
  rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]

  ---
  # Связать ServiceAccount с Role
  apiVersion: rbac.authorization.k8s.io/v1
  kind: RoleBinding
  metadata:
    name: myapp-configmap-reader
  subjects:
  - kind: ServiceAccount
    name: myapp-sa
  roleRef:
    kind: Role
    name: configmap-reader
    apiGroup: rbac.authorization.k8s.io
  ```
- Использовать ServiceAccount в Deployment:
  ```yaml
  spec:
    serviceAccountName: myapp-sa
  ```
- `kubectl auth can-i get configmaps --as=system:serviceaccount:default:myapp-sa`
- Встроенные ClusterRole: `view`, `edit`, `admin`, `cluster-admin`
- Принцип наименьших прав: приложение должно иметь только то что нужно

---

### Часть 3: Helm (Главы 6–8)

#### Глава 6: Helm — почему 20 YAML это проблема

**Цель:** читатель понимает зачем нужен Helm, прежде чем видеть как он работает.

- Проблема: 20 YAML-файлов для одного приложения
  ```
  k8s/
  ├── namespace.yaml
  ├── configmap.yaml
  ├── secret.yaml
  ├── pvc.yaml
  ├── deployment.yaml
  ├── service.yaml
  ├── ingress.yaml
  └── hpa.yaml

  Для dev: те же файлы, но другие значения (имя, image, replicas)
  Для prod: те же файлы, но другие значения
  → copy-paste с ошибками
  ```
- Helm решение: шаблоны + значения
  ```
  Chart (шаблоны)     values.dev.yaml     values.prod.yaml
       │                     │                    │
       └─────────────────────┘                    │
               └─────────────────────────────────┘
                    helm template/install
                           │
                    K8s-манифесты для dev/prod
  ```
- Helm = пакетный менеджер для K8s
  - Chart = пакет (как `.deb` или npm)
  - Release = установленный Chart (конкретная инсталляция)
  - Repository = хранилище Charts
- Установка Helm: `snap install helm --classic`
- `helm version`
- Публичные Charts: `helm search hub nginx`
- ArtifactHub: место поиска Charts

#### Глава 7: Сначала руками — потом Helm

**Цель:** читатель сначала делает то что Helm будет делать, понимает шаблонизацию.

> **Принцип этой главы:** никогда не объясняй Helm без понимания raw YAML.
> Показывай: вот raw YAML для dev, вот для prod — они отличаются только значениями.
> Значит нужен шаблон. Helm — это и есть шаблонизатор.

- Взять deployment.yaml для dev и prod — показать разницу:
  ```yaml
  # dev:
  image: myapp:latest
  replicas: 1
  resources:
    limits:
      memory: "256Mi"

  # prod:
  image: myapp:v2.0
  replicas: 3
  resources:
    limits:
      memory: "1Gi"
  ```
- Вынести разные значения в `values.yaml`
- Создать Chart:
  ```bash
  helm create myapp
  ```
- Структура Chart:
  ```
  myapp/
  ├── Chart.yaml          # метаданные (name, version, description)
  ├── values.yaml         # значения по умолчанию
  ├── templates/
  │   ├── deployment.yaml # шаблон с {{ .Values.image }}
  │   ├── service.yaml
  │   ├── ingress.yaml
  │   └── _helpers.tpl    # вспомогательные функции
  └── charts/             # зависимые Charts
  ```
- Шаблон deployment.yaml:
  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: {{ .Release.Name }}-app
  spec:
    replicas: {{ .Values.replicaCount }}
    template:
      spec:
        containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
  ```
- `helm template myapp ./myapp -f values.dev.yaml` — посмотреть финальный YAML без применения
- `helm install myapp-dev ./myapp -f values.dev.yaml -n dev`
- `helm install myapp-prod ./myapp -f values.prod.yaml -n prod`
- `helm list` — список releases
- `helm upgrade myapp-dev ./myapp -f values.dev.yaml` — обновить
- `helm uninstall myapp-dev` — удалить

#### Глава 8: Helm в практике

**Цель:** читатель использует готовые Charts и управляет зависимостями.

- Добавление репозитория:
  ```bash
  helm repo add bitnami https://charts.bitnami.com/bitnami
  helm repo update
  ```
- Установка готового Chart:
  ```bash
  helm install my-postgres bitnami/postgresql \
    --set auth.postgresPassword=secret \
    --set primary.persistence.size=5Gi \
    -n prod
  ```
- `helm show values bitnami/postgresql` — все доступные values
- `-f values.yaml` vs `--set key=value`: values файл для постоянных настроек, `--set` для переопределений
- Зависимости Charts (postgresql как зависимость твоего Chart):
  ```yaml
  # Chart.yaml
  dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  ```
- `helm dependency update` — скачать зависимости
- Helm hooks: запустить Job до/после установки (например, миграции БД)
- `helm rollback myapp-prod 1` — откат к предыдущей версии release

---

### Мини-проекты

#### Мини-проект 1: Helm chart для Python-приложения с PostgreSQL
1. Написать raw YAML для app + db (без Helm)
2. Превратить в Helm Chart
3. Создать `values.dev.yaml` и `values.prod.yaml`
4. Задеплоить в namespace dev и prod через Helm
5. Обновить image через `helm upgrade`

#### Мини-проект 2: Autoscaling при нагрузке
1. Настроить HPA (min 2, max 8, CPU 60%)
2. Запустить `kubectl run loadgen --image=busybox -- /bin/sh -c "while true; do wget ..."`
3. Наблюдать рост реплик в реальном времени
4. Остановить нагрузку — наблюдать сокращение

#### Мини-проект 3: Миграция docker-compose → K8s

Взять docker-compose.yml из Модуля 3 (книга 03-docker-devops, Глава 9) и мигрировать в K8s:
- Каждый service → Deployment
- ports → Service (ClusterIP + Ingress вместо NodePort)
- environment → ConfigMap + Secret
- volumes → PersistentVolumeClaim + StorageClass
- Nginx → Ingress с TLS

Проверка: приложение работает в K8s так же как работало в docker-compose.

---

### Приложения

#### Приложение A: Шпаргалка Helm

| Команда | Назначение |
|---------|-----------|
| `helm create NAME` | Создать Chart |
| `helm template NAME ./chart` | Показать YAML без применения |
| `helm install NAME ./chart` | Установить |
| `helm upgrade NAME ./chart` | Обновить |
| `helm uninstall NAME` | Удалить |
| `helm list` | Список releases |
| `helm rollback NAME 1` | Откат к версии 1 |
| `helm show values chart` | Доступные параметры |
| `helm repo add NAME URL` | Добавить репозиторий |
| `helm dependency update` | Обновить зависимости |

#### Приложение B: Готовые манифесты
- Ingress + TLS для одного сервиса
- HPA с метриками CPU и Memory
- StatefulSet для PostgreSQL
- Минимальный Helm Chart структура
- values.yaml шаблон с комментариями

#### Приложение C: Диагностика
- Ingress 502 → Service не существует или неправильный порт
- HPA не масштабирует → нет metrics-server или нет resource requests
- StatefulSet застрял в Pending → нет StorageClass или нет доступного PV
- `helm template` показывает неправильный YAML → ошибка в шаблоне, проверь отступы
- `helm install` падает с "already exists" → `helm upgrade --install` или удалить сначала

---

## Принципы написания

### 1. Raw YAML всегда раньше Helm

Никогда не показывай `helm install` до того как читатель написал тот же манифест вручную.
Порядок в Helm главах:
1. Вот проблема (20 одинаковых YAML)
2. Вот как выглядит один из них вручную
3. Вот как Helm это шаблонизирует
4. Теперь `helm template` — посмотри на результат

### 2. `helm template` перед `helm install`

Как `terraform plan` перед `apply`:
```bash
# Сначала посмотри что Helm сгенерирует:
helm template myapp ./chart -f values.yaml

# Только потом применяй:
helm install myapp ./chart -f values.yaml
```

### 3. Каждый продвинутый объект — решение конкретной проблемы

Структура каждой главы:
- Проблема которую объект решает (с примером из реальной жизни)
- Как объект работает (схема)
- Минимальный манифест
- Демонстрация что проблема решена

### 4. Без воды

- Без сравнения Helm vs Kustomize (упомянуть что Kustomize существует)
- Без Operator pattern (слишком продвинуто)
- Без Istio, service mesh (отдельная тема)
- Без managed K8s в облаке (EKS, GKE) — это для финального проекта

---

## Что НЕ надо делать

- ❌ Показывать `helm install` до raw YAML
- ❌ Объяснять Helm раньше чем читатель написал 5+ YAML-файлов вручную
- ❌ Опускать `helm template` в примерах
- ❌ Запускать StatefulSet без headless Service
- ❌ Настраивать HPA без resource requests в Deployment

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-11.md         # Этот файл
└── 11-kubernetes-advanced/                    # Книга 11 (создать)
    ├── book.md
    ├── chapter-00.md                       # Что строим
    ├── chapter-01.md                       # Ingress
    ├── chapter-02.md                       # HPA
    ├── chapter-03.md                       # Resources
    ├── chapter-04.md                       # StatefulSet
    ├── chapter-05.md                       # RBAC
    ├── chapter-06.md                       # Helm: зачем
    ├── chapter-07.md                       # Helm: создаём chart
    ├── chapter-08.md                       # Helm: практика
    ├── appendix-a.md
    ├── appendix-b.md
    └── appendix-c.md
```

---

## Связь с другими модулями

**Что нужно из Модуля 10 (K8s основы):**
- Все базовые объекты: Pod, Deployment, Service, ConfigMap, PVC — используются в каждой главе
- Rolling update — основа для понимания Ingress и HPA
- kubectl — продолжаем использовать

**Что даёт Модулю 12 (Мониторинг):**
- kube-prometheus-stack устанавливается через Helm (первое real-world применение Helm)
- Ingress нужен для Grafana-UI
- HPA работает с метриками из Prometheus (custom metrics)

**Что даёт Модулю 13 (GitOps):**
- Helm Charts + GitOps: ArgoCD деплоит Helm release из Git
- RBAC: ArgoCD нужны права на деплой

---

*Эта инструкция — для ИИ-агента, который будет писать одиннадцатую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Предыдущая: AGENT-INSTRUCTIONS-module-10.md (K8s основы)*
*Следующая: AGENT-INSTRUCTIONS-module-12.md (Мониторинг)*
