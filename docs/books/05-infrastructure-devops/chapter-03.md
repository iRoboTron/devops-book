# Глава 3: PostgreSQL — правильная настройка

> **Запомни:** `postgres` суперпользователь в приложении = как root для всей базы. Отдельный пользователь с минимальными правами — база безопасности.

---

## 3.1 PostgreSQL в Docker vs на хосте

### В Docker

```yaml
services:
  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
```

| Плюс | Минус |
|------|-------|
| Легко поднять | Небольшой overhead сети |
| Легко обновить | Бэкапы через `docker exec` |
| Переносимо | Сложнее тонкая настройка |

### На хосте

```bash
sudo apt install postgresql-16
```

| Плюс | Минус |
|------|-------|
| Лучше производительность | Сложнее управление версиями |
| Проще бэкапы (pg_dump напрямую) | Привязка к серверу |
| Нет overhead | Сложнее поднять несколько инстансов |

> **Запомни:** Книга учит Docker-способ (продолжение Модуля 3).
> Но принципы одинаковы: пользователи, права, параметры.

---

## 3.2 Пользователи и права

### Плохо: суперпользователь в приложении

```yaml
environment:
  DATABASE_URL: postgresql://postgres:pass@db/mydb
```

`postgres` — суперпользователь. Может:
- Удалить любую базу
- Создать нового пользователя
- Изменить любую таблицу
- Прочитать любые данные

SQL-инъекция в приложении = полный доступ ко всему.

### Хорошо: отдельный пользователь

```sql
-- Подключись к PostgreSQL
docker compose exec db psql -U postgres

-- Создать пользователя (только для своего приложения)
CREATE USER myapp WITH PASSWORD 'x7k9mP2qR5wN';

-- Создать базу
CREATE DATABASE myapp_prod OWNER myapp;

-- Права
GRANT CONNECT ON DATABASE myapp_prod TO myapp;
```

Теперь `myapp` может:
- ✅ Читать и писать в `myapp_prod`
- ❌ Не может удалить базу
- ❌ Не может создать нового пользователя
- ❌ Не может читать другие базы

### Проверить

```bash
# Подключиться как myapp
docker compose exec db psql -U myapp -d myapp_prod

-- Попробовать удалить базу (должно упасть):
DROP DATABASE myapp_prod;
-- ERROR: must be owner of database myapp_prod

-- Попробовать создать пользователя:
CREATE USER hacker WITH PASSWORD 'hack';
-- ERROR: permission denied to create role
```

> **Запомни:** Принцип минимальных привилегий.
> Приложение получает только то что ему нужно.

---

## 3.3 Основные команды `psql`

```bash
# Подключиться
docker compose exec db psql -U myapp -d myapp_prod
```

```sql
-- Список баз
\l

-- Подключиться к базе
\c myapp_prod

-- Список таблиц
\dt

-- Описание таблицы
\d users

-- Список пользователей
\du

-- Выполнить запрос
SELECT count(*) FROM users;

-- Выйти
\q
```

> **Совет:** `\` команды — только в psql.
> Обычные SQL запросы — как обычно.

---

## 3.4 `pg_hba.conf` — кто может подключаться

`pg_hba.conf` контролирует **кто** и **как** подключается.

```
# TYPE  DATABASE  USER    ADDRESS       METHOD
host    myapp_prod  myapp  0.0.0.0/0    scram-sha-256
local   all         all                 peer
```

| Поле | Значение |
|------|----------|
| `host` | TCP-подключение |
| `local` | Unix-сокет (локально) |
| `DATABASE` | Какая база |
| `USER` | Какой пользователь |
| `ADDRESS` | С какого IP |
| `METHOD` | Как аутентифицировать |

### Методы аутентификации

| Метод | Когда |
|-------|-------|
| `scram-sha-256` | По паролю (безопасно) |
| `md5` | По паролю (старый, не используй) |
| `peer` | По имени пользователя ОС (локально) |
| `trust` | Без пароля (только для тестов!) |

> **Опасно:** `trust` = любой подключается без пароля.
> Никогда не используй на продакшне.

### В Docker

PostgreSQL в Docker слушает только внутри Docker-сети.
Наружу порт не проброшен → никто снаружи не подключится.

```yaml
services:
  db:
    image: postgres:16
    # ports:  ← НЕТ! Не пробрасывай 5432 наружу
    networks:
      - backend
