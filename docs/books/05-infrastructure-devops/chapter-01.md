# Глава 1: Управление переменными окружения

> **Запомни:** Секреты разбросаны — хаос. Один `.env` файл — порядок. Кто угодно может понять как настроить приложение.

---

## 1.1 Проблема: секреты повсюду

Ты смотришь на свой сервер:

```bash
# В docker-compose.yml:
environment:
  POSTGRES_PASSWORD: mysecret123     ← пароль в коде

# В systemd unit:
Environment=SECRET_KEY=abc123        ← секрет в юните

# В скрипте backup.sh:
scp backup.tar.gz user@backup-server  ← креденшиал в скрипте
```

**Проблемы:**
- Секреты в git → вся история коммитов хранит пароли
- Секреты в разных местах → сложно обновить
- Кто угодно с доступом к репозиторию видит всё

### Решение: один `.env`

```bash
/opt/myapp/.env
POSTGRES_PASSWORD=mysecret123
SECRET_KEY=abc123
BACKUP_HOST=backup-server
```

Одно место. Легко найти. Легко обновить. Легко защитить.

---

## 1.2 Единая точка конфигурации

### `.env` файл на сервере

```bash
# /opt/myapp/.env

# База данных
POSTGRES_USER=myapp
POSTGRES_PASSWORD=x7k9mP2qR5wN
POSTGRES_DB=myapp_prod

# Приложение
SECRET_KEY=django-insecure-abc123def456
DEBUG=false
DOMAIN=myapp.ru

# Бэкапы
BACKUP_DIR=/var/backups/myapp
BACKUP_S3_BUCKET=myapp-backups
BACKUP_RETENTION_DAYS=7

# Docker
IMAGE_TAG=latest
```

### Разделённые секции

```bash
# === База данных ===
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=

# === Приложение ===
SECRET_KEY=
DEBUG=
DOMAIN=

# === Бэкапы ===
BACKUP_DIR=
BACKUP_RETENTION_DAYS=

# === Docker ===
IMAGE_TAG=
```

> **Совет:** Разделяй секции комментариями.
> Через 3 месяца ты скажешь спасибо себе настоящему.

---

## 1.3 Как `.env` подхватывается разными инструментами

### Docker Compose — автоматически

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
```

`docker compose` автоматически читает `.env` из той же директории.
Ничего дополнительного настраивать не нужно.

### systemd — через `EnvironmentFile`

```ini
# /etc/systemd/system/myapp.service
[Service]
EnvironmentFile=/opt/myapp/.env
ExecStart=/usr/bin/python3 /opt/myapp/main.py
```

Переменные из `.env` станут доступны приложению.

### Shell-скрипты — через `source`

```bash
#!/bin/bash
set -euo pipefail

source /opt/myapp/.env

echo "Backing up $POSTGRES_DB to $BACKUP_DIR"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/db.sql.gz"
```

`source` загружает все переменные из файла.

### Python-приложение — через `python-dotenv`

```python
# main.py
import os
from dotenv import load_dotenv

load_dotenv()  # Читает .env из текущей директории

secret_key = os.environ["SECRET_KEY"]
debug = os.environ.get("DEBUG", "false")
```

> **Запомни:** Один `.env` — все инструменты его читают.
> Не дублируй секреты в десяти местах.

---

## 1.4 Три уровня конфигов

```
.env.example   ← в git, шаблон без значений
.env           ← на сервере, реальные значения, НЕ в git
.env.local     ← на ноутбуке разработчика, НЕ в git
```

### `.env.example` — в git

```bash
# === База данных ===
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=

# === Приложение ===
SECRET_KEY=
DEBUG=true
DOMAIN=localhost

# === Бэкапы ===
BACKUP_DIR=/var/backups/myapp
BACKUP_RETENTION_DAYS=7

# === Docker ===
IMAGE_TAG=latest
```

Этот файл коммитится. Он показывает какие переменные нужны.

### `.env` — на сервере

```bash
POSTGRES_USER=myapp
POSTGRES_PASSWORD=x7k9mP2qR5wN
POSTGRES_DB=myapp_prod
SECRET_KEY=django-insecure-abc123def456
DEBUG=false
DOMAIN=myapp.ru
BACKUP_DIR=/var/backups/myapp
BACKUP_RETENTION_DAYS=7
IMAGE_TAG=latest
```

НЕ коммитится. Реальные значения.

### `.env.local` — на ноутбуке

```bash
POSTGRES_USER=dev
POSTGRES_PASSWORD=dev
POSTGRES_DB=dev_db
SECRET_KEY=dev-secret
DEBUG=true
DOMAIN=localhost
BACKUP_DIR=/tmp/backups
BACKUP_RETENTION_DAYS=3
IMAGE_TAG=dev
```

НЕ коммитится. Локальные значения для разработки.

---

## 1.5 Права на `.env`

```bash
chmod 600 /opt/myapp/.env
chown deploy:deploy /opt/myapp/.env
```

`600` = только владелец читает и пишет.

### Что будет если `644`

```bash
# .env имеет права 644 (чтение всем)
ls -la /opt/myapp/.env
-rw-r--r-- 1 deploy deploy 350 Apr 11 10:00 .env

