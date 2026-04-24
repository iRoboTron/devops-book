# Инструкция для ИИ-агента: Финальные проекты DevOps 2.0

> **Это Модуль 14 — финал курса DevOps 2.0.**
> Предварительные требования: пройдены все модули 1–13.
> Это не учебник. Это рабочий инструмент — 4 production-проекта.

---

## Контекст проекта

Ученик прошёл весь курс DevOps 2.0. Он знает Terraform, Ansible, Kubernetes, Helm, Prometheus, GitLab CI, ArgoCD.
Финальные проекты — это синтез. Нет новых инструментов, только применение всего что было.

**Главный принцип этого модуля:**
Никакой теории. Никаких объяснений "что такое Helm" или "зачем ArgoCD".
Только: что делать, в каком порядке, как проверить что сделано правильно.

**Критерий успеха каждого проекта:**
> Удали всё → восстанови из кода за X минут.
> Если не можешь — проект не считается завершённым.

---

## Что за модуль

**Название:** "Финальные проекты: Production-инфраструктура с нуля"

**Состоит из 4 проектов:**

```
14-14-07-final-projects-2/
├── book.md                     — обзор: как работать с проектами
├── project-1/                  — Production Python App
│   ├── README.md               — что строим, архитектура
│   ├── playbook.md             — пошаговые команды
│   └── checklist.md            — 30 пунктов проверки
├── project-2/                  — Микросервисная архитектура
│   ├── README.md
│   ├── playbook.md
│   └── checklist.md
├── project-3/                  — Disaster Recovery
│   ├── README.md
│   ├── playbook.md
│   └── checklist.md
└── project-4/                  — Platform Engineering
    ├── README.md
    ├── playbook.md
    └── checklist.md
```

---

## Общий формат каждого проекта

### README.md
- Архитектурная схема (ASCII) — что будет в итоге
- Список технологий
- Предварительные требования
- Время выполнения

### playbook.md
- Пронумерованные шаги от нуля до готового стека
- Каждый шаг: команда + однострочный комментарий
- Блоки проверки после каждого этапа: "убедись что это работает"
- Нет объяснений зачем — только что делать

### checklist.md
- 20 пунктов финальной проверки (не 30 — проверяемо за 15 минут)
- Три категории: Функциональность (7) / Надёжность (7) / Безопасность (6)
- Финальный тест: `terraform destroy && terraform apply` → всё восстановилось
- Для каждого пункта — конкретная команда проверки

---

## Проект 1: Production Python App

### Что строим

```
GitHub / GitLab
    │ git push
    ▼
GitLab CI
    ├── pytest
    ├── docker build → GitLab Registry
    └── update image tag в infra-repo
            │
            ▼
        ArgoCD
            │ helm upgrade
            ▼
    Kubernetes (k3s или managed)
        ├── Namespace: prod
        ├── Deployment: myapp (2 реплики, HPA: 2-8)
        ├── Service + Ingress (HTTPS через cert-manager)
        ├── StatefulSet: PostgreSQL + PVC
        └── ConfigMap + Secret

    Prometheus + Grafana + Loki
        ├── Метрики приложения (RED метрики)
        ├── Алерты в Telegram
        └── Логи всех Pod'ов

    Terraform (инфраструктура):
        ├── VPS (Hetzner/YandexCloud)
        ├── Firewall
        └── DNS записи

    Ansible (конфигурация):
        ├── k3s установлен
        ├── cert-manager установлен
        └── ArgoCD установлен
```

### Playbook — ключевые этапы

**Фаза 1: Инфраструктура (Terraform + Ansible)**
```
Шаг 1.1: terraform init && terraform apply
         # Создать VPS, firewall, DNS

Шаг 1.2: ansible-playbook setup-server.yml
         # Установить k3s, cert-manager, ArgoCD

Шаг 1.3: Проверить: kubectl get nodes — должен быть Ready

Шаг 1.4: Проверить: argocd app list — ArgoCD доступен
```

**Фаза 2: Мониторинг**
```
Шаг 2.1: helm install monitoring prometheus-community/kube-prometheus-stack ...
Шаг 2.2: kubectl apply -f argocd/monitoring-app.yaml
Шаг 2.3: Проверить: Grafana доступна через Ingress
Шаг 2.4: Проверить: алерт-правила загружены
```

