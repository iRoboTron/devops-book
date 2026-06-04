# Приложение D: Установка через systemd (без Docker)

Полные systemd unit-файлы для компонентов мониторинга. Для серверов где Docker не установлен или нежелателен.

---

## Структура установки

```text
/opt/
├── prometheus/          # Prometheus + конфиги
│   ├── prometheus
│   ├── prometheus.yml
│   ├── rules/
│   └── data/
├── grafana/             # Grafana
│   └── data/
├── alertmanager/        # Alertmanager
│   ├── alertmanager
│   ├── alertmanager.yml
│   └── templates/
└── node_exporter/       # Node Exporter
    ├── node_exporter
    └── textfile_collector/

/etc/systemd/system/
├── prometheus.service
├── grafana-server.service
├── alertmanager.service
└── node_exporter.service
```

---

## Установка бинарников

### Prometheus

```bash
# Скачать и распаковать
wget https://github.com/prometheus/prometheus/releases/download/v2.51.0/prometheus-2.51.0.linux-amd64.tar.gz
tar xzf prometheus-2.51.0.linux-amd64.tar.gz

# Создать пользователя (без домашней директории, без shell)
sudo useradd --no-create-home --shell /bin/false prometheus

# Скопировать бинарник и конфиги
sudo mv prometheus-2.51.0.linux-amd64 /opt/prometheus
sudo chown -R prometheus:prometheus /opt/prometheus

# Создать директорию для правил
sudo mkdir -p /opt/prometheus/rules
sudo chown prometheus:prometheus /opt/prometheus/rules

# Удалить архив
rm prometheus-2.51.0.linux-amd64.tar.gz
```

### Grafana

```bash
# Установка через apt (рекомендуется для Grafana)
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y grafana

# Или ручная установка (любой дистрибутив)
wget https://dl.grafana.com/oss/release/grafana-10.4.0.linux-amd64.tar.gz
tar xzf grafana-10.4.0.linux-amd64.tar.gz
sudo mv grafana-10.4.0 /opt/grafana
sudo useradd --no-create-home --shell /bin/false grafana
sudo chown -R grafana:grafana /opt/grafana
```

### Alertmanager

```bash
wget https://github.com/prometheus/alertmanager/releases/download/v0.27.0/alertmanager-0.27.0.linux-amd64.tar.gz
tar xzf alertmanager-0.27.0.linux-amd64.tar.gz
sudo useradd --no-create-home --shell /bin/false alertmanager
sudo mv alertmanager-0.27.0.linux-amd64 /opt/alertmanager
sudo chown -R alertmanager:alertmanager /opt/alertmanager
rm alertmanager-0.27.0.linux-amd64.tar.gz
```

### Node Exporter

```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.8.0/node_exporter-1.8.0.linux-amd64.tar.gz
tar xzf node_exporter-1.8.0.linux-amd64.tar.gz
sudo useradd --no-create-home --shell /bin/false node_exporter
sudo mv node_exporter-1.8.0.linux-amd64 /opt/node_exporter
sudo chown -R node_exporter:node_exporter /opt/node_exporter
rm node_exporter-1.8.0.linux-amd64.tar.gz
```

### Дополнительные экспортеры

```bash
# postgres_exporter
wget https://github.com/prometheus-community/postgres_exporter/releases/download/v0.15.0/postgres_exporter-0.15.0.linux-amd64.tar.gz
tar xzf postgres_exporter-0.15.0.linux-amd64.tar.gz
sudo useradd --no-create-home --shell /bin/false postgres_exporter
sudo mv postgres_exporter-0.15.0.linux-amd64 /opt/postgres_exporter
sudo chown -R postgres_exporter:postgres_exporter /opt/postgres_exporter

# blackbox_exporter
wget https://github.com/prometheus/blackbox_exporter/releases/download/v0.24.0/blackbox_exporter-0.24.0.linux-amd64.tar.gz
tar xzf blackbox_exporter-0.24.0.linux-amd64.tar.gz
sudo useradd --no-create-home --shell /bin/false blackbox_exporter
sudo mv blackbox_exporter-0.24.0.linux-amd64 /opt/blackbox_exporter
sudo chown -R blackbox_exporter:blackbox_exporter /opt/blackbox_exporter
```

---

## Systemd unit-файлы

### prometheus.service

