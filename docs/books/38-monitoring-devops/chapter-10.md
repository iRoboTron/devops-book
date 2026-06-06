# Глава 10: Pushgateway — метрики для batch jobs

## Что вы узнаете

- почему pull-модель Prometheus не работает для batch-задач и чем помогает Pushgateway;
- как настроить Pushgateway и добавить его в Prometheus;
- как отправить метрики из bash-скрипта (бэкап, cron-задача);
- почему важно удалять старые метрики после завершения job'а;
- как написать алерт на пропущенный бэкап.

**Цель:** после этой главы скрипт резервного копирования отправляет метрики (статус, длительность, размер) в Prometheus, и если бэкап не выполнился 25 часов — приходит алерт в Telegram.

---

## Когда pull не работает

Prometheus построен на pull-модели: он сам приходит за метриками по HTTP, каждый `scrape_interval` секунд.

```text
Pull (Prometheus):
Prometheus ──► GET /metrics ──► Exporter (работает 24/7)

Push (Pushgateway):
Batch Job ──► POST метрики ──► Pushgateway ──► Prometheus (pull)
```

Проблема с batch jobs:

- Скрипт бэкапа запускается → работает 5 минут → завершается.
- Он не держит HTTP-сервер на порту 9090 — Prometheus не может его опросить.
- После завершения процесса нет endpoint'а для scrape.

Решение: Pushgateway — постоянно работающий сервис, который принимает метрики от batch jobs через HTTP POST и отдаёт их Prometheus при следующем scrape.

```text
┌──────────────────────────────────────────────────────┐
│                                                      │
│  Batch Job (backup.sh) ──POST /metrics────┐          │
│  Batch Job (etl.py)    ──POST /metrics────┤          │
│  Cron script           ──POST /metrics────┤          │
│                                           ▼          │
│                                     Pushgateway:9091 │
│                                           │          │
│                              Prometheus ◄─┘ (pull)   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Добавить Pushgateway в стек

### docker-compose.yml

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

### prometheus.yml

```yaml
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']
```

Параметр `honor_labels: true` говорит Prometheus: «не перезаписывай labels которые прислал job, используй их как есть». Без этого Prometheus перезапишет `instance` и `job` своими значениями.

```bash
# Проверить что Pushgateway работает
curl http://localhost:9091/metrics | head -20

# Должна быть хотя бы pushgateway_build_info
```

---

## Отправить метрики из bash-скрипта

Создайте скрипт бэкапа, который после выполнения отправляет метрики в Pushgateway. Полный рабочий пример:

```bash
#!/bin/bash
# backup.sh — бэкап PostgreSQL с отправкой метрик в Pushgateway

set -e

PUSHGATEWAY="http://localhost:9091"
JOB="backup"
INSTANCE="db-server"

BACKUP_START=$(date +%s)
BACKUP_FILE="/backup/myapp_$(date +%Y%m%d_%H%M%S).sql.gz"

# Удалить старые метрики перед отправкой новых
curl -s -X DELETE "$PUSHGATEWAY/metrics/job/$JOB/instance/$INSTANCE" || true

echo "Запуск бэкапа: pg_dump myapp"

# Выполнить бэкап (пайп с gzip чтобы не хранить сырой дамп)
pg_dump -U postgres myapp | gzip > "$BACKUP_FILE"
BACKUP_STATUS=${PIPESTATUS[0]}

BACKUP_END=$(date +%s)
BACKUP_DURATION=$((BACKUP_END - BACKUP_START))
BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || echo 0)

echo "Бэкап завершён: статус=$BACKUP_STATUS, размер=$BACKUP_SIZE байт, длительность=$BACKUP_DURATION сек"

# Отправить метрики в Pushgateway
cat <<EOF | curl -s --data-binary @- "$PUSHGATEWAY/metrics/job/$JOB/instance/$INSTANCE"
# HELP backup_last_success_timestamp Время последнего успешного бэкапа
# TYPE backup_last_success_timestamp gauge
backup_last_success_timestamp $(date +%s)
# HELP backup_duration_seconds Длительность выполнения бэкапа
# TYPE backup_duration_seconds gauge
backup_duration_seconds $BACKUP_DURATION
# HELP backup_size_bytes Размер файла бэкапа
# TYPE backup_size_bytes gauge
backup_size_bytes $BACKUP_SIZE
# HELP backup_status 0 = успешно, 1 = ошибка
# TYPE backup_status gauge
backup_status $BACKUP_STATUS
EOF