**Фаза 3: Приложение**
```
Шаг 3.1: kubectl apply -f argocd/myapp.yaml (ArgoCD Application)
Шаг 3.2: ArgoCD синхронизирует из infra-repo
Шаг 3.3: Проверить: https://myapp.ru → 200
Шаг 3.4: Проверить: метрики в Grafana появились
```

**Фаза 4: CI/CD**
```
Шаг 4.1: Настроить GitLab CI переменные
Шаг 4.2: git push → пайплайн прошёл
Шаг 4.3: ArgoCD задеплоил новую версию
Шаг 4.4: Проверить: `kubectl rollout history` показывает деплой
```

**Финальный тест:**
```
terraform destroy
# Подождать 5 минут
terraform apply && ansible-playbook setup-server.yml
# Всё должно восстановиться за < 30 минут
```

### Checklist (30 пунктов)

**Функциональность (10 пунктов)**
- [ ] Приложение доступно через HTTPS по домену
- [ ] SSL сертификат валидный (не self-signed)
- [ ] API отвечает на `/health` → 200
- [ ] База данных подключена, данные сохраняются при рестарте Pod'а
- [ ] git push → пайплайн → новая версия задеплоена (< 10 минут)
- [ ] Rolling update: нет даунтайма при деплое
- [ ] HPA работает: при нагрузке реплики выросли
- [ ] Откат: `argocd app rollback myapp 1` → предыдущая версия
- [ ] Логи приложения видны в Grafana (Loki)
- [ ] Метрики приложения (RED) видны в Grafana

**Надёжность (10 пунктов)**
- [ ] Убить Pod → поднялся автоматически (< 30 сек)
- [ ] Перезагрузить сервер → всё поднялось само (< 5 минут)
- [ ] Удалить Pod PostgreSQL → данные сохранились после пересоздания
- [ ] ArgoCD selfHeal: ручное изменение в кластере → откатилось к Git
- [ ] Алерт в Telegram при недоступности приложения (< 2 минут)
- [ ] Алерт в Telegram при высоком error rate
- [ ] Retention метрик: 30 дней
- [ ] Liveness/Readiness probe настроены и работают
- [ ] PodDisruptionBudget: при обслуживании ноды — приложение доступно
- [ ] `terraform destroy && terraform apply` → полное восстановление

**Безопасность (10 пунктов)**
- [ ] Нет открытых портов кроме 80, 443, 22 (проверить через nmap)
- [ ] PostgreSQL не доступен снаружи кластера
- [ ] Секреты не в Git (только Sealed Secrets или Vault)
- [ ] Образ приложения без root user (`USER nonroot`)
- [ ] Ресурсы Pod'ов ограничены (requests и limits заданы)
- [ ] RBAC: CI-пользователь имеет минимальные права
- [ ] ArgoCD UI за авторизацией (не анонимный доступ)
- [ ] Grafana за авторизацией
- [ ] Network Policy: Pod'ы изолированы (db не доступна из других namespace)
- [ ] Все образы с конкретными тегами (не `latest`)

---

## Проект 2: Микросервисная архитектура

### Что строим

Три сервиса которые общаются между собой:

```
Интернет
    │ HTTPS
    ▼
Ingress NGINX
    ├──→ /api   → Service: api (FastAPI, 3 реплики)
    │               │ HTTP → Service: worker
    └──→ /       → Service: frontend (React/static, 2 реплики)

Service: worker (Python, обрабатывает задачи из очереди)
    │ → PostgreSQL (StatefulSet)
    │ → Redis (StatefulSet, для очереди)

Мониторинг:
    Prometheus scrapes all 3 services
    Grafana: дашборды для каждого сервиса + общий обзор
    Alertmanager: алерты если любой сервис недоступен
```

### Ключевые особенности

- Каждый сервис — отдельный git-репозиторий
- Каждый сервис — отдельный Helm chart
- ArgoCD ApplicationSet: один манифест → 3 приложения
- Межсервисная коммуникация только через Service (не напрямую по IP)
- Каждый сервис имеет свой `/metrics` endpoint

### Playbook — ключевые этапы

