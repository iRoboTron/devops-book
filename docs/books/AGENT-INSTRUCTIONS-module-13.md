# Инструкция для ИИ-агента: Написание книги по GitLab CI + GitOps

> **Это Модуль 13 курса DevOps 2.0.**
> Предварительные требования: пройдены модули 1–12.
> Смотри также:
> - [AGENT-INSTRUCTIONS-module-04.md](AGENT-INSTRUCTIONS-module-04.md) — Модуль 4 (GitHub Actions)
> - [AGENT-INSTRUCTIONS-module-11.md](AGENT-INSTRUCTIONS-module-11.md) — Модуль 11 (K8s + Helm)

---

## Контекст проекта

Ученик умеет деплоить в K8s и мониторить через Prometheus. Но деплой всё ещё частично ручной или через GitHub Actions с SSH.
GitLab CI — это более мощный инструмент с встроенным registry. ArgoCD — это GitOps: кластер сам синхронизируется с Git без push-доступа к серверу.

**Что он уже умеет** (не повторяй):
- GitHub Actions: тест → build → push → deploy (через SSH или kubectl)
- Helm charts для деплоя в K8s
- Понимает концепцию CI/CD из Модуля 4

**Что его раздражает прямо сейчас:**
- CI-сервер имеет SSH-доступ к production-серверу — это риск
- При каждом деплое нужно прокидывать credentials в CI
- Нет истории "кто и когда задеплоил что"
- Откат занимает время (написать новый пайплайн или делать вручную)

**Что он хочет после этой книги:**
Push в main → всё деплоится само, без SSH к серверу, с полной историей, с возможностью отката одной командой.

---

## Что за книга

**Название:** "GitLab CI + GitOps: ArgoCD и продвинутый CI/CD"

**Место в курсе:** Книга 13 из 14

**Объём:** 150-180 страниц

**Стиль:**
- Строится на знании GitHub Actions (Модуль 4) — сравнивает, не повторяет
- Проблема-первой: Глава 0 показывает боль ручного деплоя
- Каждая следующая глава убирает один ручной шаг
- ASCII-схемы для пайплайнов и GitOps потока

---

## Главная идея, которую должна передать книга

Два перехода:

**Переход 1: GitHub Actions → GitLab CI**
```
GitHub Actions:                GitLab CI:
.github/workflows/             .gitlab-ci.yml
Внешний registry               Встроенный GitLab Registry
Runner в облаке                Runner на своём сервере (дешевле)
```

**Переход 2: Push-деплой → Pull-деплой (GitOps)**
```
Push (GitHub Actions):         Pull (ArgoCD):
CI-сервер → SSH → сервер       Кластер сам смотрит в Git
CI нужны credentials кластера  Кластер сам тянет изменения
Ненадёжно при отказе CI        Работает даже если CI упал
```

**Ключевая идея GitOps:**
> Git — единственный источник правды.
> Что в Git — то в кластере. Нет ничего "настроенного вручную".
> ArgoCD не деплоит — он синхронизирует.

**Педагогический принцип — боль первой:**
Глава 0: делаем деплой вручную (SSH + docker pull + restart). Считаем шаги и риски.
Каждая следующая глава убирает один ручной шаг.
К концу: нет ни одного ручного действия.

---

## Что читатель построит к концу книги

```
Developer
    │ git push
    ▼
GitLab
    │
    ├── .gitlab-ci.yml pipeline
    │   ├── Stage: test    (pytest)
    │   ├── Stage: build   (docker build → GitLab Registry)
    │   └── Stage: update  (обновить image tag в helm-values repo)
    │
    └── Helm Values Repository (отдельный repo)
            │ изменился values.yaml (новый image tag)
            ▼
        ArgoCD (watching)
            │ обнаружил отличие Git vs кластер
            ▼
        Kubernetes cluster
            │ helm upgrade myapp
            ▼
        Задеплоено без SSH, без credentials в CI
```

