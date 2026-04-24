# Глава 4: Тома (Volumes) — данные которые не исчезают

> **Запомни:** Контейнер удалил — данные внутри исчезли. Volume — хранилище которое переживает контейнер. Для баз данных это обязательно.

---

## 4.1 Проблема: данные в контейнере временные

Ты запустил PostgreSQL в контейнере:

```bash
docker run -d --name db -e POSTGRES_PASSWORD=secret postgres
```

Создал таблицы, добавил данные. Всё работает.

Затем:

```bash
docker rm -f db
docker run -d --name db -e POSTGRES_PASSWORD=secret postgres
```

**Где данные?** Исчезли. Новый контейнер = чистая база.

### Почему

```
┌──────────────────────────┐
│  Контейнер PostgreSQL    │
│                          │
│  /var/lib/postgresql/data│  ← данные ЗДЕСЬ
│                          │  ← внутри контейнера
└──────────────────────────┘
    ↓ удалил контейнер
  Данные исчезли
```

Данные живут внутри контейнера. Контейнер = временный.

### Решение: вынести данные наружу

```
┌──────────────────────────┐
│  Контейнер PostgreSQL    │
│                          │
│  /var/lib/postgresql/data│──→ Volume: pgdata
└──────────────────────────┘       ← данные здесь
                                       (переживает контейнер)
```

---

## 4.2 Три способа хранить данные

```
1. Volume        docker volume create pgdata     → Docker управляет
2. Bind mount    -v /host/path:/container/path   → Ты управляешь
3. tmpfs         --tmpfs /tmp                    → Только в памяти
```

| Способ | Где данные | Когда использовать |
|--------|-----------|-------------------|
| **Volume** | `/var/lib/docker/volumes/` | Базы данных, кеш |
| **Bind mount** | Твой путь на хосте | Код в разработке, конфиги |
| **tmpfs** | RAM | Временные файлы, секреты |

---

## 4.3 Docker Volume — рекомендуется для баз данных

### Создать том

```bash
docker volume create pgdata
```

### Посмотреть тома

```bash
docker volume ls
DRIVER    VOLUME NAME
local     pgdata
```

### Информация о томе

```bash
docker volume inspect pgdata
[
    {
        "Driver": "local",
        "Mountpoint": "/var/lib/docker/volumes/pgdata/_data",
        "Name": "pgdata",
        ...
    }
]
```

Данные физически в `/var/lib/docker/volumes/pgdata/_data`.

### Использовать с контейнером

```bash
docker run -d --name db \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=secret \
  postgres
```

`-v pgdata:/var/lib/postgresql/data` = "том pgdata внутри контейнера на этот путь".

### Проверить что данные сохраняются

```bash
# 1. Запусти с volume
docker run -d --name db -v pgdata:/var/lib/postgresql/data -e POSTGRES_PASSWORD=secret postgres

# 2. Создай данные (подключись и создай таблицу)
docker exec -it db psql -U postgres -c "CREATE TABLE test (id INT);"

# 3. Удали контейнер
docker rm -f db

# 4. Создай новый с тем же volume
docker run -d --name db -v pgdata:/var/lib/postgresql/data -e POSTGRES_PASSWORD=secret postgres

# 5. Проверь — таблица на месте!
docker exec -it db psql -U postgres -c "\dt"
```

Таблица `test` survived!

> **Запомни:** Volume — твой лучший друг для баз данных.
> Контейнер пересоздал — данные на месте.

---

## 4.4 Bind Mount — код и конфиги

Bind mount = директория с хоста внутри контейнера.

### Для кода (разработка)

```bash
docker run -d --name app -v $(pwd):/app myapp
```

`$(pwd)` = текущая директория на хосте.
`/app` = путь внутри контейнера.

Изменил код на хосте → контейнер видит изменения сразу.

> **Зачем:** Для разработки. Hot reload — изменил файл, сервер перезагрузился.
> Не нужно пересобирать образ при каждом изменении.

### Для конфигов

```bash
docker run -d --name nginx \
  -v ./nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx
```

`:ro` = read-only (контейнер не может изменить конфиг).

> **Совет:** Конфиги всегда монтируй с `:ro`.
> Контейнер не должен менять конфигурацию.

