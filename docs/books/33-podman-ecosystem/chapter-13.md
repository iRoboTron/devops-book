# Глава 13: Диагностика и типичные проблемы

## Что вы узнаете

- как читать вывод `podman info` и находить причину проблемы;
- как диагностировать rootless-ошибки по сообщению об ошибке;
- как очистить зависшее состояние без потери данных;
- стандартный алгоритм отладки проблем с контейнерами.

---

## Алгоритм диагностики

Когда что-то не работает — следуйте этому порядку:

```text
1. Проверить статус контейнера
   podman ps -a
   
2. Посмотреть логи
   podman logs <container>
   
3. Инспектировать контейнер
   podman inspect <container>
   
4. Проверить события системы
   podman events --filter container=<container>
   
5. Если не запускается — запустить интерактивно
   podman run -it --rm <image> sh
   
6. Если проблема в сети
   podman network inspect <network>
   podman exec <container> ping <other-container>
   
7. Если проблема в rootless/правах
   podman unshare ls -la /path
   podman info --format '{{.Host.Security}}'
   
8. Debug-уровень логов
   podman --log-level=debug run ... 2>&1 | head -100
```

---

## Основные инструменты

### podman info

Первое что нужно выполнить когда что-то не так с установкой:

```bash
podman info
```

Ключевые секции:

```yaml
host:
  arch: amd64
  os: linux
  security:
    apparmor: false
    rootless: true            # ← должно быть true для rootless
    seccomp: true
    selinuxEnabled: false
  cgroupVersion: v2           # ← v2 нужен для полного rootless
  networkBackend: netavark    # ← netavark (новый) или cni (старый)
  
store:
  graphDriverName: overlay    # ← если vfs — производительность хуже
  graphRoot: /home/user/.local/share/containers/storage

version:
  Version: 5.1.2
  APIVersion: 5.1.2

plugins:
  network: [bridge, macvlan]
```

### podman events

Показывает все события: запуск, остановка, ошибки:

```bash
# Все события за последний час
podman events --since "1h"

# Следить в реальном времени
podman events

# Только для конкретного контейнера
podman events --filter container=nginx-web

# Только ошибки
podman events --filter event=die --since "24h"
```

### podman diff

Показывает что изменилось в файловой системе контейнера:

```bash
podman run -d --name test nginx

# Что изменилось в запущенном контейнере
podman diff test
# C /var                  ← changed (изменена)
# C /var/cache
# A /var/cache/nginx/...  ← added (добавлена)
```

Полезно для отладки: что пишет приложение, какие файлы создаёт.

### podman top

Процессы внутри контейнера в реальном времени:

```bash
podman top nginx-web

# Расширенный формат
podman top nginx-web pid,ppid,user,%cpu,%mem,args

# Все процессы во всех контейнерах
podman top --latest
```

---

## Диагностика по сообщению об ошибке

### Ошибки установки и запуска

**`newuidmap: write to uid_map failed: Operation not permitted`**
```text
Причина: /etc/subuid не настроен или пакет uidmap не установлен
Диагностика:
  cat /etc/subuid | grep $USER
  which newuidmap

Решение:
  sudo apt install uidmap
  sudo usermod --add-subuids 100000-165535 \
               --add-subgids 100000-165535 $USER
  podman system migrate
```

**`WARN[0000] "/" is not a shared mount`**
```text
Причина: нужна миграция после обновления Podman
Решение:
  podman system migrate
```

**`user namespaces not supported`**
```text
Причина: ядро не поддерживает или user_namespaces отключены
Диагностика:
  cat /proc/sys/user/max_user_namespaces
  # 0 — отключены

Решение:
  echo "user.max_user_namespaces=65536" | \
    sudo tee /etc/sysctl.d/userns.conf
  sudo sysctl --system
```

**`network slirp4netns not found`**
```text
Причина: не установлен slirp4netns или pasta
Решение:
  sudo apt install slirp4netns
  # или
  sudo dnf install passt  # для pasta (Podman 5+)
```

### Ошибки сети

**Контейнеры не видят друг друга**
```bash
# Проверить в какой сети контейнеры
podman inspect container1 --format '{{.NetworkSettings.Networks}}'
podman inspect container2 --format '{{.NetworkSettings.Networks}}'

# Если в разных сетях — подключить к одной:
podman network connect mynetwork container1
podman network connect mynetwork container2

# Или пересоздать с нужной сетью:
podman run --network mynetwork ...
```