---

## Структура книги

### Глава 0: Боль ручного деплоя — считаем шаги

**Цель:** читатель понимает что именно плохо в текущем процессе.

- Типичный деплой без GitLab CI:
  ```
  1. Написал код
  2. git push
  3. SSH на сервер
  4. git pull
  5. docker build -t myapp:new .
  6. docker stop myapp-container
  7. docker run -d myapp:new
  8. Проверить что работает
  9. Если нет — повторить руками
  ```
- Проблемы этого процесса:
  - 9 ручных шагов
  - SSH к production = риск
  - Нет истории кто и когда
  - Нет тестов перед деплоем
  - Откат = снова 9 шагов
- Цель курса: к концу этой книги → 0 ручных шагов

> После каждой главы будем вычёркивать ручные шаги. К главе 10 — вычеркнуты все.

---

### Часть 1: GitLab CI (Главы 1–5)

#### Глава 1: .gitlab-ci.yml — синтаксис и стадии

**Цель:** читатель пишет первый пайплайн и понимает его структуру.

- Сравнение с GitHub Actions:
  ```yaml
  # GitHub Actions:              # GitLab CI:
  on: [push]                    # триггер — автоматически
  jobs:                         stages:
    test:                         - test
      steps:                      - build
        - run: pytest           test:
                                  stage: test
                                  script:
                                    - pytest
  ```
- Минимальный `.gitlab-ci.yml`:
  ```yaml
  stages:
    - test
    - build
    - deploy

  test:
    stage: test
    image: python:3.12-slim
    script:
      - pip install -r requirements.txt
      - pytest

  build:
    stage: build
    script:
      - docker build -t myapp:$CI_COMMIT_SHA .
    only:
      - main
  ```
- Встроенные переменные:
  - `$CI_COMMIT_SHA` — hash коммита
  - `$CI_COMMIT_REF_NAME` — имя ветки
  - `$CI_REGISTRY_IMAGE` — адрес образа в GitLab Registry
  - `$CI_PROJECT_NAME` — имя проекта
- `only` / `except` / `rules` — когда запускать job
- `needs` — параллельные job'ы без ожидания stage
- `artifacts` — передать файлы между job'ами
- Pipeline UI в GitLab: наглядный граф job'ов

#### Глава 2: GitLab Runner — где запускаются пайплайны

**Цель:** читатель устанавливает свой Runner и понимает зачем.

- Shared Runner (GitLab.com) vs Self-hosted Runner:
  ```
  Shared Runner:          Self-hosted Runner:
  Бесплатно (лимиты)      Платишь только за сервер
  GitLab управляет        Ты управляешь
  Медленнее (очередь)     Быстрее (только твои задачи)
  ```
- Установка GitLab Runner на VPS:
  ```bash
  # Установка
  curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
  sudo apt install gitlab-runner

  # Регистрация
  sudo gitlab-runner register \
    --url https://gitlab.com \
    --registration-token YOUR_TOKEN \
    --executor docker \
    --docker-image alpine
  ```
- Executor: `docker` — каждый job в отдельном контейнере (изоляция)
- Runner tags: направить конкретные job'ы на конкретный Runner
- Runner в K8s: Kubernetes executor — job запускается как Pod

#### Глава 3: GitLab Registry — встроенное хранилище образов

**Цель:** читатель не использует Docker Hub, а хранит образы в GitLab.

- Зачем встроенный Registry:
  - Образ рядом с кодом и пайплайном
  - Автоматическая аутентификация в CI
  - Приватный по умолчанию
- Docker-in-Docker (DinD) в GitLab CI:
  ```yaml
  build:
    stage: build
    image: docker:24
    services:
      - docker:24-dind
    variables:
      DOCKER_TLS_CERTDIR: "/certs"
    script:
      - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
      - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
      - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  ```
