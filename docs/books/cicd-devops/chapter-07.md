# Глава 7: Автодеплой на сервер

> **Запомни:** Это финальный шаг конвейера. Код прошёл тесты → образ собран → теперь доставить его на сервер. Без SSH руками.

---

## 7.1 Стратегии деплоя

### Стратегия 1: SSH + docker-compose pull + up (учим в этой книге)

```
CI по SSH → сервер → docker pull → docker compose up -d
```

**Плюсы:** Просто, надёжно, понятно.
**Минусы:** Короткий даунтайм при перезапуске.
**Когда:** Небольшие проекты, одна команда.

### Стратегия 2: Webhook на сервере (упоминаем)

```
CI → POST webhook → сервер сам pull + up
```

**Плюсы:** Сервер контролирует деплой.
**Минусы:** Нужно написать свой сервис для webhook.

### Стратегия 3: GitOps (упоминаем)

```
CI → обновить manifest в git → ArgoCD видит → деплоит
```

**Плюсы:** Всё в git, аудит, rollback = revert коммита.
**Минусы:** Нужен Kubernetes + ArgoCD.

> **Запомни:** Стратегия 1 покрывает 90% потребностей.
> Остальные — когда вырастешь.

---

## 7.2 Подготовка сервера

### Создать пользователя deploy

```bash
# На сервере
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
```

`-aG docker` = deploy может запускать docker без sudo.

### Сгенерировать SSH-ключ для CI

На **локальной машине** (не на сервере):

```bash
ssh-keygen -t ed25519 -C "ci-deploy" -f ~/.ssh/ci_deploy -N ""
```

`-N ""` = без пассфразы (CI не может ввести пароль).

### Добавить публичный ключ на сервер

```bash
ssh-copy-id -i ~/.ssh/ci_deploy.pub deploy@server-ip
```

Или вручную:

```bash
# На сервере
mkdir -p /home/deploy/.ssh
# Вставь содержимое ci_deploy.pub
nano /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
```

### Проверить подключение

```bash
ssh -i ~/.ssh/ci_deploy deploy@server-ip
```

Должно работать без пароля.

### Приватный ключ → GitHub Secret

```bash
cat ~/.ssh/ci_deploy
```

Скопируй **весь** вывод (включая BEGIN/END строки).

GitHub → Settings → Secrets → New repository secret:

```
Name: SSH_PRIVATE_KEY
Value: (весь приватный ключ)
```

Также добавь:

```
Name: SERVER_HOST
Value: 203.0.113.50
```

---

## 7.3 appleboy/ssh-action — выполнить команды на сервере

```yaml
- uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.SERVER_HOST }}
    username: deploy
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    script: |
      cd /opt/myapp
      docker compose pull app
      docker compose up -d app
      docker image prune -f
```

### Разбор

| Параметр | Значение |
|----------|----------|
| `host` | IP сервера (из секрета) |
| `username` | Пользователь на сервере |
| `key` | SSH-ключ (из секрета) |
| `script` | Команды которые выполнить |

### Что делает скрипт

```bash
cd /opt/myapp                     ← перейти в директорию
docker compose pull app           ← скачать новый образ
docker compose up -d app          ← перезапустить (только app)
docker image prune -f             ← удалить старые образы
```

> **Запомни:** `docker compose pull` + `up -d` = обновление.
> Не нужно `down` — это вызывает даунтайм.
> `up -d` сам пересоздаст контейнер если образ новый.

---

## 7.4 Полный пайплайн: test → build → deploy

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest --tb=short

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: deploy
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/myapp
            export IMAGE_TAG=${{ github.sha }}
            docker compose pull app
            docker compose up -d app
            docker image prune -f
```

### Порядок выполнения

```
push в main
    │
    ├── test ──────────────────────▶ ✅
    │                                   │
    ├── build-and-push ────────────▶ ✅  │ (ждёт test)
    │                                   │
    └── deploy ────────────────────▶ ✅  │ (ждёт build-and-push)
```

> **Запомни:** `needs:` гарантирует порядок.
> Если test упал — build-and-push не запустится.
> Если build-and-push упал — deploy не запустится.

---

## 7.5 `needs:` — порядок jobs

### Параллельно (по умолчанию)

```yaml
jobs:
  test:
    ...
  build:
    ...
  deploy:
    ...
