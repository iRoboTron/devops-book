# Инструкция для ИИ-агента: Модуль 27 — Nextcloud: администрирование и обслуживание

> **Это Модуль 27, книга части 4 "Прочее".**
> Предварительные требования: книги 01–07 (Linux, Docker, Nginx, systemd).
> Читатель уже имеет работающий Nextcloud — книга про понимание и контроль, не про установку с нуля.

---

## Контекст проекта

Читатель уже запустил Nextcloud — через Nextcloud All-in-One (AIO) на Docker. У него работает Nginx как reverse proxy, PostgreSQL в контейнере, настроены обновления через cron-скрипт.

**Что он сейчас делает:**
- Заходит, пользуется, изредка обновляет
- Знает что там что-то происходит, но не до конца понимает как

**Что его беспокоит:**
- Не полностью понимает из чего состоит его Nextcloud
- Боится что-то сломать при обновлении
- Не уверен правильно ли настроены бэкапы
- Не знает как расследовать когда что-то ведёт себя странно
- Встречал ошибки в журнале, не понимал что делать
- Хочет уметь объяснить другому как это работает

**Что он хочет после этой книги:**
Полное понимание своей инсталляции. Уметь обновлять уверенно. Настроить нормальный бэкап. Знать как диагностировать проблемы. Иметь документацию своей установки.

---

## Что за книга

**Название:** "Nextcloud: от «оно работает» до «я понимаю как это устроено»"

**Каталог:** `27-nextcloud-admin`

**Место в курсе:** Книга 27, часть 4 "Прочее".

**Объём:** 140–170 страниц.

**Особенность книги:**
Читатель уже использует Nextcloud. Поэтому книга начинается не с «давайте установим», а с «давайте разберёмся что у тебя уже стоит». Практические задания — на реальной установке читателя.

**Стиль:**
- Ориентация на Nextcloud AIO (All-in-One) — именно эта схема у читателя
- Команды реальные, с объяснением что именно происходит
- Без лишних абстракций: конкретные файлы, конкретные директории

---

## Главная идея

Разница между «оно работает» и «я администрирую» — это понимание каждого компонента.

```
«Оно работает»:               «Я администрирую»:
↑ не знаю из чего             ↑ знаю каждый компонент
→ не знаю как обновить        → обновляю уверенно
→ боюсь сломать               → умею восстановить
→ бэкап «наверное есть»       → бэкап проверен и работает
→ ошибка = паника             → ошибка = occ + логи
```

---

## Что читатель получит к концу книги

- Схему своей установки: все контейнеры, порты, тома, пути
- Понимание occ команд (инструмент управления Nextcloud)
- Уверенное обновление с бэкапом до и проверкой после
- Настроенный и проверенный бэкап данных и БД
- Навык диагностики через логи и occ
- Документацию своей инсталляции

---

## Структура книги

### Глава 0: Что у тебя стоит — разобраться в своей установке

**Цель:** читатель точно понимает из чего состоит его Nextcloud.

Это самая важная глава книги. Начинать с диагностики, не с теории.

Разобрать Nextcloud AIO Architecture:

```
Nextcloud AIO состоит из контейнеров:

nextcloud-aio-mastercontainer  ← главный, управляет остальными
nextcloud-aio-nextcloud        ← само приложение PHP
nextcloud-aio-database         ← PostgreSQL
nextcloud-aio-redis            ← кэш сессий и файловых блокировок
nextcloud-aio-nextcloud-aio    ← web-интерфейс управления AIO
nextcloud-aio-talk             ← (если включён) видеозвонки
nextcloud-aio-clamav           ← (если включён) антивирус
```

Практика — посмотреть свои контейнеры:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Посмотреть тома
docker volume ls | grep nextcloud

# Посмотреть где данные
docker inspect nextcloud-aio-nextcloud | grep -A5 "Mounts"
```

Найти важные пути:
```bash
# Данные Nextcloud (документы, фото)
# Обычно: /mnt/ncdata или /var/lib/docker/volumes/nextcloud_aio_nextcloud_data

