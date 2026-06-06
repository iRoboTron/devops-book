# Глава 8: Alertmanager — правила, routing, Telegram

## Что вы узнаете

- как писать правила алертинга в Prometheus (recording rules и alert rules);
- жизненный цикл алерта: INACTIVE -> PENDING -> FIRING;
- конфигурация Alertmanager: routing, receivers, inhibition, silences;
- шаблоны уведомлений на Go templates;
- настройка уведомлений в Telegram;
- как избежать шторма алертов.

**Цель:** читатель настраивает алерты которые срабатывают при реальных проблемах и не шумят в остальное время. Получает уведомления в Telegram.

---

## Как работает алертинг в Prometheus

```text
Схема 3: Жизненный цикл алерта

                        for: 1m
  INACTIVE ─────────────────────────────────► PENDING
      ▲                                          │
      │                                    for истек ?
      │                                    условия всё
      │                                    ещё верны ?
      │                                          │
      │                                     да  │   нет
      │                                          │
      │                                          ▼
      │◄──────────────────────────────── FIRING ──┘
      │                                          │
      │                                    проблема
      │                                    решена ?
      │                                     (no data
      │                                      или false)
      │                                          │
      │                                     да  │
      │                                          │
      └──────────────────────────────────────────┘
```

1. **INACTIVE** — условие алерта ложно, всё нормально.
2. **PENDING** — условие стало истинным. Prometheus ждёт `for:` прежде чем перевести в FIRING. Это фильтр кратковременных скачков (flapping).
3. **FIRING** — условие истинно дольше чем `for:`. Alertmanager отправляет уведомление.
4. Возврат в **INACTIVE** — условие стало ложным или метрика пропала. Alertmanager отправляет resolved-уведомление.

```text
Схема 5: Routing tree в Alertmanager

                       ┌─────────────┐
                       │ root route  │
                       │ all alerts  │
                       └──────┬──────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ┌─────▼─────┐      ┌─────▼─────┐
              │ severity  │      │ alertname │
              │ =critical │      │ =Watchdog │
              └─────┬─────┘      └─────┬─────┘
                    │                   │
              ┌─────▼─────┐      ┌─────▼─────┐
              │ telegram- │      │ blackhole │
              │ critical  │      │ (noop)    │
              └───────────┘      └───────────┘
                    │
                    │ (continue: false → не
                    │ проверяем дальше)
                    │
              остальные алерты
                    │
              ┌─────▼─────┐
              │ telegram- │
              │ general   │
              └───────────┘
```

Каждый алерт проходит через root route. Matchers определяют в какой receiver (канал уведомления) попадает алерт. Если алерт совпал с маршрутом и `continue: false` — другие маршруты не проверяются.

---

## Alert rules в Prometheus

Правила алертинга хранятся в YAML-файлах и загружаются через `rule_files` в prometheus.yml. Создайте файл `prometheus/rules/alerts.yml`:

```yaml
groups:
  - name: infrastructure
    interval: 30s
    rules:

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Сервис {{ $labels.job }} недоступен"
          description: "Таргет {{ $labels.instance }} не отвечает больше 1 минуты"

      - alert: HighCPU
        expr: 100 - (avg by(instance)
          (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Высокий CPU на {{ $labels.instance }}"
          description: "CPU {{ $value | printf \"%.1f\" }}% больше 5 минут"

      - alert: LowMemory
        expr: (node_memory_MemAvailable_bytes
          / node_memory_MemTotal_bytes) * 100 < 15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Мало памяти на {{ $labels.instance }}"
          description: "Доступно {{ $value | printf \"%.1f\" }}% памяти"

      - alert: DiskAlmostFull
        expr: 100 - (node_filesystem_avail_bytes{mountpoint="/"}
          / node_filesystem_size_bytes{mountpoint="/"} * 100) > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Диск заполнен на {{ $value | printf \"%.0f\" }}%"
          description: "{{ $labels.instance }}: диск {{ $labels.mountpoint }}
            заполнен на {{ $value | printf \"%.0f\" }}%"

      - alert: ContainerRestarting
        expr: increase(container_restart_count[1h]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Контейнер {{ $labels.name }} перезапускается"
          description: "{{ $value | printf \"%.0f\" }} рестартов за час"

      - alert: SSLCertExpiringSoon
        expr: (probe_ssl_earliest_cert_expiry - time()) / 86400 < 14
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL сертификат истекает скоро"
          description: "{{ $labels.instance }}: осталось
            {{ $value | printf \"%.0f\" }} дней"

      - alert: Watchdog
        expr: vector(1)
        labels:
          severity: info
        annotations:
          summary: "Мониторинг работает"
```

### Разбор каждого правила

