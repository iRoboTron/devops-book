# Инструкция для ИИ-агента: Написание книги по Docker для DevOps

> **Это Модуль 3 курса DevOps.**
> Смотри также:
> - [AGENT-INSTRUCTIONS.md](AGENT-INSTRUCTIONS.md) — Модуль 1 (Linux)
> - [AGENT-INSTRUCTIONS-module-02.md](AGENT-INSTRUCTIONS-module-02.md) — Модуль 2 (Сеть, Nginx)

---

## Контекст проекта

Этот проект — обучение DevOps с нуля до самостоятельности.
Ученик — программист, который прошёл Модули 1 и 2.

**Что он уже умеет** (не повторяй, считай само собой разумеющимся):
- Уверенно работает в Linux-терминале
- Знает права, процессы, сервисы (`systemctl`, `journalctl`)
- Настраивал Nginx как reverse proxy, получал SSL-сертификат
- Умеет настраивать `ufw`, читать логи, диагностировать проблемы
- Писал shell-скрипты, создавал systemd-сервисы
- Понимает как работает HTTP, DNS, порты

**Что он хочет после этой книги:**
Взять Python-приложение с зависимостями и упаковать его в Docker-контейнер так, чтобы оно одинаково запускалось на ноутбуке и на сервере. Уметь поднять несколько сервисов (приложение + база данных + Nginx) одной командой через docker-compose. Понимать что происходит внутри, а не просто копировать чужой docker-compose.yml.

---

## Что за книга

**Название:** "Docker для DevOps: Контейнеры, образы и Compose"

**Место в курсе:** Книга 3 из 4

**Целевая аудитория:**
- Прошёл Модули 1 и 2
- Слышал про Docker, но никогда не писал Dockerfile самостоятельно
- Хочет понять зачем вообще нужны контейнеры, а не просто выучить команды

**Объём:** 130-170 страниц

**Стиль:** тот же, что в Модулях 1 и 2:
- Простой язык, без академизма
- Одна концепция — одно объяснение
- ASCII-схемы для архитектуры и потоков данных
- Много практики, реальные задачи
- Без воды

---

## Главная идея, которую должна передать книга

Docker решает одну конкретную проблему: **"у меня работает, у тебя не работает"**.

Всё остальное — следствие этой идеи:
- Образ = воспроизводимая упаковка приложения
- Контейнер = запущенная копия образа
- Dockerfile = рецепт сборки
- docker-compose = оркестрация нескольких контейнеров
- Volume = данные которые переживают контейнер
- Network = как контейнеры видят друг друга

**Каждая глава должна отвечать на вопрос "зачем", а не просто "как".**

---

## Что читатель построит к концу книги

```
docker-compose up -d
        │
        ├── [nginx:443] ← ./nginx/conf.d/app.conf
        │       │ proxy_pass
        │       ▼
        ├── [python-app:8000] ← Dockerfile (твой код)
        │       │ DATABASE_URL
        │       ▼
        └── [postgres:5432] ← volume: pgdata
                │
                └── volume: pgdata (данные не теряются при restart)
```

Один `docker-compose up` поднимает весь стек. `docker-compose down` останавливает.
Код меняется → `docker-compose build && docker-compose up -d` → обновление.

**Каждая глава — один элемент этой схемы.**

---

## Структура книги

### Глава 0: Зачем Docker и чем он отличается от виртуалки

**Цель:** читатель понимает ключевую идею — не просто "что такое контейнер", а **зачем** он нужен именно ему.

- Проблема "у меня работает": зависимости, версии Python, системные библиотеки
- Виртуальная машина vs контейнер — в чём реальная разница:
  ```
  ВМ:         [ App ] [ App ]
              [ Guest OS ][ Guest OS ]
              [ Hypervisor            ]
              [ Host OS               ]

  Docker:     [ App ] [ App ]
              [ Container runtime     ]
              [ Host OS               ]
  ```