- Альтернатива DinD: kaniko (не требует docker daemon)
- `$CI_REGISTRY`, `$CI_REGISTRY_USER`, `$CI_REGISTRY_PASSWORD` — автоматически в CI
- Политики очистки: когда удалять старые образы

#### Глава 4: Secrets и переменные окружения в GitLab

**Цель:** читатель безопасно передаёт секреты в пайплайн.

- GitLab CI/CD Variables: Settings → CI/CD → Variables
- Типы переменных:
  - `Variable` — обычная (видна в логах если не маскировать)
  - `File` — содержимое файла (для kubeconfig, ssh-ключей)
  - Masked — не показывать в логах
  - Protected — только для protected branches
- Группы переменных: переменные для всех проектов группы
- Environments: разные переменные для dev/staging/prod
  ```yaml
  deploy_prod:
    environment:
      name: production
      url: https://myapp.ru
    variables:
      K8S_NAMESPACE: prod
    rules:
      - if: $CI_COMMIT_BRANCH == "main"
  ```
- Vault integration: GitLab + HashiCorp Vault (упомянуть)
- Никогда не хардкодить секреты в `.gitlab-ci.yml`

#### Глава 5: Полный CI пайплайн

**Цель:** читатель собирает полный пайплайн: тест → build → push → deploy.

- Полный `.gitlab-ci.yml`:
  ```yaml
  stages:
    - test
    - build
    - deploy

  variables:
    DOCKER_TLS_CERTDIR: "/certs"

  test:
    stage: test
    image: python:3.12-slim
    before_script:
      - pip install -r requirements.txt
    script:
      - pytest --junitxml=report.xml
    artifacts:
      reports:
        junit: report.xml

  build:
    stage: build
    image: docker:24
    services:
      - docker:24-dind
    script:
      - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
      - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
      - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
      - docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA $CI_REGISTRY_IMAGE:latest
      - docker push $CI_REGISTRY_IMAGE:latest
    rules:
      - if: $CI_COMMIT_BRANCH == "main"

  deploy:
    stage: deploy
    image: bitnami/kubectl:latest
    script:
      - kubectl config set-cluster ...
      - kubectl set image deployment/myapp app=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    environment:
      name: production
    rules:
      - if: $CI_COMMIT_BRANCH == "main"
  ```
- Ручной вычёркивание: `push в main → образ собрался → задеплоился` — автоматически!

---

### Часть 2: GitOps и ArgoCD (Главы 6–9)

#### Глава 6: GitOps — идея и зачем ArgoCD

**Цель:** читатель понимает разницу между push-деплоем и pull-деплоем (GitOps).

- Push-деплой (CI деплоит):
  ```
  CI/CD → credentials → kubectl apply → кластер
  Проблемы:
  - CI нужны права на кластер
  - Если CI сломан — не задеплоишь
  - Кто-то мог изменить кластер вручную — CI не знает
  ```
- Pull-деплой (GitOps):
  ```
  Git (желаемое состояние)
      ↑ ArgoCD постоянно смотрит
  K8s кластер (реальное состояние)
      ← ArgoCD синхронизирует
  ```
- Принципы GitOps:
  1. Вся конфигурация в Git
  2. Git — единственный источник правды
  3. Изменения через Pull Request, не вручную
  4. Автоматическая синхронизация
- ArgoCD vs Flux: обе реализации GitOps (используем ArgoCD)
- Два репозитория (best practice):
  ```
  myapp-code/      ← код приложения, Dockerfile, тесты
  myapp-infra/     ← Helm values, K8s manifests
  ```
  CI обновляет `myapp-infra` → ArgoCD видит изменение → синхронизирует

#### Глава 7: ArgoCD — установка и первое приложение

**Цель:** читатель устанавливает ArgoCD и деплоит первое приложение через него.

- Установка:
  ```bash
  kubectl create namespace argocd
  kubectl apply -n argocd -f \
    https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
  ```
