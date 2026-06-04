# Глава 5: WAL и PITR — восстановление на любой момент времени

## Что вы узнаете

- что такое WAL и зачем он нужен;
- как настроить непрерывную архивацию WAL;
- WAL-G: промышленный инструмент для бэкапов с WAL-архивацией;
- PITR: восстановление на точный момент времени (6 шагов);
- как тестировать PITR.

**Цель главы:** WAL-архивирование + ежедневный `pg_basebackup` даёт восстановление на любую минуту последних N дней с потерей максимум нескольких секунд данных. Это не теория — вы выполните полный цикл руками.

---

## 1. Что такое WAL

WAL (Write-Ahead Log) — журнал предзаписи. Прежде чем изменить страницу данных на диске, PostgreSQL записывает это изменение в WAL.

```
Без WAL:
Данные изменились → сбой → неизвестно в каком состоянии файлы

С WAL:
WAL записан ✓ → данные изменились → сбой → применяем WAL = консистентность
```

**Как это работает (без глубокой теории):**

1. Приходит `UPDATE users SET name = 'new' WHERE id = 1`
2. PostgreSQL записывает в WAL: «на странице 42 в таблице users в строке 1 заменить 'old' на 'new'»
3. PostgreSQL подтверждает транзакцию клиенту
4. Когда-то позже (checkpoint) изменения попадают на диск

При сбое PostgreSQL на старте читает WAL и применяет все изменения, которые были подтверждены, но не записаны на диск. Это называется **восстановление после сбоя** (crash recovery) и происходит автоматически при каждом запуске.

**Где хранится WAL:**

```
$PGDATA/pg_wal/           ← текущие WAL-сегменты (по 16MB каждый)
/archive/wal/             ← архивированные WAL (настраивается)
```

**Важно понимать:** WAL — это журнал изменений, не копия данных. Без базового бэкапа WAL бесполезен — это как иметь логи всех изменений, но не иметь начального состояния.

---

## 2. WAL-архивация

По умолчанию PostgreSQL хранит только текущие WAL-файлы в `pg_wal/` и перезаписывает старые. Для PITR нужно настроить **непрерывную архивацию** — копировать каждый завершённый WAL-сегмент в надёжное место.

### 2.1. Параметры конфигурации

```ini
# /etc/postgresql/16/main/postgresql.conf

wal_level = replica              # достаточно для архивации и репликации
archive_mode = on                # включить архивацию
archive_command = 'cp %p /archive/wal/%f'
# %p = полный путь к WAL-файлу (например, /var/lib/postgresql/16/main/pg_wal/000000010000000000000042)
# %f = только имя файла (например, 000000010000000000000042)

archive_timeout = 60             # архивировать каждые 60 секунд (даже если сегмент не заполнен)
```

Параметры:

| Параметр | Значение по умолчанию | Для PITR |
|----------|----------------------|----------|
| `wal_level` | replica | `replica` (не ниже) |
| `archive_mode` | off | `on` |
| `archive_command` | (пусто) | команда копирования |
| `archive_timeout` | 0 (нет) | 60-300 секунд |

### 2.2. Создание директории архива

```bash
sudo mkdir -p /archive/wal
sudo chown postgres: /archive/wal
```

### 2.3. Применение и проверка

```bash
# Перезагрузить конфигурацию
sudo systemctl reload postgresql

# Проверить что архивация активна
sudo -u postgres psql -c "SELECT * FROM pg_stat_archiver;"
```

Вывод:

```
 archived_count | last_archived_wal        | last_archived_time
----------------+--------------------------+---------------------
             42 | 000000010000000000000042 | 2026-06-04 14:31:00
```

Если `archived_count` растёт со временем — архивация работает.

### 2.4. Команды архивации для разных хранилищ

```ini
# Локальный архив
archive_command = 'cp %p /archive/wal/%f'

# S3 через aws cli
archive_command = 'aws s3 cp %p s3://my-bucket/wal/%f'

# S3 через WAL-G
archive_command = 'wal-g wal-push %p'

# SSH на другой сервер
archive_command = 'scp %p backup-server:/archive/wal/%f'
```