# Конфиги
docker exec nextcloud-aio-nextcloud find /var/www/html/config -name "*.php"

# Где лежит config.php
docker exec nextcloud-aio-nextcloud cat /var/www/html/config/config.php
```

Важно: `config.php` может содержать пароли, salts, secret, trusted domains и другие чувствительные настройки. Нельзя вставлять его полный вывод в чаты, тикеты и публичные документы. В книге показывать, как смотреть нужные ключи выборочно через `occ config:system:get`, а не публиковать весь файл.

Нарисовать схему своей установки:
```
Интернет
    ↓ 443
Nginx (хост)
    ↓ 11000 (внутренний порт AIO)
nextcloud-aio-nextcloud
    ↓
nextcloud-aio-database (PostgreSQL :5432)
nextcloud-aio-redis (:6379)
    ↓
/mnt/ncdata (данные пользователей)
```

---

### Глава 1: occ — командная строка Nextcloud

**Цель:** читатель умеет использовать occ для управления и диагностики.

occ — это как `docker exec` + инструмент управления Nextcloud:

```bash
# Базовый формат для AIO
docker exec --user www-data nextcloud-aio-nextcloud php occ <команда>

# Чтобы не писать каждый раз длинно — создать alias
alias occ='docker exec --user www-data nextcloud-aio-nextcloud php occ'

# Или функцию в ~/.bashrc
occ() {
  docker exec --user www-data nextcloud-aio-nextcloud php occ "$@"
}
```

Важные команды:

```bash
# Статус системы
occ status
occ system:check

# Список установленных приложений
occ app:list

# Обновить все приложения
occ app:update --all

# Проверить базу данных
occ db:add-missing-indices
occ db:add-missing-columns
occ db:convert-filecache-bigint

# Очистить кэш
occ maintenance:repair

# Пересканировать файлы пользователя
occ files:scan username

# Войти в режим обслуживания
occ maintenance:mode --on
occ maintenance:mode --off

# Список пользователей
occ user:list

# Информация о пользователе
occ user:info username
```

Разобрать каждую команду: что делает, когда нужна.

Перед командами объяснить, что имя контейнера в AIO обычно такое, но может отличаться. Сначала читатель должен найти реальное имя:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
```

---

### Глава 2: Обновления — как делать правильно

**Цель:** читатель обновляет Nextcloud уверенно, с бэкапом и проверкой.

Типы обновлений:
1. Обновление приложений (apps) — безопасно, часто
2. Обновление Nextcloud (major/minor version) — требует подготовки
3. Обновление Docker-образа AIO — включает оба

Правильный порядок:

```bash
# Шаг 1: Проверить текущую версию
occ status

# Шаг 2: Сделать бэкап (см. главу 4)
# Шаг 3: Включить maintenance mode
occ maintenance:mode --on

# Шаг 4: Обновить через AIO
# (через веб-интерфейс AIO на порту 8080, или скриптом)

# Скрипт автообновления (читатель его уже имеет)
/data/scripts/update-nextcloud.sh

# Шаг 5: Выключить maintenance mode
occ maintenance:mode --off

# Шаг 6: Проверить после обновления
occ status
occ db:add-missing-indices
occ maintenance:repair
```

Разобрать скрипт читателя `/data/scripts/update-nextcloud.sh` — объяснить каждую строку.

Что проверить после обновления:
```bash
# Ошибки в логах
docker logs nextcloud-aio-nextcloud --tail=50

# Работают ли приложения
occ app:list | grep -v enabled

# Синхронизация файлов
occ files:scan --all --unscanned
```

---

### Глава 3: Приложения — установка, проверка, удаление

**Цель:** читатель управляет приложениями осознанно.

