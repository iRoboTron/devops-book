# Глава 12: Типовые сценарии — запускаем реальные сервисы

> **Цель:** собрать всё изученное вместе и запустить реальный домашний сервер с Home Assistant, Nextcloud, Jellyfin и безопасным HTTPS-доступом.

---

**Что вы узнаете:**
- как развернуть Home Assistant OS в KVM-виртуальной машине двумя способами;
- как организовать Docker-стек с Nextcloud и Jellyfin в одном LXC;
- как настроить Nginx Proxy Manager как единую точку входа для всех сервисов;
- зачем нужен Let's Encrypt и почему self-signed сертификаты — не вариант для дома.

---

## 12.1 Что мы строим

Представь реальный домашний сервер. Ты хочешь:
- управлять умным домом через Home Assistant;
- хранить файлы в Nextcloud вместо чужих облаков;
- смотреть фильмы через Jellyfin с любого устройства;
- заходить на все сервисы по красивым доменным именам с HTTPS, а не по `192.168.1.x:8080`.

На голой Ubuntu с Docker это всё работало бы как лапша из контейнеров в одном пространстве. На Proxmox — это четыре изолированных сущности, каждая со своими снапшотами и бэкапами.

Итоговая схема:

```
Proxmox Host (16GB RAM, 512GB SSD + 2TB HDD)
├── VM  200: Home Assistant OS (2GB balloon)     — умный дом
├── CT  100: Docker LXC (3GB)                   — Nextcloud + Jellyfin + Portainer
├── CT  101: Nginx Proxy Manager (512MB)         — HTTPS + Let's Encrypt
├── CT  102: AdGuard Home (256MB)                — DNS + блокировка рекламы
├── CT  103: Uptime Kuma (256MB)                 — мониторинг сервисов
└── Backup: 2TB HDD → ежедневные бэкапы, 7 копий
```

Интернет-трафик попадает только на Nginx Proxy Manager, который маршрутизирует запросы к нужным сервисам:

```
Браузер/телефон
    │
    ▼
  DuckDNS (DNS → твой IP)
    │
    ▼
  Nginx Proxy Manager LXC (:80/:443)
    ├── ha.home.duckdns.org      → VM 200 :8123
    ├── cloud.home.duckdns.org   → CT 100 :8080 (Nextcloud)
    └── media.home.duckdns.org   → CT 100 :8096 (Jellyfin)
```

Начнём с каждого компонента по очереди.

---

## 12.2 Сценарий 1: Home Assistant OS

Home Assistant — популярная платформа автоматизации умного дома. Официально она поддерживает только два варианта установки: на отдельное железо (Raspberry Pi, Green, Yellow) или в виде виртуальной машины. LXC не подходит — HAOS требует полного контроля над системой, включая загрузчик и ядро.

### Способ А: Community Scripts (рекомендуется)

Самый простой способ — запустить готовый скрипт на хосте Proxmox через Shell:

```bash
# Эта команда скачивает и запускает скрипт установки HAOS VM.
# Скрипт создаёт VM, скачивает актуальный образ HAOS, импортирует диск
# и настраивает всё необходимое автоматически.
bash -c "$(curl -fsSL https://community-scripts.org/vm-scripts/haos-vm.sh)"
```

Скрипт задаст несколько вопросов: ID виртуальной машины (предложит 200), объём RAM, хранилище. После завершения VM появится в списке и будет готова к запуску.

После первого запуска Home Assistant инициализируется несколько минут. Открывай:
```
http://192.168.1.200:8123
```
(используй IP-адрес VM, который видно в веб-интерфейсе Proxmox под именем VM)

### Способ Б: Вручную через qm importdisk

Если Community Scripts недоступны или хочется понять что происходит — делаем шаги вручную.

**Шаг 1: Скачать образ HAOS**

На сайте `https://github.com/home-assistant/operating-system/releases` найди актуальную версию. Нужен файл с расширением `.qcow2` для KVM.

```bash
# Скачать образ прямо на хост Proxmox в папку для ISO
# (замени версию на актуальную с GitHub releases)
cd /var/lib/vz/template/iso
wget "https://github.com/home-assistant/operating-system/releases/download/12.3/haos_ova-12.3.qcow2.xz"

# Распаковать архив
xz -d haos_ova-12.3.qcow2.xz
# После распаковки получится файл haos_ova-12.3.qcow2
```

