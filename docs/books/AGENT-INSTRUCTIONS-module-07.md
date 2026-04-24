# Инструкция для ИИ-агента: Написание финального проекта

> **Это Модуль 7 курса DevOps — финальный проект.**
> Предполагается что все Модули 1–6 пройдены.
> Этот модуль — не учебник. Это рабочий инструмент.

---

## Контекст

Ученик прошёл весь курс. Он знает теорию и практику каждого модуля.
Теперь ему нужен документ который позволяет поднять полный production-стек
на новом сервере — без возврата к шести книгам.

**Главный принцип этого модуля:**
Никакой теории. Никаких объяснений "что такое Docker" или "зачем нужен fail2ban".
Только: что делать, в каком порядке, как проверить что сделано правильно.

---

## Что за модуль

**Название:** "Финальный проект: Production-сервер с нуля"

**Состоит из двух документов:**

```
07-final-project/
├── book.md        — обзор: архитектура, как пользоваться playbook'ом
├── playbook.md    — пошаговые команды от чистого сервера до продакшна
└── checklist.md   — финальная проверка: 30 пунктов
```

**Объём:**
- `book.md` — 1–2 страницы
- `playbook.md` — 15–20 страниц
- `checklist.md` — 1–2 страницы

---

## Финальная архитектура

Это то что будет на сервере после прохождения playbook'а.
Схема должна быть в `book.md` — читатель видит куда идёт до начала работы.

```
GitHub
  │  git push → main
  ▼
GitHub Actions
  │  1. pytest
  │  2. docker build → ghcr.io/user/myapp:SHA
  │  3. SSH → сервер → docker compose pull → up -d
  ▼
Сервер Ubuntu
  │
  ├── [Caddy :80/:443]  ← Caddyfile (автоматический SSL)
  │       │ reverse_proxy
  │       ▼
  ├── [Python-app :8000]  ← Docker контейнер
  │       │ DATABASE_URL
  │       ▼
  ├── [PostgreSQL :5432]  ← Docker контейнер, том pgdata
  │
  ├── Безопасность:
  │   ├── ufw: открыты 22/80/443
  │   ├── fail2ban: блокировка брутфорса SSH + Nginx
  │   └── SSH: только ключи, PasswordAuthentication no
  │
  ├── Бэкапы:
  │   ├── cron 03:00 → backup.sh → /var/backups/
  │   └── rclone → Backblaze B2
  │
  └── Мониторинг:
      ├── Netdata → http://localhost:19999 (SSH-туннель)
      └── Telegram-алерты: диск/RAM/app/контейнеры
```

---

## Структура `playbook.md`

### Формат каждого шага

```bash
# Однострочный комментарий — зачем эта команда
команда
```

Не больше. Если нужно несколько слов — ок. Если хочется объяснить подробно — стоп, это не этот документ.

**Пример хорошего шага:**
```bash
# Запретить вход по паролю — только SSH-ключи
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl reload sshd
```

**Пример плохого шага:**
```bash
# SSH-ключи — более безопасный способ аутентификации чем пароли.
# Когда злоумышленник пытается перебрать пароль брутфорсом, ключи
# делают это практически невозможным потому что...
```

### Фазы playbook'а

---

#### ФАЗА 0: Подготовка (до сервера)

Что нужно иметь до начала:
- Доступ к серверу (IP, root-пароль)
- Зарегистрированный домен с A-записью на IP сервера
- GitHub-репозиторий с приложением
- Telegram-бот (токен + chat_id)
- Backblaze B2 bucket (или другое S3-хранилище)

Локально на своей машине:
```bash
# Сгенерировать SSH-ключ если нет
ssh-keygen -t ed25519 -C "deploy@myapp"

# Скопировать ключ на сервер
ssh-copy-id root@IP_СЕРВЕРА
```

---

#### ФАЗА 1: Базовая настройка сервера (~20 мин)

