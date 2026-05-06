# Глава 4: PostgreSQL

> **Цель:** не бояться базы данных Nextcloud и понимать, зачем она нужна.

---

**Аналогия:** Файлы пользователей — это коробки на складе. PostgreSQL — это каталог склада: кто владелец каждой коробки, когда её последний раз трогали, кому открыт доступ. Без каталога ты видишь коробки, но не знаешь что в них и кому они принадлежат. Именно поэтому бэкап базы так же важен, как бэкап самих файлов.

---

## 4.1 Что хранится в БД

Файлы лежат в data directory, но БД хранит метаданные: пользователей, настройки, filecache, приложения, shares, блокировки.

Если потерять БД, одних файлов недостаточно для полного восстановления нормальной системы.

---

## 4.2 Подключение

Имена контейнера и базы могут отличаться. Сначала проверь `docker ps` и переменные окружения/документацию AIO.

Пример:

```bash
docker exec -it nextcloud-aio-database psql -U nextcloud nextcloud_database
```

# Пример вывода (приглашение psql):
```
psql (15.5)
Type "help" for help.

nextcloud_database=#
```

Внутри psql:

```sql
\l
```

# Пример вывода:
```
                                   List of databases
        Name        |   Owner   | Encoding |  Collate   |   Ctype    | ...
--------------------+-----------+----------+------------+------------+-----
 nextcloud_database | nextcloud | UTF8     | en_US.utf8 | en_US.utf8 |
 postgres           | nextcloud | UTF8     | en_US.utf8 | en_US.utf8 |
 template0          | nextcloud | UTF8     | en_US.utf8 | en_US.utf8 |
 template1          | nextcloud | UTF8     | en_US.utf8 | en_US.utf8 |
(4 rows)
```

```sql
\dt
```

# Пример вывода (несколько ключевых таблиц):
```
                      List of relations
 Schema |               Name               | Type  |   Owner
--------+----------------------------------+-------+-----------
 public | oc_accounts                      | table | nextcloud
 public | oc_appconfig                     | table | nextcloud
 public | oc_calendarobjects               | table | nextcloud
 public | oc_filecache                     | table | nextcloud
 public | oc_filecache_extended            | table | nextcloud
 public | oc_share                         | table | nextcloud
 public | oc_storages                      | table | nextcloud
 public | oc_users                         | table | nextcloud
...
(87 rows)
```

```sql
SELECT pg_size_pretty(pg_database_size('nextcloud_database'));
```

# Пример вывода:
```
 pg_size_pretty
----------------
 1.2 GB
(1 row)
```

```sql
VACUUM;
\q
```

# Пример вывода VACUUM:
```
VACUUM
```

---

## 4.3 Обслуживание через occ

```bash
occ db:add-missing-indices
occ db:add-missing-columns
occ db:convert-filecache-bigint
occ maintenance:repair
```

Эти команды часто нужны после обновлений.

---

## 4.4 Практика

Узнай размер БД и запиши его в документацию. Не меняй таблицы вручную. Для администратора Nextcloud основной путь — `occ`, а не ручной SQL.

---

> **Если что-то пошло не так:**
>
> **Симптом:** `docker exec ... psql` выдаёт `could not connect to server: Connection refused` или контейнер базы не отвечает.
>
> ```bash
> # Проверить статус всех контейнеров
> docker ps -a | grep nextcloud
>
> # Пример: nextcloud-aio-database в статусе "Exited (1) 3 minutes ago"
>
> # Посмотреть почему упала база
> docker logs nextcloud-aio-database --tail=50
>
> # Частые причины:
> # - нет места на диске: "could not write to file pg_wal/..."
> # - повреждение данных при некорректном выключении
>
> # Проверить место
> df -h
>
> # Если место есть — попробовать запустить контейнер
> # Правильный способ для AIO — через AIO interface (http://localhost:8080)
> # или:
> docker start nextcloud-aio-database
>
> # После запуска проверить логи
> docker logs nextcloud-aio-database --tail=20
> ```
>
> **Симптом:** psql подключился, но запрос выдаёт `ERROR: relation "oc_filecache" does not exist`.
>
> Убедись, что подключаешься к правильной базе: `psql -U nextcloud nextcloud_database`, а не к `postgres`.
