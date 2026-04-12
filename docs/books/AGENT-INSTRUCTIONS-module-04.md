# Инструкция для ИИ-агента: Написание книги по CI/CD для DevOps

> **Это Модуль 4 курса DevOps.**
> Смотри также:
> - [AGENT-INSTRUCTIONS.md](AGENT-INSTRUCTIONS.md) — Модуль 1 (Linux)
> - [AGENT-INSTRUCTIONS-module-02.md](AGENT-INSTRUCTIONS-module-02.md) — Модуль 2 (Сеть, Nginx)
> - [AGENT-INSTRUCTIONS-module-03.md](AGENT-INSTRUCTIONS-module-03.md) — Модуль 3 (Docker)

---

## Контекст проекта

Этот проект — обучение DevOps с нуля до самостоятельности.
Ученик — программист, который прошёл Модули 1–3.

**Что он уже умеет** (не повторяй, считай само собой разумеющимся):
- Уверенно работает в Linux, настраивает сервисы через systemd
- Настраивал Nginx, HTTPS, ufw — сервер стоит и работает
- Пишет Dockerfile, docker-compose.yml, управляет томами и сетями
- Знает как работают переменные окружения и `.env`-файлы
- Умеет читать логи, диагностировать проблемы

**Чего ему не хватает:**
Каждый раз при изменении кода — вручную заходить на сервер, делать `git pull`, `docker-compose build`, `docker-compose up`. Это медленно, скучно и можно забыть шаг. Хочет: запушил в git → сервер сам обновился.

**Что он хочет после этой книги:**
Настроить пайплайн так, чтобы `git push` в ветку `main` автоматически запускал тесты, собирал Docker-образ и деплоил его на сервер. Понимать что происходит в пайплайне, уметь читать логи и чинить упавшие джобы.

---

## Что за книга

**Название:** "CI/CD для DevOps: Автоматизация от push до продакшна"

**Место в курсе:** Книга 4 из 4

**Целевая аудитория:**
- Прошёл Модули 1–3
- Делал деплой вручную и хочет его автоматизировать
- Слышал про GitHub Actions, но никогда не писал пайплайн самостоятельно

**Объём:** 130-160 страниц

**Стиль:** тот же, что во всех предыдущих модулях:
- Простой язык, без академизма
- Одна концепция — одно объяснение
- ASCII-схемы для пайплайнов и потоков данных
- Много практики, реальные задачи
- Без воды

---

## Главная идея, которую должна передать книга

CI/CD — это **конвейер**, который берёт твой код и доставляет его на сервер автоматически, каждый раз одинаково.

```
Разработчик                CI/CD                    Сервер
    │                         │                         │
    │  git push               │                         │
    ├────────────────────────►│                         │
    │                         │  1. Checkout code       │
    │                         │  2. Run tests           │
    │                         │  3. Build Docker image  │
    │                         │  4. Push to registry    │
    │                         │  5. Deploy to server    │
    │                         ├────────────────────────►│
    │                         │                         │  docker pull
    │                         │                         │  docker-compose up
    │                         │                         │
```

**CI (Continuous Integration)** — автоматически проверяет что код не сломан.
**CD (Continuous Delivery/Deployment)** — автоматически доставляет код на сервер.

Книга строится вокруг одного пайплайна, который усложняется от главы к главе.

---

## Что читатель настроит к концу книги

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest

  build-and-push:
    needs: test
    steps:
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          tags: ghcr.io/user/myapp:${{ github.sha }}

  deploy:
    needs: build-and-push
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/myapp
            echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
            docker-compose pull
            docker-compose up -d