```bash
# Подключиться
ssh root@IP_СЕРВЕРА

# Обновить систему
apt update && apt upgrade -y

# Создать пользователя deploy
useradd -m -s /bin/bash deploy
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Дать sudo без пароля для deploy (только нужные команды)
echo "deploy ALL=(ALL) NOPASSWD: /bin/systemctl, /usr/bin/docker, /usr/local/bin/docker-compose" \
  >> /etc/sudoers.d/deploy

# Проверить вход под deploy (в новом терминале!)
# ssh deploy@IP_СЕРВЕРА

# ufw: базовая настройка (СНАЧАЛА allow 22!)
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable
ufw status verbose

# SSH hardening
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sshd -t && systemctl reload sshd
```

> **Порядок важен в этой фазе:**
> 1. Скопировать ключ → 2. Проверить вход по ключу → 3. Отключить пароли

---

#### ФАЗА 2: Docker (~10 мин)

```bash
# Установить Docker (официальный способ)
curl -fsSL https://get.docker.com | sh

# Добавить deploy в группу docker
usermod -aG docker deploy

# Проверить
docker run --rm hello-world
```

---

#### ФАЗА 3: Структура проекта (~10 мин)

```bash
# Создать директорию проекта
mkdir -p /opt/myapp/{scripts,data,config}
chown -R deploy:deploy /opt/myapp

# Перейти под deploy
su - deploy
cd /opt/myapp
```

---

#### ФАЗА 4: Файл переменных окружения (~10 мин)

```bash
# Создать .env (заполнить реальными значениями)
cat > /opt/myapp/.env << 'EOF'
POSTGRES_USER=myapp
POSTGRES_PASSWORD=ЗАМЕНИ_НА_СВОЙ_ПАРОЛЬ
POSTGRES_DB=myapp_prod
DATABASE_URL=postgresql://myapp:ЗАМЕНИ_НА_СВОЙ_ПАРОЛЬ@db:5432/myapp_prod
SECRET_KEY=ЗАМЕНИ_НА_СЛУЧАЙНЫЙ_КЛЮЧ
DOMAIN=domain.ru
BACKUP_DIR=/var/backups/myapp
TG_TOKEN=TELEGRAM_BOT_TOKEN
TG_CHAT_ID=TELEGRAM_CHAT_ID
IMAGE_TAG=latest
EOF

# Закрыть от других пользователей
chmod 600 /opt/myapp/.env
```

---

#### ФАЗА 5: docker-compose.yml (~15 мин)

```bash
cat > /opt/myapp/docker-compose.yml << 'EOF'
services:
  app:
    image: ghcr.io/GITHUB_USER/REPO_NAME:${IMAGE_TAG}
    restart: unless-stopped
    env_file: .env
    networks:
      - backend
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:

networks:
  backend:
EOF
```

---

#### ФАЗА 6: Caddy (~15 мин)

```bash
mkdir -p /opt/myapp/proxy/{data,config}

cat > /opt/myapp/proxy/Caddyfile << 'EOF'
domain.ru {
    reverse_proxy localhost:8000
}
EOF

cat > /opt/myapp/proxy/docker-compose.yml << 'EOF'
services:
  caddy:
    image: caddy:2.10-alpine
    restart: always
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data:/data
      - ./config:/config
EOF

cd /opt/myapp/proxy
docker compose up -d
docker compose logs caddy
```

---

#### ФАЗА 7: Первый деплой приложения (~15 мин)

```bash
# Залогиниться в ghcr.io (нужен GitHub Personal Access Token)
echo "GITHUB_TOKEN" | docker login ghcr.io -u GITHUB_USER --password-stdin

cd /opt/myapp

# Подтянуть образ и запустить
docker compose pull
docker compose up -d

# Проверить
docker compose ps
docker compose logs --tail=30 app
curl http://localhost:8000/health
```

---

#### ФАЗА 8: Миграции БД (~5 мин)

