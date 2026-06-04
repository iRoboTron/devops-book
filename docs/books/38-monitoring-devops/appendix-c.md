# Приложение C: Шпаргалка PromQL и LogQL

Краткий справочник по PromQL (метрики) и LogQL (логи) — синтаксис, функции, примеры.

---

## PromQL

### Типы векторов

```promql
# Instant vector — одно значение на момент запроса
node_memory_MemAvailable_bytes
# Результат: одна точка на каждой временной отметке графика

# Range vector — значения за период [время]
node_cpu_seconds_total[5m]
# Результат: набор точек за 5 минут (используется ТОЛЬКО внутри функций)
```

### Селекторы (фильтрация метрик)

```promql
# Точное совпадение
node_memory_MemAvailable_bytes{instance="server1:9100"}

# Regex совпадение (=~)
node_memory_MemAvailable_bytes{instance=~"server.*"}

# Отрицание (!=)
node_memory_MemAvailable_bytes{instance!="server1:9100"}

# Regex отрицание (!~)
node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.lxcfs"}

# Несколько условий через запятую (AND)
node_cpu_seconds_total{cpu="0", mode="idle"}
```

### Функции

#### rate()
Скорость изменения Counter за период (сглаженная, средняя). Только для Counter.

```promql
# RPS (запросов в секунду) за 5 минут
rate(http_requests_total[5m])

# Ошибки в секунду за 5 минут
rate(http_requests_total{status=~"5.."}[5m])

# Трафик сети (байт/сек) за 5 минут
rate(node_network_receive_bytes_total{device="eth0"}[5m])
```

#### irate()
Мгновенная скорость Counter (последние 2 точки). Чувствительнее к пикам, но менее стабильна.

```promql
# Мгновенный RPS (последние 2 семпла)
irate(http_requests_total[5m])

# Мгновенная ошибок (резкие всплески)
irate(http_requests_total{status=~"5.."}[5m])
```

#### increase()
Абсолютный прирост Counter за период.

```promql
# Сколько запросов за последний час
increase(http_requests_total[1h])

# Сколько рестартов контейнера за час
increase(container_restart_count{name!=""}[1h])

# Сколько ошибок за последние 24 часа
increase(http_requests_total{status=~"5.."}[24h])
```

#### deriv()
Скорость изменения Gauge (наклон линейной регрессии). Для Gauge вместо rate().

```promql
# Растёт ли память (положительное значение = утечка)
deriv(node_memory_MemAvailable_bytes[30m])

# Растёт ли занятость диска
deriv(node_filesystem_avail_bytes{mountpoint="/"}[6h])
```

#### predict_linear()
Прогноз значения Gauge через N секунд на основе линейной регрессии.

```promql
# Сколько будет свободного места через 24 часа при текущем темпе
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*3600)

# Прогноз свободной памяти через 1 час
predict_linear(node_memory_MemAvailable_bytes[1h], 3600)
```

#### delta()
Разница между последним и первым значением Gauge за период.

```promql
# Изменение температуры CPU за 5 минут
delta(node_cpu_temperature_celsius[5m])

# Изменение свободной памяти за 30 минут
delta(node_memory_MemAvailable_bytes[30m])
```

#### histogram_quantile()
Вычисление перцентиля из гистограммы (требуется метрика с суффиксом `_bucket`).

```promql
# P50 (медиана) задержки HTTP-запросов
histogram_quantile(0.50, sum by(le) (rate(http_request_duration_seconds_bucket[5m])))

# P99 задержки HTTP-запросов
histogram_quantile(0.99, sum by(le) (rate(http_request_duration_seconds_bucket[5m])))

# P95 задержки по каждому экземпляру
histogram_quantile(0.95, sum by(le, instance) (rate(http_request_duration_seconds_bucket[5m])))
```

### Агрегация

#### sum()
Суммирование значений. Без `by()` — одно число.

```promql
# Суммарный RPS всех инстансов
sum(rate(http_requests_total[5m]))

# RPS по каждому инстансу (by)
sum by(instance) (rate(http_requests_total[5m]))

# RPS по коду ответа
sum by(status) (rate(http_requests_total[5m]))
```

