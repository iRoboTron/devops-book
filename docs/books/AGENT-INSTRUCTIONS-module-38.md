# Инструкция для ИИ-агента: Модуль 38 — Мониторинг с нуля

> **Роль агента:** Ты — технический писатель и DevOps-инженер с практическим опытом построения систем мониторинга. Пишешь конкретно, с реальными конфигами и командами. Объясняешь не только «как настроить», но и «что это показывает» и «как читать». Честно говоришь когда что-то избыточно для малых команд.

> **Это Модуль 38, книга части 4 "Прочее". Уровень 1.0 — без Kubernetes.**
> Книга 12 (Monitoring DevOps) остаётся уровнем 2.0 — K8s-мониторинг.
> Предварительные требования: книга 03 (Docker), книга 35 (Сети).
> Читатель умеет работать с Docker Compose, но мониторинг у него — «смотрим в логи когда что-то упало».

---

## Контекст проекта

Читатель — DevOps-инженер или разработчик у которого «мониторинга нет»:

- О проблеме узнаёт от пользователей или когда сервис уже упал.
- Логи смотрит через `docker logs` или `journalctl` вручную по запросу.
- «Мониторинг» — это `uptime` в Telegram раз в 5 минут.
- Не знает сколько RAM / CPU / диска потребляет каждый сервис.
- Не понимает разницу между метрикой, логом и трейсом.
- Слышал про Prometheus и Grafana, но «не разбирался».
- Не знает что такое алерт и как его настроить чтобы не было ложных срабатываний.

**Что он хочет после книги:**
Поднять Prometheus + Grafana + Alertmanager за один вечер. Видеть на дашборде что происходит с серверами и сервисами. Получать уведомление в Telegram когда что-то сломалось — и не получать их когда всё нормально. Уметь читать метрики и понимать что они означают.

---

## Что за книга

**Название:** "Мониторинг с нуля: Prometheus, Grafana и Alertmanager без Kubernetes"

**Каталог:** `38-monitoring-devops`

**Место в курсе:** Книга 38, часть 4 "Прочее". Уровень 1.0. Книга 12 — уровень 2.0 (K8s).

**Версии ПО:** Prometheus 2.x, Grafana 10.x, Alertmanager 0.27+, Node Exporter 1.8+. Указывать когда что-то изменилось между версиями.

**Объём:** 130–160 страниц.

**Формат файлов:** каждая глава — `chapter-XX.md`, приложения — `appendix-a.md`, `appendix-b.md`, `appendix-c.md`. Оглавление — `book.md`.

**Стиль:**
- Язык практика, не теоретика. Не «observability pipeline», а «как узнать что сервер кончается память».
- Каждая глава: «Что вы узнаете» → тело → «Типичные ошибки» → «Чек-лист» → «Попробуйте сами».
- Конфиги — полные, рабочие, с комментарием каждой строки.
- Mermaid-диаграммы для архитектур и flows, ASCII для топологий.
- Маркировка: `> ☠️ **Осторожно:**` для деструктивных операций.
- Разделять: что в `prometheus.yml`, что в `docker-compose.yml`, что в Grafana UI.

---

## Правило маркировки опасных операций

```markdown
> ☠️ **Осторожно:** [что именно ломается и почему]
```

Применять к:
- `--storage.tsdb.retention.time` слишком мало — потеря исторических данных
- удаление `data/` директории Prometheus — потеря всех метрик
- `alertmanager` без `inhibit_rules` — шторм алертов при одном инциденте
- открытие Grafana/Prometheus наружу без аутентификации

---

## Антипаттерны подачи

**Плохо:** начинать с теории «что такое observability, три столпа: metrics, logs, traces».
**Хорошо:** сразу показать работающий `docker-compose.yml` — через 10 минут читатель видит дашборд.

**Плохо:** объяснять все функции PromQL на 4 страницах.
**Хорошо:** дать 10 конкретных запросов которые отвечают на реальные вопросы (сколько памяти, какой upttime, сколько ошибок).

**Плохо:** «настройте Alertmanager под ваши нужды».
**Хорошо:** рабочий конфиг с Telegram и email, объяснить каждую строку.

**Плохо:** показывать Grafana без объяснения как читать графики.
**Хорошо:** для каждого дашборда объяснить: что показывает каждая панель, какое значение нормальное, какое тревожное.

---

## Правило: визуализация — не опционально

- **ASCII-схемы** — архитектура стека (что с чем общается, pull vs push).
- **Mermaid flowchart** — алгоритм алертинга, routing в Alertmanager.
- **Таблицы** — сравнение exporters, типы метрик, функции PromQL.
- **Скриншоты словами** — описывать UI Grafana текстом («в левом меню → Dashboards → Import»), не полагаться на картинки.

---

## Обязательные схемы

**Схема 1 — Архитектура стека мониторинга** (Глава 0):

```text
                    Pull-модель: Prometheus сам опрашивает таргеты
                    ┌─────────────────────────────────────────────┐
                    │                                             │
  node_exporter:9100 ◄──┐                                        │
  cadvisor:8080     ◄──┤── Prometheus:9090 ──► Alertmanager:9093 │
  app /metrics      ◄──┤      │                      │           │
  postgres_exporter ◄──┘      │                      ▼           │
                              │              Telegram / Email     │
                              ▼                                   │
                         Grafana:3000                             │
                         (визуализация)                           │
                                                                  │
  Loki:3100 ◄── promtail (push-модель для логов)                 │
                    └─────────────────────────────────────────────┘
```
Разместить: начало главы 0.

**Схема 2 — Pull vs Push модели** (Глава 1):

```text
Pull (Prometheus):
Prometheus ──► GET /metrics ──► Exporter
«Prometheus сам приходит за метриками по расписанию»
+ Prometheus знает что таргет недоступен (нет ответа = алерт)
- Нужен сетевой доступ от Prometheus к каждому таргету

Push (Pushgateway / Loki / StatsD):
Приложение ──► POST метрик ──► Приёмник
«Приложение само отправляет метрики»
+ Подходит для batch jobs (нет постоянного endpoint)
- Prometheus не знает упало ли приложение (оно просто перестало пушить)
```
Разместить: секция "Как Prometheus собирает метрики" в главе 1.

**Схема 3 — Жизненный цикл алерта** (Глава 8):

```mermaid
flowchart LR
    A[Prometheus\nвычисляет правило] --> B{Условие\nвыполнено?}
    B -->|Нет| A
    B -->|Да| C[Статус: PENDING\nждём for: 5m]
    C --> D{Прошло\nfor: 5m?}
    D -->|Нет| C
    D -->|Да| E[Статус: FIRING\nотправить в Alertmanager]
    E --> F[Alertmanager\nроутинг по labels]
    F --> G{Есть\ninhibition?}
    G -->|Да| H[Подавить алерт]
    G -->|Нет| I{Есть\nsilence?}
    I -->|Да| H
    I -->|Нет| J[Отправить\nуведомление]
    J --> K[Telegram / Email\n/ PagerDuty]
```
Разместить: начало главы 8.

**Схема 4 — Типы метрик Prometheus** (Глава 2):

```text
Тип           Описание                         Пример
────────────────────────────────────────────────────────────────────
Counter       Только растёт. Сбрасывается      http_requests_total
              при рестарте.                    errors_total
              → используй rate() для скорости

Gauge         Текущее значение. Растёт и       memory_used_bytes
              убывает.                         cpu_usage_percent
              → используй напрямую             active_connections

Histogram     Распределение значений.          http_request_duration_seconds
              _bucket, _sum, _count.           (99й перцентиль задержки)
              → используй histogram_quantile()

Summary       Перцентили на стороне клиента.   go_gc_duration_seconds
              Менее гибкий чем Histogram.
              → использовать редко, prefer Histogram
```
Разместить: секция "Типы метрик" в главе 2.

**Схема 5 — Routing в Alertmanager** (Глава 8):

```text
Алерт приходит из Prometheus
        │
        ▼
   route (корневой)
   receiver: telegram-general
        │
        ├── match: severity=critical
        │   receiver: pagerduty + telegram-critical
        │
        ├── match: team=backend
        │   receiver: telegram-backend
        │
        └── match: alertname=Watchdog
            receiver: blackhole (игнорировать)
```
Разместить: секция "Routing" в главе 8.

