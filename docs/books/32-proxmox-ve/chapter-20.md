# Глава 20: Итоговый проект

> **Цель:** собрать всё из книги в один работающий сервер — от чистого железа до полноценной инфраструктуры с бэкапами, мониторингом и удалённым доступом.

---

## Что вы узнаете

- как за один вечер поднять сервер от нуля до всех сервисов;
- как организовать хранилища на двух дисках (SSD + HDD);
- как проверить что каждый шаг сделан правильно;
- критерии «книга прочитана» — чёткий список что должно работать.

---

## 20.1 Описание сценария

Оборудование: мини-ПК типа Intel NUC, Beelink или Minisforum.

```
Железо:
  RAM: 16GB (например 2×8GB SO-DIMM DDR4/DDR5)
  SSD: 512GB NVMe (системный диск — Proxmox + контейнеры)
  HDD: 2TB SATA 2.5" (бэкапы + медиафайлы)
  Сеть: Gigabit Ethernet
  ОС до этого: чистое железо или Ubuntu — всё сотрётся
```

Что должно получиться на выходе:

```
Proxmox Host (192.168.1.100)
├── CT 100: Docker LXC (3GB RAM) — Nextcloud :8080, Vaultwarden :8085
├── CT 101: Nginx Proxy Manager (512MB) — HTTPS + Let's Encrypt
├── CT 102: Uptime Kuma (256MB) — мониторинг + Telegram уведомления
├── VM 200: Home Assistant OS (2GB balloon) — умный дом
├── SSD 512GB: local-lvm — системный диск (VM и LXC)
├── HDD 2TB: backup-hdd — бэкапы + медиа (Directory-хранилище)
├── Backup: ежедневно 03:00, 7 daily + 4 weekly копий
└── Tailscale → доступ с телефона из любой точки
```

Почему именно такой набор: каждый контейнер делает одну вещь. Docker LXC — пространство для сервисов. Nginx PM — единая точка входа с SSL. Uptime Kuma — сторожевой пёс. Home Assistant — умный дом в изолированной VM.

---

## 20.2 Задание 1: Установить Proxmox VE

**Что делаем:** устанавливаем Proxmox VE на SSD, отключаем платный репозиторий, обновляем систему.

**Шаги:**

1. Скачать ISO с https://www.proxmox.com/en/downloads/proxmox-virtual-environment — раздел ISO Images, последняя версия Proxmox VE.
2. Записать на флешку: Balena Etcher (Windows/Mac/Linux) или Rufus (Windows).
3. Включить виртуализацию в BIOS: VT-x (Intel) или AMD-V (AMD). Обычно называется «Intel Virtualization Technology» или «SVM Mode».
4. Загрузиться с флешки, в установщике выбрать SSD как целевой диск (512GB).
5. Задать статический IP: 192.168.1.100/24, шлюз 192.168.1.1, DNS 8.8.8.8.
6. Задать пароль root и email (для уведомлений от Proxmox).
7. После установки открыть: `https://192.168.1.100:8006` — браузер покажет предупреждение о сертификате, добавить исключение и войти.

После установки — в Shell хоста:

```bash
# Отключить enterprise-репозиторий (платный, без подписки выдаёт ошибки)
sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/pve-enterprise.list

# Если есть файл ceph enterprise репозитория — отключить его тоже
sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/ceph.list 2>/dev/null || true

# Подключить бесплатный репозиторий (без подписки)
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" \
  > /etc/apt/sources.list.d/pve-no-subscription.list

# Обновить систему — занимает 2-5 минут, это нормально
apt update && apt full-upgrade -y

# Проверить версию после обновления
pveversion
```

**Проверка:**

```bash
pveversion
# Должно быть что-то вроде: pve-manager/8.x.x
```

---

## 20.3 Задание 2: Добавить HDD как хранилище для бэкапов

**Что делаем:** HDD 2TB подключаем как Directory-хранилище. На нём будут храниться бэкапы и (при желании) медиафайлы для Jellyfin.

Почему Directory, а не LVM-Thin: бэкапы — это файлы `.tar.zst`. Directory-хранилище работает как обычная папка — просто, надёжно, файлы можно скопировать на другой диск без специальных инструментов.

**Шаги:**

