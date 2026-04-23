# Playbook: Production-сервер с нуля

> Пошаговые команды. Комментарии — одна строка. Порядок важен.
> Ссылки на модули: `(М1)`, `(М2)`, и т.д.

---

## ФАЗА 0: Подготовка (локально)

```bash
# Сгенерировать SSH-ключ если нет
ssh-keygen -t ed25519 -C "deploy@myapp"

# Скопировать ключ на сервер
ssh-copy-id root@IP_СЕРВЕРА

# Проверить доступ
ssh root@IP_СЕРВЕРА
```

> ПОРЯДОК: сначала ключ → потом всё остальное

---

## ФАЗА 1: Базовая настройка сервера (~20 мин)

```bash
# Подключиться
ssh root@IP_СЕРВЕРА

# Обновить систему
apt update && apt upgrade -y

# Создать пользователя deploy
useradd -m -s /bin/bash deploy

# Скопировать SSH-ключи
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Sudo без пароля для нужных команд
echo "deploy ALL=(ALL) NOPASSWD: /bin/systemctl, /usr/bin/docker, /usr/local/bin/docker-compose, /usr/bin/docker" \
  > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy
```

> В НОВОМ терминале — проверить вход под deploy:
> `ssh deploy@IP_СЕРВЕРА`

```bash
# ufw: СНАЧАЛА разрешить SSH!
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable
ufw status verbose
```

> ПОРЯДОК: `ufw allow 22` ДО `ufw enable`

```bash
# SSH hardening (М6)
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sshd -t && systemctl reload sshd
```

### Проверка фазы 1

```bash
# Вход по паролю должен быть заблокирован
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no deploy@IP_СЕРВЕРА
# → Permission denied (publickey)

# ufw показывает только 3 порта
ufw status
# 22, 80, 443 ALLOW
```

---

## ФАЗА 2: Docker (~10 мин)

```bash
# Установить Docker (официальный скрипт, М3)
curl -fsSL https://get.docker.com | sh

# Добавить deploy в группу docker
usermod -aG docker deploy

# Проверить (в сессии deploy!)
docker run --rm hello-world
# → Hello from Docker!
```

---

## ФАЗА 3: Структура проекта (~5 мин)

```bash
# Создать директорию
mkdir -p /opt/myapp/{scripts,data,config,proxy/{data,config}}
chown -R deploy:deploy /opt/myapp

# Перейти под deploy
su - deploy
cd /opt/myapp
```

---

## ФАЗА 4: Файл переменных окружения (~5 мин)

```bash
nano /opt/myapp/.env
```

Вставь в файл и замени значения на реальные:

```env
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
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
# Закрыть от других пользователей (М5)
chmod 600 /opt/myapp/.env
```

### Проверка фазы 4

```bash
stat -c "%a" /opt/myapp/.env
# → 600
```

---

## ФАЗА 5: docker-compose.yml (~10 мин)

```bash
nano /opt/myapp/docker-compose.yml
```

Вставь в файл:

```yaml
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
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

> Замени `GITHUB_USER/REPO_NAME` на свой репозиторий

---

## ФАЗА 6: Caddy — reverse proxy + авто-SSL (~15 мин)

```bash
nano /opt/myapp/proxy/Caddyfile
```

Вставь в файл:

```caddy
domain.ru {
    reverse_proxy localhost:8000
}
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
nano /opt/myapp/proxy/docker-compose.yml
```

Вставь в файл:

```yaml
services:
  caddy:
    image: caddy:2.10-alpine
    restart: always
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data:/data
      - ./config:/config
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
# Запустить
cd /opt/myapp/proxy
docker compose up -d
```

### Проверка фазы 6

```bash
docker compose logs caddy | grep "enabled TLS"
# → msg=enabled automatic HTTPS certificate
```

> Замени `domain.ru` в Caddyfile на свой домен
> A-запись домена должна указывать на IP сервера

---

## ФАЗА 7: Первый деплой приложения (~15 мин)

```bash
# Логин в ghcr.io (создать GitHub PAT с read:packages)
echo "GITHUB_PERSONAL_ACCESS_TOKEN" | docker login ghcr.io -u GITHUB_USER --password-stdin

