# Глава 9: Итоговый проект

> **Запомни:** Эта глава — финал всего курса. Ты соберёшь полный CI/CD пайплайн самостоятельно. Как настоящий DevOps.

---

## 9.1 Цель

Настроить полный пайплайн с нуля:

```
git push → Тесты → Docker build → ghcr.io → Deploy → Health check
   │          │          │                       │
   │          ✅         ✅                      ✅ или rollback
   ▼          ▼          ▼                       ▼
 Разработчик  pytest   образ готов   сервер обновлён
```

**Требования:**
- ✅ GitHub репозиторий с защищённой веткой `main`
- ✅ Workflow `ci.yml`: тесты на каждый push/PR
- ✅ Workflow `deploy.yml`: сборка + деплой при push в `main`
- ✅ GitHub Secrets: SERVER_HOST, SSH_PRIVATE_KEY
- ✅ Сервер: пользователь deploy, SSH-ключ, docker-compose.yml
- ✅ Rollback-скрипт на сервере
- ✅ Healthcheck в docker-compose.yml
- ✅ Бейдж статуса CI в README.md

---

## 9.2 Шаг 1: GitHub репозиторий

### Структура проекта

```
myapp/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── main.py
├── requirements.txt
├── tests/
│   └── test_main.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

### Защитить ветку main

GitHub → Settings → Branches → Add rule:

```
Branch name pattern: main
✅ Require a pull request before merging
✅ Require status checks to pass
   ✅ test
✅ Require conversation resolution
```

---

## 9.3 Шаг 2: CI workflow

### .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --tb=short
```

---

## 9.4 Шаг 3: Deploy workflow

### .github/workflows/deploy.yml

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-push:
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

            # Сохранить текущий тег
            if [ -f .env.deploy ]; then
              grep IMAGE_TAG .env.deploy | cut -d= -f2 > .prev_tag
            fi

            # Деплой
            echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
            export IMAGE_TAG=${{ github.sha }}
            docker compose pull app
            docker compose up -d --no-deps app
            docker image prune -f

            # Health check
            sleep 5
            if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
              echo "❌ Health check failed! Rolling back..."

              if [ -f .prev_tag ]; then
                PREV_TAG=$(cat .prev_tag)
                echo "IMAGE_TAG=$PREV_TAG" > .env.deploy
                export IMAGE_TAG=$PREV_TAG
                docker compose pull app
                docker compose up -d --no-deps app
                echo "🔄 Rolled back to $PREV_TAG"
              fi

              exit 1
            fi

            echo "✅ Deploy successful"
```

---

## 9.5 Шаг 4: GitHub Secrets

```
SERVER_HOST     → 203.0.113.50
SSH_PRIVATE_KEY → (содержимое ci_deploy ключа)
```

---

## 9.6 Шаг 5: Сервер

### Пользователь

```bash
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
```

### SSH-ключ

```bash
# На локальной машине
ssh-copy-id -i ~/.ssh/ci_deploy.pub deploy@server
```

### Директория приложения

```bash
sudo mkdir -p /opt/myapp
sudo chown deploy:deploy /opt/myapp
```

### docker-compose.yml

```yaml
services:
  app:
    image: ghcr.io/${IMAGE_OWNER:-user}/${IMAGE_REPO:-myapp}:${IMAGE_TAG:-latest}
    environment:
      DATABASE_URL: ${DATABASE_URL}
      SECRET_KEY: ${SECRET_KEY}
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped

volumes:
  appdata:
```

> **Примечание:** Здесь `ports: 8000:8000` для простоты.
> В реальности за Nginx (Модуль 2) — порт не пробрасываешь наружу.

### .env на сервере

```bash
# /opt/myapp/.env
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
SECRET_KEY=your-secret-key
```

### Rollback-скрипт

```bash
#!/bin/bash
set -e
cd /opt/myapp

if [ ! -f .prev_tag ]; then
    echo "❌ No previous tag found"
    exit 1
fi

PREV_TAG=$(cat .prev_tag)
echo "🔄 Rolling back to $PREV_TAG"

