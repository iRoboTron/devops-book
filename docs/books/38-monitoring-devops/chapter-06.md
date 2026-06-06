# Глава 6: cAdvisor — метрики Docker-контейнеров

## Что вы узнаете

- как cAdvisor собирает метрики Docker-контейнеров;
- ключевые метрики: CPU, память, сеть, рестарты контейнера;
- как построить дашборд по контейнерам;
- ограничения cAdvisor.

**Цель:** читатель видит сколько CPU и памяти потребляет каждый контейнер и получает алерт при частых рестартах.

---

## Зачем нужен cAdvisor

Prometheus через Node Exporter видит метрики хоста — загрузку CPU, памяти, диска. Но Node Exporter не знает про Docker-контейнеры. Если на одном сервере крутятся 10 контейнеров — мы видим только общую нагрузку на хост, но не знаем какой именно контейнер потребляет ресурсы.

**cAdvisor** (Container Advisor) решает эту проблему: он читает cgroups и namespaces ядра Linux и экспортирует метрики каждого контейнера в формате Prometheus.

cAdvisor запускается в Docker-контейнере, монтирует системные директории хоста и отдаёт метрики на порту 8080.

---

## Добавить cAdvisor в docker-compose.yml

Добавьте сервис в docker-compose.yml:

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

> ☠️ **Осторожно:** cAdvisor требует `privileged: true` для доступа к cgroups. Без этого ключевые метрики (память, сеть, диск) будут недоступны или некорректны. Проброс `/dev/kmsg` нужен чтобы избежать ошибок в логах cAdvisor на современных ядрах Linux.

Добавьте в Prometheus новый job scrape:

```yaml
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

Пересоздайте контейнеры:

```bash
docker compose up -d
```

Проверьте что cAdvisor появился в Prometheus targets:

```text
Prometheus UI → Status → Targets → cadvisor (UP)
```

---

## Ключевые метрики контейнеров

### CPU контейнера

Метрика `container_cpu_usage_seconds_total` — Counter, общее время CPU контейнера в секундах. Чтобы получить процент использования от одного ядра:

```promql
rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100
```

Если хотите процент от всех ядер (например на 4-ядерной машине 200% значит 2 полных ядра):

```promql
rate(container_cpu_usage_seconds_total{name!=""}[5m]) / on(instance) count by(instance)(container_cpu_usage_seconds_total{name!=""}) * 100
```

### Память

**Главное различие:** `container_memory_usage_bytes` включает page cache — то есть память которая фактически занята не данными приложения, а кэшированными блоками диска. Linux может вытеснить page cache в любой момент. Поэтому реальное потребление памяти показывает `container_memory_working_set_bytes`.

```promql
# Память (байт) — рабочее множество без кэша
container_memory_working_set_bytes{name!=""}
```

```promql
# Память в % от лимита (если установлен limit)
container_memory_working_set_bytes
  / container_spec_memory_limit_bytes * 100
```

> ☠️ **Осторожно:** `container_memory_usage_bytes` может показывать в 2-3 раза больше реального потребления из-за page cache. Всегда используйте `container_memory_working_set_bytes` для мониторинга и алертов. Если у контейнера нет явного лимита памяти (`container_spec_memory_limit_bytes` равен 0 или 2^64), деление на лимит не сработает — проверяйте наличие лимита через `container_spec_memory_limit_bytes > 0`.

### Сеть

```promql
# Получено байт/сек
rate(container_network_receive_bytes_total{name!=""}[5m])

# Отправлено байт/сек
rate(container_network_transmit_bytes_total{name!=""}[5m])

# Ошибки сети (пакеты)
rate(container_network_receive_errors_total{name!=""}[5m])
rate(container_network_transmit_errors_total{name!=""}[5m])
```

Метрики сети общие для всех интерфейсов контейнера. Если у контейнера несколько сетей (например bridge + overlay), данные по каждой сети доступны через метку `interface`.

### Рестарты контейнера

```promql
# Число рестартов всего (для панели Stat)
container_restart_count{name!=""}

