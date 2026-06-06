# Приложение A: Полный docker-compose.yml

Финальный рабочий файл `docker-compose.yml` со всеми компонентами книги. Готов к `docker compose up -d`.

Структура директорий:

```text
monitoring/
├── docker-compose.yml
├── prometheus/
│   ├── prometheus.yml
│   ├── rules/
│   │   └── alerts.yml
│   └── targets/
│       └── servers.json
├── alertmanager/
│   ├── alertmanager.yml
│   └── templates/
│       └── telegram.tmpl
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml
│       ├── dashboards/
│       │   └── dashboard.yml
│       └── alerting/
│           └── alert_rules.yml
├── loki/
│   └── loki-config.yml
├── promtail/
│   └── promtail-config.yml
├── blackbox/
│   └── blackbox.yml
└── .env
```

```bash
# Создать структуру директорий
mkdir -p prometheus/rules prometheus/targets
mkdir -p alertmanager/templates
mkdir -p grafana/provisioning/datasources grafana/provisioning/dashboards grafana/provisioning/alerting
mkdir -p loki promtail blackbox
touch .env
```

---

## docker-compose.yml

```yaml
# docker-compose.yml
# Полный стек мониторинга: Prometheus + Grafana + Alertmanager + Exporters + Loki
# Запуск: docker compose up -d
# Остановка: docker compose down
# Логи: docker compose logs -f <service>

# --- Volumes для постоянных данных ---
volumes:
  prometheus_data:      # метрики Prometheus (15 дней по умолчанию)
  grafana_data:         # дашборды, настройки, плагины Grafana
  alertmanager_data:    # состояние алертов (silences, inhibition)
  loki_data:            # логи Loki (30 дней)
  vm_data:              # долгосрочное хранение метрик VictoriaMetrics

# --- Изолированная сеть для всех компонентов ---
networks:
  monitoring:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.20.0.0/16

# --- Сервисы ---
services:

  # === PROMETHEUS ===
  # База данных временных рядов + сборщик метрик (pull-модель)
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: prometheus
    restart: unless-stopped
    # Ограничение ресурсов: Prometheus может потреблять много памяти
    # при большом числе time series
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
    volumes:
      # Конфигурация Prometheus
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      # Правила алертинга
      - ./prometheus/rules/:/etc/prometheus/rules/:ro
      # Динамическое обнаружение таргетов через файлы
      - ./prometheus/targets/:/etc/prometheus/targets/:ro
      # Постоянные данные метрик (важно: не удалять без необходимости)
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'    # хранить метрики 15 дней
      - '--storage.tsdb.retention.size=10GB'   # ограничить размер БД
      - '--web.enable-lifecycle'                 # hot reload через curl -X POST /-/reload
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "127.0.0.1:9090:9090"  # только localhost, не наружу
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # === GRAFANA ===
  # Визуализация: дашборды, панели, графики
  grafana:
    image: grafana/grafana:10.4.0
    container_name: grafana
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
    volumes:
      # Постоянные данные Grafana (дашборды, настройки, пользователи)
      - grafana_data:/var/lib/grafana
      # Provisioning: авто-настройка datasources и дашбордов
      - ./grafana/provisioning/:/etc/grafana/provisioning/:ro
    environment:
      # Администратор (сменить в production!)
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      # Запретить регистрацию новых пользователей
      GF_USERS_ALLOW_SIGN_UP: "false"
      # Разрешить анонимный просмотр (опционально)
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      # URL для рендеринга изображений (grafana-image-renderer)
      GF_RENDERING_SERVER_URL: http://grafana-image-renderer:8081/render
      GF_RENDERING_CALLBACK_URL: http://grafana:3000/
      # Отключить обновления (не нужно в изолированной сети)
      GF_NEWS_NEWS_FEED_ENABLED: "false"
    ports:
      - "3000:3000"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    depends_on:
      prometheus:
        condition: service_healthy

  # === GRAFANA IMAGE RENDERER ===
  # Плагин для рендеринга панелей в PNG (для алертов со скриншотами)
  grafana-image-renderer:
    image: grafana/grafana-image-renderer:3.10.0
    container_name: grafana-image-renderer
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    environment:
      HTTP_HOST: "0.0.0.0"
      HTTP_PORT: "8081"
    ports:
      - "127.0.0.1:8081:8081"
    networks:
      - monitoring

  # === NODE EXPORTER ===
  # Агент на сервере: экспортирует метрики ОС (CPU, память, диск, сеть)
  node_exporter:
    image: prom/node-exporter:v1.8.0
    container_name: node_exporter
    restart: unless-stopped
    volumes:
      # Монтируем корневую ФС хоста для получения метрик ОС
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      # Исключить виртуальные ФС из мониторинга дисков
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|run)($$|/)'
      # Включить сбор метрик network через netlink (более точные)
      - '--collector.netclass.ignored-devices=^(veth.*|docker.*|br-.*|lo)$'
    ports:
      - "127.0.0.1:9100:9100"
    networks:
      - monitoring
    pid: host  # доступ к процессам хоста для метрик CPU
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9100/metrics"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 5s

  # === cADVISOR ===
  # Метрики Docker-контейнеров: CPU, память, сеть, рестарты
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.49.1
    container_name: cadvisor
    restart: unless-stopped
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - "127.0.0.1:8080:8080"
    privileged: true  # требуется для метрик CPU и памяти контейнеров
    devices:
      - /dev/kmsg
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # === ALERTMANAGER ===
  # Маршрутизация и отправка уведомлений (Telegram, email, ...)
  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.3'
    volumes:
      # Конфигурация Alertmanager
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      # Шаблоны уведомлений (Go templates)
      - ./alertmanager/templates/:/etc/alertmanager/templates/:ro
      # Постоянные данные (silences, состояние)
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--log.level=info'
    ports:
      - "127.0.0.1:9093:9093"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9093/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # === POSTGRES EXPORTER ===
  # Метрики PostgreSQL: соединения, размер БД, cache hit ratio
  # Требует существующей БД PostgreSQL с пользователем monitoring
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    container_name: postgres_exporter
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.2'
    environment:
      # Строка подключения к PostgreSQL
      # Пользователь monitoring должен иметь доступ к pg_stat_activity
      DATA_SOURCE_NAME: "postgresql://monitoring:MonitorPass@postgres:5432/postgres?sslmode=disable"
    ports:
      - "127.0.0.1:9187:9187"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9187/metrics"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # === NGINX EXPORTER ===
  # Метрики Nginx: RPS, активные соединения, ошибки
  # Требует включенного stub_status в nginx.conf
  nginx_exporter:
    image: nginx/nginx-prometheus-exporter:1.1.0
    container_name: nginx_exporter
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'
    command:
      - '--nginx.scrape-uri=http://nginx:8080/stub_status'
    ports:
      - "127.0.0.1:9113:9113"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9113/metrics"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # === BLACKBOX EXPORTER ===
  # Проверка доступности внешних сервисов: HTTP, TCP, ICMP, DNS
  blackbox_exporter:
    image: prom/blackbox-exporter:v0.24.0
    container_name: blackbox_exporter
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'
    volumes:
      - ./blackbox/blackbox.yml:/etc/blackbox_exporter/config.yml:ro
    ports:
      - "127.0.0.1:9115:9115"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9115/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 5s

  # === PUSHGATEWAY ===
  # Приём метрик от batch jobs по push-модели (скрипты бэкапа, cron)
  pushgateway:
    image: prom/pushgateway:v1.8.0
    container_name: pushgateway
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.2'
    ports:
      - "127.0.0.1:9091:9091"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9091/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 5s

  # === LOKI ===
  # Хранилище логов (аналог Prometheus, но для логов, не метрик)
  loki:
    image: grafana/loki:2.9.7
    container_name: loki
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
    volumes:
      - ./loki/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "127.0.0.1:3100:3100"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3100/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  # === PROMTAIL ===
  # Агент для сбора логов с хоста и Docker-контейнеров, отправка в Loki
  promtail:
    image: grafana/promtail:2.9.7
    container_name: promtail
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.2'
    volumes:
      - ./promtail/promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro                           # системные логи
      - /var/lib/docker/containers:/var/lib/docker/containers:ro  # Docker логи
      - /var/run/docker.sock:/var/run/docker.sock:ro   # для docker_sd_configs
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring
    depends_on:
      loki:
        condition: service_healthy

  # === VICTORIAMETRICS ===
  # Долгосрочное хранение метрик (12+ месяцев) через Remote Write
  # Совместим с Prometheus API -> может быть datasource в Grafana
  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.100.0
    container_name: victoriametrics
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
    command:
      - '--storageDataPath=/victoria-metrics-data'
      - '--retentionPeriod=12'           # 12 месяцев хранения
      - '--httpListenAddr=:8428'
      - '--selfScrapeInterval=30s'       # мониторинг себя
    volumes:
      - vm_data:/victoria-metrics-data
    ports:
      - "127.0.0.1:8428:8428"
    networks:
      - monitoring
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8428/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

---

## Команды для работы

```bash
# Запустить весь стек
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи конкретного сервиса
docker compose logs -f prometheus
docker compose logs -f alertmanager

# Перезагрузить конфиг Prometheus без остановки
curl -X POST http://localhost:9090/-/reload

# Перезагрузить конфиг Alertmanager без остановки
curl -X POST http://localhost:9093/-/reload

# Остановить весь стек
docker compose down

# Остановить с удалением томов (ОСТОРОЖНО: потеря данных!)
docker compose down -v

# Посмотреть сколько места занимают метрики
docker exec prometheus du -sh /prometheus

# Проверить что все таргеты в UP
curl -s http://localhost:9090/api/v1/targets | jq '.data.targets[] | {job, health}'
```
