# Глава 9: Systemd и Podman — контейнеры как сервисы

## Что вы узнаете

- как запустить контейнер как системный сервис с автостартом;
- что такое Quadlet и почему он лучше `podman generate systemd`;
- как настроить rootless автозапуск без входа в систему;
- как обновлять сервис без написания shell-скриптов.

---

## Зачем интегрировать Podman с systemd

После того как контейнер запущен вручную — возникают очевидные вопросы:

- Что будет с ним после перезагрузки сервера?
- Как его перезапустить если он упал?
- Где смотреть логи?
- Как обновить образ и перезапустить сервис?

На Linux-серверах всё это — задача **systemd**. Podman интегрируется с systemd через два механизма: устаревающий `podman generate systemd` и современный **Quadlet**.

---

## podman generate systemd — классический способ

Исторически первый способ: сначала запустить контейнер, потом сгенерировать unit-файл на его основе.

```bash
# Шаг 1: запустить контейнер
podman run -d \
  --name nginx-web \
  -p 8080:80 \
  -v /home/user/html:/usr/share/nginx/html:ro \
  nginx:alpine

# Шаг 2: сгенерировать systemd unit
# Флаг --new важен: при старте сервиса контейнер будет создан заново,
# а не просто запущен существующий
podman generate systemd \
  --new \
  --name nginx-web \
  --files \
  --output ~/.config/systemd/user/

# Флаг --files — сохранить в файлы вместо вывода в stdout
# Создаст: container-nginx-web.service

# Шаг 3: зарегистрировать в systemd
systemctl --user daemon-reload
systemctl --user enable --now container-nginx-web.service

# Проверить
systemctl --user status container-nginx-web.service
```

### Проблемы `podman generate systemd`

1. **Устаревает.** В Podman 5.x помечен как deprecated, в будущих версиях будет удалён.
2. **Порядок операций.** Нужно сначала создать контейнер, потом генерировать — неудобно для декларативной конфигурации.
3. **Обновление образа.** Чтобы обновить образ — нужно заново пройти весь цикл.
4. **Хрупкость.** Сгенерированный unit жёстко привязан к именам контейнеров и томов которые существовали в момент генерации.

**Рекомендация:** для новых систем используйте Quadlet. `generate systemd` оставьте для случаев когда нужна совместимость со старым Podman (< 4.4).

---

## Quadlet — декларативный подход (Podman 4.4+)

**Quadlet** — генератор systemd unit-файлов из простых декларативных конфигов. Вместо того чтобы генерировать unit из запущенного контейнера, вы описываете желаемое состояние — и systemd сам управляет жизненным циклом.

Quadlet понимает несколько типов файлов:

| Расширение | Что описывает |
|---|---|
| `.container` | Один контейнер |
| `.pod` | Podman Pod |
| `.volume` | Named volume |
| `.network` | Podman network |
| `.image` | Автозагрузка образа |
| `.kube` | Запуск K8s YAML |

Файлы `.container` кладут в одно из мест:
- `~/.config/containers/systemd/` — пользовательские (rootless)
- `/etc/containers/systemd/` — системные (root)

Ключевое отличие от `generate systemd`: вы не пишете unit-файл руками. При `daemon-reload` генератор Quadlet превращает декларативный `.container` в обычный `.service`, которым дальше управляет systemd.

```mermaid
flowchart LR
    quadlet["nginx-web.container\n(декларативный конфиг)"]
    reload(["systemctl --user\ndaemon-reload"])
    gen["генератор Quadlet"]
    unit["nginx-web.service\n(сгенерирован)"]
    sd["systemd"]
    cont["контейнер nginx\n(через podman)"]
    quadlet --> reload --> gen --> unit --> sd
    sd -->|"start / restart"| cont
    style quadlet fill:#2d2d2d,color:#fff
    style gen fill:#4a235a,color:#fff
    style sd fill:#1a5276,color:#fff
    style cont fill:#1e8449,color:#fff
```

Именно поэтому после правки `.container` обязателен `daemon-reload`: без него генератор не перечитает конфиг и `.service` останется старым.

---

## Первый Quadlet: контейнер nginx

```bash
# Создать директорию для конфигов
mkdir -p ~/.config/containers/systemd/

# Создать .container файл
cat > ~/.config/containers/systemd/nginx-web.container << 'EOF'
[Unit]
Description=Nginx web server
After=network-online.target

[Container]
Image=docker.io/library/nginx:alpine
PublishPort=8080:80
Volume=%h/html:/usr/share/nginx/html:ro
Environment=NGINX_ENVSUBST_TEMPLATE_SUFFIX=.tmpl

[Service]
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
```

Применить:
```bash
# После создания или изменения .container файла — обязательно:
systemctl --user daemon-reload

# Теперь существует сервис nginx-web.service
systemctl --user start nginx-web.service

# Проверить
systemctl --user status nginx-web.service
# ● nginx-web.service - Nginx web server
#    Loaded: loaded (/home/user/.config/containers/systemd/nginx-web.container)
#    Active: active (running) since ...

# Логи
journalctl --user -u nginx-web.service -f

# Проверить работу
curl http://localhost:8080
```

