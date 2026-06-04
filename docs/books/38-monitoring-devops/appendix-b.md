# Приложение B: Готовые alert rules

Полный файл `prometheus/rules/alerts.yml` со всеми правилами алертинга из книги. Разделы: Infrastructure, Containers, Services, Applications, SSL, Pushgateway, Watchdog.

Файл должен быть подключён в `prometheus.yml`:

```yaml
rule_files:
  - '/etc/prometheus/rules/*.yml'
```

---

## prometheus/rules/alerts.yml

```yaml
# prometheus/rules/alerts.yml
# Правила алертинга Prometheus
# Группировка по категориям: infrastructure, containers, services, pushgateway
#
# Переменные шаблонов в annotations:
#   {{ $labels.instance }}   — таргет (ip:port)
#   {{ $labels.job }}        — имя job из prometheus.yml
#   {{ $labels.severity }}   — critical / warning / info
#   {{ $value }}             — численное значение метрики в момент срабатывания
#   {{ $labels.mountpoint }} — точка монтирования (для дисков)
#   {{ $labels.name }}       — имя контейнера (cAdvisor)
#
# Жизненный цикл:
#   INACTIVE -> PENDING (for: время) -> FIRING -> Alertmanager -> уведомление

groups:

  # =============================================
  # INFRASTRUCTURE: базовые метрики сервера
  # CPU, память, диск, сеть, системная нагрузка
  # =============================================
  - name: infrastructure
    interval: 30s

    # Сервис недоступен
    # expr: up == 0 когда Prometheus не может получить метрики с таргета
    # Это базовое правило: если таргет не отвечает — проблема с сетью или сервисом
    - alert: ServiceDown
      expr: up == 0
      for: 1m                 # ждать 1 минуту (исключить кратковременные сбои)
      labels:
        severity: critical
      annotations:
        summary: "Сервис {{ $labels.job }} недоступен"
        description: "Таргет {{ $labels.instance }} не отвечает больше 1 минуты"

    # Высокое использование CPU
    # Норма: < 70%. Тревога: > 85% более 5 минут
    - alert: HighCPU
      expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Высокий CPU на {{ $labels.instance }}"
        description: "CPU {{ $value | printf \"%.1f\" }}% больше 5 минут"

    # Экстремально высокий CPU
    - alert: CriticalCPU
      expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 95
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Критический CPU на {{ $labels.instance }}"
        description: "CPU {{ $value | printf \"%.1f\" }}% больше 2 минут"

    # Мало доступной памяти
    # Используем MemAvailable (учитывает кэш), не MemFree
    - alert: LowMemory
      expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 15
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Мало памяти на {{ $labels.instance }}"
        description: "Доступно {{ $value | printf \"%.1f\" }}% памяти"

    # Критически мало памяти
    - alert: CriticalMemory
      expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 5
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Критический дефицит памяти на {{ $labels.instance }}"
        description: "Доступно {{ $value | printf \"%.1f\" }}% — OOM killer может сработать"

    # Диск почти полный
    # Мониторинг корневого раздела (изменить mountpoint для других разделов)
    - alert: DiskAlmostFull
      expr: 100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100) > 85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Диск заполнен на {{ $value | printf \"%.0f\" }}%"
        description: "{{ $labels.instance }}: диск {{ $labels.mountpoint }} заполнен на {{ $value | printf \"%.0f\" }}%"

    # Диск критически полный
    - alert: DiskCritical
      expr: 100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100) > 95
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Диск почти полностью заполнен на {{ $value | printf \"%.0f\" }}%"
        description: "{{ $labels.instance }}: осталось менее 5% свободного места"

    # Высокая нагрузка на дисковую подсистему (I/O util > 90%)
    - alert: HighDiskIO
      expr: rate(node_disk_io_time_seconds_total[5m]) * 100 > 90
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Высокая загрузка диска на {{ $labels.instance }}"
        description: "I/O utilization {{ $value | printf \"%.0f\" }}% более 5 минут"

    # Ошибки на сетевых интерфейсах
    - alert: NetworkErrors
      expr: rate(node_network_receive_errs_total[5m]) > 0.1 or rate(node_network_transmit_errs_total[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Ошибки сети на {{ $labels.instance }}"
        description: "Обнаружены ошибки на интерфейсе {{ $labels.device }}"

    # Высокая системная нагрузка (load average > число CPU * 2)
    - alert: HighLoadAverage
      expr: node_load1 > on(instance) count by(instance)(node_cpu_seconds_total{mode="idle"}) * 2
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Высокая нагрузка на {{ $labels.instance }}"
        description: "Load average {{ $value | printf \"%.1f\" }} превышает число CPU в 2 раза"

  # =============================================
  # CONTAINERS: метрики Docker-контейнеров (cAdvisor)
  # =============================================
  - name: containers
    interval: 30s

    # Контейнер часто перезапускается
    # Более 3 рестартов за час = серьёзная проблема
    - alert: ContainerRestarting
      expr: increase(container_restart_count{name!=""}[1h]) > 3
      labels:
        severity: warning
      annotations:
        summary: "Контейнер {{ $labels.name }} перезапускается"
        description: "{{ $value | printf \"%.0f\" }} рестартов за час"

    # Контейнер потребляет > 90% лимита памяти
    - alert: ContainerHighMemory
      expr: (container_memory_working_set_bytes{name!=""} / container_spec_memory_limit_bytes{name!=""}) * 100 > 90
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Контейнер {{ $labels.name }} превышает лимит памяти"
        description: "Потребление {{ $value | printf \"%.0f\" }}% от лимита"

    # Контейнер потребляет > 90% лимита CPU
    - alert: ContainerHighCPU
      expr: rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100 / on(name) container_spec_cpu_quota{name!=""} * 100 > 90
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Контейнер {{ $labels.name }} под нагрузкой CPU"
        description: "Использование CPU {{ $value | printf \"%.0f\" }}%"

    # Контейнер не работает (завершился неожиданно)
    - alert: ContainerNotRunning
      expr: time() - container_last_seen{name!=""} > 120
      labels:
        severity: critical
      annotations:
        summary: "Контейнер {{ $labels.name }} не запущен"
        description: "Не обнаружен более 2 минут"

  # =============================================
  # SERVICES: метрики приложений и экспортеров
  # =============================================
  - name: services
    interval: 30s

    # PostgreSQL недоступен
    - alert: PostgresDown
      expr: pg_up == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "PostgreSQL недоступен"
        description: "База данных на {{ $labels.instance }} не отвечает"

    # PostgreSQL: много соединений idle in transaction
    - alert: PostgresIdleInTransaction
      expr: pg_stat_activity_count{state="idle in transaction"} > 5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "PostgreSQL: много зависших транзакций"
        description: "{{ $value | printf \"%.0f\" }} соединений idle in transaction"

    # PostgreSQL: replication lag > 1 минута
    - alert: PostgresReplicationLag
      expr: pg_replication_lag > 1
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "PostgreSQL replication lag на {{ $labels.instance }}"
        description: "Отставание реплики {{ $value }} секунд"

    # Nginx: много ошибок 5xx (> 5% от всех запросов)
    - alert: NginxHighErrorRate
      expr: sum(rate(nginx_http_requests_total{status=~"5.."}[5m])) / sum(rate(nginx_http_requests_total[5m])) * 100 > 5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Nginx: высокий процент ошибок"
        description: "Ошибки 5xx: {{ $value | printf \"%.1f\" }}% от всех запросов"

    # Blackbox: URL недоступен
    - alert: ProbeFailing
      expr: probe_success{job="blackbox_http"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "URL {{ $labels.instance }} недоступен"
        description: "Проверка blackbox провалена — сервис не отвечает"

    # Blackbox: медленный ответ (> 3 секунд)
    - alert: ProbeSlow
      expr: probe_duration_seconds > 3
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Медленный ответ от {{ $labels.instance }}"
        description: "Время ответа {{ $value | printf \"%.1f\" }} секунд"

  # =============================================
  # SSL: мониторинг сертификатов
  # =============================================
  - name: ssl
    interval: 60s

    # SSL-сертификат истекает скоро
    # Использует метрики blackbox_exporter (probe_ssl_earliest_cert_expiry)
    - alert: SSLCertExpiringSoon
      expr: (probe_ssl_earliest_cert_expiry - time()) / 86400 < 14
      for: 1h
      labels:
        severity: warning
      annotations:
        summary: "SSL сертификат истекает скоро"
        description: "{{ $labels.instance }}: осталось {{ $value | printf \"%.0f\" }} дней"

    # SSL-сертификат истекает через 3 дня — критично
    - alert: SSLCertExpiringCritical
      expr: (probe_ssl_earliest_cert_expiry - time()) / 86400 < 3
      for: 30m
      labels:
        severity: critical
      annotations:
        summary: "SSL сертификат истекает через {{ $value | printf \"%.0f\" }} дня"
        description: "{{ $labels.instance }}: требуется срочная замена сертификата"

  # =============================================
  # PUSHGATEWAY: метрики batch jobs (бэкапы, cron)
  # =============================================
  - name: pushgateway
    interval: 60s

    # Бэкап не выполнялся больше 25 часов
    # Метрика backup_last_success_timestamp отправляется скриптом бэкапа
    - alert: BackupMissed
      expr: time() - backup_last_success_timestamp > 90000   # 25 часов
      labels:
        severity: critical
      annotations:
        summary: "Бэкап не выполнялся больше 25 часов"
        description: "Последний успешный бэкап: {{ $value | humanizeTimestamp }}"

    # Бэкап завершился с ошибкой
    - alert: BackupFailed
      expr: backup_exit_code > 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Бэкап завершился с ошибкой"
        description: "Exit code: {{ $value | printf \"%.0f\" }}"

    # Бэкап выполняется дольше обычного (> 1 часа для обычных, > 2x от средней длительности)
    - alert: BackupSlow
      expr: backup_duration_seconds > 3600
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Бэкап выполняется дольше часа"
        description: "Длительность: {{ $value | printf \"%.0f\" }} секунд"

  # =============================================
  # APPS: метрики пользовательских приложений
  # (раскомментировать и адаптировать под своё приложение)
  # =============================================
  # - name: applications
  #   interval: 30s
  #
  #   # Приложение не отвечает (нет метрики up)
  #   - alert: AppDown
  #     expr: up{job="myapp"} == 0
  #     for: 1m
  #     labels:
  #       severity: critical
  #     annotations:
  #       summary: "Приложение {{ $labels.job }} не отвечает"
  #
  #   # Процент ошибок приложения > 5%
  #   - alert: AppHighErrorRate
  #     expr: sum(rate(http_requests_total{job="myapp", status=~"5.."}[5m])) / sum(rate(http_requests_total{job="myapp"}[5m])) * 100 > 5
  #     for: 5m
  #     labels:
  #       severity: warning
  #     annotations:
  #       summary: "Высокий процент ошибок в {{ $labels.job }}"
  #       description: "Ошибки: {{ $value | printf \"%.1f\" }}%"
  #
  #   # Задержка P99 > 2 секунд
  #   - alert: AppHighLatency
  #     expr: histogram_quantile(0.99, sum by(le)(rate(http_request_duration_seconds_bucket{job="myapp"}[5m]))) > 2
  #     for: 5m
  #     labels:
  #       severity: warning
  #     annotations:
  #       summary: "Высокая задержка в {{ $labels.job }}"
  #       description: "P99: {{ $value | printf \"%.2f\" }} секунд"

  # =============================================
  # WATCHDOG: мониторинг самого мониторинга
  # Dead man's switch: всегда должен быть активен
  # Если он пропал — значит Prometheus или Alertmanager сломан
  # =============================================
  - name: watchdog
    interval: 60s

    # Watchdog — всегда FIRING
    # Использовать в Alertmanager: receiver -> blackhole (игнорировать)
    # Если Watchdog не приходит — настроить внешний мониторинг (healthchecks.io)
    - alert: Watchdog
      expr: vector(1)
      labels:
        severity: info
      annotations:
        summary: "Мониторинг работает"
        description: "Watchdog активен — стек мониторинга функционирует"
```

---

## Проверка правил

```bash
# После добавления правил — перезагрузить Prometheus
curl -X POST http://localhost:9090/-/reload

# Проверить что правила загрузились
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name, rules: [.rules[].name]}'

# Посмотреть состояние алертов
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {alertname, state, labels}'

# Открыть UI: http://localhost:9090/alerts
```

---

## Что означает каждый параметр

| Параметр | Описание | Рекомендация |
|----------|----------|--------------|
| `expr` | PromQL-запрос, условие срабатывания | Чем проще — тем надёжнее |
| `for` | Время в состоянии PENDING до FIRING | 1-5 мин для инфраструктуры, 0 для Watchdog |
| `labels.severity` | critical / warning / info | critical = ночной звонок, warning = утром посмотреть |
| `annotations.summary` | Краткое описание (заголовок уведомления) | Понятно без контекста |
| `annotations.description` | Детали: instance, значение | Включать `$value` и `$labels` |