```bash
# Запустить миграции (если используется Alembic)
docker compose exec app alembic upgrade head

# Или Django
docker compose exec app python manage.py migrate
```

---

#### ФАЗА 9: Бэкапы (~20 мин)

```bash
# Установить rclone
curl https://rclone.org/install.sh | sudo bash

# Настроить Backblaze B2 (интерактивно)
rclone config

# Создать директорию бэкапов
sudo mkdir -p /var/backups/myapp
sudo chown deploy:deploy /var/backups/myapp

# Создать скрипт бэкапа
cat > /opt/myapp/scripts/backup.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

source /opt/myapp/.env
DATE=$(date +%Y-%m-%d)
DEST="${BACKUP_DIR}/${DATE}"
mkdir -p "$DEST"

# База данных
docker compose -f /opt/myapp/docker-compose.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "${DEST}/db.sql.gz"

# Конфиги (без секретов)
cp /opt/myapp/docker-compose.yml "${DEST}/"
cp /opt/myapp/proxy/Caddyfile "${DEST}/"

# Загрузить в облако
rclone copy "$DEST" "remote:myapp-backup/${DATE}"

# Удалить локальные старше 7 дней
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +

echo "[$(date)] Backup OK: ${DEST}"
SCRIPT

chmod +x /opt/myapp/scripts/backup.sh

# Проверить вручную
/opt/myapp/scripts/backup.sh

# Добавить в cron (03:00 каждую ночь)
echo "0 3 * * * deploy /opt/myapp/scripts/backup.sh >> /var/log/myapp-backup.log 2>&1" \
  | sudo tee /etc/cron.d/myapp-backup
```

---

#### ФАЗА 10: fail2ban (~15 мин)

```bash
sudo apt install -y fail2ban

sudo cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF

sudo systemctl enable --now fail2ban
sudo fail2ban-client status
```

---

#### ФАЗА 11: Автообновления (~5 мин)

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Проверить
sudo unattended-upgrade --dry-run
```

---

#### ФАЗА 12: Мониторинг — Netdata (~10 мин)

```bash
# Установить
wget -O /tmp/netdata.sh https://get.netdata.cloud/kickstart.sh
sh /tmp/netdata.sh --stable-channel --disable-telemetry

# Закрыть от интернета (только localhost)
sudo sed -i 's/.*bind to.*/    bind to = 127.0.0.1/' /etc/netdata/netdata.conf
sudo systemctl restart netdata

# Доступ: ssh -L 19999:localhost:19999 deploy@IP_СЕРВЕРА
# Открыть: http://localhost:19999
```

---

#### ФАЗА 13: Telegram-алерты (~20 мин)

```bash
# Создать конфиг алертов
sudo cat > /etc/alerting.env << 'EOF'
TG_TOKEN=TELEGRAM_BOT_TOKEN
TG_CHAT_ID=TELEGRAM_CHAT_ID
EOF
sudo chmod 600 /etc/alerting.env

# Создать скрипт мониторинга
cat > /opt/myapp/scripts/health-monitor.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

source /etc/alerting.env
source /opt/myapp/.env

HOSTNAME=$(hostname)
ALERTS=()

send_alert() {
    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      -d "chat_id=${TG_CHAT_ID}" -d "text=$1" -d "parse_mode=HTML" > /dev/null
}

# Диск
DISK=$(df / | awk 'NR==2{print $5}' | tr -d '%')
[ "$DISK" -gt 80 ] && ALERTS+=("Диск: ${DISK}%")

# RAM
RAM_FREE=$(free | awk '/^Mem:/{printf "%.0f", $4/$2*100}')
[ "$RAM_FREE" -lt 10 ] && ALERTS+=("RAM свободно: ${RAM_FREE}%")

# Приложение
CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
[ "$CODE" != "200" ] && ALERTS+=("App healthcheck: ${CODE}")

# Остановленные контейнеры
STOPPED=$(docker ps -a --filter "status=exited" --format "{{.Names}}" | tr '\n' ' ')
[ -n "$STOPPED" ] && ALERTS+=("Остановлены: ${STOPPED}")