---

## Таблица объёмов глав

| Глава | Тема | Страниц |
|-------|------|---------|
| 0 | Зачем мониторинг и как устроен стек | 5–6 |
| 1 | Быстрый старт: весь стек за 15 минут | 8–10 |
| 2 | Prometheus: концепции, метрики, конфиг | 10–12 |
| 3 | Node Exporter: метрики сервера | 8–10 |
| 4 | PromQL: 20 запросов для реальных задач | 10–12 |
| 5 | Grafana: дашборды, панели, переменные | 12–14 |
| 6 | cAdvisor и Docker-метрики | 7–8 |
| 7 | Exporters: PostgreSQL, Nginx, Redis, Blackbox | 10–12 |
| 8 | Alertmanager: правила, routing, Telegram | 12–14 |
| 9 | Loki + Promtail: логи в Grafana | 10–12 |
| 10 | Pushgateway: метрики для batch jobs | 5–6 |
| 11 | Масштабирование и long-term storage | 6–7 |
| 12 | Диагностика: что делать когда мониторинг сломан | 6–7 |
| Приложения A–C | | 8–10 |

Общий объём: 130–160 страниц.

---

## Структура книги — детальное ТЗ по главам

---

### Глава 0: Зачем мониторинг и как устроен стек

**Что вы узнаете:**
- почему «смотреть в логи когда упало» — не мониторинг;
- разницу между метриками, логами и трейсами (один абзац, без теории);
- из каких компонентов состоит стек и как они связаны;
- что будет результатом после прохождения книги.

**Цель:** читатель понимает зачем каждый компонент и чего ожидать. Мотивация, не теория.

**Темы:**

Раздел "Три вопроса которые решает мониторинг":
```text
1. Что сломалось и когда?
   Без мониторинга: узнал от пользователей через 20 минут
   С мониторингом: алерт через 1 минуту, точный момент на графике

2. Почему сломалось?
   Без мониторинга: смотришь в логи, гадаешь
   С мониторингом: видишь на графике как память росла 2 часа до падения

3. Всё ли нормально прямо сейчас?
   Без мониторинга: не знаешь пока не сломается
   С мониторингом: дашборд показывает тренды заранее
```

Разместить Схему 1 (архитектура стека) и объяснить каждый компонент одним предложением:
```text
Prometheus    — база данных временных рядов + сборщик метрик
Node Exporter — агент на сервере, экспортирует метрики ОС
cAdvisor      — экспортирует метрики Docker-контейнеров
Grafana       — визуализация: дашборды, графики, панели
Alertmanager  — маршрутизация и отправка уведомлений
Loki          — хранилище логов (как Prometheus но для логов)
Promtail      — агент для сбора логов (как Node Exporter но для логов)
```

Раздел "Метрики, логи, трейсы — один абзац":
Объяснить без глубины: метрика — числовое значение во времени (CPU = 75%), лог — текстовое событие с временной меткой, трейс — путь запроса через сервисы. В этой книге: метрики (Prometheus/Grafana) + логи (Loki). Трейсы — для микросервисов, в книгу не входят.

Раздел "Что получишь после книги":
Конкретно: работающий docker-compose стек на любом Linux-сервере. Дашборды с метриками серверов и сервисов. Алерты в Telegram. Логи в Grafana. Умение добавить новый сервис в мониторинг за 15 минут.

**Типичные ошибки:**
- Думать что мониторинг нужен только большим командам. Одному человеку с одним сервером — нужен не меньше.
- Откладывать «пока не будет время» — настраивается за вечер (Глава 1 докажет это).

**Чек-лист для самопроверки:**
- [ ] Понимаю зачем каждый компонент стека (7 строк выше)
- [ ] Знаю разницу между метрикой и логом
- [ ] Понимаю что Prometheus работает по pull-модели

**Попробуйте сами:**
1. Зайдите на любой свой сервер. Запустите `top` или `htop`. Посмотрите 5 минут. Что именно вы видите? Что произойдёт с этими данными через час? Вот почему нужен Prometheus.
2. Найдите в своих проектах последний инцидент. Сколько минут прошло до обнаружения? Как узнали? Какие данные помогли бы найти причину быстрее?

---

### Глава 1: Быстрый старт — весь стек за 15 минут

**Что вы узнаете:**
- как поднять Prometheus + Grafana + Node Exporter + Alertmanager через Docker Compose;
- как войти в Grafana и увидеть первые метрики;
- как импортировать готовый дашборд из Grafana Community.

**Цель:** читатель видит работающий мониторинг через 15 минут после начала главы. Всё остальное — детали поверх этого фундамента.

**Темы:**

Раздел "Минимальный docker-compose.yml":
Давать полный рабочий файл с комментарием каждой строки:
```yaml
# docker-compose.yml
version: '3.8'

volumes:
  prometheus_data: {}   # данные Prometheus (метрики)
  grafana_data: {}      # данные Grafana (дашборды, настройки)

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
      GF_SECURITY_ADMIN_PASSWORD: admin   # сменить в production!
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
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    ports:
      - "127.0.0.1:9093:9093"
    networks:
      - monitoring
```

Раздел "Минимальный prometheus.yml":
```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s      # опрашивать каждые 15 секунд
  evaluation_interval: 15s  # вычислять правила каждые 15 секунд

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

# Правила алертинга (добавим позже)
rule_files:
  - '/etc/prometheus/rules/*.yml'

scrape_configs:
  # Prometheus сам себя мониторит
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Метрики сервера
  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
```

Раздел "Запуск и первый вход":
```bash
# Создать структуру директорий
mkdir -p prometheus/rules alertmanager grafana/provisioning

# Запустить
docker compose up -d

# Проверить что всё запустилось
docker compose ps

# Открыть:
# Grafana:    http://localhost:3000  (admin / admin)
# Prometheus: http://localhost:9090
# Alertmanager: http://localhost:9093
```

Раздел "Импорт готового дашборда":
Объяснить пошагово (словами, без картинок):
```text
1. Открыть Grafana: http://localhost:3000
2. Войти: admin / admin → сменить пароль
3. Левое меню → Dashboards → Import
4. В поле "Import via grafana.com" ввести: 1860
   (Node Exporter Full — самый популярный дашборд)
5. Нажать Load
6. В поле "Prometheus" выбрать: Prometheus (default)
7. Нажать Import
8. Открылся дашборд с метриками сервера
```

Объяснить что ID 1860 — это Node Exporter Full дашборд на grafana.com/dashboards. Можно найти другие дашборды по адресу grafana.com/grafana/dashboards.

**Типичные ошибки:**
- Prometheus не видит node_exporter: `node_exporter` — имя контейнера, не `localhost`. Они в одной Docker-сети.
- Grafana не загружает метрики: data source не настроен. Левое меню → Connections → Data sources → Add → Prometheus → URL: `http://prometheus:9090`.
- Порт 3000 занят: другой сервис. Поменять на `3001:3000` в docker-compose.yml.

**Чек-лист для самопроверки:**
- [ ] Весь стек запущен (`docker compose ps` показывает Up для всех)
- [ ] Вижу метрики в Prometheus UI (`http://localhost:9090/targets` — все зелёные)
- [ ] Вижу дашборд Node Exporter Full в Grafana

**Попробуйте сами:**
1. Запустите стек. Откройте Prometheus UI → Status → Targets. Все ли таргеты в состоянии UP? Если нет — что показывает Error?
2. В Prometheus UI введите запрос `up` и нажмите Execute. Что показывает значение 1? А 0?
3. Импортируйте дашборд 1860. Найдите панели: CPU Usage, Memory Usage, Disk I/O. Какие значения показывают прямо сейчас?

---

### Глава 2: Prometheus — концепции, метрики, конфигурация

**Что вы узнаете:**
- как Prometheus хранит данные (time series, labels);
- четыре типа метрик: Counter, Gauge, Histogram, Summary;
- полный синтаксис `prometheus.yml`: `scrape_configs`, `relabeling`;
- как добавить новый таргет и проверить что он работает.

**Цель:** читатель понимает модель данных Prometheus и умеет добавить любой новый таргет в конфиг.

**Темы:**

Разместить Схему 2 (Pull vs Push) в начале главы.

