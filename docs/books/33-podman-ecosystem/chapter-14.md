# Глава 14: Итоговый проект — переводим реальный сервис

## Что вы узнаете

- как применить всё из книги в едином проекте;
- как пройти путь от dev-окружения до production-ready сервиса;
- что проверять на каждом этапе и как убедиться что всё работает.

---

## Что будем делать

Возьмём типичный веб-сервис: Python-приложение + PostgreSQL + Nginx. Пройдём полный путь:

```text
Шаг 1: Запуск через podman-compose (разработка)
Шаг 2: Проверка rootless — ни одна команда без sudo
Шаг 3: Публикация образов в реестр
Шаг 4: Автозапуск через Quadlet (как на настоящем сервере)
Шаг 5: K8s YAML из работающего стека
Шаг 6: CI/CD pipeline
```

---

## Подготовка: структура проекта

```bash
mkdir -p ~/final-project
cd ~/final-project

# Структура:
# final-project/
# ├── app/
# │   ├── main.py
# │   └── requirements.txt
# ├── nginx/
# │   └── default.conf
# ├── Dockerfile
# ├── docker-compose.yml
# └── .env
```

### Приложение (app/main.py)

```python
import os
import psycopg2
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json

DB_URL = os.environ.get("DATABASE_URL", "")

def get_db():
    p = urlparse(DB_URL)
    return psycopg2.connect(
        host=p.hostname, port=p.port or 5432,
        database=p.path.lstrip('/'),
        user=p.username, password=p.password
    )

def init_db():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id SERIAL PRIMARY KEY,
                path VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()
    conn.close()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}\n')
            return

        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO visits(path) VALUES(%s)", (self.path,))
                cur.execute("SELECT COUNT(*) FROM visits")
                count = cur.fetchone()[0]
            conn.commit()
            conn.close()

            resp = json.dumps({"visits": count, "path": self.path}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp + b"\n")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    if DB_URL:
        init_db()
    print(f"Starting server on port {port}")
    HTTPServer(("", port), Handler).serve_forever()
```

### Зависимости (app/requirements.txt)

```
psycopg2-binary==2.9.9
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Непривилегированный пользователь
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "main.py"]
```

### Nginx конфиг (nginx/default.conf)

```nginx
server {
    listen 80;

    location /health {
        return 200 "nginx ok\n";
        add_header Content-Type text/plain;
    }

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 10s;
    }
}
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD:-devpassword}
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myapp"]
      interval: 5s
      timeout: 3s
      retries: 10

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://myapp:${DB_PASSWORD:-devpassword}@localhost:5432/myapp
      PORT: "8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "${HTTP_PORT:-8080}:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  pgdata:
```

### .env (для dev)

```bash
DB_PASSWORD=devpassword123
HTTP_PORT=8080
```

---

## Шаг 1: Запуск через podman-compose

```bash
cd ~/final-project

# Запустить стек
podman-compose --env-file .env up -d

# Дождаться старта (PostgreSQL инициализируется несколько секунд)
sleep 5

# Проверить статус
podman-compose ps

# Функциональная проверка
curl http://localhost:8080/health
# nginx ok

curl http://localhost:8080/
# {"visits": 1, "path": "/"}

curl http://localhost:8080/
# {"visits": 2, "path": "/"}

curl http://localhost:8080/api/users
# {"visits": 3, "path": "/api/users"}

echo "=== Шаг 1 завершён: стек работает ==="
```

---

## Шаг 2: Проверка rootless

```bash
# Убедиться что ни один контейнер не запущен от root

echo "=== Проверка UID процессов ==="
for container in $(podman ps --format '{{.Names}}'); do
  PID=$(podman inspect $container --format '{{.State.Pid}}')
  UID_HOST=$(ps -o uid= -p $PID 2>/dev/null || echo "stopped")
  echo "$container: PID=$PID, UID на хосте=$UID_HOST"
done

# Ожидаемый результат: UID = ваш UID (например, 1000), не 0

echo ""
echo "=== Подтверждение rootless ==="
podman info --format '{{.Host.Security.Rootless}}'
# true
```

---

## Шаг 3: Публикация образов в реестр

```bash
# Собрать образ с версионным тегом
APP_VERSION="v1.0.0"
REGISTRY="ghcr.io"
REPO="${REGISTRY}/$(git config user.name | tr '[:upper:]' '[:lower:]')/final-project"

podman build -t ${REPO}:${APP_VERSION} -t ${REPO}:latest .

# Войти в реестр
echo "$GITHUB_TOKEN" | podman login $REGISTRY -u YOUR_GITHUB_USER --password-stdin

# Запушить
podman push ${REPO}:${APP_VERSION}
podman push ${REPO}:latest

echo "=== Образ доступен: ${REPO}:${APP_VERSION} ==="

# Проверить через skopeo (без скачивания):
skopeo inspect docker://${REPO}:${APP_VERSION} | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Образ создан:', d.get('Created', 'unknown'))
print('Слоёв:', len(d.get('Layers', [])))
"
```

