# Глава 5: Grafana — дашборды, панели, переменные

> **Запомни:** Grafana — это лицо твоего мониторинга. Хороший дашборд отвечает на вопросы за секунду. Плохой — заставляет искать данные по десятку панелей.

---

## Что вы узнаете

- создать дашборд с нуля: добавить панель, написать запрос, настроить оси;
- типы визуализаций: Time series, Stat, Gauge, Bar, Table, Heatmap, Logs;
- переменные: переключатель instance/environment на дашборде;
- provisioning: хранить дашборды в коде (Git);
- экспорт и импорт JSON-дашбордов;
- provisioning alert rules в Grafana.

**Цель:** ты создаёшь собственный дашборд, а не только импортируешь готовые. Дашборды хранятся в Git.

---

## Создать первую панель (пошагово, без скриншотов)

### Шаг 1: Новая панель

1. Grafana → Dashboards → New → New Dashboard.
2. Нажмите **Add visualization**.
3. В правой панели на вкладке **Query** выберите datasource **Prometheus** (если его нет — добавьте: Connections → Data sources → Add → Prometheus → URL: `http://prometheus:9090`).

### Шаг 2: Запрос

В поле **Metrics** введите PromQL-запрос:

```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

Нажмите Shift+Enter или кнопку **Run queries** — должен появиться график.

### Шаг 3: Тип визуализации

Выберите **Time series** (по умолчанию). Этот тип подходит для большинства метрик, меняющихся во времени.

### Шаг 4: Настройки панели

Справа — панель настроек (если не видна — нажмите кнопку с шестерёнкой в правом верхнем углу).

- **Panel title**: `Использование CPU (%)`
- **Legend**: выберите **Custom**, введите `{{instance}}`. В легенде будет отображаться имя сервера, а не `{instance="server1:9100"}`.
- **Unit**: Standard options → Unit → выбрать `Percent (0-100)`.
- **Min**: `0`, **Max**: `100`.

### Шаг 5: Thresholds (пороговые значения)

Вкладка **Thresholds**:

- Нажмите **Add threshold**.
- Base: зелёный (значение по умолчанию).
- `80`: жёлтый (предупреждение).
- `90`: красный (критично).

Thresholds окрашивают фон или линию графика при превышении.

### Шаг 6: Сохранить

Нажмите **Apply** (в правом верхнем углу). Затем **Save dashboard** (Ctrl+S). Дайте имя: `Серверы`.

---

## Типы визуализаций и когда что использовать

Grafana предлагает десятки типов панелей, но для мониторинга серверов нужны в основном эти:

### Time series

```text
Назначение:   метрика меняется со временем
Примеры:      CPU, память, трафик, RPS, задержка
Настройка:    X — время, Y — значение
Легенда:      {{instance}} или {{job}}
```

Это основной тип. Используется для 80% панелей.

### Stat

```text
Назначение:   одно текущее значение крупным шрифтом
Примеры:      uptime, количество ошибок за час, версия приложения
Настройка:    Unit, Color (green/red по порогу)
Важно:        Показывает только последнее значение — бесполезен если
              метрика не обновляется (например, uptime один раз)
```

Идеален для дашборда «сводка сверху» — 4 панели Stat в ряд: uptime, CPU, память, диск.

### Gauge

```text
Назначение:   значение на шкале (как тахометр)
Примеры:      заполнение диска, память, CPU
Настройка:    Min/Max, Thresholds
Ограничение:  показывает только текущее значение, нет истории
```

Хорош для панели «диск» на дашборде — сразу видно заполнен ли раздел.

### Bar chart

```text
Назначение:   сравнение нескольких значений
Примеры:      топ-5 контейнеров по памяти, количество запросов по кодам
Настройка:    Orientation: horizontal/vertical
```

Годится для «кто жрёт ресурсы» — topk запросы лучше всего выводить в Bar chart.

### Table

```text
Назначение:   несколько метрик в табличном виде
Примеры:      список всех серверов с CPU/памятью/диском
Настройка:    Columns — метрики, Rows — instance
              можно сортировать по колонке
```

Полезен дашборд «все серверы в одной таблице» — сразу видно кто в красной зоне.

### Heatmap

```text
Назначение:   распределение значений (гистограмма во времени)
Примеры:      задержка запросов P99 по минутам
Настройка:    Buckets (обычно auto)
```

Для анализа задержек — показывает как распределение latency меняется во времени.

### Logs

```text
Назначение:   строки логов в реальном времени
Примеры:      ошибки из Loki
Настройка:    datasource Loki, запрос LogQL
```

Полезен на дашборде с метриками — добавить панель Logs внизу для контекста.

---

## Переменные — переключатель на дашборде

Переменные — это выпадающие списки которые подставляются в PromQL. Главная переменная: `$instance` для выбора сервера.

### Создать переменную $instance

1. Dashboard Settings (шестерёнка вверху) → Variables → **New Variable**.
2. **Name**: `instance`
3. **Label**: `Сервер`
4. **Type**: `Query`
5. **Query**: `label_values(up{job="node"}, instance)`
6. **Multi-value**: включи (чтобы выбрать несколько серверов)
7. **Include All option**: включи (чтобы выбрать все)

Grafana выполнит запрос `label_values(up{job="node"}, instance)` и соберёт все значения label `instance` из метрики `up`. В выпадающем списке появятся: `server1:9100`, `server2:9100`, `All`.

### Использовать переменную в панелях

В любой панели вместо конкретного сервера пиши `$instance`:

```promql
node_memory_MemAvailable_bytes{instance="$instance"}
```

Grafana подставит выбранные значения. Если выбрано два сервера — запрос станет:

```promql
node_memory_MemAvailable_bytes{instance=~"server1:9100|server2:9100"}
```

### Другие полезные переменные

```text
# $job — выбор job
Type: Query
Query: label_values(up, job)