echo "IMAGE_TAG=$PREV_TAG" > .env.deploy
export IMAGE_TAG=$PREV_TAG
docker compose pull app
docker compose up -d --no-deps app

sleep 5
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Rollback successful"
else
    echo "❌ Rollback failed!"
    exit 1
fi
```

---

## 9.7 Шаг 6: Makefile

```makefile
.PHONY: test lint build up down deploy

test:
	pytest --tb=short

lint:
	flake8 . --count --exit-zero

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

deploy:
	git push origin main
	# CI подхватит и задеплоит
```

---

## 9.8 Шаг 7: Бейдж в README

```markdown
# MyApp

[![CI](https://github.com/user/myapp/actions/workflows/ci.yml/badge.svg)](https://github.com/user/myapp/actions/workflows/ci.yml)
[![Deploy](https://github.com/user/myapp/actions/workflows/deploy.yml/badge.svg)](https://github.com/user/myapp/actions/workflows/deploy.yml)

Python application with CI/CD.
```

Результат:
```
# MyApp
[![CI] 🟢] [![Deploy] 🟢]
```

---

## 9.9 Финальный чеклист

```
□ git push в feature-ветку → запускается test job
□ Тесты проходят → ✅ в PR
□ Тесты failing → merge заблокирован
□ Merge в main → автоматически запускается deploy
□ build-and-push job → образ в ghcr.io
□ deploy job → сервер обновлён
□ curl https://server:8000/health → 200
□ Rollback работает: ./rollback.sh
□ После reboot сервера → docker compose up (restart: unless-stopped)
□ .env НЕТ в git
□ Secrets НЕ видны в логах Actions
□ Бейдж в README показывает статус
```

### Если что-то не работает

```bash
# 1. CI не запускается
#    → Проверь .github/workflows/*.yml синтаксис
#    → Проверь что файл в репозитории

# 2. Тесты failing в CI но работают локально
#    → Версия Python совпадает?
#    → Все зависимости установлены?
#    → Смотри логи: pytest --tb=short

# 3. Деплой не работает
#    → SSH ключ правильный?
#    → Пользователь deploy в группе docker?
#    → SERVER_HOST правильный?

# 4. Сайт не обновился после деплоя
#    → IMAGE_TAG правильный? (cat .env.deploy)
#    → docker compose pull скачал новый образ?
#    → docker compose ps — новый контейнер запущен?

# 5. Rollback не работает
#    → .prev_tag существует?
#    → Предыдущий образ ещё в ghcr.io?
```

---

## 9.10 Поздравляю!

Ты прошёл все 4 модуля. Вот что ты теперь умеешь:

### Модуль 1: Linux
- ✅ Уверенно работаешь в терминале
- ✅ Управляешь сервисами, правами, пользователями
- ✅ Читаешь логи, диагностируешь проблемы

### Модуль 2: Сеть
- ✅ Настраиваешь Nginx как reverse proxy
- ✅ Получаешь SSL-сертификаты
- ✅ Настраиваешь фаервол

### Модуль 3: Docker
- ✅ Пишешь Dockerfile
- ✅ Описываешь стек в docker-compose.yml
- ✅ Управляешь томами и сетями

### Модуль 4: CI/CD
- ✅ Настраиваешь GitHub Actions
- ✅ Автоматические тесты
- ✅ Сборка и публикация Docker-образа
- ✅ Автодеплой на сервер
- ✅ Rollback при проблемах

---

## 9.11 Что дальше

Ты самостоятельный DevOps. Вот направления для роста:

| Направление | Что изучить |
|------------|-------------|
| **Мониторинг** | Prometheus, Grafana, алертинг |
| **Логи** | ELK Stack, Loki, структурированные логи |
| **Инфраструктура как код** | Terraform, Ansible |
| **Оркестрация** | Kubernetes, Helm |
| **Облака** | AWS, GCP, Azure |
| **Безопасность** | Vault, SOPS, security scanning |
| **Бэкапы** | pg_dump, volume backup, disaster recovery |

---

> **Ты начал с 3 команд Linux. Теперь ты умеешь построить полный CI/CD пайплайн.**
>
> **Это уровень настоящего DevOps.**
>
> **Иди и строй.**