if [ ${#ALERTS[@]} -gt 0 ]; then
    MSG="<b>${HOSTNAME}</b>%0A"
    for a in "${ALERTS[@]}"; do MSG+="• ${a}%0A"; done
    send_alert "$MSG"
fi
SCRIPT

chmod +x /opt/myapp/scripts/health-monitor.sh

# Добавить в cron (каждые 5 минут)
echo "*/5 * * * * deploy /opt/myapp/scripts/health-monitor.sh" \
  | sudo tee -a /etc/cron.d/myapp-backup

# Ежедневный отчёт (08:00)
cat > /opt/myapp/scripts/daily-report.sh << 'SCRIPT'
#!/bin/bash
source /etc/alerting.env

HOSTNAME=$(hostname)
UPTIME=$(uptime -p)
DISK=$(df / | awk 'NR==2{print $5}')
RAM=$(free -h | awk '/^Mem:/{print $3"/"$2}')
CONTAINERS=$(docker ps --format "{{.Names}}" | tr '\n' ' ')
BANNED=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Banned IP" | awk '{print $NF}')

MSG="<b>Отчёт: ${HOSTNAME}</b>%0A"
MSG+="Аптайм: ${UPTIME}%0A"
MSG+="Диск: ${DISK}%0A"
MSG+="RAM: ${RAM}%0A"
MSG+="Контейнеры: ${CONTAINERS}%0A"
MSG+="Заблокировано fail2ban: ${BANNED}"

curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" -d "text=${MSG}" -d "parse_mode=HTML" > /dev/null
SCRIPT

chmod +x /opt/myapp/scripts/daily-report.sh
echo "0 8 * * * deploy /opt/myapp/scripts/daily-report.sh" \
  | sudo tee -a /etc/cron.d/myapp-backup
```

---

#### ФАЗА 14: CI/CD — GitHub Actions (~30 мин)

На сервере:
```bash
# Создать SSH-ключ для деплоя из GitHub Actions
ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N ""

# Добавить публичный ключ в authorized_keys
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# Показать приватный ключ — скопировать в GitHub Secrets
cat ~/.ssh/github_actions
```

В репозитории GitHub → Settings → Secrets добавить:
- `SERVER_HOST` — IP сервера
- `SSH_PRIVATE_KEY` — приватный ключ (весь, включая BEGIN/END)
- `GHCR_TOKEN` — GitHub Personal Access Token (read:packages, write:packages)

Создать `.github/workflows/deploy.yml`:
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
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GHCR_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: deploy
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/myapp
            sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=${{ github.sha }}/" .env
            docker compose pull app
            docker compose up -d --no-deps app
            docker compose exec -T app alembic upgrade head
            docker image prune -f
```

Проверить:
```bash
# Запушить что-нибудь и наблюдать в GitHub Actions
git commit --allow-empty -m "test deploy"
git push
```

---

### Финальная структура файлов на сервере

После прохождения всех фаз должно быть:

```
/opt/myapp/
├── .env                          (chmod 600)
├── docker-compose.yml
├── scripts/
│   ├── backup.sh
│   ├── health-monitor.sh
│   └── daily-report.sh
└── proxy/
    ├── Caddyfile
    ├── docker-compose.yml
    ├── data/                     (сертификаты Caddy)
    └── config/

/etc/
├── alerting.env                  (chmod 600)
├── cron.d/myapp-backup
└── fail2ban/jail.local

/var/backups/myapp/               (бэкапы)
/var/log/myapp-backup.log         (лог бэкапов)
```

---

## Структура `checklist.md`

30 пунктов, разбитых по секциям. Каждый пункт — команда проверки + ожидаемый результат.

### Формат:

```markdown
**ПРИЛОЖЕНИЕ**
- [ ] `curl https://domain.ru` → 200 OK
- [ ] `curl http://domain.ru` → 301 redirect
      ...

**CI/CD**
- [ ] Пустой коммит → деплой прошёл автоматически
      ...
```

### Секции checklist'а:

1. **Приложение** (5 пунктов) — доступность, healthcheck, редирект
2. **CI/CD** (4 пункта) — автодеплой, провал теста блокирует деплой
3. **Безопасность** (6 пунктов) — SSH, ufw, fail2ban
4. **Бэкапы** (4 пункта) — скрипт работает, файл в облаке
5. **Мониторинг** (5 пунктов) — алерты приходят, Netdata доступен
6. **Стабильность** (6 пунктов) — reboot, restart контейнера, диск не растёт

---

## Принципы написания

### 1. Никакой теории
Если хочется объяснить — не объяснять. Ссылаться на модуль:
```
# (подробнее: Модуль 2, Глава 6)
```

### 2. Комментарий = одна строка
```bash
# Хорошо:
# Запретить вход под root
sudo sed -i ...

# Плохо:
# Вход под root опасен потому что если злоумышленник...
```

### 3. Каждая фаза — проверяемый результат
В конце каждой фазы — 1-2 команды которые подтверждают что фаза прошла успешно:
```bash
# Проверить фазу 2 (Docker)
docker run --rm hello-world  # должно напечатать "Hello from Docker!"
```

### 4. Порядок важен — предупреждать явно
Где нарушение порядка ломает сервер — выделять:
```
> ПОРЯДОК: сначала `ufw allow 22`, потом `ufw enable`
> ПОРЯДОК: сначала проверить вход по ключу, потом отключить пароли
```

### 5. Заменяемые значения — заглавными
```bash
ssh root@IP_СЕРВЕРА
ghcr.io/GITHUB_USER/REPO_NAME:latest
```
Читатель видит что нужно заменить.

### 6. `checklist.md` — только проверки, никаких команд настройки
Если пункт не прошёл — читатель идёт в нужный модуль, не чинит здесь.

---

## Что НЕ надо делать

- ❌ Не объяснять зачем каждая команда (это сделано в модулях 1–6)
- ❌ Не давать альтернативные варианты ("или можно так, или вот так")
- ❌ Не добавлять опциональные шаги без явной пометки `(опционально)`
- ❌ Не отступать от линейного порядка — документ читается сверху вниз
- ❌ Не дублировать `checklist.md` в `playbook.md` — это разные документы
- ❌ Не писать `book.md` длиннее 2 страниц

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-07.md   # Этот файл
└── 07-final-project/                    # Модуль 7 (создать)
    ├── book.md                       # Обзор + архитектурная схема
    ├── playbook.md                   # Пошаговый playbook
    └── checklist.md                  # Финальная проверка
```

---

## Связь с курсом

Каждая фаза явно ссылается на модуль:

| Фаза | Модуль |
|------|--------|
| 0–1: Сервер, SSH, ufw | М1, М2 |
| 2: Docker | М3 |
| 3–5: Приложение, .env, compose | М3, М5 |
| 6: Caddy | М2 |
| 7–8: Деплой, миграции | М3, М5 |
| 9: Бэкапы | М5 |
| 10–11: fail2ban, автообновления | М6 |
| 12–13: Netdata, Telegram | М6 |
| 14: CI/CD | М4 |

---

## Итог

После прохождения `playbook.md` и прохождения `checklist.md`:

```
✅ Python-приложение доступно по HTTPS
✅ git push → автоматический деплой
✅ PostgreSQL с ежедневными бэкапами в облако
✅ SSH: только ключи, brute-force заблокирован
✅ Telegram-алерты при падении сервисов
✅ Netdata-дашборд доступен через SSH-туннель
```

Это финал курса. Читатель умеет всё что было заявлено в README.

---

*Эта инструкция — для ИИ-агента, который будет писать финальный модуль курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Все предыдущие модули: /home/adelfos/Documents/lessons/dev-ops/docs/books/*