**Шаг 2: Создать пустую VM**

Через веб-интерфейс: кнопка **Create VM** → выставить параметры:
- VM ID: 200, Name: homeassistant
- OS: Do not use any media (образ мы подключим отдельно)
- System: Machine q35, BIOS OVMF (UEFI), добавить EFI disk
- Disk: удали диск который создаётся по умолчанию (он не нужен)
- CPU: 2 cores, RAM: 2048 MB (с Ballooning, minimum 512)
- Network: VirtIO, bridge vmbr0

**Шаг 3: Импортировать образ как диск VM**

```bash
# Эта команда берёт образ qcow2 и импортирует его как диск
# виртуальной машины 200 на хранилище local-lvm
qm importdisk 200 /var/lib/vz/template/iso/haos_ova-12.3.qcow2 local-lvm

# Пример вывода:
# imported disk as 'unused0:local-lvm:vm-200-disk-1'
```

**Шаг 4: Подключить диск и настроить загрузку**

После импорта диск появится во вкладке Hardware VM как `Unused Disk 0`. Нужно:
1. Дважды кликнуть на `Unused Disk 0` → выбрать тип `VirtIO Block` → Add.
2. Перейти в **Options → Boot Order** → поставить новый диск первым, снять галочку с `ide2` (CD/DVD).

**Шаг 5: Запустить VM**

```bash
qm start 200
```

Открывай веб-интерфейс VM через Console и наблюдай за загрузкой. Через 2-3 минуты Home Assistant будет доступен по адресу который покажет консоль.

### Настройка Balloon Memory для Home Assistant

HAOS работает стабильно с 2GB RAM, но потребляет больше при активной автоматизации. Balloon Memory позволяет VM брать больше RAM когда нужно:

```
Hardware → Memory:
  Memory: 2048 MB
  Minimum memory: 512 MB
  Ballooning Device: ✅ включить
```

VM стартует с 512MB, автоматически расширяется до 2GB по мере необходимости. Proxmox не тратит RAM впустую, когда HA простаивает.

---

## 12.3 Сценарий 2: Docker-сервер с Nextcloud и Jellyfin

Для сервисов на основе Docker лучше выделить один LXC-контейнер. Это даёт изоляцию от хоста, снапшоты всего стека одной командой и удобный бэкап.

### Создать Docker LXC через Community Scripts

```bash
# На хосте Proxmox в Shell — скрипт создаёт LXC с Debian 12,
# устанавливает Docker, Docker Compose и Portainer автоматически
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"
```

Скрипт спросит параметры: ID контейнера (100), RAM (3072 MB), диск (20GB), хранилище. После завершения войди в контейнер:

```bash
pct enter 100
```

Проверь что Docker работает:

```bash
docker --version
# Docker version 26.x.x, build ...

docker run hello-world
# Hello from Docker!
```

### Вручную (если скрипт недоступен)

```bash
# 1. Создать LXC — privileged, с поддержкой nesting для Docker
pct create 100 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname docker-01 \
  --memory 3072 \
  --cores 4 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1 \
  --storage local-lvm \
  --rootfs local-lvm:20 \
  --unprivileged 0 \
  --features keyctl=1,nesting=1

# 2. Запустить и войти
pct start 100
pct enter 100

# 3. Установить Docker официальным скриптом
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

### Запустить Nextcloud

Nextcloud — это облачное хранилище которое ты держишь у себя. Данные не уходят в Google Drive или Dropbox.

```bash
# Внутри Docker LXC (CT 100)
mkdir -p /opt/nextcloud
cat > /opt/nextcloud/docker-compose.yml << 'EOF'
services:
  db:
    image: mariadb:10.11
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: "changeme_root"
      MYSQL_DATABASE: nextcloud
      MYSQL_USER: nextcloud
      MYSQL_PASSWORD: "changeme_nc"
    volumes:
      - db_data:/var/lib/mysql

  nextcloud:
    image: nextcloud:28
    restart: always
    ports:
      - "8080:80"
    depends_on:
      - db
    environment:
      MYSQL_HOST: db
      MYSQL_DATABASE: nextcloud
      MYSQL_USER: nextcloud
      MYSQL_PASSWORD: "changeme_nc"
      NEXTCLOUD_TRUSTED_DOMAINS: "cloud.home.duckdns.org 192.168.1.100"
    volumes:
      - nc_data:/var/www/html