echo "Метрики отправлены в Pushgateway"

# Если бэкап не удался — выйти с кодом ошибки
exit $BACKUP_STATUS
```

Ключевые моменты:

- **DELETE перед отправкой** — удаляем старые метрики этого job'а, чтобы не накапливались дубликаты.
- **# HELP и # TYPE** — опциональны, но сильно упрощают отладку. В Prometheus UI вы увидите не только значение, но и описание.
- **backup_last_success_timestamp** — timestamp последнего успешного бэкапа. Именно эту метрику мы будем мониторить.

### Python-версия (для тех кто не пишет на bash)

```python
#!/usr/bin/env python3
"""backup.py — отправка метрик в Pushgateway из Python."""
import time
import subprocess
import requests

PUSHGATEWAY = "http://localhost:9091"
JOB = "backup"
INSTANCE = "db-server"

def send_metrics(status, duration, size):
    """Отправить метрики в Pushgateway."""
    # Удалить старые метрики
    requests.delete(f"{PUSHGATEWAY}/metrics/job/{JOB}/instance/{INSTANCE}")

    # Новые метрики
    metrics = f"""\
# HELP backup_last_success_timestamp Время последнего успешного бэкапа
# TYPE backup_last_success_timestamp gauge
backup_last_success_timestamp {int(time.time())}
# HELP backup_duration_seconds Длительность
# TYPE backup_duration_seconds gauge
backup_duration_seconds {duration}
# HELP backup_size_bytes Размер
# TYPE backup_size_bytes gauge
backup_size_bytes {size}
# HELP backup_status Статус
# TYPE backup_status gauge
backup_status {status}
"""
    resp = requests.post(
        f"{PUSHGATEWAY}/metrics/job/{JOB}/instance/{INSTANCE}",
        data=metrics
    )
    resp.raise_for_status()

if __name__ == "__main__":
    start = time.time()
    result = subprocess.run(["pg_dump", "-U", "postgres", "myapp"],
                          capture_output=True)
    duration = time.time() - start
    send_metrics(result.returncode, duration, len(result.stdout))
```

---

## Очистка метрик из Pushgateway

После завершения batch job метрики остаются в Pushgateway навсегда. Это создаёт две проблемы:

1. Если job завершился с ошибкой, метрика `backup_status=1` останется висеть. Через сутки Prometheus увидит две метрики: старую (с ошибкой) и новую (успешную). Алерт не сработает — `backup_last_success_timestamp` будет содержать свежее значение, несмотря на старую ошибку.

2. Если job перестал запускаться (сломался cron, упал сервер), метрика `backup_last_success_timestamp` будет показывать старый timestamp, и алтерт сработает. Но если вы несколько раз запускали job вручную, в Pushgateway накопится несколько time series для одного job'а с разными labels.

**Правильный паттерн: DELETE → PUSH**

```bash
# 1. Удалить старые метрики job'а
curl -X DELETE http://localhost:9091/metrics/job/backup

# 2. Или конкретного instance
curl -X DELETE http://localhost:9091/metrics/job/backup/instance/server1

# 3. Добавить в скрипт перед отправкой новых метрик
curl -s -X DELETE "$PUSHGATEWAY/metrics/job/$JOB/instance/$INSTANCE" || true
```

DELETE удаляет все метрики с указанными labels. После DELETE Pushgateway не отдаёт этот time series при scrape, и Prometheus перестаёт его видеть.

> ☠️ **Осторожно:** Если не удалять старые метрики, Pushgateway накопит несколько time series для одного job'а. Prometheus увидит несколько значений с разными timestamp. Запрос `backup_last_success_timestamp` вернёт все значения, а не только последнее. Алерт `time() - backup_last_success_timestamp > 90000` сработает некорректно.

---

## Алерт на пропущенный бэкап

Самый важный алерт для batch-задач: «задача не выполнялась дольше ожидаемого».

```yaml
# prometheus/rules/alerts.yml
groups:
  - name: backups
    interval: 30s
    rules:
      - alert: BackupMissed
        expr: time() - backup_last_success_timestamp > 90000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Бэкап не выполнялся больше 25 часов"
          description: "{{ $labels.instance }} — последний успешный бэкап: {{ $value | humanizeDuration }} назад"

      - alert: BackupFailed
        expr: backup_status == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Бэкап завершился с ошибкой"
          description: "{{ $labels.instance }} — exit code: {{ $value | printf \"%.0f\" }}"