> ☠️ **Осторожно:** `archive_command` выполняется от пользователя postgres. При использовании `scp` или `aws` нужно настроить SSH-ключи / IAM роли для этого пользователя. Ошибки архивации пишутся в лог PostgreSQL — проверяйте их.

---

## 3. WAL-G — промышленный инструмент для бэкапов

WAL-G — стандарт индустрии для PostgreSQL backup. Поддерживает S3, GCS, Azure, локальную файловую систему. Сжатие, дедупликация, delta backup.

### 3.1. Установка

```bash
# Скачать последний релиз
curl -L https://github.com/wal-g/wal-g/releases/latest/download/wal-g-pg-ubuntu-20.04-amd64 \
  -o /usr/local/bin/wal-g

chmod +x /usr/local/bin/wal-g

# Проверить
wal-g version
```

### 3.2. Конфигурация

```json
// ~/.walg.json (или /etc/wal-g/config.json)
{
  "WALG_FILE_PREFIX": "/backup/walg",
  "PGDATABASE": "postgres",
  "PGUSER": "postgres",
  "PGHOST": "/var/run/postgresql",
  "PGPORT": "5432",
  "WALG_COMPRESSION_METHOD": "zstd",
  "WALG_DELTA_MAX_STEPS": "6"
}
```

Для S3:

```json
{
  "WALG_S3_PREFIX": "s3://my-pg-backup/",
  "AWS_ACCESS_KEY_ID": "...",
  "AWS_SECRET_ACCESS_KEY": "...",
  "AWS_REGION": "eu-central-1",
  "WALG_COMPRESSION_METHOD": "zstd"
}
```

### 3.3. Интеграция с PostgreSQL

```ini
# /etc/postgresql/16/main/postgresql.conf

archive_command = 'wal-g wal-push %p'
restore_command = 'wal-g wal-fetch %f %p'
```

Перезагрузить:

```bash
sudo systemctl reload postgresql
```

### 3.4. Базовый бэкап через WAL-G

```bash
# Полный бэкап
wal-g backup-push /var/lib/postgresql/16/main

# Дельта-бэкап (только изменения)
wal-g backup-push /var/lib/postgresql/16/main --delta
```

### 3.5. Список бэкапов

```bash
wal-g backup-list
```

Вывод:

```
name                          modified             size
base_000000010000000000000042  2026-06-04T14:00:00  2.3 GiB
base_0000000100000000000000A0  2026-06-04T06:00:00  2.1 GiB
```

### 3.6. Восстановление из WAL-G

```bash
# Восстановить последний бэкап
wal-g backup-fetch /var/lib/postgresql/16/main LATEST

# Восстановить конкретный бэкап
wal-g backup-fetch /var/lib/postgresql/16/main base_000000010000000000000042
```

---

## 4. PITR — восстановление на момент времени

Point-In-Time Recovery позволяет восстановить кластер на любой момент в прошлом — минута, секунда, точная транзакция.

### 4.1. Сценарий

Классический сценарий для PITR:

```
14:30 — всё работает
14:31:55 — кто-то выполнил DELETE FROM orders WHERE 1=1 (удалены все заказы)
14:32 — обнаружено
14:33 — начинаем восстановление на 14:31:30
```

### 4.2. Процедура PITR (6 шагов)

**Шаг 1. Остановить PostgreSQL**

```bash
sudo systemctl stop postgresql
```

**Шаг 2. Сохранить текущие данные (или очистить)**

```bash
# Вариант A: сохранить текущие данные (на случай ошибки)
sudo mv /var/lib/postgresql/16/main /var/lib/postgresql/16/main_corrupted

# Вариант B: очистить (уверены что восстановимся)
sudo rm -rf /var/lib/postgresql/16/main/*
```

> ☠️ **Осторожно:** Никогда не удаляйте данные без резервной копии. Если бэкап повреждён — старые данные это единственное что у вас есть.

**Шаг 3. Восстановить базовый бэкап**

```bash
# Вариант A: из pg_basebackup
sudo cp -r /backup/basebackup_20260604/* /var/lib/postgresql/16/main/
sudo chown -R postgres: /var/lib/postgresql/16/main

# Вариант B: из WAL-G
sudo -u postgres wal-g backup-fetch /var/lib/postgresql/16/main LATEST
```

**Шаг 4. Создать recovery.signal**