cd /opt/myapp

# Запустить
docker compose pull
docker compose up -d
```

### Проверка фазы 7

```bash
docker compose ps
# app и db → Up (healthy)

docker compose logs --tail=30 app

curl http://localhost:8000/health
# → {"status": "ok"}
```

---

## ФАЗА 8: Миграции БД (~5 мин)

```bash
# Alembic (SQLAlchemy / FastAPI)
docker compose exec app alembic upgrade head

# Или Django
# docker compose exec app python manage.py migrate
```

### Проверка фазы 8

```bash
docker compose exec db psql -U myapp -d myapp_prod -c "\dt"
# → список таблиц
```

---

## ФАЗА 9: Бэкапы (~20 мин)

```bash
# Установить rclone
curl https://rclone.org/install.sh | sudo bash

# Настроить Backblaze B2 (интерактивно, М5)
rclone config

# Директория бэкапов
sudo mkdir -p /var/backups/myapp
sudo chown deploy:deploy /var/backups/myapp
```

Открой скрипт бэкапа:

```bash
nano /opt/myapp/scripts/backup.sh
```

Вставь в файл:

```bash
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

if [ ! -s "${DEST}/db.sql.gz" ]; then
    echo "ERROR: Empty backup!"
    exit 1
fi

# Конфиги
cp /opt/myapp/docker-compose.yml "${DEST}/"
cp /opt/myapp/proxy/Caddyfile "${DEST}/"

# Облако
rclone copy "$DEST" "remote:myapp-backup/${DATE}/"

# Удалить старые (>7 дней)
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +

echo "[$(date)] Backup OK: ${DEST}"
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
chmod +x /opt/myapp/scripts/backup.sh

# Проверить вручную
/opt/myapp/scripts/backup.sh
```

```bash
sudo nano /etc/cron.d/myapp-backup
```

Вставь в файл:

```cron
0 3 * * * deploy /opt/myapp/scripts/backup.sh >> /var/log/myapp-backup.log 2>&1
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

### Проверка фазы 9

```bash
ls -la /var/backups/myapp/
# → директория с датой, внутри db.sql.gz

rclone ls remote:myapp-backup/
# → файл в облаке
```

---

## ФАЗА 10: fail2ban (~10 мин)

```bash
sudo apt install -y fail2ban
sudo nano /etc/fail2ban/jail.local
```

Вставь в файл:

```ini
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
sudo systemctl enable --now fail2ban
```

### Проверка фазы 10

```bash
sudo fail2ban-client status
# → Jail list: sshd, nginx-http-auth

sudo fail2ban-client status sshd
# → Currently banned: N
```

---

## ФАЗА 11: Автообновления (~5 мин)

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Проверить
sudo unattended-upgrade --dry-run
```

---

## ФАЗА 12: Netdata (~10 мин)

```bash
# Установить (М6)
wget -O /tmp/netdata.sh https://get.netdata.cloud/kickstart.sh
sh /tmp/netdata.sh --stable-channel --disable-telemetry

# Закрыть от интернета
sudo sed -i 's/.*bind to.*/    bind to = 127.0.0.1/' /etc/netdata/netdata.conf
sudo systemctl restart netdata
```

### Проверка фазы 12

```bash
systemctl status netdata
# → active (running)

# Доступ через SSH-туннель:
# ssh -L 19999:localhost:19999 deploy@IP_СЕРВЕРА
# Открыть: http://localhost:19999
```

---

## ФАЗА 13: Telegram-алерты (~20 мин)

```bash
# Конфиг с токенами
sudo nano /etc/alerting.env
```

Вставь в файл:

```env
TG_TOKEN=TELEGRAM_BOT_TOKEN
TG_CHAT_ID=TELEGRAM_CHAT_ID
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
sudo chmod 600 /etc/alerting.env
```

Открой скрипт мониторинга:

```bash
nano /opt/myapp/scripts/health-monitor.sh
```

Вставь в файл:

```bash
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
[ "$DISK" -gt 80 ] && ALERTS+=("💾 Диск: ${DISK}%")

