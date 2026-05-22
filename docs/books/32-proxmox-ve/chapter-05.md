# Глава 5: KVM виртуальные машины

> **Что вы узнаете:**
> - когда LXC-контейнера недостаточно и нужна полноценная виртуальная машина;
> - как создать VM с правильными настройками дисков и сети (VirtIO);
> - что такое Balloon Memory и как она экономит RAM;
> - зачем нужен qemu-guest-agent и что ломается без него;
> - особенности установки Windows VM — где взять драйверы и почему без них не работает диск;
> - типичные ошибки и как их исправить.

---

## 5.1 VM или LXC — когда что выбирать

В предыдущих главах мы работали с LXC-контейнерами. Это быстрый и экономный способ запускать Linux-сервисы. Но LXC — не универсальное решение.

**LXC — это общее ядро.** Контейнер использует ядро хоста Proxmox. Это его сильная сторона (скорость, малый overhead) и одновременно ограничение.

```text
Хост Proxmox (ядро 6.8)
  ├── LXC 100: Debian 12  ← использует ядро хоста
  ├── LXC 101: Ubuntu 24  ← тоже ядро хоста
  └── VM 200: Windows 11  ← своё ядро, полная изоляция
```

**Когда нужна KVM VM, а не LXC:**

| Ситуация | Почему LXC не подойдёт |
|----------|----------------------|
| Windows Server / Windows Desktop | LXC работает только с Linux |
| Home Assistant OS (официальный образ) | HAOS требует своё ядро и полный контроль железа |
| Приложение требует специфической версии ядра | LXC жёстко привязан к ядру хоста |
| Максимальная изоляция (безопасность) | При уязвимости ядра LXC даёт выход на хост |
| Тестирование другого дистрибутива | Нужен отдельный загрузчик, systemd, ядро |
| Приложение с kernel modules | Загрузка модулей в LXC ограничена |

**Сравнение накладных расходов:**

```text
LXC контейнер (1GB лимит):
  Overhead: ~5-20 MB RAM, старт за 1-2 секунды
  Производительность: почти нативная

KVM VM (1GB RAM):
  Overhead: ~150-300 MB RAM на QEMU процессы
  Старт: 15-30 секунд
  Производительность: 97-99% нативной (с KVM)
```

Вывод прост: запускай LXC по умолчанию, переходи на VM только когда есть конкретная причина.

---

## 5.2 Создание VM через веб-интерфейс

### Загрузить ISO-образ

Прежде чем создавать VM, нужно загрузить ISO-образ ОС в хранилище Proxmox.

Datacenter → pve (узел) → local → ISO Images → Upload

Или скачать напрямую с URL прямо в интерфейсе: Upload → Download from URL.

Для Ubuntu Server: `https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso`

### Мастер создания VM

Нажми кнопку **Create VM** в правом верхнем углу. Откроется мастер из нескольких вкладок:

**General:**
- VM ID: оставь автоматический (следующий свободный)
- Name: осмысленное имя, например `ubuntu-server-01`

**OS:**
- ISO image: выбери загруженный ISO
- Type: Linux, Version: 6.x - 2.6 Kernel

**System:**
- Machine: q35 (современный, рекомендуется)
- BIOS: SeaBIOS (для большинства задач) или OVMF (UEFI, нужен для Windows 11)
- Qemu Agent: **включить** — важно, объясним ниже

**Disks:**
- Тип шины: **VirtIO Block** — самый быстрый вариант для Linux
- Размер: 32 GB (для Ubuntu Server достаточно)
- Cache: Write back (быстрее) или None (безопаснее при отключении питания)
- SSD emulation: включи если хост на SSD — гость видит устройство как SSD

**CPU:**
- Cores: 2 (для домашнего сервера)
- Type: host — использует все возможности реального CPU, самое быстрое

> Не выбирай Type: kvm64 или Default (kvm64) для production VM. Тип host даёт лучшую производительность и нужен для вложенной виртуализации.