```

Push в `main` → тесты → сборка образа → деплой на сервер. Без единого ручного шага.

---

## Структура книги

### Глава 0: Что такое CI/CD и зачем это нужно

**Цель:** читатель понимает зачем всё это, до того как начнёт настраивать.

- Жизнь без CI/CD: ручной деплой, пропущенный шаг, "работало час назад"
- Что такое CI и CD — разница:
  - CI: каждый коммит проверяется автоматически
  - CD (Delivery): можно задеплоить одной кнопкой
  - CD (Deployment): деплой происходит автоматически
- Обзор инструментов: GitHub Actions, GitLab CI, Jenkins, CircleCI
  - Почему книга про GitHub Actions: бесплатно, встроено в GitHub, достаточно для начала
- Схема: как GitHub Actions вписывается в рабочий процесс
- **Нет упражнений** — это обзорная глава

---

### Часть 1: Git для CI/CD (Главы 1-2)

#### Глава 1: Git — ветки, merge, pull request

**Цель:** читатель работает с ветками и понимает какие коммиты попадут в деплой.

> **Важно:** Не учить git с нуля — предполагается что читатель знает `git add`, `commit`, `push`. Здесь — углублённо про то, что нужно для CI/CD.

- Ветки: зачем нужны в контексте деплоя
  - `main` (или `master`) — то что в продакшне
  - `develop` — то что тестируется
  - `feature/xxx` — то что разрабатывается
- Стратегии веток: GitHub Flow (простая) vs Git Flow (сложная)
  - Для начала: только GitHub Flow — одна `main`, feature-ветки, PR
  ```
  main ─────────────────────────────── [продакшн]
         ↑ merge
  feature/login ──────────── [разработка]
  ```
- `git merge` vs `git rebase` — когда что использовать
- Pull Request / Merge Request: код-ревью перед деплоем
- Защита ветки `main`: запретить прямой push, требовать PR
- Теги и версии: `git tag v1.0.0`, семантическое версионирование
- `git log --oneline --graph` — видеть историю наглядно
- **Упражнения:** создать feature-ветку, сделать PR, смержить, посмотреть историю

#### Глава 2: Git Hooks — автоматизация на уровне git

**Цель:** читатель понимает как git может запускать скрипты автоматически.

- Что такое git hook: скрипт который запускается при определённом событии
- Хуки на клиенте:
  - `pre-commit` — запустить линтер до коммита
  - `commit-msg` — проверить формат сообщения коммита
  - `pre-push` — запустить тесты до push
- Хуки на сервере:
  - `post-receive` — задеплоить после push (простой деплой без GitHub Actions)
- Простой деплой через `post-receive` хук:
  ```bash
  #!/bin/bash
  # /opt/myapp.git/hooks/post-receive
  cd /opt/myapp
  git pull
  docker-compose build
  docker-compose up -d
  ```
- `pre-commit` утилита — менеджер хуков (упомянуть, не углубляться)
- **Упражнения:** написать `pre-commit` хук для линтера, настроить `post-receive` для простого автодеплоя

> **Запомни:** Git хуки в `.git/hooks/` не коммитятся в репозиторий. Если нужно чтобы хуки работали у всей команды — используй `pre-commit` утилиту или CI.

---

### Часть 2: GitHub Actions (Главы 3-5)

#### Глава 3: Первый пайплайн

**Цель:** читатель запускает свой первый GitHub Actions workflow.

- Как работает GitHub Actions:
  ```
  Событие (push) → Workflow → Job → Step → Action
  ```
- Файл `.github/workflows/ci.yml` — где лежит и как называть
- Структура workflow:
  - `on:` — триггеры (push, pull_request, schedule, workflow_dispatch)
  - `jobs:` — параллельные или последовательные задачи
  - `runs-on:` — где выполняется (ubuntu-latest, windows, macos)
  - `steps:` — шаги внутри job
  - `uses:` — готовое действие из маркетплейса
  - `run:` — произвольная команда
- Минимальный пример — проверить что Python-код запускается:
  ```yaml
  on: [push]
  jobs:
    hello:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: echo "Hello from GitHub Actions"
        - run: python --version
  ```
- Runner: что это, бесплатные лимиты GitHub
- Логи: как читать вывод каждого шага в интерфейсе GitHub
- Значки статуса: `[![CI](badge-url)](workflow-url)` в README
- **Упражнения:** создать workflow, намеренно сломать шаг, прочитать логи и починить

#### Глава 4: Тесты в пайплайне

**Цель:** читатель автоматически запускает тесты при каждом push.

- Зачем тесты в CI: "не сломал ли я что-то новым коммитом"
- Установка зависимостей и запуск pytest:
  ```yaml
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -r requirements.txt
    - run: pytest --tb=short
  ```
- `actions/setup-python` — зачем action вместо просто `run: python`
- Матрица версий: тестировать на нескольких версиях Python:
  ```yaml
  strategy:
    matrix:
      python-version: ['3.11', '3.12']
  ```
- Кэш зависимостей: `actions/cache` для pip — чтобы не ставить заново каждый раз
- Статус проверки в Pull Request — блокировать merge если тесты не прошли
- Покрытие кода: `pytest --cov` + вывод в Summary (базово)
- **Упражнения:** добавить тесты в пайплайн, настроить матрицу версий, проверить что PR не мержится при упавших тестах

> **Запомни:** CI без тестов — это просто "запустить скрипт при push". Ценность CI именно в том что он говорит "этот коммит сломал вот это".

#### Глава 5: Секреты и переменные окружения в GitHub Actions

**Цель:** читатель безопасно передаёт ключи SSH и другие секреты в пайплайн.

- Проблема: нельзя хранить SSH-ключ в `.github/workflows/deploy.yml`
- GitHub Secrets: Settings → Secrets and variables → Actions
  - `secrets.SERVER_HOST` — IP сервера
  - `secrets.SSH_PRIVATE_KEY` — приватный ключ для SSH на сервер
  - `secrets.REGISTRY_TOKEN` — токен для Docker registry
- Переменные (Variables) vs Секреты (Secrets):
  - Variables — несекретные значения (URL сервера, имя образа)
  - Secrets — пароли, ключи, токены
- Как использовать в workflow: `${{ secrets.MY_SECRET }}`
- Переменные окружения в workflow:
  ```yaml
  env:
    IMAGE_NAME: ghcr.io/${{ github.repository }}
    IMAGE_TAG: ${{ github.sha }}
  ```
- `github` контекст: `github.sha`, `github.ref_name`, `github.actor`
- Environment (Environments в GitHub): staging vs production, ручное подтверждение
- **Упражнения:** добавить секреты, использовать их в workflow, убедиться что они не попадают в логи

> **Запомни:** GitHub автоматически маскирует значения секретов в логах. Но не стоит проверять это намеренно.

---

### Часть 3: Деплой (Главы 6-7)

#### Глава 6: Сборка и публикация Docker-образа

**Цель:** пайплайн собирает образ и публикует его в реестр.

- Зачем реестр: сервер тянет уже собранный образ, не собирает сам
- GitHub Container Registry (ghcr.io) — бесплатно, встроено в GitHub
- Логин в ghcr.io из Actions:
  ```yaml
  - uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
  ```
- `GITHUB_TOKEN` — автоматический токен, не нужно создавать вручную
- Сборка и публикация:
  ```yaml
  - uses: docker/build-push-action@v5
    with:
      push: true
      tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
  ```
- Тегирование образов:
  - По `github.sha` — для деплоя конкретного коммита
  - По `latest` — удобно, но непредсказуемо
  - По тегу git (`v1.0.0`) — для релизов
- Кэш слоёв Docker в Actions: `cache-from`, `cache-to` — ускорение сборки
- `docker/metadata-action` — автоматические теги по git-событиям
- **Упражнения:** опубликовать образ в ghcr.io, проверить что он появился в GitHub → Packages

#### Глава 7: Автодеплой на сервер

**Цель:** пайплайн деплоит новый образ на сервер по SSH.

- Стратегии деплоя:
  ```
  1. SSH + docker-compose pull + up   → просто, для небольших проектов
  2. SSH + скрипт деплоя             → больше контроля
  3. Webhook на сервере              → сервер сам тянет по сигналу
  ```
  Книга учит стратегию 1 (SSH), упоминает остальные.
- Подготовка сервера:
  - Создать пользователя `deploy` с минимальными правами
  - Добавить SSH-ключ в `~/.ssh/authorized_keys`
  - Добавить `deploy` в группу `docker`
- `appleboy/ssh-action` — выполнить команды на сервере по SSH:
  ```yaml
  - uses: appleboy/ssh-action@v1
    with:
      host: ${{ secrets.SERVER_HOST }}
      username: deploy
      key: ${{ secrets.SSH_PRIVATE_KEY }}
      script: |
        cd /opt/myapp
        export IMAGE_TAG=${{ github.sha }}
        docker-compose pull app
        docker-compose up -d app
        docker image prune -f
  ```
- `needs:` — порядок jobs: тесты → сборка → деплой
  ```yaml
  jobs:
    test:
      ...
    build:
      needs: test
      ...
    deploy:
      needs: build
      ...
  ```
- Проверка деплоя: `docker-compose exec app curl localhost:8000/health`
- **Упражнения:** настроить полный пайплайн test → build → deploy, сломать тест и проверить что деплой не произошёл

> **Порядок важен:** `needs: [test, build]` означает "запускай только если оба прошли успешно". Без этого — деплой сломанного кода.

---

### Часть 4: Стратегии и надёжность (Главы 8-9)

#### Глава 8: Стратегии деплоя

**Цель:** читатель знает как деплоить без даунтайма и откатываться при проблемах.

- Проблема простого деплоя:
  ```
  docker-compose down   ← 5-10 секунд даунтайма
  docker-compose up -d
  ```
- **Rolling update через docker-compose:**
  ```yaml
  # docker-compose.yml
  services:
    app:
      image: ghcr.io/user/myapp:${IMAGE_TAG}
  ```
  ```bash
  # на сервере
  docker-compose pull app
  docker-compose up -d --no-deps app   # перезапустить только app без down
  ```
- **Healthcheck перед переключением:**
  ```bash
  docker-compose up -d app
  docker-compose exec app curl -f localhost:8000/health || docker-compose rollback
  ```
- **Rollback — откат к предыдущей версии:**
  ```bash
  # Сохраняем предыдущий тег
  PREV_TAG=$(cat /opt/myapp/.current_tag)
  echo $NEW_TAG > /opt/myapp/.current_tag
  # Если деплой упал:
  IMAGE_TAG=$PREV_TAG docker-compose up -d app
  ```
- Переменная `IMAGE_TAG` в `.env` файле на сервере — как обновлять
- Blue-green деплой: идея (объяснить концепцию, не реализовывать)
- Ручное подтверждение перед продакшн-деплоем:
  ```yaml
  deploy-production:
    environment:
      name: production
  ```
  GitHub будет просить подтвердить в UI.
- **Упражнения:** реализовать rollback-скрипт, протестировать откат вручную

#### Глава 9: Итоговый проект

**Цель:** собрать полный пайплайн с нуля, самостоятельно.

Что нужно настроить:
1. GitHub репозиторий с защищённой веткой `main` (merge только через PR)
2. Workflow `ci.yml`: тесты на каждый push/PR
3. Workflow `deploy.yml`: сборка + деплой при push в `main`
4. GitHub Secrets: SERVER_HOST, SSH_PRIVATE_KEY, REGISTRY_TOKEN
5. Сервер: пользователь `deploy`, SSH-ключ, `/opt/myapp` с `docker-compose.yml`
6. Rollback-скрипт на сервере
7. Healthcheck в `docker-compose.yml`
8. Бейдж статуса CI в README.md

**Чеклист готовности:**
- [ ] `git push` в feature-ветку → запускаются тесты
- [ ] PR с упавшими тестами → merge заблокирован
- [ ] Merge в `main` → автоматически деплоится на сервер
- [ ] `curl https://domain.ru/health` → 200 после деплоя
- [ ] Откат работает: `./rollback.sh` возвращает предыдущую версию
- [ ] Секреты не видны в логах Actions

