# Глава 6: docker-compose — весь стек одной командой

> **Запомни:** `docker run` с 10 флагами — неудобно и не воспроизводимо. docker-compose.yml — один файл, один запуск, весь стек.

---

## 6.1 Проблема: много контейнеров, много команд

Без docker-compose:

```bash
# База данных
docker network create backend

docker run -d --network backend --name db \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=mydb \
  postgres:16

# Приложение
docker run -d --network backend --name app \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:secret@db:5432/mydb \
  myapp:1.0

# Nginx
docker run -d --network backend --name nginx \
  -p 80:80 \
  -v ./nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine
```

**Проблемы:**
- 10+ команд чтобы запустить
- Нужно помнить порядок запуска (сначала БД!)
- Легко ошибиться в флаге
- Остановить: `docker rm -f db app nginx`
- Забыл том? Данные потеряны.

---

## 6.2 Решение: docker-compose.yml

Один файл описывает **весь стек**:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: mydb
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - backend

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://user:secret@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy
    networks:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    networks:
      - backend

volumes:
  pgdata:

networks:
  backend:
```

### Одна команда

```bash
docker compose up -d
```

Всё запустилось. В правильном порядке. С правильными настройками.

> **Запомни:** `docker compose` (без дефиса) — новая версия (v2).
> `docker-compose` (с дефисом) — старая (v1, Python).
> Используй `docker compose` — он идёт с Docker.

---

## 6.3 Структура файла

```yaml
services:          ← КОНТЕЙНЕРЫ (что запускаем)
  db:              ← имя сервиса
    image: ...     ← образ или build
    ...

  app:
    build: .       ← собрать из Dockerfile
    ...

volumes:           ← ТОМА (где хранить данные)
  pgdata:

networks:          ← СЕТИ (как общаются)
  backend:
```

### YAML — основы синтаксиса

YAML — формат данных который читает человек.

```yaml
# Комментарий
ключ: значение

список:
  - элемент1
  - элемент2

вложенность:
  внутри:
    ещё: значение
```

**Правила:**
- Отступы = 2 пробела (НЕ табы!)
- `:` после ключа + пробел
- `-` = элемент списка

---

## 6.4 image vs build

### `image` — использовать готовый образ

```yaml
services:
  db:
    image: postgres:16
```

Скачает с Docker Hub если нет локально.

### `build` — собрать из Dockerfile

```yaml
services:
  app:
    build: .
```

`.` = текущая директория (где docker-compose.yml и Dockerfile).

### Оба вместе

```yaml
services:
  app:
    build: .
    image: myusername/myapp:1.0
```

Соберёт из Dockerfile И даст тег `myusername/myapp:1.0`.

---

## 6.5 `depends_on` — порядок запуска

```yaml
services:
  app:
    depends_on:
      - db
```

Docker запустит `db` **перед** `app`.

### Проблема: просто `depends_on` недостаточно

```yaml
depends_on:
  - db
```

Docker ждёт пока контейнер `db` **запущен**.
Но PostgreSQL может запускаться 30 секунд.
`app` стартует раньше чем БД готова.

### Решение: `condition: service_healthy`

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    depends_on:
      db:
        condition: service_healthy
```

Теперь `app` ждёт пока `db` **здоров**.

### healthcheck — как работает

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U user"]
  interval: 5s      # проверять каждые 5 секунд
  timeout: 3s       # ждать ответ 3 секунды
  retries: 5        # 5 попыток = признать unhealthy
  start_period: 10s # первые 10 секунд не проверять (запуск)