**Memory:**
- 2048 MB (2 GB) — для Ubuntu Server
- Balloon device: включить (объясним в следующем разделе)

**Network:**
- Bridge: vmbr0
- Model: **VirtIO (paravirt)** — самый быстрый, всегда использовать для Linux

**Confirm:**
- Start after created: включи, чтобы VM сразу запустилась

После создания перейди на вкладку **Console** — откроется экран загрузки. Установи ОС как обычно.

---

## 5.3 Создание VM через CLI

Для автоматизации или воспроизводимости — создание через `qm create`:

```bash
# Создаём Ubuntu Server VM с ID 200
# VirtIO диск 32GB, VirtIO сеть, 2 ядра, 2GB RAM
qm create 200 \
  --name ubuntu-server-01 \
  --memory 2048 \
  --cores 2 \
  --sockets 1 \
  --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --virtio0 local-lvm:32 \
  --ide2 local:iso/ubuntu-24.04-live-server-amd64.iso,media=cdrom \
  --boot order=ide2 \
  --machine q35 \
  --ostype l26 \
  --agent enabled=1

# Запустить VM
qm start 200
```

Управление VM через CLI:

```bash
qm list                    # список всех VM
qm status 200              # статус VM 200
qm start 200               # запустить
qm stop 200                # принудительная остановка (как выдернуть провод)
qm shutdown 200            # корректное выключение через гостевую ОС
qm reboot 200              # перезагрузка
qm reset 200               # жёсткий сброс
qm console 200             # открыть консоль (в терминале)
```

---

## 5.4 Balloon Memory — динамическая память

Представь двух жильцов квартиры. Вместо того чтобы жёстко делить площадь заранее, они договорились: каждый берёт столько, сколько нужно сейчас.

Balloon Memory работает так же: VM получает память динамически в зависимости от нагрузки.

```text
Без balloon:
  VM 200: жёстко выделено 4 GB — занято всегда, даже если VM простаивает

С balloon:
  VM 200: минимум 512 MB, максимум 4 GB
  В режиме ожидания: ~600 MB реально занято
  При нагрузке: автоматически вырастает до 4 GB
```

### Настройка через веб-интерфейс

VM → Hardware → Memory:

```text
Memory (MiB):         4096   ← максимум
Minimum memory (MiB):  512   ← стартовый минимум
Ballooning Device:      ✅   ← включить
```

### Как это работает технически

Гипервизор загружает в гостевую ОС специальный драйвер — balloon. Когда хосту нужна память, он через этот драйвер просит гостя «сдуться» (освободить часть RAM). Когда гостю нужно больше — хост «надувает» его обратно.

**Требования:**
- В Linux balloon-драйвер встроен в ядро с версии 2.6.27. Работает из коробки.
- В Windows нужен VirtIO balloon driver из пакета VirtIO Drivers (про это в разделе 5.6).

### Проверка что balloon работает

```bash
# Внутри Linux VM — смотреть реальное потребление памяти
free -h

# На хосте Proxmox — реальное использование памяти VM
qm monitor 200 <<< "info balloon"
# Вывод: balloon: actual=614400 kB  (т.е. ~600 MB реально занято)
```

Если balloon не работает, VM всегда займёт максимальное значение памяти.

---

## 5.5 qemu-guest-agent — обязательный компонент

qemu-guest-agent (QGA) — это небольшой демон, работающий внутри VM. Он создаёт канал связи между гостевой ОС и гипервизором.

**Что ломается без QGA:**

| Функция | Без QGA | С QGA |
|---------|---------|-------|
| IP-адрес в веб-интерфейсе | Не отображается | Виден сразу |
| Корректное выключение из Proxmox | Принудительное (как выдернуть провод) | Через ACPI + ожидание завершения |
| Снапшоты без остановки VM | Файловая система может быть грязной | Freeze/thaw перед снапшотом |
| `qm shutdown` | Работает, но долго | Быстро и чисто |
| Время синхронизации | Drift после снапшота | Синхронизируется автоматически |