- Ключевые понятия: образ, контейнер, слои, registry
- Установка Docker на Ubuntu (официальный способ, не через `apt install docker.io`)
- Проверка: `docker run hello-world`
- `docker --version`, `docker info`
- **Упражнений нет** — это обзорная глава, практика начнётся со следующей

> **Запомни:** Контейнер — это не мини-виртуалка. Это изолированный процесс на хосте с собственной файловой системой.

---

### Часть 1: Образы и контейнеры (Главы 1-3)

#### Глава 1: Первый контейнер

**Цель:** читатель запускает контейнеры и понимает их жизненный цикл.

- `docker run` — анатомия команды
  - `docker run ubuntu echo "hello"` — запустить и выйти
  - `docker run -it ubuntu bash` — интерактивный режим
  - `docker run -d nginx` — в фоне
  - `docker run --name myapp ...` — имя контейнера
  - `docker run -p 8080:80 nginx` — проброс портов (хост:контейнер)
  - `docker run --rm ...` — удалить после остановки
- Жизненный цикл контейнера:
  ```
  создан → запущен → остановлен → удалён
  (created) (running) (stopped)  (removed)
  ```
- `docker ps` — запущенные контейнеры
- `docker ps -a` — все (включая остановленные)
- `docker stop / start / restart / rm`
- `docker logs myapp` — логи контейнера
- `docker logs -f myapp` — следить в реальном времени
- `docker exec -it myapp bash` — зайти внутрь запущенного контейнера
- **Упражнения:** запустить Nginx в контейнере, зайти внутрь, посмотреть логи, остановить

> **Запомни:** Контейнер — это процесс. Остановил процесс — контейнер остановлен. Данные внутри контейнера исчезают при `docker rm`.

#### Глава 2: Образы

**Цель:** читатель понимает откуда берутся образы и как ими управлять.

- Что такое образ: слои, copy-on-write
  ```
  Образ nginx:latest
  ├── Layer 3: nginx config files (2MB)
  ├── Layer 2: nginx binary (10MB)
  └── Layer 1: debian:bookworm-slim (28MB)
  ```
- Docker Hub — реестр образов: hub.docker.com
  - Официальные образы: `ubuntu`, `python`, `postgres`, `nginx`
  - Тег: `python:3.12-slim` vs `python:3.12` vs `python:latest`
- `docker pull python:3.12-slim`
- `docker images` — список локальных образов
- `docker rmi` — удалить образ
- `docker image prune` — удалить неиспользуемые
- Именование: `registry/user/name:tag`
- Почему `python:3.12-slim` а не `python:latest`:
  - `latest` непредсказуем (сегодня 3.12, завтра 3.13)
  - `slim` = без лишних пакетов, меньше размер, меньше уязвимостей
- **Упражнения:** найти образ на Docker Hub, скачать несколько версий, сравнить размеры

> **Совет:** Всегда фиксируй тег образа. `python:latest` в продакшне — это бомба замедленного действия.

#### Глава 3: Dockerfile — написать свой образ

**Цель:** читатель пишет Dockerfile для реального Python-приложения.

- Что такое Dockerfile: рецепт сборки образа
- Базовые инструкции:
  - `FROM` — базовый образ
  - `WORKDIR` — рабочая директория (создаёт и переходит)
  - `COPY` — скопировать файлы с хоста в образ
  - `RUN` — выполнить команду при сборке
  - `ENV` — переменная окружения
  - `EXPOSE` — документация порта (не открывает!)
  - `CMD` — команда по умолчанию при запуске
  - `ENTRYPOINT` — точка входа (разница с CMD)
- Минимальный Dockerfile для FastAPI/Flask:
  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- `docker build -t myapp:1.0 .`