---

## Шаг 4: Автозапуск через Quadlet

```bash
# Остановить podman-compose стек
podman-compose down

mkdir -p ~/.config/containers/systemd/

# Том для PostgreSQL
cat > ~/.config/containers/systemd/final-pgdata.volume << 'EOF'
[Volume]
EOF

# Сервис PostgreSQL
cat > ~/.config/containers/systemd/final-db.container << 'EOF'
[Unit]
Description=Final Project — PostgreSQL
After=network-online.target

[Container]
Image=docker.io/library/postgres:16-alpine
Environment=POSTGRES_PASSWORD=devpassword123
Environment=POSTGRES_DB=myapp
Environment=POSTGRES_USER=myapp
Volume=final-pgdata.volume:/var/lib/postgresql/data

[Service]
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# Приложение (зависит от DB)
cat > ~/.config/containers/systemd/final-app.container << 'EOF'
[Unit]
Description=Final Project — Python App
After=final-db.service
Requires=final-db.service

[Container]
Image=ghcr.io/YOUR_GITHUB_USER/final-project:latest
Environment=DATABASE_URL=postgresql://myapp:devpassword123@localhost:5432/myapp
Environment=PORT=8000
Network=host

[Service]
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Nginx
cat > ~/.config/containers/systemd/final-nginx.container << 'EOF'
[Unit]
Description=Final Project — Nginx
After=final-app.service

[Container]
Image=docker.io/library/nginx:alpine
PublishPort=8080:80
Volume=%h/final-project/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro

[Service]
Restart=always

[Install]
WantedBy=default.target
EOF

# Применить
systemctl --user daemon-reload
systemctl --user enable --now final-db.service
sleep 10  # дождаться PostgreSQL
systemctl --user enable --now final-app.service
systemctl --user enable --now final-nginx.service

# Проверить
systemctl --user status final-db.service final-app.service final-nginx.service

# Функциональная проверка
sleep 5
curl http://localhost:8080/health
curl http://localhost:8080/

echo "=== Шаг 4 завершён: Quadlet настроен ==="
```

Включить автозапуск без логина:
```bash
sudo loginctl enable-linger $USER
# После следующей перезагрузки сервисы стартуют автоматически
```

---

## Шаг 5: K8s YAML из работающего стека

```bash
# Создать Pod для экспорта (как в chapter 7)
podman pod create --name final-pod \
  -p 8080:80 \
  -p 8000:8000

podman run -d --pod final-pod --name final-nginx \
  -v ~/final-project/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine

podman run -d --pod final-pod --name final-app \
  -e DATABASE_URL=postgresql://myapp:devpassword123@localhost:5432/myapp \
  -e PORT=8000 \
  ghcr.io/YOUR_GITHUB_USER/final-project:latest

# Сгенерировать черновик
podman kube generate final-pod > k8s/pod-draft.yaml

# Остановить тестовый Pod
podman pod rm --force final-pod

# Проверить черновик
cat k8s/pod-draft.yaml
```

Что нужно адаптировать в YAML (по Приложению D):
- `kind: Pod` → `kind: Deployment`
- `localhost/...` → реальный реестр
- Добавить `resources.requests/limits`
- Добавить `readinessProbe`
- Вынести секреты в `kind: Secret`

```bash
# Протестировать адаптированный YAML (без кластера):
podman kube play k8s/deployment.yaml
curl http://localhost:8080/
podman kube down k8s/deployment.yaml

echo "=== Шаг 5 завершён: K8s YAML готов ==="
```

---

## Шаг 6: CI/CD pipeline