Снапшоты без QGA создаются «вслепую» — файловая система VM может быть в несогласованном состоянии. Это особенно критично для баз данных.

### Установка QGA в Linux VM

```bash
# Debian / Ubuntu
apt update && apt install qemu-guest-agent -y

# CentOS / Rocky / AlmaLinux
dnf install qemu-guest-agent -y

# Включить и запустить
systemctl enable --now qemu-guest-agent

# Проверить что работает
systemctl status qemu-guest-agent
```

Пример вывода успешного статуса:

```
● qemu-guest-agent.service - QEMU Guest Agent
     Loaded: loaded (/lib/systemd/system/qemu-guest-agent.service; enabled)
     Active: active (running) since Fri 2026-05-23 10:00:00 UTC
```

После установки в веб-интерфейсе Proxmox у VM появятся IP-адреса на вкладке Summary.

### Включить QGA в настройках VM

В веб-интерфейсе: VM → Options → QEMU Guest Agent → Enabled: ✅

Или через CLI:

```bash
# На хосте Proxmox
qm set 200 --agent enabled=1
```

> Если QGA включён в настройках, но не установлен в гостевой ОС — `qm shutdown` будет зависать. Proxmox ждёт ответа от агента, а его нет. Решение: или установить QGA, или отключить в настройках VM.

---

## 5.6 Особенности Windows VM

Windows требует отдельного внимания. По умолчанию Windows не умеет работать с VirtIO-устройствами — ей нужны специальные драйверы.

### Проблема: Windows не видит диск при установке

При установке Windows с VirtIO-диском установщик показывает пустой экран "Where do you want to install Windows?" — диски не найдены.

```text
Плохо:
  Создать VM → VirtIO диск → установить Windows → "Диски не найдены"

Правильно:
  Создать VM → VirtIO диск + подключить VirtIO Drivers ISO → 
  При установке загрузить драйвер вручную → Windows видит диск
```

### Скачать VirtIO Drivers

Официальный ISO с драйверами от Proxmox / Red Hat:

```bash
# Скачать прямо в Proxmox через CLI
cd /var/lib/vz/template/iso/
wget https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso
```

Или через веб-интерфейс: local → ISO Images → Download from URL → вставить ссылку.

### Создание Windows VM

При создании VM в мастере:

- **OS type**: Microsoft Windows, Version: 11/2022 (или нужная)
- **Machine**: q35
- **BIOS**: OVMF (UEFI) — для Windows 11 обязательно
- **Disk bus**: VirtIO Block (быстрее SCSI/SATA)
- **Network model**: VirtIO (paravirt)

После вкладки Disks, до нажатия Finish — добавь второй CD-ROM с VirtIO ISO:
Hardware → Add → CD/DVD Drive → выбрать virtio-win.iso

### Установка Windows — загрузка драйверов

На экране выбора диска нажми **Load driver** → Browse → выбери CD-диск с virtio-win:

- Для диска: `virtio-win → viostor → w11 → amd64` (Windows 11)
- Для сети после установки: `NetKVM → w11 → amd64`

После загрузки драйвера viostor диск появится и установка продолжится.

### После установки Windows

```text
Установить из virtio-win.iso:
1. Открыть Диспетчер устройств — найти устройства с вопросами
2. Запустить virtio-win-guest-tools.exe с ISO
   (или установить вручную каждый драйвер)

Это установит:
  - VirtIO SCSI драйвер (диски)
  - VirtIO Net (сеть — интернет появится)
  - VirtIO Balloon (динамическая память)
  - QEMU Guest Agent (управление из Proxmox)
  - VirtIO Serial (дополнительный канал связи)
```

### TPM и Secure Boot для Windows 11

Windows 11 требует TPM 2.0. Proxmox поддерживает виртуальный TPM:

```bash
# При создании VM — в разделе System:
# TPM State: добавить → Storage: local-lvm, Version: v2.0
# BIOS: OVMF (UEFI)
# Pre-Enroll keys: включить для Secure Boot
```

---

## 5.7 Типичные ошибки и решения

