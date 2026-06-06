# Глава 2: Пользователи, роли и права

**Цель главы:** каждый сервис подключается к PostgreSQL со своим пользователем, у которого есть только необходимые права. Пользователь `postgres` — только для администрирования.

---

## Что вы узнаете

- как устроена система прав в PostgreSQL: роли, привилегии, схемы;
- принцип наименьших привилегий для приложений;
- как создать пользователя с минимальными правами;
- что такое `GRANT` и `REVOKE` и почему без `ALTER DEFAULT PRIVILEGES` ничего не работает.

---

## Роль = пользователь в PostgreSQL

В PostgreSQL **роль** и **пользователь** — это один и тот же объект. Разница только в атрибуте `LOGIN`:

- `CREATE ROLE name;` — создаёт роль без права входа (`LOGIN` = false)
- `CREATE USER name;` — создаёт роль с правом входа (`LOGIN` = true)

`CREATE USER` — это синтаксический сахар над `CREATE ROLE ... WITH LOGIN`.

Роль без `LOGIN` используется как группа прав. Ты выдаёшь права группе, а затем добавляешь в неё пользователей.

```sql
-- Просмотр всех ролей
\du
```

```
                                    List of roles
 Role name  |                         Attributes                         | Member of
------------+------------------------------------------------------------+-----------
 postgres   | Superuser, Create role, Create DB, Replication, Bypass RLS | {}
 appuser    |                                                            | {}
 readonly   |                                                            | {}
```

Или через системную таблицу:

```sql
SELECT rolname,
       rolsuper AS superuser,
       rolcreaterole AS create_role,
       rolcreatedb AS create_db,
       rolcanlogin AS can_login
FROM pg_roles
ORDER BY rolname;
```

```
        rolname        | superuser | create_role | create_db | can_login
-----------------------+-----------+-------------+-----------+-----------
 appuser               | f         | f           | f         | t
 pg_database_owner     | f         | f           | f         | f
 pg_read_all_data      | f         | f           | f         | f
 pg_write_all_data     | f         | f           | f         | f
 postgres              | t         | t           | t         | t
 readonly              | f         | f           | f         | t
(6 rows)
```

Обрати внимание на встроенные роли `pg_read_all_data` и `pg_write_all_data` — появились в PostgreSQL 14. Дают права на чтение/запись всех таблиц во всех БД без явного GRANT. Удобно для аналитики и миграций.

---

## Создание пользователей для приложения

Принцип наименьших привилегий: приложение должно иметь ровно столько прав, сколько нужно для работы, и ни грамом больше.

### Минимальный набор: пользователь + БД + права на схему

```sql
-- Создать пользователя без прав суперпользователя
CREATE USER appuser WITH PASSWORD 'StrongPassword123';

-- Создать БД с владельцем (опционально, но удобно)
CREATE DATABASE myapp OWNER appuser;

-- Подключиться к БД
\c myapp

-- Дать права на схему public
GRANT USAGE ON SCHEMA public TO appuser;

-- Дать права на существующие таблицы
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO appuser;

-- Дать права на будущие таблицы (важно!)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO appuser;
```

### Почему `ALTER DEFAULT PRIVILEGES` — обязательно?

`GRANT ... ON ALL TABLES` даёт права только на таблицы, которые существуют **на момент выполнения GRANT**. После миграции, которая создаёт новую таблицу, `appuser` не будет иметь к ней доступа.

```sql
-- Создали новую таблицу после GRANT
CREATE TABLE orders (id SERIAL PRIMARY KEY, user_id INT, amount NUMERIC);

-- appuser не может читать orders:
-- ERROR: permission denied for table orders
```

`ALTER DEFAULT PRIVILEGES` указывает PostgreSQL: «все будущие таблицы в этой схеме автоматически получают указанные права».

Проверка, какие дефолтные привилегии установлены:

```sql
SELECT pg_catalog.pg_get_userbyid(d.defacluser) AS user,
       defaclnamespace::regnamespace AS schema,
       defaclobjtype,
       pg_catalog.array_to_string(d.defaclacl, ', ') AS privileges
FROM pg_catalog.pg_default_acl d
ORDER BY d.defacluser;
```