- Или через Helm:
  ```bash
  helm repo add argo https://argoproj.github.io/argo-helm
  helm install argocd argo/argo-cd -n argocd --create-namespace
  ```
- Доступ к UI:
  ```bash
  kubectl port-forward svc/argocd-server -n argocd 8080:443
  # пароль: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
  ```
- Настроить Ingress для ArgoCD UI (постоянный доступ)
- argocd CLI: `brew install argocd`
- Первое Application:
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: myapp
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://gitlab.com/user/myapp-infra.git
      targetRevision: main
      path: helm/myapp
      helm:
        valueFiles:
          - values.prod.yaml
    destination:
      server: https://kubernetes.default.svc
      namespace: prod
    syncPolicy:
      automated:
        prune: true        # удалять ресурсы которых нет в Git
        selfHeal: true     # восстанавливать при ручных изменениях кластера
  ```
- `kubectl apply -f application.yaml -n argocd`
- ArgoCD UI: видишь граф ресурсов, статус синхронизации, историю деплоев
- `argocd app sync myapp` — принудительная синхронизация
- `argocd app history myapp` — история

#### Глава 8: CI обновляет Git, ArgoCD деплоит

**Цель:** читатель настраивает полный GitOps цикл: push → CI → Git → ArgoCD → K8s.

- Как CI обновляет image tag в infra-репозитории:
  ```yaml
  # В .gitlab-ci.yml (myapp-code repo)
  update_image:
    stage: deploy
    image: alpine/git
    script:
      - git clone https://gitlab-ci-token:$CI_JOB_TOKEN@gitlab.com/user/myapp-infra.git
      - cd myapp-infra
      - |
        sed -i "s|image: .*|image: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA|" helm/myapp/values.prod.yaml
      - git config user.email "ci@gitlab.com"
      - git config user.name "GitLab CI"
      - git add .
      - git commit -m "Update myapp image to $CI_COMMIT_SHA"
      - git push
    rules:
      - if: $CI_COMMIT_BRANCH == "main"
  ```
- Полный цикл без единого ручного шага:
  ```
  git push → GitLab CI: test → build → push image → update infra repo
                                                              ↓
                                              ArgoCD: обнаружил изменение
                                                              ↓
                                              K8s: helm upgrade myapp
  ```
- selfHeal: кто-то изменил кластер вручную → ArgoCD вернёт к состоянию из Git
- prune: удалил ресурс из Git → ArgoCD удалит из кластера
- Почему два репозитория:
  - Можно изменить конфиг без изменения кода
  - История деплоев отделена от истории кода
  - Разные права: developer → code repo, ops → infra repo

#### Глава 9: Progressive Delivery — Canary и Blue-Green

**Цель:** читатель деплоит новую версию постепенно, не на 100% трафика сразу.

- Проблема rolling update: 100% трафика переключается на новую версию
- Canary deployment: 10% → 50% → 100%
  ```
  v1: ████████ 80%
  v2: ██ 20%
  ```
- Blue-Green deployment: два полных окружения, моментальное переключение
  ```
  Blue (active):  myapp:v1  ← 100% трафика
  Green (idle):   myapp:v2  ← тестируем

  После проверки: переключить трафик → Green становится active
  ```
- Argo Rollouts: расширение ArgoCD для progressive delivery
  ```bash
  kubectl create namespace argo-rollouts
  kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
  ```
- Rollout ресурс (замена Deployment):
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Rollout
  metadata:
    name: myapp
  spec:
    replicas: 5
    strategy:
      canary:
        steps:
        - setWeight: 20      # 20% трафика на новую версию
        - pause: {duration: 5m}  # подождать 5 минут
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
    template:
      # ... те же поля что в Deployment
  ```