volumes:
  db_data:
  nc_data:
EOF

cd /opt/nextcloud && docker compose up -d
```

Через 2-3 минуты Nextcloud будет доступен по адресу `http://192.168.1.100:8080`. При первом заходе создашь учётную запись администратора.

### Запустить Jellyfin

Jellyfin — медиасервер с открытым кодом. Позволяет смотреть фильмы, сериалы и музыку с любого устройства в домашней сети и удалённо.

```bash
# Внутри Docker LXC
mkdir -p /opt/jellyfin /mnt/media

cat > /opt/jellyfin/docker-compose.yml << 'EOF'
services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    restart: always
    ports:
      - "8096:8096"
    volumes:
      - ./config:/config
      - ./cache:/cache
      - /mnt/media:/media:ro   # медиафайлы подключаются как read-only
    environment:
      - JELLYFIN_PublishedServerUrl=http://media.home.duckdns.org
EOF

cd /opt/jellyfin && docker compose up -d
```

Jellyfin открывается по адресу `http://192.168.1.100:8096`. При первом запуске мастер настройки попросит указать папки с медиафайлами — укажи `/media`.

Для медиафайлов лучше использовать отдельный HDD, примонтированный к LXC. Как это сделать — в главе 18 (сценарий 2).

### Portainer — управление Docker через веб

Если установка шла через Community Scripts, Portainer уже есть. Если нет:

```bash
# Внутри LXC
docker run -d \
  --name portainer \
  --restart always \
  -p 9000:9000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

Portainer открывается по `http://192.168.1.100:9000`. Удобный дашборд для просмотра состояния контейнеров, просмотра логов и управления стеками.

---

## 12.4 Сценарий 3: Nginx Proxy Manager — единая точка входа

Сейчас сервисы доступны только по IP и порту: `192.168.1.100:8080`, `192.168.1.200:8123`. Это неудобно и небезопасно для доступа из интернета. Nginx Proxy Manager (NPM) решает обе проблемы: красивые домены и HTTPS.

### Установить NPM через Community Scripts

```bash
# На хосте Proxmox — скрипт создаёт отдельный LXC с NPM
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/nginx-proxy-manager.sh)"
```

NPM запустится в новом LXC (ID 101) и будет доступен по адресу:
```
http://192.168.1.101:81
```

Логин по умолчанию: `admin@example.com` / `changeme` — сразу смени при первом входе.

### Вручную через Docker Compose

```bash
# Внутри LXC 101 (или в Docker LXC если хочешь объединить)
mkdir -p /opt/npm && cd /opt/npm

cat > docker-compose.yml << 'EOF'
services:
  npm:
    image: jc21/nginx-proxy-manager:latest
    restart: always
    ports:
      - "80:80"      # HTTP
      - "443:443"    # HTTPS
      - "81:81"      # Веб-интерфейс NPM
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
EOF

docker compose up -d
```

### Настроить прокси-хосты

В интерфейсе NPM: **Proxy Hosts → Add Proxy Host**.

Для Nextcloud:
```
Domain Names:    cloud.home.duckdns.org
Scheme:          http
Forward Hostname/IP: 192.168.1.100   ← IP Docker LXC
Forward Port:    8080
```

Для Home Assistant:
```
Domain Names:    ha.home.duckdns.org
Scheme:          http
Forward Hostname/IP: 192.168.1.200   ← IP HA VM
Forward Port:    8123
```

Для Jellyfin:
```
Domain Names:    media.home.duckdns.org
Scheme:          http
Forward Hostname/IP: 192.168.1.100
Forward Port:    8096
```

После добавления хостов трафик маршрутизируется правильно. Но пока HTTPS не настроен — браузер будет показывать предупреждение о незащищённом соединении.

---

## 12.5 Сценарий 4: Let's Encrypt через DuckDNS

### Почему self-signed сертификат — плохой вариант

Самоподписанный (self-signed) сертификат можно сгенерировать за секунду и браузер перестанет кричать об ошибке. Но это полумера с серьёзными последствиями:

**Браузер помечает сайт как опасный.** Каждый новый браузер или устройство требует вручную добавить исключение. На телефоне гостя это объяснять особенно неудобно.