# $env — окружение (если есть label environment)
Type: Query
Query: label_values(up, environment)
```

### Фильтрация по instance в PromQL на дашборде

Если переменная `$instance` включена и выбрано несколько серверов — все панели на дашборде автоматически покажут данные только по выбранным серверам. Это работает через подстановку `{instance="$instance"}` в каждый запрос.

Без `$instance` — панели показывают все серверы, что на большом дашборде превращается в кашу.

---

## Provisioning — дашборды в Git

Provisioning позволяет описать datasource и дашборды в YAML-файлах. Grafana читает их при старте и автоматически создаёт всё что описано. Это **Infrastructure as Code (IaC)** для мониторинга.

### Структура директорий

```text
grafana/
└── provisioning/
    ├── datasources/
    │   └── prometheus.yml
    ├── dashboards/
    │   ├── dashboard.yml       # провайдер
    │   └── node-exporter.json  # экспортированный дашборд
    └── alerting/
        └── alert_rules.yml     # правила алертов (Grafana Alerting)
```

### Datasource

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

Этот файл говорит Grafana: «создай datasource с именем Prometheus, подключись к `http://prometheus:9090`, сделай его дефолтовым и не давай редактировать из UI».

### Провайдер дашбордов

```yaml
# grafana/provisioning/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: default
    folder: Provisioned
    type: file
    disableDeletion: true
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards
```

Параметры:

- `disableDeletion: true` — нельзя удалить дашборд из UI (чтобы случайно не потерять).
- `updateIntervalSeconds: 30` — Grafana проверяет изменения на диске каждые 30 секунд.
- `path` — где лежат JSON-файлы дашбордов.

### Дашборд в JSON

Экспорт дашборда:

```text
Dashboard → Settings → JSON Model → скопировать весь текст
Сохранить как: grafana/provisioning/dashboards/node-exporter.json
```

Импорт JSON-файла:

```text
Grafana → Dashboards → New → Import → Upload dashboard JSON file
```

После того как JSON лежит в `provisioning/dashboards/`, Grafana подхватит его автоматически (в течение `updateIntervalSeconds`). Если не подхватился — перезапустите Grafana:

```bash
docker compose restart grafana
```

---

## Экспорт и импорт дашбордов

### Экспорт

Для переноса между стендами или сохранения в Git:

1. Открыть дашборд.
2. Шестерёнка (Dashboard Settings) → **JSON Model**.
3. Скопировать весь JSON.
4. Сохранить в файл, например `dashboards/my-dashboard.json`.

### Импорт

```text
Grafana → Dashboards → New → Import
```

Варианты:

- **Import via grafana.com**: ввести ID дашборда (например, 1860 для Node Exporter).
- **Upload JSON file**: загрузить сохранённый ранее JSON.
- **Paste JSON**: вставить JSON напрямую.

После импорта выберите datasource (если импортированный дашборд использует Prometheus — выберите свой). Нажмите **Import**.

---

## Provisioning alert rules

В Grafana можно создавать не только дашборды, но и alert rules через provisioning. Это альтернатива Alertmanager (оба подхода работают, выбирайте один).

> В этой книге основное внимание уделено Alertmanager (Глава 8). Но если у вас уже есть Grafana и не хочется разворачивать отдельный Alertmanager — можно использовать встроенный Alerting Grafana.

### Пример alert rule в provisioning

```yaml
# grafana/provisioning/alerting/alert_rules.yml
apiVersion: 1

groups:
  - orgId: 1
    name: infrastructure
    interval: 60s
    rules:
      - title: ServiceDown
        condition: A
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: up == 0
              intervalMs: 60000
              maxDataPoints: 0
        noDataState: Alerting
        execErrState: Alerting
        for: 1m
        annotations:
          summary: "Сервис {{ $labels.instance }} недоступен"
```

Пояснение параметров:

- `condition: A` — ссылка на refId из `data`. Если в правиле несколько условий (например, A и B), можно комбинировать.
- `datasourceUid: prometheus` — UID datasource (по умолчанию совпадает с именем).
- `noDataState: Alerting` — если данные перестали поступать — алерт.
- `execErrState: Alerting` — если запрос упал с ошибкой — алерт.
- `for: 1m` — ждать 1 минуту перед FIRING, как в Alertmanager.

