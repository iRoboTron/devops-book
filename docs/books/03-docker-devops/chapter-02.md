# Глава 2: Образы

> **Запомни:** Образ — это не монолит. Он состоит из слоёв. Понимание слоёв — ключ к быстрым сборкам и маленьким образам.

---

## 2.1 Что такое образ: слои и copy-on-write

В Модуле 0 ты узнал что образ = "упаковка" приложения.
Теперь разберёмся **как** он устроен внутри.

### Образ = стопка слоёв

```
Образ python:3.12-slim
┌──────────────────────────┐
│ Слой 3: pip install ...  │  15 MB
├──────────────────────────┤
│ Слой 2: COPY app.py .    │  50 KB
├──────────────────────────┤
│ Слой 1: python:3.12-slim │  45 MB
└──────────────────────────┘
    Итого: ~60 MB
```

Каждый слой — **read-only**. Слои не меняются.

### Copy-on-Write (CoW)

Когда ты запускаешь контейнер:

```
┌──────────────────────────┐
│  Read-Write слой         │  ← Только для записи
├──────────────────────────┤
│  Слой 3: pip install     │  ← Read-only
├──────────────────────────┤
│  Слой 2: COPY app.py     │  ← Read-only
├──────────────────────────┤
│  Слой 1: python:3.12     │  ← Read-only
└──────────────────────────┘
```

- Чтение = из любого слоя (сверху вниз)
- Запись = только в верхний read-write слой
- Удаление контейнера = read-write слой исчезает

> **Запомни:** Слои образа read-only и **делятся** между контейнерами.
> Два контейнера из одного образа = одни и те же слои на диске.
> Не дублируются!

---

## 2.2 Docker Hub — реестр образов

**Docker Hub** — hub.docker.com — публичный реестр образов.

### Официальные образы

Проверенные образи от Docker:

| Образ | Что внутри |
|-------|-----------|
| `ubuntu` | Ubuntu |
| `python` | Python + Debian |
| `nginx` | Nginx + Debian |
| `postgres` | PostgreSQL + Debian |
| `redis` | Redis + Alpine |
| `alpine` | Минимальный Linux (5 MB) |

### Тег образа

Один образ — много версий:

```
python:3.12.3-slim-bookworm   ← конкретная версия, slim, Debian bookworm
python:3.12-slim              ← последняя 3.12.x, slim
python:3.12                   ← последняя 3.12.x, полная
python:latest                 ← последняя вообще
python:3.11-slim              ← предыдущая версия, slim
```

Формат: `имя:версия-вариант-основа`

### Почему не `latest`

```yaml
# Плохо:
image: python:latest

# Сегодня: 3.12 → работает
# Через месяц: 3.13 → твой код не работает
```

```yaml
# Хорошо:
image: python:3.12-slim

# Всегда 3.12.x. Предсказуемо.
```

> **Запомни:** `latest` — непредсказуем.
> Фиксируй тег. `python:3.12-slim` а не `python:latest`.
> Это как `pip install flask` без версии — завтра сломается.

---

## 2.3 `docker pull` — скачать образ

```bash
docker pull python:3.12-slim
```

Docker скачивает образ с Docker Hub.

```
3.12-slim: Pulling from library/python
a1b2c3d4e5f6: Pull complete
b2c3d4e5f6g7: Pull complete
c3d4e5f6g7h8: Pull complete
Digest: sha256:abc123...
Status: Downloaded newer image for python:3.12-slim
```

Каждая строка `Pull complete` — один слой.

### Скачивается только то чего нет

Если образ частично есть — докачает только недостающие слои:

```bash
docker pull python:3.12-slim
# Уже есть слои 1 и 2
a1b2c3d4e5f6: Already exists    ← не качает
b2c3d4e5f6g7: Already exists    ← не качает
c3d4e5f6g7h8: Pull complete     ← докачивает новый
```

---

## 2.4 `docker images` — список образов

```bash
docker images
REPOSITORY    TAG           IMAGE ID       CREATED       SIZE
python        3.12-slim     abc123def456   2 weeks ago   134MB
nginx         latest        def456ghi789   3 weeks ago   187MB
ubuntu        24.04         ghi789jkl012   1 month ago   78MB
hello-world   latest        jkl012mno345   6 months ago  13.3kB
```

| Колонка | Значение |
|---------|----------|
| `REPOSITORY` | Имя образа |
| `TAG` | Версия |
| `IMAGE ID` | Хэш образа (уникальный) |
| `CREATED` | Когда собран |
| `SIZE` | Размер на диске |

> **Совет:** SIZE — полный размер всех слоёв.
> Если два образа делят слои — реальный размер меньше суммы.

---

## 2.5 `docker rmi` — удалить образ

```bash
docker rmi python:3.12-slim
```

Удаляет образ с тега `3.12-slim`.

### Удалить по ID

```bash
docker rmi abc123def456
```

### Удалить все неиспользуемые

```bash
docker image prune
```