**Мобильные приложения не работают.** Home Assistant Companion App и мобильный клиент Nextcloud отказываются подключаться к серверу с self-signed сертификатом — они просто выдают ошибку без возможности добавить исключение.

**Нет защиты от подмены.** Self-signed сертификат никак не подтверждает что ты подключаешься именно к своему серверу, а не к кому-то, кто перехватил трафик.

Let's Encrypt — бесплатный центр сертификации. Сертификаты от него доверяют все браузеры и все мобильные приложения. NPM умеет автоматически получать и обновлять их каждые 90 дней.

### Зарегистрировать бесплатный домен на DuckDNS

DuckDNS — бесплатный DNS-сервис. Ты получаешь домен вида `yourname.duckdns.org` и можешь указать ему любой IP-адрес.

1. Зайди на `https://www.duckdns.org` и войди через GitHub, Google или Reddit.
2. Создай субдомен: например `homeserver` → получишь `homeserver.duckdns.org`.
3. Укажи IP своего сервера (домашний внешний IP) или IP для тестирования.
4. Скопируй свой **Token** — он понадобится для NPM.

Для множества сервисов удобнее получить **wildcard-сертификат** на `*.homeserver.duckdns.org` — он покроет все поддомены: `ha.homeserver.duckdns.org`, `cloud.homeserver.duckdns.org`, `media.homeserver.duckdns.org`.

### Получить сертификат через NPM

В интерфейсе NPM: **SSL Certificates → Add SSL Certificate → Let's Encrypt**.

```
Domain Names:        *.homeserver.duckdns.org
                     homeserver.duckdns.org
Email Address:       твой@email.com
Use a DNS Challenge: ✅ включить
DNS Provider:        DuckDNS
Credentials:         Token: твой_токен_с_сайта_duckdns.org
```

Нажми **Save**. NPM обратится к Let's Encrypt, тот попросит подтвердить владение доменом через DNS-запись. NPM автоматически создаст нужную TXT-запись через DuckDNS API и Let's Encrypt выдаст сертификат.

Через 1-2 минуты в списке SSL Certificates появится новый сертификат с зелёным значком.

**Главное преимущество DNS-01 метода:** не нужно открывать порт 80 для верификации. Сертификат работает даже если у тебя нет публичного IP или используешь Tailscale для доступа.

### Включить HTTPS в прокси-хостах

Теперь для каждого прокси-хоста в NPM:
1. Открыть хост → вкладка **SSL**.
2. Выбрать только что созданный сертификат `*.homeserver.duckdns.org`.
3. Включить **Force SSL** — HTTP будет автоматически перенаправляться на HTTPS.
4. Для Home Assistant включить также **Websockets Support** — HA использует их для real-time обновлений.

После этого браузер будет открывать сервисы с зелёным замком:
```
https://ha.homeserver.duckdns.org     — Home Assistant
https://cloud.homeserver.duckdns.org  — Nextcloud
https://media.homeserver.duckdns.org  — Jellyfin
```

### Home Assistant и внешние домены

Home Assistant требует явно разрешить внешние URL. В конфигурации HA (`configuration.yaml`):

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 192.168.1.101   # IP Nginx Proxy Manager LXC
```

Это говорит HA что запросы через прокси легитимны. Без этого HA будет возвращать ошибку 400.

---

## 12.6 Итоговая схема домашнего сервера

После всех настроек сервер выглядит так:

```
Proxmox Host (16GB RAM, 512GB SSD + 2TB HDD)
│
├── VM 200: Home Assistant OS (2GB balloon, 2 CPU)
│     └── :8123 → ha.homeserver.duckdns.org
│
├── CT 100: Docker LXC (3GB RAM, 4 CPU, 20GB SSD)
│     ├── Nextcloud  :8080 → cloud.homeserver.duckdns.org
│     ├── Jellyfin   :8096 → media.homeserver.duckdns.org
│     └── Portainer  :9000 (только локально)
│
├── CT 101: Nginx Proxy Manager (512MB RAM, 1 CPU, 5GB SSD)
│     ├── :80/:443 — точка входа всего HTTPS трафика
│     └── Let's Encrypt wildcard *.homeserver.duckdns.org
│
├── CT 102: AdGuard Home (256MB RAM, 1 CPU, 2GB SSD)
│     └── DNS :53 — блокировка рекламы для всей сети
│
├── CT 103: Uptime Kuma (256MB RAM, 1 CPU, 4GB SSD)
│     └── :3001 — мониторинг всех сервисов + Telegram
│
└── Backup: 2TB HDD
      └── Datacenter → Backup → ежедневно 03:00, zstd, 7 копий
