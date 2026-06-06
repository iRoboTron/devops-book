# Глава 4: PromQL — 20 запросов для реальных задач

> **Запомни:** PromQL — это не язык программирования, а язык запросов к метрикам. Ты не пишешь программы, ты задаёшь вопросы: «сколько памяти осталось?», «какой RPS был за последние 5 минут?».

---

## Что вы узнаете

- основы синтаксиса PromQL: селекторы, range vector, instant vector;
- ключевые функции: `rate()`, `irate()`, `increase()`, `histogram_quantile()`;
- 20 конкретных запросов для диагностики и мониторинга;
- как агрегировать по labels через `by()` и `without()`;
- что такое перцентили и почему среднее задержки врёт.

**Цель:** ты не знаешь PromQL наизусть — ты знаешь 20 запросов для реальных задач и умеешь адаптировать их под свои метрики.

---

## Основы синтаксиса за 5 минут

### Селекторы (Instant Vector)

Выбрать метрику — самое простое:

```promql
node_memory_MemAvailable_bytes
```

Без уточнения вернутся значения для всех комбинаций labels. Если нужно одно значение — фильтруй:

```promql
node_memory_MemAvailable_bytes{instance="server1:9100"}
node_memory_MemAvailable_bytes{instance=~"server.*"}    # regex
node_memory_MemAvailable_bytes{instance=~"server1|server2"}
```

Операторы в селекторах:

| Оператор | Значение |
|----------|----------|
| `=`      | Равно |
| `!=`     | Не равно |
| `=~`     | Соответствует regex |
| `!~`     | Не соответствует regex |

### Range Vector

Это не отдельный запрос, а модификатор — «значения за последние N минут». Используется внутри функций:

```promql
node_cpu_seconds_total[5m]    # 5 минут истории
```

Range vector нельзя отобразить на графике напрямую — он нужен для `rate()`, `increase()`, `avg_over_time()` и других функций.

### Instant Vector

То что отображается на графике — одно значение на каждый момент времени:

```promql
node_memory_MemAvailable_bytes                    # текущее значение
rate(node_cpu_seconds_total{mode="idle"}[5m])     # скорость за 5 минут
```

---

## Ключевые функции

### rate() — сглаженная скорость

```promql
rate(http_requests_total[5m])    # запросов/сек, усреднённая за 5 минут
```

`rate()` вычисляет скорость изменения Counter за указанный интервал. Сглаживает пики — подходит для дашбордов и алертов. Всегда округляй интервал до периода > 4x scrape interval. Для `scrape_interval=15s` минимальный `[1m]`, рекомендуемый `[5m]`.

### irate() — мгновенная скорость

```promql
irate(http_requests_total[5m])   # запросов/сек, по последним двум точкам
```

`irate()` считает скорость по последним двум точкам данных. Чувствительнее к пикам — хорошо для диагностики, плохо для алертов (ложные срабатывания).

**Когда что использовать:**

| Функция | Для чего |
|---------|----------|
| `rate()` | Дашборды, алерты, тренды |
| `irate()` | Диагностика, поиск пиков, ad-hoc запросы |

### increase() — абсолютный прирост

```promql
increase(http_requests_total[1h])    # сколько запросов за последний час
```

Полезно для алертов: «сколько рестартов контейнера за час?»:

```promql
increase(container_restart_count[1h]) > 3
```

### Агрегация: sum, avg, max, min

```promql
sum(rate(http_requests_total[5m]))                        # суммарный RPS по всем инстансам
avg(node_memory_MemAvailable_bytes)                       # средняя память по всем серверам
max(node_load1)                                            # максимальный load среди всех серверов
```

### by() — группировать по label

```promql
# RPS по каждому серверу
sum by(instance) (rate(http_requests_total[5m]))

# RPS по кодам ответа
sum by(status_code) (rate(http_requests_total[5m]))

# RPS по серверу + код ответа
sum by(instance, status_code) (rate(http_requests_total[5m]))
```