### Что умеет и не умеет appuser

```sql
-- Подключиться к своей БД — может
\c myapp appuser

-- Читать данные — может (GRANT SELECT)
SELECT * FROM users LIMIT 1;

-- Создать БД — не может (нет CREATEDB)
CREATE DATABASE another_db;
-- ERROR: permission denied to create database

-- Удалить чужую таблицу — не может (нет прав владельца)
DROP TABLE users;
-- ERROR: must be owner of table users

-- Удалить строки — может (GRANT DELETE)
DELETE FROM users WHERE id = 999;
```

---

## Read-only пользователь для аналитики и мониторинга

Для мониторинга, аналитики и read-replica часто нужен пользователь, который может только читать данные.

```sql
CREATE USER readonly WITH PASSWORD 'ReadOnlyPass123';

\c myapp
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO readonly;
```

В PostgreSQL 14+ есть встроенная роль `pg_read_all_data`, которая даёт SELECT на все таблицы всех БД без явного GRANT:

```sql
GRANT pg_read_all_data TO readonly;
-- Теперь readonly может SELECT из любой таблицы любого schema
```

Проверка:

```sql
\c myapp readonly

SELECT count(*) FROM users;
-- работает

INSERT INTO users (name) VALUES ('test');
-- ERROR: permission denied for table users
```

---

## Разделение прав по схемам

Если несколько сервисов используют одну БД, их данные изолируются через схемы. Каждый сервис видит только свою схему.

```sql
-- Создать схемы для разных сервисов
CREATE SCHEMA service_a;
CREATE SCHEMA service_b;

-- Создать пользователей
CREATE USER service_a_user WITH PASSWORD 'PassA123';
CREATE USER service_b_user WITH PASSWORD 'PassB456';

-- service_a_user видит и меняет только service_a
GRANT USAGE ON SCHEMA service_a TO service_a_user;
GRANT ALL ON ALL TABLES IN SCHEMA service_a TO service_a_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA service_a
  GRANT ALL ON TABLES TO service_a_user;

-- service_b_user видит и меняет только service_b
GRANT USAGE ON SCHEMA service_b TO service_b_user;
GRANT ALL ON ALL TABLES IN SCHEMA service_b TO service_b_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA service_b
  GRANT ALL ON TABLES TO service_b_user;

-- Установить search_path для каждого пользователя
ALTER USER service_a_user SET search_path = service_a, public;
ALTER USER service_b_user SET search_path = service_b, public;
```

Теперь при подключении `service_a_user` видит таблицы схемы `service_a` как `SELECT * FROM users`, а таблицы `service_b` для него невидимы:

```sql
\c myapp service_a_user
SELECT * FROM users;  -- ищет в service_a.users

SELECT * FROM service_b.orders;
-- ERROR: permission denied for schema service_b
```