#### avg(), max(), min()
Среднее, максимум, минимум.

```promql
# Средний CPU по всем серверам
avg(100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))

# Максимальная загрузка CPU среди серверов
max by(instance) (100 - (avg by(cpu)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))

# Минимальная доступная память среди серверов
min by(instance) ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)
```

#### count()
Количество time series, удовлетворяющих условию.

```promql
# Сколько CPU ядер на сервере
count by(instance) (node_cpu_seconds_total{mode="idle"})

# Сколько таргетов в UP
count(up == 1)

# Сколько контейнеров запущено
count(container_last_seen{name!=""})
```

#### topk()
Топ N значений.

```promql
# Топ-5 контейнеров по памяти
topk(5, container_memory_working_set_bytes{name!=""})

# Топ-3 сервера по CPU
topk(3, 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))

# Топ-10 IP адресов по числу запросов (LogQL)
topk(10, sum by(remote_addr) (rate({job="nginx"}[5m])))
```

#### by() и without()
Управление группировкой при агрегации.

```promql
# by() — группировать по указанным labels
sum by(instance, job) (rate(http_requests_total[5m]))

# without() — агрегировать по всем кроме указанных
# Равносильно by(instance), но не требует знать все другие labels
sum without(cpu, mode) (rate(node_cpu_seconds_total[5m]))
```

### Операторы

#### Арифметические

```promql
# + - * / ^ %
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100   # процент
rate(node_disk_read_bytes_total[5m]) + rate(node_disk_written_bytes_total[5m])  # сумма IO
```

#### Сравнения (возвращают 0 или 1)

```promql
up == 0                        # таргеты в DOWN
node_load1 > 4                 # нагрузка выше порога
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 15  # памяти мало
```

#### Логические (and, or, unless)

```promql
# И: сервер с высокой нагрузкой И мало памяти
(node_load1 > 4) and ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 15)

# ИЛИ: сервер с высокой нагрузкой ИЛИ мало памяти
(node_load1 > 4) or ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 15)

# UNLESS: сервер с высокой нагрузкой НО НЕ с малым диском
(node_load1 > 4) unless (node_filesystem_avail_bytes{mountpoint="/"} < 1e9)
```

#### Bool mode в сравнениях (возвращает 0 или 1 вместо фильтрации)

```promql
# Фильтрация (по умолчанию): возвращает метрику если условие истинно
up == 0   # вернёт метрики где up = 0

# Bool mode: возвращает 1 если истинно, 0 если ложно
up == bool 0   # вернёт 1 для DOWN, 0 для UP
```

### 20 реальных запросов (кратко)

| Задача | Запрос |
|--------|--------|
| CPU % | `100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| Память % | `(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` |
| Диск % | `100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)` |
| Uptime (дни) | `(time() - node_boot_time_seconds) / 86400` |
| Load > CPU | `node_load1 > on(instance) count by(instance)(node_cpu_seconds_total{mode="idle"})` |
| RPS | `sum by(instance) (rate(http_requests_total[5m]))` |
| Ошибки % | `sum(rate(http_requests_total{status=~"[45].."}[5m])) / sum(rate(http_requests_total[5m])) * 100` |
| P99 latency | `histogram_quantile(0.99, sum by(le)(rate(http_request_duration_seconds_bucket[5m])))` |
| Top 5 CPU | `topk(5, rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100)` |
| Top 5 RAM | `topk(5, container_memory_working_set_bytes{name!=""})` |
| Прогноз диска | `predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*3600)` |
| Дней до полного | `node_filesystem_avail_bytes{mountpoint="/"} / (rate(node_filesystem_avail_bytes[6h]) * -1) / 86400` |
| Трафик | `rate(node_network_receive_bytes_total{device="eth0"}[5m])` |

---

## LogQL

### Label selectors (обязательная часть)

Фильтрация логов по labels (как PromQL, но для логов).

```logql
# Все логи из job
{job="varlogs"}

# Все логи контейнера nginx
{container="nginx"}

# Все логи с host = myserver
{job="docker", host="myserver"}

# Regex по label
{container=~"nginx|apache"}
```

### Line filters (фильтрация по содержимому)

```logql
# Содержит строку "error" (быстрый поиск)
{container="nginx"} |= "error"

