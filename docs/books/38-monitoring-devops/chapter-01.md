# Глава 1: Быстрый старт — весь стек за 15 минут

## Что вы узнаете

- как поднять Prometheus + Grafana + Node Exporter + Alertmanager через Docker Compose;
- как установить компоненты через systemd если Docker недоступен;
- как войти в Grafana и увидеть первые метрики;
- как импортировать готовый дашборд из Grafana Community.

Цель главы: через 15 минут после её начала у вас работающий мониторинг. Всё остальное в книге — детали поверх этого фундамента.

---

## Минимальный docker-compose.yml

Создайте директорию проекта и файл `docker-compose.yml`. Каждая строка прокомментирована — вы должны понимать что делает каждый параметр.

```yaml
version: '3.8'

volumes:
  prometheus_data: {}   # данные Prometheus (метрики)
  grafana_data: {}      # данные Grafana (дашборды, настройки)
  alertmanager_data: {} # данные Alertmanager (silences, статусы)

networks:
  monitoring:           # изолированная сеть для компонентов

services:

  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'   # хранить 15 дней метрик
      - '--web.enable-lifecycle'               # reload конфига без рестарта
    ports:
      - "127.0.0.1:9090:9090"   # только localhost, не наружу
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:10.4.0
    container_name: grafana
    restart: unless-stopped
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    ports:
      - "3000:3000"
    networks:
      - monitoring

  node_exporter:
    image: prom/node-exporter:v1.8.0
    container_name: node_exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|run)($$|/)'
    ports:
      - "127.0.0.1:9100:9100"
    networks:
      - monitoring
    pid: host   # нужен для метрик процессов хоста

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager
    restart: unless-stopped
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "127.0.0.1:9093:9093"
    networks:
      - monitoring
```

> ☠️ **Осторожно:** Порты привязаны к `127.0.0.1` — сервисы доступны только с localhost. Если открыть `0.0.0.0:9090` или `0.0.0.0:3000`, любой в сети сможет читать ваши метрики и менять дашборды. В production всегда используйте reverse proxy с аутентификацией (nginx + htpasswd или Traefik с basic auth).

---

## Установка через systemd (без Docker)

Docker есть не везде. На VPS или bare-metal сервере Prometheus, Node Exporter и Alertmanager можно установить напрямую через systemd. Это проще для одного сервера — не нужен Docker, меньше слоёв абстракции.

Trade-offs: Docker даёт изоляцию и упрощает обновление (сменил image — перезапустил). Systemd — меньше накладных расходов, проще интеграция с хостом (логи в journald, мониторинг через systemd). Для одного сервера systemd проще.

### Prometheus

```bash
# Загрузить и распаковать
wget https://github.com/prometheus/prometheus/releases/download/v2.51.0/prometheus-2.51.0.linux-amd64.tar.gz
tar xzf prometheus-2.51.0.linux-amd64.tar.gz
sudo mv prometheus-2.51.0.linux-amd64 /opt/prometheus
sudo useradd --no-create-home --shell /bin/false prometheus
sudo chown -R prometheus:prometheus /opt/prometheus
```

```ini
# /etc/systemd/system/prometheus.service
[Unit]
Description=Prometheus
After=network.target

[Service]
User=prometheus
ExecStart=/opt/prometheus/prometheus \
  --config.file=/opt/prometheus/prometheus.yml \
  --storage.tsdb.path=/opt/prometheus/data \
  --web.enable-lifecycle
Restart=always

[Install]
WantedBy=multi-user.target
```

### Node Exporter

```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.8.0/node_exporter-1.8.0.linux-amd64.tar.gz
tar xzf node_exporter-1.8.0.linux-amd64.tar.gz
sudo mv node_exporter-1.8.0.linux-amd64 /opt/node_exporter
sudo useradd --no-create-home --shell /bin/false node_exporter
sudo chown -R node_exporter:node_exporter /opt/node_exporter
```