### Разница: Volume vs Bind Mount

| | Volume | Bind Mount |
|--|--------|-----------|
| Где хранится | Docker управляет (`/var/lib/docker/volumes/`) | Твой путь на хосте |
| Права доступа | Docker настраивает | Твои права на хосте |
| Когда использовать | Базы данных, постоянные данные | Код в разработке, конфиги |
| Переносимость | Работает везде | Зависит от ОС хоста |

---

## 4.5 tmpfs — только в памяти

```bash
docker run -d --name app --tmpfs /tmp myapp
```

Данные в `/tmp` живут только в RAM.
Контейнер остановил — данные исчезли.

> **Когда использовать:**
> - Временные файлы которые не нужны после перезапуска
> - Секреты которые не должны касаться диска
> - Кеш который можно потерять

---

## 4.6 Очистка томов

### Удалить неиспользуемые

```bash
docker volume prune
```

Удаляет тома которые не привязаны к контейнерам.

> **Опасно:** Данные в томе исчезнут навсегда.
> Проверь что том не нужен перед удалением.

### Удалить конкретный том

```bash
docker volume rm pgdata
```

### Посмотреть сколько места занимают

```bash
docker system df -v
```

---

## 4.7 Бэкап тома

### Сделать бэкап

```bash
docker run --rm \
  -v pgdata:/source:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/pgdata-backup.tar.gz -C /source .
```

**Что происходит:**
1. `--rm` — временный контейнер
2. `-v pgdata:/source:ro` — подключил том только для чтения
3. `-v $(pwd):/backup` — подключил текущую директорию хоста
4. `alpine tar czf ...` — создал архив

### Восстановить из бэкапа

```bash
docker run --rm \
  -v pgdata:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/pgdata-backup.tar.gz -C /target
```

---

## 📝 Упражнения

### Упражнение 4.1: Volume для PostgreSQL
**Задача:**
1. Создай том: `docker volume create testdb`
2. Запусти PostgreSQL: `docker run -d --name db -v testdb:/var/lib/postgresql/data -e POSTGRES_PASSWORD=secret postgres`
3. Подожди 10 секунд ( PostgreSQL запускается)
4. Создай таблицу: `docker exec -it db psql -U postgres -c "CREATE TABLE users (id INT, name TEXT);"`
5. Проверь: `docker exec -it db psql -U postgres -c "\dt"`
6. Удали контейнер: `docker rm -f db`
7. Создай новый с тем же томом: `docker run -d --name db -v testdb:/var/lib/postgresql/data -e POSTGRES_PASSWORD=secret postgres`
8. Проверь что таблица на месте: `docker exec -it db psql -U postgres -c "\dt"`

### Упражнение 4.2: Bind mount для кода
**Задача:**
1. Создай `~/docker-test/app.py`:
   ```python
   print("Version 1")
   ```
2. Запусти: `docker run --rm -v $(pwd):/app python:3.12-slim python /app/app.py`
3. Что вывелось?
4. Измени `app.py` на `print("Version 2")`
5. Запусти снова — изменился вывод без пересборки образа?

### Упражнение 4.3: Чтение тома
**Задача:**
1. Создай том и запиши данные (как в 4.1)
2. Посмотри где данные: `docker volume inspect testdb`
3. Посмотри размер: `ls -la /var/lib/docker/volumes/testdb/_data`

### Упражнение 4.4: Очистка
**Задача:**
1. Останови контейнер: `docker rm -f db`
2. Удали том: `docker volume rm testdb`
3. Проверь: `docker volume ls` — том исчез?
4. Запусти prune: `docker volume prune`

---

## 📋 Чеклист главы 4

- [ ] Я понимаю проблему: данные в контейнере временные
- [ ] Я знаю три способа хранения: volume, bind mount, tmpfs
- [ ] Я могу создать и использовать volume для базы данных
- [ ] Я могу использовать bind mount для кода в разработке
- [ ] Я понимаю разницу между volume и bind mount
- [ ] Я могу сделать бэкап тома и восстановить
- [ ] Я могу очистить неиспользуемые тома

**Всё отметил?** Переходи к Главе 5 — сети Docker.
