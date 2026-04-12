# Глава 8: Nginx в Docker и полный стек

> **Запомни:** Nginx в контейнере — тот же Nginx. Но теперь он часть Docker-сети и общается с app по имени сервиса.

---

## 8.1 Nginx как сервис в compose

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - app
    networks:
      - frontend
      - backend
```

### Разбор

| Директива | Зачем |
|-----------|-------|
| `image: nginx:alpine` | Лёгкий образ (42 МБ) |
| `ports: 80:80, 443:443` | Открыть наружу |
| `volumes: ./nginx/conf.d` | Твои конфиги внутри контейнера |
| `:ro` | Read-only (контейнер не меняет конфиги) |
| `depends_on: app` | Nginx стартует после app |
| `networks: frontend, backend` | Видит и интернет и app |

---

## 8.2 Конфиг Nginx для Docker

Создай `nginx/conf.d/app.conf`:

```nginx
upstream app {
    server app:8000;
}

server {
    listen 80;
    server_name myapp.local;

    location / {
        proxy_pass http://app;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Ключевое отличие

```nginx
server app:8000;    ← имя сервиса из compose
```

Не `127.0.0.1:8000`. Не IP. **Имя сервиса**.

Docker DNS разрешает `app` → IP контейнера `app`.

> **Запомни:** В Docker-сети контейнеры общаются по имени.
> `app:8000`, `db:5432`, `redis:6379`.
> Это работает только в custom bridge сети.

---

## 8.3 Две сети: frontend + backend

```yaml
services:
  nginx:
    networks:
      - frontend    ← интернет
      - backend     ← app

  app:
    networks:
      - backend     ← только backend

  db:
    networks:
      - backend     ← только backend

networks:
  frontend:
  backend:
```

### Схема

```
Интернет
    │
    ▼ (frontend сеть)
┌─────────┐
│  nginx  │
└───┬─────┘
    │ (backend сеть)
    ├──→ ┌─────────┐
    │    │   app   │
    │    └───┬─────┘
    │        │ (backend сеть)
    │        ▼
    │    ┌─────────┐
    └──→ │   db    │
         └─────────┘
```

| Сервис | frontend | backend | Вид снаружи |
|--------|----------|---------|-------------|
| Nginx | ✅ | ✅ | ✅ (порт 80/443) |
| app | ❌ | ✅ | ❌ |
| db | ❌ | ✅ | ❌ |

> **Запомни:** Это сегментация.
> База данных НЕ доступна из интернета.
> Приложение НЕ доступно напрямую — только через Nginx.

---

## 8.4 SSL-сертификаты из хоста

Certbot на хосте → сертификаты в `/etc/letsencrypt/`.
Nginx в контейнере → нужен доступ к сертификатам.

### Bind mount сертификатов

```yaml
services:
  nginx:
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro    ← с хоста
      - ./nginx/certbot-www:/var/www/certbot:rw  ← для challenge
    ports:
      - "80:80"
      - "443:443"
```

### Nginx конфиг с SSL

```nginx
server {
    listen 443 ssl;
    server_name myapp.ru;

    ssl_certificate /etc/letsencrypt/live/myapp.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP → HTTPS + certbot challenge
server {
    listen 80;
    server_name myapp.ru;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```

> **Порядок важен:** Certbot нужен порт 80 для challenge.
> Nginx должен отдавать challenge файлы на порт 80.

---

## 8.5 `restart: unless-stopped`

```yaml
services:
  app:
    build: .
    restart: unless-stopped

  db:
    image: postgres:16
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    restart: unless-stopped
```

`restart: unless-stopped` = перезапускать если упал или сервер перезагрузился.
Исключение: ты вручную остановил (`docker compose stop`).

### Политики restart

| Политика | Когда перезапускает |
|----------|-------------------|
| `no` | Никогда (по умолчанию) |
| `always` | Всегда |
| `unless-stopped` | Всегда, кроме ручной остановки |
| `on-failure` | Только если упал с ошибкой |

> **Совет:** Для продакшена — `unless-stopped`.
> Сервисы поднимутся после reboot сервера.

---

## 8.6 Полный стек: Nginx + App + DB

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./nginx/certbot-www:/var/www/certbot:rw
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

### Структура проекта

```
myproject/
├── docker-compose.yml
├── Dockerfile
├── .env
├── .env.example
├── .gitignore
├── main.py
├── requirements.txt
└── nginx/
    ├── conf.d/
    │   └── app.conf
    └── certbot-www/
```

---

## 📝 Упражнения

### Упражнение 8.1: Добавить Nginx в compose
**Задача:**
1. Создай `nginx/conf.d/app.conf` (как в 8.2)
2. Добавь сервис nginx в docker-compose.yml (с frontend/backend сетями)
3. Подними: `docker compose up -d`
4. Проверь: `curl http://localhost` — работает через Nginx?
5. Убедись что db не доступна снаружи: `nc -zv localhost 5432`

### Упражнение 8.2: restart policy
**Задача:**
1. Добавь `restart: unless-stopped` ко всем сервисам
2. Перезагрузи сервер (или `docker compose down && docker compose up -d`)
3. Проверь: `docker compose ps` — все поднялись?

### Упражнение 8.3: Self-signed SSL в Docker
**Задача:**
1. Создай self-signed сертификат:
   ```bash
   mkdir -p nginx/certs
   openssl req -x509 -nodes -days 365 \
     -newkey rsa:2048 \
     -keyout nginx/certs/app.key \
     -out nginx/certs/app.crt \
     -subj "/CN=myapp.local"
   ```
2. Измени nginx конфиг для HTTPS (как в 8.4, без certbot)
3. Добавь volume в compose: `- ./nginx/certs:/etc/nginx/certs:ro`
4. Подними и проверь: `curl -k https://localhost`

### Упражнение 8.4: DevOps Think
**Задача:** «Ты добавил Nginx в compose. Теперь при `docker compose up` приложение отвечает 502. Почему?»

Подсказки:
1. Запущен ли app? `docker compose ps`
2. Видит ли Nginx app? `docker compose exec nginx ping app`
3. Правильный ли upstream в nginx конфиге? (`server app:8000`)
4. Какой порт слушает app? (EXPOSE в Dockerfile)
5. Логи nginx: `docker compose logs nginx` — что в error.log?

---

## 📋 Чеклист главы 8

- [ ] Я могу добавить Nginx в docker-compose.yml
- [ ] Я понимаю что `proxy_pass http://app` использует имя сервиса
- [ ] Я понимаю зачем две сети (frontend/backend)
- [ ] Я могу пробросить SSL-сертификаты из хоста в контейнер
- [ ] Я понимаю как certbot работает с Nginx в контейнере
- [ ] Я использую `restart: unless-stopped` для продакшена
- [ ] Я могу написать полный стек (nginx + app + db)

**Всё отметил?** Переходи к Главе 9 — итоговый проект.