# Любой пользователь на сервере может прочитать:
cat /opt/myapp/.env
POSTGRES_PASSWORD=x7k9mP2qR5wN
SECRET_KEY=django-insecure-abc123def456
```

> **Опасно:** `chmod 644 .env` = пароли для всех пользователей сервера.
> Всегда `chmod 600`.

### Проверка

```bash
stat -c "%a %U:%G" /opt/myapp/.env
600 deploy:deploy
```

---

## 1.6 Проверка через `docker-compose config`

```bash
cd /opt/myapp
docker compose config
```

Показывает финальный конфиг с подставленными переменными:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: myapp
      POSTGRES_PASSWORD: x7k9mP2qR5wN
      POSTGRES_DB: myapp_prod
```

> **Опасно:** `docker compose config` показывает секреты!
> Не копи вывод если в нём есть пароли.
> Используй `--no-normalize` чтобы скрыть значения.

---

## 1.7 `envsubst` — подставить переменные в шаблон

Иногда нужен конфиг с переменными. Например Nginx:

```nginx
# nginx/conf.d/app.conf.template
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://app:8000;
    }
}
```

Подставить:

```bash
source /opt/myapp/.env
envsubst '${DOMAIN}' < app.conf.template > app.conf
```

Результат:

```nginx
server {
    listen 80;
    server_name myapp.ru;
    ...
}
```

> **Совет:** `envsubst` удобен когда один шаблон конфига
> используется на разных серверах с разными доменами.

---

## 📝 Упражнения

### Упражнение 1.1: Создать .env
**Задача:**
1. Создай `/opt/myapp/.env` со всеми переменными
2. Создай `/opt/myapp/.env.example` (пустой шаблон)
3. Добавь `.env` в `.gitignore`
4. Проверь: `git status` — `.env` не tracked?

### Упражнение 1.2: Права
**Задача:**
1. Проверь текущие права: `ls -la /opt/myapp/.env`
2. Исправь если нужно: `chmod 600 /opt/myapp/.env`
3. Проверь владельца: `chown deploy:deploy /opt/myapp/.env`
4. Проверь: `stat -c "%a %U:%G" /opt/myapp/.env`

### Упражнение 1.3: Docker Compose
**Задача:**
1. Замени хардкод в docker-compose.yml на `${VAR}`
2. Проверь: `docker compose config` — переменные подставились?
3. Проверь без нормализации: `docker compose config --no-normalize`

### Упражнение 1.4: Скрипт с source
**Задача:**
1. Создай скрипт который читает `.env`:
   ```bash
   #!/bin/bash
   source /opt/myapp/.env
   echo "DB: $POSTGRES_DB"
   echo "Domain: $DOMAIN"
   ```
2. Запусти — переменные видны?

### Упражнение 1.5: DevOps Think
**Задача:** «Ты нашёл `.env` с правами `644` на продакшн сервере. Что делаешь?»

Ответ:
1. Немедленно: `chmod 600 /opt/myapp/.env`
2. Проверь кто читал файл: `last`, `auditd` логи
3. Поменяй ВСЕ пароли в `.env` (считай скомпрометированными)
4. Обнови секреты в GitHub Actions
5. Проверь git — не был ли `.env` закоммичен
6. Добавь проверку прав в health-check скрипт

---

## 📋 Чеклист главы 1

- [ ] Все переменные собраны в один `.env`
- [ ] `.env` имеет права `600` и правильного владельца
- [ ] `.env.example` в git (шаблон без значений)
- [ ] `.env` в `.gitignore`
- [ ] `docker-compose.yml` использует `${VAR}` а не хардкод
- [ ] `docker compose config` показывает правильный конфиг
- [ ] Скрипты используют `source .env` вместо хардкода
- [ ] Я понимаю три уровня конфигов (example / server / local)

**Всё отметил?** Переходи к Главе 2 — продвинутый Nginx.