```ini
# /etc/systemd/system/node_exporter.service
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
ExecStart=/opt/node_exporter/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
```

### Grafana

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y grafana
```

```ini
# /etc/systemd/system/grafana-server.service (создаётся при установке)
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

### Alertmanager

```bash
wget https://github.com/prometheus/alertmanager/releases/download/v0.27.0/alertmanager-0.27.0.linux-amd64.tar.gz
tar xzf alertmanager-0.27.0.linux-amd64.tar.gz
sudo mv alertmanager-0.27.0.linux-amd64 /opt/alertmanager
sudo useradd --no-create-home --shell /bin/false alertmanager
sudo chown -R alertmanager:alertmanager /opt/alertmanager
```

```ini
# /etc/systemd/system/alertmanager.service
[Unit]
Description=Alertmanager
After=network.target

[Service]
User=alertmanager
ExecStart=/opt/alertmanager/alertmanager \
  --config.file=/opt/alertmanager/alertmanager.yml \
  --storage.path=/opt/alertmanager/data
Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable prometheus node_exporter grafana-server alertmanager
sudo systemctl start prometheus node_exporter grafana-server alertmanager
```

В systemd-версии Node Exporter указывайте `localhost:9100` в `prometheus.yml` (он работает на хосте, а не в Docker-сети).

---

## Минимальный prometheus.yml

Создайте файл `prometheus/prometheus.yml`:

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s      # опрашивать таргеты каждые 15 секунд
  evaluation_interval: 15s  # вычислять правила алертов каждые 15 секунд

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

# Правила алертинга (добавим в главе 8)
rule_files:
  - '/etc/prometheus/rules/*.yml'

scrape_configs:
  # Prometheus сам себя мониторит
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Метрики сервера через Node Exporter
  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
```

Если используете systemd — замените `node_exporter:9100` на `localhost:9100`, потому что Node Exporter работает на хосте, а не в Docker-контейнере.

---

## Запуск и первый вход

```bash
# Создать структуру директорий
mkdir -p prometheus/rules alertmanager grafana/provisioning

# Запустить стек
docker compose up -d

# Проверить что контейнеры запущены
docker compose ps

# Посмотреть логи если что-то пошло не так
docker compose logs prometheus
docker compose logs node_exporter
```

После запуска откройте в браузере:

- **Grafana:** `http://localhost:3000` — логин `admin`, пароль `admin`. После первого входа Grafana попросит сменить пароль. Для тестового стенда можно оставить `admin/admin`.
- **Prometheus UI:** `http://localhost:9090` — страница со встроенным query browser и статусом таргетов.
- **Alertmanager UI:** `http://localhost:9093` — показывает текущие алерты и silences.

Проверка что Prometheus видит таргеты:

```bash
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep -E '"health"|"scrapeUrl"'
```

Или откройте `http://localhost:9090/targets` в браузере. Оба таргета (`prometheus` и `node`) должны быть в статусе UP.

> ☠️ **Осторожно:** После `docker compose down -v` данные Prometheus и Grafana будут удалены вместе с volumes. Никогда не используйте `-v` если на сервере есть production-метрики. Для остановки без потери данных: `docker compose down` (без `-v`).

---

## Импорт готового дашборда

Grafana Community Dashboards — это каталог готовых дашбордов по адресу `grafana.com/grafana/dashboards`. Самый популярный для Node Exporter — дашборд 1860 («Node Exporter Full»). Он показывает CPU, память, диск, сеть, load average, uptime и десятки других метрик сервера.

Пошаговая инструкция (словами, без картинок):

```text
1. Откройте Grafana в браузере: http://localhost:3000
2. Войдите: admin / admin → смените пароль
3. В левом меню нажмите Dashboards (четыре квадрата)
4. В выпадающем меню выберите Import
5. В поле "Import via grafana.com" введите: 1860
   (Node Exporter Full — дашборд с метриками сервера)
6. Нажмите Load
7. В выпадающем списке "Prometheus" выберите datasource Prometheus
   (если он там один — он выбран по умолчанию)
8. Нажмите Import
9. Откроется дашборд с метриками вашего сервера
```

