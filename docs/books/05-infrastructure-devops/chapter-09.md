# Глава 9: Итоговый проект

> **Запомни:** Это финал книги. Приведи сервер из предыдущих модулей к production-ready состоянию. Без халтуры.

---

## 9.1 Цель

Настроить production-ready сервер:

```
/opt/myapp/
├── docker-compose.yml          ← с лимитами, healthcheck, restart policy
├── .env                        ← chmod 600, в gitignore
├── .env.example                ← шаблон в git
├── nginx/
│   ├── conf.d/app.conf         ← security headers, rate limiting
│   └── snippets/
│       ├── ssl.conf
│       └── security-headers.conf
├── scripts/
│   ├── backup.sh               ← бэкап БД + файлов
│   ├── restore.sh              ← восстановление
│   └── health-check.sh         ← проверка стека
└── alembic/                    ← миграции
    └── versions/

/etc/cron.d/
├── myapp-backup                ← ежедневный бэкап 3:00
└── docker-prune                ← еженедельная чистка

/var/backups/myapp/             ← локальные бэкапы (7 дней)
```

---

## Стартовая точка

Тип проекта: **продолжение итогового проекта книги 4**.

Это не чистая VM. В этой главе ты доводишь уже работающий Docker/CI/CD-сервер до production-ready состояния: переменные окружения, база данных, Nginx-настройки, бэкапы, восстановление, лимиты и health-check.

До начала должно быть:
- сервер из итогового проекта книги 4;
- пользователь `deploy`;
- каталог `/opt/myapp`;
- `docker-compose.yml`, `.env`, `.env.example` и `.gitignore`;
- Docker Compose поднимает приложение и PostgreSQL;
- GitHub Actions уже умеет собрать образ и обновить контейнер на сервере;
- `curl http://localhost/health` или внешний URL приложения отвечает успешно.

Если у тебя чистая VM, сначала пройди итоговые проекты книг 3 и 4. Эта глава не устанавливает приложение с нуля, а укрепляет и стандартизирует уже работающий стек.

Быстрая проверка входного состояния:

```bash
id deploy
ls -la /opt/myapp
test -f /opt/myapp/docker-compose.yml
test -f /opt/myapp/.env
cd /opt/myapp && docker compose ps
```

---

## 9.2 Шаг 1: Конфигурация

### `.env` с правами 600

```bash
chmod 600 /opt/myapp/.env
chown deploy:deploy /opt/myapp/.env
```

### `.env.example` в git

```bash
cp /opt/myapp/.env /opt/myapp/.env.example
# Удалить реальные значения
nano /opt/myapp/.env.example
git add .env.example && git commit -m "Add .env.example"
```

### `.gitignore`

```
.env
.env.local
```

---

## 9.3 Шаг 2: PostgreSQL

### Отдельный пользователь

```sql
CREATE USER myapp WITH PASSWORD 'x7k9mP2qR5wN';
CREATE DATABASE myapp_prod OWNER myapp;
GRANT ALL PRIVILEGES ON DATABASE myapp_prod TO myapp;
```

### Параметры

```yaml
command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c max_connections=100
```

### Порт не проброшен

```yaml
# ports: "5432:5432"  ← УБРАТЬ
```

---

## 9.4 Шаг 3: Nginx

### Заголовки безопасности

```nginx
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### Rate limiting

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

### Gzip

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

---

## 9.5 Шаг 4: docker-compose.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - frontend
      - backend

  app:
    build: .
    environment:
      DATABASE_URL: ${DATABASE_URL}
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512m
          cpus: '0.5'
    networks:
      - backend

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    command: >
      postgres
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c max_connections=100
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1g
          cpus: '1.0'
    networks:
      - backend

volumes:
  pgdata:

networks:
  frontend:
  backend:
```

---

## 9.6 Шаг 5: Бэкапы

### backup.sh

Создай `/opt/myapp/scripts/backup.sh` (как в Главе 6).

### restore.sh

Создай `/opt/myapp/scripts/restore.sh` (как в Главе 7).

### cron

```bash
# /etc/cron.d/myapp-backup
0 3 * * * deploy /opt/myapp/scripts/backup.sh >> /var/log/myapp-backup.log 2>&1
```

---

## 9.7 Шаг 6: Docker daemon.json

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
```

```bash
sudo systemctl restart docker
```

### Docker prune cron

```bash
# /etc/cron.d/docker-prune
0 4 * * 0 root docker system prune -f >> /var/log/docker-prune.log 2>&1
```

---

## 9.8 Шаг 7: Миграции

### Alembic настроена

```bash
cd /opt/myapp
alembic init alembic
```

### В CI/CD — миграция перед деплоем

```yaml
script: |
  cd /opt/myapp
  docker compose run --rm app alembic upgrade head
  docker compose pull app
  docker compose up -d --no-deps app