**`Error: rootlessport cannot expose privileged port 80`**
```bash
# Вариант 1: использовать порт > 1024
podman run -p 8080:80 nginx

# Вариант 2: разрешить через sysctl
sudo sysctl net.ipv4.ip_unprivileged_port_start=80
# Persistent:
echo "net.ipv4.ip_unprivileged_port_start=80" | \
  sudo tee /etc/sysctl.d/unprivileged-ports.conf
sudo sysctl --system
```

**DNS не работает внутри контейнера**
```bash
# Проверить resolv.conf внутри контейнера
podman exec mycontainer cat /etc/resolv.conf

# Если пустой или неверный — задать явно:
podman run --dns 8.8.8.8 myimage

# Или настроить в containers.conf:
# [containers]
# dns_servers = ["8.8.8.8", "1.1.1.1"]
```

### Ошибки прав доступа

**`permission denied` при монтировании тома**
```bash
# Диагностика: проверить права директории
ls -la /path/to/mount

# Проверить как маппируется UID:
podman unshare ls -la /path/to/mount

# Решения:
# 1. Изменить владельца:
chown -R $USER:$USER /path/to/mount

# 2. Использовать --userns=keep-id:
podman run -v /path/to/mount:/data --userns=keep-id myimage

# 3. SELinux: добавить :z
podman run -v /path/to/mount:/data:z myimage
```

**Образ собирается, но запрещено писать в директорию**
```bash
# Внутри контейнера процесс запускается как root (UID 0)
# но реальный UID на хосте — 100000+ (из subuid)
# Это нормально, но влияет на bind-mounts

# Проверить UID внутри контейнера:
podman exec mycontainer id
# uid=0(root) gid=0(root)

# UID снаружи:
ps aux | grep <process>
# UID = 100000 (не 0)
```

### Ошибки образов

**`Error: short-name "nginx" did not resolve`**
```bash
# Настроить unqualified-search-registries
cat >> ~/.config/containers/registries.conf << 'EOF'
unqualified-search-registries = ["docker.io"]
EOF

# Или использовать полное имя:
podman pull docker.io/library/nginx:latest
```

**`Error: unable to pull image: ... 429 Too Many Requests`**
```bash
# Rate limit Docker Hub
# Залогиниться (200 запросов вместо 100):
podman login docker.io

# Или использовать альтернативный реестр:
podman pull quay.io/library/nginx  # не всегда доступно
```

**Образ скачивается но `podman run` падает**
```bash
# Посмотреть что происходит при старте
podman run --rm myimage  # посмотреть вывод

# Если падает сразу — проверить CMD/ENTRYPOINT
podman inspect myimage --format '{{.Config.Cmd}}'
podman inspect myimage --format '{{.Config.Entrypoint}}'

# Запустить с другой командой:
podman run --rm -it --entrypoint sh myimage
```

### Проблемы с systemd/Quadlet

**Квадлет игнорирует изменения в .container файле**
```bash
# После любого изменения .container файла обязательно:
systemctl --user daemon-reload

# Проверить что systemd видит новый файл:
systemctl --user cat nginx-web.service
```

**Сервис останавливается после выхода из SSH**
```bash
# Включить linger:
sudo loginctl enable-linger $USER
loginctl show-user $USER | grep Linger
# Linger=yes

# Перезапустить сервис:
systemctl --user restart nginx-web.service
```

**`Failed to connect to bus: No such file or directory`**
```bash
# XDG_RUNTIME_DIR не установлен (часто при sudo или смене пользователя)
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user status
```

---

## Очистка зависшего состояния

### Безопасная очистка

```bash
# Посмотреть что занимает место
podman system df
# TYPE            TOTAL   ACTIVE  SIZE    RECLAIMABLE
# Images          15      3       4.2GB   2.8GB (66%)
# Containers      8       2       120MB   118MB (98%)
# Volumes         5       2       800MB   400MB (50%)

# Удалить остановленные контейнеры
podman container prune

# Удалить образы не используемые ни одним контейнером
podman image prune

# Удалить неиспользуемые сети
podman network prune

# Всё сразу (кроме томов):
podman system prune
```

### Деструктивная очистка

> ☠️ **Осторожно:** следующие команды удаляют данные без возможности восстановления. Убедитесь что данные либо не нужны, либо есть резервная копия.

```bash
# Удалить конкретный том (и его данные!)
podman volume rm myvolume

# Удалить все неиспользуемые тома
podman volume prune

# ☠️ Удалить ВСЁ — контейнеры, образы, тома, сети:
podman system prune --all --volumes

# ☠️ Полный сброс Podman (как чистая установка):
podman system reset
# Вопрос: Are you sure you want to continue? [y/N]
```

