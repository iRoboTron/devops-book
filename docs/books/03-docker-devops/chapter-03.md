# Глава 3: Dockerfile — написать свой образ

> **Запомни:** Dockerfile — это рецепт. Каждая инструкция = слой образа. Порядок инструкций влияет на скорость сборки.

---

## 3.1 Что такое Dockerfile

**Dockerfile** — текстовый файл с инструкциями для сборки образа.

```
Dockerfile → docker build → Образ → docker run → Контейнер
```

Это как shell-скрипт но для сборки образа.

### Минимальный Dockerfile

```dockerfile
FROM python:3.12-slim
CMD ["echo", "Hello from Docker!"]
```

Собери:
```bash
docker build -t hello .
```

Запусти:
```bash
docker run hello
Hello from Docker!
```

---

## 3.2 `FROM` — базовый образ

```dockerfile
FROM python:3.12-slim
```

**Что делает:** Говорит Docker с какого образа начать.

**Зачем:** Ты не начинаешь с нуля. Ты берёшь готовый образ со всем нужным.

**Что будет если убрать:** Docker не поймёт от чего строить. Ошибка сборки.

> **Совет:** Для Python всегда `python:X.Y-slim`.
> Не `ubuntu` + установка Python вручную.
> Не `python:latest`.

---

## 3.3 `WORKDIR` — рабочая директория

```dockerfile
WORKDIR /app
```

**Что делает:** Создаёт директорию и переходит в неё.

**Зачем:** Все последующие команды будут выполняться в этой папке.

**Что будет если убрать:** Будет `/` (корень). Файлы будут разбросаны.

### Эквивалент без WORKDIR

```dockerfile
# С WORKDIR:
WORKDIR /app
COPY app.py .

# Без WORKDIR (так не делай):
COPY app.py /app/app.py
RUN cd /app && python app.py
```

> **Запомни:** `WORKDIR` создаёт директорию если её нет.
> Не нужен `RUN mkdir /app`.

---

## 3.4 `COPY` — скопировать файлы

```dockerfile
COPY requirements.txt .
```

**Что делает:** Копирует файл с хоста в образ.

**Формат:** `COPY откуда куда`

`.` = текущая WORKDIR.

### Скопировать всё

```dockerfile
COPY . .
```

Всё из директории где Dockerfile — в WORKDIR образа.

### Что будет если убрать

Приложение не попадёт в образ. Контейнер запустится без кода.

> **Опасно:** `COPY . .` копирует ВСЁ включая `.git`, `__pycache__`, `.env`.
> Используй `.dockerignore` чтобы исключить ненужное.

---

## 3.5 `RUN` — выполнить при сборке

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

**Что делает:** Выполняет команду **во время сборки** образа.

**Зачем:** Установить зависимости, создать файлы, настроить систему.

**Что будет если убрать:** Зависимости не установятся. Приложение упадёт при запуске.

### RUN vs CMD

| Инструкция | Когда выполняется | Сколько раз |
|-----------|------------------|-------------|
| `RUN` | При сборке образа (`docker build`) | Один раз при сборке |
| `CMD` | При запуске контейнера (`docker run`) | Каждый раз при запуске |

```dockerfile
RUN pip install flask    ← при сборке (установить flask в образ)
CMD ["python", "app.py"] ← при запуске (запустить приложение)
```

> **Запомни:** RUN = "собрать". CMD = "запустить".
> Не путай — частая ошибка новичков.

---

## 3.6 `ENV` — переменная окружения

```dockerfile
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
```

**Что делает:** Устанавливает переменную в образе.

**Зачем:** Приложение может читать переменные через `os.environ`.

**Что будет если убрать:** Приложение будет использовать значения по умолчанию.

> **Опасно:** Не храни секреты в ENV в Dockerfile!
> `ENV DB_PASSWORD=secret` останется в слоях образа навсегда.
> Для секретов — передавай через `docker run -e` или `.env` файл.

---

## 3.7 `EXPOSE` — документация порта

```dockerfile
EXPOSE 8000
```

**Что делает:** **Документирует** какой порт использует приложение.