# RAM
RAM_FREE=$(free | awk '/^Mem:/{printf "%.0f", $4/$2*100}')
[ "$RAM_FREE" -lt 10 ] && ALERTS+=("🧠 RAM: ${RAM_FREE}% свободно")

# Приложение
CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
[ "$CODE" != "200" ] && ALERTS+=("🔴 App: healthcheck ${CODE}")

# Контейнеры
STOPPED=$(docker ps -a --filter "status=exited" --format "{{.Names}}" | tr '\n' ' ')
[ -n "$STOPPED" ] && ALERTS+=("🐳 Остановлены: ${STOPPED}")

if [ ${#ALERTS[@]} -gt 0 ]; then
    MSG="<b>${HOSTNAME}</b>\n"
    for a in "${ALERTS[@]}"; do MSG+="• ${a}\n"; done
    MSG+="\n⏰ $(date '+%Y-%m-%d %H:%M')"
    send_alert "$MSG"
fi
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
chmod +x /opt/myapp/scripts/health-monitor.sh
```

Открой скрипт ежедневного отчёта:

```bash
nano /opt/myapp/scripts/daily-report.sh
```

Вставь в файл:

```bash
#!/bin/bash
source /etc/alerting.env
HOSTNAME=$(hostname)
UPTIME=$(uptime -p)
DISK=$(df / | awk 'NR==2{print $5}')
RAM=$(free -h | awk '/^Mem:/{print $3"/"$2}')
BANNED=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Banned" | awk '{print $NF}')

MSG="📊 <b>Отчёт: ${HOSTNAME}</b>\n"
MSG+="• Аптайм: ${UPTIME}\n"
MSG+="• Диск: ${DISK}\n"
MSG+="• RAM: ${RAM}\n"
MSG+="• fail2ban: ${BANNED} IP\n"
MSG+="\n⏰ $(date '+%Y-%m-%d')"

curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" -d "text=${MSG}" -d "parse_mode=HTML" > /dev/null
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
chmod +x /opt/myapp/scripts/daily-report.sh
```

Открой cron-файл:

```bash
sudo nano /etc/cron.d/myapp-monitor
```

Вставь в файл:

```cron
*/5 * * * * deploy /opt/myapp/scripts/health-monitor.sh
0 8 * * * deploy /opt/myapp/scripts/daily-report.sh
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

### Проверка фазы 13

```bash
# Запустить вручную — должно прийти сообщение в Telegram
/opt/myapp/scripts/health-monitor.sh
```

---

## ФАЗА 14: CI/CD — GitHub Actions (~30 мин)

### На сервере

```bash
# SSH-ключ для GitHub Actions
ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N ""

# Показать публичный ключ
cat ~/.ssh/github_actions.pub
```

Скопируй выведенную строку, открой `authorized_keys`:

```bash
nano ~/.ssh/authorized_keys
```

Вставь публичный ключ новой строкой, сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
# Показать приватный — скопировать в GitHub Secrets
cat ~/.ssh/github_actions
```

### В GitHub

Settings → Secrets and variables → Actions → New repository secret:

| Secret | Значение |
|--------|----------|
| `SERVER_HOST` | IP сервера |
| `SSH_PRIVATE_KEY` | Приватный ключ из `~/.ssh/github_actions` |
| `GHCR_TOKEN` | GitHub PAT (read:packages, write:packages) |

### Workflow

```bash
mkdir -p .github/workflows
nano .github/workflows/deploy.yml
```

Вставь в файл:

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
          cache-from: type=gha
          cache-to: type=gha,mode=max

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
            docker compose exec -T app alembic upgrade head || true
            docker image prune -f
```

Сохрани файл: `Ctrl+O`, `Enter`, затем выйди: `Ctrl+X`.

```bash
git add .github/workflows/deploy.yml
git commit -m "Add CI/CD pipeline"
git push
```

### Проверка фазы 14

```bash
# Открыть GitHub → Actions → наблюдать за проходом
# Или тестовый push:
git commit --allow-empty -m "test deploy"
git push
```

---

## Финальная структура файлов

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
├── cron.d/
│   ├── myapp-backup
│   └── myapp-monitor
└── fail2ban/jail.local

/var/backups/myapp/               (локальные бэкапы)
```
