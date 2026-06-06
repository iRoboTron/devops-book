# Глава 3: Node Exporter — метрики сервера

> **Запомни:** Node Exporter превращает сервер в источник метрик. После этой главы ты будешь читать дашборд как показания приборной панели.

---

## Что вы узнаете

- какие метрики отдаёт Node Exporter и что они означают;
- как читать CPU, память, диск и сеть в Prometheus через PromQL;
- какие коллекторы включены по умолчанию и какие стоит добавить;
- как мониторить несколько серверов в одном job.

**Цель:** ты видишь дашборд с метриками сервера и понимаешь каждую панель. Знаешь какие метрики сигнализируют о проблеме, а какие — просто цифры.

---

## Как Node Exporter устроен

Node Exporter — это агент, который читает `/proc`, `/sys` и другие псевдо-файловые системы Linux и отдаёт их в формате Prometheus. Он не хранит данные, не считает тренды — только экспортирует текущее состояние системы в метрики.

Статус коллекторов можно проверить:

```bash
curl -s http://localhost:9100/metrics | head -20
```

По умолчанию включены все безопасные коллекторы. Некоторые (например, `perf`, `processes` с большим числом процессов) отключены, потому что могут создавать нагрузку.

---

## Ключевые метрики CPU

Процессор — первое куда смотришь при замедлении работы. Node Exporter отдаёт метрики через `node_cpu_seconds_total` — это счётчик (Counter), который показывает сколько секунд каждое ядро провело в каждом режиме.

### Режимы CPU

| Режим    | Что означает |
|----------|-------------|
| `idle`   | Процессор ничего не делает |
| `user`   | Выполняется код приложений |
| `system` | Выполняется код ядра (системные вызовы) |
| `iowait` | Процессор ждёт завершения операций ввода-вывода (диск) |
| `steal`  | Гипервизор использует CPU для других виртуальных машин (только VPS) |

### Общее использование CPU (%)

```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

Это самый популярный запрос. Он берёт `idle` (простой), усредняет по всем ядрам, переводит в проценты и вычитает из 100. Результат — насколько загружен процессор в среднем.

Для просмотра по каждому ядру отдельно — убери `avg`:

```promql
100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)
```

### Использование по режимам

```promql
rate(node_cpu_seconds_total[5m])
```

Этот запрос покажет все режимы сразу: `user`, `system`, `iowait`, `idle`. На графике ты увидишь какая часть CPU уходит на приложения, какая на ядро, а какая на ожидание диска.

### iowait — индикатор проблем с диском

```promql
rate(node_cpu_seconds_total{mode="iowait"}[5m])
```

Значение > 0.3 (30% одного ядра ждёт диск) — повод проверить подсистему ввода-вывода. Если средний iowait по всем ядрам > 0.1, это уже заметное замедление работы сервисов.

**Когда iowait растёт:**

- диск перегружен (много случайных операций);
- один медленный диск тащит все операции;
- файловая система fragmented или неправильный планировщик;
- на VPS — сосед по гипервизору нагружает общее хранилище.

---

## Метрики памяти

Здесь самая частая ошибка новичков — путать `MemFree` и `MemAvailable`.

### MemFree vs MemAvailable

```promql
# Свободная память (физически не используется)
node_memory_MemFree_bytes