---

## Синтаксис Quadlet .container

Разберём все секции подробнее.

### Секция [Container]

```ini
[Container]
# Образ (обязательно, полный путь рекомендуется)
Image=docker.io/library/nginx:alpine

# Порты: hostPort:containerPort
PublishPort=8080:80
PublishPort=8443:443

# Тома
Volume=/host/path:/container/path:ro,z
Volume=myvolume:/data

# Переменные окружения
Environment=KEY=value
Environment=ANOTHER_KEY=another_value

# Файл с переменными
EnvironmentFile=/etc/myapp/env

# Имя контейнера (по умолчанию: имя файла без .container)
ContainerName=my-nginx

# Запуск от имени пользователя (rootless: от текущего, rootful: можно задать)
User=1000

# Сеть
Network=mynetwork.network   # ссылка на .network файл
Network=host                 # или host/bridge/etc

# Метки
Label=app.version=1.0
Label=app.environment=production

# Capabilities
AddCapability=NET_BIND_SERVICE
DropCapability=ALL

# Автообновление (подробнее ниже)
AutoUpdate=registry
```

### Секция [Unit]

Стандартная systemd секция [Unit]. Полезные параметры:

```ini
[Unit]
Description=Мой сервис
# Запускать после сети:
After=network-online.target
# Если есть зависимость от другого контейнера:
After=postgres-db.service
Requires=postgres-db.service
```

### Секция [Service]

```ini
[Service]
# Политика перезапуска
Restart=always          # всегда перезапускать
# Restart=on-failure  # только при ошибке
# Restart=no          # никогда

# Пауза перед перезапуском
RestartSec=10

# Таймаут запуска
TimeoutStartSec=60

# Переменные окружения для самого systemd (не контейнера)
Environment=PODMAN_SYSTEMD_UNIT=%n
```

### Секция [Install]

```ini
[Install]
# Для пользовательских сервисов (rootless):
WantedBy=default.target

# Для системных сервисов:
# WantedBy=multi-user.target
```

---

## Зависимости между сервисами

Если приложению нужна БД — правильно это описать в Quadlet:

```bash
# Создать сервис для PostgreSQL
cat > ~/.config/containers/systemd/postgres-db.container << 'EOF'
[Unit]
Description=PostgreSQL database

[Container]
Image=docker.io/library/postgres:16-alpine
Environment=POSTGRES_PASSWORD=secret
Environment=POSTGRES_DB=myapp
Environment=POSTGRES_USER=myapp
Volume=pgdata.volume:/var/lib/postgresql/data

[Service]
Restart=always

[Install]
WantedBy=default.target
EOF

# Создать том для данных
cat > ~/.config/containers/systemd/pgdata.volume << 'EOF'
[Volume]
# Имя volume создаётся автоматически из имени файла: pgdata
EOF

# Создать сервис для приложения
cat > ~/.config/containers/systemd/myapp.container << 'EOF'
[Unit]
Description=My Application
After=postgres-db.service
Requires=postgres-db.service

[Container]
Image=registry.example.com/myapp:latest
Environment=DATABASE_URL=postgresql://myapp:secret@localhost:5432/myapp
PublishPort=8000:8000
Network=host

[Service]
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Применить всё
systemctl --user daemon-reload
systemctl --user enable --now postgres-db.service myapp.service

# Проверить порядок запуска
systemctl --user list-dependencies myapp.service
```

---

## Pod через Quadlet

Для запуска нескольких контейнеров как единого Pod:

```bash
# Описать Pod
cat > ~/.config/containers/systemd/webapp.pod << 'EOF'
[Unit]
Description=Web Application Pod

[Pod]
PublishPort=8080:80
PublishPort=8000:8000

[Install]
WantedBy=default.target
EOF

# Контейнеры в Pod
cat > ~/.config/containers/systemd/webapp-nginx.container << 'EOF'
[Unit]
Description=Nginx in webapp pod
After=webapp-pod.service
BindsTo=webapp-pod.service

[Container]
Image=nginx:alpine
Pod=webapp.pod

[Service]
Restart=always
EOF

cat > ~/.config/containers/systemd/webapp-api.container << 'EOF'
[Unit]
Description=API in webapp pod
After=webapp-pod.service
BindsTo=webapp-pod.service

[Container]
Image=registry.example.com/myapp:latest
Pod=webapp.pod
Environment=API_PORT=8000

[Service]
Restart=on-failure
EOF

systemctl --user daemon-reload
systemctl --user start webapp-pod.service
```

---

## Автозапуск без логина: loginctl enable-linger

По умолчанию пользовательские systemd-сервисы запускаются только когда пользователь залогинен. После выхода из SSH — сервисы останавливаются.

Чтобы сервисы работали всегда — нужен **linger**:

```bash
# Включить linger для текущего пользователя
sudo loginctl enable-linger $USER

# Или для другого пользователя:
sudo loginctl enable-linger deploy-user

# Проверить
loginctl show-user $USER | grep Linger
# Linger=yes

# Теперь сервисы запустятся при загрузке без логина
# Проверить после перезагрузки:
systemctl --user is-active nginx-web.service
```

