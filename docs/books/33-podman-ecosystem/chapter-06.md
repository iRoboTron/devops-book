# Глава 6: Podman Compose — многоконтейнерные приложения

## Что вы узнаете

- как запустить существующий `docker-compose.yml` через Podman без изменений;
- какие директивы поддерживаются в `podman-compose`, а какие нет;
- что такое Podman Pods и чем они отличаются от Compose по архитектуре;
- с какими проблемами вы столкнётесь и как их обойти.

---

## Установка podman-compose

`podman-compose` — это Python-утилита, отдельный проект от Podman. Устанавливается независимо.

```bash
# Вариант 1: pip (самая свежая версия)
pip3 install podman-compose

# Вариант 2: пакетный менеджер (может быть устаревшая версия)
sudo apt install podman-compose    # Ubuntu/Debian
sudo dnf install podman-compose    # Fedora/RHEL

# Проверить версию (нужна 1.0+)
podman-compose --version
# podman-compose version 1.2.0
```

Если хотите алиас:
```bash
alias docker-compose='podman-compose'
echo "alias docker-compose='podman-compose'" >> ~/.bashrc
```

---

## Ваш docker-compose.yml работает без изменений

Это главное что нужно знать: `podman-compose` читает стандартный `docker-compose.yml`. Не нужно создавать отдельный файл, переписывать конфиг, менять имена сервисов.

Возьмём типичный стек: Python-приложение + PostgreSQL + Nginx.

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myapp"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://myapp:secret@db:5432/myapp
      DEBUG: "false"
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  pgdata:
```

```bash
# Запуск — идентично docker-compose
podman-compose up -d

# Статус
podman-compose ps

# Логи конкретного сервиса
podman-compose logs -f app

# Выполнить команду внутри сервиса
podman-compose exec db psql -U myapp

# Остановить без удаления данных
podman-compose stop

# Остановить и удалить (тома остаются)
podman-compose down

# Остановить и удалить всё включая тома
podman-compose down -v
```

---

## Что поддерживается, что нет

### Поддерживается

```yaml
services:
  app:
    image: myapp:latest          # ✅
    build: .                     # ✅ podman build
    build:
      context: ./app
      dockerfile: Dockerfile.prod # ✅
    ports:
      - "8080:80"                # ✅
    volumes:
      - ./data:/app/data         # ✅ bind mount
      - appdata:/app/storage     # ✅ named volume
    environment:
      KEY: value                 # ✅
    env_file: .env               # ✅
    depends_on:
      db:
        condition: service_healthy  # ✅ (podman-compose 1.0+)
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 10s              # ✅
    restart: always              # ✅
    networks:
      - backend                  # ✅
    command: ["python", "app.py"] # ✅
    entrypoint: /start.sh        # ✅
    user: "1000:1000"            # ✅
    working_dir: /app            # ✅
    labels:
      app.version: "1.0"        # ✅

networks:
  backend:
    driver: bridge               # ✅

volumes:
  appdata:                       # ✅
```

### Не поддерживается или работает частично

```yaml
services:
  app:
    deploy:                      # ❌ Swarm-директива, игнорируется
      replicas: 3
    secrets:                     # ❌ Swarm secrets, не работает
      - db_password
    configs:                     # ❌ Swarm configs
      - source: nginx_config
        target: /etc/nginx.conf

secrets:                         # ❌ Swarm secrets
  db_password:
    external: true

profiles:                        # ⚠️ может не поддерживаться в старых версиях
  - debug

extends:                         # ⚠️ частичная поддержка
  file: base.yml
  service: base
```

---

## Известные проблемы podman-compose

Честно о том с чем вы столкнётесь:

### 1. Медленнее docker-compose

`podman-compose` запускает контейнеры последовательно, вызывая `podman run` для каждого. `docker-compose` использует API и делает это параллельно. Разница заметна на стеках из 5+ сервисов.

На macOS/Windows разрыв ещё больше: сеть проксируется через Podman Machine (VM), каждый запрос проходит дополнительный слой.

### 2. depends_on с healthcheck

В старых версиях podman-compose (`< 1.0`) `depends_on: condition: service_healthy` игнорировалось — все сервисы стартовали одновременно. Приложение падало потому что БД ещё не готова.

```bash
# Проверить версию:
podman-compose --version
# Нужна 1.0+

# Если старая версия и нет возможности обновить —
# добавить retry-логику в приложение:
# while not db.is_ready(): sleep(1)
```

### 3. Сеть: broadcast и multicast не работают

В rootless-режиме Podman использует `slirp4netns` или `pasta` вместо обычного bridge. Это userspace реализация — она не поддерживает broadcast и multicast.

Если ваш сервис использует mDNS, service discovery через broadcast или multicast — в rootless это не работает. Решения:
- Использовать DNS для обнаружения сервисов
- Перейти на root Podman для этого конкретного стека
- Использовать `--network=host` (теряете изоляцию)

### 4. Порты < 1024

Та же проблема что в главе 4. Если nginx слушает 80 — нужно либо использовать 8080, либо настроить sysctl.

### 5. Volumes и SELinux

На RHEL/Fedora с SELinux — добавлять `:z` к mount:

```yaml
volumes:
  - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro,z  # ← добавить ,z
