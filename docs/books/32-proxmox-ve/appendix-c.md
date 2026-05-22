# Приложение C: Схемы типовых домашних серверов

> Три варианта конфигурации для разного уровня железа. Выбрать подходящий и использовать как основу для своего сервера.

---

## C.1 Вариант Budget — мини-ПК начального уровня

**Железо:** 4–6 GB RAM, один SSD 128–256 GB, нет HDD.

Типичные устройства: старый NUC, мини-ПК за 5–8 тысяч рублей, старый ноутбук без батарейки.

**Когда выбирать этот вариант:**
- Начинаете с Proxmox и хотите разобраться без серьёзных вложений.
- Нужен только Home Assistant или один-два небольших сервиса.
- Нет критичных данных — потеря не катастрофа.

**Схема контейнеров:**

```
Proxmox Host (192.168.1.100)
│
├── VM 200: Home Assistant OS (1GB balloon, 2 CPU, 32GB)
│   └── Умный дом: устройства, автоматизации, дашборды
│
├── CT 101: AdGuard Home (256MB, 1 CPU, 2GB)
│   └── DNS для всей сети, блокировка рекламы
│
└── CT 102: Uptime Kuma (256MB, 1 CPU, 4GB)
    └── Мониторинг HA и AdGuard + Telegram уведомления
```

**Таблица ресурсов:**

| Контейнер | RAM лимит | CPU | Диск | Сервис |
|-----------|-----------|-----|------|--------|
| VM 200: HA OS | 1 GB (min 512 MB) | 2 | 32 GB | Home Assistant |
| CT 101: AdGuard | 256 MB | 1 | 2 GB | DNS + блокировка рекламы |
| CT 102: Uptime Kuma | 256 MB | 1 | 4 GB | Мониторинг |
| **Хост Proxmox** | ~500 MB | — | ~8 GB | Система |
| **ИТОГО** | ~2 GB | 4 | ~46 GB | — |

Остаток RAM: ~2–4 GB свободно — хороший запас для стабильной работы.

**Хранилище:**

```
SSD 128/256 GB → LVM-Thin (local-lvm)
  ├── VM-диски и LXC-диски
  └── Нет второго диска → бэкапы на USB-накопитель

Бэкап-стратегия:
  Раз в неделю вручную: vzdump --all --compress zstd --storage local
  Скопировать файлы бэкапа на USB-флешку или внешний диск
```

**Особенности и ограничения:**

- Нет автоматических ежедневных бэкапов — только ручные, только если не забудете.
- ZFS не рекомендуется: ARC-кэш ZFS требует ~500 MB+ RAM, при 4–6 GB это ощутимо.
- Вместо Nextcloud — только AdGuard и HA: не хватит места и RAM для полноценного облака.
- Home Assistant с balloon-memory: стартует с 512 MB, растёт до 1 GB по мере надобности.

**Настройка DNS в роутере:**

Чтобы AdGuard Home работал для всей сети — указать в настройках DHCP роутера DNS-сервер: `192.168.1.101` (IP контейнера AdGuard). Все устройства в сети автоматически получат этот DNS и будут защищены от рекламы.

**Итоговая оценка:** минимальный работающий сервер. Умный дом + блокировка рекламы + мониторинг. Хорошая точка входа в Proxmox.

---

## C.2 Вариант Standard — 16 GB RAM, SSD + HDD

**Железо:** 16 GB RAM, SSD 512 GB NVMe, HDD 2 TB SATA.

Типичные устройства: Intel NUC 12/13 Pro, Beelink EQ/SER серии, Minisforum UM серии.

**Когда выбирать этот вариант:**
- Хотите полноценный домашний сервер с несколькими сервисами.
- Нужны файловое облако, медиасервер, умный дом в одном месте.
- Важны автоматические бэкапы.

**Схема контейнеров:**