| Правило | Что проверяет | Почему именно так |
|---------|---------------|-------------------|
| ServiceDown | `up == 0` — таргет не отвечает на scrape | `for: 1m` чтобы не срабатывать при одном пропущенном scrape |
| HighCPU | idle CPU < 15% (загрузка > 85%) | `for: 5m` — кратковременные писки CPU нормальны |
| LowMemory | MemAvailable < 15% от MemTotal | MemAvailable — реально доступная с учётом page cache |
| DiskAlmostFull | занято > 85% на корневой ФС | `for: 10m` — могут быть временные файлы (логи, кэш пакетов) |
| ContainerRestarting | > 3 рестартов за час | Единичный рестарт может быть при обновлении контейнера |
| SSLCertExpiringSoon | < 14 дней до истечения | `for: 1h` — проверка раз в час, не дёргать часто |
| Watchdog | `vector(1)` — всегда истинно | Сигнал что Prometheus жив. Если пропал — мониторинг сломан |

### Подключение правил в prometheus.yml

```yaml
rule_files:
  - "rules/alerts.yml"
```

---

## Alertmanager конфиг — Telegram

### docker-compose.yml

```yaml
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    restart: unless-stopped
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports:
      - "127.0.0.1:9093:9093"
    networks:
      - monitoring
```

### alertmanager/alertmanager.yml

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  receiver: telegram-general

  routes:
    - matchers:
        - severity = critical
      receiver: telegram-critical
      continue: false

    - matchers:
        - alertname = Watchdog
      receiver: blackhole

receivers:
  - name: blackhole

  - name: telegram-general
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: -1001234567890
        message: '{{ template "telegram.default" . }}'
        parse_mode: Markdown

  - name: telegram-critical
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: -1009876543210
        message: '{{ template "telegram.critical" . }}'
        parse_mode: Markdown

inhibit_rules:
  - source_matchers:
      - alertname = ServiceDown
      - severity = critical
    target_matchers:
      - severity = warning
    equal: ['instance']
```

---

## Шаблоны уведомлений (Go templates)

Шаблоны позволяют кастомизировать сообщения алертов. Создайте `alertmanager/templates/telegram.tmpl`:

```gotmpl
{{ define "telegram.default" -}}
{{ range .Alerts -}}
*{{ .Labels.alertname }}*
{{ .Annotations.summary }}
{{ .Annotations.description }}
*Severity:* {{ .Labels.severity }}
*Status:* {{ .Status }}
*Started:* {{ .StartsAt.Format "2006-01-02 15:04:05" }}
{{- end }}
{{- end }}

{{ define "telegram.critical" -}}
CRITICAL ALERT
{{ range .Alerts -}}
*{{ .Labels.alertname }}*
{{ .Annotations.description }}
*Instance:* {{ .Labels.instance }}
{{- end }}
{{- end }}
```

Подключите шаблоны в alertmanager.yml:

```yaml
templates:
  - 'templates/*.tmpl'
```

### Доступные переменные в шаблонах

| Переменная | Описание |
|-----------|----------|
| `{{ .Alerts }}` | Список алертов в группе |
| `{{ .Status }}` | `firing` или `resolved` |
| `{{ .Labels.alertname }}` | Имя алерта |
| `{{ .Labels.severity }}` | Severity метка |
| `{{ .Annotations.summary }}` | Аннотация summary |
| `{{ .Annotations.description }}` | Аннотация description |
| `{{ .Value }}` | Значение выражения для данного алерта |
| `{{ .StartsAt.Format "2006-01-02 15:04:05" }}` | Время срабатывания |

### Пример форматирования resolved

Добавьте в шаблон проверку статуса:

```gotmpl
{{ define "telegram.default" -}}
{{ range .Alerts }}
{{ if eq .Status "firing" }}*FIRING*{{ else }}*RESOLVED*{{ end }}
*{{ .Labels.alertname }}*
{{ .Annotations.description }}
{{ end }}
{{- end }}
```

---

## Параметры группировки

```yaml
route:
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

- `group_by` — метки по которым алерты группируются в одно сообщение. Если 3 сервера упали одновременно — будет 3 группы (по `instance`). Если группировать по `alertname` — одно сообщение с 3 серверами.
- `group_wait` — время ожидания перед отправкой первой группы. За 30 секунд могут прийти ещё алерты — они попадут в ту же группу.
- `group_interval` — как часто проверять группу повторно, если алерты ещё активны.
- `repeat_interval` — как часто слать повторное уведомление если алерт всё ещё FIRING. Минимум 4 часа, иначе Telegram будет спамить.

> ☠️ **Осторожно:** Никогда не ставьте `repeat_interval: 1m`. Если проблема не решается 3 часа — получите 180 сообщений. `repeat_interval` — это частота напоминаний, не частота проверок.

---

## Inhibition rules — подавление шума

Если сервер упал — алерт ServiceDown сработает на Node Exporter. Но на этом же сервере могут быть ещё 10 exporter-ов (postgres_exporter, nginx_exporter, redis_exporter) — каждый из них тоже уйдёт в ServiceDown. Результат: 11 алертов вместо одного.

**Inhibition rule** подавляет алерты с `severity: warning` если есть активный алерт `severity: critical` на том же `instance`:

```yaml
inhibit_rules:
  - source_matchers:
      - alertname = ServiceDown
      - severity = critical
    target_matchers:
      - severity = warning
    equal: ['instance']
```

