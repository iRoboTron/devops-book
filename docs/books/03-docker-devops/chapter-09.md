# Глава 9: Итоговый проект

> **Запомни:** Эта глава — не теория. Ты соберёшь полный стек самостоятельно. Без подсказок, по чеклисту. Как настоящий DevOps.

---

## 9.1 Цель

Собрать Docker-стек проекта с нуля:

```
docker-compose up -d
        │
        ├── [nginx:80] ← обратный прокси в Docker
        │       │ proxy_pass → app:8000
        │       ▼
        ├── [python-app:8000] ← Dockerfile (твой код)
        │       │ DATABASE_URL
        │       ▼
        └── [postgres:5432] ← volume: pgdata
                │
                └── volume: pgdata (данные не теряются)
```

**Требования:**
- ✅ Dockerfile для Python-приложения
- ✅ docker-compose.yml с app + db + nginx
- ✅ Секреты в `.env` (не в коде!)
- ✅ Healthcheck для базы данных
- ✅ Volume для данных PostgreSQL
- ✅ Nginx как reverse proxy
- ✅ `restart: unless-stopped`
- ✅ Makefile для удобства

---

## Стартовая точка

Тип проекта: **новый Docker-сервер / новая Docker-VM**.

Ты не продолжаешь итоговый проект книги 2. В книге 2 приложение работало на хосте через systemd и host Nginx. В этой книге мы специально собираем другой вариант: приложение, база данных и Nginx живут в Docker Compose.

До начала должно быть:
- Ubuntu Server или VM;
- Docker и Docker Compose plugin установлены по главе 0 этой книги;
- пользователь с `sudo`;
- свободный порт `80` на этой машине;
- пустой или специально подготовленный каталог `/opt/myapp`.

Если ты запускаешь это на той же VM, где проходил книгу 2, сначала останови host Nginx или используй новую VM. Иначе контейнер `nginx` не сможет занять порт `80`.

Если у тебя чистая Ubuntu без Docker, сначала выполни установку Docker из главы 0 этой книги, затем возвращайся сюда. Этот итоговый проект создаёт приложение в `/opt/myapp`; книга 4 будет продолжать именно этот путь.

---

## 9.2 Шаг 1: Подготовка проекта

### Структура

```
/opt/myapp/
├── docker-compose.yml
├── Dockerfile
├── .env
├── .env.example
├── .gitignore
├── Makefile
├── main.py
├── requirements.txt
└── nginx/
    └── conf.d/
        └── app.conf
```

### Создай директорию

```bash
sudo mkdir -p /opt/myapp/nginx/conf.d
sudo chown -R "$USER:$USER" /opt/myapp
cd /opt/myapp
```

---

## 9.3 Шаг 2: Python-приложение

### main.py

```python
import os
import psycopg2
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Docker DevOps</title></head>
            <body>
                <h1>Full Stack in Docker!</h1>
                <p>Time: {datetime.datetime.now().strftime('%H:%M:%S')}</p>
                <p><a href="/health">Health Check</a></p>
                <p><a href="/users">Users Count</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "python-app"}).encode())
        elif self.path == '/users':
            try:
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
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"DB Error: {str(e)}".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    print("Running on http://0.0.0.0:8000")
    server.serve_forever()
```

### requirements.txt

```
psycopg2-binary
```

---

## 9.4 Шаг 3: Dockerfile

`Dockerfile` описывает, как собрать образ приложения `app`. Это файл именно с именем `Dockerfile`, без расширения `.txt` или `.dockerfile`.

Создай его в каталоге проекта, там же где лежат `main.py` и `requirements.txt`:

```bash
nano Dockerfile
```

Вставь в него весь код ниже без изменений:

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

Что делает каждая строка:

| Строка | Зачем нужна |
| --- | --- |
| `FROM python:3.12-slim` | Берет готовый легкий образ с Python 3.12. |
| `ENV PYTHONUNBUFFERED=1` | Делает так, чтобы логи Python сразу попадали в `docker compose logs`. |
| `WORKDIR /app` | Создает рабочую папку `/app` внутри контейнера и дальше выполняет команды из нее. |
| `COPY requirements.txt .` | Копирует файл зависимостей в контейнер. |
| `RUN pip install --no-cache-dir -r requirements.txt` | Устанавливает зависимости из `requirements.txt`. |
| `COPY . .` | Копирует остальной код проекта в контейнер. |
| `EXPOSE 8000` | Документирует, что приложение слушает порт `8000` внутри контейнера. |
| `CMD ["python", "main.py"]` | Запускает приложение командой `python main.py`. |

Важно, что `requirements.txt` копируется и устанавливается до `COPY . .`. Docker сможет переиспользовать этот слой при пересборке, если зависимости не менялись, и сборка будет быстрее.

---

## 9.5 Шаг 4: .env и секреты

В этом шаге нужно создать три файла:

- `.env.example` — пример настроек без настоящих секретов. Его можно хранить в git.
- `.env` — реальные настройки для запуска проекта. Его нельзя хранить в git.
- `.gitignore` — список файлов, которые git должен игнорировать.

Создай файл-пример:

```bash
nano .env.example
```

Вставь в него:

```env
POSTGRES_USER=app_user
POSTGRES_PASSWORD=
POSTGRES_DB=app_db
DATABASE_URL=postgresql://app_user:CHANGE_ME@db:5432/app_db
SECRET_KEY=change-me-to-random-string
```

Здесь `CHANGE_ME` показывает, что настоящий пароль должен быть только в `.env`.

Теперь создай реальный файл с настройками:

```bash
nano .env
```

Вставь в него пример ниже, но лучше замени `POSTGRES_PASSWORD` и `SECRET_KEY` на свои значения:

```env
POSTGRES_USER=app_user
POSTGRES_PASSWORD=x7k9mP2qR5wN
POSTGRES_DB=app_db
DATABASE_URL=postgresql://app_user:x7k9mP2qR5wN@db:5432/app_db
SECRET_KEY=django-insecure-abc123def456
```

Что здесь важно:

- `POSTGRES_USER` — пользователь PostgreSQL.
- `POSTGRES_PASSWORD` — пароль этого пользователя.
- `POSTGRES_DB` — имя базы данных.
- `DATABASE_URL` — строка подключения приложения к базе.
- `SECRET_KEY` — секретный ключ приложения, его нельзя публиковать.

В `DATABASE_URL` должны совпадать пользователь, пароль и база:

```text
postgresql://POSTGRES_USER:POSTGRES_PASSWORD@db:5432/POSTGRES_DB
```

Имя `db` в середине строки — это не домен и не `localhost`. Это имя сервиса базы данных из `docker-compose.yml`. Docker Compose сам создаст внутреннюю сеть, и контейнер `app` сможет обратиться к контейнеру `db` по этому имени.

Ограничь права на `.env`, чтобы файл мог читать только текущий пользователь:

```bash
chmod 600 .env
```

Теперь создай `.gitignore`:

```bash
nano .gitignore
```

Вставь в него:

```
.env
__pycache__/
*.pyc
venv/
```

После этого `.env` не попадет в репозиторий, а `.env.example` останется как инструкция для другого человека или для будущего запуска проекта.

---

## 9.6 Шаг 5: Nginx конфиг

### nginx/conf.d/app.conf

```nginx
upstream app {
    server app:8000;
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://app;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    access_log /var/log/nginx/app-access.log;
    error_log /var/log/nginx/app-error.log;
}
```

---

## 9.7 Шаг 6: docker-compose.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
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
    networks:
      - backend

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - backend

volumes:
  pgdata:

networks:
  frontend:
  backend:
```

---

## 9.8 Шаг 7: Makefile

`Makefile` не обязателен для Docker, но он сильно упрощает работу. Вместо длинных команд `docker compose ...` мы будем писать короткие команды вида `make up`, `make logs`, `make db-shell`.

Создай файл именно с именем `Makefile`, без расширения:

```bash
nano Makefile
```

Вставь в него:

```makefile
.PHONY: up down build restart logs logs-nginx logs-db shell db-shell ps clean

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up -d --build

restart:
	docker compose restart

logs:
	docker compose logs -f app

logs-nginx:
	docker compose logs -f nginx

logs-db:
	docker compose logs -f db

shell:
	docker compose exec app bash

db-shell:
	docker compose exec db psql -U $$(grep POSTGRES_USER .env | cut -d= -f2) -d $$(grep POSTGRES_DB .env | cut -d= -f2)

ps:
	docker compose ps

clean:
	docker compose down -v
	docker compose rm -f