```yaml
# .github/workflows/ci.yml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE: ghcr.io/${{ github.repository_owner }}/final-project

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Podman
        run: sudo apt-get install -y podman

      - name: Login to GHCR
        if: github.event_name != 'pull_request'
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | \
          podman login ${{ env.REGISTRY }} \
            -u ${{ github.actor }} \
            --password-stdin

      - name: Build
        run: |
          podman build \
            --cache-from ${{ env.IMAGE }}:cache \
            -t ${{ env.IMAGE }}:${{ github.sha }} \
            . || \
          podman build \
            -t ${{ env.IMAGE }}:${{ github.sha }} \
            .

      - name: Test
        run: |
          # Запустить контейнер и проверить /health
          podman run -d --name test-app \
            -p 18000:8000 \
            ${{ env.IMAGE }}:${{ github.sha }}

          # Подождать старта (без БД — только проверка что запускается)
          sleep 3

          # Проверить что контейнер жив
          podman inspect test-app --format '{{.State.Status}}'

          podman stop test-app
          podman rm test-app

      - name: Push
        if: github.event_name != 'pull_request'
        run: |
          podman push ${{ env.IMAGE }}:${{ github.sha }}
          podman tag ${{ env.IMAGE }}:${{ github.sha }} ${{ env.IMAGE }}:latest
          podman push ${{ env.IMAGE }}:latest
          # Обновить кэш
          podman tag ${{ env.IMAGE }}:${{ github.sha }} ${{ env.IMAGE }}:cache
          podman push ${{ env.IMAGE }}:cache
```

---

## Финальная проверка

```bash
echo "=== ФИНАЛЬНЫЙ ЧЕКЛИСТ ==="

# 1. Rootless
if podman info --format '{{.Host.Security.Rootless}}' | grep -q true; then
  echo "✅ Rootless: работает"
else
  echo "❌ Rootless: НЕ работает"
fi

# 2. Стек через Quadlet
if systemctl --user is-active final-nginx.service | grep -q active; then
  echo "✅ Quadlet: сервисы активны"
else
  echo "❌ Quadlet: сервисы не активны"
fi

# 3. Приложение отвечает
if curl -sf http://localhost:8080/health > /dev/null; then
  echo "✅ Приложение: отвечает на /health"
else
  echo "❌ Приложение: не отвечает"
fi

# 4. Данные сохраняются
VISITS_BEFORE=$(curl -s http://localhost:8080/ | python3 -c "import json,sys; print(json.load(sys.stdin)['visits'])")
curl -s http://localhost:8080/ > /dev/null
VISITS_AFTER=$(curl -s http://localhost:8080/ | python3 -c "import json,sys; print(json.load(sys.stdin)['visits'])")
if [ "$VISITS_AFTER" -gt "$VISITS_BEFORE" ]; then
  echo "✅ База данных: счётчик растёт"
else
  echo "❌ База данных: счётчик не меняется"
fi

# 5. Образ в реестре
if skopeo inspect docker://ghcr.io/YOUR_USER/final-project:latest > /dev/null 2>&1; then
  echo "✅ Реестр: образ доступен"
else
  echo "⚠️  Реестр: образ недоступен (нужен GITHUB_TOKEN)"
fi

# 6. Linger для автозапуска
if loginctl show-user $USER | grep -q "Linger=yes"; then
  echo "✅ Linger: включён (автозапуск после reboot)"
else
  echo "⚠️  Linger: не включён — сервисы не стартуют без логина"
fi
```

---

## Что дальше

Вы прошли полный путь: от понимания OCI-стандарта до production-ready сервиса на Podman. Что можно сделать дальше:

**Углубиться в безопасность:**
- Добавить seccomp-профили для контейнеров
- Настроить AppArmor/SELinux политики
- Использовать `podman image scan` для поиска уязвимостей

**Kubernetes:**
- Задеплоить финальный проект в настоящий кластер (minikube, kind, облако)
- Добавить Ingress, ConfigMap, HorizontalPodAutoscaler
- Настроить GitOps через Argo CD

**Мониторинг:**
- Экспортировать метрики через Prometheus
- Настроить алерты на падение контейнеров
- Логи через Loki + Grafana

---

## Критерии готовности проекта

- [ ] Стек запускается через `podman-compose up` без ошибок
- [ ] Ни одна команда не требует `sudo`
- [ ] Образ опубликован в GHCR или другой реестр
- [ ] Сервисы стартуют при загрузке через Quadlet без входа пользователя
- [ ] K8s YAML сгенерирован и проверен через `podman kube play`
- [ ] CI pipeline собирает и пушит образ при каждом push в main
- [ ] Финальный чеклист показывает все зелёные статусы

## Попробуйте сами

1. Добавьте в приложение эндпоинт `/reset` который очищает счётчик визитов. Пересоберите образ через CI (убедитесь что pipeline зелёный) и обновите Quadlet-сервис через `podman auto-update`.

2. Создайте второй Quadlet-сервис который запускает `podman-compose logs` по расписанию и сохраняет последние 100 строк в файл. Используйте `.container` файл с `Environment=PODMAN_COMPOSE_PROVIDER=...`.

3. Деплойте финальный K8s YAML в minikube или kind. Что потребовалось изменить по сравнению с `podman kube play`? Зафиксируйте разницу в README проекта.
