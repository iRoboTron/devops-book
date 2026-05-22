# Приложение A: Шпаргалка команд

> Все основные команды Proxmox VE в одном месте. Структурировано по разделам — открывать когда нужно быстро вспомнить синтаксис.

---

## A.1 LXC-контейнеры — pct

### Просмотр и статус

```bash
pct list                          # список всех LXC с их статусами
pct status <vmid>                 # статус конкретного контейнера (running/stopped)
pct config <vmid>                 # показать конфигурацию контейнера
```

### Управление жизненным циклом

```bash
pct start <vmid>                  # запустить контейнер
pct stop <vmid>                   # остановить контейнер (жёстко)
pct shutdown <vmid>               # корректно завершить работу (через init)
pct reboot <vmid>                 # перезагрузить контейнер
pct enter <vmid>                  # войти в консоль контейнера (интерактивно)
pct exec <vmid> -- <команда>      # выполнить команду внутри контейнера
pct exec 100 -- bash -c "apt update && apt upgrade -y"
```

### Создание и удаление

```bash
# Создать LXC-контейнер — основная форма
pct create <vmid> <шаблон> \
  --hostname <имя> \
  --memory <MB> \
  --cores <N> \
  --net0 name=eth0,bridge=vmbr0,ip=<IP>/24,gw=<GW>,type=veth \
  --storage <хранилище> \
  --rootfs <хранилище>:<GB> \
  --unprivileged 0|1 \
  --features keyctl=1,nesting=1

pct destroy <vmid>                # удалить контейнер (необратимо)
pct destroy <vmid> --purge        # удалить вместе со всеми снапшотами
```

### Изменение параметров

```bash
pct set <vmid> --memory 2048      # изменить лимит RAM (в MB)
pct set <vmid> --cores 4          # изменить количество ядер
pct set <vmid> --hostname new-name  # переименовать
pct set <vmid> --cpuunits 512     # снизить приоритет CPU (по умолчанию 1024)
pct set <vmid> --onboot 1         # включить автозапуск при старте хоста
```

### Диски и хранилище

```bash
pct resize <vmid> rootfs +10G     # расширить корневой диск на 10GB
pct resize <vmid> rootfs +20G     # файловая система расширяется автоматически

# Переместить диск на другое хранилище (--delete удалит старый)
pct move-volume <vmid> rootfs --storage data-hdd --delete
```

### Снапшоты

```bash
pct snapshot <vmid> <имя>                    # создать снапшот
pct snapshot 100 before-update --description "Перед обновлением $(date)"

pct listsnapshot <vmid>                      # список снапшотов
pct rollback <vmid> <имя>                    # откатить к снапшоту
pct delsnapshot <vmid> <имя>                 # удалить снапшот
```

### Клонирование и шаблоны

```bash
pct clone <src-vmid> <dst-vmid>              # клонировать контейнер
pct clone 100 200 --hostname new-service --storage local-lvm

pct stop <vmid>
pct template <vmid>                          # превратить в шаблон (необратимо!)
# После этого шаблон используется как основа для pct create
```

### Скачивание шаблонов

```bash
pveam update                                 # обновить список доступных шаблонов
pveam available                              # список всех доступных шаблонов
pveam available | grep debian                # фильтр по Debian
pveam download local debian-12-standard_12.7-1_amd64.tar.zst
pveam list local                             # скачанные шаблоны
```

---

## A.2 KVM виртуальные машины — qm

### Просмотр и статус

```bash
qm list                           # список всех VM
qm status <vmid>                  # статус VM (running/stopped)
qm config <vmid>                  # конфигурация VM
```

### Управление жизненным циклом

```bash
qm start <vmid>                   # запустить VM
qm stop <vmid>                    # остановить VM (жёстко, как выдернуть питание)
qm shutdown <vmid>                # корректно завершить (через OS)
qm reboot <vmid>                  # перезагрузить
qm reset <vmid>                   # аппаратный reset (как кнопка на корпусе)
qm stop <vmid> --skiplock         # принудительная остановка (если завис)
```