```
Фаза 1: Инфраструктура (такая же как Проект 1)

Фаза 2: Базовые сервисы
  Шаг 2.1: kubectl apply -f redis/   (StatefulSet + Service)
  Шаг 2.2: kubectl apply -f postgres/ (StatefulSet + Service)
  Шаг 2.3: Проверить: redis-cli ping → PONG
  Шаг 2.4: Проверить: psql -h postgres-svc → подключился

Фаза 3: Сервисы приложения (через ArgoCD ApplicationSet)
  Шаг 3.1: kubectl apply -f argocd/appset.yaml
  Шаг 3.2: argocd app list — видим api, worker, frontend
  Шаг 3.3: Проверить: каждый сервис отвечает на /health
  Шаг 3.4: Проверить: api → worker → postgres работает (e2e тест)

Фаза 4: Мониторинг каждого сервиса
  Шаг 4.1: ServiceMonitor для каждого сервиса
  Шаг 4.2: PrometheusRule: алерты для каждого
  Шаг 4.3: Grafana: дашборды для api, worker, frontend

Финальный тест:
  - Убить worker → api ставит задачи в очередь → worker поднялся → обработал
  - Убить postgres → worker ждёт → postgres поднялся → данные не потеряны
  - Задеплоить новую версию api → worker и frontend не перезапускаются
```

### Checklist (30 пунктов)

**Функциональность (10)**
- [ ] Все 3 сервиса доступны через Ingress
- [ ] api → worker коммуникация работает
- [ ] worker → postgres запись работает
- [ ] Redis очередь работает (задачи не теряются при перезапуске worker)
- [ ] Независимый деплой: обновить api без перезапуска worker
- [ ] ArgoCD ApplicationSet управляет всеми 3 сервисами
- [ ] Каждый сервис имеет отдельный CI пайплайн
- [ ] Метрики всех 3 сервисов в Grafana
- [ ] Логи всех 3 сервисов в Loki
- [ ] e2e тест: запрос через api → обработан worker → результат в postgres

**Надёжность (10)**
- [ ] Убить один из сервисов → остальные продолжают работать
- [ ] Redis failover: задачи сохраняются при рестарте Redis
- [ ] HPA настроен для api (публичный трафик)
- [ ] readinessProbe: сервис не получает трафик до готовности
- [ ] Алерт если любой из 3 сервисов недоступен > 2 минут
- [ ] Откат любого сервиса: `argocd app rollback api 1`
- [ ] Network Policy: worker не доступен из интернета (только через api)
- [ ] PodDisruptionBudget для api: минимум 1 реплика при обслуживании ноды
- [ ] Graceful shutdown: сервис не теряет запросы при остановке
- [ ] `terraform destroy && apply` → всё восстановлено за < 40 минут

**Безопасность (10)**
- [ ] Inter-service auth: api → worker через JWT или shared secret
- [ ] postgres доступен только из namespace приложения (Network Policy)
- [ ] Redis доступен только из namespace приложения
- [ ] Каждый сервис запускается под своим ServiceAccount
- [ ] Нет privileged контейнеров
- [ ] Все секреты в Sealed Secrets или Vault (не в Git открытым текстом)
- [ ] Resource limits для каждого сервиса
- [ ] readOnlyRootFilesystem: true (где возможно)
- [ ] Образы сканированы на уязвимости (trivy в CI)
- [ ] Все внешние зависимости pinned (конкретные версии)

---

## Проект 3: Disaster Recovery

### Что строим

Инфраструктура полностью описана в коде. Симуляция катастрофы и восстановление.

```
Цель: RTO < 30 минут, RPO < 5 минут

RTO (Recovery Time Objective)  — за сколько восстановить сервис
RPO (Recovery Point Objective) — сколько данных можно потерять
```

### Архитектура бэкапов

```
Kubernetes кластер
    │
    ├── Velero (backup operator)
    │   ├── Каждые 6 часов → backup кластера → S3
    │   └── Каждые 5 минут → backup PostgreSQL WAL → S3
    │
    ├── PostgreSQL
    │   └── WAL archiving → S3 (point-in-time recovery)
    │
    └── Terraform state → remote backend (S3)

Мониторинг бэкапов:
    Prometheus → метрики Velero
    Алерт если backup не выполнялся > 24 часов
```

### Playbook — симуляция катастроф

**Сценарий 1: Упал один Pod**
```
Шаг 1.1: kubectl delete pod myapp-xxx
Шаг 1.2: Наблюдать: pod поднялся за < 30 сек
Шаг 1.3: Проверить: данные не потеряны
Результат: автоматическое восстановление, RTO = 30 сек
```