```bash
# Список всех доступных приложений (с поиском)
occ app:list
occ app:search notes

# Установить приложение
occ app:install notes

# Включить / выключить
occ app:enable notes
occ app:disable notes

# Удалить
occ app:remove notes

# Обновить конкретное
occ app:update notes
# Или все сразу
occ app:update --all
```

Проблема несовместимости приложений:
```bash
# CAdViewer история читателя — пример реальной проблемы
# Приложение вызывало deprecated метод OC\Server::getLogger()
# Решение: удалить приложение

# Диагностика: что вызывает ошибки в логах
docker logs nextcloud-aio-nextcloud 2>&1 | grep -i "error\|exception" | tail -20
```

---

### Глава 4: PostgreSQL — понять и не бояться

**Цель:** читатель понимает что такое БД Nextcloud и умеет с ней работать.

Проверить состояние:
```bash
# Подключиться к PostgreSQL
docker exec -it nextcloud-aio-database psql -U nextcloud nextcloud_database

# Основные команды внутри psql:
\l      — список баз
\dt     — список таблиц
\du     — список пользователей
\q      — выйти

# Размер базы
SELECT pg_size_pretty(pg_database_size('nextcloud_database'));

# Количество записей в основных таблицах
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;
```

Регулярное обслуживание через occ:
```bash
# Добавить отсутствующие индексы (после обновлений)
occ db:add-missing-indices

# Конвертировать bigint
occ db:convert-filecache-bigint

# Оптимизация
docker exec nextcloud-aio-database vacuumdb -U nextcloud -d nextcloud_database -z -v
```

---

### Глава 5: Бэкапы — настроить и проверить

**Цель:** бэкап работает, проверен, восстановление понятно.

Что нужно бэкапить:
```
1. Данные пользователей (/mnt/ncdata или аналог)
2. База данных PostgreSQL
3. Конфиг (/var/www/html/config/config.php)
4. Кастомные темы и приложения (если есть)
```

Сравнить варианты бэкапа:

| Вариант | Что защищает | Плюсы | Минусы | Когда использовать |
|---|---|---|---|---|
| AIO backup | штатный путь AIO | проще и безопаснее для AIO | нужно понять где лежит и как восстановить | основной вариант |
| pg_dump + файлы | БД и данные | понятно вручную | легко получить неконсистентный бэкап | учебно и для понимания |
| snapshot VPS | весь сервер | быстро | не всегда проверяет восстановление приложения | перед рискованным обновлением |
| внешний backup | защита от потери сервера | переживает аварию VPS | требует настройки доступа и шифрования | для важных данных |

Скрипт бэкапа базы:
```bash
#!/bin/bash
# backup-nextcloud.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/data/backups/nextcloud"
mkdir -p "$BACKUP_DIR"

# 1. Включить maintenance mode
docker exec --user www-data nextcloud-aio-nextcloud php occ maintenance:mode --on

# 2. Бэкап PostgreSQL
docker exec nextcloud-aio-database pg_dump \
  -U nextcloud nextcloud_database \
  | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# 3. Копия конфига
docker cp nextcloud-aio-nextcloud:/var/www/html/config/config.php \
  "$BACKUP_DIR/config_$DATE.php"

# 4. Выключить maintenance mode
docker exec --user www-data nextcloud-aio-nextcloud php occ maintenance:mode --off

echo "Backup complete: $BACKUP_DIR/db_$DATE.sql.gz"
```

Проверка восстановления (на тестовой VM):
```bash
# Восстановить базу из дампа
cat db_20260101.sql.gz | gunzip | \
  docker exec -i nextcloud-aio-database psql -U nextcloud nextcloud_database
```

Cron для автоматических бэкапов:
```bash
# /etc/cron.d/nextcloud-backup
0 2 * * * root /data/scripts/backup-nextcloud.sh >> /var/log/nextcloud-backup.log 2>&1
```

Разобрать скрипт читателя `/data/scripts/update-nextcloud.sh` — убедиться что бэкап происходит ДО обновления.