Раздел "Модель данных: time series и labels":
```text
Метрика = имя + набор labels + значение + timestamp

Пример: одна метрика node_cpu_seconds_total имеет много time series:

node_cpu_seconds_total{cpu="0", mode="idle"}        → 12345.6
node_cpu_seconds_total{cpu="0", mode="user"}        → 234.5
node_cpu_seconds_total{cpu="1", mode="idle"}        → 11987.3
node_cpu_seconds_total{cpu="1", mode="iowait"}      → 45.2

Каждая комбинация labels = отдельный time series.
```

Разместить Схему 4 (типы метрик).

Раздел "Формат `/metrics` endpoint":
Показать реальный вывод Node Exporter (первые строки) и объяснить формат:
```text
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 12345.67
node_cpu_seconds_total{cpu="0",mode="user"} 234.56

# HELP node_memory_MemFree_bytes Memory information field MemFree_bytes.
# TYPE node_memory_MemFree_bytes gauge
node_memory_MemFree_bytes 1073741824
```
`# HELP` — описание, `# TYPE` — тип метрики, затем значения.

```bash
# Посмотреть метрики Node Exporter напрямую
curl http://localhost:9100/metrics | head -50

# Найти конкретную метрику
curl -s http://localhost:9100/metrics | grep "^node_memory_MemAvailable"
```

Раздел "Полный `prometheus.yml` с объяснениями":
```yaml
global:
  scrape_interval: 15s       # как часто опрашивать таргеты
  scrape_timeout: 10s        # сколько ждать ответа (< scrape_interval)
  evaluation_interval: 15s   # как часто вычислять recording rules и алерты
  # Метки которые добавляются ко всем метрикам этого Prometheus
  external_labels:
    cluster: 'production'
    region: 'ru-msk'

scrape_configs:
  - job_name: 'myapp'
    metrics_path: '/metrics'   # путь (дефолт /metrics)
    scheme: 'http'             # http или https
    scrape_interval: 30s       # переопределить global для этого job
    static_configs:
      - targets:
          - 'app1:8080'
          - 'app2:8080'
        labels:
          environment: 'production'   # добавить label ко всем метрикам

  # Динамическое обнаружение через file_sd (из файла)
  - job_name: 'dynamic-targets'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s
```

Раздел "Добавить таргет и проверить":
```bash
# 1. Добавить в prometheus.yml
# 2. Перезагрузить конфиг без рестарта:
curl -X POST http://localhost:9090/-/reload

# 3. Проверить в UI:
# http://localhost:9090/targets → найти новый job
# Status: UP = всё работает
# Status: DOWN = ошибка (смотреть поле Error)

# Частые причины DOWN:
# connection refused → сервис не запущен или неверный порт
# context deadline exceeded → таргет не отвечает за scrape_timeout
# 404 → неверный metrics_path
```

Раздел "Файловое обнаружение сервисов (file_sd)":
Объяснить что при добавлении нового сервера не нужно редактировать prometheus.yml:
```json
// /etc/prometheus/targets/servers.json
[
  {
    "targets": ["server1:9100", "server2:9100"],
    "labels": {"env": "prod", "team": "backend"}
  },
  {
    "targets": ["server3:9100"],
    "labels": {"env": "staging"}
  }
]
```
Prometheus обновит таргеты через `refresh_interval` без рестарта.

**Типичные ошибки:**
- `scrape_timeout` больше `scrape_interval` — Prometheus выдаст ошибку при старте.
- Labels с высокой кардинальностью (например, `user_id` или `request_id` как label) — миллионы time series, Prometheus упадёт по памяти. Labels должны иметь небольшое число уникальных значений.
- Не добавить `--web.enable-lifecycle` — `curl -X POST /-/reload` не работает, нужен рестарт.

**Чек-лист для самопроверки:**
- [ ] Понимаю что time series = имя метрики + labels
- [ ] Знаю все 4 типа метрик и когда что использовать
- [ ] Умею добавить таргет в prometheus.yml и проверить в UI
- [ ] Умею перезагрузить конфиг без рестарта через `/-/reload`

**Попробуйте сами:**
1. Откройте `http://localhost:9100/metrics`. Найдите 3 метрики разных типов (counter, gauge). По названию догадайтесь что они измеряют.
2. Добавьте в `prometheus.yml` таргет с несуществующим адресом (`- targets: ['fake:9999']`). Перезагрузите конфиг. Найдите его в Targets — статус DOWN и описание ошибки.
3. Создайте файл `prometheus/targets/extra.json` с одним таргетом. Подождите 30 секунд. Появился ли он в Targets без рестарта Prometheus?

---

### Глава 3: Node Exporter — метрики сервера

**Что вы узнаете:**
- какие метрики экспортирует Node Exporter и что они означают;
- как читать CPU, память, диск и сеть в Prometheus;
- коллекторы: какие включены по умолчанию, какие добавить;
- мониторинг нескольких серверов.

**Цель:** читатель видит дашборд с метриками своего сервера и понимает каждую панель. Знает какие метрики сигнализируют о проблеме.

**Темы:**

Раздел "Ключевые метрики CPU":
```promql
# Использование CPU в процентах (усреднённо по всем ядрам)
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Использование CPU по режимам (user, system, iowait)
rate(node_cpu_seconds_total[5m])

# Высокий iowait — признак узкого места на диске
rate(node_cpu_seconds_total{mode="iowait"}[5m]) > 0.3
```

Объяснить режимы CPU: `idle` — ничего не делает, `user` — код приложений, `system` — ядро, `iowait` — ждёт диска (важно для диагностики).

Раздел "Метрики памяти":
```promql
# Доступная память в байтах (MemAvailable — реально доступно приложениям)
node_memory_MemAvailable_bytes

# Использованная память в %
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Swap использование
(1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes) * 100
```

Объяснить разницу: `MemFree` (физически свободна) vs `MemAvailable` (доступно с учётом кэша). Для мониторинга — всегда `MemAvailable`.

Раздел "Метрики диска":
```promql
# Занято место в %
100 - (node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.lxcfs"} /
       node_filesystem_size_bytes * 100)

# Скорость чтения/записи (байт/сек)
rate(node_disk_read_bytes_total[5m])
rate(node_disk_written_bytes_total[5m])

# IOPS
rate(node_disk_reads_completed_total[5m])
rate(node_disk_writes_completed_total[5m])

# I/O utilization % (время диск занят)
rate(node_disk_io_time_seconds_total[5m]) * 100
```

Раздел "Метрики сети":
```promql
# Трафик входящий/исходящий (байт/сек)
rate(node_network_receive_bytes_total{device!~"lo|veth.*|docker.*|br-.*"}[5m])
rate(node_network_transmit_bytes_total{device!~"lo|veth.*|docker.*|br-.*"}[5m])

# Ошибки сетевого интерфейса
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])
```

Раздел "Системные метрики":
```promql
# Load average (нагрузка системы)
node_load1   # за 1 минуту
node_load5   # за 5 минут
node_load15  # за 15 минут
# Норма: load1 < числа_CPU. Тревога: load1 > числа_CPU * 2

# Количество CPU на сервере
count by(instance) (node_cpu_seconds_total{mode="idle"})

# Uptime сервера
time() - node_boot_time_seconds

# Количество открытых файловых дескрипторов
node_filefd_allocated / node_filefd_maximum * 100
```

Раздел "Мониторинг нескольких серверов":
```yaml
# prometheus.yml — несколько серверов
scrape_configs:
  - job_name: 'nodes'
    static_configs:
      - targets:
          - 'server1:9100'
          - 'server2:9100'
          - 'server3:9100'
```

В Grafana использовать переменную `$instance` для переключения между серверами на дашборде (Глава 5).

**Типичные ошибки:**
- `node_memory_MemFree_bytes` показывает мало — это не значит что память кончается. Linux использует свободную память под кэш. Смотреть `MemAvailable`.
- Load average > числа CPU — не всегда плохо если это I/O wait. Смотреть CPU mode iowait.
- Фильтр сетевых интерфейсов `device!~"lo|veth.*|docker.*"` — без него метрики замусориваются виртуальными интерфейсами Docker.