Source — алерт-триггер (ServiceDown). Target — алерты которые подавляются (все warning). `equal: ['instance']` — подавление работает только если `instance` совпадает.

---

## Silences — временно заглушить алерт

Silences — ручное подавление на время. Используется когда:
- идёт плановое обслуживание;
- проблема известна и исправляется;
- тестирование правил.

Как создать:

```text
Alertmanager UI (порт 9093) → Silences → New Silence
- Matchers: alertname="DiskAlmostFull", instance="server1:9100"
- Duration: 4h
- Comment: "Плановая очистка диска, вернусь к норме через 2 часа"
- Creator: "devops"
```

Silence действует пока не истечёт Duration. Можно продлить или отменить досрочно.

> ☠️ **Осторожно:** Silences — это плохо если их много. Каждый silence — сигнал что что-то не так: либо порог алерта неверный, либо проблема не решается годами. Раз в месяц проверяйте список silences.

---

## Как получить Telegram bot token и chat ID

```text
1. Написать @BotFather в Telegram
2. /newbot → ввести имя → получить токен (вида 123456:ABC-DEF1234gh)
3. Добавить бота в группу или написать ему лично
4. Узнать chat_id:
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   → найти "chat":{"id": ...}
   Для группы: id отрицательный (-1001234567890)
```

Если бот не присылает сообщения:
- проверьте что бот добавлен в чат;
- chat_id должен быть отрицательным для групповых чатов;
- бот должен быть администратором группы (для старых версий Telegram).

---

## Grafana встроенный алертинг

Grafana (начиная с версии 8) имеет собственный алертинг — можно создавать алерты прямо в UI Grafana без настройки Alertmanager. Это удобно для:

- быстрых алертов на основе произвольных датасорсов (Prometheus + Loki + Elasticsearch одновременно);
- алертов по логам (Loki): «ошибка в логах > N раз за 5 минут»;
- алертов без Prometheus (например только CloudWatch или InfluxDB).

Недостатки Grafana alerting:
- нет inhibition rules;
- нет routing tree (все алерты в один receiver);
- шаблоны сообщений ограничены;
- всё в UI — сложно хранить в Git.

Вывод: Prometheus + Alertmanager для инфраструктурных алертов. Grafana alerting — для бизнес-метрик и быстрых прототипов.

---

## Типичные ошибки

- Алерт без `for:` — срабатывает при первом же нарушении, много ложных тревог. Всегда добавлять `for: 5m` минимум.
- Не настроить `inhibit_rules` — при падении сервера получишь 20 алертов о его сервисах вместо одного.
- `repeat_interval: 1m` — будешь получать сообщения каждую минуту пока проблема не решена. Минимум `4h`.
- `group_wait: 0s` — каждый алерт в отдельном сообщении. При инциденте с 10 проблемами = 10 сообщений. Нужен `group_wait: 30s`.
- Watchdog настроен но никто не заметил его пропажу — мониторинг мониторинга работает только если есть внешняя система (например Uptime Kuma проверяет Prometheus).
- Telegram bot token в git — если репозиторий публичный, бот токен станет публичным и любой сможет писать от имени вашего бота. Используйте переменные окружения или файлы с паролями не в git.
- Подавление всех `warning` без `equal: ['instance']` — если один сервер упал, а второй имеет проблемы с памятью, inhibition rule подавит оба warning.

---

## Чек-лист для самопроверки

- [ ] Написал хотя бы 3 alert rules и понимаю синтаксис
- [ ] Понимаю INACTIVE -> PENDING -> FIRING и зачем нужен `for:`
- [ ] Настроил Alertmanager с Telegram-уведомлениями
- [ ] Добавил `inhibit_rules` чтобы избежать шторма алертов
- [ ] Настроил группировку (group_wait, group_interval, repeat_interval)
- [ ] Watchdog активен и кто-то мониторит сам мониторинг
- [ ] Шаблоны сообщений вынесены в отдельный файл `.tmpl`
- [ ] Telegram token не попал в публичный git

---

## Попробуйте сами

1. Добавьте правило `HighCPU` с порогом 5% (чтобы оно гарантированно сработало). Запустите Prometheus. Подождите `evaluation_interval`. В Prometheus UI -> Alerts найдите алерт в состоянии PENDING. Подождите `for:` — он перейдёт в FIRING.

2. Настройте Telegram-бота. Убедитесь что алерт пришёл в чат. Разрешите проблему (перезапустите Prometheus или уберите правило) — придёт сообщение о resolving.

3. Добавьте Watchdog алерт. Он должен всегда быть в FIRING. Остановите Prometheus (`docker stop prometheus`). Через несколько минут Watchdog пропадёт — это тест что мониторинг мониторинга не работает. Запустите Prometheus обратно.

4. Создайте silence для алерта `DiskAlmostFull` на 2 часа. Проверьте в Alertmanager UI что алерт подавлен. Отмените silence.

5. Настройте inhibition rule: остановите Node Exporter на одном сервере (ServiceDown -> critical). Должны подавиться все warning алерты на том же instance. Проверьте в Alertmanager UI что алерты помечены как `inhibited`.