```

---

## 9.9 Шаг 8: health-check.sh

Создай `/opt/myapp/scripts/health-check.sh`:

```bash
#!/bin/bash
set -euo pipefail

ERRORS=0

# Проверить контейнеры
if ! docker compose ps | grep -q "Up"; then
    echo "❌ Container not running"
    ERRORS=$((ERRORS + 1))
fi

# Проверить healthcheck БД
DB_STATUS=$(docker inspect --format='{{.State.Health.Status}}' myapp-db-1 2>/dev/null || echo "unknown")
if [ "$DB_STATUS" != "healthy" ]; then
    echo "❌ Database not healthy: $DB_STATUS"
    ERRORS=$((ERRORS + 1))
fi

# Проверить приложение
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ App health check failed: $HTTP_CODE"
    ERRORS=$((ERRORS + 1))
fi

# Проверить диск
DISK_USE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USE" -gt 85 ]; then
    echo "❌ Disk usage: ${DISK_USE}%"
    ERRORS=$((ERRORS + 1))
fi

# Проверить .env права
ENV_PERMS=$(stat -c "%a" /opt/myapp/.env 2>/dev/null || echo "000")
if [ "$ENV_PERMS" != "600" ]; then
    echo "❌ .env permissions: $ENV_PERMS (should be 600)"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed"
else
    echo "⚠️ $ERRORS check(s) failed"
    exit 1
fi
```

```bash
chmod +x /opt/myapp/scripts/health-check.sh
```

### Запускать по cron

```bash
# /etc/cron.d/myapp-health
*/15 * * * * deploy /opt/myapp/scripts/health-check.sh >> /var/log/myapp-health.log 2>&1
```

Каждые 15 минут.

---

## 9.10 Финальный чеклист

```
□ .env с правами 600 и правильным владельцем
□ .env.example в git (шаблон без значений)
□ PostgreSQL от отдельного пользователя (не postgres суперпользователь)
□ Порт 5432 НЕ проброшен наружу
□ Параметры PostgreSQL настроены (shared_buffers, max_connections)
□ Nginx заголовки безопасности добавлены
□ Rate limiting настроен
□ Gzip включен
□ docker-compose.yml: restart: unless-stopped для всех сервисов
□ docker-compose.yml: healthcheck для БД
□ docker-compose.yml: лимиты памяти для контейнеров
□ Миграции Alembic настроены
□ backup.sh работает вручную
□ restore.sh проверен на тестовой машине
□ Cron для бэкапов (ежедневно 3:00)
□ Docker daemon.json настроен (ротация логов)
□ Cron для docker-prune (еженедельно)
□ health-check.sh создан и запущен по cron
□ df -h: диск < 70%
□ nc -zv localhost 5432: соединение отклонено (порт закрыт снаружи)
□ docker compose ps: все сервисы Up (healthy)
```

---

## 9.11 Сохранение VM для книги 6

После финального чеклиста сделай снапшот VM. Это входная точка для книги 6: в следующей книге ты будешь проводить аудит, hardening, мониторинг и runbook уже на этом production-ready сервере.

Перед снапшотом проверь:

```bash
cd /opt/myapp
docker compose ps
/opt/myapp/scripts/health-check.sh
ls -lah /var/backups/myapp
sudo systemctl status cron
```

Сохрани VM с понятным именем, например:

```text
after-book-5-infra-myapp
```

В снапшоте уже должны быть:

- рабочий Docker Compose стек в `/opt/myapp`;
- CI/CD из книги 4;
- `.env` с правами `600`;
- PostgreSQL с закрытым внешним портом;
- backup/restore-скрипты;
- cron для бэкапов и health-check;
- проверенный restore на тестовой машине.

Если в книге 6 ты ошибёшься с SSH hardening, fail2ban, ufw или алертами, откат к этому снапшоту вернёт сервер к рабочему состоянию после инфраструктурной настройки.

---

## 9.12 Поздравляю!

Ты прошёл 5 модулей из 6. Вот что ты теперь умеешь:

| Модуль | Навык |
|--------|-------|
| 1. Linux | Терминал, сервисы, права, логи |
| 2. Сеть | Nginx, HTTPS, ufw, DNS |
| 3. Docker | Образы, Compose, volumes, сети |
| 4. CI/CD | GitHub Actions, автодеплой, rollback |
| 5. Инфраструктура | Бэкапы, миграции, надёжность |

**Остался Модуль 6: Безопасность и мониторинг.**

---

> **Твой сервер — production-ready.**
> Данные защищены. Сервис восстанавливается. Ресурсы контролируются.
> Это уровень настоящего DevOps.