### Guest Agent команды

```bash
# Требует установленного qemu-guest-agent внутри VM
qm guest cmd <vmid> shutdown      # мягкий shutdown через агент
qm guest cmd <vmid> network-get-interfaces  # получить IP-адреса
qm guest exec <vmid> -- ls /      # выполнить команду внутри VM
```

### Снапшоты VM

```bash
qm snapshot <vmid> <имя>          # создать снапшот VM
qm snapshot 200 before-upgrade --description "Before upgrade $(date)"

qm listsnapshot <vmid>            # список снапшотов
qm rollback <vmid> <имя>          # откатить VM к снапшоту
qm delsnapshot <vmid> <имя>       # удалить снапшот
```

### Диски VM

```bash
# Переместить диск на другое хранилище
qm move-disk <vmid> virtio0 <хранилище> --delete

# Импортировать диск из файла образа (например HAOS)
qm importdisk <vmid> haos.qcow2 local-lvm

# Изменить порядок загрузки
qm set <vmid> --boot order=virtio0
```

### Создание VM через CLI

```bash
# Создать VM без диска (диск добавить отдельно через importdisk или в UI)
qm create <vmid> \
  --name my-vm \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0 \
  --ostype l26 \
  --agent enabled=1

# Добавить диск из хранилища
qm set <vmid> --virtio0 local-lvm:32
```

---

## A.3 Хранилища — pvesm

```bash
pvesm status                      # статус всех хранилищ (имя, тип, использование)
pvesm list <хранилище>            # содержимое хранилища
pvesm list local                  # содержимое local (ISO, шаблоны)
pvesm list local-lvm              # диски VM и LXC

pvesm alloc <хранилище> <vmid> <имя> <размер>  # выделить место вручную
pvesm free <хранилище> <volume-id>             # освободить вручную
```

---

## A.4 Бэкапы — vzdump

```bash
# Бэкап конкретного контейнера
vzdump <vmid> --compress zstd --storage backup-hdd --mode snapshot

# Бэкап с режимом остановки (надёжнее для БД)
vzdump <vmid> --compress zstd --storage backup-hdd --mode stop

# Бэкап всех VM и LXC одной командой
vzdump --all --compress zstd --storage backup-hdd --mode snapshot

# Восстановить LXC из бэкапа
pct restore <vmid> /mnt/backup-hdd/dump/vzdump-lxc-100-DATE.tar.zst \
  --storage local-lvm

# Восстановить VM из бэкапа
qm restore <vmid> /mnt/backup-hdd/dump/vzdump-qemu-200-DATE.vma.zst \
  --storage local-lvm
```

Режимы бэкапа:
| Режим | Описание | Когда использовать |
|-------|---------|------------------|
| `snapshot` | Быстро, контейнер не останавливается | Большинство случаев |
| `suspend` | Пауза во время снятия снапшота | Если нужна чистота данных |
| `stop` | Полная остановка, потом бэкап, потом старт | Критичные БД, максимальная надёжность |

---

## A.5 Хост и система

```bash
# Версия и диагностика
pveversion                        # версия Proxmox VE
pveversion --verbose              # подробная информация о компонентах

# Репозитории и обновления
apt update && apt full-upgrade -y  # обновить Proxmox и все пакеты
pveam update                       # обновить список LXC шаблонов

# Заморозить/разморозить пакет (перед мажорным обновлением)
apt-mark hold pve-kernel-$(uname -r)
apt-mark unhold pve-kernel-*

# Логи
journalctl -f                      # логи в реальном времени
journalctl -u pve-container@100    # логи конкретного контейнера
journalctl -u qemu-server@200      # логи конкретной VM
dmesg | grep -i "oom\|error"       # ядро: OOM и ошибки

# Оптимизация места для журналов
journalctl --vacuum-size=200M      # оставить не более 200MB логов
journalctl --vacuum-time=7d        # или не старше 7 дней
```

---