# Рестарты за последний час (для алертов)
increase(container_restart_count{name!=""}[1h])
```

Значение `container_restart_count` показывает сколько раз Docker перезапускал контейнер с момента его создания. Если контейнер имеет `restart: unless-stopped` и падает — счётчик растёт.

### Статус контейнера

```promql
container_last_seen{name!=""}
```

Метрика показывает timestamp когда контейнер был последний раз виден cAdvisor. Если контейнер остановлен — метрика перестаёт обновляться и через 5-10 минут исчезает из результатов.

---

## Метки cAdvisor и фильтрация шума

cAdvisor собирает метрики для всех cgroups на системе — включая служебные, системные и пустые. При запросах к Prometheus нужно обязательно фильтровать шум.

### Основные метки

- `name` — имя контейнера (например `nginx`, `prometheus`)
- `image` — образ (например `nginx:1.25`)
- `id` — полный ID контейнера
- `container` — альтернативное имя (в новых версиях вместо `name`)

### Фильтрация

Базовая фильтрация:

```promql
{name!="", image!=""}
```

Исключение служебных контейнеров:

```promql
{name!="", name!~".*cadvisor.*", name!~".*prometheus.*", image!=""}
```

Или через метку `container` (для новых версий):

```promql
{container!="", container!="POD"}
```

Лучший подход — создать recording rule или переменную в Grafana для списка отслеживаемых контейнеров. Но для большинства случаев достаточно `name!=""`.

---

## Топ контейнеров по ресурсам через topk

Функция `topk(k, query)` возвращает k записей с наибольшими значениями.

### Топ-10 контейнеров по памяти

```promql
topk(10, container_memory_working_set_bytes{name!=""})
```

### Топ-5 контейнеров по CPU

```promql
topk(5, rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100)
```

### Топ-10 по сетевому трафику

```promql
topk(10, rate(container_network_receive_bytes_total{name!=""}[5m]))
```

> ☠️ **Осторожно:** `topk()` возвращает нестабильные результаты — на каждом scrape список контейнеров может меняться местами. Для дашбордов используйте `topk()` только с сортировкой, а для алертов не используйте topk вообще — алерт должен срабатывать на конкретный контейнер, а не на «кто сейчас в топе».

---

## Дашборд контейнеров в Grafana

Создайте дашборд с панелями:

### Панель 1: CPU контейнеров (Time series)

```promql
rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100
```

Legend: `{{name}}`
Unit: `percent` (0-100)

### Панель 2: Память (Time series)

```promql
topk(10, container_memory_working_set_bytes{name!=""})
```

Unit: `bytes (IEC)` — отобразит в GiB/MiB

### Панель 3: Сеть (Time series)

```promql
rate(container_network_receive_bytes_total{name!=""}[5m])
```

### Панель 4: Рестарты (Stat или Table)

```promql
container_restart_count{name!=""}
```

Threshold: красный если `restart_count > 3`

### Панель 5: Использование лимита памяти (Gauge)

```promql
(container_memory_working_set_bytes / container_spec_memory_limit_bytes) * 100
```

Filter: `container_spec_memory_limit_bytes > 0` (только контейнеры с лимитом)

---

## Алерты на основе метрик cAdvisor

Метрики cAdvisor можно использовать в alert rules (подробно в Главе 8). Два самых полезных алерта:

**Контейнер часто перезапускается:**

```yaml
- alert: ContainerRestarting
  expr: increase(container_restart_count[1h]) > 3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Контейнер {{ $labels.name }} перезапускается"
    description: "{{ $value | printf \"%.0f\" }} рестартов за час"
```

**Контейнер не использует лимит памяти (potential waste):**

```promql
(container_spec_memory_limit_bytes > 0)
  and
(container_memory_working_set_bytes / container_spec_memory_limit_bytes < 0.1)
```

Этот запрос находит контейнеры с лимитом памяти, которые используют меньше 10% от лимита — сигнал что ресурсы выделены с запасом.

**Контейнер не имеет лимита памяти:**

```promql
container_memory_working_set_bytes{name!=""}
  unless on(name) container_spec_memory_limit_bytes > 0