### VM не видит диск при установке Windows

**Симптом:** экран установки Windows пустой, дисков нет.

**Причина:** VirtIO драйвер не загружен.

**Решение:** нажать "Load driver" и выбрать драйвер viostor из ISO virtio-win.

---

### qm shutdown зависает

**Симптом:** команда `qm shutdown 200` висит и не завершается.

**Причина 1:** QGA включён в настройках, но не установлен в гостевой ОС.

```bash
# Проверить настройки VM
qm config 200 | grep agent

# Вариант 1: установить QGA внутри VM
# Вариант 2: отключить QGA в настройках
qm set 200 --agent enabled=0
```

**Причина 2:** VM зависла и не отвечает на сигналы.

```bash
qm stop 200          # принудительная остановка
qm start 200         # запустить снова
```

---

### IP-адрес не виден в Proxmox

**Симптом:** на вкладке Summary VM нет IP-адресов, только "Guest Agent is not running".

**Решение:**

```bash
# Внутри VM
systemctl status qemu-guest-agent

# Если не установлен:
apt install qemu-guest-agent -y
systemctl enable --now qemu-guest-agent
```

---

### Balloon Memory не работает — VM всегда занимает максимум

**Симптом:** VM с настройками min=512MB, max=4GB всегда показывает 4GB в `free -h`.

**Причина 1:** balloon device не включён в Hardware.

```bash
# Проверить
qm config 200 | grep balloon
# Если нет balloon — добавить через веб-интерфейс: Hardware → Memory → включить Ballooning
```

**Причина 2:** внутри Windows не установлен VirtIO Balloon Driver.

Решение: установить virtio-win-guest-tools.exe.

---

### VM стартует медленно — несколько минут

**Симптом:** VM долго грузится, в консоли "Starting...".

**Причина:** CPU Type не host, а kvm64 — VM не видит аппаратные оптимизации.

```bash
# Остановить VM
qm shutdown 200

# Изменить тип CPU
qm set 200 --cpu host

# Запустить
qm start 200
```

---

### Снапшот VM завершился с ошибкой "QEMU driver error"

**Симптом:** снапшот с включённой опцией "Include RAM" не создаётся.

**Причина:** снапшот с дампом RAM (живой снапшот) требует определённых условий. Проще делать снапшот без RAM.

```bash
# Снапшот без дампа RAM (рекомендуется для большинства задач)
qm snapshot 200 before-update --description "Before nginx update"

# Откат
qm rollback 200 before-update
```

---

## 5.8 Практика

**Задание:** создать Ubuntu Server VM, установить ОС, настроить qemu-guest-agent и Balloon Memory.

Шаги:

1. Загрузить ISO Ubuntu Server 24.04 через веб-интерфейс.
2. Создать VM: VirtIO диск, VirtIO сеть, 2 ядра, min 512 MB / max 2048 MB RAM, QGA enabled.
3. Установить Ubuntu Server через консоль.
4. Внутри VM:

```bash
# Установить qemu-guest-agent
apt update && apt install qemu-guest-agent -y
systemctl enable --now qemu-guest-agent

# Проверить
systemctl status qemu-guest-agent
```

5. В Proxmox на вкладке Summary VM — убедиться что виден IP-адрес.
6. Выполнить `qm shutdown <vmid>` с хоста — VM должна корректно завершить работу.
7. Сделать снапшот: VM → Snapshots → Take Snapshot.

---

## Чек-лист для самопроверки

- [ ] Могу объяснить три конкретных случая когда нужна VM, а не LXC
- [ ] VM создана с типом диска VirtIO и типом сети VirtIO
- [ ] qemu-guest-agent установлен, IP-адрес виден на вкладке Summary
- [ ] Balloon Memory настроена с минимальным и максимальным значением
- [ ] Выполнил `qm shutdown` — VM завершила работу корректно, не зависла
- [ ] Сделал снапшот VM и знаю как откатиться
- [ ] Понимаю зачем нужны VirtIO Drivers для Windows и где их скачать