**Чек-лист для самопроверки:**
- [ ] Знаю PromQL-запросы для CPU, памяти, диска и сети
- [ ] Понимаю разницу между MemFree и MemAvailable
- [ ] Знаю что load average > числа CPU — сигнал проблемы
- [ ] Умею добавить несколько серверов в один job

**Попробуйте сами:**
1. Введите в Prometheus UI: `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`. Какое использование CPU прямо сейчас? Запустите `stress --cpu 2 --timeout 30` — как изменился график через 15 секунд?
2. Введите запрос для доступной памяти. Запустите что-то тяжёлое (`docker pull ubuntu:latest`). Как изменилась память?
3. Найдите метрики диска. Запустите `dd if=/dev/zero of=/tmp/test bs=1M count=500` — видно ли запись на графике I/O?

---

### Глава 4: PromQL — 20 запросов для реальных задач

**Что вы узнаете:**
- основы синтаксиса PromQL: selectors, functions, operators;
- 20 конкретных запросов для диагностики и мониторинга;
- как использовать `rate()`, `irate()`, `increase()`, `histogram_quantile()`;
- как агрегировать по labels через `by()` и `without()`.

**Цель:** читатель не знает PromQL наизусть — он знает 20 запросов для реальных задач и умеет адаптировать их.

**Темы:**

Раздел "Основы синтаксиса за 5 минут":
```promql
# Selector — выбрать метрику
node_memory_MemAvailable_bytes
node_memory_MemAvailable_bytes{instance="server1:9100"}
node_memory_MemAvailable_bytes{instance=~"server.*"}  # regex

# Range vector — значения за период [5m]
node_cpu_seconds_total[5m]  # используется внутри функций

# Instant vector — текущее значение (используется для графиков)
node_memory_MemAvailable_bytes  # одно значение на момент времени
```

Раздел "Ключевые функции":
```promql
# rate() — скорость изменения Counter за период (сглаженная)
rate(http_requests_total[5m])          # запросов/сек за последние 5 минут

# irate() — мгновенная скорость (последние 2 точки)
irate(http_requests_total[5m])         # более чувствительна к пикам

# increase() — абсолютный прирост Counter за период
increase(http_requests_total[1h])      # сколько запросов за последний час

# sum(), avg(), max(), min() — агрегация
sum(rate(http_requests_total[5m]))     # суммарный RPS
avg(node_memory_MemAvailable_bytes)    # средняя память по всем серверам

# by() — группировать по label
sum by(instance) (rate(http_requests_total[5m]))  # RPS по каждому серверу
sum by(status_code) (rate(http_requests_total[5m]))  # RPS по кодам ответа

# without() — агрегация по всему кроме указанных labels
sum without(cpu, mode) (rate(node_cpu_seconds_total[5m]))
```

Раздел "20 запросов для реальных задач":
Давать каждый запрос с комментарием — что показывает и когда использовать:

```promql
# === СЕРВЕР ===

# 1. Использование CPU (%)
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 2. Доступная память (%)
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# 3. Занятость диска (%)
100 - (node_filesystem_avail_bytes{mountpoint="/"} /
       node_filesystem_size_bytes{mountpoint="/"} * 100)

# 4. Uptime серверов
(time() - node_boot_time_seconds) / 86400   # в днях

# 5. Load average выше нормы (норма < числа CPU)
node_load1 > on(instance) count by(instance)(node_cpu_seconds_total{mode="idle"})


# === ПРИЛОЖЕНИЕ ===

# 6. RPS (запросов/сек)
sum by(instance) (rate(http_requests_total[5m]))

# 7. Процент ошибок (4xx + 5xx)
sum(rate(http_requests_total{status=~"[45].."}[5m])) /
sum(rate(http_requests_total[5m])) * 100

# 8. Задержка P99 через histogram
histogram_quantile(0.99, sum by(le) (rate(http_request_duration_seconds_bucket[5m])))

# 9. Количество активных соединений
pg_stat_activity_count   # PostgreSQL

# 10. Uptime сервиса (1 = работает, 0 = упал)
up{job="myapp"}


# === DOCKER ===

# 11. CPU контейнера (%)
rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100

# 12. Память контейнера (байт)
container_memory_usage_bytes{name!=""}

# 13. Контейнеры которые рестартовали
increase(container_restart_count[1h]) > 0


# === ДИАГНОСТИКА ===

# 14. Топ-5 сервисов по использованию CPU
topk(5, rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100)

# 15. Топ-5 сервисов по потреблению памяти
topk(5, container_memory_usage_bytes{name!=""})

# 16. Скорость роста занятости диска (прогноз полного диска)
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*3600)

# 17. Количество дней до полного диска
node_filesystem_avail_bytes{mountpoint="/"} /
(rate(node_filesystem_avail_bytes{mountpoint="/"}[6h]) * -1) / 86400

# 18. Сетевой трафик (байт/сек)
rate(node_network_receive_bytes_total{device="eth0"}[5m])

# 19. Таргеты которые недоступны
up == 0

# 20. Количество рестартов всех сервисов за час
sum(increase(kube_pod_container_status_restarts_total[1h]))
```

Раздел "histogram_quantile — перцентили задержки":
Объяснить отдельно: P50 (медиана), P95, P99 — что они означают для пользователя. Почему среднее (avg) задержки врёт и почему перцентили правдивее.

**Типичные ошибки:**
- `rate()` применять к Gauge — неверно. `rate()` только для Counter. Для Gauge использовать значение напрямую или `deriv()`.
- `[5m]` слишком мало при `scrape_interval=15s` — нужно минимум 4 точки (60s). Рекомендация: `[5m]` для 15s scrape.
- `sum()` без `by()` суммирует всё в одно число — теряешь информацию по инстансам.

**Чек-лист для самопроверки:**
- [ ] Знаю разницу между `rate()` и `irate()` и когда что использовать
- [ ] Умею агрегировать метрики через `sum by(label)()`
- [ ] Умею написать запрос для CPU, памяти, RPS, процента ошибок
- [ ] Понимаю что `predict_linear()` прогнозирует на будущее

**Попробуйте сами:**
1. Введите 5 запросов из списка выше в Prometheus UI. Убедитесь что все работают и возвращают значения.
2. Напишите запрос: «процент CPU в режиме iowait за последние 5 минут по каждому ядру». Подсказка: `rate(node_cpu_seconds_total{mode="iowait"}[5m]) * 100`.
3. Используйте `predict_linear` для диска: через сколько часов диск заполнится при текущей скорости роста? (Если диск не растёт — искусственно создайте файл.)

---

### Глава 5: Grafana — дашборды, панели, переменные

**Что вы узнаете:**
- создать дашборд с нуля: добавить панель, написать запрос, настроить оси;
- типы визуализаций: Time series, Stat, Gauge, Bar, Table, Heatmap;
- переменные: переключатель instance/environment на дашборде;
- provisioning: хранить дашборды в коде (Git).

**Цель:** читатель создаёт собственный дашборд, а не только импортирует готовые. Дашборды хранятся в Git.

**Темы:**

Раздел "Создать панель (пошагово словами)":
```text
1. Grafana → Dashboards → New → New Dashboard
2. Add visualization
3. В правой панели: Query → выбрать datasource Prometheus
4. В поле Metrics: ввести PromQL-запрос
5. Выбрать тип визуализации: Time series (для графиков во времени)
6. Panel title: дать понятное имя
7. В Legend: изменить формат меток {{instance}} или {{job}}
8. Axes: настроить единицы (bytes, percent, short)
9. Thresholds: добавить порог (красный при > 80%)
10. Apply → Save dashboard (Ctrl+S)
```

Раздел "Типы визуализаций и когда что":
```text
Time series  — метрика меняется со временем (CPU, трафик, RPS)
Stat         — одно текущее значение крупным шрифтом (uptime, версия)
Gauge        — значение на шкале (диск 75%)
Bar chart    — сравнение нескольких значений
Table        — несколько метрик в табличном виде
Heatmap      — распределение (гистограммы задержки)
Logs         — строки логов из Loki
```

Раздел "Переменные — переключатель на дашборде":
```text
Dashboard Settings → Variables → New Variable

Тип: Query
Name: instance
Label: Server
Query: label_values(up{job="node"}, instance)
→ В выпадающем списке появятся все серверы

Использовать в панелях:
node_memory_MemAvailable_bytes{instance="$instance"}
```