---

### Приложения

#### Приложение A: Шпаргалка по GitHub Actions
- Контексты: `github.*`, `secrets.*`, `env.*`
- Часто используемые actions: checkout, setup-python, docker/login, ssh-action
- Триггеры: push, pull_request, schedule, workflow_dispatch

#### Приложение B: Готовые шаблоны workflow
- `ci.yml` — тесты + линтер
- `deploy.yml` — сборка Docker + деплой по SSH
- `release.yml` — деплой по git-тегу с ручным подтверждением

#### Приложение C: Диагностика пайплайнов
- Job не запускается → проверь `on:` и ветку
- `Permission denied` при docker push → проверь `permissions:` и `GITHUB_TOKEN`
- SSH: `Host key verification failed` → `StrictHostKeyChecking no` или добавить в known_hosts
- Деплой прошёл, сайт не обновился → `docker-compose ps`, `docker logs`
- Пайплайн медленный → добавь кэш pip и Docker layer cache

---

## Принципы написания

Все принципы Модулей 1–3, плюс специфичные для CI/CD:

### 1. Пайплайн строится постепенно
Не показывай финальный `deploy.yml` в начале — он пугает.
Начни с `echo "hello"`, добавляй шаги по одному.
К концу книги читатель сам соберёт финальный файл, понимая каждую строку.