```

**Использование ресурсов при такой конфигурации:**

| Контейнер/VM | RAM лимит | CPU | Диск |
|---|---|---|---|
| HA OS (VM 200) | 2GB balloon | 2 | 32GB SSD |
| Docker LXC (CT 100) | 3GB | 4 | 20GB SSD |
| Nginx PM (CT 101) | 512MB | 1 | 5GB SSD |
| AdGuard (CT 102) | 256MB | 1 | 2GB SSD |
| Uptime Kuma (CT 103) | 256MB | 1 | 4GB SSD |
| **Итого** | **~6GB** | **9** | **63GB SSD** |

На 16GB RAM остаётся около 10GB свободными — запас для хоста Proxmox, кэша и роста нагрузки.

### Доступ к серверу

**Из домашней сети:** напрямую по IP или через домены (если в роутере настроен DNS override или используешь AdGuard Home как DNS-сервер).

**Из интернета:** через Nginx Proxy Manager по доменам `*.homeserver.duckdns.org` — с HTTPS и зелёным замком.

**Из любой точки через Tailscale:** даже без открытых портов. Установи Tailscale на хост Proxmox (глава 11) и получай доступ ко всей инфраструктуре через Tailscale IP.

Лучшая комбинация для дома: домены через DuckDNS + NPM для удобного HTTPS-доступа, Tailscale для управления Proxmox без риска выставить :8006 в интернет.

---

## 12.7 Типичные ошибки

**Home Assistant не запускается после импорта диска.**
Проверь порядок загрузки: VM → Options → Boot Order — HAOS диск должен быть первым. Убедись что EFI disk добавлен в Hardware (без него UEFI VM не запустится).

**Nextcloud выдаёт ошибку "Trusted domain is not allowed".**
В `docker-compose.yml` переменная `NEXTCLOUD_TRUSTED_DOMAINS` должна содержать все домены через пробел: IP контейнера, локальный домен и внешний домен NPM. Пересоздай контейнер или добавь домен через `occ`:
```bash
docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:set trusted_domains 2 --value="cloud.homeserver.duckdns.org"
```

**NPM не может получить сертификат Let's Encrypt.**
Проверь правильность токена DuckDNS. Убедись что субдомен существует в аккаунте DuckDNS. Let's Encrypt имеет лимит на количество попыток — подожди час перед повторной попыткой.

**Home Assistant отдаёт 400 Bad Request через NPM.**
Добавь в `configuration.yaml` секцию `http` с `trusted_proxies` — IP контейнера NPM. Перезагрузи конфигурацию HA: Developer Tools → Services → `homeassistant.reload_core_config`.

**Jellyfin не может воспроизвести видео.**
Если видео требует транскодирования, а CPU слабый — рассмотри passthrough встроенной графики (глава 10). Для просмотра без транскодирования достаточно прямой трансляции (Direct Play) — убедись что клиент поддерживает нужный кодек.

**LXC с Docker не запускается, ошибка "nesting not enabled".**
Проверь конфигурацию контейнера:
```bash
cat /etc/pve/lxc/100.conf | grep features
# Должно быть: features: keyctl=1,nesting=1
```
Если строки нет — добавь и перезапусти LXC:
```bash
pct stop 100
# Добавь через веб: CT 100 → Options → Features → Nesting ✅, Keyctl ✅
pct start 100
```

---

## Чек-лист для самопроверки

- [ ] Home Assistant OS запущен, веб-интерфейс открывается по IP:8123
- [ ] Nextcloud и Jellyfin работают в Docker LXC, доступны по IP и порту
- [ ] Nginx Proxy Manager установлен, маршрутизирует запросы к сервисам
- [ ] Получен Let's Encrypt сертификат через DuckDNS, браузер показывает зелёный замок
- [ ] Понимаю почему self-signed сертификаты не подходят для мобильных приложений
- [ ] Итоговая схема сервера задокументирована с IP-адресами и портами