## A.6 Proxmox API — pvesh

```bash
# Базовые запросы
pvesh get /nodes                          # список узлов кластера
pvesh get /nodes/proxmox/status           # статус хоста
pvesh get /nodes/proxmox/lxc             # список LXC
pvesh get /nodes/proxmox/qemu            # список VM
pvesh get /nodes/proxmox/storage         # список хранилищ

# Создать LXC через API (то же что через веб-интерфейс)
pvesh create /nodes/proxmox/lxc \
  --vmid 200 \
  --hostname myapp \
  --ostemplate local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --memory 512 \
  --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.200/24,gw=192.168.1.1 \
  --storage local-lvm \
  --rootfs local-lvm:8

# Удалить LXC через API
pvesh delete /nodes/proxmox/lxc/200
```

---

## A.7 Сеть

```bash
# Применить изменения сети без перезагрузки
ifreload -a

# Проверить мосты и интерфейсы
ip link show
brctl show                         # показать мосты и подключённые интерфейсы
ip addr show vmbr0                 # IP-адрес на мосту

# Tailscale
tailscale up                       # авторизоваться
tailscale ip -4                    # свой Tailscale IP
tailscale status                   # статус и список устройств сети
tailscale up --advertise-routes=192.168.1.0/24  # subnet routing
```

---

## A.8 Диски и ZFS

```bash
# Информация о дисках
lsblk                              # список всех блочных устройств
lsblk -f                           # с файловыми системами

# LVM
pvs                                # Physical Volumes
vgs                                # Volume Groups
lvs                                # Logical Volumes
lvdisplay /dev/pve/data            # подробно о конкретном томе

# ZFS
zpool list                         # список пулов с размерами
zpool status                       # состояние пулов (ONLINE/DEGRADED/FAULTED)
zpool status -v                    # подробно, с ошибками
zfs list                           # список датасетов
zfs get compressratio pool/data    # коэффициент сжатия
zpool scrub tank                   # запустить проверку целостности данных

# SMART
apt install smartmontools -y
smartctl -H /dev/sda               # быстрая проверка: PASSED или FAILED
smartctl -a /dev/sda               # полный отчёт
smartctl -t short /dev/sda         # запустить короткий тест (2 минуты)
```

---

## A.9 Скрипты обновления всех контейнеров

```bash
# Обновить все запущенные LXC одной командой
for ct in $(pct list | awk 'NR>1 && $2=="running" {print $1}'); do
  echo "=== Обновляю CT $ct ==="
  pct exec $ct -- bash -c "apt update -qq && apt upgrade -y" 2>/dev/null || true
done

# Сделать снапшот всех VM перед мажорным обновлением
for vmid in $(qm list | awk 'NR>1 {print $1}'); do
  qm snapshot $vmid pre-upgrade --description "Before upgrade $(date +%Y-%m-%d)"
done

# Сделать снапшот всех LXC
for ctid in $(pct list | awk 'NR>1 {print $1}'); do
  pct snapshot $ctid pre-upgrade --description "Before upgrade $(date +%Y-%m-%d)"
done
```

---

## A.10 Диагностика типичных проблем

```bash
# Место
df -h                              # использование дисков
du -sh /* 2>/dev/null | sort -rh | head -20   # топ-20 по размеру
pvesm status                       # хранилища Proxmox

# CPU и процессы
htop                               # интерактивный монитор
pct exec 100 -- top -bn1 | head -20  # топ процессов внутри LXC

# OOM (Out of Memory)
dmesg | grep -i "oom\|killed"      # OOM события ядра
journalctl -u pve-container@100 | grep -i oom

# Контейнер не запускается
pct start 100                      # смотреть вывод ошибки
cat /etc/pve/lxc/100.conf         # проверить конфигурацию
pvesm status                       # хранилище доступно?

# Веб-интерфейс недоступен
systemctl status pveproxy          # статус веб-сервиса
systemctl restart pveproxy         # перезапустить
systemctl status pvedaemon         # daemon авторизации
```