### 2. Объясняй YAML-синтаксис при первом использовании
GitHub Actions — это YAML. Отступы важны.
При первом использовании любой конструкции (`on:`, `jobs:`, `steps:`, `uses:`) объясняй что она значит.

### 3. Показывай логи Actions
После каждого примера workflow показывай как выглядит успешный и провальный вывод в интерфейсе GitHub.
Читатель должен знать где читать логи, не только как их писать.

### 4. Безопасность по умолчанию
- Секреты не в файлах — всегда через GitHub Secrets
- Пользователь `deploy` с минимальными правами — не `root`
- Образы с конкретными тегами — не `latest`

### 5. ASCII-схемы обязательны
Особенно для:
- Общей схемы пайплайна (push → jobs → сервер)
- Порядка jobs (test → build → deploy)
- Стратегий деплоя

### 6. Никакой воды
- Без Jenkins, CircleCI, GitLab CI в деталях (только упомянуть)
- Без Kubernetes, Helm, ArgoCD
- Без микросервисов и сложных топологий
- Без теории про DevOps-культуру и Agile

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS.md                    # Модуль 1
├── AGENT-INSTRUCTIONS-module-02.md          # Модуль 2
├── AGENT-INSTRUCTIONS-module-03.md          # Модуль 3
├── AGENT-INSTRUCTIONS-module-04.md          # Этот файл
├── linux-for-devops/                        # Книга 1
├── nginx-https-devops/                      # Книга 2
├── docker-devops/                           # Книга 3
└── cicd-devops/                             # Книга 4 (создать)
    ├── book.md                              # Оглавление
    ├── chapter-00.md
    └── ...