PostgreSQL 12+ использует файл `recovery.signal` для входа в режим восстановления:

```bash
sudo touch /var/lib/postgresql/16/main/recovery.signal
sudo chown postgres: /var/lib/postgresql/16/main/recovery.signal
```

**Шаг 5. Настроить параметры восстановления**

```bash
# Записать параметры восстановления в postgresql.auto.conf
sudo -u postgres bash -c "cat >> /var/lib/postgresql/16/main/postgresql.auto.conf << 'EOF'

# Команда восстановления WAL из архива
restore_command = 'cp /archive/wal/%f %p'

# Цель восстановления — точное время
recovery_target_time = '2026-06-04 14:31:30'

# Действие после достижения цели: promote (стать primary)
recovery_target_action = 'promote'

EOF"
```

Параметры восстановления:

| Параметр | Описание |
|----------|----------|
| `restore_command` | Команда получения WAL из архива (аналог archive_command, но наоборот) |
| `recovery_target_time` | Восстановиться до этого момента (формат: `'YYYY-MM-DD HH:MI:SS'`) |
| `recovery_target_xid` | Восстановиться до определённой транзакции по XID |
| `recovery_target_lsn` | Восстановиться до определённой позиции в WAL |
| `recovery_target_action` | `pause` (остановиться), `promote` (стать primary), `shutdown` |
| `recovery_target_inclusive` | `true` (включительно), `false` (исключительно) |

**Шаг 6. Запустить PostgreSQL и мониторить**

```bash
sudo systemctl start postgresql

# Мониторить лог восстановления
sudo journalctl -u postgresql -f
# или
sudo tail -f /var/log/postgresql/postgresql.log
```

В логе вы увидите:

```
LOG:  starting point-in-time recovery to "2026-06-04 14:31:30+03"
LOG:  restored log file "0000000100000000000000A0" from archive
LOG:  recovery stopping before commit of transaction 12345
LOG:  pausing at the end of recovery
LOG:  recovery has paused
LOG:  recovery promoting after reaching recovery target
LOG:  database system is ready to accept connections
```

### 4.3. Проверка после PITR

```sql
-- Данные восстановились?
SELECT count(*) FROM orders;

-- До какой точки восстановились?
SELECT pg_last_wal_replay_lsn();
SELECT pg_last_xact_replay_timestamp();
```

### 4.4. Если цель не указана — восстановление до последнего WAL

```bash
# Без recovery_target_time — восстановит всё что есть в архиве
# Это обычное восстановление, не PITR
cat >> /var/lib/postgresql/16/main/postgresql.auto.conf << 'EOF'
restore_command = 'cp /archive/wal/%f %p'
EOF
```

### 4.5. Продвинутые цели восстановления

```bash
# Восстановить до конкретной транзакции
recovery_target_xid = '12345'
recovery_target_inclusive = false   # не включая указанную транзакцию

# Восстановить до LSN
recovery_target_lsn = '1A/BCDE1234'

# Восстановить до имени (имя задаётся через pg_create_restore_point())
recovery_target_name = 'before_migration_v2'
```

Создание restore point (для миграций):

```sql
-- Перед опасной миграцией
SELECT pg_create_restore_point('before_migration_v2');
```

После этого можно восстановиться до этого restore point по имени.

---

## 5. Тестирование PITR

**Критически важно:** PITR нужно тестировать. Архивация может работать годами, а при реальном инциденте оказаться что archive_command возвращает ошибку, но никто не проверял.

### 5.1. Полный тест PITR