- `docker build` — что происходит при каждом шаге
- Слои и кэш: почему `COPY requirements.txt` идёт ДО `COPY . .`
  ```
  # Медленно (кэш ломается при любом изменении кода):
  COPY . .
  RUN pip install -r requirements.txt

  # Быстро (кэш pip держится пока requirements.txt не изменился):
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  ```
- `.dockerignore` — что не копировать (`.git`, `__pycache__`, `.env`, `venv`)
- `docker build --no-cache` — пересобрать без кэша
- **Упражнения:** написать Dockerfile для своего Python-приложения, оптимизировать порядок инструкций, измерить размер образа

> **Опасно:** Не копируй `.env` файл с секретами в образ. Он останется в слоях образа навсегда, даже если потом удалить командой `RUN rm .env`.

---

### Часть 2: Данные и сеть (Главы 4-5)

#### Глава 4: Тома (Volumes) — данные которые не исчезают

**Цель:** читатель решает проблему потери данных при пересоздании контейнера.

- Проблема: база данных в контейнере теряет данные при `docker rm`
- Три способа хранить данные:
  ```
  1. Volume     docker volume create pgdata    → Docker управляет
  2. Bind mount -v /host/path:/container/path  → Ты управляешь
  3. tmpfs      --tmpfs /tmp                   → Только в памяти
  ```
- **Docker Volume** (рекомендуется для баз данных):
  - `docker volume create pgdata`
  - `docker volume ls`
  - `docker volume inspect pgdata`
  - `docker run -v pgdata:/var/lib/postgresql/data postgres`
  - Данные живут в `/var/lib/docker/volumes/` на хосте
- **Bind Mount** (рекомендуется для кода в разработке):
  - `docker run -v $(pwd):/app myapp` — код с хоста внутри контейнера
  - Изменения в коде сразу видны контейнеру (hot reload)
  - Права доступа: UID/GID хоста vs контейнера
- `docker volume prune` — удалить неиспользуемые тома
- Бэкап тома: как сделать и восстановить
- **Упражнения:** запустить PostgreSQL с volume, наполнить данными, пересоздать контейнер — проверить что данные сохранились

#### Глава 5: Сети Docker

**Цель:** читатель понимает как контейнеры видят друг друга и изолированы от внешнего мира.

- По умолчанию контейнеры изолированы от хоста и друг от друга
- Типы сетей Docker:
  ```
  bridge   (по умолчанию) — изолированная сеть, выход через NAT
  host     — контейнер использует сеть хоста напрямую
  none     — без сети совсем
  custom   — именованная bridge-сеть (рекомендуется)
  ```
- Почему custom bridge лучше default bridge:
  - В custom сети контейнеры видят друг друга **по имени** (DNS)
  - В default bridge — только по IP (который меняется при рестарте)
- `docker network create mynet`
- `docker network ls`
- `docker run --network mynet --name app ...`
- `docker run --network mynet --name db postgres`
- Из контейнера `app` можно обращаться к `db:5432` (по имени!)
- `docker network inspect mynet`
- `docker network connect / disconnect`
- Схема сетей в типичном стеке:
  ```
  Интернет
      │
  [nginx] — port 443 открыт наружу
      │ (custom bridge сеть)
  [python-app] — не виден снаружи
      │ (та же сеть)
  [postgres] — не виден снаружи
  ```
- **Упражнения:** запустить app + db в одной сети, проверить что db не доступен снаружи, но доступен из app

---

### Часть 3: Docker Compose (Главы 6-7)

#### Глава 6: docker-compose — весь стек одной командой

**Цель:** читатель описывает многоконтейнерное приложение в одном файле.

- Проблема: `docker run` с 10 флагами — неудобно и не воспроизводимо
- `docker-compose.yml` — декларативное описание стека
- Структура файла:
  ```yaml
  services:
    app:
      ...
    db:
      ...
  volumes:
    ...
  networks:
    ...
  ```