Раздел "Provisioning — дашборды в Git":
```yaml
# grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

```yaml
# grafana/provisioning/dashboards/dashboard.yml
apiVersion: 1
providers:
  - name: default
    folder: Provisioned
    type: file
    disableDeletion: true         # нельзя удалить из UI
    updateIntervalSeconds: 30     # обновлять каждые 30 сек
    options:
      path: /etc/grafana/provisioning/dashboards
```

```text
Как экспортировать дашборд в JSON:
Dashboard → ⚙️ Settings → JSON Model → скопировать → сохранить как файл
```

Объяснить: дашборды в JSON-файлах → в Git → Grafana подхватывает автоматически. Это IaC для дашбордов.

**Типичные ошибки:**
- Строить дашборд из десятков панелей — трудно читать, медленно грузится. 6-8 ключевых панелей лучше чем 30 мелких.
- Не настроить единицы измерения — `1073741824` вместо `1 GiB`. В настройках панели: Standard options → Unit → выбрать `bytes (IEC)`.
- Provisioned дашборды нельзя изменить в UI если `disableDeletion: true` — создать копию и редактировать её.

**Чек-лист для самопроверки:**
- [ ] Создал дашборд с нуля: хотя бы 3 панели разных типов
- [ ] Настроил переменную `$instance` для выбора сервера
- [ ] Сохранил дашборд в JSON-файл в Git через provisioning
- [ ] Настроил правильные единицы измерения (bytes, %)

**Попробуйте сами:**
1. Создайте дашборд «Здоровье сервера» с 4 панелями: CPU %, Memory %, Disk %, Uptime. Для CPU и Memory — Time series, для Disk — Gauge, для Uptime — Stat.
2. Добавьте переменную `$instance` которая позволяет выбирать сервер. Все панели должны фильтроваться по выбранному серверу.
3. Экспортируйте дашборд в JSON. Добавьте файл в `grafana/provisioning/dashboards/`. Пересоздайте контейнер Grafana (`docker compose restart grafana`) — дашборд появился автоматически?

---

### Глава 6: cAdvisor — метрики Docker-контейнеров

**Что вы узнаете:**
- как cAdvisor собирает метрики Docker-контейнеров;
- ключевые метрики: CPU, память, сеть, рестарты контейнера;
- как построить дашборд по контейнерам;
- ограничения cAdvisor.

**Цель:** читатель видит сколько CPU и памяти потребляет каждый контейнер и получает алерт при частых рестартах.

**Темы:**

Раздел "Добавить cAdvisor в docker-compose.yml":
```yaml
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
    privileged: true
    devices:
      - /dev/kmsg
    networks:
      - monitoring
```

```yaml
# prometheus.yml — добавить scrape
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

Раздел "Ключевые метрики контейнеров":
```promql
# CPU контейнера (% от одного ядра)
rate(container_cpu_usage_seconds_total{name!="", name!~".*cadvisor.*"}[5m]) * 100

# Память (байт) — рабочее множество без кэша
container_memory_working_set_bytes{name!=""}

# Память в % от лимита (если установлен limit)
container_memory_working_set_bytes /
container_spec_memory_limit_bytes * 100

# Сеть контейнера
rate(container_network_receive_bytes_total{name!=""}[5m])

# Рестарты контейнера (число рестартов всего)
container_restart_count{name!=""}

# Рестарты за последний час (для алертов)
increase(container_restart_count{name!=""}[1h])

# Статус контейнера (1 = running)
container_last_seen{name!=""}
```

Раздел "Метки cAdvisor и фильтрация":
Объяснить: cAdvisor экспортирует метрики для каждого контейнера включая внутренние. Нужна фильтрация:
```promql
# Исключить системные cgroup и пустые имена
{name!="", name!~".*_.*", image!=""}

# Или через label container вместо name (зависит от версии)
{container!="", container!="POD"}
```

**Типичные ошибки:**
- `container_memory_usage_bytes` включает page cache — показывает больше чем реально используется. Для мониторинга: `container_memory_working_set_bytes`.
- cAdvisor нужен `privileged: true` — без него часть метрик недоступна.
- Много шума от служебных контейнеров: `k8s_POD`, `infra`, пустые имена. Всегда добавлять фильтр `name!=""`.

**Чек-лист для самопроверки:**
- [ ] cAdvisor запущен и виден в Prometheus targets
- [ ] Умею найти топ-5 контейнеров по памяти через `topk()`
- [ ] Настроил алерт на частые рестарты контейнера
- [ ] Понимаю разницу между `memory_usage_bytes` и `memory_working_set_bytes`

**Попробуйте сами:**
1. Запустите ресурсоёмкий контейнер: `docker run -d --name stress polinux/stress stress --cpu 1 --vm 1 --vm-bytes 256M`. Найдите его в Prometheus по `container_cpu_usage_seconds_total`. Через 2 минуты остановите контейнер.
2. Создайте в Grafana панель «Топ-10 контейнеров по памяти» используя `topk(10, container_memory_working_set_bytes{name!=""})`.
3. Принудительно убейте контейнер (`docker kill <id>`). Docker его перезапустит (если `restart: unless-stopped`). Нашли ли увеличение `container_restart_count` в метриках?

---

### Глава 7: Exporters — PostgreSQL, Nginx, Redis, Blackbox

**Что вы узнаете:**
- концепция exporter: любой сервис можно мониторить через Prometheus;
- postgres_exporter: ключевые метрики БД;
- nginx-prometheus-exporter: RPS, ошибки, соединения;
- redis_exporter: память, команды, hit rate;
- blackbox_exporter: проверка URL, TCP-портов, DNS.

**Цель:** читатель добавляет мониторинг любого сервиса из списка за 15 минут.

**Темы:**

Раздел "Концепция exporter":
Объяснить: exporter — это прокси между Prometheus и сервисом у которого нет native `/metrics`. Exporter опрашивает сервис через его родной протокол и отдаёт метрики в формате Prometheus.

```text
Prometheus ──► GET :9187/metrics ──► postgres_exporter ──► PostgreSQL SQL queries
Prometheus ──► GET :9113/metrics ──► nginx_exporter    ──► Nginx stub_status
Prometheus ──► GET :9121/metrics ──► redis_exporter    ──► Redis INFO
```

Раздел "postgres_exporter":
```yaml
# docker-compose.yml
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    environment:
      DATA_SOURCE_NAME: "postgresql://monitoring:MonitorPass@postgres:5432/postgres?sslmode=disable"
    ports:
      - "127.0.0.1:9187:9187"
    networks:
      - monitoring
```

```promql
# Активные соединения
pg_stat_activity_count

# Соединения по состоянию
pg_stat_activity_count{state="active"}
pg_stat_activity_count{state="idle in transaction"}  # тревога если > 5

# Размер БД
pg_database_size_bytes

# Replication lag
pg_replication_lag

# Cache hit ratio
rate(pg_stat_database_blks_hit[5m]) /
(rate(pg_stat_database_blks_hit[5m]) + rate(pg_stat_database_blks_read[5m]))
```

Раздел "Nginx exporter":
```nginx
# nginx.conf — включить stub_status
server {
    listen 8080;
    location /stub_status {
        stub_status;
        allow 127.0.0.1;
        deny all;
    }
}
```

```yaml
  nginx_exporter:
    image: nginx/nginx-prometheus-exporter:1.1.0
    command:
      - '--nginx.scrape-uri=http://nginx:8080/stub_status'
    ports:
      - "127.0.0.1:9113:9113"
```

```promql
nginx_connections_active    # активные соединения
nginx_http_requests_total   # всего запросов (Counter)
rate(nginx_http_requests_total[5m])  # RPS
```

Раздел "Blackbox exporter — проверка доступности":
Blackbox exporter проверяет внешние сервисы: HTTP-URL, TCP-порт, ICMP, DNS.

```yaml
  blackbox_exporter:
    image: prom/blackbox-exporter:v0.24.0
    volumes:
      - ./blackbox/blackbox.yml:/etc/blackbox_exporter/config.yml:ro
    ports:
      - "127.0.0.1:9115:9115"
```

```yaml
# blackbox/blackbox.yml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_status_codes: [200, 201, 204]
      method: GET
      fail_if_ssl: false
      fail_if_not_ssl: false

  tcp_connect:
    prober: tcp
    timeout: 5s
```