```

Все три запускаются одновременно. ❌

### Последовательно

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

test → build → deploy. ✅

### Несколько зависимостей

```yaml
jobs:
  test:
    ...
  lint:
    ...
  deploy:
    needs: [test, lint]
    ...
```

deploy ждёт И test И lint.

---

## 7.6 Передача тега образа на сервер

Сервер должен знать какой образ тянуть.

### Способ 1: .env файл на сервере

CI пишет .env на сервере:

```yaml
script: |
  cd /opt/myapp
  echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
  docker compose pull app
  docker compose up -d app
```

docker-compose.yml читает:

```yaml
services:
  app:
    image: ghcr.io/user/myapp:${IMAGE_TAG}
```

### Способ 2: Переменная окружения

```yaml
script: |
  cd /opt/myapp
  export IMAGE_TAG=${{ github.sha }}
  docker compose pull app
  docker compose up -d app
```

docker compose подхватит `IMAGE_TAG` из окружения.

---

## 7.7 Проверка деплоя

### После деплоя — проверить что работает

```yaml
script: |
  cd /opt/myapp
  echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
  docker compose pull app
  docker compose up -d app
  docker image prune -f

  # Проверка
  sleep 5
  curl -f http://localhost:8000/health || exit 1
```

`curl -f` = fail on HTTP error.
`|| exit 1` = если curl упал — весь шаг упал.

> **Совет:** Всегда проверяй health endpoint после деплоя.
> Иначе CI покажет ✅ а сервер будет 502.

---

## 📝 Упражнения

### Упражнение 7.1: Подготовка сервера
**Задача:**
1. Создай пользователя deploy: `sudo useradd -m -s /bin/bash deploy`
2. Добавь в docker: `sudo usermod -aG docker deploy`
3. Сгенерируй SSH-ключ: `ssh-keygen -t ed25519 -C "ci-deploy" -f ~/.ssh/ci_deploy -N ""`
4. Скопируй на сервер: `ssh-copy-id -i ~/.ssh/ci_deploy.pub deploy@server`
5. Проверь: `ssh -i ~/.ssh/ci_deploy deploy@server`

### Упражнение 7.2: GitHub Secrets
**Задача:**
1. Добавь `SERVER_HOST` = IP сервера
2. Добавь `SSH_PRIVATE_KEY` = содержимое `~/.ssh/ci_deploy`

### Упражнение 7.3: ssh-action
**Задача:**
1. Создай workflow с deploy job (как в 7.3)
2. Запушь в main — деплой прошёл?
3. Зайди на сервер: `ssh deploy@server`
4. Проверь: `docker compose ps` — app работает?

### Упражнение 7.4: Полный пайплайн
**Задача:**
1. Собери все jobs в один workflow (test → build → deploy)
2. Сделай commit который ломает тест — деплой не запустился?
3. Почини тест — полный пайплайн прошёл?

### Упражнение 7.5: DevOps Think
**Задача:** «Деплой прошёл (CI зелёный) но сайт не обновился. Почему?»

Подсказки:
1. Правильный ли IMAGE_TAG на сервере? (`cat .env.deploy`)
2. Тянет ли compose правильный образ? (`docker compose config`)
3. Запущен ли новый контейнер? (`docker compose ps`)
4. Health check проходит? (`curl http://localhost:8000/health`)
5. Может Nginx кеширует старый ответ?

---

## 📋 Чеклист главы 7

- [ ] Я понимаю стратегию деплоя по SSH
- [ ] Я создал пользователя deploy с правами docker
- [ ] Я сгенерировал SSH-ключ без пассфразы для CI
- [ ] Я добавил секреты SERVER_HOST и SSH_PRIVATE_KEY
- [ ] Я могу использовать appleboy/ssh-action
- [ ] Я понимаю полный пайплайн: test → build → deploy
- [ ] Я понимаю `needs:` для порядка jobs
- [ ] Я передаю IMAGE_TAG на сервер
- [ ] Я проверяю health endpoint после деплоя

**Всё отметил?** Переходи к Главе 8 — стратегии деплоя.
