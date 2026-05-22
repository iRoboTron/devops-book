# Глава 10: PCI Passthrough и GPU

> **Что вы узнаете:**
> - что такое IOMMU и зачем он нужен для проброса устройств;
> - как включить IOMMU в GRUB для Intel и AMD и проверить результат;
> - как «спрятать» GPU от хоста через blacklist и передать его напрямую в VM;
> - когда Jellyfin реально выигрывает от GPU passthrough, а когда достаточно software transcoding.

---

Раньше — если хотел запустить Windows-игры рядом с Linux-сервером, нужно было два отдельных компьютера. С Proxmox и PCI passthrough это один сервер: виртуальная машина получает физическую видеокарту напрямую, без какого-либо слоя эмуляции.

PCI passthrough — это не магия и не эксклюзивная функция дорогих серверов. Это стандартная возможность любого современного десктопного или серверного железа. Главное условие: CPU и материнская плата поддерживают IOMMU.

---

## 10.1 Что такое IOMMU и зачем он нужен

Обычно все устройства в системе общаются с RAM напрямую через шину PCI. Если отдать видеокарту виртуальной машине без какой-либо защиты, она сможет читать и писать в любую область памяти хоста. Это дыра в безопасности размером с ворота.

IOMMU (Input/Output Memory Management Unit) — аппаратный блок в CPU и чипсете, который создаёт изолированное адресное пространство для каждого PCI-устройства. Виртуальная машина с GPU работает только со своей памятью, не имея доступа к памяти хоста или других VM.

```text
Без IOMMU:
  GPU → шина PCI → вся RAM (хост + все VM) — небезопасно

С IOMMU:
  GPU → IOMMU → изолированное адресное пространство VM — безопасно
```

У Intel эта технология называется **VT-d** (Virtualization Technology for Directed I/O).
У AMD — **AMD-Vi** (AMD I/O Virtualization Technology), в современных процессорах называется **AMD-V**.

Без IOMMU PCI passthrough невозможен физически — Proxmox просто не даст добавить PCI-устройство в VM.

---

## 10.2 Проверка поддержки в BIOS

Прежде чем трогать GRUB, убедитесь что технология включена в прошивке.

**Что искать в BIOS/UEFI:**
- Intel: `VT-d`, `Intel Virtualization for Directed I/O`
- AMD: `IOMMU`, `AMD-Vi`, `SVM Mode`

Обычно находится в разделах: `Advanced → CPU Configuration`, `Advanced → System Agent`, `Chipset → VT-d`.

Если пункта нет — процессор или материнская плата не поддерживают IOMMU. Большинство CPU старше 2012 года уже имеют эту поддержку, но некоторые бюджетные платы её отключают или вовсе не выставляют в BIOS.

---

## 10.3 Включение IOMMU в GRUB

После включения в BIOS нужно сообщить ядру Linux что использовать IOMMU. Это делается через параметры загрузки.

Открыть файл конфигурации GRUB на хосте Proxmox:

```bash
nano /etc/default/grub
```

Найти строку `GRUB_CMDLINE_LINUX_DEFAULT` и добавить параметры:

```bash
# Для Intel — добавить intel_iommu=on iommu=pt
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"

# Для AMD — добавить amd_iommu=on iommu=pt
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"
```

Параметр `iommu=pt` означает **passthrough mode** — он ускоряет работу устройств, которые не пробрасываются в VM. Без него все PCI-устройства на хосте проходят через IOMMU даже когда не нужно, что немного снижает производительность.

Применить изменения и перезагрузиться:

```bash
# Эта команда перегенерирует конфиг загрузчика с новыми параметрами
update-grub

reboot
```

---

## 10.4 Проверка через dmesg

После перезагрузки убедиться что IOMMU действительно заработал:

```bash
# Ищем строки DMAR (Intel) или AMD-Vi (AMD) в журнале загрузки
dmesg | grep -e DMAR -e IOMMU | head -20
```

Для Intel должна быть строка вида:
```
DMAR: IOMMU enabled
```

Для AMD:
```
AMD-Vi: AMD IOMMUv2 loaded and initialized
```

Если эти строки есть — IOMMU активен. Если ничего нет — перепроверьте BIOS и правильность параметра в GRUB.

Посмотреть IOMMU-группы (как именно устройства объединены):

```bash
# Эта команда показывает все PCI-устройства и их группы изоляции
find /sys/kernel/iommu_groups/ -type l | sort -V | head -40
```