```
Proxmox Host (192.168.1.100)
│
├── CT 100: Docker LXC (3GB RAM, 4 CPU, 20GB SSD)
│   ├── Nextcloud → порт 8080 (файловое облако)
│   ├── Vaultwarden → порт 8085 (менеджер паролей)
│   └── Portainer → порт 9000 (управление Docker)
│
├── CT 101: Nginx Proxy Manager (512MB, 1 CPU, 5GB SSD)
│   ├── cloud.myserver.duckdns.org → CT100:8080
│   ├── vault.myserver.duckdns.org → CT100:8085
│   └── ha.myserver.duckdns.org → VM200:8123
│       Let's Encrypt через DuckDNS, автообновление
│
├── CT 102: AdGuard Home (256MB, 1 CPU, 2GB SSD)
│   └── DNS для всей сети: 192.168.1.103
│
├── CT 103: Uptime Kuma (256MB, 1 CPU, 4GB SSD)
│   └── Мониторинг всех сервисов + Telegram уведомления
│
├── VM 200: Home Assistant OS (2GB balloon, 2 CPU, 32GB SSD)
│   └── Умный дом (рекомендуется изолировать в VLAN 30)
│
└── HDD 2TB → backup-hdd (Directory)
    ├── Ежедневные бэкапы CT 100, 101, 102, 103
    ├── Ежедневные бэкапы VM 200
    └── Медиафайлы для Jellyfin (опционально, /mnt/media)
```

**Таблица ресурсов:**

| Контейнер | RAM лимит | CPU | Диск | Сервис |
|-----------|-----------|-----|------|--------|
| CT 100: Docker LXC | 3 GB | 4 | 20 GB SSD | Nextcloud, Vaultwarden |
| CT 101: Nginx PM | 512 MB | 1 | 5 GB SSD | Reverse proxy + TLS |
| CT 102: AdGuard | 256 MB | 1 | 2 GB SSD | DNS + реклама |
| CT 103: Uptime Kuma | 256 MB | 1 | 4 GB SSD | Мониторинг |
| VM 200: HA OS | 2 GB balloon | 2 | 32 GB SSD | Home Assistant |
| **Хост Proxmox** | ~500 MB | — | ~8 GB | Система |
| **ИТОГО SSD** | ~6.5 GB RAM | 9 | ~71 GB | — |
| **HDD 2TB** | — | — | 2 TB | Бэкапы + медиа |

Остаток RAM: ~9 GB свободно — можно добавить Jellyfin или другой сервис.

**Хранилище:**

```
SSD 512GB → LVM-Thin (local-lvm)
  ├── Диски VM и LXC (71GB используется)
  └── ~430GB свободно — место для роста

HDD 2TB → Directory (backup-hdd)
  ├── /mnt/backup-hdd/dump/ — файлы vzdump бэкапов
  └── /mnt/backup-hdd/media/ — медиафайлы Jellyfin (опционально)
```

**Стратегия бэкапов:**

```
Расписание: ежедневно 03:00
Хранилище: backup-hdd
Retention:
  Keep Daily:   7   (неделя ежедневных копий)
  Keep Weekly:  4   (месяц еженедельных)
  Keep Monthly: 2   (два месяца)

Место на HDD:
  CT 100 (Docker) ~5-8 GB × 7 daily = ~50-60 GB
  VM 200 (HAOS) ~3-5 GB × 7 daily = ~20-35 GB
  Прочие CT ~1 GB × 7 = ~7 GB
  ИТОГО: ~100-110 GB под бэкапы, ~1.9 TB остаётся под медиа
```

**Особенности:**

- LVM-Thin на SSD: снапшоты работают, хорошая производительность, просто в управлении.
- ZFS не нужен: один SSD → нет смысла в RAID, RAM достаточно для работы без ZFS-кэша.
- Home Assistant в VM: официально поддерживаемый способ, все Supervisor add-ons работают.
- Выход в интернет через NPM + DuckDNS + Let's Encrypt: бесплатный HTTPS без публичного IP.
- Tailscale на хосте: доступ ко всем сервисам с телефона через Tailscale IP.

**Итоговая оценка:** оптимальный домашний сервер. Покрывает большинство задач домашней сети. Хорошо сбалансирован по ресурсам.

---

## C.3 Вариант Advanced — 32 GB+ RAM, ZFS, GPU passthrough

**Железо:** 32–64 GB RAM, два SSD NVMe (mirror), три HDD (RAIDZ), дискретный GPU.

Типичные устройства: сборка в mini-ITX корпусе, б/у сервер Supermicro, HP ProLiant, Dell PowerEdge.

**Когда выбирать этот вариант:**
- Нужна максимальная надёжность данных (RAID + ZFS checksums).
- Хранится много медиа и нужен аппаратный транскодинг 4K.
- Планируется Windows VM для работы или игр рядом с Linux-сервисами.
- Хотите PBS для экономии места на инкрементальных бэкапах.
- Нужна полная изоляция сетей (VLAN, zero-trust).