- Полный пример для Python + PostgreSQL:
  ```yaml
  services:
    app:
      build: .
      ports:
        - "8000:8000"
      environment:
        DATABASE_URL: postgresql://user:pass@db:5432/mydb
      depends_on:
        db:
          condition: service_healthy
      networks:
        - backend

    db:
      image: postgres:16
      environment:
        POSTGRES_USER: user
        POSTGRES_PASSWORD: pass
        POSTGRES_DB: mydb
      volumes:
        - pgdata:/var/lib/postgresql/data
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U user"]
        interval: 5s
        timeout: 3s
        retries: 5
      networks:
        - backend

  volumes:
    pgdata:

  networks:
    backend:
  ```
- Основные команды:
  - `docker-compose up -d` — поднять в фоне
  - `docker-compose down` — остановить и удалить контейнеры
  - `docker-compose down -v` — и тома тоже (осторожно!)
  - `docker-compose build` — пересобрать образы
  - `docker-compose logs -f app` — логи сервиса
  - `docker-compose exec app bash` — зайти внутрь
  - `docker-compose ps` — статус сервисов
  - `docker-compose restart app` — перезапустить один сервис
- `depends_on` с `condition: service_healthy` — почему просто `depends_on` недостаточно
- **Упражнения:** написать docker-compose.yml для своего проекта, проверить что `docker-compose down && docker-compose up` не теряет данные

> **Запомни:** `docker-compose down -v` удаляет тома. База данных исчезнет. Всегда думай перед `-v`.

#### Глава 7: Переменные окружения и секреты

**Цель:** читатель не хранит пароли в docker-compose.yml и Dockerfile.

- Почему нельзя хардкодить секреты:
  - Образ в Docker Hub — виден всем
  - `git log` — история хранит удалённые строки
- Три способа передавать переменные:
  ```
  1. environment: в docker-compose.yml  → только для несекретных
  2. .env файл + ${VAR} в compose       → секреты на сервере
  3. Docker secrets                     → для серьёзного продакшна
  ```
- `.env` файл рядом с `docker-compose.yml`:
  ```
  POSTGRES_PASSWORD=supersecret
  SECRET_KEY=abc123
  ```
- В `docker-compose.yml`:
  ```yaml
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  ```
- `.gitignore` — `.env` ВСЕГДА в игноре
- `.env.example` — шаблон без значений, коммитится в git
- `env_file:` директива — передать весь файл в контейнер
- Проверка: `docker-compose config` — показывает финальный конфиг с подставленными переменными
- **Упражнения:** вынести все секреты в `.env`, убедиться что `docker-compose config` не показывает их в образе

> **Опасно:** `.env` файл должен быть в `.gitignore` с первого коммита. Один случайный push — и секреты навсегда в истории git.

---

### Часть 4: Продакшн и практика (Главы 8-9)

#### Глава 8: Nginx в Docker и полный стек

**Цель:** читатель добавляет Nginx в docker-compose и получает рабочий HTTPS-стек.

- Nginx как отдельный сервис в compose:
  ```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - app
    networks:
      - backend
      - frontend
  ```
- Конфиг Nginx для proxy_pass к контейнеру app:
  ```nginx
  upstream app {
    server app:8000;  # имя сервиса из compose
  }
  ```
- Две сети: `frontend` (nginx ↔ интернет) и `backend` (nginx ↔ app ↔ db)
  ```
  Интернет → [nginx] → [app] → [db]
              frontend   backend  backend
  ```
- SSL-сертификаты: как пробросить certbot-сертификаты из хоста в контейнер через bind mount
- Альтернатива: Nginx Proxy Manager или Traefik — упомянуть, не объяснять
- Restart policy: `restart: unless-stopped` — контейнер поднимается после ребута сервера
- **Упражнения:** добавить Nginx в docker-compose, проверить что db не доступна снаружи, но app работает через HTTPS

#### Глава 9: Итоговый проект

**Цель:** самостоятельно собрать полный стек с нуля по чеклисту.