Обязательное правило: бэкап считается рабочим только после restore drill. В книге должен быть отдельный безопасный сценарий проверки восстановления на тестовой VM или отдельном контейнере, без риска для боевого Nextcloud.

---

### Глава 6: Производительность — Redis и кэширование

**Цель:** читатель понимает зачем Redis и как проверить что он работает.

```bash
# Проверить что Redis запущен и подключён
docker exec nextcloud-aio-redis redis-cli ping
# Ответ: PONG

# Статистика Redis
docker exec nextcloud-aio-redis redis-cli info | grep -E "used_memory|connected_clients|keyspace_hits|keyspace_misses"
```

Проверить в Nextcloud что Redis используется:
```bash
occ config:system:get redis
# Ожидаемый вывод:
# Array
# (
#   [host] => nextcloud-aio-redis
#   [port] => 6379
# )
```

Проверить APCu (кэш PHP):
```bash
docker exec nextcloud-aio-nextcloud php -r "var_dump(apcu_cache_info()['num_entries']);"
```

Добавить фоновые задачи Nextcloud:

- AJAX cron — простой, но плох для постоянной работы;
- Webcron — компромисс;
- System cron — правильный вариант для своего сервера.

Объяснить, как проверить предупреждения в админке Nextcloud и какие команды `occ` помогают исправить индексы, MIME-типы и фоновые задачи.

---

### Глава 7: Диагностика — когда что-то идёт не так

**Цель:** читатель знает как расследовать проблемы шаг за шагом.

Алгоритм диагностики:
```
1. Что именно не работает? (синхронизация, загрузка файлов, вход)
2. Смотрим логи
3. Запускаем occ system:check
4. Проверяем статус контейнеров
5. Смотрим ресурсы сервера
```

Логи:
```bash
# Логи приложения Nextcloud
docker logs nextcloud-aio-nextcloud --tail=100 2>&1 | grep -i error

# Логи внутри контейнера
docker exec nextcloud-aio-nextcloud tail -f /var/www/html/data/nextcloud.log

# Логи PostgreSQL
docker logs nextcloud-aio-database --tail=50

# Логи Redis
docker logs nextcloud-aio-redis --tail=50
```

Типичные проблемы и решения:

| Проблема | Команда диагностики | Решение |
|---|---|---|
| Файлы не видны | `occ files:scan --all` | Пересканировать |
| Медленная работа | `occ status` + Redis check | Очистить кэш |
| OCC ошибка после обновления | `occ db:add-missing-indices` | Добавить индексы |
| Приложение не запускается | `docker logs nc-app --tail=50` | Проверить логи |
| "Maintenance mode" завис | `occ maintenance:mode --off` | Выключить вручную |

Ресурсы сервера:
```bash
# CPU и RAM
docker stats --no-stream

# Диск
df -h
docker system df  # сколько занимают образы/тома
```

---

### Глава 8: Безопасность Nextcloud

**Цель:** базовый security-чеклист для своей инсталляции.

```bash
# Встроенная проверка безопасности
occ security:scan

# Проверить настройки
occ config:list system | grep -E "mail|smtp|password_policy|bruteforce"
```

Важные настройки:

```bash
# Включить защиту от брутфорса
occ config:system:set auth.bruteforce.protection.enabled --value=true --type=bool

# Политика паролей
occ config:app:set password_policy minLength --value=12

# Проверить права на директорию данных
docker exec nextcloud-aio-nextcloud stat -c "%a %U %G" /var/www/html/data
# Должно быть: 770 www-data www-data (или 750)
```

Проверить открытые файлы конфигурации:
```bash
# config.php не должен быть читаем всем
docker exec nextcloud-aio-nextcloud stat -c "%a" /var/www/html/config/config.php
# Должно быть: 640
```

---

### Глава 9: Пользователи и администрирование

**Цель:** читатель умеет управлять пользователями через occ.