# Доступная память (реально доступна приложениям)
node_memory_MemAvailable_bytes
```

- **MemFree** — память которая вообще не используется. Ничем. Linux держит её минимум, потому что свободная память — бесполезная память.
- **MemAvailable** — MemFree + память в кэше, которую ядро может немедленно отдать приложению. Если приложению нужно 1 ГБ памяти, ядро выкинет ненужный кэш и отдаст эти 1 ГБ.

> Для мониторинга всегда используй `MemAvailable`. Если упало `MemFree` — это нормально. Если упало `MemAvailable` — память реально кончается.

### Использование памяти в процентах

```promql
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
```

Нормальное значение: 40–70%. Выше 85% — пора смотреть что съедает память. Выше 95% — OOM Killer может убить процесс в любой момент.

### Использование Swap

```promql
(1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes) * 100
```

Если swap используется не ноль (или больше 10%) при наличии свободной памяти — значит у тебя неправильно настроен `swappiness`. На сервере обычно ставят `vm.swappiness=1` или `10`. Проверить:

```bash
cat /proc/sys/vm/swappiness
```

Если swap заполняется и `MemAvailable` низкий — память реально кончилась.

---

## Метрики диска

Делим на две группы: занятое место (пространство) и активность (I/O).

### Занятое место в процентах

```promql
100 - (node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.lxcxs"} /
       node_filesystem_size_bytes * 100)
```

Фильтр `fstype!~"tmpfs|fuse.lxcxs"` исключает виртуальные файловые системы (tmpfs, cgroup, devtmpfs). Без него ты получишь десятки мусорных точек монтирования.

Конкретный раздел:

```promql
100 - (node_filesystem_avail_bytes{mountpoint="/"} /
       node_filesystem_size_bytes{mountpoint="/"} * 100)
```

- < 80% — зелёная зона
- 80–90% — пора чистить или расширять
- > 90% — алерт, диск может заполниться в ближайшие дни

### Скорость чтения/записи (байт/сек)

```promql
rate(node_disk_read_bytes_total[5m])
rate(node_disk_written_bytes_total[5m])
```

Показывает реальный поток данных на диски. На SSD нормой считается 200–500 МБ/с. Если видишь 5 МБ/с при 100% iowait — диск узкое место.

### IOPS (операций ввода-вывода в секунду)

```promql
rate(node_disk_reads_completed_total[5m])
rate(node_disk_writes_completed_total[5m])
```

IOPS важнее чем байты, если приложение делает много маленьких операций (базы данных). 1000 IOPS на HDD — предел. 50000+ на NVMe — норма.

### I/O utilization (время занятости диска)

```promql
rate(node_disk_io_time_seconds_total[5m]) * 100
```

Показывает какой процент времени диск был занят. 100% при этом скорость 5 МБ/с — диск упёрся в IOPS, а не в пропускную способность. 100% при 500 МБ/с — диск утилизирован нормально, это его предел.

---

## Метрики сети

### Трафик (байт/сек)

```promql
rate(node_network_receive_bytes_total{device!~"lo|veth.*|docker.*|br-.*"}[5m])
rate(node_network_transmit_bytes_total{device!~"lo|veth.*|docker.*|br-.*"}[5m])
```

Фильтр исключает loopback (lo) и виртуальные интерфейсы Docker (veth, docker, br-). Без него на графике будет каша из десятков интерфейсов, большинство из которых с нулевым трафиком.

Если нужно конкретное устройство:

```promql
rate(node_network_receive_bytes_total{device="eth0"}[5m])
```

### Ошибки сетевого интерфейса

```promql
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])
```

Любое ненулевое значение — проблема:

- `receive_errs` — плохой кабель, несовпадение duplex, слишком длинная линия;
- `transmit_errs` — перегрузка буфера, коллизии;

Для диагностики также смотреть:

```promql
rate(node_network_receive_drop_total[5m])
rate(node_network_transmit_drop_total[5m])
```

Drop означает что пакеты отброшены из-за переполнения буфера — сеть не справляется с объёмом.

---

## Системные метрики

### Load Average

```promql
node_load1   # за 1 минуту
node_load5   # за 5 минут
node_load15  # за 15 минут
```

Load average — количество процессов ожидающих CPU + количество процессов в состоянии I/O wait. Это не процент загрузки, а длина очереди.

**Как интерпретировать:**

- `load1 < число_CPU` — всё хорошо
- `load1 = число_CPU` — процессоры загружены полностью
- `load1 > число_CPU * 2` — серьёзная перегрузка

```promql
# Сравнить load1 с числом CPU
node_load1 > on(instance) count by(instance)(node_cpu_seconds_total{mode="idle"})
```

Запрос возвращает 1 (тревога) если load1 превышает количество ядер.

**Нюанс:** высокий load при низком CPU usage — значит нагрузка создаётся iowait. Если load = 8, CPU idle = 90%, процессы ждут диск. Лечится заменой HDD на SSD или оптимизацией запросов к БД.

### Количество CPU

```promql
count by(instance) (node_cpu_seconds_total{mode="idle"})
```

Нужно для расчёта нормы load average и для отображения числа ядер на дашборде.

### Uptime сервера

```promql
time() - node_boot_time_seconds
```

Показывает сколько секунд сервер работает без перезагрузки. Для отображения в днях:

```promql
(time() - node_boot_time_seconds) / 86400
```

Если uptime < 1 часа и не было планового рестарта — сервер аварийно перезагрузился (kernel panic, OOM, отключение питания).

### Файловые дескрипторы

```promql
node_filefd_allocated / node_filefd_maximum * 100
```

Показывает сколько процентов от лимита открытых файлов занято. Если значение приближается к 100% — процессы не могут открывать новые файлы и соединения. Типичная ситуация: утечка файловых дескрипторов в приложении.

---

## Коллекторы Node Exporter

Node Exporter включает коллекторы по умолчанию. Вот основные:

| Коллектор | Метрики | По умолчанию |
|-----------|---------|-------------|
| `cpu` | `node_cpu_seconds_total` | Да |
| `meminfo` | `node_memory_*` | Да |
| `filesystem` | `node_filesystem_*` | Да |
| `diskstats` | `node_disk_*` | Да |
| `netdev` | `node_network_*` | Да |
| `loadavg` | `node_load*` | Да |
| `stat` | `node_boot_time`, `node_intr` | Да |
| `textfile` | Пользовательские метрики из файлов | Да |
| `systemd` | Состояние systemd-юнитов | Нет |
| `processes` | `node_processes_*` (число процессов) | Нет |
| `ntp` | Смещение времени NTP | Нет |

Чтобы включить отключённый коллектор, добавь флаг при запуске:

```text
--collector.systemd
--collector.processes
```

Пример в `docker-compose.yml`:

```yaml
command:
  - '--path.procfs=/host/proc'
  - '--path.rootfs=/rootfs'
  - '--path.sysfs=/host/sys'
  - '--collector.systemd'
  - '--collector.processes'