```bash
# Найти новый диск (обычно /dev/sdb если SSD — /dev/sda или /dev/nvme0n1)
lsblk
# Пример вывода:
# NAME        MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
# sda           8:0    0  1.8T  0 disk
# nvme0n1     259:0    0  477G  0 disk
#   nvme0n1p1 259:1    0  477G  0 part /

# Создать таблицу разделов GPT и раздел на весь диск
parted /dev/sda mklabel gpt
parted /dev/sda mkpart primary 0% 100%

# Отформатировать в ext4
mkfs.ext4 /dev/sda1

# Создать точку монтирования и смонтировать
mkdir -p /mnt/backup-hdd
echo "/dev/sda1 /mnt/backup-hdd ext4 defaults,nofail 0 2" >> /etc/fstab
mount -a

# Проверить что диск смонтирован
df -h /mnt/backup-hdd
# Должно показать ~1.8TB свободного места
```

Теперь добавить хранилище в Proxmox через веб-интерфейс:

```
Datacenter → Storage → Add → Directory
  ID: backup-hdd
  Directory: /mnt/backup-hdd
  Content: VZDump backup file, Container template, ISO image
```

После добавления хранилище появится в левой панели под узлом.

---

## 20.4 Задание 3: Создать Docker LXC

**Что делаем:** создаём LXC-контейнер с Docker через Community Scripts — это самый быстрый способ. Затем разберём что именно создал скрипт.

**Через Community Scripts (рекомендуется):**

```bash
# На хосте Proxmox в Shell — скрипт создаст LXC и установит Docker+Portainer
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"
```

Скрипт спросит несколько параметров — оставить значения по умолчанию или настроить вручную. Обычно он создаёт контейнер с ID 100.

**Если скрипт недоступен — вручную:**

```bash
# 1. Скачать шаблон Debian 12
pveam update
pveam download local debian-12-standard_12.7-1_amd64.tar.zst

# 2. Создать privileged LXC (нужен для Docker — unprivileged контейнеры
#    не поддерживают все функции Docker без сложных настроек)
pct create 100 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname docker-01 \
  --memory 3072 \
  --cores 4 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.101/24,gw=192.168.1.1,type=veth \
  --storage local-lvm \
  --rootfs local-lvm:20 \
  --unprivileged 0 \
  --features keyctl=1,nesting=1 \
  --start 1

# 3. Войти в контейнер и установить Docker
pct enter 100
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
exit
```

Установить лимит памяти 3GB через веб-интерфейс: CT 100 → Hardware → Memory → 3072 MB.

**Проверка:**

```bash
pct exec 100 -- docker run hello-world
# Должно появиться сообщение "Hello from Docker!"

pct exec 100 -- docker ps
pct list
# CT 100 должен быть в статусе running
```

---

## 20.5 Задание 4: Запустить Nextcloud в Docker LXC

**Что делаем:** запускаем Nextcloud — файловое облако — внутри Docker LXC из задания 3.

Nextcloud будет доступен по порту 8080 на IP контейнера (192.168.1.101:8080). В следующем задании настроим красивый HTTPS-домен через Nginx PM.

```bash
# Войти в Docker LXC
pct enter 100

# Создать директорию для данных
mkdir -p /opt/nextcloud

# Запустить Nextcloud через Docker
docker run -d \
  --name nextcloud \
  --restart unless-stopped \
  -p 8080:80 \
  -v /opt/nextcloud/data:/var/www/html \
  nextcloud:latest

# Проверить что запустился
docker ps
# Должен быть контейнер nextcloud в статусе Up

exit
```

Открыть в браузере: `http://192.168.1.101:8080` — откроется мастер первоначальной настройки Nextcloud. Создать учётную запись администратора.

Дополнительно — запустить Vaultwarden (менеджер паролей):

```bash
pct enter 100
docker run -d \
  --name vaultwarden \
  --restart unless-stopped \
  -p 8085:80 \
  -v /opt/vaultwarden:/data \
  vaultwarden/server:latest
exit
```

---

## 20.6 Задание 5: Установить Nginx Proxy Manager

**Что делаем:** создаём отдельный LXC для Nginx Proxy Manager. Он будет принимать весь входящий трафик на портах 80 и 443 и перенаправлять его к нужным сервисам.

Зачем отдельный контейнер: NPM управляет TLS-сертификатами и трафиком. Отделить его от Docker LXC — значит что проблема с одним не затронет другой.