```

---

## 3.5 Параметры производительности

Эти параметры в `postgresql.conf`.

### shared_buffers

```
shared_buffers = 256MB
```

Сколько памяти PostgreSQL использует для кеширования данных.

**Правило:** ~25% от RAM сервера.

| RAM сервера | shared_buffers |
|-------------|---------------|
| 2 ГБ | 512MB |
| 4 ГБ | 1GB |
| 8 ГБ | 2GB |

### effective_cache_size

```
effective_cache_size = 1GB
```

Сколько памяти доступно для кеша (включая OS cache).

**Правило:** ~75% от RAM.

### max_connections

```
max_connections = 100
```

Максимум одновременных подключений.

> **Совет:** Не ставь 1000.
> Каждое соединение ест память.
> 100 = достаточно для большинства приложений.
> Если нужно больше — используй PgBouncer (пул соединений).

### work_mem

```
work_mem = 64MB
```

Память на одну сортировку/хеш-таблицу.

**Правило:** `RAM / (max_connections * 2)`.

Для 4GB RAM и 100 соединений: `4096 / 200 = 20MB`.

### Как настроить в Docker

```yaml
services:
  db:
    image: postgres:16
    command: >
      postgres
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c max_connections=100
      -c work_mem=64MB
    volumes:
      - pgdata:/var/lib/postgresql/data
```

Или через файл конфигурации:

```yaml
    volumes:
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

> **Запомни:** Не копируй параметры слепо.
> Пойми что каждый делает — и подставь свои значения.

---

## 3.6 `pg_activity` — мониторинг запросов

`pg_activity` — как `htop` но для PostgreSQL.

```bash
pip install pg_activity
pg_activity -U myapp -d myapp_prod
```

Показывает:
- Активные запросы
- Время выполнения
- Блокировки
- Нагрузку на CPU/память

> **Совет:** Удобно когда сервер тормозит и ты не понимаешь почему.
> Один взгляд — и видишь какой запрос завис.

---

## 📝 Упражнения

### Упражнение 3.1: Отдельный пользователь
**Задача:**
1. Подключись к PostgreSQL: `docker compose exec db psql -U postgres`
2. Создай пользователя: `CREATE USER myapp WITH PASSWORD 'secret';`
3. Создай базу: `CREATE DATABASE myapp_prod OWNER myapp;`
4. Проверь: `\du` — пользователь есть?
5. Подключись как myapp: `docker compose exec db psql -U myapp -d myapp_prod`
6. Попробуй удалить базу — получилось? (не должно)

### Упражнение 3.2: Параметры
**Задача:**
1. Добавь параметры в docker-compose.yml (как в 3.5)
2. Перезапусти: `docker compose up -d db`
3. Проверь: `docker compose exec db psql -U postgres -c "SHOW shared_buffers;"`
4. Значение правильное?

### Упражнение 3.3: Проверка безопасности
**Задача:**
1. Убедись что порт 5432 НЕ проброшен: `ss -tlnp | grep 5432`
2. Пусто? ✅ (порт только внутри Docker-сети)
3. Если проброшен — убери `ports:` из compose и перезапусти

### Упражнение 3.4: pg_activity
**Задача:**
1. Установи: `pip install pg_activity`
2. Запусти: `pg_activity -U myapp -d myapp_prod`
3. Посмотри на активные запросы
4. Нажми `q` для выхода

### Упражнение 3.5: DevOps Think
**Задача:** «Приложение подключается к БД как `postgres`. Ты создал отдельного пользователя `myapp`. Как перевести приложение без даунтайма?»

Ответ:
1. Обнови `DATABASE_URL` в `.env` на нового пользователя
2. Дай новому пользователю те же права на существующие таблицы:
   ```sql
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myapp;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO myapp;
   ```
3. Перезапусти приложение: `docker compose up -d app`
4. Проверь что работает: `curl http://localhost/health`

---

## 📋 Чеклист главы 3

- [ ] PostgreSQL работает от отдельного пользователя (не postgres)
- [ ] Приложение подключается с минимальными правами
- [ ] Пользователь НЕ может удалить базу или создать роль
- [ ] Порт 5432 НЕ проброшен наружу
- [ ] Параметры производительности настроены (shared_buffers, max_connections)
- [ ] Я знаю основные команды psql (\l, \dt, \du, \q)
- [ ] Я понимаю pg_hba.conf и методы аутентификации

**Всё отметил?** Переходи к Главе 4 — миграции базы данных.