Что нужно сделать:
1. Написать `Dockerfile` для Python-приложения
2. Написать `docker-compose.yml` с app + db + nginx
3. Вынести все секреты в `.env`
4. Настроить `healthcheck` для базы данных
5. Настроить тома для данных PostgreSQL
6. Настроить Nginx как reverse proxy
7. Проверить `restart: unless-stopped`
8. Написать Makefile или shell-скрипт для типичных операций:
   ```makefile
   up:     docker-compose up -d
   down:   docker-compose down
   build:  docker-compose build
   logs:   docker-compose logs -f app
   shell:  docker-compose exec app bash
   ```

**Чеклист готовности:**
- [ ] `docker-compose up -d` — всё поднимается без ошибок
- [ ] `docker-compose ps` — все сервисы `Up (healthy)`
- [ ] Приложение доступно через браузер
- [ ] `docker-compose down && docker-compose up -d` — данные в базе сохранились
- [ ] После `reboot` сервера — всё поднялось само
- [ ] `.env` нет в git
- [ ] `docker images` — образ приложения не тяжелее 200МБ

---

### Приложения

#### Приложение A: Шпаргалка команд
Таблица: команда → назначение → пример

#### Приложение B: Готовые шаблоны
- Dockerfile для Python/FastAPI
- Dockerfile для Python/Django
- `docker-compose.yml`: app + PostgreSQL
- `docker-compose.yml`: app + PostgreSQL + Nginx
- `.dockerignore` шаблон
- `.env.example` шаблон

#### Приложение C: Диагностика
- Контейнер не стартует → `docker logs`, `docker inspect`
- Не могу достучаться до db → `docker network inspect`, имена сервисов
- Образ слишком большой → `docker history myapp`, многоэтапная сборка
- `docker-compose up` зависает → `depends_on` + `healthcheck`
- Порт уже занят → `docker ps -a`, удалить старый контейнер

---

## Принципы написания

Все принципы Модулей 1 и 2, плюс специфичные для Docker:

### 1. Одна инструкция Dockerfile — одно объяснение
Не давай Dockerfile целиком без разбора.
Каждую инструкцию объясняй:
- **Что делает**
- **Зачем** именно здесь
- **Что будет если убрать**

### 2. Порядок слоёв важен — объясняй каждый раз
Кэш Docker — самая частая причина непонимания.
После любого Dockerfile с `COPY` + `RUN pip install` объясняй:
> "Если поменять строку кода, Docker пересборет только с `COPY . .`.
> Если поменять `requirements.txt`, пересберёт с `pip install`.
> Именно поэтому `requirements.txt` идёт раньше остального кода."

### 3. ASCII-схемы обязательны
Особенно важны для:
- Архитектуры стека (кто с кем общается)
- Слоёв образа
- Сетей Docker
- Потока данных запроса

### 4. Показывай что происходит при сломанной конфигурации
Docker даёт неочевидные сообщения об ошибках.
После каждого важного паттерна показывай:
- Как выглядит правильный вывод
- Как выглядит неправильный вывод
- Как читать `docker logs` и `docker inspect`

### 5. Контейнер ≠ виртуалка — повторяй при каждом удобном случае
Новички постоянно пытаются "зайти в контейнер и что-то настроить".
Формируй правильную ментальную модель:
- Конфигурация — в Dockerfile или volume
- Изменения внутри запущенного контейнера — временные
- Правильный путь: изменил Dockerfile → пересобрал образ → поднял новый контейнер

### 6. Никакой воды
- Без истории Docker и Solomon Hykes
- Без сравнения Docker с Podman и containerd
- Без Kubernetes (это другой курс)
- Без multi-stage builds в основном тексте (только упомянуть в приложении)
- Без Docker Swarm

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS.md                    # Модуль 1
├── AGENT-INSTRUCTIONS-module-02.md          # Модуль 2
├── AGENT-INSTRUCTIONS-module-03.md          # Этот файл
├── linux-for-devops/                        # Книга 1
├── nginx-https-devops/                      # Книга 2
└── docker-devops/                           # Книга 3 (создать)
    ├── book.md                              # Оглавление
    ├── chapter-00.md
    ├── chapter-01.md
    └── ...