```

Контейнер без лимита может потребить всю память хоста — в production всегда устанавливайте `--memory` лимиты.

## Ограничения cAdvisor

1. **Не хранит метрики.** cAdvisor только собирает и отдаёт — он не заменяет Prometheus. Хранение обеспечивает Prometheus.
2. **Нет агрегации.** Каждый контейнер — отдельный временной ряд. Если у вас 100 контейнеров — Prometheus получает 100 рядов только для CPU. Это нормально до 500-1000 контейнеров на один cAdvisor.
3. **Нет исторических данных.** cAdvisor показывает метрики с момента своего запуска. При перезапуске cAdvisor данные начинаются с нуля (но Prometheus хранит историю).
4. **Нет метрик логов.** cAdvisor не анализирует stdout/stderr контейнеров. Для логов нужен Loki (Глава 9).
5. **Netdata vs cAdvisor.** Netdata даёт больше метрик (диск, сеть по интерфейсам, процессы) и имеет встроенный дашборд. cAdvisor — легковесное решение только для контейнеров.
6. **k8s:** для Kubernetes есть встроенный kubelet который отдаёт метрики pod-ов через `/metrics/cadvisor`. Отдельный cAdvisor в k8s не нужен — kubelet сам поставляется с cAdvisor внутри.

---

## Типичные ошибки

- `container_memory_usage_bytes` включает page cache — показывает больше чем реально используется. Для мониторинга: `container_memory_working_set_bytes`.
- cAdvisor нужен `privileged: true` — без него часть метрик недоступна (память, сеть, диск).
- Много шума от служебных контейнеров: `k8s_POD`, `infra`, пустые имена. Всегда добавлять фильтр `name!=""`.
- Пропущен проброс `/dev/kmsg` — в логах cAdvisor появляются ошибки `open /dev/kmsg: no such file or directory`. На новых ядрах это приводит к потере метрик.
- `topk()` на алертах — непредсказуемое поведение. Алерт должен быть на конкретный контейнер, а не на «самый жирный в топе».
- Port mapping cAdvisor через `0.0.0.0:8080:8080` (без `127.0.0.1`) — cAdvisor доступен снаружи, что даёт информацию о всех контейнерах на хосте.

---

## Чек-лист для самопроверки

- [ ] cAdvisor запущен и виден в Prometheus targets
- [ ] Умею найти топ-5 контейнеров по памяти через `topk()`
- [ ] Настроил алерт на частые рестарты контейнера
- [ ] Понимаю разницу между `memory_usage_bytes` и `memory_working_set_bytes`
- [ ] Фильтрую служебные контейнеры через `name!=""`
- [ ] cAdvisor слушает только на `127.0.0.1:8080`
- [ ] Знаю что у cAdvisor нет встроенного хранения — данные хранит Prometheus

---

## Попробуйте сами

1. Запустите ресурсоёмкий контейнер:
   ```bash
   docker run -d --name stress polinux/stress \
     stress --cpu 1 --vm 1 --vm-bytes 256M
   ```
   Найдите его в Prometheus по `container_cpu_usage_seconds_total`. Через 2 минуты остановите контейнер.

2. Создайте в Grafana панель «Топ-10 контейнеров по памяти» используя `topk(10, container_memory_working_set_bytes{name!=""})`. Убедитесь что в топе действительно ваш `stress` контейнер.

3. Принудительно убейте контейнер (`docker kill <id>`). Docker его перезапустит (если `restart: unless-stopped`). Нашли ли увеличение `container_restart_count` в метриках?

4. Запустите `docker run -d --name nginx nginx:alpine`. Проверьте метрики сети: сколько байт получено/отправлено за минуту? Зайдите в контейнер через `docker exec` и выполните `apt update && apt install curl && curl google.com` — отследите рост сетевых метрик в Prometheus.

5. Удалите контейнер `stress`, создайте новый с `--memory="128m"`. Проверьте значение `container_spec_memory_limit_bytes` — равно ли оно 134217728 (128 MiB)? Рассчитайте процент использования лимита.