**Сценарий 2: Corrupted deployment**
```
Шаг 2.1: kubectl set image deployment/myapp app=broken-image:latest
Шаг 2.2: Наблюдать: CrashLoopBackOff
Шаг 2.3: Получить алерт в Telegram
Шаг 2.4: argocd app rollback myapp 1
Шаг 2.5: Проверить: сервис восстановлен
Результат: откат через ArgoCD, RTO = 3 минуты
```

**Сценарий 3: Потеря данных PostgreSQL**
```
Шаг 3.1: Создать тестовые данные в БД
Шаг 3.2: Удалить PVC: kubectl delete pvc pgdata-0
Шаг 3.3: kubectl delete statefulset postgres
Шаг 3.4: velero restore create --from-backup postgres-backup
Шаг 3.5: Проверить: данные восстановлены
Результат: восстановление из backup, RTO = 10 минут
```

**Сценарий 4: Потеря всего сервера**
```
Шаг 4.1: terraform destroy
         # Сервер уничтожен
Шаг 4.2: terraform apply && ansible-playbook setup.yml
Шаг 4.3: velero restore create --from-backup full-cluster-backup
Шаг 4.4: Проверить: все сервисы работают
Шаг 4.5: Проверить: данные в БД — максимум 5 минут потерь
Результат: полное восстановление, RTO = 30 минут
```

### Checklist (30 пунктов)

**Функциональность бэкапов (10)**
- [ ] Velero установлен и настроен
- [ ] Backup кластера создаётся по расписанию (каждые 6 часов)
- [ ] Backup PostgreSQL создаётся (WAL archiving в S3)
- [ ] Terraform state в remote backend (S3)
- [ ] `velero get backups` — видны последние бэкапы
- [ ] Тест restore: `velero restore create --from-backup latest`
- [ ] Point-in-time recovery PostgreSQL — протестировано
- [ ] Все бэкапы зашифрованы (S3 server-side encryption)
- [ ] Мониторинг бэкапов: метрики Velero в Prometheus
- [ ] Алерт: backup не выполнялся > 24 часов → Telegram

**Сценарии восстановления (10)**
- [ ] Сценарий 1 пройден: Pod падает → восстановился за < 30 сек
- [ ] Сценарий 2 пройден: broken deploy → rollback за < 3 мин
- [ ] Сценарий 3 пройден: потеря PVC → restore из backup за < 10 мин
- [ ] Сценарий 4 пройден: потеря сервера → полное восстановление за < 30 мин
- [ ] RPO подтверждён: потеря данных < 5 минут при Сценарии 4
- [ ] Runbook написан: пошаговые инструкции для каждого сценария
- [ ] Runbook проверен: второй человек следовал и восстановил
- [ ] RTO подтверждён измерением времени восстановления
- [ ] Уведомления: каждый инцидент логируется (начало + конец)
- [ ] Post-mortem шаблон: для разбора инцидента

**Документация (10)**
- [ ] Архитектурная схема актуальна
- [ ] Все секреты документированы (где хранятся, как ротировать)
- [ ] SLA документирован (RTO, RPO, uptime %)
- [ ] Процедура обновления кластера описана
- [ ] Процедура добавления нового сервиса описана
- [ ] Процедура масштабирования описана
- [ ] Oncall runbook: кто что делает при инциденте
- [ ] Контакты: кому звонить при разных типах инцидентов
- [ ] `terraform destroy && apply && restore` задокументировано с таймингами
- [ ] Quarterly DR drill: расписание тестирования восстановления

---

## Проект 4: Platform Engineering

### Что строим

Внутренняя платформа для разработчиков. Developer self-service: разработчик деплоит сам, без помощи ops.

```
Platform Stack:

GitLab (код + CI/CD)
    │
ArgoCD (GitOps деплой)
    │
Kubernetes (вычисления)
    │
Prometheus + Grafana + Loki (observability)
    │
Backstage (developer portal) — опционально

Developer experience:
  push code → pipeline → deployed
  никаких тикетов в ops
  никаких ручных шагов
  самообслуживание через UI
```

### Что умеет платформа

**Разработчик может:**
- Задеплоить новое приложение через шаблон (Helm chart boilerplate)
- Посмотреть логи своего приложения в Grafana
- Откатить деплой в ArgoCD UI
- Масштабировать приложение через values.yaml