### without() — агрегация по всем кроме указанных

```promql
# Суммарное CPU, не разбивая по cpu и mode
sum without(cpu, mode) (rate(node_cpu_seconds_total[5m]))
```

`without()` удобен когда не хочешь перечислять все labels которые нужно сохранить. `by(instance)` = `without(cpu, mode, job, ...)`. Выбирай что проще читается.

### topk() — топ N значений

```promql
# Топ-5 сервисов по потреблению CPU
topk(5, rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100)
```

`topk()` возвращает ровно K временных рядов с наибольшими значениями. Остальные отбрасывает.

---

## 20 запросов для реальных задач

### Сервер

**1. Использование CPU (%)**

```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

Базовый запрос для любой панели CPU. Показывает среднюю загрузку процессоров на каждом сервере. Если нужно по одному серверу — добавь фильтр `{instance="..."}`.

**2. Доступная память (%)**

```promql
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
```

MemAvailable, не MemFree. Если это значение меньше 15% — серверу не хватает памяти.

**3. Занятость диска (%)**

```promql
100 - (node_filesystem_avail_bytes{mountpoint="/"} /
       node_filesystem_size_bytes{mountpoint="/"} * 100)
```

Для мониторинга корневого раздела. Если нужно следить за `/var/lib/docker` — замени `mountpoint`.

**4. Uptime серверов (в днях)**

```promql
(time() - node_boot_time_seconds) / 86400
```

`time()` возвращает текущий timestamp UNIX. `node_boot_time_seconds` — timestamp когда сервер загрузился. Разница в секундах, деление на 86400 даёт дни. Сервер с uptime < 1 день после сбоя.

**5. Load average выше нормы**

```promql
node_load1 > on(instance) count by(instance)(node_cpu_seconds_total{mode="idle"})
```

Сравнивает load1 с числом CPU на том же сервере. Если load > CPU — сервер перегружен. Если даёт ложные срабатывания — увеличивай порог:

```promql
node_load1 > on(instance) count by(instance)(node_cpu_seconds_total{mode="idle"}) * 2
```

### Приложение

**6. RPS (запросов в секунду)**

```promql
sum by(instance) (rate(http_requests_total[5m]))
```

Предполагает что приложение экспортирует `http_requests_total` (Counter). Если у тебя `nginx_http_requests_total` или `api_requests_total` — замени имя метрики.

**7. Процент ошибок (4xx + 5xx)**

```promql
sum(rate(http_requests_total{status=~"[45].."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

Берёт все запросы с кодом 4xx и 5xx, делит на общее число запросов. Норма: < 1%. Если ошибок > 5% — проблема.

Если хочешь отдельно 4xx и 5xx:

```promql
# Ошибки клиента (4xx)
sum(rate(http_requests_total{status=~"4.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100

# Ошибки сервера (5xx)
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

5xx всегда критичнее 4xx.

**8. Задержка P99 через histogram**

```promql
histogram_quantile(0.99, sum by(le) (rate(http_request_duration_seconds_bucket[5m])))
```

Этот запрос нужно разобрать подробно. `http_request_duration_seconds` — это метрика типа Histogram. Она содержит `_bucket{le="0.1"}`, `_bucket{le="0.5"}`, ..., `_bucket{le="+Inf"}` — счётчики запросов которые уложились в каждый лимит.

`histogram_quantile(0.99, ...)` вычисляет: «99% запросов были быстрее какого значения?».

Подробнее про перцентили — в отдельном разделе ниже.

**9. Активные соединения с БД**

```promql
pg_stat_activity_count
```

Метрика PostgreSQL exporter. Если число активных соединений приближается к `max_connections` — пора увеличивать лимит или искать утечку соединений.

**10. Uptime сервиса (1 = работает, 0 = упал)**

```promql
up{job="myapp"}
```

Метрика `up` — встроенная в Prometheus. On означает что scrape прошёл успешно. Если 0 — таргет недоступен. Используется в алерте ServiceDown.

### Docker

**11. CPU контейнера (%)**

```promql
rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100
```

Фильтр `name!=""` исключает системные cgroup (их много, они зашумляют график). Значение — проценты от одного ядра. Если контейнер использует 200% — он занял 2 ядра.

**12. Память контейнера (байт)**

```promql
container_memory_usage_bytes{name!=""}
```

Используй `container_memory_working_set_bytes` вместо `container_memory_usage_bytes` — первая включает page cache и может сильно завышать реальное потребление.

**13. Контейнеры которые рестартовали за час**

```promql
increase(container_restart_count[1h]) > 0
```

Возвращает контейнеры с хотя бы одним рестартом за час. Если контейнер рестартует чаще чем раз в 10 минут — он нестабилен. Алерт: `> 3` за час.

### Диагностика

**14. Топ-5 сервисов по использованию CPU**

```promql
topk(5, rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100)
```

Кто жрёт CPU? Этот запрос показывает пятёрку самых прожорливых контейнеров.

**15. Топ-5 сервисов по потреблению памяти**

```promql
topk(5, container_memory_working_set_bytes{name!=""})
```

Аналогично для памяти. Если один контейнер стабильно в топе и использует > 80% лимита — ему нужен лимит побольше или оптимизация.

**16. Прогноз заполнения диска**

```promql
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*3600)
```

`predict_linear` экстраполирует тренд за последние 6 часов на 24 часа вперёд. Если прогноз показывает 0 — диск заполнится в ближайшие сутки.

**17. Количество дней до полного диска**

```promql
node_filesystem_avail_bytes{mountpoint="/"} /
(rate(node_filesystem_avail_bytes{mountpoint="/"}[6h]) * -1) / 86400
```

Более понятное выражение: сколько дней осталось. Если значение < 14 дней — пора чистить или расширять.

**18. Сетевой трафик (байт/сек)**

```promql
rate(node_network_receive_bytes_total{device="eth0"}[5m])
rate(node_network_transmit_bytes_total{device="eth0"}[5m])
```

Для конкретного интерфейса. На дашборде обычно показывают оба графика (входящий/исходящий) на одной панели.

**19. Таргеты которые недоступны**

```promql
up == 0
```

Мгновенно показывает какие таргеты упали. В алерте: `up{job!="pushgateway"} == 0` — исключаем Pushgateway, он всегда down когда нет активных job.

**20. Рестарты Kubernetes Pod'ов за час**

```promql
sum(increase(kube_pod_container_status_restarts_total[1h]))
```

Если у тебя нет Kubernetes — этот запрос не сработает. Аналог для Docker: `increase(container_restart_count{name!=""}[1h])`.

---

## histogram_quantile — перцентили задержки

### Почему среднее (avg) врёт

Представь: 99 запросов выполнились за 10 мс, а один — за 10 секунд. Среднее: ~110 мс. По среднему всё `normal` — 110 мс это нормально. А реально 1% пользователей ждали 10 секунд.

Перцентили показывают правду:

- **P50 (медиана)** — половина запросов быстрее этого значения.
- **P95** — 95% запросов быстрее. Только 5% медленнее.
- **P99** — 99% запросов быстрее. Только 1% медленнее.

### Практические значения

| Перцентиль | Норма для API | Тревога |
|-----------|---------------|---------|
| P50 | < 50 мс | > 200 мс |
| P95 | < 200 мс | > 500 мс |
| P99 | < 500 мс | > 2 с |

### Как работает histogram_quantile

Prometheus хранит Histogram в виде бакетов:

```text
http_request_duration_seconds_bucket{le="0.01"}    500   # 500 запросов до 10 ms
http_request_duration_seconds_bucket{le="0.05"}   1200   # 1200 запросов до 50 ms
http_request_duration_seconds_bucket{le="0.1"}    1500
http_request_duration_seconds_bucket{le="0.5"}    1800
http_request_duration_seconds_bucket{le="+Inf"}   2000   # всего 2000 запросов
```

`histogram_quantile(0.99, ...)` берёт бакеты и вычисляет: «99% из 2000 = 1980-й запрос по скорости. Между какими бакетами он находится?». Ответ: между `le="0.5"` (1800 запросов) и `le="+Inf"` (2000 запросов) — линейно интерполирует внутри бакета.

**Важно:** чтобы histogram_quantile работал корректно, нужно `sum by(le)`. Если не агрегировать по le, buckets не будут отсортированы и результат будет мусором.

**Важно 2:** Для правильного P99 нужно чтобы счётчик `le="+Inf"` совпадал с `_count`. Если они не равны — часть запросов не попала в бакеты.

---

## Типичные ошибки

- `rate()` применять к Gauge — неверно. `rate()` только для Counter. Для Gauge используй значение напрямую или `deriv()`.
- `[5m]` слишком мало при `scrape_interval=15s` — нужно минимум 4 точки (60s). Рекомендация: `[5m]` для scrape_interval 15s, `[10m]` для 30s.
- `sum()` без `by()` суммирует всё в одно число — теряешь информацию по инстансам. Если на дашборде общий RPS — `sum(rate(...))`. Если по серверам — `sum by(instance) (rate(...))`.
- `histogram_quantile` без `sum by(le)` — `le` label должен быть сохранён, иначе бакеты не сгруппируются правильно.
- Использование `irate()` для алертов — ложные срабатывания на каждом scrape. Для алертов всегда `rate()`.
- Не фильтровать пустые labels в cAdvisor — `container_cpu_usage_seconds_total` без `{name!=""}` вернёт тысячи системных cgroup.

---

## Чек-лист для самопроверки

- [ ] Знаю разницу между `rate()` и `irate()` и когда что использовать
- [ ] Умею агрегировать метрики через `sum by(label)()`
- [ ] Умею написать запрос для CPU, памяти, RPS, процента ошибок
- [ ] Понимаю что `predict_linear()` прогнозирует на будущее
- [ ] Знаю что P99 показывает задержку для худшего 1% запросов
- [ ] Понимаю почему среднее (avg) задержки не надёжно
- [ ] Умею фильтровать виртуальные интерфейсы и файловые системы

---

## Попробуйте сами

1. Введите 5 любых запросов из списка выше в Prometheus UI. Убедитесь что все работают и возвращают значения. Попробуйте изменить `[5m]` на `[1m]` — график стал более «рваным»? Это потому что меньше точек усреднения.

2. Напишите запрос: «процент CPU в режиме iowait за последние 5 минут по каждому ядру»:
   ```promql
   rate(node_cpu_seconds_total{mode="iowait"}[5m]) * 100
   ```
   Если iowait > 5% хотя бы на одном ядре — запустите нагрузку на диск: `dd if=/dev/zero of=/tmp/test bs=1M count=500 &`. Наблюдайте за ростом iowait.

3. Используйте `predict_linear` для диска:
   ```promql
   predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*3600)
   ```
   Если диск не растёт — создайте временный файл:
   ```bash
   dd if=/dev/zero of=/tmp/fill bs=1M count=200
   ```
   Подождите 10-15 минут, чтобы появился тренд. Затем перезапустите запрос — видно что прогнозное значение уменьшается?

4. Найдите метрику `up`:
   ```promql
   up
   ```
   Все значения 1? Остановите Node Exporter: `docker compose stop node_exporter`. Через `scrape_interval` значение станет 0. Запустите снова — вернётся к 1.

5. Добавьте панель с P99 в Grafana. Используйте:
   ```promql
   histogram_quantile(0.99, sum by(le) (rate(http_request_duration_seconds_bucket[5m])))
   ```
   Если у тебя нет метрики `http_request_duration_seconds` — это нормально. Запомни синтаксис, он пригодится когда появится Histogram.