**Зачем:** Подсказка для людей и инструментов. `docker run -P` откроет этот порт.

**Что будет если убрать:** Ничего! Это только документация. Порт всё равно нужно пробрасывать через `-p`.

> **Запомни:** `EXPOSE` НЕ открывает порт.
> Это как комментарий "приложение слушает 8000".
> Для реального проброса: `docker run -p 8000:8000`.

---

## 3.8 `CMD` — команда по умолчанию

```dockerfile
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Что делает:** Команда которая запустится когда ты сделаешь `docker run`.

**Формат:** JSON-массив (список аргументов).

**Что будет если убрать:** Образ соберётся но при `docker run` будет ошибка: "No command specified".

### CMD vs ENTRYPOINT

`CMD` можно переопределить при запуске:

```dockerfile
CMD ["python", "app.py"]
```

```bash
docker run myapp              # запустит python app.py
docker run myapp bash         # запустит bash (переопределил CMD)
```

`ENTRYPOINT` нельзя переопределить (без `--entrypoint`):

```dockerfile
ENTRYPOINT ["python", "app.py"]
```

```bash
docker run myapp              # запустит python app.py
docker run myapp bash         # запустит python app.py bash (app получил аргумент "bash")
```

> **Совет:** Для начала используй только `CMD`.
> `ENTRYPOINT` нужен когда хочешь чтобы контейнер ВСЕГДА запускал одно приложение.

---

## 3.9 Полный Dockerfile для Python-приложения

```dockerfile
# Базовый образ
FROM python:3.12-slim

# Переменная чтобы Python не буферизовал вывод (логи сразу видны)
ENV PYTHONUNBUFFERED=1

# Рабочая директория
WORKDIR /app

# Сначала зависимости (лучше для кэша)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потом код
COPY . .

# Документация порта
EXPOSE 8000

# Команда запуска
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 3.10 Почему `requirements.txt` ДО `COPY . .`

Это **критически важная** концепция — кэш слоёв Docker.

### Медленно (плохой порядок)

```dockerfile
COPY . .                              ← слой A
RUN pip install -r requirements.txt   ← слой B
```

Ты изменил одну строчку в `app.py`:

```
Сборка #1: слой A (кэш), слой B (кэш)  ← 30 секунд
Сборка #2: изменил app.py
           → слой A пересобран (код изменился)
           → слой B ПЕРЕСОБРАН (зависит от A!)  ← 30 секунд заново!
```

`pip install` запускается каждый раз даже если `requirements.txt` не менялся.

### Быстро (хороший порядок)

```dockerfile
COPY requirements.txt .               ← слой A
RUN pip install -r requirements.txt   ← слой B
COPY . .                              ← слой C
```

Ты изменил одну строчку в `app.py`:

```
Сборка #1: слой A (кэш), слой B (кэш), слой C (кэш)  ← 30 секунд
Сборка #2: изменил app.py
           → слой A кэш (requirements.txt не менялся!)
           → слой B кэш (pip install из кэша!)
           → слой C пересобран (код изменился)  ← 2 секунды!
```

> **Запомни:** 
> 1. Сначала `COPY requirements.txt`
> 2. Потом `RUN pip install`
> 3. Потом `COPY . .`
> 
> Это ускоряет сборку в 10-50 раз.

### Визуально

```
Изменился requirements.txt:
  [COPY req.txt] → пересобрать
  [pip install]  → пересобрать
  [COPY . .]     → пересобрать

Изменился app.py:
  [COPY req.txt] → кэш ✓
  [pip install]  → кэш ✓
  [COPY . .]     → пересобрать ← только это!
```

---

## 3.11 `docker build` — собрать образ

```bash
docker build -t myapp:1.0 .
```

| Часть | Значение |
|-------|----------|
| `-t myapp:1.0` | Тег (имя:версия) |
| `.` | Контекст сборки (текущая директория) |

### Что видит Docker

```
[+] Building 3.2s
[1/5] FROM python:3.12-slim          ← FROM
[2/5] WORKDIR /app                   ← WORKDIR
[3/5] COPY requirements.txt .        ← COPY
[4/5] RUN pip install ...            ← RUN
[5/5] COPY . .                       ← COPY
```