```yaml
# prometheus.yml — проверять URL
  - job_name: 'blackbox_http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://myapp.example.com
          - https://api.example.com/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox_exporter:9115
```

```promql
# Доступен ли URL (1 = да, 0 = нет)
probe_success{job="blackbox_http"}

# Время ответа
probe_duration_seconds

# Дней до истечения SSL-сертификата
(probe_ssl_earliest_cert_expiry - time()) / 86400
```

**Типичные ошибки:**
- Blackbox exporter запускается в Docker, но проверяет `localhost` — проверяет себя, не хост. Использовать IP хоста или DNS-имя сервиса.
- Nginx stub_status открыт без ограничений по IP — любой может посмотреть статистику. Всегда `allow 127.0.0.1; deny all;`.
- `DATA_SOURCE_NAME` postgres_exporter в env виден в `docker inspect`. Использовать Docker secrets или файл с паролем.

**Чек-лист для самопроверки:**
- [ ] Понимаю что exporter — это прокси между Prometheus и сервисом
- [ ] Добавил postgres_exporter и вижу метрики БД
- [ ] Настроил Blackbox exporter для проверки доступности URL
- [ ] Знаю как отслеживать срок истечения SSL через probe_ssl_earliest_cert_expiry

**Попробуйте сами:**
1. Запустите postgres_exporter. В Prometheus найдите `pg_up` — значение 1. Остановите PostgreSQL. Через 30 секунд `pg_up` стало 0? Это и есть мониторинг БД.
2. Настройте Blackbox для проверки `https://google.com`. Найдите `probe_ssl_earliest_cert_expiry`. Посчитайте сколько дней до истечения сертификата.
3. Добавьте в Blackbox проверку несуществующего URL. `probe_success` = 0. Это будущий алерт «сайт недоступен».

---

### Глава 8: Alertmanager — правила, routing, Telegram

**Что вы узнаете:**
- как писать правила алертинга в Prometheus (recording rules и alert rules);
- жизненный цикл алерта: INACTIVE → PENDING → FIRING;
- конфигурация Alertmanager: routing, receivers, inhibition, silences;
- настройка уведомлений в Telegram и email;
- как избежать шторма алертов.

**Цель:** читатель настраивает алерты которые срабатывают при реальных проблемах и не шумят в остальное время. Получает уведомления в Telegram.

**Темы:**

Разместить Схему 3 (жизненный цикл алерта) и Схему 5 (routing).

Раздел "Alert rules в Prometheus":
```yaml
# prometheus/rules/alerts.yml
groups:
  - name: infrastructure
    interval: 30s   # частота вычисления (дефолт: global evaluation_interval)
    rules:

      # Сервис недоступен
      - alert: ServiceDown
        expr: up == 0
        for: 1m        # тревога только если DOWN больше 1 минуты
        labels:
          severity: critical
        annotations:
          summary: "Сервис {{ $labels.job }} недоступен"
          description: "Таргет {{ $labels.instance }} не отвечает больше 1 минуты"

      # Высокое использование CPU
      - alert: HighCPU
        expr: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Высокий CPU на {{ $labels.instance }}"
          description: "CPU {{ $value | printf \"%.1f\" }}% больше 5 минут"

      # Мало памяти
      - alert: LowMemory
        expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Мало памяти на {{ $labels.instance }}"
          description: "Доступно {{ $value | printf \"%.1f\" }}% памяти"

      # Диск почти полный
      - alert: DiskAlmostFull
        expr: 100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100) > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Диск заполнен на {{ $value | printf \"%.0f\" }}%"
          description: "{{ $labels.instance }}: диск {{ $labels.mountpoint }} заполнен на {{ $value | printf \"%.0f\" }}%"

      # Рестарты контейнеров
      - alert: ContainerRestarting
        expr: increase(container_restart_count[1h]) > 3
        labels:
          severity: warning
        annotations:
          summary: "Контейнер {{ $labels.name }} перезапускается"
          description: "{{ $value | printf \"%.0f\" }} рестартов за час"

      # SSL истекает через 14 дней
      - alert: SSLCertExpiringSoon
        expr: (probe_ssl_earliest_cert_expiry - time()) / 86400 < 14
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL сертификат истекает скоро"
          description: "{{ $labels.instance }}: осталось {{ $value | printf \"%.0f\" }} дней"

      # Watchdog — алерт который всегда должен быть активен
      # Если он пропал — значит что-то сломалось в самом мониторинге
      - alert: Watchdog
        expr: vector(1)
        labels:
          severity: info
        annotations:
          summary: "Мониторинг работает"
```

Раздел "Alertmanager конфиг — Telegram":
```yaml
# alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m   # считать алерт разрешённым если не стреляет 5 минут

route:
  # Группировка алертов: не отправлять каждый по отдельности
  group_by: ['alertname', 'instance']
  group_wait: 30s        # ждать 30 сек чтобы собрать группу
  group_interval: 5m     # повторять если не разрешился
  repeat_interval: 4h    # повторять FIRING алерт каждые 4 часа

  receiver: telegram-general   # куда по умолчанию

  routes:
    # Критические — в отдельный чат
    - matchers:
        - severity = critical
      receiver: telegram-critical
      continue: false

    # Watchdog — игнорировать
    - matchers:
        - alertname = Watchdog
      receiver: blackhole

receivers:
  - name: blackhole   # ничего не делать

  - name: telegram-general
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: -1001234567890    # ID чата (отрицательный для группы)
        message: |
          {{ range .Alerts }}
          {{ if eq .Status "firing" }}🔴{{ else }}✅{{ end }} *{{ .Labels.alertname }}*
          {{ .Annotations.summary }}
          {{ .Annotations.description }}
          {{ end }}
        parse_mode: Markdown

  - name: telegram-critical
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: -1009876543210   # другой чат для критических

# Подавление: если сервер недоступен — не слать алерты о его сервисах
inhibit_rules:
  - source_matchers:
      - alertname = ServiceDown
      - severity = critical
    target_matchers:
      - severity = warning
    equal: ['instance']   # только если instance совпадает
```

Раздел "Как получить Telegram bot token и chat ID":
```text
1. Создать бота: написать @BotFather → /newbot → получить токен
2. Добавить бота в группу или написать ему лично
3. Узнать chat_id:
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   → найти "chat":{"id": ...}
   Для группы: id отрицательный (-1001234567890)
```

Раздел "Silences — временно заглушить алерт":
```text
Alertmanager UI → Silences → New Silence
Matchers: alertname="DiskAlmostFull", instance="server1:9100"
Duration: 4h
Comment: "Плановая очистка диска, вернусь к норме через 2 часа"
```

**Типичные ошибки:**
- Алерт без `for:` — срабатывает при первом же нарушении, много ложных тревог. Всегда добавлять `for: 5m` минимум.
- Не настроить `inhibit_rules` — при падении сервера получишь 20 алертов о его сервисах вместо одного.
- `repeat_interval: 1m` — будешь получать сообщения каждую минуту пока проблема не решена. Минимум `4h`.
- `group_wait: 0s` — каждый алерт в отдельном сообщении. При инциденте с 10 проблемами = 10 сообщений. Нужен `group_wait: 30s`.

**Чек-лист для самопроверки:**
- [ ] Написал хотя бы 3 alert rules и понимаю синтаксис
- [ ] Понимаю INACTIVE → PENDING → FIRING и зачем нужен `for:`
- [ ] Настроил Alertmanager с Telegram-уведомлениями
- [ ] Добавил `inhibit_rules` чтобы избежать шторма алертов

**Попробуйте сами:**
1. Добавьте правило `HighCPU` с порогом 5% (чтобы оно сработало). Запустите Prometheus. Подождите `evaluation_interval`. В Prometheus UI → Alerts — найдите алерт в состоянии PENDING. Подождите `for:` — перейдёт в FIRING.
2. Настройте Telegram-бота. Убедитесь что алерт пришёл в чат. Разрешите проблему (или уберите правило) — придёт сообщение о resolving.
3. Добавьте Watchdog алерт. Он должен всегда быть в FIRING. Остановите Prometheus. Через несколько минут Watchdog пропадёт — это тест что мониторинг мониторинга работает.

---