```

`pg_isready` — утилита PostgreSQL которая проверяет готовность.

> **Совет:** Всегда добавляй healthcheck для баз данных.
> Без него app может стартовать раньше чем БД готова.

---

## 6.6 Основные команды docker compose

### Поднять весь стек

```bash
docker compose up -d
```

`-d` = detach (в фоне).

### Посмотреть статус

```bash
docker compose ps
NAME            STATUS          PORTS
myproject-db-1  Up (healthy)    5432/tcp
myproject-app-1 Up              0.0.0.0:8000->8000/tcp
myproject-nginx-1 Up            0.0.0.0:80->80/tcp
```

### Логи

```bash
docker compose logs          # все логи
docker compose logs app      # только app
docker compose logs -f app   # следить в реальном времени
docker compose logs --tail 50 app  # последние 50 строк
```

### Зайти в контейнер

```bash
docker compose exec app bash
```

### Остановить и удалить контейнеры

```bash
docker compose down
```

Контейнеры удалены. **Тома сохранены.**

### Остановить, удалить контейнеры И тома

```bash
docker compose down -v
```

> **Опасно:** `-v` удаляет тома. База данных исчезнет.
> Всегда думай перед `-v`.

### Пересобрать и поднять

```bash
docker compose up -d --build
```

Пересоберёт образы из Dockerfile и поднимет всё.

### Перезапустить один сервис

```bash
docker compose restart app
```

---

## 6.7 Полный пример: Python + PostgreSQL

### Проект

```
myproject/
├── docker-compose.yml
├── Dockerfile
├── main.py
└── requirements.txt
```

### main.py

```python
import os
import psycopg2
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        elif self.path == '/users':
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM users;")
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"users": count}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    server.serve_forever()
```

### requirements.txt

```
psycopg2-binary
```

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: mydb
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backend

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:secret@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy
    networks:
      - backend

volumes:
  pgdata:

networks:
  backend:
```

### Запуск

```bash
docker compose up -d
```

### Проверка

```bash
docker compose ps
# Все Up (healthy)

curl http://localhost:8000/health
{"status": "ok"}

curl http://localhost:8000/users
{"users": 0}
```

---

## 📝 Упражнения

### Упражнение 6.1: Первый docker-compose
**Задача:**
1. Создай директорию проекта с файлами выше (main.py, requirements.txt, Dockerfile, docker-compose.yml)
2. Подними: `docker compose up -d`
3. Проверь статус: `docker compose ps`
4. Все сервисы работают?

### Упражнение 6.2: Логи и exec
**Задача:**
1. Посмотри логи: `docker compose logs -f app`
2. В другом терминале: `curl http://localhost:8000/health`
3. Видишь запрос в логах?
4. Зайди в контейнер БД: `docker compose exec db psql -U user -d mydb`
5. Создай таблицу: `CREATE TABLE users (id SERIAL PRIMARY KEY);`
6. Выйди и проверь API: `curl http://localhost:8000/users`

### Упражнение 6.3: Перезапуск и данные
**Задача:**
1. Останови всё: `docker compose down`
2. Подними снова: `docker compose up -d`
3. Проверь что таблица users сохранилась: `curl http://localhost:8000/users`
4. Теперь останови с удалением томов: `docker compose down -v`
5. Подними снова: `docker compose up -d`
6. Что с данными? (таблица исчезла?)

### Упражнение 6.4: Пересборка
**Задача:**
1. Измени main.py (добавь новый эндпоинт)
2. Пересобери и подними: `docker compose up -d --build`
3. Проверь новый функционал

### Упражнение 6.5: DevOps Think
**Задача:** «`docker compose up` зависает на шаге app. app ждёт db но db не становится healthy. Почему?»

Подсказки:
1. Проверь логи db: `docker compose logs db`
2. Правильный ли `pg_isready -U user`? (совпадает ли POSTGRES_USER?)
3. Достаточно ли времени на запуск? (start_period)
4. Проверь healthcheck: `docker compose ps` — db здоров?

---

## 📋 Чеклист главы 6

- [ ] Я понимаю зачем нужен docker-compose (vs много docker run)
- [ ] Я понимаю структуру файла (services, volumes, networks)
- [ ] Я знаю основы YAML (отступы, списки, вложенность)
- [ ] Я понимаю разницу image vs build
- [ ] Я понимаю почему depends_on без condition недостаточно
- [ ] Я могу настроить healthcheck для базы данных
- [ ] Я знаю основные команды (up, down, logs, exec, ps)
- [ ] Я знаю что `down -v` удаляет тома (опасно!)
- [ ] Я могу написать docker-compose.yml для app + db

**Всё отметил?** Переходи к Главе 7 — переменные окружения и секреты.