### Проверить что собралось

```bash
docker images
REPOSITORY   TAG   SIZE
myapp        1.0   156MB
```

### Запустить

```bash
docker run -d --name myapp -p 8000:8000 myapp:1.0
```

---

## 3.12 `.dockerignore` — что НЕ копировать

Создай файл `.dockerignore` рядом с Dockerfile:

```
.git
__pycache__
*.pyc
.env
venv/
.idea/
.vscode/
*.md
Dockerfile
docker-compose.yml
```

Docker НЕ будет копировать эти файлы в образ.

> **Опасно:** `.env` с паролями в образе = катастрофа.
> Он останется в слоях навсегда, даже если потом удалить.
> Всегда добавляй `.env` в `.dockerignore`.

---

## 3.13 `docker build --no-cache` — пересобрать без кэша

```bash
docker build --no-cache -t myapp:1.0 .
```

Пересоберёт все слои с нуля.

> **Когда использовать:** Когда кэш сломался или ты не понимаешь почему образ неправильный.
> Обычно не нужен — Docker сам правильно управляет кэшем.

---

## 📝 Упражнения

### Упражнение 3.1: Минимальный Dockerfile
**Задача:**
1. Создай директорию: `mkdir ~/docker-test && cd ~/docker-test`
2. Создай Dockerfile:
   ```dockerfile
   FROM python:3.12-slim
   CMD ["echo", "Hello from my first Dockerfile!"]
   ```
3. Собери: `docker build -t hello .`
4. Запусти: `docker run hello`
5. Что вывелось?

### Упражнение 3.2: Dockerfile с кодом
**Задача:**
1. Создай `~/docker-test/main.py`:
   ```python
   print("App is running!")
   ```
2. Создай `~/docker-test/requirements.txt` (пустой)
3. Создай Dockerfile:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["python", "main.py"]
   ```
4. Собери: `docker build -t myapp .`
5. Запусти: `docker run myapp`
6. Что вывелось?

### Упражнение 3.3: Кэш слоёв
**Задача:**
1. Измени `main.py` (добавь `print("Changed!")`)
2. Собери снова: `docker build -t myapp .`
3. Видишь `[cached]` на шагах pip install?
4. Теперь измени `requirements.txt` (добавь `requests`)
5. Собери снова — pip install пересобрался?

### Упражнение 3.4: .dockerignore
**Задача:**
1. Создай `.git`, `__pycache__`, `.env` в директории
2. Добавь `.dockerignore`:
   ```
   .git
   __pycache__
   .env
   ```
3. Собери с `--progress=plain`: `docker build --progress=plain -t myapp .`
4. Убедись что excluded файлы не копируются

### Упражнение 3.5: DevOps Think
**Задача:** «Твой Dockerfile копирует `.env` с паролями. Ты удалил его командой `RUN rm .env`. Всё в порядке?»

Ответ:
- НЕТ! `.env` остался в слое `COPY . .`
- `RUN rm .env` создал новый слой, но предыдущий слой всё ещё содержит `.env`
- Любой кто скачает образ может посмотреть историю слоёв и найти `.env`
- Решение: добавь `.env` в `.dockerignore`
- Секреты передай через `-e` или `.env` файл при запуске

---

## 📋 Чеклист главы 3

- [ ] Я понимаю что Dockerfile — рецепт сборки
- [ ] Я понимаю каждую инструкцию: FROM, WORKDIR, COPY, RUN, ENV, EXPOSE, CMD
- [ ] Я понимаю разницу между RUN (сборка) и CMD (запуск)
- [ ] Я понимаю почему requirements.txt идёт ДО COPY . . (кэш слоёв)
- [ ] Я могу собрать образ (`docker build -t`)
- [ ] Я могу использовать `.dockerignore`
- [ ] Я не копирую `.env` и секреты в образ
- [ ] Я понимаю что EXPOSE только документирует порт

**Всё отметил?** Переходи к Главе 4 — тома (volumes).