Пример вывода:
```
/sys/kernel/iommu_groups/1/devices/0000:00:01.0
/sys/kernel/iommu_groups/2/devices/0000:00:02.0
/sys/kernel/iommu_groups/14/devices/0000:01:00.0
/sys/kernel/iommu_groups/14/devices/0000:01:00.1
```

Устройства `0000:01:00.0` и `0000:01:00.1` находятся в одной группе 14. Это важно: **все устройства одной IOMMU-группы нужно пробрасывать вместе**. Если у видеокарты есть аудио-компонент (второй адрес) — пробрасывать нужно оба.

---

## 10.5 Blacklist драйвера GPU на хосте

Proxmox при старте загружает драйверы для всего обнаруженного железа. Если видеокарту захватит хост — VM не сможет её получить.

Решение: заблокировать загрузку драйвера GPU на уровне хоста.

```bash
# Для NVIDIA карт (nouveau — open source драйвер, nvidia — проприетарный)
echo "blacklist nouveau" >> /etc/modprobe.d/blacklist.conf
echo "blacklist nvidia" >> /etc/modprobe.d/blacklist.conf

# Для AMD карт
echo "blacklist amdgpu" >> /etc/modprobe.d/blacklist.conf
echo "blacklist radeon" >> /etc/modprobe.d/blacklist.conf
```

Если нужно использовать встроенную графику CPU для вывода консоли, а дискретную карту пробрасывать в VM — blacklist нужно делать только для дискретной. Встроенная (Intel HD / AMD Vega) продолжит работать.

После изменения blacklist — обновить initramfs и перезагрузиться:

```bash
# Эта команда пересобирает образ начальной файловой системы с учётом blacklist
update-initramfs -u

reboot
```

Проверить что драйвер не загружен:

```bash
# Если команда ничего не выводит — драйвер отключён успешно
lsmod | grep nouveau
lsmod | grep nvidia
lsmod | grep amdgpu
```

---

## 10.6 Добавление PCI-устройства в VM

VM должна быть **остановлена** перед добавлением PCI-устройства.

Через веб-интерфейс:

1. Выбрать VM → **Hardware** → **Add** → **PCI Device**.
2. В списке найти видеокарту по PCI-адресу (например `0000:01:00.0 NVIDIA GeForce RTX 3060`).
3. Включить **All Functions** — автоматически добавит все функции устройства (GPU + аудио компонент).
4. Включить **PCI-Express** если устройство на шине PCIe — улучшает производительность.
5. (Опционально) включить **ROM-Bar** — нужно для некоторых карт NVIDIA.

Через CLI — то же самое одной командой:

```bash
# Эта команда добавляет PCI-устройство 01:00 в VM с ID 201
# hostpci0 — первый PCI passthrough слот в VM
qm set 201 -hostpci0 01:00,allf=1,pcie=1
```

Запустить VM и убедиться что карта видна внутри:

```bash
# Если VM на Linux — зайти в консоль и проверить
qm terminal 201
# Внутри VM:
lspci | grep -i vga
```

---

## 10.7 Jellyfin и аппаратное транскодирование

Jellyfin — медиасервер. Когда клиент запрашивает видео в формате, который он не поддерживает, Jellyfin перекодирует его на лету (transcode). Это тяжёлая операция.

**Без GPU:**
- 1080p h264 → 1080p h264 (copy): ~5% CPU, быстро.
- 1080p h265 → 1080p h264 (transcode): 80-100% CPU, один поток может загрузить весь сервер.
- 4K h265 HDR → 1080p SDR: на слабом CPU — не тянет совсем.

**С GPU passthrough:**
- 4K h265 HDR → 1080p SDR: 10-20% GPU, 5-10% CPU, в реальном времени.
- Можно одновременно транскодировать 5-10 потоков — GPU справляется там, где CPU задыхается.

Схема для Jellyfin с GPU passthrough:

```text
Proxmox Host
└── VM 202: Jellyfin (Debian 12, 2GB RAM)
    └── hostpci0: NVIDIA RTX 3060 (passthrough)
         → NVENC/NVDEC аппаратное кодирование/декодирование
```

Настройка внутри Jellyfin VM:

```bash
# Установить NVIDIA драйвер внутри VM (не на хосте!)
apt install nvidia-driver -y

# Проверить что карта видна
nvidia-smi
```