```

### Форматирование
- Markdown
- `#` — название главы, `##` — раздел, `###` — подраздел
- Код с языком: ` ```yaml `, ` ```bash `, ` ```dockerfile `
- ASCII-схемы в ` ```text ` или ` ``` `
- Таблицы для сравнений

### Объём
- Каждая глава: 15-20 страниц
- Примеры workflow: минимум 2 варианта (простой и с улучшениями)
- Упражнения: 3-5 на главу

---

## Проверка качества

Перед сдачей каждой главы проверь:

1. **Понятность:** поймёт ли человек, который никогда не писал workflow?
2. **Нарастание сложности:** каждая глава строит на предыдущей, не перепрыгивает?
3. **Безопасность:** нет ли секретов в примерах кода?
4. **Схемы:** есть ли ASCII-диаграмма пайплайна?
5. **Логи:** показано ли как выглядит успешный и упавший прогон?
6. **Упражнения:** проверяют ли они реальную настройку, а не просто копирование?
7. **Без воды:** нет ли сравнений с Jenkins и рассуждений про DevOps-культуру?

---

## Что НЕ надо делать

- ❌ Не объяснять Jenkins, CircleCI, GitLab CI подробно
- ❌ Не объяснять Kubernetes, Helm, ArgoCD — это другой курс
- ❌ Не хардкодить секреты в примерах (даже "для простоты")
- ❌ Не показывать финальный сложный workflow в начале книги
- ❌ Не деплоить под `root` пользователем в примерах
- ❌ Не использовать `latest` тег образов в примерах деплоя
- ❌ Не объяснять git с нуля — только то что нужно для CI/CD
- ❌ Не уходить в теорию DevOps-культуры, Agile, Scrum

---

## Связь с другими модулями

**Что нужно из Модуля 1:**
- Shell-скрипты — скрипт деплоя и rollback на сервере
- systemd — понять что docker-compose запускается как сервис
- SSH — пайплайн ходит на сервер по SSH

**Что нужно из Модуля 2:**
- Nginx — за ним живёт приложение которое мы деплоим
- ufw — помнить про нюанс с Docker и iptables

**Что нужно из Модуля 3:**
- `docker-compose.yml` — пайплайн обновляет именно его
- `IMAGE_TAG` в `.env` — механизм смены версии образа
- `docker-compose pull` + `up -d` — команды деплоя

**Что даёт финальному проекту:**
Это последняя книга. После неё читатель умеет:
- Разрабатывать локально
- Пушить код
- Автоматически получать его на сервере с тестами и без даунтайма

---

## План работы

1. **book.md** — оглавление книги 4
2. **chapter-00.md** — что такое CI/CD, зачем
3. **chapter-01.md** — git ветки для CI/CD
4. И так далее по одной главе

**Не пиши всю книгу сразу.** Пиши по одной главе, проверяй, получай обратную связь.

---

*Эта инструкция — для ИИ-агента, который будет писать четвёртую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Смотри Модуль 3: /home/adelfos/Documents/lessons/dev-ops/docs/books/AGENT-INSTRUCTIONS-module-03.md*