```

### Форматирование
- Markdown
- `#` — название главы, `##` — раздел, `###` — подраздел
- Код в блоках с языком: ` ```bash `, ` ```dockerfile `, ` ```yaml `, ` ```nginx `
- ASCII-схемы в блоках ` ```text ` или ` ``` `
- Таблицы для сравнений и справочной информации

### Объём
- Каждая глава: 15-20 страниц
- Примеры: минимум 3 на концепцию
- Упражнения: 3-5 на главу

---

## Проверка качества

Перед сдачей каждой главы проверь:

1. **Понятность:** поймёт ли человек, который видит Docker первый раз?
2. **Практичность:** можно ли сразу применить на реальном проекте?
3. **Модель мышления:** формирует ли глава правильное понимание (контейнер ≠ виртуалка)?
4. **Безопасность:** есть ли предупреждения про секреты в образах и `down -v`?
5. **Схемы:** есть ли ASCII-диаграмма для архитектуры?
6. **Упражнения:** проверяют ли они понимание, а не просто копирование команд?
7. **Без воды:** нет ли теории ради теории?

---

## Что НЕ надо делать

- ❌ Не объяснять Kubernetes, Docker Swarm, Podman
- ❌ Не делать multi-stage builds основной темой (только упомянуть)
- ❌ Не объяснять CI/CD — это Модуль 4
- ❌ Не сравнивать Docker с другими инструментами контейнеризации
- ❌ Не давать Dockerfile без объяснения каждой строки
- ❌ Не показывать `docker run` с 10 флагами без docker-compose.yml
- ❌ Не хардкодить пароли в примерах кода (формируй привычку с первой страницы)
- ❌ Не предполагать что читатель знает YAML (объяснить синтаксис при первом use)
- ❌ Не писать `FROM ubuntu` там где нужен `FROM python:3.12-slim`

---

## Связь с другими модулями

**Что нужно из Модуля 1:**
- `systemctl` — для управления Docker-демоном
- Права пользователей — добавить себя в группу `docker`
- Файловая система — понять где Docker хранит данные (`/var/lib/docker`)

**Что нужно из Модуля 2:**
- Nginx как reverse proxy — теперь он будет в контейнере
- Порты и проброс — `docker run -p 80:80` — та же логика
- ufw — Docker сам открывает порты в iptables, обходя ufw (важный нюанс!)

**Что даёт Модулю 4 (CI/CD):**
- `docker build` + `docker push` — то что GitHub Actions будет делать автоматически
- Образы с тегами версий — CI будет тегировать по git commit/tag
- `docker-compose.yml` на сервере — CD будет его обновлять

---

## Важный нюанс: Docker и ufw

Docker по умолчанию **обходит** правила ufw через iptables.
Если открыть порт в `docker-compose.yml` — он будет доступен снаружи, **даже если ufw deny**.

Это нужно объяснить в главе про сети (глава 5) и напомнить в главе про Nginx (глава 8).

Решение: не пробрасывать порты базы данных наружу (не писать `ports:` для db-сервиса).
Правило: `ports:` только для сервисов которые должны быть доступны снаружи.

---

## План работы

1. **book.md** — оглавление книги 3
2. **chapter-00.md** — зачем Docker, установка
3. **chapter-01.md** — первый контейнер
4. И так далее по одной главе

**Не пиши всю книгу сразу.** Пиши по одной главе, проверяй, получай обратную связь.

---

*Эта инструкция — для ИИ-агента, который будет писать третью книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Смотри Модуль 2: /home/adelfos/Documents/lessons/dev-ops/docs/books/AGENT-INSTRUCTIONS-module-02.md*