### Глава 9: Loki + Promtail — логи в Grafana

**Что вы узнаете:**
- как Loki хранит логи (в отличие от ELK);
- Promtail: сбор логов из файлов и Docker;
- LogQL: базовые запросы для поиска в логах;
- интеграция логов и метрик на одном дашборде.

**Цель:** читатель видит логи в Grafana рядом с метриками. При инциденте переходит с графика метрики на соответствующие строки логов.

**Темы:**

Раздел "Loki vs ELK":
```text
ELK (Elasticsearch + Logstash + Kibana):
+ Полнотекстовый поиск, индексирование
- Требует много RAM (Elasticsearch от 2GB)
- Сложная настройка и поддержка
- Дорого в production

Loki (Grafana Labs):
+ Лёгкий: индексирует только labels, не содержимое
+ Тесная интеграция с Grafana
+ Хранит логи сжатыми (как объекты)
- Поиск по тексту медленнее чем в ES
- Не подходит для сложного full-text search

→ Для большинства DevOps-задач Loki достаточен
```

Раздел "Добавить Loki + Promtail в docker-compose.yml":
```yaml
  loki:
    image: grafana/loki:2.9.7
    container_name: loki
    restart: unless-stopped
    volumes:
      - ./loki/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "127.0.0.1:3100:3100"
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:2.9.7
    container_name: promtail
    restart: unless-stopped
    volumes:
      - ./promtail/promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro              # системные логи
      - /var/lib/docker/containers:/var/lib/docker/containers:ro  # Docker логи
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring
```

```yaml
# loki/loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 30d   # хранить логи 30 дней
```

```yaml
# promtail/promtail-config.yml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Системные логи
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlogs
          host: myserver
          __path__: /var/log/*.log

  # Docker-логи контейнеров
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: container
      - source_labels: ['__meta_docker_container_image']
        target_label: image
```

Раздел "LogQL — запросы в логах":
```logql
# Все логи контейнера nginx
{container="nginx"}

# Найти строки содержащие "error"
{container="nginx"} |= "error"

# Исключить строки с "health"
{container="nginx"} != "health"

# Regex-фильтр
{container="nginx"} |~ "ERROR|CRITICAL"

# Парсить JSON-логи
{container="myapp"} | json | level="error"

# Считать ошибки в минуту (для графика)
rate({container="nginx"} |= "error" [1m])

# Топ-10 IP по числу запросов (из nginx access log)
topk(10, sum by(remote_addr) (
  rate({job="nginx_access"} | logfmt | __error__="" [5m])
))
```

Раздел "Добавить Loki как datasource в Grafana":
```text
Grafana → Connections → Data Sources → Add → Loki
URL: http://loki:3100
Save & Test
```

```text
Использование в дашборде:
1. Добавить панель → тип Logs
2. Query: {container="myapp"} |= "error"
3. Панель показывает строки логов в реальном времени
```

Раздел "Связать метрики и логи":
```text
Grafana Explore → выбрать Prometheus → найти момент spike на графике →
переключиться на Loki → тот же временной диапазон → видеть логи в момент spike

Или через Derived fields:
В datasource Loki → Derived fields:
Name: TraceID
Regex: traceID=(\w+)
URL: http://jaeger:16686/trace/$${__value.raw}
→ В логах traceID кликается и открывает трейс
```

**Типичные ошибки:**
- Loki без `retention_period` хранит логи вечно — диск заполнится. Всегда устанавливать retention.
- Много уникальных labels в Loki (например, `user_id` как label) — как в Prometheus, высокая кардинальность = большой индекс = медленно. Labels должны быть немногочисленными.
- Promtail не видит Docker-логи — нужен доступ к `/var/lib/docker/containers` и сокету Docker.

**Чек-лист для самопроверки:**
- [ ] Loki + Promtail запущены, логи поступают в Loki
- [ ] Умею написать LogQL-запрос для фильтрации по тексту и labels
- [ ] Вижу логи в Grafana Explore
- [ ] Понимаю разницу между Loki и ELK и когда что выбрать

**Попробуйте сами:**
1. Запустите Loki + Promtail. Откройте Grafana → Explore → выберите Loki. Введите `{job="varlogs"}` — видите системные логи?
2. Создайте несколько ошибочных запросов к nginx (`curl http://localhost/nonexistent`). Найдите в Loki логи с `|= "404"`.
3. Откройте Prometheus метрику и Loki логи в Grafana Explore одновременно (через split view). Убедитесь что временные диапазоны синхронизированы.

---

### Глава 10: Pushgateway — метрики для batch jobs

**Что вы узнаете:**
- зачем нужен Pushgateway: когда pull-модель не работает;
- как отправить метрики из bash-скрипта и Python;
- правило: один job — одна группа метрик;
- почему Pushgateway не нужен там где работает pull.

**Цель:** скрипт резервного копирования отправляет метрики (статус, длительность, размер) в Prometheus.

**Темы:**

Раздел "Когда pull-модель не работает":
```text
Batch job (скрипт бэкапа, ETL, задание cron):
- Запускается → работает → завершается
- Нет постоянного HTTP-сервера
- Prometheus не может опросить его (нечего опрашивать)

Решение: job отправляет метрики в Pushgateway
Prometheus опрашивает Pushgateway (он постоянно работает)
```

Раздел "Добавить Pushgateway":
```yaml
  pushgateway:
    image: prom/pushgateway:v1.8.0
    container_name: pushgateway
    restart: unless-stopped
    ports:
      - "127.0.0.1:9091:9091"
    networks:
      - monitoring
```

```yaml
# prometheus.yml
  - job_name: 'pushgateway'
    honor_labels: true    # использовать labels из push, не переопределять
    static_configs:
      - targets: ['pushgateway:9091']
```

Раздел "Отправить метрики из bash":
```bash
# Скрипт бэкапа с метриками
#!/bin/bash
BACKUP_START=$(date +%s)
PUSHGATEWAY="http://localhost:9091"
JOB="backup"
INSTANCE="server1"

# Выполнить бэкап
pg_dump -U postgres myapp > /backup/myapp_$(date +%Y%m%d).sql
BACKUP_STATUS=$?
BACKUP_END=$(date +%s)
BACKUP_DURATION=$((BACKUP_END - BACKUP_START))
BACKUP_SIZE=$(du -sb /backup/myapp_$(date +%Y%m%d).sql | cut -f1)

# Отправить метрики
cat <<EOF | curl -s --data-binary @- "$PUSHGATEWAY/metrics/job/$JOB/instance/$INSTANCE"
# TYPE backup_last_success_timestamp gauge
backup_last_success_timestamp $(date +%s)
# TYPE backup_duration_seconds gauge
backup_duration_seconds $BACKUP_DURATION
# TYPE backup_size_bytes gauge
backup_size_bytes $BACKUP_SIZE
# TYPE backup_exit_code gauge
backup_exit_code $BACKUP_STATUS
EOF

echo "Метрики отправлены в Pushgateway"
```

Раздел "Алерт на неудачный бэкап":
```yaml
# Алерт: бэкап не выполнялся больше 25 часов
- alert: BackupMissed
  expr: time() - backup_last_success_timestamp > 90000   # 25 часов
  labels:
    severity: critical
  annotations:
    summary: "Бэкап не выполнялся больше 25 часов"
```

**Типичные ошибки:**
- Использовать Pushgateway для обычных сервисов — это антипаттерн. Для постоянно работающих сервисов — pull.
- Не удалять старые метрики из Pushgateway — после завершения job метрики остаются и могут вводить в заблуждение.

**Чек-лист для самопроверки:**
- [ ] Понимаю когда нужен Pushgateway (batch jobs) и когда не нужен
- [ ] Умею отправить метрики из bash-скрипта через curl
- [ ] Настроил алерт на основе метрик из Pushgateway

**Попробуйте сами:**
1. Напишите скрипт который отправляет `script_last_run_timestamp` в Pushgateway. Запустите его. Найдите метрику в Prometheus.
2. Добавьте алерт: если `script_last_run_timestamp` не обновлялся больше 10 минут — алерт. Не запускайте скрипт 11 минут. Сработал ли алерт?

---

### Глава 11: Масштабирование и long-term storage