### Что происходит без linger

```text
Без linger:
  Загрузка → пользователь не залогинен → user@UID.service не запущен
  → контейнеры не запускаются

С linger:
  Загрузка → systemd запускает user@UID.service для пользователя
  → Quadlet-сервисы запускаются автоматически
  → Контейнеры работают даже без активного сеанса
```

---

## Обновление образа

### Вручную

```bash
# 1. Скачать новый образ
podman pull registry.example.com/myapp:latest

# 2. Перезапустить сервис (Quadlet пересоздаст контейнер с новым образом)
systemctl --user restart myapp.service

# 3. Проверить что работает
systemctl --user status myapp.service
curl http://localhost:8000/health
```

### Автообновление через AutoUpdate

Quadlet поддерживает автоматическое обновление образов:

```ini
[Container]
Image=registry.example.com/myapp:latest
AutoUpdate=registry  # ← проверять обновления в реестре
```

```bash
# Включить systemd таймер для проверки обновлений
systemctl --user enable --now podman-auto-update.timer

# Принудительная проверка:
podman auto-update

# Посмотреть что обновится:
podman auto-update --dry-run
```

> **Как работает AutoUpdate:** Podman сравнивает digest образа в реестре с локальным. Если отличается — скачивает новый и перезапускает сервис через systemd. Сервис brief downtime во время перезапуска.

---

## Команды и диагностика

```bash
# Управление сервисом
systemctl --user start nginx-web.service
systemctl --user stop nginx-web.service
systemctl --user restart nginx-web.service
systemctl --user reload nginx-web.service    # reload config без перезапуска (если поддерживается)

# Включить/выключить автозапуск
systemctl --user enable nginx-web.service
systemctl --user disable nginx-web.service

# Статус
systemctl --user status nginx-web.service
systemctl --user is-active nginx-web.service
systemctl --user is-enabled nginx-web.service

# Логи
journalctl --user -u nginx-web.service          # все логи
journalctl --user -u nginx-web.service -f       # следить в реальном времени
journalctl --user -u nginx-web.service --since "1 hour ago"
journalctl --user -u nginx-web.service -n 50    # последние 50 строк

# Применить изменения в .container файле
systemctl --user daemon-reload
systemctl --user restart nginx-web.service

# Список всех пользовательских сервисов
systemctl --user list-units --type=service
```

---

## Типичные ошибки

**Quadlet игнорирует `.container` файл после создания**
Забыли выполнить `systemctl --user daemon-reload`. Без этого systemd не знает о новых файлах.

**`Failed to connect to bus: No such file or directory`**
XDG_RUNTIME_DIR не установлен. Исправление:
```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
```

**Сервис останавливается при выходе из SSH**
Не включён linger: `sudo loginctl enable-linger $USER`.

**Файл `.container` создан, `daemon-reload` выполнен, но сервис не появился**
Неправильное имя файла или расположение. Проверить:
```bash
ls ~/.config/containers/systemd/*.container   # должны быть там
systemctl --user daemon-reload
systemctl --user list-units '*nginx*'          # найти сервис
```

**Quadlet не видит Volume из `.volume` файла**
Том должен быть в том же каталоге что и `.container`. Имя тома в `Volume=` должно совпадать с именем файла без `.volume`.

**AutoUpdate не работает**
Нужно включить таймер:
```bash
systemctl --user enable --now podman-auto-update.timer
systemctl --user status podman-auto-update.timer
```

---

## Чек-лист для самопроверки

- [ ] Создал `.container` файл и запустил его через `systemctl --user start`
- [ ] Проверил логи контейнера через `journalctl --user -u <service>`
- [ ] Включил `loginctl enable-linger` и убедился что сервис работает без активного сеанса
- [ ] Понимаю разницу между `podman generate systemd` (устаревает) и Quadlet (современный)
- [ ] После изменения `.container` файла выполнил `daemon-reload` перед перезапуском

## Попробуйте сами

1. Создайте Quadlet-сервис для nginx и проверьте полный жизненный цикл:
   ```bash
   mkdir -p ~/.config/containers/systemd/
   # Создать nginx-web.container (пример в начале главы)
   systemctl --user daemon-reload
   systemctl --user start nginx-web.service
   curl http://localhost:8080
   # Изменить PublishPort на 9090 в .container файле
   systemctl --user daemon-reload
   systemctl --user restart nginx-web.service
   curl http://localhost:9090
   systemctl --user stop nginx-web.service
   ```

2. Включите linger и проверьте автозапуск:
   ```bash
   sudo loginctl enable-linger $USER
   systemctl --user enable nginx-web.service
   sudo reboot
   # После перезагрузки (без логина):
   # ssh user@host
   systemctl --user status nginx-web.service
   # Должно быть active (running)
   ```

3. Создайте два связанных сервиса (PostgreSQL и приложение) с зависимостью `After=` и `Requires=`. Убедитесь что приложение стартует только после того как PostgreSQL готов.