```

### Textfile Collector — свои метрики из скриптов

Если нужно добавить метрику, которой нет в Node Exporter (например, температура CPU или статус RAID-массива):

```bash
#!/bin/bash
# /usr/local/bin/node_custom_metrics.sh
echo 'custom_temperature_celsius{chip="cpu"} 55' > /var/lib/node_exporter/textfile/custom.prom
```

Node Exporter читает файлы из директории `--collector.textfile.directory` при каждом scrape.

---

## Мониторинг нескольких серверов

Node Exporter ставится на каждый сервер. Prometheus опрашивает их все:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'nodes'
    static_configs:
      - targets:
          - 'server1:9100'
          - 'server2:9100'
          - 'server3:9100'
```

Если серверов много — используй `file_sd_configs`:

```yaml
  - job_name: 'nodes'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/nodes/*.json'
        refresh_interval: 30s
```

Содержимое файла `nodes/production.json`:

```json
[
  {
    "targets": ["10.0.1.10:9100", "10.0.1.11:9100"],
    "labels": {"env": "production"}
  },
  {
    "targets": ["10.0.2.10:9100"],
    "labels": {"env": "staging"}
  }
]
```

Так можно добавлять новые серверы без перезагрузки Prometheus — просто кладёшь новый JSON-файл.

### В Grafana

Для переключения между серверами используется переменная `$instance` (подробно в Главе 5). В PromQL она подставляется так:

```promql
node_memory_MemAvailable_bytes{instance="$instance"}
```

---

## Что показывает каждая панель на дашборде

