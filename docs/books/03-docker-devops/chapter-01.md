# Глава 1: Первый контейнер

> **Запомни:** Контейнер — это запущенный процесс. Остановил процесс — контейнер остановлен. Данные внутри контейнера исчезают при удалении.

---

## 1.1 `docker run` — анатомия команды

`docker run` — главная команда Docker. Она делает сразу всё:

1. Скачивает образ (если нет локально)
2. Создаёт контейнер
3. Запускает его

```bash
docker run ubuntu echo "Hello from Docker!"
```

Что произошло:

```
1. Docker не нашёл образ ubuntu локально
2. Скачал его с Docker Hub
3. Создал контейнер из образа
4. Запустил внутри: echo "Hello from Docker!"
5. Команда завершилась → контейнер остановился
```

### Разбор

```bash
docker run ubuntu echo "Hello from Docker!"
└──┬──┘ └─┬──┘ └──────┬──────┘
   │       │           │
   │       │           Команда внутри контейнера
   │       Образ (image)
   Команда Docker
```

---

## 1.2 Интерактивный режим: `-it`

Обычный `docker run` запускает и сразу выходит.
Чтобы **работать** внутри контейнера — нужен интерактивный режим.

```bash
docker run -it ubuntu bash
```

```
root@abc12345678:/#
```

Ты внутри Ubuntu! Но это не полноценная система — только базовые утилиты.

```bash
root@abc12345678:/# ls
bin  boot  dev  etc  home  lib  ...
root@abc12345678:/# cat /etc/os-release
PRETTY_NAME="Ubuntu 24.04 LTS"
...
root@abc12345678:/# exit
```

`exit` — выйти из контейнера. Контейнер остановится.

### Что значит `-it`

```bash
-it = -i + -t
```

| Флаг | Что делает |
|------|-----------|
| `-i` (interactive) | Держит stdin открытым (ты можешь вводить команды) |
| `-t` (tty) | Выделяет псевдо-терминал (ты видишь вывод) |

Вместе = полноценный терминал внутри контейнера.

> **Запомни:** `-it` нужен когда хочешь работать внутри контейнера.
> Без `-it` — только одна команда и выход.

---

## 1.3 Запуск в фоне: `-d`

`-d` = **d**etach (отсоединиться).

Контейнер работает в фоне. Терминал свободен.

```bash
docker run -d nginx
a1b2c3d4e5f6...
```

Nginx работает в фоне. Ты можешь делать другие дела.

```bash
docker ps
CONTAINER ID   IMAGE   STATUS          NAMES
a1b2c3d4e5f6   nginx   Up 30 seconds   nervous_brown
```

Чтобы остановить:

```bash
docker stop a1b2c3d4e5f6
```

> **Запомни:** `-d` для сервисов которые должны работать постоянно.
> `-it` для отладки и ручной работы внутри.

---

## 1.4 Имя контейнера: `--name`

Docker даёт контейнерам случайные имена:

```bash
docker run -d nginx
# nervous_brown, happy_einstein, determined_yonath...
```

Удобнее дать своё имя:

```bash
docker run -d --name my-nginx nginx
```

Теперь:

```bash
docker stop my-nginx
docker start my-nginx
docker logs my-nginx
```

Вместо запоминания `a1b2c3d4e5f6`.

> **Совет:** Всегда используй `--name` для сервисов.
> Для одноразовых контейнеров — не нужно.

---

## 1.5 Проброс портов: `-p`

По умолчанию контейнер **изолирован** от внешнего мира.
Nginx внутри контейнера слушает порт 80 — но снаружи его не видно.

```bash
docker run -d --name my-nginx nginx
curl http://localhost
# Connection refused — порт не проброшен!
```

**`-p`** пробрасывает порт с хоста в контейнер:

```bash
docker run -d --name my-nginx -p 8080:80 nginx
```

```
-p 8080:80
   └─┬─┘ └┬┘
     │    │
     │    Порт внутри контейнера (Nginx слушает 80)
     Порт на хосте (ты обращаешься к 8080)
```

Теперь:

```bash
curl http://localhost:8080
```

Запрос идёт по пути:

```
Браузер → localhost:8080 → Docker → контейнер:80 → Nginx → ответ обратно
```

### Несколько портов

```bash
docker run -d --name myapp -p 80:80 -p 443:443 nginx
```

### Только для localhost

```bash
docker run -d --name myapp -p 127.0.0.1:8000:8000 myapp
```

Только с локальной машины. Не из сети.