**Схема контейнеров:**

```
Proxmox Host (ZFS mirror: 2×SSD NVMe, ZFS RAIDZ: 3×HDD SATA)
│
├── CT 100: Docker LXC (4GB, 4 CPU, ZFS dataset)
│   ├── Nextcloud — файловое облако
│   ├── Vaultwarden — менеджер паролей
│   └── Gitea — self-hosted Git
│
├── CT 101: Nginx Proxy Manager (512MB, 1 CPU)
│   └── wildcard Let's Encrypt *.myserver.duckdns.org
│
├── VM 200: Home Assistant OS (2GB balloon, 2 CPU) [VLAN 30]
│   └── Умный дом в изолированной сети IoT
│
├── VM 201: Windows 11 (8GB balloon, 8 CPU + GPU passthrough)
│   └── Рабочий/игровой Windows без второго физического ПК
│
├── CT 202: Jellyfin (2GB, 4 CPU + GPU passthrough)
│   └── Медиасервер с 4K транскодированием (NVIDIA/AMD)
│
├── CT 203: Netdata (1GB, 2 CPU)
│   └── Мониторинг хоста: CPU, RAM, диски, ZFS метрики
│
├── CT 204: Proxmox Backup Server (2GB, 2 CPU)
│   └── Инкрементальные бэкапы: только дельта изменений
│       PBS datastore на ZFS RAIDZ HDD
│
└── CT 205: AdGuard + Uptime Kuma (512MB, 1 CPU)
    └── DNS + мониторинг всех сервисов
```

**Таблица ресурсов:**

| Контейнер | RAM | CPU | Диск | Особенности |
|-----------|-----|-----|------|-------------|
| CT 100: Docker LXC | 4 GB | 4 | ZFS датасет | Сжатие zstd, snapshots |
| CT 101: Nginx PM | 512 MB | 1 | 5 GB | Wildcard cert |
| VM 200: HA OS | 2 GB balloon | 2 | 32 GB | VLAN 30, IoT изоляция |
| VM 201: Windows 11 | 8 GB balloon | 8 | 128 GB | GPU passthrough полный |
| CT 202: Jellyfin | 2 GB | 4 | 10 GB | GPU passthrough для transcode |
| CT 203: Netdata | 1 GB | 2 | 5 GB | ZFS ARC метрики |
| CT 204: PBS | 2 GB | 2 | HDD pool | Инкрементальные бэкапы |
| CT 205: AdGuard+Kuma | 512 MB | 1 | 4 GB | DNS + мониторинг |
| **Хост Proxmox** | ~1 GB | — | — | ZFS ARC ~4-8 GB |
| **ИТОГО** | ~20 GB | 24 | ZFS | ZFS занимает ~6 GB RAM под ARC |

Остаток RAM: ~6–8 GB — ZFS ARC, ~6 GB реально свободно. При 64 GB остаётся значительный запас.

**Хранилище — ZFS конфигурация:**

```
ZFS mirror (2×SSD NVMe 1TB):
  zpool create ssd-mirror mirror /dev/nvme0n1 /dev/nvme1n1
  zfs set compression=zstd ssd-mirror
  zfs create ssd-mirror/vm-disks     # диски VM
  zfs create ssd-mirror/ct-data      # данные LXC
  → Добавить в Proxmox: Storage → Add → ZFS → ssd-mirror

  Преимущества: RAID1 из двух SSD, если один умрёт — данные сохранятся.
  ZFS compression=zstd: экономит 20-40% места на текстовых данных бесплатно.

ZFS RAIDZ (3×HDD 4TB):
  zpool create hdd-raidz raidz /dev/sda /dev/sdb /dev/sdc
  zfs set compression=lz4 hdd-raidz
  zfs create hdd-raidz/backups      # PBS datastore
  zfs create hdd-raidz/media        # медиафайлы для Jellyfin
  → Добавить в Proxmox: Storage → Add → ZFS → hdd-raidz

  RAIDZ = один диск может упасть, данные сохранятся.
  Итоговый размер: 2×4TB (8TB из 12TB — треть уходит на избыточность).
```

**GPU passthrough — настройка:**