**Перед деструктивной очисткой:**
```bash
# Проверить что в томах:
podman volume ls
for v in $(podman volume ls -q); do
  echo "=== $v ==="
  podman volume inspect $v --format '{{.Mountpoint}}'
  ls -la $(podman volume inspect $v --format '{{.Mountpoint}}') | head -5
done
```

---

## Продвинутая диагностика

### Подробные логи Podman

```bash
# Debug-уровень — показывает все операции
podman --log-level=debug run --rm alpine echo hi 2>&1 | head -50

# Trace — максимальная детализация (очень много вывода)
podman --log-level=trace run --rm alpine echo hi 2>&1 | head -100
```

### strace для контейнерного процесса

```bash
# Запустить контейнер
podman run -d --name debug-app myapp

# Найти PID на хосте
podman inspect debug-app --format '{{.State.Pid}}'
PID=12345

# strace
sudo strace -f -p $PID -e trace=network,file 2>&1 | head -50
```

### Проверить cgroups контейнера

```bash
# cgroup v2: файлы в /sys/fs/cgroup/
podman inspect mycontainer --format '{{.State.Pid}}'
PID=12345

# Найти cgroup:
cat /proc/$PID/cgroup
# 0::/user.slice/user-1000.slice/user@1000.service/...

# Посмотреть лимиты:
cat /sys/fs/cgroup/user.slice/.../memory.max
cat /sys/fs/cgroup/user.slice/.../cpu.max
```

### Проверить что слышит приложение

```bash
# Порты которые слушает приложение внутри контейнера:
podman exec myapp ss -tlnp
# или
podman exec myapp netstat -tlnp

# С хоста — порты которые Podman перебрасывает:
podman port myapp
# 8080/tcp -> 0.0.0.0:8080
```

---

## Справочник типичных ошибок

| Сообщение | Причина | Решение |
|-----------|---------|---------|
| `newuidmap: write to uid_map failed` | Нет uidmap или subuid | `apt install uidmap` + `usermod --add-subuids` |
| `"/" is not a shared mount` | После обновления Podman | `podman system migrate` |
| `slirp4netns not found` | Нет пакета | `apt install slirp4netns` |
| `privileged port 80` | rootless не может < 1024 | Использовать 8080 или sysctl |
| `short-name did not resolve` | Нет unqualified registries | Добавить docker.io в registries.conf |
| `429 Too Many Requests` | Rate limit Docker Hub | `podman login docker.io` |
| `permission denied` на том | UID mismatch | `--userns=keep-id` или `chown` |
| `Failed to connect to bus` | Нет XDG_RUNTIME_DIR | `export XDG_RUNTIME_DIR=/run/user/$(id -u)` |
| Сервис останавливается после logout | Нет linger | `loginctl enable-linger $USER` |
| Quadlet не применяется | Не выполнен daemon-reload | `systemctl --user daemon-reload` |

---

## Чек-лист для самопроверки

- [ ] Умею читать `podman info` и находить подозрительные значения
- [ ] Знаю стандартный алгоритм диагностики (ps → logs → inspect → events → interactive)
- [ ] Могу определить тип ошибки по сообщению и применить решение
- [ ] Знаю разницу между безопасной (`container prune`) и деструктивной (`system prune --all --volumes`) очисткой
- [ ] Умею смотреть логи systemd-сервиса через `journalctl --user`

## Попробуйте сами

1. Намеренно создайте ошибку и найдите её через диагностику:
   ```bash
   # Запустить контейнер с неверной командой
   podman run -d --name broken alpine nonexistent-command
   
   # Найти проблему:
   podman ps -a       # статус?
   podman logs broken # что в логах?
   podman inspect broken --format '{{.State.ExitCode}}'
   podman events --filter container=broken
   ```

2. Исследуйте что занимает место:
   ```bash
   podman system df
   podman images
   podman volume ls
   # Скачайте несколько образов и сравните размер до/после prune
   podman pull python:3.12
   podman pull nginx:latest
   podman image prune
   podman system df  # изменилось?
   ```

3. Воспроизведите ошибку с правами на том и диагностируйте:
   ```bash
   sudo mkdir -p /tmp/root-owned
   sudo touch /tmp/root-owned/file.txt
   
   # Попробуйте записать в него из контейнера:
   podman run --rm -v /tmp/root-owned:/data alpine touch /data/new.txt
   # Ошибка?
   
   # Теперь с --userns=keep-id:
   podman run --rm -v /tmp/root-owned:/data --userns=keep-id alpine touch /data/new.txt
   # Другой результат?
   ```