> **Запомни:** `-p 8080:80` = "то что в контейнере на 80, доступно на хосте через 8080".
> Левое число — хост. Правое — контейнер.

---

## 1.6 Автоудаление: `--rm`

После остановки контейнер остаётся в системе:

```bash
docker run --name temp ubuntu echo "done"
docker ps -a  # виден остановленный контейнер
```

`--rm` удаляет контейнер сразу после остановки:

```bash
docker run --rm --name temp ubuntu echo "done"
docker ps -a  # контейнера нет
```

> **Совет:** Используй `--rm` для одноразовых контейнеров (тесты, отладка).
> Не используй для сервисов — их нужно перезапускать.

---

## 1.7 Жизненный цикл контейнера

```
                   docker create
                        │
                        ▼
                    ┌────────┐
                    │Created │  ← Контейнер создан, не запущен
                    └───┬────┘
                        │ docker start
                        ▼
                    ┌──────────┐
        docker stop │ Running  │ docker pause
          ┌─────────┤          ├─────────┐
          ▼         └───┬──────┘         ▼
    ┌───────────┐       │          ┌──────────┐
    │  Exited   │       │          │  Paused  │
    │ (stopped) │       │          └────┬─────┘
    └─────┬─────┘       │               │
          │             │ docker unpause │
          │ docker start│               │
          ▼             ▼               ▼
    ┌────────────────────────┐
    │       Running          │
    └────────────┬───────────┘
                 │ docker rm
                 ▼
           Удалён навсегда
```

### Основные состояния

| Состояние | Что значит | Команда |
|-----------|-----------|---------|
| Created | Создан, не запущен | `docker create` |
| Running | Работает | `docker start` |
| Exited | Остановлен | `docker stop` |
| Paused | Приостановлен (заморожен) | `docker pause` |
| Removed | Удалён | `docker rm` |

> **Запомни:** `docker stop` ≠ `docker rm`.
> `stop` — остановил (можно запустить снова).
> `rm` — удалил (нельзя вернуть).

---

## 1.8 `docker ps` — посмотреть контейнеры

### Запущенные

```bash
docker ps
CONTAINER ID   IMAGE   COMMAND   STATUS         PORTS     NAMES
a1b2c3d4e5f6   nginx   "nginx…"  Up 5 minutes   0.0.0.0:8080->80/tcp   my-nginx
```

| Колонка | Значение |
|---------|----------|
| `CONTAINER ID` | Уникальный ID (короткий) |
| `IMAGE` | Из какого образа |
| `COMMAND` | Что запускает |
| `STATUS` | Сколько работает |
| `PORTS` | Проброшенные порты |
| `NAMES` | Имя контейнера |

### Все контейнеры (включая остановленные)

```bash
docker ps -a
CONTAINER ID   IMAGE    COMMAND    STATUS                      NAMES
a1b2c3d4e5f6   nginx    "nginx…"   Up 5 minutes                my-nginx
b2c3d4e5f6g7   ubuntu   "bash"     Exited (0) 2 minutes ago    temp
```

`Exited (0)` — вышел нормально (код 0).
`Exited (1)` — вышел с ошибкой.

### Только ID

```bash
docker ps -q
a1b2c3d4e5f6
```

Удобно для скриптов.

---

## 1.9 Управление контейнерами

### Остановить

```bash
docker stop my-nginx
```

Отправляет SIGTERM → ждёт 10 сек → SIGKILL.
Контейнер может корректно закрыться.

### Запустить снова

```bash
docker start my-nginx
```

Тот же контейнер, те же данные, тот же IP.

### Перезапустить

```bash
docker restart my-nginx
```

То же что `stop` + `start`.

### Удалить

```bash
docker rm my-nginx
```

Только остановленный контейнер. Если работает — сначала `stop`.

Или принудительно:

```bash
docker rm -f my-nginx
```

### Удалить все остановленные

```bash
docker container prune
```

---

## 1.10 Логи контейнера

```bash
docker logs my-nginx
```

Показывает stdout и stderr контейнера.

### Следить в реальном времени

```bash
docker logs -f my-nginx
```

`-f` = follow. Как `tail -f`.

### Последние N строк

```bash
docker logs --tail 50 my-nginx
```

### С временными метками

```bash
docker logs --timestamps my-nginx
```

> **Запомни:** `docker logs` — первое что делаешь когда контейнер "не работает".
> Там почти всегда причина.

---

## 1.11 Зайти в запущенный контейнер: `docker exec`

```bash
docker exec -it my-nginx bash
```