- `kubectl argo rollouts get rollout myapp --watch`
- `kubectl argo rollouts promote myapp` — продвинуть на следующий шаг
- `kubectl argo rollouts abort myapp` — откат немедленно
- Анализ: автоматически проверять метрики и прерывать если error rate вырос
  ```yaml
  analysis:
    templates:
    - templateName: error-rate
    startingStep: 2
  ```

---

### Часть 3: ApplicationSet (Глава 10)

#### Глава 10: ApplicationSet — деплой в несколько окружений

**Цель:** читатель управляет несколькими окружениями из одного места.

- Проблема: 3 окружения × ручное создание Application в ArgoCD = хаос
- ApplicationSet: генератор ArgoCD Applications
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: ApplicationSet
  metadata:
    name: myapp-envs
  spec:
    generators:
    - list:
        elements:
        - env: dev
          namespace: dev
          values: values.dev.yaml
        - env: staging
          namespace: staging
          values: values.staging.yaml
        - env: prod
          namespace: prod
          values: values.prod.yaml
    template:
      metadata:
        name: "myapp-{{env}}"
      spec:
        source:
          repoURL: https://gitlab.com/user/myapp-infra.git
          path: helm/myapp
          helm:
            valueFiles:
              - "{{values}}"
        destination:
          namespace: "{{namespace}}"
  ```
- Один ApplicationSet → 3 Application → 3 деплоя
- Добавить окружение: добавить строку в `elements`
- Git generator: Application для каждой ветки или директории в репозитории

---

### Мини-проекты

#### Мини-проект 1: GitLab CI пайплайн
Настроить пайплайн для Python-приложения:
- `test`: pytest + coverage report
- `build`: docker build → push в GitLab Registry (тег = commit SHA)
- `deploy`: kubectl set image (простой деплой без ArgoCD)

Проверка: push → пайплайн прошёл → новая версия в кластере автоматически.

#### Мини-проект 2: ArgoCD автодеплой
1. Создать два репозитория: `app` (код) и `infra` (Helm values)
2. Настроить ArgoCD Application для `infra` репозитория
3. В CI: после build → обновить image tag в `infra` репозитории
4. Наблюдать: ArgoCD обнаружил изменение → задеплоил автоматически

Вычеркнуть: SSH к серверу, ручной docker pull, ручной restart.

#### Мини-проект 3: Blue-Green деплой
1. Настроить Argo Rollouts с Blue-Green стратегией
2. Задеплоить v1
3. Пустить трафик: `while true; do curl -s .../version; sleep 0.5; done`
4. Запустить деплой v2
5. Наблюдать: v1 всё ещё принимает трафик пока v2 не проверена
6. Переключить: `kubectl argo rollouts promote myapp`
7. Убедиться что переключение произошло без единой ошибки

---

### Приложения

#### Приложение A: Шпаргалка ArgoCD

| Команда | Назначение |
|---------|-----------|
| `argocd app list` | Список приложений |
| `argocd app get myapp` | Статус приложения |
| `argocd app sync myapp` | Принудительная синхронизация |
| `argocd app history myapp` | История деплоев |
| `argocd app rollback myapp 5` | Откат к ревизии 5 |
| `argocd app diff myapp` | Разница Git vs кластер |

#### Приложение B: Готовые конфиги
- Полный `.gitlab-ci.yml`: test → build → update infra
- ArgoCD Application манифест
- ArgoCD ApplicationSet для 3 окружений
- Argo Rollouts: canary strategy
- Argo Rollouts: blue-green strategy

#### Приложение C: Диагностика
- ArgoCD `OutOfSync` → `argocd app diff`, понять что отличается
- ArgoCD не видит репозиторий → проверить credentials в Settings → Repositories
- GitLab CI не может push в infra repo → настроить deploy token или SSH key
- Rollout застрял → `argocd rollouts describe`, проверить analysisrun
- `selfHeal` откатывает ручные изменения → это правильное поведение, изменяй только через Git

---

## Принципы написания

### 1. Боль-первой → автоматизация-потом

Глава 0 задаёт список из 9 ручных шагов.
После каждой части — буквально вычёркивать шаги:
```
~~1. Написал код~~       (в git всегда)
~~2. git push~~          (автоматически триггерит CI)
~~3. SSH на сервер~~     (ArgoCD деплоит без SSH)
...
```
К концу книги: 0 ручных шагов, весь список вычеркнут.

### 2. GitLab CI vs GitHub Actions — явно

Читатель знает GitHub Actions (Модуль 4). Используй это:
```yaml
# GitHub Actions (знакомо):
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest

# GitLab CI (новое):
test:
  script:
    - pytest
  # триггер — автоматически при push
```
Показывай эквивалентные конструкции — читатель переносит знания.

### 3. Два репозитория — объяснять каждый раз

Паттерн app-repo + infra-repo непривычен. При каждом упоминании объяснять зачем:
```
app-repo  → код → CI → образ
                    ↓
              infra-repo (CI делает коммит с новым тегом)
                    ↓
              ArgoCD → кластер
```

### 4. ASCII-схемы для потока деплоя

В каждой главе — схема того что мы автоматизировали:
```
До этой главы:      После этой главы:
[ручной шаг X]  →  [автоматический шаг X]
```

### 5. Никакой воды

- Без истории создания GitLab
- Без сравнения ArgoCD vs Flux в деталях
- Без Jenkins, TeamCity, CircleCI
- Без Spinnaker

---

## Что НЕ надо делать

- ❌ Повторять GitHub Actions из Модуля 4 — только сравнивать
- ❌ Хардкодить credentials в `.gitlab-ci.yml`
- ❌ Настраивать ArgoCD без Ingress — только port-forward неудобен
- ❌ Пропускать паттерн двух репозиториев — это ключевая практика
- ❌ Объяснять Canary/Blue-Green без демонстрации с реальным трафиком

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-13.md          # Этот файл
└── gitops-devops/                           # Книга 13 (создать)
    ├── book.md
    ├── chapter-00.md                        # Боль ручного деплоя
    ├── chapter-01.md                        # .gitlab-ci.yml
    ├── chapter-02.md                        # GitLab Runner
    ├── chapter-03.md                        # GitLab Registry
    ├── chapter-04.md                        # Secrets и variables
    ├── chapter-05.md                        # Полный CI пайплайн
    ├── chapter-06.md                        # GitOps: идея и ArgoCD
    ├── chapter-07.md                        # ArgoCD: первое приложение
    ├── chapter-08.md                        # CI + ArgoCD: полный цикл
    ├── chapter-09.md                        # Canary и Blue-Green
    ├── chapter-10.md                        # ApplicationSet
    ├── appendix-a.md
    ├── appendix-b.md
    └── appendix-c.md
```

---

## Связь с другими модулями

**Что нужно из Модуля 4 (GitHub Actions):**
- Концепция CI/CD — та же, другой синтаксис
- Секреты в CI — та же идея
- docker build + push — повторяется, но теперь в GitLab Registry

**Что нужно из Модуля 11 (K8s + Helm):**
- Helm charts — ArgoCD деплоит именно их
- Namespace — ArgoCD управляет по namespace
- RBAC — ArgoCD нужны права на кластер

**Что нужно из Модуля 12 (Мониторинг):**
- Prometheus метрики — используются в Argo Rollouts Analysis
- Grafana annotations — отмечать деплои ArgoCD на графиках

**Что даёт Модулю 14 (Финальные проекты):**
- Полный GitOps пайплайн — используется во всех 4 проектах
- ArgoCD — основной инструмент деплоя
- ApplicationSet — управление dev/staging/prod

---

*Эта инструкция — для ИИ-агента, который будет писать тринадцатую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Предыдущая: AGENT-INSTRUCTIONS-module-12.md (Мониторинг)*
*Следующая: AGENT-INSTRUCTIONS-module-14.md (Финальные проекты)*