Если дашборд пустой — проверьте что в левом верхнем углу выбран правильный datasource (Prometheus) и выбран хост в выпадающем списке `$host` и `$instance`.

Если datasource Prometheus не появился — добавьте его вручную:

```text
1. Левое меню → Connections → Data Sources → Add data source
2. Выберите Prometheus
3. В поле URL введите: http://prometheus:9090
4. Нажмите Save & Test
5. Внизу должно появиться "Successfully queried the Prometheus API"
```

Grafana автоматически подхватит datasource если вы настроили provisioning. Для быстрого старта достаточно добавить datasource через UI.

---

## Типичные ошибки

- **Prometheus не видит node_exporter.** Причина: в `prometheus.yml` указан `localhost:9100`, а Node Exporter запущен в контейнере с другим именем. В Docker Compose сервисы общаются по имени контейнера: `node_exporter:9100`. Если запускаете через systemd — используйте `localhost:9100`.

- **Grafana не загружает метрики.** Data source не настроен или неверный URL. Prometheus доступен для Grafana по адресу `http://prometheus:9090` (внутри Docker-сети). Если Grafana на хосте, а Prometheus в Docker — используйте `http://localhost:9090`.

- **Порт 3000 занят.** Другой сервис (например, настроечная панель хостинга) уже слушает 3000. Поменяйте внешний порт в `docker-compose.yml`: `"3001:3000"`. Grafana будет доступна по `http://localhost:3001`.

- **Node Exporter показывает только метрики контейнера, не хоста.** Если запустить Node Exporter без `pid: host` и монтирования `/proc`, `/sys`, `/rootfs` — он увидит только свою cgroup. Всегда монтируйте эти директории и используйте `pid: host`.

- **Grafana просит сменить пароль при каждом входе.** Если вы не меняли пароль после первого входа — это норма. Пароль хранится в volume `grafana_data`. При удалении volume пароль сбрасывается на `admin/admin`. Используйте provisioning для фиксации пароля в конфиге.

---

## Чек-лист для самопроверки

- [ ] Весь стек запущен: `docker compose ps` показывает состояние Up для всех четырёх контейнеров.
- [ ] Вижу метрики в Prometheus UI: `http://localhost:9090/targets` — оба таргета (prometheus, node) в статусе UP.
- [ ] Вижу дашборд Node Exporter Full (ID 1860) в Grafana: графики CPU, памяти, диска и сети отображают данные.
- [ ] Могу войти в Grafana (`admin/admin`) и Prometheus UI.
- [ ] Знаю как перезапустить стек без потери данных: `docker compose restart` (не `down -v`).

---

## Попробуйте сами

1. Запустите стек. Откройте Prometheus UI (http://localhost:9090) → Status → Targets. Все ли таргеты в состоянии UP? Если нет — что показывает поле Error? Исправьте ошибку.

2. В Prometheus UI откройте вкладку Graph, введите запрос `up` и нажмите Execute. Что показывает значение 1? А если бы было 0? (1 = таргет жив и отвечает, 0 = таргет недоступен.)

3. Импортируйте дашборд 1860 (Node Exporter Full). Найдите панели: CPU Busy, Memory Available, Disk I/O, Network Traffic. Какие значения показывают сейчас? Запустите ресурсоёмкий процесс (`stress --cpu 2 --timeout 30`) — как изменились графики через 15 секунд?

4. Остановите контейнер Node Exporter: `docker compose stop node_exporter`. Откройте http://localhost:9090/targets через 30 секунд. Таргет `node` перешёл в DOWN? Запустите обратно: `docker compose start node_exporter`. Таргет вернулся в UP?