Этот паттерн часто используется в SaaS-приложениях, где несколько клиентов (tenant'ов) находятся в одной БД, но с разными схемами.

---

## Смена пароля и ротация

Пароли в PostgreSQL хранятся в виде хеша (scram-sha-256, если настроено в pg_hba.conf). Метод шифрования задаётся параметром `password_encryption`:

```sql
SHOW password_encryption;
```

```
 password_encryption
---------------------
 scram-sha-256
(1 row)
```

> В PostgreSQL 10+ по умолчанию используется scram-sha-256. `md5` — устарел, используй только для совместимости со старыми клиентами.

```sql
-- Сменить пароль
ALTER USER appuser WITH PASSWORD 'NewPassword456';

-- Посмотреть, когда истекает пароль (NULL = никогда)
SELECT rolname, rolvaliduntil
FROM pg_roles
WHERE rolname = 'appuser';
```

```
 rolname | rolvaliduntil
---------+---------------
 appuser | (null)
(1 row)
```

```sql
-- Пароль с временем истечения
ALTER USER appuser WITH PASSWORD 'TempPass' VALID UNTIL '2026-12-31 23:59:59+00';

-- Убрать срок действия
ALTER USER appuser VALID UNTIL 'infinity';
```

### Интеграция с Vault

В production лучшая практика — не хранить пароли PostgreSQL в файлах конфигурации вообще. Vault Database Engine (книга 36) создаёт временных пользователей PostgreSQL автоматически:

```
Как это работает:
1. Приложение запрашивает у Vault credentials для PostgreSQL
2. Vault динамически создаёт пользователя в PostgreSQL
3. Пароль генерируется автоматически, живёт N минут (TTL)
4. После истечения TTL Vault удаляет пользователя из PostgreSQL
5. Приложение должно обновлять credentials до истечения TTL

Преимущества:
- Никаких паролей в конфигах и .env файлах
- Автоматическая ротация
- При утечке credentials — живут ограниченное время
- Audit trail: Vault логирует кто и когда запрашивал доступ
```

Настройка Vault Database Engine для PostgreSQL:

```bash
# Включить Database Engine
vault secrets enable database

# Настроить подключение к PostgreSQL
vault write database/config/myapp \
    plugin_name=postgresql-database-plugin \
    allowed_roles="app-role" \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/myapp" \
    username="vault_admin" \
    password="VaultAdminPass"

# Создать роль с TTL
vault write database/roles/app-role \
    db_name=myapp \
    creation_statements="CREATE USER \"{{name}}\" WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
                         GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; \
                         ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"
```

---

## Типичные ошибки

- **Использовать суперпользователя `postgres` для подключения из приложения.** При SQL-инъекции злоумышленник получает полный доступ к серверу PostgreSQL: может создать суперпользователя, прочитать любую БД, выполнить `COPY ... TO PROGRAM`. Для приложения — отдельный пользователь без суперправ.

- **Думать, что `GRANT ALL ON DATABASE` даёт доступ к таблицам.** `GRANT ON DATABASE` даёт только право подключиться (`CONNECT`) и создавать объекты в схеме (`CREATE`). Для доступа к таблицам нужен явный `GRANT ON TABLES` или `GRANT ON ALL TABLES IN SCHEMA`.

- **Не выдать `ALTER DEFAULT PRIVILEGES`.** После миграции новые таблицы будут без прав у appuser. Приложение получает `permission denied`, инцидент, все ищут проблему не в том месте.

- **Хранить пароль в строке подключения в коде.** `postgresql://appuser:password@host/db` — пароль попадает в логи CI/CD, APM-системы (DataDog, New Relic), error tracking (Sentry), git history. Использовать переменные окружения, secrets manager или Vault.

- **Пароль без срока истечения.** Если пароль скомпрометирован, он действителен до ручной смены. В production — ротация каждые 30-90 дней через CI/CD или Vault.

---

## Чек-лист для самопроверки

- [ ] Понимаю, что в PostgreSQL роль = пользователь, и `CREATE USER` = `CREATE ROLE ... WITH LOGIN`
- [ ] Умею создать пользователя с минимальными правами для приложения
- [ ] Знаю, зачем нужен `ALTER DEFAULT PRIVILEGES` и чем отличается от `GRANT ... ON ALL TABLES`
- [ ] Умею создать read-only пользователя для мониторинга и аналитики

---

## Попробуйте сами

1. Создайте пользователя `appuser` без суперправ. Создайте таблицу от имени `postgres`. Попробуйте SELECT от `appuser` — ошибка? Выдайте `GRANT SELECT`. Попробуйте снова. Создайте вторую таблицу — `appuser` снова без прав? Теперь добавьте `ALTER DEFAULT PRIVILEGES` и создайте третью таблицу. Убедитесь, что права на будущие таблицы работают.

2. Подключитесь от имени `appuser` и попробуйте `CREATE DATABASE` — должно быть `permission denied`. Попробуйте `DROP TABLE` чужой таблицы. Убедитесь, что изоляция работает.

3. Создайте read-only пользователя. Подключитесь от его имени. Попробуйте `INSERT` — ошибка. `SELECT` — работает. Это мониторинговый пользователь.