```bash
#!/bin/bash
# /opt/backup/test_pitr.sh
# Полный цикл: бэкап → изменение → удаление → PITR

set -euo pipefail

TESTDIR="/tmp/pg_pitr_test"
PGDATA="/var/lib/postgresql/16/main"
ARCHIVE="/archive/wal"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="/var/log/pg_pitr_test_${TIMESTAMP}.log"

echo "[$(date)] === PITR TEST START ===" | tee -a "$LOG"

# 1. Убедиться что архивация работает
CURRENT_ARCHIVED=$(sudo -u postgres psql -At -c "SELECT archived_count FROM pg_stat_archiver;")
echo "[1] Архивация активна. Архивов: $CURRENT_ARCHIVED" | tee -a "$LOG"

# 2. Создать тестовые данные
sudo -u postgres psql -d myapp -c "
  DROP TABLE IF EXISTS pitr_test;
  CREATE TABLE pitr_test (id serial, data text, created_at timestamptz default now());
  INSERT INTO pitr_test (data) SELECT 'row_' || generate_series(1, 1000);
"

BEFORE_COUNT=$(sudo -u postgres psql -At -d myapp -c "SELECT count(*) FROM pitr_test;")
echo "[2] Создано $BEFORE_COUNT строк" | tee -a "$LOG"

# 3. Запомнить время
RECOVERY_TARGET=$(date '+%Y-%m-%d %H:%M:%S' -d '+1 minute')
echo "[3] Цель восстановления: $RECOVERY_TARGET" | tee -a "$LOG"

# 4. Подождать чтобы архивировался WAL
sleep 60

# 5. Удалить данные
sudo -u postgres psql -d myapp -c "DROP TABLE pitr_test;"
echo "[4] Таблица удалена" | tee -a "$LOG"

# 6. Дождаться архивации WAL с удалением
sleep 60

# 7. Выполнить PITR
echo "[5] Запуск PITR..." | tee -a "$LOG"

sudo systemctl stop postgresql

# Сохранить текущие данные
sudo mv "$PGDATA" "${PGDATA}_pitr_test"

# Восстановить из архива
sudo mkdir -p "$PGDATA"
sudo chown postgres: "$PGDATA"

# Восстановить базовый бэкап (должен быть сделан ранее)
# В реальном тесте — pgbackrest restore или копия base backup

# Создать recovery.signal
sudo touch "$PGDATA/recovery.signal"
sudo chown postgres: "$PGDATA/recovery.signal"

# Настроить восстановление
sudo -u postgres bash -c "cat >> $PGDATA/postgresql.auto.conf << 'EOF'
restore_command = 'cp /archive/wal/%f %p'
recovery_target_time = '${RECOVERY_TARGET}'
recovery_target_action = 'promote'
EOF"

sudo systemctl start postgresql

# Ждать пока PostgreSQL поднимется
sleep 10

# 8. Проверить данные
AFTER_COUNT=$(sudo -u postgres psql -At -d myapp -c "SELECT count(*) FROM pitr_test;" 2>/dev/null || echo "0")

if [ "$AFTER_COUNT" = "$BEFORE_COUNT" ]; then
    echo "[6] УСПЕХ: $AFTER_COUNT строк после PITR (совпадает с $BEFORE_COUNT)" | tee -a "$LOG"
else
    echo "[6] ПРОВАЛ: $AFTER_COUNT строк после PITR (ожидалось $BEFORE_COUNT)" | tee -a "$LOG"
    exit 1
fi

# 9. Очистить тестовые данные
sudo -u postgres psql -d myapp -c "DROP TABLE pitr_test;"
echo "[7] Тестовая таблица удалена" | tee -a "$LOG"

echo "[$(date)] === PITR TEST COMPLETED ===" | tee -a "$LOG"
```

### 5.2. Периодичность тестирования

| Окружение | Частота |
|-----------|---------|
| Production | Раз в месяц минимум |
| Staging | Раз в неделю |
| После изменения конфигурации | Обязательно |
| После смены версии PostgreSQL | Обязательно |

---

## 6. Мониторинг WAL-архивации

### 6.1. pg_stat_archiver

```sql
SELECT
  archived_count,
  last_archived_wal,
  last_archived_time,
  failed_count,
  last_failed_wal,
  last_failed_time,
  stats_reset
FROM pg_stat_archiver;
```

Если `failed_count > 0` — архивация не работает. Смотреть в лог PostgreSQL.

### 6.2. Проверка целостности WAL

```bash
# Проверить WAL-файл
pg_waldump /archive/wal/000000010000000000000042

# Проверить что нет gap в архиве
ls -la /archive/wal/ | wc -l
```

### 6.3. Размер WAL под нагрузкой

```sql
-- WAL-генерация за последний час
SELECT count(*) * 16 / 1024.0 AS wal_gb
FROM pg_ls_waldir()
WHERE modification > now() - interval '1 hour';
```

Это помогает планировать размер архива:

```
Размер архива = WAL_в_день × retention_days
Пример: 2GB WAL в день × 30 дней = 60GB
```

---

## 7. Комбинированная стратегия

Для production-систем:

```
                  ┌─────────────────────────┐
                  │     Стратегия backup     │
                  ├─────────────────────────┤
                  │ pg_basebackup: ежедневно │
                  │                  в 02:00 │
                  │ WAL архив: непрерывно    │
                  │                  каждые  │
                  │                  60 сек  │
                  │ Retention: 30 дней       │
                  │ Тест PITR: ежемесячно    │
                  └─────────────────────────┘
```

**RPO (Recovery Point Objective):** максимум 60 секунд (archive_timeout)
**RTO (Recovery Time Objective):** зависит от размера БД — тестировать и знать цифру

---

## Типичные ошибки

- `archive_command` написан, но `wal_level != replica` — WAL архивируется неполно, PITR не гарантирован. В PostgreSQL 16 по умолчанию `replica`, но проверять обязательно.
- Архив на том же сервере что и данные — при сбое сервера теряется и то и другое. WAL-архив должен быть на отдельном сервере или в S3.
- Не тестировать PITR — единственный способ убедиться что восстановление работает. Бэкап делается годами, а при первом реальном восстановлении — ошибка потому что archive_command сломан.
- `recovery_target_time` в неверном часовом поясе — восстановление на неверный момент. Всегда указывать timezone: `'2026-06-04 14:31:00+03'`. PostgreSQL по умолчанию использует timezone сервера.
- `archive_timeout = 0` — при низкой нагрузке WAL может не архивироваться часами. На маломощных dev-серверах это увеличивает RPO до часов. Ставить 60-300 секунд.
- Забыть `restore_command` в recovery.signal конфиге — PostgreSQL не найдёт WAL и не сможет восстановиться.
- Удалить pg_wal/ руками — данные повреждены, PostgreSQL не стартует. WAL удаляет только сам PostgreSQL, не лезть руками.
- recovery_target_action = 'pause' — после достижения цели сервис не начнёт принимать соединения. В production использовать `promote` если не нужен ручной контроль.

---

## Чек-лист для самопроверки

- [ ] Понимаю что WAL — это журнал изменений, не копия данных. WAL + base backup = восстановление.
- [ ] Умею настроить `archive_command` и `archive_timeout`
- [ ] Проверил `pg_stat_archiver` — `archived_count` растёт, `failed_count = 0`
- [ ] Знаю процедуру PITR наизусть: 6 шагов от остановки до проверки
- [ ] Понимаю разницу между crash recovery (автоматически) и PITR (вручную)
- [ ] Настроил WAL-G или pgBackRest для архивации
- [ ] Провёл полный тест PITR: создал данные → удалил → восстановил на момент ДО удаления
- [ ] Знаю свой RPO и RTO

---

## Попробуйте сами

1. **Настройте простую WAL-архивацию.** Добавьте в `postgresql.conf`:
   ```ini
   archive_mode = on
   archive_command = 'cp %p /tmp/wal_archive/%f'
   archive_timeout = 60
   ```
   Создайте директорию `/tmp/wal_archive`. Перезагрузите PostgreSQL. Сделайте несколько изменений в БД. Проверьте что в `/tmp/wal_archive/` появились файлы. Это и есть WAL-архивация.

2. **Выполните полный PITR-тест.** Создайте таблицу с данными. Запомните время. Подождите 2 минуты. Удалите таблицу. Подождите ещё 2 минуты (чтобы WAL с удалением ушёл в архив). Выполните PITR на момент ДО удаления. Проверьте что таблица и данные вернулись.

3. **Настройте WAL-G.** Установите, настройте `~/.walg.json` с локальным хранилищем. Выполните `wal-g backup-push`. Проверьте `wal-g backup-list`. Сделайте несколько изменений, подождите архивации, выполните `wal-g backup-fetch LATEST` в тестовую директорию.

4. **Изучите pg_wal директорию.** Выполните `ls -lh $PGDATA/pg_wal/`. Посмотрите размер одного WAL-сегмента (16MB). Выполните `pg_waldump` на одном из WAL-файлов — увидите какие транзакции в нём записаны.