**Через Community Scripts:**

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/nginx-proxy-manager.sh)"
```

**Вручную (если скрипт недоступен):**

```bash
# Создать LXC для NPM
pct create 101 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname nginx-pm \
  --memory 512 \
  --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.102/24,gw=192.168.1.1,type=veth \
  --storage local-lvm \
  --rootfs local-lvm:5 \
  --unprivileged 0 \
  --features nesting=1 \
  --start 1

# Установить Docker и NPM
pct enter 101
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

mkdir -p /opt/npm && cd /opt/npm
cat > docker-compose.yml << 'EOF'
services:
  npm:
    image: jc21/nginx-proxy-manager:latest
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "81:81"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
EOF
docker compose up -d
exit
```

Открыть веб-интерфейс NPM: `http://192.168.1.102:81`

Данные по умолчанию:
- Email: `admin@example.com`
- Password: `changeme`

Сменить пароль при первом входе.

---

## 20.7 Задание 6: Получить Let's Encrypt сертификат

**Что делаем:** настраиваем бесплатный HTTPS-домен через DuckDNS и Let's Encrypt. После этого Nextcloud будет доступен по `https://nextcloud.myserver.duckdns.org` с зелёным замком.

**Шаг 1: Получить домен DuckDNS**

1. Зайти на https://www.duckdns.org и войти через Google/GitHub.
2. Создать поддомен, например `myserver` → получите `myserver.duckdns.org`.
3. Скопировать токен (строка вида `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

**Шаг 2: Настроить Proxy Host в NPM**

В NPM → Hosts → Proxy Hosts → Add Proxy Host:

```
Domain Names: nextcloud.myserver.duckdns.org
Forward Hostname: 192.168.1.101
Forward Port: 8080
```

Вкладка SSL:
```
SSL Certificate: Request a new SSL Certificate
Email: ваш@email.com
DNS Challenge: DuckDNS
DuckDNS Token: ваш-токен
```

NPM автоматически запросит сертификат через Let's Encrypt (DNS-01 challenge — работает даже без открытого порта 80 в интернете).

После сохранения: `https://nextcloud.myserver.duckdns.org` откроется с зелёным замком.

**Проверка:**

Открыть в браузере `https://nextcloud.myserver.duckdns.org` — должен открыться Nextcloud без предупреждений о сертификате.

---

## 20.8 Задание 7: Установить Tailscale на хост

**Что делаем:** устанавливаем Tailscale на хост Proxmox. После этого заходить в веб-интерфейс Proxmox и все сервисы можно с телефона или ноутбука из любой точки — без открытых портов в интернет.

```bash
# Установить Tailscale на хост Proxmox
curl -fsSL https://tailscale.com/install.sh | sh

# Авторизоваться — откроется ссылка для входа через браузер
tailscale up

# Узнать Tailscale IP (начинается с 100.x.x.x)
tailscale ip -4

# Открыть доступ ко всей домашней сети через subnet routing
# После этой команды в admin-консоли Tailscale нужно одобрить маршрут
tailscale up --advertise-routes=192.168.1.0/24
```

Одобрить маршрут: https://login.tailscale.com/admin/machines → найти свой хост → Edit route settings → включить `192.168.1.0/24`.

**Проверка:**

1. Открыть Tailscale на телефоне (приложение).
2. Подключиться к сети.
3. Открыть в мобильном браузере: `https://100.x.x.x:8006` (Tailscale IP вместо x.x.x).
4. Веб-интерфейс Proxmox должен открыться.

---

## 20.9 Задание 8: Настроить автоматические бэкапы

**Что делаем:** настраиваем ежедневные бэкапы всех контейнеров и VM на HDD-хранилище с расписанием и автоматической очисткой старых копий.

Через веб-интерфейс: Datacenter → Backup → Add

```
Storage: backup-hdd
Schedule: 03:00
Mode: Snapshot (не останавливает контейнер)
Compression: ZSTD (лучшее сжатие)
All VMs and CTs: включить

Retention:
  Keep Last: 1
  Keep Daily: 7
  Keep Weekly: 4
  Keep Monthly: 2
```

Почему Snapshot mode: контейнер не останавливается, сервис доступен во время бэкапа. Минус — есть минимальный риск незаконченных транзакций в БД. Для критичных данных (PostgreSQL, MySQL) использовать Stop mode.

Проверить расписание — оно должно появиться в списке с временем следующего запуска.

**Ручной тест бэкапа:**

```bash
# Запустить бэкап CT 100 прямо сейчас вручную (не ждать 03:00)
vzdump 100 --compress zstd --storage backup-hdd --mode snapshot

# Посмотреть что сохранилось
ls -lh /mnt/backup-hdd/dump/
# Должен появиться файл vzdump-lxc-100-YYYY_MM_DD-HH_MM_SS.tar.zst
```

**Проверка восстановления (обязательно):**

```bash
# Восстановить CT 100 под тестовым ID 999 — не трогает рабочий контейнер
pct restore 999 /mnt/backup-hdd/dump/vzdump-lxc-100-*.tar.zst \
  --storage local-lvm --hostname test-restore

# Запустить тестовый контейнер
pct start 999

# Проверить что данные на месте
pct exec 999 -- docker ps      # контейнеры Docker должны быть видны
pct exec 999 -- df -h          # данные на месте

# Удалить тестовый контейнер после проверки
pct stop 999 && pct destroy 999
```

Правило: непроверенный бэкап — не бэкап. Делать тестовое восстановление раз в месяц.

---

## 20.10 Задание 9: Снапшот, поломка, откат

**Что делаем:** на практике проверяем как работают снапшоты — делаем снапшот, ломаем что-то внутри, откатываем.

Этот сценарий моделирует реальную ситуацию: «собирался обновить приложение, что-то пошло не так».

```bash
# Шаг 1: Убедиться что CT 100 запущен и всё работает
pct status 100
pct exec 100 -- docker ps

# Шаг 2: Остановить CT 100 (снапшот LXC требует остановленного контейнера
#         если на LVM-Thin — можно и на работающем, но надёжнее остановить)
pct stop 100

# Шаг 3: Сделать снапшот с описанием
pct snapshot 100 before-nextcloud-update \
  --description "Перед обновлением Nextcloud $(date +%Y-%m-%d)"

# Убедиться что снапшот создан
pct listsnapshot 100
# Должен показать: before-nextcloud-update

# Шаг 4: Запустить CT 100 и сломать что-нибудь внутри
pct start 100
pct exec 100 -- bash -c "docker stop nextcloud && docker rm nextcloud"
pct exec 100 -- bash -c "rm -rf /opt/nextcloud"

# Проверить — Nextcloud не работает
pct exec 100 -- docker ps
# nextcloud пропал из списка

# Шаг 5: Откатить снапшот
pct stop 100
pct rollback 100 before-nextcloud-update

# Шаг 6: Запустить и проверить что всё восстановилось
pct start 100
sleep 15   # подождать пока Docker запустит контейнеры

pct exec 100 -- docker ps
# nextcloud снова в списке
```

Открыть в браузере `http://192.168.1.101:8080` — Nextcloud должен снова работать.

---

## 20.11 Задание 10: Мониторинг и Telegram-уведомления

**Что делаем:** устанавливаем Uptime Kuma для мониторинга сервисов и настраиваем три cron-скрипта на хосте для автоматических проверок с уведомлениями в Telegram.

**Установить Uptime Kuma:**

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptimekuma.sh)"
```

Скрипт создаст CT 102 с Uptime Kuma. Открыть: `http://192.168.1.103:3001` (IP зависит от DHCP, проверить через `pct list`).

