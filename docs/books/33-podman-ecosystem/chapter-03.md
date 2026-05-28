# Глава 3: Установка и первые шаги с Podman

## Что вы узнаете

- как установить Podman на Ubuntu/Debian и RHEL/Fedora;
- как проверить что rootless работает корректно;
- где Podman хранит образы и чем это отличается от Docker;
- какие конфигурационные файлы за что отвечают.

---

## Установка

### Ubuntu 22.04 / Debian 12

```bash
sudo apt update
sudo apt install -y podman

# Проверить версию
podman --version
# podman version 4.6.2
```

> **Примечание:** В Ubuntu 22.04 из стандартных репозиториев может поставиться Podman 3.x. Для Podman 4.x+ (с поддержкой Quadlet) добавьте репозиторий kubic:
>
> ```bash
> # Kubic репозиторий для свежего Podman на Debian/Ubuntu
> source /etc/os-release
> echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/unstable/xUbuntu_${VERSION_ID}/ /" \
>   | sudo tee /etc/apt/sources.list.d/devel-kubic-libcontainers-unstable.list
> curl -fsSL "https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/unstable/xUbuntu_${VERSION_ID}/Release.key" \
>   | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/devel-kubic-libcontainers-unstable.gpg
> sudo apt update && sudo apt install -y podman
> ```

### Fedora / RHEL 9 / AlmaLinux / Rocky Linux

```bash
sudo dnf install -y podman

podman --version
# podman version 5.x.x
```

На RHEL/Fedora Podman уже предустановлен в последних версиях и является рекомендованным инструментом вместо Docker.

### Проверить установку

```bash
# Полная информация о системе Podman
podman info
```

Ключевые строки в выводе:
```yaml
host:
  security:
    rootless: true          # ← должно быть true
    selinuxEnabled: false   # зависит от дистрибутива
store:
  graphDriverName: overlay  # файловая система для слоёв
  graphRoot: /home/user/.local/share/containers/storage  # ← не /var/lib/docker
```

---

## Первый запуск

```bash
# Запустить контейнер без sudo
podman run --rm hello-world
```

Если вы видите «Hello from Docker!» (или аналог от Podman) — установка прошла успешно, rootless работает.

```bash
# Интерактивный контейнер
podman run -it --rm alpine sh

# Внутри контейнера:
/ # id
uid=0(root) gid=0(root) groups=0(root)   # root внутри...

/ # exit

# ...но не снаружи. Пока контейнер работал:
ps aux | grep sleep
# user   12345  ...   sleep   ← UID текущего пользователя, не 0
```

Это rootless в действии: `id` внутри показывает root, но на хосте процесс запускается от вашего пользователя.

---

## Где хранятся образы

Docker хранит всё в `/var/lib/docker` — общем месте для всей системы. Podman в rootless-режиме хранит образы отдельно для каждого пользователя.

```bash
# Место хранения образов текущего пользователя
echo ~/.local/share/containers/storage/

# Скачать образ
podman pull alpine:latest

# Посмотреть где он лежит на диске
podman image inspect alpine:latest \
  --format '{{.GraphDriver.Data.UpperDir}}'
# /home/user/.local/share/containers/storage/overlay/abc123.../diff

# Сравнить размер
du -sh ~/.local/share/containers/storage/
```

Важное следствие: образы разных пользователей изолированы. То что скачал `user1` — не видит `user2`. Это хорошо для безопасности, но нужно учитывать в CI где каждая сборка — новый пользователь.

---

## Конфигурационные файлы

Podman берёт конфигурацию из нескольких мест. Пользовательские настройки переопределяют системные.

### registries.conf — список реестров

```bash
# Системный (для всех пользователей)
cat /etc/containers/registries.conf

# Пользовательский (только для текущего)
cat ~/.config/containers/registries.conf  # может не существовать
```

Ключевые параметры:
```toml
# Реестры для поиска при неполном имени образа
unqualified-search-registries = ["docker.io", "quay.io"]

# Если пусто — podman search nginx не будет работать без полного пути
# Рекомендуется добавить docker.io:
[[registry]]
location = "docker.io"
```

Без `unqualified-search-registries` команда `podman pull nginx` выдаст ошибку — нужно писать `podman pull docker.io/library/nginx`. Это намеренное решение: явное лучше неявного.

### storage.conf — хранилище образов

```bash
cat /etc/containers/storage.conf
```

Обычно трогать не нужно. Полезно если хотите перенести хранилище на другой диск:

```toml
[storage]
driver = "overlay"
# Изменить путь к хранилищу (по умолчанию ~/.local/share/containers/storage)
graphRoot = "/data/containers/storage"
```

