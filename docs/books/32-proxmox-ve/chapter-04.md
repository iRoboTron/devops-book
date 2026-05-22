# Глава 4: Docker внутри LXC

> **Цель:** правильно запустить Docker в LXC-контейнере — вручную и через Community Scripts.

---

## Что вы узнаете

- почему Docker не запускают напрямую на хосте Proxmox («священный уровень»);
- как настроить LXC-контейнер для работы с Docker (features: nesting, keyctl);
- как установить Docker вручную и проверить что всё работает;
- как использовать Community Scripts для быстрого развёртывания;
- как запустить nginx и убедиться что он открывается в браузере.

---

## 4.1 Почему не на хосте — «священный уровень»

Если вы только пришли к Proxmox после Ubuntu с Docker, первый соблазн — поставить Docker прямо на хост Proxmox. Так привычнее. Не надо возиться с LXC. Технически это работает.

Но это плохая идея, и вот почему.

Хост Proxmox — это священный уровень. Он должен делать одно дело: запускать виртуальные машины и контейнеры. Как только вы начинаете ставить туда сервисы, начинаются проблемы:

```
Плохо:
Proxmox Host → Docker → nginx, nextcloud, jellyfin
  - Docker-демон мешает управлению сетью в Proxmox
  - Обновление ядра может сломать и Docker, и все контейнеры сразу
  - Нет снапшотов для Docker-стека
  - Нет бэкапа одним кликом
  - Невозможно изолировать сервисы по RAM/CPU отдельно

Правильно:
Proxmox Host → LXC (docker-01) → Docker → nginx, nextcloud, jellyfin
  - Docker изолирован в контейнере
  - Снапшот LXC = снапшот всего Docker-стека за секунды
  - Бэкап LXC включает всё: образы, тома, конфиги
  - Хост остаётся чистым и стабильным
  - Сломался Docker — пересоздал LXC, хост не тронут
```

Ещё одна причина: Docker активно работает с сетевыми правилами iptables и создаёт виртуальные интерфейсы. На хосте Proxmox это конфликтует с сетевой моделью гипервизора. Бывает что после запуска Docker интерфейс Proxmox перестаёт работать корректно.

**Правило:** хост Proxmox — только для управления. Все сервисы — в LXC или VM.

---

## 4.2 Почему именно LXC, а не VM для Docker

Можно запустить Ubuntu VM и поставить туда Docker. Это тоже работает. Но LXC легче:

| | LXC с Docker | VM с Docker |
|---|---|---|
| Накладные расходы по RAM | ~20–30 MB на LXC | ~200–500 MB на VM |
| Время запуска | 1–2 секунды | 15–30 секунд |
| Снапшоты | Да | Да |
| Бэкапы | Быстрее (нет полного диска VM) | Медленнее |
| Изоляция ядра | Общее с хостом | Отдельное |

Для Docker-сервисов LXC — оптимальный выбор. VM нужна, когда требуется отдельное ядро или запускается Windows.

---

## 4.3 Настройка LXC для Docker: features

Docker внутри LXC требует двух специальных параметров:

- **nesting=1** — разрешает вложенную виртуализацию. Docker создаёт свои пространства имён (namespaces) внутри контейнера. Без этого Docker не запустится.
- **keyctl=1** — разрешает доступ к ключевому кольцу ядра. Нужно для корректной работы containerd и некоторых образов.

Также контейнер должен быть **privileged** (привилегированный). Unprivileged LXC ограничивает возможности, и Docker в нём работает нестабильно или вовсе не запускается.

### Настройка через веб-интерфейс

При создании LXC снимите галочку «Unprivileged container».

После создания контейнера:
```
CT → Options → Features → включить Nesting и Keyctl
```

### Настройка через конфиг на хосте

Файл конфига каждого LXC хранится на хосте в `/etc/pve/lxc/<VMID>.conf`.

```bash
# Открыть конфиг контейнера с ID 100
nano /etc/pve/lxc/100.conf
```

Добавить или изменить строку:

```
features: keyctl=1,nesting=1
```

После изменения конфига перезапустить контейнер:

```bash
pct stop 100 && pct start 100
```

### Создание LXC с нужными параметрами через CLI

```bash
# Создаём privileged LXC с Debian 12, сразу с нужными features
# --unprivileged 0 — контейнер привилегированный
pct create 100 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname docker-01 \
  --memory 2048 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --storage local-lvm \
  --rootfs local-lvm:20 \
  --features keyctl=1,nesting=1 \
  --unprivileged 0 \
  --password
```

Запустить и войти:

```bash
pct start 100
pct enter 100
```

---

## 4.4 Установка Docker вручную

Внутри LXC используем официальный скрипт установки от Docker:

```bash
# Обновить пакеты
apt update && apt upgrade -y

# Установить Docker официальным скриптом
# Скрипт сам определяет дистрибутив и добавляет репозиторий Docker
curl -fsSL https://get.docker.com | sh
```

Включить и запустить Docker:

```bash
# Запустить сервис и добавить в автозапуск
systemctl enable --now docker
```

Проверить статус:

```bash
systemctl status docker
```

Пример вывода при успешном запуске:
```
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled)
     Active: active (running) since ...
```

---

## 4.5 Проверка установки

Запустить тестовый контейнер:

```bash
docker run hello-world
```

Пример вывода:
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

Проверить список запущенных контейнеров:

```bash
docker ps
```

Проверить версию:

```bash
docker --version
# Docker version 27.x.x, build ...
```

Если `hello-world` запустился — Docker в LXC работает корректно. Если вместо этого появляется ошибка вроде `cannot create container`, скорее всего features не применились. Проверьте конфиг:

```bash
# На хосте Proxmox (не внутри LXC)
grep features /etc/pve/lxc/100.conf
# Должна быть строка: features: keyctl=1,nesting=1
```

---

## 4.6 Community Scripts — один скрипт вместо ручной установки

Community Scripts — коллекция готовых bash-скриптов, которые создают LXC (или VM) и устанавливают нужный сервис автоматически. Поддерживаются сообществом, обновляются регулярно.

Скрипт для Docker LXC создаёт контейнер с нужными настройками и устанавливает Docker + Portainer (веб-интерфейс для управления контейнерами).

Запускается **на хосте Proxmox** в Shell:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"
```

Скрипт задаст несколько вопросов: ID контейнера, размер диска, RAM. Можно принять значения по умолчанию.

После завершения скрипт выведет IP-адрес контейнера и порт для доступа к Portainer.

**Важно:** всегда читайте что делает скрипт перед запуском. Просмотр содержимого:

```bash
curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh | less
```

Страница проекта с документацией: `https://community-scripts.github.io/ProxmoxVE/`

---

## 4.7 Пример: запустить nginx и проверить в браузере

Это практическое задание: запустить nginx в Docker внутри LXC и убедиться что страница открывается.

### Шаг 1: Узнать IP контейнера

Внутри LXC:

```bash
ip a show eth0
```

Пример вывода:
```
2: eth0@if5: <BROADCAST,MULTICAST,UP,LOWER_UP>
    inet 192.168.1.105/24 brd 192.168.1.255 scope global eth0
```

IP контейнера: `192.168.1.105`.

Или на хосте Proxmox:

```bash
pct exec 100 -- ip -4 a show eth0 | grep inet
```

### Шаг 2: Запустить nginx

Внутри LXC:

```bash
# Запустить nginx, прокинуть порт 80 контейнера на порт 8080 хоста LXC
# --name nginx — имя для удобного управления
# -d — в фоне
# -p 8080:80 — порт 8080 LXC → порт 80 nginx-контейнера
docker run -d --name nginx -p 8080:80 nginx
```

### Шаг 3: Проверить что nginx запустился

```bash
docker ps
```

Пример вывода:
```
CONTAINER ID   IMAGE   COMMAND                  CREATED         STATUS         PORTS                  NAMES
a1b2c3d4e5f6   nginx   "/docker-entrypoint.…"   5 seconds ago   Up 4 seconds   0.0.0.0:8080->80/tcp   nginx
```

### Шаг 4: Проверить из браузера

Открыть в браузере:
```
http://192.168.1.105:8080
```

Должна появиться страница «Welcome to nginx!».

Если браузер не открывает — проверить что запрос с правильного IP:

```bash
# Внутри LXC или на хосте Proxmox
curl -s http://192.168.1.105:8080 | grep -o "<title>.*</title>"
# <title>Welcome to nginx!</title>
```

### Шаг 5: Остановить и удалить тестовый контейнер

```bash
docker stop nginx
docker rm nginx
```

---

## 4.8 Типичные ошибки

### Docker не запускается: `kernel: unshare(CLONE_NEWNS) failed`

Причина: features не применены или контейнер privileged не выставлен.

```bash
# На хосте Proxmox — проверить конфиг
cat /etc/pve/lxc/100.conf | grep -E "features|unprivileged"
# Должно быть:
# features: keyctl=1,nesting=1
# unprivileged: 0
```

Если нет — добавить вручную и перезапустить LXC.

### `permission denied while trying to connect to the Docker daemon socket`

Пользователь не добавлен в группу docker. Внутри LXC:

```bash
# Если работаете не под root
usermod -aG docker $USER
# Перезайти в терминал чтобы группа применилась
```

### `iptables: No chain/target/match by that name`

Иногда возникает на старых ядрах Proxmox. Внутри LXC:

```bash
update-alternatives --set iptables /usr/sbin/iptables-legacy
update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
systemctl restart docker
```

---

## 4.9 Сравнение: ручная установка против Community Scripts

| | Ручная установка | Community Scripts |
|---|---|---|
| Время | 5–10 минут | 2–3 минуты |
| Контроль | Полный | Ограниченный |
| Понимание что происходит | Да | Требует чтения скрипта |
| Portainer в комплекте | Нет (надо отдельно) | Да |
| Подходит для обучения | Да | Для быстрого старта |
| Надёжность при проблемах сети | Высокая | Зависит от GitHub |

Рекомендация: сначала разобраться с ручной установкой — один раз. Потом использовать Community Scripts для скорости. Если скрипт недоступен — знаешь как сделать руками.

---

## Практика

1. Создать LXC с Debian 12 как privileged контейнер с features `keyctl=1,nesting=1`.
2. Войти в LXC через `pct enter` и установить Docker официальным скриптом.
3. Убедиться что `docker run hello-world` работает без ошибок.
4. Запустить `nginx` на порту 8080 и открыть в браузере по IP LXC.
5. (Опционально) Попробовать Community Scripts: запустить скрипт на хосте и сравнить результат.

---

## Чек-лист для самопроверки

- [ ] Docker установлен в LXC, `docker run hello-world` работает
- [ ] Понимаю зачем нужны nesting и keyctl — и что будет если их не включить
- [ ] Знаю разницу между privileged и unprivileged LXC применительно к Docker
- [ ] Контейнер с nginx открывается в браузере по IP LXC на порту 8080
- [ ] Знаю как проверить и исправить features в `/etc/pve/lxc/<ID>.conf`
- [ ] Понимаю почему Docker не ставится напрямую на хост Proxmox