```bash
# Список пользователей
occ user:list

# Информация о пользователе
occ user:info username

# Создать пользователя
occ user:add --password-from-env --display-name="Имя" username

# Сбросить пароль
occ user:resetpassword username

# Заблокировать / разблокировать
occ user:disable username
occ user:enable username

# Удалить
occ user:delete username

# Квота
occ user:setting username files quota 5GB
```

Группы:
```bash
occ group:list
occ group:add имя_группы
occ group:adduser имя_группы username
```

---

### Глава 10: Итоговый проект — документация своей установки

**Цель:** читатель создаёт документацию своей инсталляции.

Задачи:

1. **Схема установки:** нарисовать какие контейнеры, порты, тома, пути
2. **Инвентаризация:** версия Nextcloud, версии приложений, PostgreSQL, Redis
3. **Бэкап:** проверить что скрипт работает, запустить вручную, убедиться что файл создан
4. **Restore test:** восстановить дамп базы в отдельном контейнере
5. **Чеклист обновления:** пошаговая инструкция под свою установку
6. **Runbook:** «что делать если Nextcloud не открывается» — пошаговый алгоритм

Шаблон документации:
```markdown
# Nextcloud — моя установка

## Версии
- Nextcloud: X.Y.Z
- PHP: X.Y
- PostgreSQL: X.Y

## Компоненты
| Контейнер | Порт | Том | Путь данных |
|-----------|------|-----|-------------|

## Важные пути
- Данные: /mnt/ncdata
- Конфиг: /data/nextcloud/config
- Бэкапы: /data/backups/nextcloud
- Скрипты: /data/scripts/

## Обслуживание
- Автообновление: cron 3:00 ежедневно
- Бэкап БД: cron 2:00 ежедневно
- Ротация бэкапов: хранить 7 дней

## Процедура обновления
1. ...

## Диагностика
...
```

---

## Обязательные сравнения

1. Nextcloud AIO vs классическая установка — почему AIO проще для одного человека
2. PostgreSQL vs SQLite vs MySQL для Nextcloud — почему PostgreSQL правильный выбор
3. Бэкап с maintenance mode vs без — зачем останавливать запись
4. occ vs веб-интерфейс — когда что использовать

---

## Особые требования

### Критерии готовности

Книга должна закончиться документацией реальной установки Nextcloud и проверенным обслуживанием. Обязательно проверить:

- контейнеры, порты, тома и пути записаны в таблицу;
- `occ` работает через найденное реальное имя контейнера;
- бэкап настроен и хотя бы один раз проверен восстановлением на тестовом стенде;
- порядок обновления описан как чеклист;
- логи Nextcloud, PostgreSQL, Redis и Nginx известны читателю;
- есть runbook "Nextcloud не открывается";
- секреты из `config.php` не попали в документацию.

### Про reverse proxy

Добавить отдельный блок про типовые настройки за Nginx:

- `trusted_domains`;
- `trusted_proxies`;
- `overwriteprotocol`;
- реальные IP клиентов за reverse proxy;
- HTTPS на внешнем контуре.

Не давать универсальный конфиг без объяснения, потому что AIO, внешний Nginx и домен могут быть настроены по-разному.

### Про AIO-специфику
Почти все команды в книге — через `docker exec nextcloud-aio-nextcloud`. Это специфика AIO. Объяснить один раз в начале.

Но сначала научить находить реальные имена контейнеров, потому что в разных установках они могут отличаться.

### Про реальную установку читателя
Читатель уже имеет конкретные пути, скрипты, настройки. Книга должна предлагать команды для диагностики существующей установки, а не установку с нуля.

### Не делать
- Не описывать установку Nextcloud с нуля — это не цель книги
- Не углубляться в разработку приложений для Nextcloud
- Не охватывать enterprise-функции (LDAP, SAML) — это за рамками
- Не публиковать полный `config.php` и другие секреты в примерах вывода