### Создание UID datasource

Если в provisioning datasources не указан явный UID, Grafana генерирует его из имени. Чтобы быть уверенным, укажите UID:

```yaml
# grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
```

Теперь в alert rules можно ссылаться на `datasourceUid: prometheus`.

---

## Антипаттерны построения дашбордов

### Слишком много панелей на одном дашборде

6-8 ключевых панелей лучше чем 30 мелких. Дашборд должен отвечать на вопросы, а не показывать «все метрики которые есть». Если панелей много — разбейте на несколько дашбордов:

- `Серверы` — CPU, память, диск, сеть, load, uptime.
- `Контейнеры` — ресурсы контейнеров, рестарты.
- `Приложение` — RPS, ошибки, задержки.

### Не настроены единицы измерения

Число `1073741824` не говорит ни о чём. В настройках панели:

```text
Standard options → Unit → выбрать:
- bytes (IEC) для памяти (KiB, MiB, GiB)
- percent (0-100) для CPU
- seconds (s) для задержки
- bytes/sec для скорости сети/диска
- short для безразмерных (RPS, соединения)
```

### Нет переменных

Дашборд с метриками всех серверов на одном графике — это каша. Добавьте `$instance` чтобы можно было выбрать один сервер. Добавьте `$env` чтобы переключаться между production/staging.

### Графики без лимитов осей

Y-ось CPU от 0 до 100, а не от -50 до 150. Всегда устанавливайте `Min` и `Max` если они известны. Особенно для процентов и шкал.

### Provisioned дашборды с disableDeletion: true

Дашборд нельзя отредактировать и сохранить через UI, только через JSON-файл. Это правильно для IaC, но неочевидно новому инженеру. Создайте копию дашборда (Save as) для экспериментов.

---

## Типичные ошибки

- Строить дашборд из десятков панелей — трудно читать, медленно грузится. 6-8 ключевых панелей лучше чем 30 мелких.
- Не настроить единицы измерения — `1073741824` вместо `1 GiB`. Всегда проверяйте Standard options → Unit.
- Provisioned дашборды нельзя изменить в UI если `disableDeletion: true` — создайте копию и редактируйте её.
- Не использовать переменную `$instance` — на дашборде отображаются все серверы одновременно, графики нечитаемы.
- Использовать Time series для single-value метрик (версия, uptime) — Stat или Stat + Gauge нагляднее.
- Дашборды только в UI — при пересоздании контейнера Grafana все дашборды пропадут. Всегда provisioning в Git.

---

## Чек-лист для самопроверки

- [ ] Создал дашборд с нуля: хотя бы 3 панели разных типов
- [ ] Настроил переменную `$instance` для выбора сервера
- [ ] Сохранил дашборд в JSON-файл в Git через provisioning
- [ ] Настроил правильные единицы измерения (bytes, percent, seconds)
- [ ] Добавил thresholds (пороги) на ключевые панели
- [ ] Настроил datasource через provisioning YAML
- [ ] Знаю разницу между Time series, Stat, Gauge, Bar, Table
- [ ] Умею экспортировать и импортировать дашборды

---

## Попробуйте сами

1. Создайте дашборд «Здоровье сервера» с 4 панелями:

   - **CPU %** — Time series с запросом `100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`. Легенда: `{{instance}}`.
   - **Memory %** — Time series с запросом `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100`.
   - **Disk %** — Gauge с запросом `100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)`. Установите Min=0, Max=100. Пороги: 80% жёлтый, 90% красный.
   - **Uptime** — Stat с запросом `(time() - node_boot_time_seconds) / 86400`. Unit: `none`. Decimal: 1.

2. Добавьте переменную `$instance`:
   - Dashboard Settings → Variables → New.
   - Name: `instance`, Label: `Сервер`, Type: `Query`.
   - Query: `label_values(up{job="node"}, instance)`.
   - Multi-value: включите, Include All option: включите.
   - Во все 4 панели добавьте в запрос `{instance="$instance"}`.
   - Переключайтесь между серверами — данные должны меняться.

3. Настройте provisioning:
   - Создайте директорию `grafana/provisioning/datasources/`.
   - Положите туда `prometheus.yml` с datasource Prometheus.
   - Создайте `grafana/provisioning/dashboards/dashboard.yml` — провайдер.
   - Экспортируйте дашборд «Здоровье сервера» в JSON, положите файл рядом.
   - Перезапустите Grafana: `docker compose restart grafana`.
   - Откройте Grafana — дашборд появился автоматически?

4. Импортируйте готовый дашборд Node Exporter Full (ID 1860):
   - Dashboards → New → Import → введите `1860`.
   - Выберите datasource Prometheus.
   - Изучите панели. Какие единицы измерения использованы? Какие thresholds? Сколько панелей?
   - Сравните с дашбордом который вы создали сами — что лишнего, чего не хватает?