Удаляет "dangling" образы (без тегов, промежуточные).

### Удалить все образы которые не используются контейнерами

```bash
docker image prune -a
```

> **Опасно:** `prune -a` удалит скачанные образы.
> Потом придётся качать снова.
> Используй когда нужно освободить место.

---

## 2.6 Сравнение размеров образов

Не все образы одинаково тяжелые:

```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

### python: разные варианты

| Образ | Размер | Когда использовать |
|-------|--------|-------------------|
| `python:3.12` | ~1 ГБ | Полная система, компиляторы |
| `python:3.12-slim` | ~134 МБ | **Для большинства задач** |
| `python:3.12-alpine` | ~50 МБ | Минимальный, но могут быть проблемы с библиотеками |

### nginx: разные варианты

| Образ | Размер | Когда использовать |
|-------|--------|-------------------|
| `nginx:latest` | ~187 МБ | Стандартный |
| `nginx:alpine` | ~42 МБ | Минимальный, для продакшена |

> **Совет:** `slim` — золотая середина для Python.
> `alpine` — ещё меньше, но musl libc вместо glibc может вызвать проблемы.
> Для начала — используй `slim`.

---

## 2.7 Именование: registry/user/name:tag

Полное имя образа:

```
registry.example.com/my-org/myapp:1.0.0
└──────┬──────┘ └──┬──┘ └─┬───┘ └─┬──┘
   registry      user   name    tag
```

| Часть | По умолчанию | Когда нужно |
|-------|-------------|-------------|
| `registry` | Docker Hub | Свой реестр |
| `user` | `library/` (официальные) | Твой аккаунт |
| `name` | Обязательно | Имя образа |
| `tag` | `latest` | Версия |

### Примеры

```
nginx:alpine              = docker.io/library/nginx:alpine
python:3.12-slim          = docker.io/library/python:3.12-slim
myusername/myapp:1.0      = docker.io/myusername/myapp:1.0
ghcr.io/user/app:v2       = GitHub Container Registry
```

---

## 2.8 `docker history` — посмотреть слои

```bash
docker history python:3.12-slim
IMAGE          CREATED     SIZE
abc123def456   2 weeks ago  45MB    ← python:3.12-slim base
b2c3d4e5f6g7   2 weeks ago  89MB    ← pip install + стандартные пакеты
c3d4e5f6g7h8   3 weeks ago  0B      ← команда (CMD)
```

Показывает из каких слоёв состоит образ и сколько каждый весит.

> **Совет:** Если образ слишком большой — `docker history` покажет какой слой виноват.

---

## 📝 Упражнения

### Упражнение 2.1: Скачать образы
**Задача:**
1. Скачай Python: `docker pull python:3.12-slim`
2. Скачай Nginx: `docker pull nginx:alpine`
3. Скачай Alpine: `docker pull alpine:3.19`

### Упражнение 2.2: Сравнить размеры
**Задача:**
1. Посмотри все образы: `docker images`
2. Какой самый большой? Самый маленький?
3. Скачай ещё `python:3.12` (не slim): `docker pull python:3.12`
4. Сравни: `python:3.12` vs `python:3.12-slim` — разница в размере?

### Упражнение 2.3: Посмотреть слои
**Задача:**
1. Посмотри слои Python: `docker history python:3.12-slim`
2. Посмотри слои Nginx: `docker history nginx:alpine`
3. Какой слой самый большой в каждом образе?

### Упражнение 2.4: Очистка
**Зауда:**
1. Удали конкретный образ: `docker rmi alpine:3.19`
2. Убедись что удалён: `docker images`
3. Запусти dangling-образы: `docker image prune`
4. Сколько места освободилось?

### Упражнение 2.5: DevOps Think
**Задача:** «Ты написал `FROM python:latest` в Dockerfile. Через месяц приложение перестало работать. Почему? Как исправить?»

Ответ:
- `latest` мог обновиться с 3.12 до 3.13
- Python 3.13 может быть несовместим с твоими библиотеками
- Решение: зафиксируй тег `FROM python:3.12-slim`
- Ещё лучше: `FROM python:3.12.3-slim-bookworm` — конкретная версия

---

## 📋 Чеклист главы 2

- [ ] Я понимаю что образ состоит из слоёв (read-only)
- [ ] Я понимаю copy-on-write (запись в верхний слой)
- [ ] Я знаю что такое Docker Hub и официальные образы
- [ ] Я понимаю систему тегов (версия-вариант-основа)
- [ ] Я знаю почему не стоит использовать `latest`
- [ ] Я могу скачать образ (`docker pull`)
- [ ] Я могу посмотреть образы (`docker images`)
- [ ] Я могу удалить образ (`docker rmi`)
- [ ] Я могу посмотреть слои образа (`docker history`)
- [ ] Я понимаю полное имя образа (registry/user/name:tag)
- [ ] Я знаю разницу между slim, alpine и full образами

**Всё отметил?** Переходи к Главе 3 — Dockerfile.