```

> **Важно:** В Makefile перед командами нужны табы, не пробелы. Например, строка `docker compose up -d` под `up:` должна начинаться с клавиши Tab. Если увидишь ошибку `missing separator`, почти всегда проблема именно в пробелах вместо таба.

Что делает каждая цель:

| Цель | Команда | Что происходит |
| --- | --- | --- |
| `up` | `make up` | Запускает все сервисы в фоне. |
| `down` | `make down` | Останавливает и удаляет контейнеры, но не удаляет volume с базой. |
| `build` | `make build` | Пересобирает образ приложения и запускает сервисы заново. |
| `restart` | `make restart` | Перезапускает уже созданные контейнеры. |
| `logs` | `make logs` | Показывает логи приложения `app`. |
| `logs-nginx` | `make logs-nginx` | Показывает логи Nginx. |
| `logs-db` | `make logs-db` | Показывает логи PostgreSQL. |
| `shell` | `make shell` | Открывает bash внутри контейнера `app`. |
| `db-shell` | `make db-shell` | Открывает консоль PostgreSQL внутри контейнера `db`. |
| `ps` | `make ps` | Показывает состояние контейнеров. |
| `clean` | `make clean` | Полностью останавливает проект и удаляет volume с данными базы. |

Самая сложная строка здесь:

```makefile
docker compose exec db psql -U $$(grep POSTGRES_USER .env | cut -d= -f2) -d $$(grep POSTGRES_DB .env | cut -d= -f2)
```

Она нужна для `make db-shell`.

Разбор:

- `docker compose exec db` — выполнить команду внутри контейнера `db`.
- `psql` — открыть консоль PostgreSQL.
- `grep POSTGRES_USER .env | cut -d= -f2` — взять имя пользователя из файла `.env`.
- `grep POSTGRES_DB .env | cut -d= -f2` — взять имя базы из файла `.env`.
- `$$` используется потому, что в Makefile один `$` имеет специальный смысл. Чтобы передать обычный `$` в shell-команду, пишут `$$`.

Команду `make clean` используй только когда нужно полностью сбросить проект во время обучения. Она выполняет `docker compose down -v`, а ключ `-v` удаляет volume `pgdata`, то есть данные PostgreSQL.

Использование:

```bash
make up        # запустить
make down      # остановить
make build     # пересобрать и запустить
make logs      # логи приложения
make shell     # зайти в app
make db-shell  # зайти в БД
make ps        # статус
make clean     # полностью сбросить проект и удалить данные БД
```

---

## 9.9 Шаг 8: Запуск и проверка

### Запустить

```bash
make up
# или: docker compose up -d
```

### Проверить

```bash
# 1. Статус
make ps
# Все Up (healthy)?

# 2. Главная страница
curl http://localhost/

# 3. Health check
curl http://localhost/health

# 4. Users (должно быть 0)
curl http://localhost/users

# 5. Логи
make logs
```

### Проверить данные сохраняются

```bash
# Зайди в БД
make db-shell

# Создай таблицу
CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT);
INSERT INTO users (name) VALUES ('Ivan');
\q

# Проверь через API
curl http://localhost/users
# {"users": 1}

# Пересоздай контейнеры
make down
make up

# Данные на месте?
curl http://localhost/users
# {"users": 1} ← да!
```

---

## 9.10 Финальный чеклист

```
□ docker compose up -d — всё поднимается без ошибок
□ docker compose ps — все сервисы Up
□ db — Up (healthy)
□ curl http://localhost/ — возвращает HTML
□ curl http://localhost/health — {"status": "ok"}
□ curl http://localhost/users — работает с БД
□ docker compose down && docker compose up -d — данные сохранились
□ После reboot сервера — всё поднялось само (restart: unless-stopped)
□ .env НЕТ в git
□ docker images — образ app не тяжелее 200МБ
□ db НЕ доступна снаружи (nc -zv localhost 5432 → timeout)
```

### Если что-то не работает

```bash
# 1. Статус
docker compose ps

# 2. Логи
docker compose logs db      # БД
docker compose logs app     # приложение
docker compose logs nginx   # прокси

# 3. Проверить соединение
docker compose exec app ping db

# 4. Проверить конфиг
docker compose config

# 5. Healthcheck
docker inspect --format='{{.State.Health.Status}}' myproject-db-1
```

---

## 9.11 Сохранение VM для книги 4

После финального чеклиста сделай снапшот VM. Это важная точка: книга 4 начинается не с чистой Ubuntu, а с этого Docker-проекта в `/opt/myapp`.

Перед снапшотом проверь:

```bash
cd /opt/myapp
docker compose ps
curl http://localhost/health
curl http://localhost/users
```

Сохрани VM с понятным именем, например:

```text
after-book-3-docker-myapp
```

Не выполняй `make clean` перед снапшотом. Команда `make clean` удаляет volume PostgreSQL, а для книги 4 нужен уже работающий Docker-стек с приложением, базой, Nginx, `.env` и `docker-compose.yml`.

Если в книге 4 что-то сломаешь, можно будет откатиться к этому снапшоту и продолжить настройку CI/CD заново.

---

## 9.12 Что дальше

Ты прошёл Модуль 3. Вот что ты теперь умеешь:

- ✅ Писать Dockerfile для Python-приложения
- ✅ Описывать стек в docker-compose.yml
- ✅ Управлять секретами через `.env`
- ✅ Настраивать healthcheck для БД
- ✅ Использовать volumes для данных
- ✅ Настраивать сети Docker (frontend/backend)
- ✅ Добавлять Nginx в compose
- ✅ Использовать Makefile для удобства

### Следующий модуль: CI/CD

В Модуле 4:
- GitHub Actions
- Автоматический билд и push образа
- Автодеплой на сервер по push в main
- Zero-downtime deployment

---

> **Поздравляю!** Ты упаковал полноценный стек в Docker.
> Одна команда — и всё работает.
> Это уровень настоящего DevOps.