**Ops команда делает (один раз):**
- Настраивает Kubernetes кластер
- Настраивает ArgoCD, Prometheus, GitLab
- Создаёт templates для новых приложений
- Устанавливает guardrails (Resource Quota, Network Policy, LimitRange)

### Playbook — создание платформы

**Фаза 1: Foundation (то же что Проект 1)**
```
- Terraform: VPS, firewall, DNS
- Ansible: k3s, cert-manager
- ArgoCD: установка
- Prometheus stack: установка
- Loki: установка
```

**Фаза 2: Guardrails — безопасные дефолты**
```
Шаг 2.1: ResourceQuota для каждого namespace:
  - CPU: max 4 cores
  - Memory: max 8Gi
  - Pods: max 20

Шаг 2.2: LimitRange — дефолты для контейнеров:
  - CPU request: 100m, limit: 500m
  - Memory request: 128Mi, limit: 512Mi

Шаг 2.3: Network Policy — изоляция по умолчанию:
  - Запретить весь ingress внутри кластера
  - Разрешить только явно описанные соединения

Шаг 2.4: PodSecurityAdmission:
  - Namespace label: pod-security.kubernetes.io/enforce=restricted

Шаг 2.5: Проверить: нельзя создать privileged Pod в tenant namespace
```

**Фаза 3: Developer templates**
```
Шаг 3.1: Создать "golden path" Helm chart:
  helm create platform-app-template
  # Включает: Deployment, Service, Ingress, HPA, ServiceMonitor, PrometheusRule

Шаг 3.2: Создать ApplicationSet template в ArgoCD:
  # Разработчик создаёт файл в infra-repo → ArgoCD создаёт Application

Шаг 3.3: GitLab CI template:
  # Разработчик include этот template → получает тест+build+deploy бесплатно
  # .gitlab-ci.yml разработчика:
  include:
    - project: platform/ci-templates
      file: '/templates/python-service.yml'

Шаг 3.4: Документация для разработчика:
  "Как задеплоить новое приложение за 15 минут"
```

**Фаза 4: Onboarding нового приложения**
```
Шаг 4.1: Разработчик создаёт репозиторий myservice
Шаг 4.2: Копирует .gitlab-ci.yml с include платформы
Шаг 4.3: Создаёт values.yaml в infra-repo
Шаг 4.4: Создаёт Application в ArgoCD (или через ApplicationSet)
Шаг 4.5: Метрики и логи появляются автоматически
Итог: новый сервис в production за < 30 минут
```

### Checklist (30 пунктов)

**Platform capabilities (10)**
- [ ] Новое приложение онбордится за < 30 минут по документации
- [ ] GitLab CI template работает: разработчик только include, без copy-paste
- [ ] ArgoCD ApplicationSet создаёт Application автоматически из infra-repo
- [ ] Метрики нового приложения появляются в Grafana без настройки (автодискавери)
- [ ] Логи нового приложения появляются в Loki без настройки (Promtail)
- [ ] Dефолтные алерты работают для всех приложений (pod crash, high error rate)
- [ ] Resource Quota установлен для каждого namespace
- [ ] LimitRange обеспечивает дефолтные limits для новых Pod'ов
- [ ] Network Policy применена по умолчанию (deny all, allow explicit)
- [ ] Документация: "Как задеплоить новый сервис" — проверена независимым человеком

**Developer experience (10)**
- [ ] push → deploy без помощи ops
- [ ] Разработчик видит логи своего сервиса в Grafana (не нужен kubectl)
- [ ] Разработчик делает rollback через ArgoCD UI (не нужен kubectl)
- [ ] Разработчик видит статус пайплайна в GitLab (всё в одном месте)
- [ ] Разработчик получает алерт в Telegram при падении его сервиса
- [ ] Canary деплой доступен из коробки (Argo Rollouts настроен)
- [ ] Разработчик может масштабировать сервис через values.yaml
- [ ] Feature flags через ConfigMap (без рестарта приложения)
- [ ] Secrets rotation без даунтайма (через Kubernetes Secrets + reload)
- [ ] Локальная разработка: docker-compose совместим с K8s манифестами