Когда ты импортируешь дашборд Node Exporter Full (ID 1860), вот что означают его панели:

| Панель | Метрика | Норма | Тревога |
|--------|---------|-------|---------|
| CPU Usage | `100 - idle%` | < 70% | > 85% |
| Memory Usage | `MemAvailable` | > 30% | < 15% |
| Disk Space | `node_filesystem_avail` | < 80% filled | > 90% |
| Disk I/O | `rate(node_disk_*_bytes)` | < 50 MB/s | > 200 MB/s |
| Network Traffic | `rate(node_network_*_bytes)` | зависит от канала | > 80% пропускной способности |
| Load Average | `node_load*` | < CPU count | > CPU count * 2 |

---

## Типичные ошибки

- `node_memory_MemFree_bytes` показывает мало — это не значит что память кончается. Linux использует свободную память под кэш. Смотреть `MemAvailable`.
- Load average > числа CPU — не всегда плохо если это I/O wait. Смотреть CPU mode iowait.
- Фильтр сетевых интерфейсов `device!~"lo|veth.*|docker.*"` — без него метрики замусориваются десятками виртуальных интерфейсов Docker.
- `node_filesystem_*` без `fstype!~"tmpfs"` — панель показывает tmpfs (виртуальные ФС в RAM), у них всегда 100% занятости.
- Не отключены ненужные коллекторы на слабых серверах — каждый коллектор это `read()` из `/proc` и немного нагрузки. На 512 MB VPS стоит отключить лишнее флагами `--no-collector.<name>`.
- Использование `rate()` для Gauge-метрик — ошибка. `rate()` только для Counter. Для Gauge (как `node_memory_MemFree_bytes`) используй значение напрямую.

---

## Чек-лист для самопроверки

- [ ] Знаю PromQL-запросы для CPU, памяти, диска и сети
- [ ] Понимаю разницу между MemFree и MemAvailable
- [ ] Знаю что load average > числа CPU — сигнал проблемы
- [ ] Умею отличать CPU bottleneck от I/O bottleneck
- [ ] Могу объяснить что такое iowait и когда это проблема
- [ ] Умею добавить несколько серверов в один job
- [ ] Знаю какие коллекторы включены по умолчанию
- [ ] Понимаю как фильтровать виртуальные сетевые интерфейсы

---

## Попробуйте сами

1. Запустите стек из Главы 1. Откройте Prometheus UI и введите:
   ```
   100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
   ```
   Какое использование CPU прямо сейчас? Запустите `stress --cpu 2 --timeout 30` (если нет stress: `apt install stress`). Через 15 секунд проверьте график — как изменилось значение?

2. Введите запрос для доступной памяти:
   ```
   (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
   ```
   Запустите что-то тяжёлое:
   ```bash
   docker pull ubuntu:latest
   ```
   Наблюдайте за памятью 2–3 минуты. Потребовалось ли больше памяти на скачивание? После завершения — вернулась ли память к исходному значению?

3. Найдите метрики диска. Создайте тестовую нагрузку:
   ```bash
   dd if=/dev/zero of=/tmp/test bs=1M count=500
   ```
   После этой команды проверьте:
   ```
   rate(node_disk_written_bytes_total[5m])
   ```
   Видна ли запись на графике? Через 1–2 минуты значение должно вернуться к обычному уровню.

4. Настройте мониторинг второго сервера. Если есть второй сервер — установите Node Exporter и добавьте в `prometheus.yml`. Если нет — добавьте `localhost:9100` как второй таргет. Убедитесь что оба сервера отображаются в Prometheus Targets.

5. Искусственно поднимите load average:
   ```bash
   stress --cpu 4 --timeout 60 &
   dd if=/dev/zero of=/tmp/test bs=1M count=1000 &
   ```
   Следите за `node_load1` и `node_cpu_seconds_total{mode="iowait"}`. Через минуту процессы завершатся — load вернётся к норме. Это наглядная демонстрация как нагрузка на CPU и диск влияет на load average.