```ini
# /etc/systemd/system/prometheus.service
[Unit]
Description=Prometheus — система мониторинга и база временных рядов
Documentation=https://prometheus.io/docs/introduction/overview/
After=network.target
Wants=network-online.target

[Service]
# Пользователь без привилегий
User=prometheus
Group=prometheus

# Тип: процесс запускается и остаётся в памяти
Type=simple

# Путь к бинарнику и аргументы
ExecStart=/opt/prometheus/prometheus \
  --config.file=/opt/prometheus/prometheus.yml \
  --storage.tsdb.path=/opt/prometheus/data \
  --storage.tsdb.retention.time=15d \
  --storage.tsdb.retention.size=10GB \
  --web.enable-lifecycle \
  --web.console.libraries=/opt/prometheus/console_libraries \
  --web.console.templates=/opt/prometheus/consoles

# Рабочая директория
WorkingDirectory=/opt/prometheus

# Политика рестарта
Restart=always
RestartSec=5

# Ограничения безопасности
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes

# Лимиты
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### grafana-server.service

```ini
# /etc/systemd/system/grafana-server.service
# Для установки через apt: systemctl enable grafana-server (уже есть)
# Для ручной установки:
[Unit]
Description=Grafana — визуализация метрик и дашборды
Documentation=https://grafana.com/docs/
After=network.target
Wants=network-online.target

[Service]
User=grafana
Group=grafana
Type=simple

# Grafana поставляется со своим бинарником grafana-server в /opt/grafana/bin/
ExecStart=/opt/grafana/bin/grafana-server \
  --homepath=/opt/grafana \
  --config=/opt/grafana/conf/defaults.ini \
  --packaging=unknown

# Путь к данным (переопределяет defaults.ini)
Environment=GF_PATHS_DATA=/opt/grafana/data
Environment=GF_PATHS_LOGS=/opt/grafana/logs
Environment=GF_PATHS_PLUGINS=/opt/grafana/plugins
Environment=GF_PATHS_PROVISIONING=/opt/grafana/provisioning
Environment=GF_SECURITY_ADMIN_USER=admin
Environment=GF_SECURITY_ADMIN_PASSWORD=admin
Environment=GF_USERS_ALLOW_SIGN_UP=false

WorkingDirectory=/opt/grafana

Restart=always
RestartSec=10

ProtectSystem=full
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes

LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### alertmanager.service

```ini
# /etc/systemd/system/alertmanager.service
[Unit]
Description=Alertmanager — маршрутизация и отправка алертов
Documentation=https://prometheus.io/docs/alerting/latest/alertmanager/
After=network.target
Wants=network-online.target

[Service]
User=alertmanager
Group=alertmanager
Type=simple

ExecStart=/opt/alertmanager/alertmanager \
  --config.file=/opt/alertmanager/alertmanager.yml \
  --storage.path=/opt/alertmanager/data \
  --log.level=info

WorkingDirectory=/opt/alertmanager

Restart=always
RestartSec=5

ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes

LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### node_exporter.service

```ini
# /etc/systemd/system/node_exporter.service
[Unit]
Description=Node Exporter — метрики сервера (CPU, память, диск, сеть)
Documentation=https://prometheus.io/docs/guides/node-exporter/
After=network.target
Wants=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple

ExecStart=/opt/node_exporter/node_exporter \
  --path.procfs=/proc \
  --path.sysfs=/sys \
  --path.rootfs=/ \
  --collector.filesystem.mount-points-exclude=^/(sys|proc|dev|run)($$|/) \
  --collector.netclass.ignored-devices=^(veth.*|docker.*|br-.*|lo)$ \
  --web.listen-address=:9100 \
  --log.level=info

# Node Exporter требует доступа к /proc, /sys, /
# Поэтому ProtectSystem выключен
ProtectSystem=false
ProtectHome=false
PrivateTmp=yes
NoNewPrivileges=yes

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### postgres_exporter.service (дополнительно)

```ini
# /etc/systemd/system/postgres_exporter.service
[Unit]
Description=PostgreSQL Exporter — метрики БД
After=network.target
Wants=network-online.target

[Service]
User=postgres_exporter
Group=postgres_exporter
Type=simple

Environment=DATA_SOURCE_NAME=postgresql://monitoring:MonitorPass@localhost:5432/postgres?sslmode=disable
ExecStart=/opt/postgres_exporter/postgres_exporter \
  --web.listen-address=:9187

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### blackbox_exporter.service (дополнительно)

```ini
# /etc/systemd/system/blackbox_exporter.service
[Unit]
Description=Blackbox Exporter — проверка доступности URL, TCP, ICMP
After=network.target

[Service]
User=blackbox_exporter
Group=blackbox_exporter
Type=simple

ExecStart=/opt/blackbox_exporter/blackbox_exporter \
  --config.file=/opt/blackbox_exporter/blackbox.yml \
  --web.listen-address=:9115

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Запуск и управление