```

---

## Podman Pods — нативная группировка

Pods — нативный механизм Podman (и Kubernetes) для объединения контейнеров. Контейнеры в одном Pod разделяют:
- Сетевое пространство (один IP, видят друг друга через localhost)
- PID namespace (опционально)

Это точно такая же концепция что в Kubernetes Pod — и неслучайно: Podman Pod можно экспортировать в K8s YAML (об этом — в главе 7).

### Создать Pod вручную

```bash
# Создать pod с проброшенным портом
podman pod create --name webapp -p 8080:80 -p 5432:5432

# Запустить контейнеры в pod
podman run -d --pod webapp --name nginx-web nginx:alpine
podman run -d --pod webapp --name postgres-db \
  -e POSTGRES_PASSWORD=secret postgres:16-alpine

# Посмотреть что внутри
podman pod ps
# POD ID        NAME    STATUS    CREATED    INFRA ID      # OF CONTAINERS
# abc123...     webapp  Running   ...        def456...     3

podman ps --pod
# CONTAINER ID  NAME              STATUS   POD
# 111aaa...     webapp-infra      Running  abc123...  ← инфра-контейнер
# 222bbb...     nginx-web         Running  abc123...
# 333ccc...     postgres-db       Running  abc123...
```

Инфра-контейнер (`webapp-infra`) — специальный контейнер который держит network namespace пока Pod живёт. Он всегда есть, его не нужно трогать.

### Связь между контейнерами в Pod

Поскольку они в одном network namespace — общаются через localhost:

```bash
# Внутри nginx-web можно достучаться до postgres через localhost:
podman exec nginx-web nc -z localhost 5432 && echo "postgres доступен"

# Или из postgres к nginx:
podman exec postgres-db nc -z localhost 80 && echo "nginx доступен"
```

### Управление Pod

```bash
# Остановить весь pod (все контейнеры)
podman pod stop webapp

# Запустить
podman pod start webapp

# Перезапустить
podman pod restart webapp

# Удалить pod вместе с контейнерами
podman pod rm webapp

# Принудительно удалить запущенный pod
podman pod rm --force webapp

# Инспектировать pod
podman pod inspect webapp
```

---

## Сравнение: Compose vs Pod

Какой подход выбрать?

```text
podman-compose:
  + Привычный синтаксис из Docker
  + Один файл описывает весь стек
  + Управление как единым целым (up/down/logs)
  + Хорошо для разработки
  - Зависит от отдельного инструмента (podman-compose)
  - Ограниченная поддержка некоторых директив

Podman Pod:
  + Нативный механизм Podman
  + Экспортируется в K8s YAML напрямую
  + Более предсказуемое поведение сети (shared namespace)
  + Лучше интегрируется с systemd (Quadlet)
  - Нет файла описания стека (кроме K8s YAML)
  - Управлять несколькими контейнерами сложнее вручную
```

**Рекомендация:** для разработки и быстрого старта — `podman-compose`. Для деплоя и интеграции с systemd — Podman Pod + Quadlet (глава 9) или `podman kube play` (глава 7).

---

## Практический пример: стек с nginx.conf

Создадим полноценный пример с конфигом nginx:

```bash
# Структура проекта
mkdir -p ~/projects/myapp
cd ~/projects/myapp

# nginx.conf
cat > nginx.conf << 'EOF'
server {
    listen 80;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        return 200 "ok\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Простое приложение (имитация)
cat > app.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello from Python app!\n")

HTTPServer(("", 8000), Handler).serve_forever()
EOF

cat > Dockerfile << 'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
EOF

# docker-compose.yml уже описан выше (упрощённая версия):
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  app:
    build: .
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
    restart: unless-stopped
EOF

# Запустить
podman-compose up -d

# Проверить
curl http://localhost:8080/
# Hello from Python app!

curl http://localhost:8080/health
# ok
```

---

## Типичные ошибки

**`Error response from daemon: Conflict. The container name "..." is already in use`**
Контейнер с таким именем уже существует. Очистить:
```bash
podman-compose down
# или вручную:
podman rm -f webapp_app_1 webapp_nginx_1
```

**Сервис стартует раньше чем БД готова (depends_on не работает)**
Обновить podman-compose до версии 1.0+. Временное решение — retry в приложении.

**`Error: short-name "nginx" did not resolve`**
Добавить `docker.io` в `unqualified-search-registries` (см. глава 3).

**Тома исчезают после `podman-compose down`**
По умолчанию `down` удаляет только контейнеры и сети, тома остаются. Если тома удалились — был использован `down -v`. Это нормальное поведение по команде.

---

## Чек-лист для самопроверки

- [ ] Установил `podman-compose` версии 1.0+
- [ ] Запустил существующий `docker-compose.yml` через `podman-compose up` без изменений
- [ ] Создал Pod вручную и запустил в нём несколько контейнеров
- [ ] Понимаю разницу между `podman-compose` и `podman pod`
- [ ] Знаю какие директивы docker-compose не поддерживаются

## Попробуйте сами

1. Возьмите любой `docker-compose.yml` из своих проектов (или создайте минимальный с nginx + alpine) и запустите через `podman-compose up -d`. Что потребовало изменений?

2. Создайте Pod вручную с двумя контейнерами (nginx и любым другим) и проверьте что они видят друг друга через `localhost`:
   ```bash
   podman pod create --name test-pod -p 8080:80
   podman run -d --pod test-pod --name web nginx:alpine
   podman run -d --pod test-pod --name checker alpine sleep 300
   # Из checker достучаться до nginx:
   podman exec checker wget -qO- http://localhost:80
   podman pod rm --force test-pod
   ```

3. Сравните подход: запустите тот же стек через `podman-compose` и через Pod. Какой удобнее для разработки? Какой — для деплоя?
