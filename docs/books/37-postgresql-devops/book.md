# PostgreSQL для DevOps: надёжная эксплуатация без паники

> Версия PostgreSQL 16. Примеры работают на PostgreSQL 15 и 16.
> Объём: 150-180 страниц.
> Целевая аудитория: DevOps-инженеры, которые разворачивают приложения в Docker/K8s, но PostgreSQL для них — «чёрный ящик, который просто должен работать».

**Предварительные требования:** Docker, основы сетей, знакомство с Vault (книги 03, 35, 36 курса).

---

## Оглавление

### Глава 0 — PostgreSQL для DevOps: не DBA, но и не игнорировать

Чем задачи DevOps отличаются от задач DBA. Пять типичных инцидентов, которые можно было предотвратить. Что читатель получит после книги и чего в ней нет. Правильные ожидания.

### Глава 1 — Запуск, конфигурация, важные файлы

Docker Compose с персистентностью, нативная установка на Ubuntu 22.04, структура PGDATA, ключевые параметры postgresql.conf со стартовыми значениями, применение изменений (reload vs restart), ALTER SYSTEM.

### Глава 2 — Пользователи, роли и права

Система прав в PostgreSQL: роли, привилегии, схемы. Принцип наименьших привилегий. Создание пользователя приложения, read-only мониторинг, изоляция через схемы, ротация паролей, интеграция с Vault.

### Глава 3 — pg_hba.conf, SSL и безопасное подключение

Формат правил pg_hba.conf, порядок применения, методы аутентификации (scram-sha-256, md5, trust). Настройка SSL, принудительное шифрование через pg_hba.conf. Диагностика ошибок подключения: 5 типовых сообщений и их причины.

### Глава 4 — Бэкапы: pg_dump и pg_basebackup

Три инструмента бэкапа: pg_dump, pg_basebackup, pgBackRest. Логический и физический бэкап. Автоматизация через cron. Тест восстановления как обязательная процедура.

### Глава 5 — WAL и PITR: восстановление на любой момент

Что такое WAL и зачем он нужен. Непрерывная архивация WAL. WAL-G — промышленный инструмент. PITR: 6 шагов восстановления на точный момент времени.

### Глава 6 — Мониторинг: что смотреть и как

Ключевые системные представления (pg_stat_activity, pg_stat_user_tables, pg_stat_replication). postgres_exporter для Prometheus. Минимальный набор метрик и их пороги. Как найти блокировки и убить зависший запрос.

### Глава 7 — Медленные запросы: pg_stat_statements и EXPLAIN

Топ медленных запросов через pg_stat_statements. Чтение EXPLAIN ANALYZE: три главных сигнала проблемы. Индексы: когда добавлять, CONCURRENTLY, поиск неиспользуемых индексов.

### Глава 8 — Connection Pooling: PgBouncer

Почему 500 соединений убивают PostgreSQL. Три режима PgBouncer: session, transaction, statement. Установка и конфигурация. Мониторинг через SHOW POOLS.

### Глава 9 — Репликация: streaming replication и read replicas

Как работает streaming replication. Настройка primary + replica через pg_basebackup -R. Мониторинг lag, ручной failover, logical replication.

### Глава 10 — PostgreSQL в Docker и Kubernetes

Правильная конфигурация контейнера: данные, конфиги, секреты. StatefulSet, PVC, headless service. PgBouncer sidecar. CloudNativePG — оператор для production K8s. Terraform-провижининг.

### Глава 11 — Миграции без даунтайма: expand/contract

Какие DDL-операции блокируют таблицу. Паттерн expand/contract: добавить колонку с NOT NULL, переименовать колонку. Инструменты: squawk, strong_migrations.

### Глава 12 — Диагностика: алгоритм разбора инцидентов

Системный подход: алгоритм первичной диагностики за 5-10 минут. Пять типовых сценариев. Vacuum troubleshooting. pgbench — нагрузочное тестирование. Что собрать для передачи DBA.

### Глава 13 — Тюнинг производительности: память, vacuum, pgbench

Настройка памяти: shared_buffers, work_mem, maintenance_work_mem, effective_cache_size. Тюнинг autovacuum для высоконагруженной БД. Методология pgbench: baseline -> одно изменение -> замер -> сравнение.

---

## Приложения

### Приложение A — Шпаргалка команд

psql команды, администрирование (pg_dump, pg_restore, pg_basebackup), роли и права, pg_stat_activity, PgBouncer консоль, WAL и репликация.

### Приложение B — Важные системные представления (pg_stat_*)

Таблица каждого представления: описание, когда использовать, пример запроса. pg_stat_activity, pg_stat_user_tables, pg_stat_user_indexes, pg_stat_replication, pg_stat_bgwriter, pg_stat_database, pg_locks, pg_stat_statements.

### Приложение C — Чеклист production PostgreSQL

20 пунктов, которые должны быть настроены перед выходом в production: бэкапы, мониторинг, алерты, pgBouncer, SSL, autovacuum, shared_buffers, тест восстановления.

### Приложение D — Справочник pg_hba.conf

Полный справочник форматов записей с примерами для разработки, production, SSL-only и аутентификации по сертификату.

### Приложение E — Матрица совместимости инструментов

Версионная совместимость pgBackRest, WAL-G, PgBouncer, Patroni, CloudNativePG, postgres_exporter с PostgreSQL 14-17.