В Uptime Kuma добавить мониторы:
- Nextcloud: `http://192.168.1.101:8080` → тип HTTP(s)
- Nginx PM: `http://192.168.1.102:81` → тип HTTP(s)
- Proxmox: `https://192.168.1.100:8006` → тип HTTP(s), игнорировать cert

**Настроить Telegram-бота:**

```bash
# 1. Создать бота: в Telegram написать @BotFather → /newbot
# 2. Получить TOKEN (длинная строка)
# 3. Написать боту что-нибудь, затем получить chat_id:
#    curl https://api.telegram.org/botТВОЙ_ТОКЕН/getUpdates

# Создать скрипт уведомлений
cat > /usr/local/bin/tg-notify << 'EOF'
#!/bin/bash
TOKEN="вставить_токен_сюда"
CHAT_ID="вставить_chat_id_сюда"
curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=$1" \
  -d "parse_mode=HTML" > /dev/null
EOF
chmod +x /usr/local/bin/tg-notify

# Проверить что работает
tg-notify "✅ Proxmox настроен на $(hostname)"
```

**Три cron-скрипта:**

```bash
# Скрипт 1: healthcheck — перезапустить упавший контейнер и уведомить
cat > /usr/local/bin/pve-healthcheck << 'EOF'
#!/bin/bash
# Список ID контейнеров которые должны быть running
REQUIRED_CTS="100 101 102"

for CT_ID in $REQUIRED_CTS; do
  STATUS=$(pct status $CT_ID 2>/dev/null | awk '{print $2}')
  if [ "$STATUS" != "running" ]; then
    echo "$(date): CT $CT_ID is $STATUS, restarting..." >> /var/log/pve-healthcheck.log
    pct start $CT_ID
    sleep 10
    NEW_STATUS=$(pct status $CT_ID | awk '{print $2}')
    if [ "$NEW_STATUS" != "running" ]; then
      tg-notify "🔴 ALERT: CT $CT_ID не запустился на $(hostname)"
    else
      tg-notify "🟡 WARNING: CT $CT_ID упал, перезапущен автоматически"
    fi
  fi
done
EOF
chmod +x /usr/local/bin/pve-healthcheck

# Скрипт 2: diskcheck — алерт когда диск заполнен > 85%
cat > /usr/local/bin/pve-diskcheck << 'EOF'
#!/bin/bash
THRESHOLD=85

while IFS= read -r line; do
  USE=$(echo "$line" | awk '{print $5}' | tr -d '%')
  MOUNT=$(echo "$line" | awk '{print $6}')
  if [ "$USE" -gt "$THRESHOLD" ] 2>/dev/null; then
    tg-notify "⚠️ Диск ${MOUNT} заполнен на ${USE}% на $(hostname)"
  fi
done < <(df -h | tail -n +2)
EOF
chmod +x /usr/local/bin/pve-diskcheck

# Скрипт 3: ежедневный отчёт каждое утро в 09:00
cat > /usr/local/bin/pve-dailyreport << 'EOF'
#!/bin/bash
CT_COUNT=$(pct list | grep running | wc -l)
VM_COUNT=$(qm list | grep running | wc -l)
RAM_USED=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
DISK_ROOT=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')
DISK_HDD=$(df -h /mnt/backup-hdd | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}' 2>/dev/null || echo "N/A")

tg-notify "📊 <b>Proxmox Daily — $(hostname)</b>
Uptime: $(uptime -p)
RAM: ${RAM_USED}
SSD: ${DISK_ROOT}
HDD: ${DISK_HDD}
Running: ${CT_COUNT} CT, ${VM_COUNT} VM"
EOF
chmod +x /usr/local/bin/pve-dailyreport

# Добавить в cron
echo "*/5 * * * * root /usr/local/bin/pve-healthcheck" > /etc/cron.d/pve-healthcheck
echo "0 8 * * * root /usr/local/bin/pve-diskcheck" > /etc/cron.d/pve-diskcheck
echo "0 9 * * * root /usr/local/bin/pve-dailyreport" > /etc/cron.d/pve-dailyreport
```