# НЕ содержит "health" (исключить шум)
{container="nginx"} != "health"

# Regex: ERROR или FATAL
{container="nginx"} |~ "ERROR|FATAL"

# Regex отрицание: не содержит цифр
{container="nginx"} !~ "[0-9]+"

# Комбинирование: nginx И ошибка, но НЕ health
{container="nginx"} |= "error" != "health"
```

### Парсеры

#### JSON

```logql
# Парсить JSON-логи в структурированные поля
{container="myapp"} | json

# Фильтр по полю после парсинга
{container="myapp"} | json | level = "error"

# Достать поле из JSON
{container="myapp"} | json | user_id = "12345"

# JSON с ошибками (поля __error__)
{container="myapp"} | json | __error__ = ""  # только валидный JSON
```

#### logfmt

```logql
# Парсить logfmt-формат (key=value пробелы)
{job="nginx_access"} | logfmt

# Фильтр по полю
{job="nginx_access"} | logfmt | status = "500"

# Только валидные строки
{job="nginx_access"} | logfmt | __error__ = ""
```

#### pattern (нестандартный формат)

```logql
# Парсинг по шаблону с именованными полями
{container="myapp"} | pattern "<ip> - - <_> \"<method> <path> <_>\" <status> <size>"
```

### Metric queries (превратить логи в графики)

```logql
# rate() — скорость появления логов в секунду
rate({container="nginx"} |= "error" [5m])

# count_over_time() — количество строк за период
count_over_time({container="nginx"}[5m])

# Сумма по label
sum by(container) (rate({job="docker"} |= "error" [5m]))

# Топ-10 IP по числу запросов (nginx access log)
topk(10, sum by(remote_addr) (
  rate({job="nginx_access"} | logfmt | __error__="" [5m])
))

# Количество ошибок в минуту по каждому контейнеру
sum by(container) (
  count_over_time({job="docker"} |= "error" [1m])
)

# 99-й перцентиль длительности запросов (logfmt + quantile)
quantile_over_time(0.99,
  {job="nginx_access"} | logfmt | __error__="" | unwrap duration [5m]
)
```

### Полезные LogQL-запросы

| Задача | Запрос |
|--------|--------|
| Все логи контейнера | `{container="nginx"}` |
| Ошибки в контейнере | `{container="nginx"} |= "error"` |
| Исключить healthcheck | `{container="nginx"} != "health"` |
| JSON-логи уровня error | `{container="myapp"} | json | level="error"` |
| График ошибок в минуту | `rate({container="nginx"} |= "error" [1m])` |
| Количество строк в минуту | `count_over_time({container="nginx"}[1m])` |
| Топ ошибок по контейнерам | `topk(5, sum by(container) (count_over_time({job="docker"} |= "error" [5m])))` |

### Сравнение PromQL и LogQL

```text
PromQL (метрики)              | LogQL (логи)
------------------------------|------------------------------
node_memory_MemFree_bytes     | {job="varlogs"}
{instance="server1"}          | {container="nginx"}
rate(metric[5m])              | rate({container="nginx"}[5m])
sum by(instance)(metric)      | sum by(container)(rate(...))
topk(5, metric)               | topk(5, sum by(container)(...))
histogram_quantile(0.99, ...) | quantile_over_time(0.99, ... | unwrap value)
```

---

## Типичные ошибки PromQL

| Ошибка | Правильно | Почему |
|--------|-----------|--------|
| `rate(node_memory_MemFree_bytes[5m])` | `node_memory_MemFree_bytes` | `rate()` только для Counter, не для Gauge |
| `sum(metric)` без `by()` | `sum by(instance)(metric)` | Одно число вместо разбивки по серверам |
| `[1m]` при `scrape_interval=15s` | `[5m]` | Нужно минимум 4 точки (60s), рекомендуется 5m |
| `increase(metric[1h])` для restart | `increase(metric[1h])` | OK, но помнить что increase для Counter |
| `> 85` вместо `> 85` у процентов | `... * 100 > 85` | PromQL возвращает доли (0-1), умножать на 100 |