**Что вы узнаете:**
- сколько данных хранит Prometheus и как управлять размером;
- Remote Write: отправить метрики во внешнее хранилище;
- VictoriaMetrics как long-term storage;
- когда одного Prometheus недостаточно.

**Цель:** читатель знает ограничения одного Prometheus и как их обойти если нужно хранить данные дольше 15 дней.

**Темы:**

Раздел "Сколько хранит один Prometheus":
```text
Объём данных:
~1-2 байта на sample (точку)
15 секунд × 100 метрик × 365 дней = ~63 млн samples ≈ 100MB
1000 метрик × то же = 1GB

По умолчанию Prometheus хранит 15 дней.
Для большинства: этого достаточно.

Когда 15 дней мало:
- «Что было в прошлом квартале?»
- Сравнение год к году
- Compliance / аудит
```

Раздел "Remote Write в VictoriaMetrics":
```yaml
# prometheus.yml — отправлять метрики во внешнее хранилище
remote_write:
  - url: "http://victoriametrics:8428/api/v1/write"
    queue_config:
      max_samples_per_send: 10000
      max_shards: 30
```

```yaml
# docker-compose.yml
  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.100.0
    container_name: victoriametrics
    command:
      - '--storageDataPath=/victoria-metrics-data'
      - '--retentionPeriod=12'   # 12 месяцев
    volumes:
      - vm_data:/victoria-metrics-data
    ports:
      - "127.0.0.1:8428:8428"
```

```text
Grafana datasource для VictoriaMetrics:
URL: http://victoriametrics:8428
Type: Prometheus (VictoriaMetrics совместим с Prometheus API)
```

Раздел "Когда одного Prometheus недостаточно":
```text
Нужны несколько Prometheus когда:
- > 1 млн активных time series (один Prometheus обычно держит 1-3 млн)
- Несколько изолированных datacenter (каждый свой Prometheus)
- Нужна высокая доступность самого мониторинга

Решения:
- Thanos / Cortex / Mimir — federation и high availability
- VictoriaMetrics Cluster — enterprise вариант
→ Для большинства DevOps-задач один Prometheus + VictoriaMetrics достаточен
```

**Типичные ошибки:**
- `--storage.tsdb.retention.time=1y` без Remote Write и без большого диска — Prometheus упадёт по OOM или заполнит диск.
- Не мониторить сам Prometheus — метрика `prometheus_tsdb_head_series` показывает число активных time series. Рост без причины = утечка cardinality.

**Чек-лист для самопроверки:**
- [ ] Знаю сколько примерно хранит мой Prometheus (`du -sh /var/lib/docker/volumes/prometheus_data`)
- [ ] Понимаю разницу между retention в Prometheus и long-term storage
- [ ] Знаю что такое Remote Write и как добавить VictoriaMetrics

**Попробуйте сами:**
1. Проверьте текущий размер данных Prometheus: `docker exec prometheus du -sh /prometheus`. Сколько занимают метрики за несколько дней?
2. Добавьте `remote_write` в VictoriaMetrics. Убедитесь что метрики поступают: откройте `http://localhost:8428` — там UI VictoriaMetrics.

---

### Глава 12: Диагностика — что делать когда мониторинг сломан

**Что вы узнаете:**
- алгоритм диагностики когда алерты не приходят;
- как проверить что Prometheus собирает метрики;
- типичные проблемы Alertmanager;
- self-monitoring: мониторинг самого мониторинга.

**Цель:** читатель знает что делать если «мониторинг молчит». Не паникует — идёт по алгоритму.

**Темы:**

Раздел "Алгоритм: алерт не пришёл":
```mermaid
flowchart TD
    A[Алерт не пришёл] --> B{Prometheus\nотвечает?}
    B -->|Нет| C[docker compose ps\njournalctl -u prometheus]
    B -->|Да| D{Таргет UP\nв /targets?}
    D -->|Нет| E[Проверить сеть\nи конфиг scrape]
    D -->|Да| F{Алерт в FIRING\nв /alerts?}
    F -->|Нет| G[Проверить правило\nв /rules\nформула верна?]
    F -->|Да| H{Alertmanager\nполучил алерт?}
    H -->|Нет| I[Проверить\nalerting: блок\nв prometheus.yml]
    H -->|Да| J{В Telegram\nпришло?}
    J -->|Нет| K[Проверить\nbot_token и chat_id\nАМ логи]
```

Раздел "Самодиагностика Prometheus":
```promql
# Prometheus мониторит себя — эти метрики всегда должны быть доступны
prometheus_build_info              # версия
prometheus_tsdb_head_series        # число активных time series
rate(prometheus_tsdb_head_samples_appended_total[5m])  # samples/sec
prometheus_rule_evaluation_failures_total  # ошибки вычисления rules
```

Раздел "Проверка Alertmanager":
```bash
# Логи Alertmanager
docker logs alertmanager | tail -50

# Тестовая отправка алерта напрямую в Alertmanager
curl -X POST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"summary": "Тестовый алерт"},
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }]'
# → должен прийти в Telegram
```

Раздел "Watchdog алерт как тест работоспособности":
Объяснить паттерн «dead man's switch»: Watchdog алерт всегда должен быть активен. Если он пропал — значит Prometheus или Alertmanager сломан. Для этого настроить отдельный receiver (например, `healthchecks.io` или отдельный Telegram-чат) который получает Watchdog и молчит. Если Watchdog перестал приходить — значит мониторинг упал.

**Типичные ошибки:**
- Не проверять `/targets` после добавления нового таргета — думаешь что мониторинг работает, а таргет DOWN.
- Не тестировать алерты заранее — узнаёшь что Telegram bot token устарел только во время реального инцидента.
- Не мониторить сам мониторинг — Prometheus упал, никто не знает.

**Чек-лист для самопроверки:**
- [ ] Знаю алгоритм «алерт не пришёл» — 6 шагов
- [ ] Умею тестировать Alertmanager через прямой API-запрос
- [ ] Настроил Watchdog алерт
- [ ] Знаю где смотреть логи каждого компонента

**Попробуйте сами:**
1. Намеренно сломайте Telegram bot token (поменяйте на неверный). Дождитесь FIRING алерта. Алерт есть в Prometheus, но в Telegram не пришёл. Пройдите по алгоритму диагностики — где сломалось?
2. Отправьте тестовый алерт напрямую в Alertmanager через curl. Пришло в Telegram? Это значит Alertmanager и Telegram работают. Проблема в Prometheus → Alertmanager.
3. Остановите Prometheus. Через 5 минут — Watchdog пропал из Alertmanager. Это и есть «мониторинг мониторинга».

---

## Приложения

### Приложение A: Полный docker-compose.yml

Финальный рабочий `docker-compose.yml` со всеми компонентами книги: Prometheus, Grafana, Node Exporter, cAdvisor, Alertmanager, Loki, Promtail, Pushgateway, postgres_exporter, nginx_exporter, blackbox_exporter. С volumes, networks, healthchecks. Готов к `docker compose up -d`.

### Приложение B: Готовые alert rules

Полный файл `prometheus/rules/alerts.yml` со всеми правилами из книги. Разделы: Infrastructure (CPU, Memory, Disk, Network), Containers (рестарты, ресурсы), Services (uptime, errors, latency), Backups (Pushgateway-алерты), SSL (истечение сертификата), Watchdog.

### Приложение C: Шпаргалка PromQL и LogQL

**PromQL**: selectors, functions (rate, irate, increase, histogram_quantile, predict_linear), aggregation (sum, avg, topk, by, without), операторы. По 2-3 примера каждой функции.

**LogQL**: label selectors, line filters (`|=`, `!=`, `|~`), parsers (`| json`, `| logfmt`), metric queries (`rate`, `count_over_time`).

---

## Что читатель получит к концу книги

- Работающий стек мониторинга на любом Linux-сервере (один `docker compose up`)
- Дашборды в Grafana: серверы, контейнеры, PostgreSQL, Nginx
- Алерты в Telegram: уведомления при реальных проблемах без ложного шума
- Логи в Grafana через Loki: поиск по тексту рядом с метриками
- Умение писать PromQL для реальных задач (20 запросов из книги)
- Понимание архитектуры: что с чем общается и зачем
- Алгоритм диагностики когда что-то в мониторинге не работает
- Дашборды и алерты в Git (provisioning)