**Проверка:**

```bash
# Запустить вручную чтобы не ждать cron
/usr/local/bin/pve-dailyreport
# В Telegram должен прийти отчёт с данными о системе
```

---

## 20.12 Задание 11: Idempotent bash-скрипт создания Docker LXC

**Что делаем:** пишем bash-скрипт, который создаёт Docker LXC воспроизводимо. Главное свойство — idempotent: запустить дважды безопасно, второй запуск ничего лишнего не сделает.

Зачем это нужно: если придётся переносить сервер — запустил скрипт и всё готово. Нет записей «как именно я кликал в интерфейсе».

```bash
cat > /usr/local/bin/create-docker-lxc.sh << 'EOF'
#!/bin/bash
# create-docker-lxc.sh — idempotent скрипт создания Docker LXC
# Запускать повторно безопасно: если LXC существует — не пересоздаёт

set -e

VMID=100
HOSTNAME="docker-01"
MEMORY=3072
CORES=4
STORAGE="local-lvm"
DISK_SIZE=20
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
IP="192.168.1.101/24"
GW="192.168.1.1"

echo "=== Docker LXC Setup: CT $VMID ==="

# Шаг 1: Проверить что шаблон скачан
if ! pveam list local | grep -q "debian-12-standard"; then
  echo "Скачиваю шаблон Debian 12..."
  pveam download local debian-12-standard_12.7-1_amd64.tar.zst
fi

# Шаг 2: Создать LXC если не существует
if pct status $VMID &>/dev/null; then
  echo "LXC $VMID уже существует, пропускаю создание"
else
  echo "Создаю LXC $VMID..."
  pct create $VMID $TEMPLATE \
    --hostname $HOSTNAME \
    --memory $MEMORY \
    --cores $CORES \
    --net0 name=eth0,bridge=vmbr0,ip=$IP,gw=$GW,type=veth \
    --storage $STORAGE \
    --rootfs $STORAGE:$DISK_SIZE \
    --unprivileged 0 \
    --features keyctl=1,nesting=1
  echo "LXC $VMID создан"
fi

# Шаг 3: Запустить если не запущен
STATUS=$(pct status $VMID | awk '{print $2}')
if [ "$STATUS" != "running" ]; then
  echo "Запускаю LXC $VMID..."
  pct start $VMID
  sleep 10
fi

# Шаг 4: Установить Docker если не установлен
if ! pct exec $VMID -- which docker &>/dev/null; then
  echo "Устанавливаю Docker в LXC $VMID..."
  pct exec $VMID -- bash -c "apt update -qq && apt install -y curl"
  pct exec $VMID -- bash -c "curl -fsSL https://get.docker.com | sh"
  pct exec $VMID -- systemctl enable --now docker
  echo "Docker установлен"
else
  echo "Docker уже установлен"
fi

echo ""
echo "=== Готово ==="
pct status $VMID
pct exec $VMID -- docker --version
EOF

chmod +x /usr/local/bin/create-docker-lxc.sh
```