```

Как это работает:

- `backup_last_success_timestamp` — Unix timestamp последнего успешного бэкапа.
- `time()` — текущее время в секундах с 1970.
- `time() - backup_last_success_timestamp > 90000` — разница больше 25 часов (25 * 60 * 60 = 90000).
- Если бэкап выполняется раз в сутки, 25 часов — запас в 1 час на задержки.

```promql
# Проверить в Prometheus UI
time() - backup_last_success_timestamp
# Если значение > 90000 — алерт должен сработать

# Посмотреть статус последнего бэкапа
backup_status
# 0 = успешно, 1 = ошибка

# Длительность
backup_duration_seconds
```

---

## Push-only метрики и уведомления через Alertmanager

Напомним, что Alertmanager поддерживает Go-шаблоны для уведомлений. Вы можете сделать сообщение с информацией о бэкапе:

```yaml
# alertmanager/alertmanager.yml
templates:
  - '/etc/alertmanager/templates/*.tmpl'

# alertmanager/templates/telegram.tmpl
{{ define "telegram.default" }}
{{ range .Alerts }}
{{ if eq .Status "firing" }}🔴{{ else }}✅{{ end }} *{{ .Labels.alertname }}*
{{ .Annotations.summary }}
{{ .Annotations.description }}
*Instance:* {{ .Labels.instance }}
*Severity:* {{ .Labels.severity }}
*Active:* {{ .StartsAt.Format "15:04 UTC" }}
{{ end }}
{{ end }}
```

---

## Типичные ошибки

Pushgateway решает конкретную задачу — batch jobs. Но его часто используют неправильно.

**Антипаттерн 1: Pushgateway для постоянно работающих сервисов.**

```text
Неправильно:
Ваше веб-приложение шлёт метрики в Pushgateway раз в 15 секунд.

Правильно:
Веб-приложение реализует /metrics endpoint, Prometheus забирает сам (pull).
```

Если сервис работает 24/7 и может ответить на HTTP-запрос — используйте pull. Pushgateway добавляет лишнюю точку отказа и скрывает факт падения сервиса (Prometheus видит Pushgateway, а не упавший сервис).

**Антипаттерн 2: Метрики без очистки.**

```text
Неправильно:
Скрипт отправляет метрики, но не удаляет старые.

Правильно:
Перед отправкой — DELETE, после отправки — проверка что новых метрик ровно 1.
```

**Антипаттерн 3: Использование Pushgateway как долговременного хранилища.**

Pushgateway хранит метрики в памяти. При рестарте Pushgateway данные теряются. Это буфер, а не БД. Если Prometheus не успел их забрать — данные пропали.

---

## Чек-лист для самопроверки

- [ ] Понимаю когда нужен Pushgateway (batch jobs) и когда не нужен (постоянные сервисы)
- [ ] Pushgateway добавлен в docker-compose и виден в Prometheus targets
- [ ] Написан скрипт отправки метрик с DELETE перед отправкой
- [ ] Метрики из скрипта видны в Prometheus (Graph → `backup_last_success_timestamp`)
- [ ] Настроен алерт на пропущенный бэкап (`time() - backup_last_success_timestamp > 90000`)
- [ ] Настроен алерт на неудачный бэкап (`backup_status == 1`)
- [ ] Проверена очистка метрик: после DELETE метрика исчезает из `/metrics` Pushgateway

---

## Попробуйте сами

1. Запустите Pushgateway. Отправьте тестовую метрику вручную:
   ```bash
   echo "test_metric 42" | curl -s --data-binary @- http://localhost:9091/metrics/job/testjob
   ```
   Проверьте в Prometheus: зайдите в Graph, введите `test_metric`. Значение 42 видно?

2. Напишите скрипт который шлёт `script_last_run_timestamp` в Pushgateway. Запустите его. Найдите метрику в Prometheus.

3. Добавьте алерт: если `script_last_run_timestamp` не обновлялся больше 10 минут — алерт. Не запускайте скрипт 11 минут. Сработал ли алерт? Выполните скрипт — алерт разрешился?

4. Сломайте скрипт намеренно (замените `exit 0` на `exit 1`). Дождитесь алерта BackupFailed. Почините скрипт — алерт должен разрешиться.

5. Проверьте что происходит без DELETE: запустите скрипт 3 раза подряд. Сколько time series для `backup_last_success_timestamp` показывает Prometheus? Теперь добавьте DELETE — сколько после этого?