Ты внутри **работающего** контейнера.

```bash
root@a1b2c3d4e5f6:/# ls /etc/nginx
conf.d  fastcgi_params  mime.types  ...
root@a1b2c3d4e5f6:/# exit
```

Контейнер продолжает работать. Ты просто подключился к нему.

### Выполнить одну команду

```bash
docker exec my-nginx ls /etc/nginx
```

### Запустить конкретную команду

```bash
docker exec my-nginx nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
```

> **Запомни:** `docker exec` = подключиться к работающему контейнеру.
> `docker run` = создать новый контейнер.
> Не путай.

### Когда `bash` нет

Некоторые образы (alpine) не имеют bash:

```bash
docker exec -it my-alpine sh
```

`sh` вместо `bash`.

---

## 1.12 Сводная таблица `docker run` флагов

| Флаг | Что делает | Пример |
|------|-----------|--------|
| `-d` | В фоне | `docker run -d nginx` |
| `-it` | Интерактивный | `docker run -it ubuntu bash` |
| `--name` | Имя | `docker run --name myapp nginx` |
| `-p host:container` | Проброс порта | `docker run -p 8080:80 nginx` |
| `--rm` | Удалить после остановки | `docker run --rm ubuntu echo hi` |
| `-e VAR=val` | Переменная окружения | `docker run -e DB_HOST=db myapp` |
| `-v vol:path` | Том | `docker run -v pgdata:/var/lib/postgresql postgres` |

---

## 📝 Упражнения

### Упражнение 1.1: Первый контейнер
**Задача:**
1. Запусти: `docker run ubuntu echo "Hello DevOps!"`
2. Что вывелось?
3. Запусти: `docker run hello-world`
4. Что произошло?

### Упражнение 1.2: Интерактивный режим
**Задача:**
1. Зайди в Ubuntu: `docker run -it ubuntu bash`
2. Внутри контейнера:
   - `cat /etc/os-release` — какая версия?
   - `ls /` — что есть?
   - `which python` — есть Python?
3. Выйди: `exit`
4. Контейнер остановился? Проверь: `docker ps -a`

### Упражнение 1.3: Nginx в фоне
**Задача:**
1. Запусти Nginx: `docker run -d --name web -p 8080:80 nginx`
2. Проверь: `docker ps` — статус?
3. Открой браузер: `http://localhost:8080` — видишь "Welcome to nginx!"?
4. Или curl: `curl -I http://localhost:8080`
5. Посмотри логи: `docker logs web`
6. Останови: `docker stop web`
7. Запусти снова: `docker start web`
8. Проверь что работает: `curl -I http://localhost:8080`

### Упражнение 1.4: exec и logs
**Задача:**
1. Убедись что Nginx работает: `docker ps`
2. Зайди внутрь: `docker exec -it web bash`
3. Внутри: `ls /usr/share/nginx/html/` — где страницы?
4. Внутри: `cat /usr/share/nginx/html/index.html` — что там?
5. Выйди: `exit`
6. Проверь конфиг Nginx: `docker exec web nginx -t`
7. Посмотри логи: `docker logs -f web` — открой сайт в браузере, увидишь запрос

### Упражнение 1.5: Жизненный цикл
**Задача:**
1. Создай но не запускай: `docker create --name test ubuntu echo "test"`
2. `docker ps -a` — какой статус?
3. Запусти: `docker start test`
4. `docker ps -a` — какой статус теперь?
5. Подожди — контейнер завершится
6. `docker ps -a` — какой статус?
7. Удали: `docker rm test`
8. `docker ps -a` — контейнер исчез?

---

## 📋 Чеклист главы 1

- [ ] Я понимаю что `docker run` = скачать + создать + запустить
- [ ] Я могу запустить контейнер в интерактивном режиме (`-it`)
- [ ] Я могу запустить контейнер в фоне (`-d`)
- [ ] Я могу дать контейнеру имя (`--name`)
- [ ] Я могу пробросить порт (`-p host:container`)
- [ ] Я понимаю жизненный цикл (created → running → exited → removed)
- [ ] Я могу посмотреть контейнеры (`docker ps`, `docker ps -a`)
- [ ] Я могу остановить, запустить, удалить контейнер
- [ ] Я могу посмотреть логи (`docker logs`, `docker logs -f`)
- [ ] Я могу зайти внутрь работающего контейнера (`docker exec -it`)
- [ ] Я понимаю разницу между `docker run` и `docker exec`

**Всё отметил?** Переходи к Главе 2 — образы.