```bash
# 1. Включить IOMMU в GRUB
# Intel:
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
# AMD:
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"
update-grub && reboot

# 2. Загрузить vfio модули
echo "vfio" >> /etc/modules
echo "vfio_iommu_type1" >> /etc/modules
echo "vfio_pci" >> /etc/modules
echo "vfio_virqfd" >> /etc/modules
update-initramfs -u && reboot

# 3. Blacklist драйвера на хосте (GPU будет только у VM/LXC)
echo "blacklist nouveau" >> /etc/modprobe.d/blacklist.conf
echo "blacklist nvidia" >> /etc/modprobe.d/blacklist.conf
# Для AMD: echo "blacklist amdgpu" >> /etc/modprobe.d/blacklist.conf
update-initramfs -u && reboot

# 4. Добавить GPU в Windows VM:
#    VM 201 (остановить) → Hardware → Add → PCI Device → выбрать GPU
#    Включить "All Functions" и "PCI-Express"

# 5. Для Jellyfin LXC (аппаратный транскодинг):
#    CT 202 → Resources → Add → PCI Device → GPU
#    Внутри LXC установить драйверы (NVIDIA CUDA или VAAPI)
```

**Сеть — VLAN zero-trust:**

```
VLAN 10 — Management (192.168.10.0/24):
  Proxmox :8006, SSH :22
  Доступ: только через Tailscale (100.x.x.x/8)
  Firewall: DROP всё входящее кроме Tailscale

VLAN 20 — Services (192.168.20.0/24):
  Nextcloud, Gitea, Vaultwarden, NPM
  Доступ: LAN + HTTPS через NPM
  Firewall: нет прямого доступа к VLAN 10

VLAN 30 — IoT (192.168.30.0/24):
  Home Assistant, умные устройства, IP-камеры
  Firewall:
    IN  ACCEPT :8123 (HA web)
    IN  ACCEPT :1883 (MQTT)
    OUT DROP   → 192.168.10.0/24 (нет доступа к management)
    OUT DROP   → 192.168.20.0/24 (нет доступа к сервисам)
    OUT ACCEPT → internet (HA нужен интернет для интеграций)
```

**Proxmox Backup Server — инкрементальные бэкапы:**

```
PBS в CT 204 → datastore на hdd-raidz/backups

Настройка в Proxmox:
  Datacenter → Storage → Add → Proxmox Backup Server
  Server: 192.168.20.X (IP CT 204)
  Datastore: backups

Расписание:
  Ежедневно 02:00 — все CT и VM → PBS
  Retention: 14 daily, 8 weekly, 3 monthly

Инкрементальность: первый бэкап полный, далее — только изменения.
Для VM 201 (Windows, 128GB): после первого бэкапа каждый следующий
  занимает 1-5 GB вместо 30-40 GB при обычном vzdump.
```

**Итоговая оценка:**

Этот вариант — серьёзная инфраструктура. Здесь:
- Данные защищены на двух уровнях: ZFS RAID + PBS с дедупликацией.
- Windows VM рядом с Linux — не нужен второй компьютер.
- 4K медиа транскодируется аппаратно — без нагрузки на CPU.
- Сети изолированы: IoT устройства не могут обратиться к серверным сервисам.

Недостатки: дорого в обслуживании (несколько дисков → несколько точек отказа), высокое энергопотребление, сложнее администрировать.

---

## C.4 Сравнительная таблица вариантов

| Параметр | Budget | Standard | Advanced |
|----------|--------|----------|----------|
| RAM | 4–6 GB | 16 GB | 32–64 GB |
| Системный диск | SSD 128–256 GB | SSD 512 GB | 2×SSD NVMe (mirror) |
| Второй диск | Нет | HDD 2 TB | 3×HDD SATA (RAIDZ) |
| Файловая система | ext4 / LVM-Thin | LVM-Thin | ZFS |
| GPU | Нет | Нет | Да (passthrough) |
| VLAN изоляция | Нет | Опционально | Да, zero-trust |
| Бэкапы | Ручные (USB) | Ежедневные (HDD) | PBS инкрементальные |
| Типичные сервисы | HA + AdGuard | +Nextcloud, NPM | +Windows VM, Jellyfin 4K |
| Стоимость железа | 5–15 тыс. руб. | 20–40 тыс. руб. | 50–150 тыс. руб. |
| Энергопотребление | 10–25 Вт | 15–35 Вт | 40–100 Вт |
| Для кого | Начинающие | Большинство задач | Продвинутые / энтузиасты |
