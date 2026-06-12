# Мониторинг с нуля: Prometheus, Grafana и Alertmanager без Kubernetes

**Модуль 38** курса DevOps-инженер. Уровень 1.0 — без Kubernetes.

**Целевая аудитория:** DevOps-инженеры и разработчики, у которых «мониторинга нет». О проблемах узнают от пользователей, логи смотрят через `docker logs`, а мониторинг — это `uptime` в Telegram раз в 5 минут.

**Предварительные требования:** книга 03 (Docker), книга 35 (Сети). Читатель умеет работать с Docker Compose.

**Версии ПО:** Prometheus 2.x, Grafana 10.x, Alertmanager 0.27+, Node Exporter 1.8+, Loki 2.9+.

**Объём:** 130–160 страниц.

**Формат:** все компоненты запускаются через Docker Compose. Альтернативно — установка через systemd (Приложение D).

---

## Глава 0: Зачем мониторинг и как устроен стек

Мотивационная глава без единой строчки конфигов. Три вопроса которые решает мониторинг, архитектура стека из шести компонентов, разница между метриками, логами и трейсами. Что читатель получит после книги и почему «смотреть в логи когда упало» — это не мониторинг.

## Глава 1: Быстрый старт — весь стек за 15 минут

Docker Compose-файл с Prometheus, Grafana, Node Exporter и Alertmanager. Минимальная конфигурация Prometheus. Запуск, проверка, первый вход в Grafana. Импорт дашборда Node Exporter Full (ID 1860) пошагово. Альтернативная установка через systemd для серверов без Docker.

## Глава 2: Prometheus — концепции, метрики, конфигурация

Pull vs Push модель, time series и labels, четыре типа метрик (Counter, Gauge, Histogram, Summary). Формат `/metrics` endpoint — реальный вывод curl. Полный `prometheus.yml` с объяснением каждой секции. Добавление таргетов, hot reload через `/-/reload`. Динамическое обнаружение через `file_sd_configs`.

## Глава 3: Node Exporter — метрики сервера

Ключевые метрики CPU, памяти, диска и сети. PromQL-запросы для каждой группы метрик. Режимы CPU, разница между MemFree и MemAvailable, фильтрация сетевых интерфейсов. Мониторинг нескольких серверов в одном job. Коллекторы — какие включены и какие добавить.

## Глава 4: PromQL — 20 запросов для реальных задач

Основы синтаксиса за 5 минут: selectors, range vector, instant vector. Ключевые функции: `rate()`, `irate()`, `increase()`, `histogram_quantile()`, `predict_linear()`. Агрегация через `by()` и `without()`. 20 конкретных запросов для сервера, приложения, Docker и диагностики.

## Глава 5: Grafana — дашборды, панели, переменные

Создание панели с нуля: запрос, тип визуализации, оси, пороги. Типы визуализаций и когда что использовать. Переменные — переключатель instance/environment на дашборде. Provisioning: хранение дашбордов в JSON-файлах в Git. IaC для Grafana.

## Глава 6: cAdvisor — метрики Docker-контейнеров

Добавление cAdvisor в стек. Ключевые метрики контейнеров: CPU, память (working set), сеть, рестарты. Фильтрация системных контейнеров. Построение дашборда по контейнерам с топ-10 по памяти. Ограничения cAdvisor.

## Глава 7: Exporters — PostgreSQL, Nginx, Redis, Blackbox

Концепция exporter: прокси между Prometheus и сервисом. postgres_exporter: соединения, размер БД, cache hit ratio. Nginx exporter: stub_status, RPS, активные соединения. Redis exporter: память, команды, hit rate. Blackbox exporter: проверка HTTP, TCP, SSL-сертификатов. Synthetic monitoring с валидацией JSON-ответа. Альтернативы для малых команд: Uptime Kuma, Netdata.

## Глава 8: Alertmanager — правила, routing, Telegram

Жизненный цикл алерта: INACTIVE → PENDING → FIRING. Правила алертинга: ServiceDown, HighCPU, LowMemory, DiskAlmostFull, ContainerRestarting, SSLCertExpiringSoon, Watchdog. Конфигурация Alertmanager: routing, group_by, group_wait, repeat_interval. Уведомления в Telegram: создание бота, получение chat_id. Inhibition rules для предотвращения шторма алертов. Silences для временного глушения.

## Глава 9: Loki + Promtail — логи в Grafana

Loki vs ELK: когда что выбирать. Добавление Loki и Promtail в Docker Compose. Конфигурация Promtail: системные логи и Docker-логи. LogQL: label selectors, line filters, парсинг JSON/logfmt. Интеграция логов и метрик на одном дашборде. Derived fields для перехода из лога в трейс. Logrotate для Docker-логов.

## Глава 10: Pushgateway — метрики для batch jobs

Когда pull-модель не работает: batch jobs, cron-скрипты, бэкапы. Добавление Pushgateway в стек. Отправка метрик из bash-скрипта и Python. Очистка старых метрик. Алерт на неудачный бэкап через `time() - backup_last_success_timestamp`. Правило: не использовать Pushgateway для постоянно работающих сервисов.

## Глава 11: Масштабирование и long-term storage

Сколько данных хранит один Prometheus. Управление retention. Remote Write в VictoriaMetrics для хранения метрик на 12+ месяцев. Когда одного Prometheus недостаточно: 1 млн+ time series, изолированные дата-центры, HA мониторинга. Grafana provisioning alert rules — все правила в Git.

## Глава 12: Диагностика — что делать когда мониторинг сломан

Алгоритм из 6 шагов: «алерт не пришёл». Самодиагностика Prometheus: `prometheus_tsdb_head_series`, `prometheus_rule_evaluation_failures_total`. Проверка Alertmanager через прямой API-запрос curl. Watchdog алерт как dead man's switch — мониторинг мониторинга. Типичные проблемы и их решения.

---

## Приложения

### Приложение A: Полный docker-compose.yml

Финальный рабочий `docker-compose.yml` со всеми компонентами книги: Prometheus, Grafana, Node Exporter, cAdvisor, Alertmanager, Loki, Promtail, Pushgateway, postgres_exporter, nginx_exporter, blackbox_exporter. С volumes, networks, healthchecks. Готов к `docker compose up -d`.

### Приложение B: Готовые alert rules

Полный файл `prometheus/rules/alerts.yml` со всеми правилами из книги. Разделы: Infrastructure (CPU, Memory, Disk, Network), Containers (рестарты, ресурсы), Services (uptime, errors, latency), Backups, SSL, Watchdog.

### Приложение C: Шпаргалка PromQL и LogQL

PromQL: selectors, функции (rate, irate, increase, histogram_quantile, predict_linear), агрегация (sum, avg, topk, by, without), операторы. По 2-3 примера каждой функции. LogQL: label selectors, line filters, парсеры, metric queries.

### Приложение D: Установка через systemd (без Docker)

Полные systemd unit-файлы для Prometheus, Grafana, Alertmanager, Node Exporter. Trade-offs: Docker vs systemd — изоляция и автообновление против простоты для одного сервера.

### Глоссарий

Ключевые термины книги с указанием глав — [**glossary.md**](glossary.md).