```bash
# Перечитать systemd unit-файлы
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable prometheus
sudo systemctl enable grafana-server
sudo systemctl enable alertmanager
sudo systemctl enable node_exporter

# Запустить компоненты
sudo systemctl start prometheus
sudo systemctl start grafana-server
sudo systemctl start alertmanager
sudo systemctl start node_exporter

# Проверить статус
sudo systemctl status prometheus
sudo systemctl status grafana-server

# Проверить что слушают порты
sudo ss -tlnp | grep -E '9090|3000|9093|9100'

# Посмотреть логи
sudo journalctl -u prometheus -n 50 -f
sudo journalctl -u grafana-server -n 50 -f

# Перезагрузить конфиг Prometheus
sudo systemctl reload prometheus    # если настроен ExecReload
# или
kill -HUP $(pidof prometheus)

# Остановить
sudo systemctl stop node_exporter

# Отключить автозапуск
sudo systemctl disable node_exporter
```

---

## Docker vs systemd: Trade-offs

```text
Критерий              | Docker                                 | systemd
----------------------|----------------------------------------|----------------------------------------
Изоляция              | Полная: свои network, pid, mount       | Процессы на хосте, разделяют порты
                      | namespace. Контейнер изолирован.       | Любой сервис видит все процессы.
----------------------|----------------------------------------|----------------------------------------
Установка             | docker compose up -d (одна команда)    | 4 команды wget + tar + useradd + cp
                      | + создать файлы конфигов              | + создать service файлы + daemon-reload
----------------------|----------------------------------------|----------------------------------------
Обновление            | docker compose pull <service> && down && up -d  | wget + tar + systemctl restart
                      | Автоматически через watchtower         | Вручную, нужно следить за версиями
----------------------|----------------------------------------|----------------------------------------
Ресурсы               | Небольшие накладные: Docker engine     | Минимальные: процесс напрямую на хосте
                      | + контейнер (~50MB на сервис)         | (~5MB на бинарник)
----------------------|----------------------------------------|----------------------------------------
Сеть                  | Контейнеры общаются по имени в сети    | localhost или IP, нужно знать порты
                      | Docker DNS (prometheus:9090)           | prometheus.yml: localhost:9100
----------------------|----------------------------------------|----------------------------------------
Healthcheck           | healthcheck в docker-compose.yml       | systemd сам перезапускает упавший
                      | + restart: unless-stopped              | процесс (Restart=always)
----------------------|----------------------------------------|----------------------------------------
Логи                  | docker logs <service>                  | journalctl -u <service>
                      | docker compose logs -f                  | journalctl -u <service> -f
----------------------|----------------------------------------|----------------------------------------
Безопасность          | Изоляция контейнера от хоста           | NoNewPrivileges=yes, ProtectSystem=
                      | Дополнительная изоляция через seccomp  | но процессы разделяют ядро с хостом
----------------------|----------------------------------------|----------------------------------------
Сложность             | Нужен установленный Docker             | Только бинарник + systemd (есть везде)
                      | Нужен опыт работы с Docker Compose     | Минимальные требования к системе
```

### Когда выбирать Docker

- Docker уже установлен и используется на сервере
- Хочется изоляции между компонентами мониторинга
- Нужно быстро развернуть и обновлять
- Несколько серверов — одинаковый docker-compose везде
- Есть watchtower для автообновления

### Когда выбирать systemd

- На сервере нет Docker и ставить его не планируется
- Минимальный VPS (512MB RAM) — Docker engine ест ресурсы
- Нужна максимальная производительность (diskg IO метрики точнее без прослойки)
- Используется конфигурационный менеджер (Ansible, Puppet) — systemd units удобнее
- Требования безопасности: процессы не должны иметь доступ к Docker socket

### Компромиссный вариант

Node Exporter и cAdvisor на хосте (systemd) для точных метрик сервера и Docker.
Prometheus, Grafana, Alertmanager — в Docker для простоты управления.
Loki + Promtail — на хосте (systemd), чтобы логи собирались даже когда Docker упал.

```text
Схема: гибрид systemd + Docker

Хост (systemd):
  Node Exporter :9100   — точные метрики CPU/диска
  Promtail       :9080   — сбор логов (работает если Docker упал)

Docker Compose:
  Prometheus     :9090   — сбор метрик
  Grafana        :3000   — дашборды
  Alertmanager   :9093   — алерты
  Loki           :3100   — хранение логов
  Pushgateway    :9091   — batch jobs
```