**Безопасность и compliance (10)**
- [ ] PodSecurityAdmission: restricted mode для tenant namespace
- [ ] Нет privileged контейнеров ни в одном tenant namespace
- [ ] Все образы проходят сканирование trivy в CI pipeline
- [ ] RBAC: разработчик видит только свой namespace
- [ ] ArgoCD: разработчик может sync только свои Applications
- [ ] Secrets: Sealed Secrets или Vault — нет открытых секретов в Git
- [ ] Audit log: все действия в кластере логируются
- [ ] Container image: все образы от доверенных источников (image policy)
- [ ] Сканирование конфигурации: kube-bench или Polaris
- [ ] Quarterly security review: процедура описана и запланирована

---

## Принципы написания

### 1. Никакой теории — только команды и проверки

Формат каждого шага playbook:
```markdown
### Шаг 3.2: Установить ArgoCD

```bash
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd \
  -f argocd/values.yaml
```

✅ Проверить: `kubectl get pods -n argocd` — все поды Running
✅ Проверить: `argocd app list` — нет ошибок
```

### 2. Финальный тест — удали всё и восстанови

Каждый проект должен заканчиваться:
```markdown
## Финальная проверка — восстановление с нуля

```bash
# Уничтожить всё
terraform destroy

# Засечь время
time (terraform apply && ansible-playbook setup.yml && velero restore ...)

# Ожидаемое время: Project 1 < 30min, Project 2 < 40min
```

Если не восстановился — найди что не автоматизировано и автоматизируй.
```

### 3. Runbook для каждого инцидента

В каждом проекте — секция "Что делать если...":
```markdown
## Если приложение недоступно

1. Проверить: `kubectl get pods -n prod`
2. Проверить: `kubectl describe pod myapp-xxx`
3. Проверить: `argocd app get myapp`
4. Посмотреть: Grafana → MyApp dashboard
5. Откатить: `argocd app rollback myapp 1`
```

### 4. Тайминги — конкретные

После каждого сценария DR — замерить и записать реальное время:
```markdown
| Сценарий | Ожидаемый RTO | Фактический RTO |
|----------|---------------|-----------------|
| Pod падает | < 30 сек | ___ сек |
| Broken deploy | < 3 мин | ___ мин |
| Потеря PVC | < 10 мин | ___ мин |
| Потеря сервера | < 30 мин | ___ мин |
```

### 5. Checklistы — как настоящий production

Каждый checklist написать так, как если бы его заполнял SRE перед production-запуском.
Не "теоретически" — каждый пункт должен быть проверяемым командой или действием.

---

## Что НЕ надо делать

- ❌ Объяснять что такое ArgoCD, Prometheus, Terraform — читатель это знает
- ❌ Давать теорию без команды
- ❌ Пропускать блоки проверки после каждого шага
- ❌ Оставлять финальный тест опциональным — он обязателен
- ❌ Писать checklist без конкретных команд проверки
- ❌ Делать проекты полностью независимыми — они строятся один на другом

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-14.md          # Этот файл
└── 14-14-07-final-projects-2/                      # Модуль 14 (создать)
    ├── book.md                              # Обзор и как работать
    ├── project-1/
    │   ├── README.md                        # Архитектура, требования
    │   ├── playbook.md                      # Пошаговые команды
    │   └── checklist.md                     # 30 пунктов проверки
    ├── project-2/
    │   ├── README.md
    │   ├── playbook.md
    │   └── checklist.md
    ├── project-3/
    │   ├── README.md
    │   ├── playbook.md
    │   └── checklist.md
    └── project-4/
        ├── README.md
        ├── playbook.md
        └── checklist.md
```

---

## Связь с курсом

Все предыдущие модули используются в каждом проекте:

| Инструмент | Откуда | Где в проектах |
|-----------|--------|----------------|
| Terraform | M8 | Все проекты: инфраструктура |
| Ansible | M9 | Все проекты: настройка серверов |
| K8s basics | M10 | Все проекты: деплой |
| K8s + Helm | M11 | Все проекты: packaging |
| Prometheus + Grafana | M12 | Все проекты: observability |
| GitLab CI + ArgoCD | M13 | Все проекты: CI/CD |
| Linux | M1 | Все проекты: основа |
| Docker | M3 | Все проекты: контейнеры |
| Nginx/Caddy | M2 | Все проекты: Ingress |
| Security | M6 | Проект 3 и 4: безопасность |

---

*Эта инструкция — для ИИ-агента, который будет писать финальный модуль курса DevOps 2.0.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Предыдущая: AGENT-INSTRUCTIONS-module-13.md (GitLab CI + GitOps)*
*Это последний модуль курса DevOps 2.0.*