Пример вывода `nvidia-smi` внутри VM:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 525.147.05   Driver Version: 525.147.05   CUDA Version: 12.0    |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce...  Off  | 00000000:00:10.0 Off |                  N/A |
+-----------------------------------------------------------------------------+
```

В веб-интерфейсе Jellyfin: **Dashboard → Playback → Transcoding → Hardware acceleration → NVENC**.

---

## 10.8 Таблица типичных ошибок

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `No IOMMU groups found` | IOMMU не включён или не работает | Проверить BIOS (VT-d/AMD-Vi), убедиться в правильности параметра GRUB |
| `Device is in use by another process` | Хост захватил GPU | Добавить в blacklist, пересобрать initramfs, перезагрузиться |
| VM не запускается после добавления PCI | Несколько устройств в одной IOMMU-группе | Пробросить все устройства группы через `allf=1` |
| GPU видна в VM, но не работает | Нет драйверов в гостевой ОС | Установить NVIDIA/AMD драйверы внутри VM |
| NVIDIA карта не инициализируется | Карта обнаруживает что работает в VM (Anti-VM check) | Добавить `args: -cpu host,hidden=1` в конфиг VM |
| `VFIO: Error resetting device` при старте VM | GPU не поддерживает function-level reset | Добавить `rombar=0` или найти модифицированный ROM |
| После reboot GPU снова захвачена хостом | Blacklist не сохранился в initramfs | Повторить `update-initramfs -u`, проверить `/etc/modprobe.d/` |

Отдельно про ошибку с NVIDIA Anti-VM. Некоторые карты отказываются работать в виртуальной среде. Решение — скрыть факт виртуализации:

```bash
# Добавить в конфиг VM /etc/pve/qemu-server/201.conf
args: -cpu host,kvm=off
```

Или через CLI:
```bash
qm set 201 --cpu host,hidden=1
```

---

## 10.9 Когда PCI passthrough не нужен

PCI passthrough — мощный инструмент, но он добавляет сложность. Прежде чем браться за него, стоит ответить на вопросы:

**Jellyfin без 4K:**
Если контент только 1080p, один пользователь и сервер — какой-нибудь N100 или i5 с 8GB RAM — software transcoding справляется отлично. GPU passthrough здесь не даёт ощутимого выигрыша.

**Встроенная графика CPU:**
Intel Quick Sync и AMD AMF — это аппаратное транскодирование прямо в CPU. Для Jellyfin можно использовать без всякого passthrough через `/dev/dri` (device passthrough, не PCI passthrough). Значительно проще и работает из LXC-контейнера.

```bash
# Для LXC с Jellyfin — проброс /dev/dri без PCI passthrough
# В /etc/pve/lxc/104.conf добавить:
lxc.cgroup2.devices.allow: c 226:* rwm
lxc.cgroup2.devices.allow: c 29:0 rwm
lxc.mount.entry: /dev/fb0 dev/fb0 none bind,optional,create=file
lxc.mount.entry: /dev/dri dev/dri none bind,optional,create=dir
lxc.mount.entry: /dev/dri/renderD128 dev/dri/renderD128 none bind,optional,create=file
```

**Один пользователь, один поток:**
Если медиасервер — только для себя и смотришь один поток — экономия ресурсов от passthrough не окупает время на настройку.

**Когда PCI passthrough действительно нужен:**
- Игровая VM с Windows — нужна «настоящая» видеокарта с полной производительностью.
- Несколько одновременных 4K потоков в Jellyfin.
- ML-задачи (обучение моделей, inference) в изолированной VM.
- Специализированное железо: карты захвата видео, аппаратные ускорители.

---

## 10.10 Практика

Проверить поддержку IOMMU на своём хосте:

```bash
# Шаг 1: убедиться что IOMMU включён в BIOS
# Шаг 2: добавить параметры в GRUB и перезагрузиться
# Шаг 3: проверить результат
dmesg | grep -e DMAR -e IOMMU | head -5

# Посмотреть группы устройств
find /sys/kernel/iommu_groups/ -type l | sort -V | head -20

# Посмотреть какие PCI-устройства есть на сервере
lspci | grep -iE "vga|3d|display|nvidia|amd|radeon"
```

Если есть подходящая видеокарта и IOMMU работает — попробовать пробросить карту в тестовую VM с Debian 12, убедиться что `lspci` внутри VM показывает карту.

---

## Чек-лист для самопроверки

- [ ] Проверил включён ли IOMMU через `dmesg | grep -e DMAR -e IOMMU`
- [ ] Понимаю разницу между IOMMU-группой и отдельным PCI-устройством — знаю почему нужно пробрасывать всю группу
- [ ] Знаю зачем нужен blacklist драйвера на хосте и как его применить через `update-initramfs`
- [ ] Понимаю когда Jellyfin выигрывает от GPU passthrough, а когда достаточно `/dev/dri` через LXC
- [ ] Могу объяснить разницу: PCI passthrough (полное устройство в VM) vs device passthrough `/dev/dri` (встроенная графика для LXC)