**Проверка idempotентности:**

```bash
# Первый запуск — создаёт всё с нуля
/usr/local/bin/create-docker-lxc.sh

# Второй запуск — ничего лишнего не делает, только проверяет
/usr/local/bin/create-docker-lxc.sh
# Должно вывести: "LXC 100 уже существует, пропускаю создание"
# и "Docker уже установлен"
```

---

## 20.13 Задание 12: /etc/pve в Git

**Что делаем:** помещаем конфигурацию Proxmox под контроль версий. `/etc/pve/` — это вся конфигурация сервера: параметры контейнеров, VM, сети, хранилищ.

```bash
# Установить git если не установлен
apt install -y git

# Перейти в каталог конфигурации и инициализировать репозиторий
cd /etc/pve
git init
git config user.email "admin@proxmox.local"
git config user.name "Proxmox Admin"

# Первый коммит — состояние после настройки
git add .
git commit -m "initial: proxmox setup with docker-lxc and nginx-pm $(date +%Y-%m-%d)"

# Посмотреть что зафиксировано
git log --oneline
git show HEAD --stat
```

После каждого значимого изменения — делать коммит:

```bash
# Пример: добавили VM с Home Assistant
git add -A && git commit -m "add vm-200 home-assistant-os"

# Изменили память Docker LXC
git add -A && git commit -m "docker-lxc: increase memory to 4GB"

# Проверить историю
git log --oneline
```

История коммитов — это документация сервера. Через год можно вспомнить что именно и когда менялось.

---

## 20.14 Финальная схема сервера

После выполнения всех 12 заданий сервер выглядит так:

```
Proxmox VE 8.x (192.168.1.100 / Tailscale 100.x.x.x)
│
├── STORAGE
│   ├── local-lvm (SSD 512GB) — VM и LXC диски
│   └── backup-hdd (HDD 2TB) — бэкапы + медиа
│
├── CONTAINERS
│   ├── CT 100: docker-01 (3GB RAM, 4 CPU, 20GB SSD)
│   │   ├── nextcloud:latest → порт 8080
│   │   └── vaultwarden:latest → порт 8085
│   │
│   ├── CT 101: nginx-pm (512MB, 1 CPU, 5GB SSD)
│   │   ├── → cloud.myserver.duckdns.org → CT100:8080
│   │   └── → vault.myserver.duckdns.org → CT100:8085
│   │       Let's Encrypt wildcard, автообновление
│   │
│   └── CT 102: uptime-kuma (256MB, 1 CPU, 4GB SSD)
│       ├── мониторинг CT 100, CT 101
│       └── Telegram уведомления
│
├── VIRTUAL MACHINES
│   └── VM 200: Home Assistant OS (2GB balloon, 2 CPU, 32GB SSD)
│       └── ha.myserver.duckdns.org → VM200:8123
│
├── BACKUP (ежедневно 03:00)
│   ├── vzdump CT 100, 101, 102 → backup-hdd
│   ├── vzdump VM 200 → backup-hdd
│   └── Retention: 7 daily, 4 weekly, 2 monthly
│
├── MONITORING (cron на хосте)
│   ├── */5 min: healthcheck CT 100/101/102 → Telegram
│   ├── 08:00: diskcheck SSD+HDD → Telegram если > 85%
│   └── 09:00: daily report → Telegram
│
├── ACCESS
│   ├── LAN: https://192.168.1.100:8006 (только из дома)
│   ├── Remote: https://100.x.x.x:8006 (через Tailscale)
│   └── Public: https://*.myserver.duckdns.org (Let's Encrypt)
│
└── INFRASTRUCTURE AS CODE
    ├── /etc/pve → git (история всех изменений конфигурации)
    └── /usr/local/bin/create-docker-lxc.sh (воспроизводимое создание LXC)
```

---

## 20.15 Критерии «книга прочитана»

Книга прочитана, если вы можете поставить галочки напротив всех пунктов:

**Понимание концепций:**

- [ ] Могу объяснить зачем Proxmox если есть Ubuntu с Docker (изоляция, снапшоты, бэкапы)
- [ ] Понимаю разницу: KVM VM vs LXC-контейнер vs Docker-контейнер
- [ ] Знаю когда использовать LVM-Thin, а когда ZFS — и почему
- [ ] Понимаю разницу снапшот vs бэкап — и что первый не заменяет второй

**Базовые навыки:**

- [ ] Установил Proxmox VE на реальное железо, зашёл в веб-интерфейс
- [ ] Создал LXC-контейнер командой `pct create` с нужными параметрами
- [ ] Создал KVM VM, установил qemu-guest-agent, IP виден в Proxmox
- [ ] Установил Docker в LXC и запустил контейнер через `docker run`

**Реальные сервисы:**

- [ ] Хотя бы один сервис (Nextcloud, Home Assistant, Jellyfin) работает и открывается в браузере
- [ ] Nginx Proxy Manager настроен и проксирует хотя бы один сервис
- [ ] HTTPS сертификат Let's Encrypt получен — в браузере зелёный замок

**Надёжность:**

- [ ] Автоматические бэкапы по расписанию работают
- [ ] Тестовое восстановление из бэкапа под ID 999 выполнено и проверено
- [ ] Снапшот сделан, что-то сломано, снапшот откатил всё обратно

**Доступность:**

- [ ] Tailscale установлен на хост, веб-интерфейс открывается через Tailscale IP с телефона

**Автоматизация:**

- [ ] Три cron-скрипта работают: healthcheck, diskcheck, dailyreport
- [ ] Telegram уведомления приходят ежедневно (проверить вручную `/usr/local/bin/pve-dailyreport`)
- [ ] Написан idempotent bash-скрипт создания LXC — запущен дважды, второй раз ничего лишнего не сделал
- [ ] `/etc/pve` под контролем git, есть минимум 3 коммита с осмысленными сообщениями

---

## Чек-лист для самопроверки

- [ ] Proxmox установлен, обновлён, enterprise-репозиторий отключён
- [ ] HDD добавлен как backup-hdd, бэкапы пишутся туда
- [ ] Docker LXC работает, Nextcloud открывается по HTTPS с зелёным замком
- [ ] Nginx Proxy Manager проксирует сервисы
- [ ] Home Assistant OS запущен в VM 200
- [ ] Tailscale: вхожу в Proxmox с телефона без VPN
- [ ] Бэкапы по расписанию: тестовое восстановление под ID 999 пройдено
- [ ] Снапшот: сделал, сломал, откатил — всё работает
- [ ] Telegram уведомления: приходит ежедневный отчёт
- [ ] /etc/pve в git, скрипт создания LXC написан и проверен дважды
