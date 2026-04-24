# Приложение C: Диагностика

> Когда что-то не работает — ищи здесь.

---

## C.1 Контейнер не стартует

### Симптом

```bash
docker compose ps
NAME    STATUS
app     Exited (1)
```

### Диагностика

```bash
# 1. Логи контейнера
docker logs app
# или
docker compose logs app

# 2. Подробная информация
docker inspect app

# 3. Попробуй запустить вручную
docker run --rm myapp python main.py
```

### Частые причины

| Причина | Решение |
|---------|---------|
| Ошибка в коде Python | Смотри traceback в логах |
| Не найдена зависимость | Проверь requirements.txt |
| Переменная окружения не задана | Проверь `.env` и `docker compose config` |
| Порт уже занят | `ss -tlnp | grep 8000` |

---

## C.2 Не могу достучаться до базы данных

### Симптом

```
psycopg2.OperationalError: could not connect to server: Connection refused
```

### Диагностика

```bash
# 1. Запущена ли БД?
docker compose ps db

# 2. Healthcheck прошёл?
docker compose ps
# db должен быть (healthy)

# 3. Логи БД
docker compose logs db

# 4. Проверить сеть
docker network inspect myproject_backend

# 5. Попробовать пинговать из app
docker compose exec app ping db

# 6. Проверить DATABASE_URL
docker compose exec app printenv DATABASE_URL
```

### Частые причины

| Причина | Решение |
|---------|---------|
| БД ещё не запустилась | Проверь healthcheck, подожди |
| Неправильное имя хоста | Должно быть `db` (имя сервиса), не `localhost` |
| Неправильный пароль | Проверь `.env` |
| app и db в разных сетях | Проверь `networks` в compose |
| Порт проброшен наружу но не внутри | Не нужен `-p` для внутренних сервисов |

---

## C.3 Образ слишком большой

### Симптом

```bash
docker images
REPOSITORY   TAG   SIZE
myapp        1.0   1.2GB    ← слишком!
```

### Диагностика

```bash
docker history myapp:1.0
```

Покажет какой слой самый большой.

### Решение

| Проблема | Решение |
|----------|---------|
| `FROM python:3.12` (полный) | `FROM python:3.12-slim` |
| `apt install` без `--no-install-recommends` | `apt install --no-install-recommends -y` |
| Кэш pip в образе | `pip install --no-cache-dir` |
| Копируются ненужные файлы | `.dockerignore` |
| Сборка и рантайм в одном образе | Multi-stage build (см. ниже) |

### Multi-stage build (базово)

```dockerfile
# Stage 1: сборка
FROM python:3.12 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: рантайм
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
CMD ["python", "main.py"]
```

---

## C.4 `docker compose up` зависает

### Симптом

```
[+] Running 3/3
 ✔ Network myproject_backend  Created
 ✔ Container myproject-db-1   Starting...
```

И висит.

### Диагностика

```bash
# Логи БД
docker compose logs db

# Healthcheck статус
docker inspect --format='{{.State.Health.Status}}' myproject-db-1
```

### Частые причины

| Причина | Решение |
|---------|---------|
| БД медленно запускается | Увеличь `start_period` в healthcheck |
| БД упала с ошибкой | Смотри логи БД |
| `depends_on` без healthcheck | Добавь `condition: service_healthy` |
| Диск заполнен | `df -h` |

---

## C.5 Порт уже занят

### Симптом

```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

### Решение

```bash
# 1. Кто занимает порт
ss -tlnp | grep 8000

# 2. Остановить старый контейнер
docker rm -f old-container

# 3. Или используй другой порт
docker compose up -d  # в compose другой порт
```

---

## C.6 Docker не запускается после reboot

### Симптом

```bash
docker ps
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

### Решение

```bash
# 1. Запустить демон
sudo systemctl enable --now docker

# 2. Проверить статус
systemctl status docker

# 3. Если не помогает — рестарт
sudo systemctl restart docker
```

---

## C.7 Контейнер ест всю память

### Симптом

```bash
docker stats
CONTAINER   CPU %   MEM USAGE / LIMIT
myapp       5%      1.8GiB / 2GiB    ← почти всё!
```

### Решение

```bash
# 1. Ограничить память в compose
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512M

# 2. Или при запуске
docker run --memory=512m myapp

# 3. Найти утечку в коде
docker compose logs app
```

---

## C.8 Контейнер не может прочитать файл

### Симптом

```
PermissionError: [Errno 13] Permission denied: '/app/data/file.txt'
```

### Причина

UID внутри контейнера ≠ UID на хосте.

### Решение

```yaml
# Bind mount с правильными правами
volumes:
  - ./data:/app/data:rw

# Или использовать Docker volume вместо bind mount
volumes:
  - appdata:/app/data
```