После изменения нужно выполнить `podman system migrate`.

### containers.conf — поведение контейнеров

```bash
cat /etc/containers/containers.conf
```

Здесь можно задать умолчания для всех контейнеров: сеть, ресурсы, seccomp-профиль. Для начала трогать не нужно.

---

## Добавить реестры для удобной работы

По умолчанию Podman требует полного имени образа. Чтобы `podman pull nginx` работало как в Docker — добавьте `docker.io` в список реестров для поиска.

```bash
# Создать пользовательский конфиг
mkdir -p ~/.config/containers/

cat > ~/.config/containers/registries.conf << 'EOF'
unqualified-search-registries = ["docker.io"]
EOF

# Теперь работает сокращённое имя
podman pull nginx        # равнозначно docker.io/library/nginx:latest
podman pull python:3.12  # равнозначно docker.io/library/python:3.12
```

---

## Проверка user namespaces

Rootless Podman использует user namespaces — механизм ядра Linux для маппинга UID. Убедимся что всё настроено.

```bash
# Проверить что user namespaces включены
cat /proc/sys/user/max_user_namespaces
# Должно быть > 0 (обычно 14620 или больше)

# Посмотреть маппинг UID для своего пользователя
cat /etc/subuid
# username:100000:65536
# Это значит: UID 100000-165535 зарезервированы для username

cat /etc/subgid
# username:100000:65536

# Если записи нет — добавить:
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER
```

Проверить что маппинг работает:
```bash
# Войти в user namespace
podman unshare cat /proc/self/uid_map
# Вывод:    0    1000    1
#           ^      ^     ^
#         UID 0  UID 1000  только 1 UID
# Внутри namespace UID 0 = UID 1000 снаружи
```

---

## Установить вспомогательные утилиты

```bash
# skopeo — работа с образами и реестрами
sudo apt install -y skopeo    # Ubuntu/Debian
sudo dnf install -y skopeo    # RHEL/Fedora

# buildah — сборка образов (часто идёт с Podman)
sudo apt install -y buildah
sudo dnf install -y buildah

# podman-compose — аналог docker-compose
pip3 install podman-compose
# или
sudo apt install podman-compose

# Проверить всё
podman --version
skopeo --version
buildah --version
podman-compose --version
```

---

## Типичные ошибки при установке

**`WARN[0000] "/" is not a shared mount`**
Появляется после обновления пакета Podman. Исправляется:
```bash
podman system migrate
```

**`newuidmap: write to uid_map failed: Operation not permitted`**
Нет пакета `uidmap` или не заполнен `/etc/subuid`:
```bash
sudo apt install uidmap
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER
# Перелогиниться (или newgrp)
```

**`Error: short-name resolution enforced but unqualified image name "nginx" has no candidates`**
Не настроен `unqualified-search-registries`. Добавить `docker.io` в `~/.config/containers/registries.conf` как показано выше.

**`cannot find newuidmap: exec: "newuidmap": executable file not found`**
```bash
sudo apt install uidmap
```

**User namespaces отключены (старые системы)**
```bash
cat /proc/sys/user/max_user_namespaces
# 0 — отключены

# Включить (не persistent):
sudo sysctl user.max_user_namespaces=65536

# Persistent (добавить в /etc/sysctl.d/):
echo "user.max_user_namespaces=65536" | sudo tee /etc/sysctl.d/userns.conf
sudo sysctl --system
```

---

## Чек-лист для самопроверки

- [ ] Podman установлен, `podman --version` показывает 4.4+ или 5.x
- [ ] `podman run --rm hello-world` работает без sudo
- [ ] `podman info` показывает `rootless: true`
- [ ] Знаю где хранятся образы (`~/.local/share/containers/storage/`)
- [ ] `/etc/subuid` содержит запись для моего пользователя

## Попробуйте сами

1. Запустите `podman run -d --name test-sleep alpine sleep 120`. Пока контейнер работает, выполните `ps aux | grep sleep`. Какой UID у процесса на хосте? Теперь остановите контейнер.

2. Скачайте образ `python:3.12-slim` и найдите где он физически лежит на диске:
   ```bash
   podman pull python:3.12-slim
   du -sh ~/.local/share/containers/storage/
   podman image inspect python:3.12-slim --format '{{.GraphDriver.Data}}'
   ```

3. Добавьте `docker.io` в `unqualified-search-registries` и проверьте что `podman pull nginx` работает без полного пути. Затем попробуйте `podman search python` — из каких реестров приходят результаты?
