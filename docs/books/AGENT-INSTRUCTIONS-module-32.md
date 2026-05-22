# Инструкция для ИИ-агента: Модуль 32 — Proxmox VE

> **Это Модуль 32, книга части 4 "Прочее".**
> Предварительные требования: базовые знания Linux (книга 01), понимание Docker (книга 03), базовые знания сетей. Читатель уже работал с сервером или хочет поднять домашний сервер с нуля.

---

## Контекст проекта

Читатель хочет организовать сервер дома или в небольшой компании. Сейчас у него либо "просто Ubuntu с Docker", либо он только начинает. Он слышал про Proxmox, но:

- не понимает зачем он нужен, если можно просто поставить Ubuntu и Docker;
- не знает чем LXC отличается от Docker и когда что использовать;
- не разобрался как грамотно распределить ресурсы между виртуальными машинами и контейнерами;
- боится что "гипервизор — это сложно";
- хочет запустить Home Assistant, Nextcloud, Jellyfin, свои сервисы — но не знает как это правильно организовать;
- не понимает как работает хранилище, снапшоты, бэкапы;
- хочет чтобы можно было всё восстановить если что-то сломается.

**Что он хочет после книги:**
Поднять Proxmox на реальном сервере или мини-ПК, запустить несколько LXC-контейнеров и виртуальных машин, настроить бэкапы, подключить удалённый доступ через Tailscale — и уверенно управлять этим через веб-интерфейс.

---

## Что за книга

**Название:** "Proxmox VE: домашний и корпоративный гипервизор с нуля"

**Каталог:** `32-proxmox-ve`

**Место в курсе:** Книга 32, часть 4 "Прочее".

**Объём:** 180–220 страниц.

**Особенность книги:**
Это практическое руководство с реальными сценариями. Не пересказ официальной документации — в ней уже 27 подробных глав на английском. Здесь: понятное объяснение концепций, практические сценарии, типичные ошибки и их решения, готовые рецепты для домашнего сервера.

**Стиль:**
- Простой язык, без лишнего академизма.
- Каждая глава начинается с блока «Что вы узнаете» и заканчивается «Чек-листом для самопроверки».
- Много сравнений: "раньше делал так → теперь через Proxmox вот так".
- Пары "плохо → лучше" для типичных ошибок.
- Конкретные команды сопровождаются объяснением что они делают.
- Сценарии приближены к реальной жизни: Home Assistant, Nextcloud, Docker-стек.

---

## Главная идея

Proxmox — это не "сложный энтерпрайз". Это удобная основа для любого сервера: дома, в маленькой компании, у фрилансера. Он даёт то, чего нет у просто Ubuntu: изоляцию сервисов, снапшоты, бэкапы одним кликом, лёгкое восстановление и возможность запускать что угодно — хоть Docker, хоть Windows, хоть Home Assistant.

```text
Раньше:
один сервер → Ubuntu → Docker → всё в одной системе → сломалось одно → проблемы у всех

С Proxmox:
один сервер → Proxmox → LXC(Docker) + LXC(Nextcloud) + VM(Windows) → сломалось одно → восстановил из снапшота за 2 минуты
```

**Ключевое понимание:**
- LXC контейнер ≠ Docker контейнер. LXC — это мини-система с systemd. Docker внутри LXC — лучший способ запускать сервисы.
- Память и CPU в LXC не резервируются жёстко — используется только то, что нужно.
- Снапшот ≠ бэкап. Снапшот — быстрый откат. Бэкап — надёжное хранение.
- Community Scripts — это "магазин приложений" для Proxmox: одна команда и сервис готов.

---

## Что читатель получит к концу книги

- Установленный и настроенный Proxmox VE на реальном железе.
- Понимание разницы между KVM, LXC и Docker — и когда что использовать.
- Работающие LXC-контейнеры с Docker, Nextcloud или другими сервисами.
- Настроенные бэкапы с расписанием и проверенным восстановлением.
- Удалённый доступ через Tailscale.
- Умение использовать Community Scripts и ручные альтернативы.
- Понимание хранилищ: LVM-Thin, ZFS, Directory — когда что выбрать.
- Навык быстрого восстановления из снапшота или бэкапа.
- Рабочие скрипты мониторинга с уведомлениями в Telegram.
- Хотя бы один bash-скрипт автоматизации, создающий LXC воспроизводимо.
- Базовое понимание кластеризации — чтобы знать куда расти.

---

## Структура книги

### Глава 0: Зачем Proxmox, если есть Ubuntu с Docker

**Что вы узнаете:**
- чем гипервизор отличается от обычной ОС;
- когда Proxmox решает реальные проблемы, а когда он избыточен;
- что конкретно меняется при переходе с Ubuntu+Docker.

**Цель:** убедить (или честно сказать "не надо") в том, что Proxmox решает реальные проблемы.

Объяснить:
- что такое гипервизор и зачем он нужен;
- чем отличается тип 1 (bare-metal, Proxmox) от типа 2 (VirtualBox поверх ОС);
- что теряет и что получает пользователь при переходе с Ubuntu+Docker на Proxmox;
- типичный сценарий "домашний сервер через год": Home Assistant + Nextcloud + торрент + медиасервер — и почему без гипервизора это становится хаосом.

Сравнение:

```text
Ubuntu + Docker:
+ просто
+ знакомо
- всё в одном пространстве
- один контейнер забивает CPU — все тормозят
- нет снапшотов всей системы
- обновил ядро — сломал всё

Proxmox:
+ изоляция сервисов
+ снапшоты и бэкапы за секунды
+ можно запускать Windows рядом с Linux
+ лёгкое восстановление
- ещё один слой для понимания
- не нужен для одного сервиса
```

**Когда Proxmox НЕ нужен:** один сервис, минимальное железо (< 4GB RAM), нет нужды в изоляции.

**Практика:** ответить на вопросы: сколько сервисов планируешь, сколько RAM, нужна ли изоляция, нужны ли бэкапы по расписанию.

**Чек-лист для самопроверки:**
- [ ] Понимаю разницу между гипервизором типа 1 и типа 2
- [ ] Могу объяснить, зачем нужна изоляция сервисов
- [ ] Принял осознанное решение — Proxmox подходит для моих задач
- [ ] Знаю минимальные требования к железу

---

### Глава 1: Установка Proxmox VE

**Что вы узнаете:**
- как установить Proxmox на реальное железо;
- как отключить платный репозиторий и подключить бесплатный;
- как попасть в веб-интерфейс после установки.

**Цель:** установить Proxmox на реальное железо от нуля до веб-интерфейса.

Темы:
- Системные требования (минимальные и рекомендуемые).
- Где скачать ISO и как записать на флешку (Balena Etcher, Rufus).
- Процесс установки шаг за шагом.
- Первый вход в веб-интерфейс: `https://IP:8006`.
- Отключение платного enterprise-репозитория, подключение бесплатного.
- Обновление системы после установки.

Типичные ошибки:
- BIOS: не включена виртуализация (VT-x / AMD-V) → как включить.
- Установка на диск с данными → предупреждение.
- Не открывается веб-интерфейс → браузер блокирует self-signed cert → как добавить исключение.

Команды после установки:
```bash
# Отключить enterprise репозиторий (платный)
sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/pve-enterprise.list

# Добавить бесплатный репозиторий (без подписки)
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" \
  > /etc/apt/sources.list.d/pve-no-subscription.list

# Обновить систему
apt update && apt full-upgrade -y
```

**Практика:** установить Proxmox, зайти в веб-интерфейс, сделать обновление.

**Чек-лист для самопроверки:**
- [ ] Proxmox установлен, веб-интерфейс открывается по HTTPS
- [ ] Enterprise-репозиторий отключён, no-subscription подключён
- [ ] `apt update && apt full-upgrade` прошёл без ошибок
- [ ] В Summary видны CPU, RAM, диски

---

### Глава 2: Знакомство с веб-интерфейсом

**Что вы узнаете:**
- где находятся ключевые разделы интерфейса;
- как запускать, останавливать и управлять VM/LXC;
- как открыть консоль контейнера.

**Цель:** ориентироваться в интерфейсе не методом тыка.

Ключевые элементы (без лишнего пересказа пунктов меню):
- Левая панель: Datacenter → Node → Storage → VM/CT.
- Shell на уровне Node — SSH прямо в браузере к хосту Proxmox.
- Summary узла — загрузка CPU, RAM, дисков в реальном времени.
- Tasks/Logs — лог всех операций, здесь смотреть ошибки.

Основные действия:
- Создать VM/LXC: кнопка в правом верхнем углу.
- Запуск/стоп/ребут: кнопки в верхней панели при выборе VM/CT.
- Консоль: вкладка Console — открывается в браузере.
- Снапшот: вкладка Snapshots → Take Snapshot.
- Бэкап: вкладка Backup → Backup now.

Важный момент: CTRL+C в консоли Proxmox передаётся внутрь системы, а не прерывает команду в браузере. Для копирования — правая кнопка мыши.

**Практика:** найти в интерфейсе версию Proxmox, нагрузку CPU, доступную RAM, список хранилищ.

**Чек-лист для самопроверки:**
- [ ] Нашёл Shell хоста и выполнил команду `pveversion`
- [ ] Нашёл раздел Storage и вижу доступные хранилища
- [ ] Понимаю где смотреть логи задач (Tasks)
- [ ] Умею открыть консоль контейнера

---

### Глава 3: LXC-контейнеры — основа домашнего сервера

**Что вы узнаете:**
- чем LXC отличается от Docker-контейнера;
- как создавать и управлять LXC через CLI и веб-интерфейс;
- что происходит когда контейнеру не хватает памяти (OOM).

**Цель:** понять что такое LXC и научиться создавать контейнеры.

Объяснить разницу:
```text
Docker-контейнер:
- одно приложение
- без init-системы
- умирает вместе с процессом

LXC-контейнер:
- полноценная мини-система
- работает systemd, cron, SSH
- можно установить Docker внутрь
- ближе к "лёгкой виртуальной машине"
```

Создание LXC через веб-интерфейс:
- Скачать шаблон (template) через Datacenter → Storage → CT Templates.
- Настроить: RAM, CPU, диск, сеть, пароль.
- Важные настройки при создании:
  - Unprivileged container — безопаснее, подходит для большинства задач.
  - Privileged container — нужен для Docker внутри LXC.
  - Features: nesting=1, keyctl=1 — обязательно для Docker.

Создание LXC через CLI:
```bash
# Эта команда создаёт LXC-контейнер с ID 100 из шаблона Debian 12,
# выделяет 1GB RAM, 2 ядра CPU, диск 8GB на хранилище local-lvm
pct create 100 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname mycontainer \
  --memory 1024 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --storage local-lvm \
  --rootfs local-lvm:8 \
  --password
```

Управление LXC:
```bash
pct start 100            # запустить контейнер
pct stop 100             # остановить
pct enter 100            # войти в консоль контейнера
pct exec 100 -- bash -c "apt update"   # выполнить команду внутри
pct list                 # список всех контейнеров
```

Динамическое распределение ресурсов:
- Память: указывается лимит, не резервирование.
- CPU: weight и cores — как работает планировщик.
- Два контейнера по 4GB лимита на 8GB хосте — работает корректно, каждый берёт сколько нужно прямо сейчас.

#### [ИЗМЕНЕНО] Out Of Memory (OOM) — что происходит когда памяти не хватило

Если контейнер превысил лимит памяти, ядро Linux запускает OOM Killer — он принудительно убивает процессы внутри контейнера чтобы освободить память. Приложение может упасть без предупреждения.

Как увидеть OOM в логах:
```bash
# На хосте Proxmox
dmesg | grep -i "oom\|killed"
# Пример вывода: "Memory cgroup out of memory: Kill process 1234 (node) score 900 or sacrifice child"

journalctl -u pve-container@100 | grep -i oom
```

Настройки памяти на хосте (влияют на все контейнеры):
```bash
# Проверить текущее значение swappiness (по умолчанию 60)
cat /proc/sys/vm/swappiness

# Снизить до 10 для серверов с LXC — своп используется реже
echo "vm.swappiness=10" >> /etc/sysctl.d/99-proxmox.conf
sysctl -p /etc/sysctl.d/99-proxmox.conf
```

Своп для LXC — подушка безопасности:
- В конфиге LXC через веб: Hardware → Memory → Swap: 512.
- Не злоупотреблять на SSD — ускоряет износ.

Рекомендация: устанавливать лимит памяти LXC с запасом 20-30% от реального потребления. Пример: приложение потребляет ~800MB — ставить лимит 1024MB.

**Практика:** создать LXC с Debian 12, зайти в консоль, обновить пакеты, проверить swap.

**Чек-лист для самопроверки:**
- [ ] Скачал шаблон и создал LXC через CLI
- [ ] Вошёл в консоль через `pct enter` и выполнил команду
- [ ] Понимаю разницу между лимитом памяти и резервированием
- [ ] Знаю как найти OOM в логах

---

### Глава 4: Docker внутри LXC

**Что вы узнаете:**
- почему Docker запускают в LXC, а не напрямую на хосте Proxmox;
- как правильно настроить LXC для Docker;
- как использовать Community Scripts для быстрой установки.

**Цель:** правильно запустить Docker в LXC-контейнере.

Почему Docker в LXC, а не Docker напрямую на хосте Proxmox:
- Хост Proxmox — это священный уровень. Не засорять его сервисами.
- LXC даёт изоляцию, лимиты, бэкапы, снапшоты для всего Docker-стека.
- Легко пересоздать или восстановить весь контейнер с Docker одной командой.

Настройка LXC для Docker (в конфиге на хосте):
```bash
# Файл /etc/pve/lxc/100.conf — добавить строку:
features: keyctl=1,nesting=1
```

Или через веб-интерфейс: CT → Options → Features → включить Nesting и Keyctl.

Установка Docker в LXC:
```bash
# Внутри LXC контейнера — официальный скрипт установки
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

Проверка:
```bash
docker run hello-world
docker ps
```

Community Scripts — самый простой способ:
```bash
# На хосте Proxmox, в Shell — создаёт LXC и устанавливает Docker автоматически
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"
```

**Практика:** создать LXC с Docker, запустить `nginx` через docker run, проверить что открывается в браузере.

**Чек-лист для самопроверки:**
- [ ] Docker установлен в LXC, `docker run hello-world` работает
- [ ] Понимаю зачем нужны nesting и keyctl
- [ ] Контейнер с Nginx открывается в браузере по IP LXC

---

### Глава 5: KVM виртуальные машины

**Что вы узнаете:**
- когда LXC недостаточно и нужна полная VM;
- как настроить balloon memory для динамического распределения RAM;
- зачем нужен qemu-guest-agent.

**Цель:** когда и как использовать полноценные VM.

Когда LXC не подходит и нужна KVM VM:
- Windows Server / Windows Desktop.
- Приложения требующие специфического ядра.
- Максимальная изоляция (безопасность).
- Тестирование ОС.
- Home Assistant OS (официально — только VM или отдельное железо).

Создание VM:
- Загрузить ISO на хранилище: Storage → ISO Images → Upload.
- Создать VM через мастер: CPU, RAM, диск, ISO, сеть.
- Тип диска: VirtIO — самый быстрый, рекомендован для Linux.
- Тип сети: VirtIO — аналогично.
- Для Windows: добавить VirtIO drivers ISO отдельно (скачать с сайта Proxmox).

Balloon Memory — динамическая память:
```text
Настройка VM: Hardware → Memory
  Minimum memory: 512 MB    ← стартовый минимум
  Maximum memory: 4096 MB   ← потолок
  Ballooning device: ✅

VM стартует с 512MB, растёт до 4GB по мере надобности.
Требует balloon-драйвер в гостевой ОС (в Linux есть по умолчанию, в Windows — VirtIO drivers).
```

Установка qemu-guest-agent — обязательно:
```bash
# Внутри Linux VM — агент позволяет Proxmox "видеть" состояние ОС изнутри
apt install qemu-guest-agent
systemctl enable --now qemu-guest-agent
```

Что даёт agent: корректный shutdown из интерфейса, IP-адрес в веб-интерфейсе, freeze файловой системы для корректных снапшотов.

**Практика:** создать Ubuntu Server VM, установить qemu-guest-agent, проверить IP в веб-интерфейсе Proxmox.

**Чек-лист для самопроверки:**
- [ ] VM создана и запущена, консоль открывается
- [ ] qemu-guest-agent установлен, IP виден в Proxmox
- [ ] Balloon memory настроена с минимумом и максимумом
- [ ] Понимаю разницу: KVM VM vs LXC — когда что выбрать

---

### Глава 6: Community Scripts — магазин приложений для Proxmox

**Что вы узнаете:**
- что такое Community Scripts и как ими пользоваться;
- как установить популярные сервисы одной командой;
- как действовать если скрипт недоступен или устарел.

**Цель:** использовать https://community-scripts.org/ для быстрого разворачивания сервисов.

Что такое Community Scripts:
- Коллекция bash-скриптов, поддерживаемых сообществом.
- Каждый скрипт создаёт LXC (или VM) и устанавливает нужный сервис.
- Активно обновляются, поддерживают актуальные версии.
- Более 200 готовых скриптов.

Как пользоваться:
```bash
# Открыть Shell на хосте Proxmox и вставить команду со страницы
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"
```

Популярные скрипты:
| Сервис | Что делает |
|--------|-----------|
| Docker LXC | LXC + Docker + Portainer |
| Home Assistant OS | VM с официальным HAOS |
| Nextcloud | LXC с Nextcloud AIO |
| Jellyfin | LXC с медиасервером |
| Nginx Proxy Manager | LXC с reverse proxy |
| Vaultwarden | LXC с менеджером паролей |
| Gitea | LXC с self-hosted Git |
| AdGuard Home | LXC с DNS-блокировщиком рекламы |
| Uptime Kuma | LXC с мониторингом |
| Tailscale | установка на хост или в LXC |

Что происходит под капотом скрипта:
- Создаётся LXC с нужными параметрами.
- Устанавливается ПО и зависимости.
- Настраивается systemd сервис.
- Выводится IP и порт для доступа.

**Важно:** всегда читать что делает скрипт перед запуском. Смотреть исходник на GitHub или через `curl -fsSL <url> | less`.

#### [ИЗМЕНЕНО] Ручные альтернативы (план Б если скрипт недоступен)

Скрипты могут быть временно недоступны (DNS, firewall, устаревший URL). Для надёжности — знать ручной способ.

**Docker LXC — вручную:**
```bash
# 1. Создать privileged LXC с Debian 12 через веб-интерфейс
#    Features: nesting=1, keyctl=1
# 2. Запустить и войти
pct start 100 && pct enter 100
# 3. Установить Docker
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

**Nginx Proxy Manager — вручную:**
```bash
# Внутри LXC с Docker
mkdir -p /opt/npm && cd /opt/npm
cat > docker-compose.yml << 'EOF'
services:
  npm:
    image: jc21/nginx-proxy-manager:latest
    ports:
      - "80:80"
      - "443:443"
      - "81:81"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
EOF
docker compose up -d
```

**Uptime Kuma — вручную:**
```bash
# Внутри LXC с Docker — одна команда
docker run -d --name uptime-kuma --restart always \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:latest
```

**Практика:** установить Uptime Kuma через Community Scripts, открыть в браузере, добавить первый монитор. Потом попробовать поднять второй экземпляр вручную.

**Чек-лист для самопроверки:**
- [ ] Установил хотя бы один сервис через Community Scripts
- [ ] Прочитал исходник скрипта перед запуском
- [ ] Могу установить Docker LXC вручную без скрипта
- [ ] Uptime Kuma открывается, добавлен первый монитор

---

### Глава 7: Хранилища — диски, LVM, ZFS

**Что вы узнаете:**
- какие типы хранилищ есть в Proxmox и для чего каждый;
- честное сравнение LVM-Thin и ZFS с цифрами;
- как добавить новый диск к работающему серверу.

**Цель:** разобраться с хранением данных в Proxmox.

Типы хранилищ в Proxmox:
| Тип | Для чего | Снапшоты |
|-----|---------|---------|
| Directory | ISO, бэкапы, CT-шаблоны | Нет для VM/CT |
| LVM | Быстро, просто | Нет |
| LVM-Thin | Быстро + снапшоты | Да |
| ZFS | Надёжно + снапшоты + compression | Да |
| NFS/CIFS | Сетевое хранилище | Зависит |
| Ceph | Кластерное хранилище | Да |

#### [ИЗМЕНЕНО] Честное сравнение LVM-Thin vs ZFS

```
| Параметр             | LVM-Thin              | ZFS                        |
|----------------------|-----------------------|----------------------------|
| Снапшоты             | Да (CoW)              | Да (CoW)                   |
| Overhead на RAM      | ~10-50MB              | ~1GB на каждые 1TB данных  |
| Overhead по месту    | минимальный           | +5-15% на метаданные       |
| Производительность SSD | отличная            | отличная + сжатие бесплатно|
| Производительность HDD | хорошая             | медленнее без ARC-кэша     |
| RAID из коробки      | нет (нужен mdadm)     | Да (mirror, RAIDZ)         |
| Проверка целостности | нет                   | Да (checksums + scrub)     |
| Сжатие данных        | нет                   | Да (lz4, zstd — прозрачно) |
| Сложность            | низкая                | средняя                    |
| Реальный выигрыш по месту от сжатия | 0%  | 20-40% для текстов/логов  |
```

**Когда выбрать LVM-Thin:**
- Один диск (SSD).
- Мало RAM (< 8GB): ZFS ARC съест память.
- Простота важнее надёжности.
- Начинающий администратор.

**Когда выбрать ZFS:**
- Два и более диска (нужен RAID).
- Хранение критичных данных (документы, бэкапы медиатеки).
- RAM 16GB+ — можно отдать 4-8GB под ARC-кэш ZFS.
- Нужна защита от тихого повреждения данных (bitrot).

Добавить второй диск (LVM-Thin):
```bash
lsblk                         # найти новый диск (например /dev/sdb)
pvcreate /dev/sdb             # создать Physical Volume
vgcreate data-vg /dev/sdb    # создать Volume Group
lvcreate -l 100%FREE --thinpool data-pool data-vg   # создать Thin Pool

# Добавить в Proxmox: Datacenter → Storage → Add → LVM-Thin
```

Создать ZFS pool из двух дисков (mirror = RAID1):
```bash
zpool create tank mirror /dev/sdc /dev/sdd
zpool status    # убедиться что работает
zpool list      # размер и заполненность
```

**Практика:** добавить Directory-хранилище для бэкапов, проверить что оно видно в Proxmox.

**Чек-лист для самопроверки:**
- [ ] Могу объяснить разницу LVM-Thin vs ZFS по трём параметрам
- [ ] Добавил хотя бы одно дополнительное хранилище
- [ ] Понимаю почему ZFS требует больше RAM
- [ ] Знаю команды для проверки состояния LVM и ZFS

---

### Глава 8: Снапшоты и бэкапы

**Что вы узнаете:**
- в чём принципиальная разница между снапшотом и бэкапом;
- как настроить автоматические бэкапы по расписанию;
- что такое Proxmox Backup Server и когда он нужен.

**Цель:** никогда не терять данные и уметь восстанавливаться.

Разница снапшот vs бэкап:
```text
Снапшот:
- мгновенный (секунды)
- хранится на том же диске
- для быстрого отката (перед обновлением, экспериментом)
- не защищает от потери диска!

Бэкап (dump):
- полная копия в файл (минуты)
- хранится отдельно (другой диск, NAS, S3)
- защищает от потери железа
- можно перенести на другой сервер
```

Сделать снапшот:
```bash
pct snapshot 100 before-update --description "Before nginx update $(date)"
# Или через веб: CT → Snapshots → Take Snapshot
```

Откат снапшота:
```bash
pct rollback 100 before-update
# Через веб: CT → Snapshots → выбрать → Rollback
```

Настройка автоматических бэкапов:
- Datacenter → Backup → Add.
- Выбрать хранилище, расписание, режим сжатия (zstd — лучший).
- Режимы: Snapshot (быстро), Suspend (пауза), Stop (остановить — надёжнее всего).
- Retention: keep 7 daily, 4 weekly, 3 monthly.

Рекомендуемое расписание:
```text
Ежедневно в 03:00: автоматический бэкап на второй диск
Раз в месяц: тестовое восстановление бэкапа (обязательно!)
```

Восстановление из бэкапа:
```bash
pct restore 100 /mnt/backup/dump/vzdump-lxc-100-2026_05_22.tar.zst \
  --storage local-lvm
```

#### [ИЗМЕНЕНО] Proxmox Backup Server (PBS) — инкрементальные бэкапы

PBS — отдельный проект Proxmox для продвинутых бэкапов. Преимущества перед vzdump:

| | vzdump | PBS |
|---|---|---|
| Тип | Полный бэкап каждый раз | Инкрементальный (только изменения) |
| Место | Много (N × полный размер) | Мало (дедупликация + delta) |
| Скорость повторного бэкапа | Медленно | Быстро |
| Верификация | Нет | Встроенная |
| Сложность | Просто | Сложнее |

Установка PBS через Community Scripts:
```bash
bash -c "$(curl -fsSL https://community-scripts.org/ct/proxmox-backup-server.sh)"
```

Подключить PBS к Proxmox: Datacenter → Storage → Add → Proxmox Backup Server → указать IP и datastore.

Для домашнего сервера с 2-3 контейнерами — vzdump достаточно. PBS выгоден когда контейнеров много или данные меняются редко (экономия места значительная).

**Практика:** сделать снапшот LXC-контейнера, изменить что-то внутри, откатить снапшот.

**Чек-лист для самопроверки:**
- [ ] Сделал снапшот и успешно откатился
- [ ] Настроен автоматический бэкап по расписанию
- [ ] Понимаю разницу между Snapshot/Suspend/Stop режимами бэкапа
- [ ] Знаю как восстановить контейнер из файла бэкапа командой

---

### Глава 9: Сеть в Proxmox

**Что вы узнаете:**
- как устроена сетевая модель Proxmox (bridge, veth);
- как назначать статические IP контейнерам;
- как изолировать сервисы через VLAN.

**Цель:** понять сетевую модель и настроить типовые схемы.

Основные понятия:
- `vmbr0` — виртуальный мост (bridge), к которому подключаются VM и LXC.
- Физический интерфейс (enp3s0) → мост vmbr0 → VM/LXC через виртуальные интерфейсы veth.

Типовая конфигурация `/etc/network/interfaces`:
```
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    bridge-ports enp3s0
    bridge-stp off
    bridge-fd 0
```

Назначить статический IP контейнеру:
```bash
# В конфиге LXC /etc/pve/lxc/100.conf:
net0: name=eth0,bridge=vmbr0,hwaddr=...,ip=192.168.1.101/24,gw=192.168.1.1,type=veth
```

Статический IP предпочтительнее DHCP для серверов — IP не меняется после перезагрузки роутера.

Встроенный Firewall: Datacenter → Firewall → включить, добавить правила на уровне VM/LXC.

#### [ИЗМЕНЕНО] VLAN и изоляция сетей

Зачем изолировать Home Assistant:
- HA управляет физическими устройствами (розетки, замки, камеры).
- IoT устройства часто имеют уязвимости и годами не обновляются.
- Изоляция в VLAN 30 — HA может управлять устройствами, но не может выйти в основную сеть.

Схема трёх VLAN:
```
VLAN 10 — Management (192.168.10.0/24): Proxmox :8006, SSH
VLAN 20 — Services (192.168.20.0/24): Nextcloud, Gitea, рабочие серверы
VLAN 30 — IoT (192.168.30.0/24): Home Assistant, умные устройства
```

Настройка VLAN на мосту `/etc/network/interfaces`:
```
auto vmbr0
iface vmbr0 inet manual
    bridge-ports enp3s0
    bridge-stp off
    bridge-fd 0
    bridge-vids 2-4094

auto vmbr0.10
iface vmbr0.10 inet static
    address 192.168.10.1/24

auto vmbr0.20
iface vmbr0.20 inet static
    address 192.168.20.1/24

auto vmbr0.30
iface vmbr0.30 inet static
    address 192.168.30.1/24
```

Назначить VLAN контейнеру (tag=30 — IoT сегмент):
```bash
# В /etc/pve/lxc/200.conf (Home Assistant LXC)
net0: name=eth0,bridge=vmbr0,tag=30,ip=192.168.30.10/24,gw=192.168.30.1,type=veth
```

**Практика:** назначить статический IP двум LXC-контейнерам, проверить пинг между ними.

**Чек-лист для самопроверки:**
- [ ] Понимаю схему: физический интерфейс → vmbr0 → veth → LXC
- [ ] Настроил статический IP хотя бы одному контейнеру
- [ ] Понимаю зачем нужны VLAN и что такое тег сети
- [ ] Знаю как включить встроенный Firewall

---

### [ИЗМЕНЕНО] Глава 10: PCI Passthrough и GPU

**Что вы узнаете:**
- что такое PCI passthrough и когда он нужен;
- как включить IOMMU и пробросить GPU в VM;
- типичные ошибки и как их исправить.

**Цель:** пробросить физическое устройство (GPU, USB-контроллер) напрямую в VM для аппаратного транскодирования (Jellyfin), Windows-игровой VM или ML-задач.

Что такое IOMMU:
- IOMMU (Input/Output Memory Management Unit) — технология изоляции устройств.
- Позволяет передать физическое PCI-устройство напрямую в VM, минуя хост.
- Требует поддержки в CPU и BIOS (VT-d для Intel, AMD-Vi для AMD).

Включение IOMMU в GRUB:
```bash
# Для Intel — редактировать /etc/default/grub:
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"

# Для AMD:
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"

# Применить
update-grub
reboot
```

Проверка что IOMMU работает:
```bash
dmesg | grep -e DMAR -e IOMMU | head -10
# Должна быть строка: "DMAR: IOMMU enabled" или "AMD-Vi: AMD IOMMUv2 loaded"

# Посмотреть группы IOMMU (устройства в одной группе пробрасываются вместе)
find /sys/kernel/iommu_groups/ -type l | sort -V | head -30
```

Blacklist драйвера GPU на хосте (чтобы Proxmox не захватил GPU):
```bash
echo "blacklist nouveau" >> /etc/modprobe.d/blacklist.conf
echo "blacklist nvidia" >> /etc/modprobe.d/blacklist.conf
# Для AMD GPU:
echo "blacklist amdgpu" >> /etc/modprobe.d/blacklist.conf

update-initramfs -u
reboot
```

Добавить GPU в VM:
- VM должна быть остановлена.
- VM → Hardware → Add → PCI Device → выбрать нужное устройство.
- Включить "All Functions" и "PCI-Express" если доступно.

Jellyfin + GPU passthrough:
- Нужно для аппаратного транскодирования h264/h265, особенно при стриминге 4K.
- Без GPU — Jellyfin использует CPU, нагрузка высокая.
- С GPU passthrough — транскодирование в 10-20 раз быстрее.

Типичные ошибки:
| Ошибка | Причина | Решение |
|--------|---------|---------|
| `No IOMMU groups found` | IOMMU не включён | Проверить BIOS (VT-d/AMD-Vi) и GRUB |
| `Device is in use` | Хост использует GPU | Добавить в blacklist |
| VM не стартует после добавления PCI | Устройства в одной IOMMU группе | Пробросить все устройства группы |
| GPU не видно в VM | Нет драйверов в гостевой ОС | Установить драйверы NVIDIA/AMD |

Когда PCI passthrough НЕ нужен:
- Домашний Jellyfin без 4K контента — software transcoding достаточно.
- Нет подходящего GPU (встроенная графика CPU обычно подходит для простого транскодирования).
- Только один пользователь стримит.

**Практика:** проверить поддержку IOMMU на своём хосте командами выше. Если есть GPU — попробовать пробросить в тестовую VM.

**Чек-лист для самопроверки:**
- [ ] Проверил включён ли IOMMU (dmesg)
- [ ] Понимаю зачем нужен blacklist драйвера на хосте
- [ ] Знаю что такое IOMMU группы и почему важно пробрасывать всю группу
- [ ] Понимаю когда passthrough нужен, а когда достаточно software transcoding

---

### Глава 11: Удалённый доступ через Tailscale

**Что вы узнаете:**
- почему нельзя открывать порт 8006 в интернет;
- как установить Tailscale на Proxmox и получить доступ с телефона;
- как открыть доступ ко всей домашней сети через subnet routing.

**Цель:** безопасно обращаться к Proxmox и контейнерам из любой точки без открытых портов.

Почему не открывать порт 8006 в интернет:
- Proxmox веб-интерфейс не должен быть публичным.
- Боты сканируют порты 8006, 22, 80, 443 — это факт, не паранойя.
- Tailscale создаёт приватную сеть поверх интернета (WireGuard под капотом).

Установка Tailscale на хост Proxmox:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
# Открыть ссылку для авторизации в браузере
tailscale ip -4    # узнать свой Tailscale IP
```

Доступ к Proxmox по Tailscale IP:
```
https://100.x.x.x:8006
```

Subnet routing — открыть доступ ко всей домашней сети:
```bash
# Proxmox становится gateway для всей сети 192.168.1.0/24
tailscale up --advertise-routes=192.168.1.0/24
# В консоли Tailscale admin: одобрить маршрут для устройства
```

После этого с телефона через Tailscale можно обращаться ко всем устройствам домашней сети по их IP.

**Практика:** установить Tailscale на Proxmox, зайти в веб-интерфейс через Tailscale IP с телефона.

**Чек-лист для самопроверки:**
- [ ] Tailscale установлен, хост виден в admin-консоли
- [ ] Веб-интерфейс Proxmox открывается через Tailscale IP
- [ ] Понимаю разницу: открытый порт в интернет vs Tailscale туннель
- [ ] (опционально) Subnet routing настроен

---

### Глава 12: Типовые сценарии — запускаем реальные сервисы

**Что вы узнаете:**
- как развернуть Home Assistant OS в VM;
- как организовать Docker-сервисы за Nginx Proxy Manager;
- как получить бесплатный HTTPS-сертификат через Let's Encrypt.

**Цель:** показать как выглядит реальный домашний сервер на Proxmox.

#### Сценарий 1: Home Assistant OS

```bash
# Community Scripts создаёт VM с HAOS автоматически
bash -c "$(curl -fsSL https://community-scripts.org/vm-scripts/haos-vm.sh)"
```

Или вручную:
```bash
# Скачать HAOS образ, создать VM без диска
qm importdisk 200 haos_ova-12.3.qcow2 local-lvm
# Сделать диск bootable: VM → Hardware → Hard Disk → Options → Boot Order
```

#### Сценарий 2: Docker-сервер (Nextcloud, Jellyfin)

```bash
# LXC с Docker через Community Scripts
bash -c "$(curl -fsSL https://community-scripts.org/ct/docker.sh)"

# Внутри LXC
docker run -d --name nextcloud -p 8080:80 nextcloud
docker run -d --name jellyfin -p 8096:8096 jellyfin/jellyfin
```

#### Сценарий 3: Nginx Proxy Manager как точка входа

```
Интернет → 80/443 → Nginx Proxy Manager LXC
    ├── cloud.myserver.com → Nextcloud LXC :8080
    ├── ha.myserver.com    → Home Assistant VM :8123
    └── media.myserver.com → Jellyfin LXC :8096
```

#### [ИЗМЕНЕНО] Сценарий 4: ACME / Let's Encrypt через Nginx Proxy Manager

Почему самоподписанные сертификаты — плохо:
- Браузер показывает «Небезопасно» — пугает пользователей и усложняет работу.
- Мобильные приложения (Home Assistant Companion) часто отказываются работать с self-signed.

Получить бесплатный сертификат через NPM:
1. Нужен публичный домен (например бесплатный DuckDNS: duckdns.org).
2. В NPM: SSL → Request new certificate → Let's Encrypt.
3. Метод DNS-01 через DuckDNS API — не нужен открытый порт 80.
4. NPM автоматически обновляет сертификаты каждые 90 дней.

Итог: `https://myserver.duckdns.org` с зелёным замком, даже без публичного IP — через Tailscale.

#### Сценарий 5: Итоговая схема домашнего сервера

```
Proxmox Host (16GB RAM, 512GB SSD + 2TB HDD)
├── CT 100: Docker LXC (3GB) — Nextcloud, Jellyfin, Portainer
├── CT 101: Nginx Proxy Manager (512MB) — HTTPS + Let's Encrypt
├── CT 102: AdGuard Home (256MB) — DNS + блокировка рекламы
├── CT 103: Uptime Kuma (256MB) — мониторинг сервисов
├── VM 200: Home Assistant OS (2GB balloon) — умный дом
└── Backup: 2TB HDD → ежедневные бэкапы, 7 копий
```

**Практика:** спланировать своё распределение ресурсов по шаблону выше.

**Чек-лист для самопроверки:**
- [ ] Запущен хотя бы один реальный сервис (Nextcloud, HA или Jellyfin)
- [ ] Nginx Proxy Manager проксирует хотя бы один сервис
- [ ] Настроен Let's Encrypt сертификат (или понимаю как это сделать)
- [ ] Схема сервера задокументирована

---

### Глава 13: Обслуживание и мониторинг

**Что вы узнаете:**
- как правильно обновлять Proxmox и контейнеры;
- как установить мониторинг хоста через Netdata;
- как безопасно делать мажорные обновления (7→8, 8→9).

**Цель:** правильно обновлять Proxmox и контейнеры, видеть состояние системы.

Обновление хоста Proxmox:
```bash
apt update && apt full-upgrade -y
pveam update  # обновить список шаблонов LXC
```

Обновление всех LXC-контейнеров одной командой:
```bash
for ct in $(pct list | awk 'NR>1 {print $1}'); do
  echo "=== Updating CT $ct ==="
  pct exec $ct -- bash -c "apt update && apt upgrade -y" 2>/dev/null || true
done
```

#### [ИЗМЕНЕНО] Мониторинг хоста — Netdata

Netdata — лёгкий агент мониторинга с красивым веб-интерфейсом в реальном времени. Показывает: CPU, RAM, диски, сеть, процессы — без настройки.

Установка через Community Scripts:
```bash
bash -c "$(curl -fsSL https://community-scripts.org/ct/netdata.sh)"
```

Или вручную в LXC:
```bash
wget -O /tmp/netdata-kickstart.sh https://get.netdata.cloud/kickstart.sh
sh /tmp/netdata-kickstart.sh --stable-channel --disable-telemetry
```

Открыть: `http://IP-LXC:19999`

Что мониторить обязательно:
- `disk_space./` — место на системном диске (алерт > 85%)
- `mem.available` — доступная память
- `system.load` — средняя нагрузка
- `net.eth0` — входящий/исходящий трафик

#### [ИЗМЕНЕНО] Мажорные обновления Proxmox (7→8, 8→9)

Мажорное обновление — это не просто `apt upgrade`. Нужна подготовка.

```bash
# Шаг 1: Заморозить текущее ядро (не обновлять автоматически)
apt-mark hold pve-kernel-$(uname -r)

# Шаг 2: Сделать снапшоты всех VM и LXC
for vmid in $(qm list | awk 'NR>1 {print $1}'); do
  qm snapshot $vmid pre-upgrade --description "Before PVE upgrade $(date +%Y-%m-%d)"
done
for ctid in $(pct list | awk 'NR>1 {print $1}'); do
  pct snapshot $ctid pre-upgrade --description "Before PVE upgrade $(date +%Y-%m-%d)"
done

# Шаг 3: Следовать официальному upgrade guide
# https://pve.proxmox.com/wiki/Upgrade_from_8_to_9

# Шаг 4: После успешного обновления разморозить ядро
apt-mark unhold pve-kernel-*
```

Если обновление сломалось — загрузиться со старым ядром через GRUB → Advanced Options.

Полезные команды диагностики:
```bash
pveversion           # версия Proxmox
qm list              # список VM
pct list             # список LXC
pvesm status         # состояние хранилищ
journalctl -f        # логи в реальном времени
```

**Практика:** установить Netdata, открыть дашборд, написать cron-скрипт обновления всех LXC.

**Чек-лист для самопроверки:**
- [ ] Netdata установлен и открывается в браузере
- [ ] Написан и добавлен в cron скрипт обновления всех LXC
- [ ] Понимаю разницу между обычным и мажорным обновлением
- [ ] Знаю как заморозить ядро командой apt-mark hold

---

### [ИЗМЕНЕНО] Глава 14: Автоматизация и инфраструктура как код

**Что вы узнаете:**
- почему кликать в веб-интерфейс — это технический долг;
- как управлять Proxmox через API и Ansible;
- как написать idempotent bash-скрипт создания LXC.

**Цель:** перейти от ручных действий в веб-интерфейсе к воспроизводимой инфраструктуре.

Почему кликать в интерфейс — это технический долг:
- После 10 контейнеров ты не помнишь как создавал первый.
- Нет документации — нет воспроизводимости.
- При переезде на новый сервер придётся всё делать заново вручную.
- IaC = документация + воспроизводимость + история изменений.

#### Proxmox API через pvesh

```bash
pvesh get /nodes                         # список узлов кластера
pvesh get /nodes/proxmox/qemu           # список VM
pvesh get /nodes/proxmox/lxc           # список LXC

# Создать LXC через API (то же что кнопки в веб-интерфейсе)
pvesh create /nodes/proxmox/lxc \
  --vmid 200 \
  --hostname myapp \
  --ostemplate local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --memory 512 \
  --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.200/24,gw=192.168.1.1 \
  --storage local-lvm \
  --rootfs local-lvm:8
```

#### Хранить /etc/pve/ в Git — это уже IaC

```bash
# /etc/pve/ содержит всю конфигурацию Proxmox: LXC конфиги, VM, сеть, storage
cd /etc/pve
git init
git add .
git commit -m "initial: current proxmox state $(date +%Y-%m-%d)"

# После каждого изменения — коммит
git add -A && git commit -m "add ct-100 docker-lxc"
```

#### Ansible — модуль community.general.proxmox

```yaml
# playbook: create-docker-lxc.yml
- name: Create Docker LXC
  hosts: proxmox
  tasks:
    - name: Create LXC container
      community.general.proxmox:
        api_host: "{{ proxmox_host }}"
        api_user: "root@pam"
        api_token_id: "ansible"
        api_token_secret: "{{ proxmox_token }}"
        vmid: 100
        hostname: docker-01
        ostemplate: "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
        memory: 2048
        cores: 2
        storage: local-lvm
        disk: "local-lvm:8"
        netif: '{"net0":"name=eth0,bridge=vmbr0,ip=192.168.1.101/24,gw=192.168.1.1"}'
        features: "keyctl=1,nesting=1"
        state: present
```

#### Terraform (направление для роста)

Существует провайдер `bpg/proxmox` для Terraform — позволяет описывать VM и LXC как код:
```hcl
resource "proxmox_virtual_environment_container" "docker" {
  node_name = "proxmox"
  vm_id     = 100
  # ...
}
```

Подходит для продвинутого уровня и корпоративного использования. Изучить после освоения основ Terraform.

#### Bash-скрипт idempotent создания LXC с Docker

```bash
#!/bin/bash
# create-docker-lxc.sh — idempotent: повторный запуск безопасен

VMID=100
HOSTNAME="docker-01"
MEMORY=2048
CORES=2
STORAGE="local-lvm"
DISK_SIZE=20
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
IP="192.168.1.101/24"
GW="192.168.1.1"

# Проверить — уже существует?
if pct status $VMID &>/dev/null; then
  echo "LXC $VMID already exists, skipping creation"
else
  echo "Creating LXC $VMID..."
  pct create $VMID $TEMPLATE \
    --hostname $HOSTNAME \
    --memory $MEMORY \
    --cores $CORES \
    --net0 name=eth0,bridge=vmbr0,ip=$IP,gw=$GW \
    --storage $STORAGE \
    --rootfs $STORAGE:$DISK_SIZE \
    --features keyctl=1,nesting=1 \
    --unprivileged 0
fi

# Запустить если не запущен
if [ "$(pct status $VMID | awk '{print $2}')" != "running" ]; then
  pct start $VMID
  sleep 5
fi

# Установить Docker если не установлен
if ! pct exec $VMID -- which docker &>/dev/null; then
  echo "Installing Docker in LXC $VMID..."
  pct exec $VMID -- bash -c "curl -fsSL https://get.docker.com | sh"
  pct exec $VMID -- systemctl enable --now docker
fi

echo "Done. LXC $VMID is ready with Docker."
pct status $VMID
```

**Практика:** написать idempotent bash-скрипт, запустить его дважды и убедиться что второй запуск ничего не сломал.

**Чек-лист для самопроверки:**
- [ ] Выполнил хотя бы один `pvesh get` запрос к API
- [ ] `/etc/pve` добавлен в git репозиторий
- [ ] Написан idempotent bash-скрипт создания LXC
- [ ] Понимаю зачем нужна идемпотентность в скриптах

---

### Глава 15: Введение в кластеризацию

**Что вы узнаете:**
- что такое кластер Proxmox и зачем он нужен;
- минимальные требования для кластера;
- когда кластер нужен, а когда достаточно одного узла.

**Цель:** понять что такое кластер Proxmox и когда он нужен — не настраивать, но знать куда расти.

Что такое кластер:
- Несколько серверов Proxmox объединены в один кластер.
- Общее управление через один веб-интерфейс.
- Живая миграция VM между узлами без остановки.
- High Availability (HA) — VM автоматически перезапускается на другом узле при сбое.

Минимум для кластера: 3 узла (quorum — голосование при сбое).

Shared storage для кластера:
- Ceph — встроенное в Proxmox распределённое хранилище.
- NFS/iSCSI — внешний NAS.

Когда думать о кластере:
- Есть несколько физических серверов.
- Нужна высокая доступность (сервисы не должны падать при сбое одного сервера).

Для домашнего использования: один узел + хорошие бэкапы = достаточно.

**Практика:** ознакомиться с разделом Datacenter → HA в интерфейсе.

**Чек-лист для самопроверки:**
- [ ] Понимаю зачем нужен quorum из 3 узлов
- [ ] Знаю разницу между HA и обычным кластером
- [ ] Понимаю когда кластер избыточен для домашнего сервера

---

### Глава 16: Миграция с Ubuntu на Proxmox

**Что вы узнаете:**
- два подхода к миграции с Ubuntu на Proxmox;
- как перенести Docker-стек в LXC;
- типичные ловушки при переносе.

**Цель:** помочь тем, кто уже имеет работающий сервер на Ubuntu, перейти на Proxmox.

Два подхода:

**Подход 1: Новый сервер (рекомендуется)**
- Установить Proxmox на новое железо.
- Перенести сервисы по одному в LXC/VM.
- Проверить работу, выключить старый сервер.

**Подход 2: Переустановка на том же железе**
- Создать бэкап данных (не всей Ubuntu, а данных сервисов).
- Установить Proxmox на тот же сервер.
- Восстановить сервисы из бэкапа в LXC.

Перенос Docker-стека:
```bash
# На старом Ubuntu-сервере
docker compose down
tar -czf myservice-data.tar.gz ./data ./config ./.env

# Скопировать на новый LXC
scp myservice-data.tar.gz root@192.168.1.101:/opt/

# На новом LXC с Docker
cd /opt && tar -xzf myservice-data.tar.gz
docker compose up -d
```

Типичные ловушки при миграции:
- IP-адреса изменились — обновить DNS-записи.
- Пути к файлам другие — обновить переменные в конфигах.
- Переменные окружения — проверить `.env` файл.
- Порты — убедиться что нет конфликтов.

**Практика:** написать чеклист миграции одного сервиса (минимум 8 пунктов).

**Чек-лист для самопроверки:**
- [ ] Знаю два подхода к миграции и их отличия
- [ ] Могу перенести docker-compose стек в LXC
- [ ] Понимаю типичные ловушки (IP, пути, переменные)
- [ ] Написал чеклист миграции для своего случая

---

### Глава 17: Безопасность Proxmox

**Что вы узнаете:**
- что сделать сразу после установки для защиты сервера;
- как настроить двухфакторную аутентификацию;
- схему zero-trust изоляции сетей для домашнего сервера.

**Цель:** базовая защита сервера от типичных угроз.

Что делать сразу после установки:
```bash
# Сменить пароль root (если стандартный)
passwd

# Отключить SSH root по паролю — только ключи
sed -i 's/^#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd
```

Двухфакторная аутентификация (TFA):
- Datacenter → Users → выбрать пользователя → TFA.
- Поддерживает TOTP (Google Authenticator, Authy).
- Обязательно для пользователей с доступом из интернета.

Fail2ban против брутфорса:
```bash
apt install fail2ban -y
# Jail для pvedaemon (Proxmox auth)
cat > /etc/fail2ban/jail.d/proxmox.conf << 'EOF'
[proxmox]
enabled = true
port = https,8006
filter = proxmox
logpath = /var/log/daemon.log
maxretry = 3
bantime = 3600
EOF
systemctl restart fail2ban
```

Firewall правила:
```
Datacenter → Firewall → Enable
Правила:
  ACCEPT  TCP 8006  source: Tailscale IP (100.x.x.x/8)
  ACCEPT  TCP 22    source: Tailscale IP
  DROP    ALL       (всё остальное входящее)
```

#### [ИЗМЕНЕНО] VLAN и Firewall: схема zero-trust для домашнего сервера

Zero-trust — каждый сегмент сети не доверяет другому по умолчанию. Трафик разрешается явно, а не запрещается выборочно.

```
VLAN 10 (Management, 192.168.10.0/24):
  → Proxmox веб-интерфейс :8006, SSH :22
  → Доступ ТОЛЬКО через Tailscale или с доверенных IP

VLAN 20 (Services, 192.168.20.0/24):
  → Nextcloud, Gitea, Vaultwarden
  → Доступ из LAN и через NPM+HTTPS
  → Не имеет доступа к VLAN 10

VLAN 30 (IoT, 192.168.30.0/24):
  → Home Assistant, умные розетки, камеры
  → НЕ может ходить в VLAN 10 или 20
  → Интернет — только через NPM (конкретные порты)
```

Правила Proxmox Firewall для VLAN 30 (IoT — максимальная изоляция):
```
IN  ACCEPT TCP dport=8123  # Home Assistant web
IN  ACCEPT TCP dport=1883  # MQTT broker
OUT DROP   dest=192.168.10.0/24  # нет доступа к management
OUT DROP   dest=192.168.20.0/24  # нет доступа к сервисам
OUT ACCEPT dest=0.0.0.0/0        # интернет разрешён
```

Мониторинг попыток входа:
```bash
grep "pvedaemon" /var/log/syslog | grep "authentication failure"
journalctl -u sshd | grep "Failed"
fail2ban-client status proxmox    # статус бана
```

**Практика:** настроить TFA для учётной записи. Включить Firewall с базовыми правилами.

**Чек-лист для самопроверки:**
- [ ] SSH root по паролю отключён
- [ ] TFA включён для основного пользователя
- [ ] Fail2ban установлен и настроен
- [ ] Понимаю схему zero-trust для трёх VLAN

---

### Глава 18: Обслуживание и диагностика

**Что вы узнаете:**
- как находить и решать типичные проблемы: место, CPU, диски, сеть;
- как добавить новый диск к работающему серверу;
- как клонировать контейнер и создавать шаблоны.

**Цель:** разобрать сценарии из жизни администратора — диагностика и оперативное устранение.

Формат каждого сценария:
```
Ситуация → Симптом → Диагностика → Решение → Профилактика
```

---

#### Сценарий 1: Кончилось место — Nextcloud пишет ошибки

**Симптом:** `Error while copying file to target location (copied bytes: 0)`

**Диагностика:**
```bash
df -h                                        # где кончилось место
du -sh /* 2>/dev/null | sort -rh | head -20  # топ-20 крупных папок
du -sh /var/lib/docker/*                     # место в Docker
pvesm status                                 # состояние LVM хранилищ
```

**Решение А — почистить мусор Docker:**
```bash
docker system prune -a --volumes   # удалить неиспользуемые образы и тома
journalctl --vacuum-size=100M      # урезать логи systemd
```

**Решение Б — расширить диск LXC:**
```bash
pct resize 100 rootfs +20G    # расширить корневой диск CT 100 на 20GB
# Файловая система расширяется автоматически
df -h                         # проверить
```

**Профилактика:** алерт на disk > 85%, медиафайлы хранить на HDD а не SSD.

---

#### Сценарий 2: Добавить новый физический диск к работающему серверу

```bash
lsblk                         # найти новый диск (например /dev/sdb)
parted /dev/sdb mklabel gpt
parted /dev/sdb mkpart primary 0% 100%

# Для LVM-Thin хранилища (VM/LXC):
pvcreate /dev/sdb1
vgcreate data-hdd /dev/sdb1
lvcreate -l 100%FREE --thinpool data-pool data-hdd
# Datacenter → Storage → Add → LVM-Thin

# Для бэкапов (Directory):
mkfs.ext4 /dev/sdb1
mkdir /mnt/backup-hdd
echo "/dev/sdb1 /mnt/backup-hdd ext4 defaults 0 2" >> /etc/fstab
mount -a
# Datacenter → Storage → Add → Directory
```

---

#### Сценарий 3: Контейнер не запускается

**Диагностика:**
```bash
pct start 100                       # смотреть вывод ошибки
journalctl -u pve-container@100     # журнал контейнера
cat /etc/pve/lxc/100.conf           # проверить конфиг
pvesm status                        # хранилище доступно?
```

| Причина | Симптом | Решение |
|---------|---------|---------|
| Хранилище offline | `storage 'local-lvm' is not online` | `pvesm status`, перемонтировать |
| Нет места | `No space left on device` | Очистить место |
| Сломан конфиг | `parse error in config` | Исправить `/etc/pve/lxc/100.conf` |
| Занят veth | `veth already exists` | `ip link delete veth100i0` |

---

#### Сценарий 4: VM зависла — не реагирует

```bash
qm status 200             # текущий статус
qm guest cmd 200 shutdown # мягкий shutdown через guest agent
qm reset 200              # жёсткий Reset (как кнопка на корпусе)
qm stop 200 --skiplock    # принудительная остановка
qm start 200
```

---

#### Сценарий 5: Потерял доступ к веб-интерфейсу

```bash
# С другого устройства:
ping 192.168.1.100             # сервер живёт?
nmap -p 8006,22 192.168.1.100  # порты открыты?

# Физически или через IPMI — войти в консоль сервера:
systemctl status pveproxy      # веб-сервис работает?
systemctl restart pveproxy     # перезапустить
```

**Профилактика:** статический IP, Tailscale как резервный канал.

---

#### Сценарий 6: CPU 100% — кто виноват?

```bash
htop                                         # общая картина
pct exec 100 -- top -bn1 | head -20         # топ процессов в LXC 100
# В веб-интерфейсе: каждый CT/VM показывает свой % CPU

# Ограничить виновный контейнер:
pct set 100 -cpuunits 256    # снизить приоритет (по умолчанию 1024)
```

---

#### Сценарий 7: Диск умирает — SMART предупреждения

```bash
apt install smartmontools -y
smartctl -H /dev/sda          # PASSED или FAILED?
smartctl -a /dev/sda          # полный отчёт

# Критичные атрибуты (ненулевые значения — опасно):
# Reallocated_Sector_Ct, Current_Pending_Sector, Offline_Uncorrectable
```

**Если диск плохой:**
```bash
# Немедленный бэкап ВСЕГО на другое хранилище
vzdump --all --compress zstd --storage backup-hdd --mode snapshot
# Заказать новый диск
```

Автоматический мониторинг SMART:
```bash
cat > /etc/smartd.conf << 'EOF'
/dev/sda -a -o on -S on -s (S/../.././02|L/../../6/03) -m root -M exec /usr/share/smartmontools/smartd-runner
/dev/sdb -a -o on -S on -s (S/../.././02|L/../../6/03) -m root -M exec /usr/share/smartmontools/smartd-runner
EOF
systemctl enable --now smartd
```

---

#### Сценарий 8: Перенести LXC на другое хранилище

```bash
# LXC — переместить rootfs на data-hdd, старый удалить
pct move-volume 100 rootfs --storage data-hdd --delete

# VM — переместить диск
qm move-disk 200 virtio0 data-hdd --delete
```

---

#### Сценарий 9: Создать шаблон из LXC

```bash
pct stop 100                                        # остановить
pct template 100                                    # превратить в шаблон (необратимо)
pct clone 100 200 --hostname new-service --storage local-lvm  # создать копию
pct start 200
```

**Практика:** намеренно заполнить диск тестового контейнера, найти проблему и расширить диск.

**Чек-лист для самопроверки:**
- [ ] Умею расширить диск LXC командой pct resize
- [ ] Умею добавить новый физический диск и подключить к Proxmox
- [ ] Знаю как найти что занимает место и кто грузит CPU
- [ ] Создал шаблон из LXC и запустил из него новый контейнер

---

### Глава 19: Аварийное восстановление и мониторинг

**Что вы узнаете:**
- как восстановить контейнер из бэкапа — на том же и на другом сервере;
- как настроить уведомления в Telegram;
- как написать скрипты автоматических проверок.

**Цель:** выстроить систему раннего оповещения и уметь восстанавливаться в любой ситуации.

---

#### Сценарий 1: Восстановление из бэкапа — полный цикл

**На том же сервере:**
```bash
pct restore 100 /mnt/backup-hdd/dump/vzdump-lxc-100-2026_05_22.tar.zst \
  --storage local-lvm
pct start 100
```

**На другом сервере (железо сгорело):**
```bash
# Скопировать бэкап на новый сервер
scp /mnt/backup/dump/vzdump-lxc-100-*.tar.zst root@new-server:/tmp/

# Восстановить
pct restore 100 /tmp/vzdump-lxc-100-*.tar.zst --storage local-lvm

# Проверить сетевые настройки — IP может конфликтовать
cat /etc/pve/lxc/100.conf
pct start 100
```

**Тестовое восстановление (раз в месяц — обязательно):**
```bash
pct restore 999 /mnt/backup/dump/vzdump-lxc-100-*.tar.zst \
  --storage local-lvm --hostname test-restore
pct start 999
pct exec 999 -- systemctl status    # сервисы запустились?
pct exec 999 -- df -h               # данные на месте?
pct stop 999 && pct destroy 999     # удалить тестовый контейнер
```

**Правило:** непроверенный бэкап — не бэкап.

---

#### Сценарий 2: Настройка уведомлений в Telegram

**Создать бота и скрипт уведомлений:**
```bash
# Создать Telegram бота: @BotFather → /newbot → получить TOKEN
# CHAT_ID: написать боту, открыть api.telegram.org/botTOKEN/getUpdates

cat > /usr/local/bin/tg-notify << 'EOF'
#!/bin/bash
TOKEN="ваш_токен_бота"
CHAT_ID="ваш_chat_id"
curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=$1" \
  -d "parse_mode=HTML" > /dev/null
EOF
chmod +x /usr/local/bin/tg-notify

# Проверить
tg-notify "✅ Proxmox test message from $(hostname)"
```

**Email через встроенные уведомления Proxmox:**
- Datacenter → Notifications → Add → Sendmail или SMTP.
- Настроить relay через Gmail/Яндекс с app-password.

**Uptime Kuma + Telegram (самый простой вариант):**
- Settings → Notifications → Add → Telegram.
- Добавить HTTP-мониторы для каждого сервиса.
- Uptime Kuma сам шлёт уведомление при недоступности.

---

#### Сценарий 3: Автоматические проверки — cron-скрипты

**Скрипт 1: Healthcheck — перезапустить упавший контейнер и уведомить:**
```bash
cat > /usr/local/bin/pve-healthcheck << 'EOF'
#!/bin/bash
REQUIRED_CTS="100 101 102 103"   # список обязательных контейнеров

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
echo "*/5 * * * * root /usr/local/bin/pve-healthcheck" > /etc/cron.d/pve-healthcheck
```

**Скрипт 2: Мониторинг места на дисках:**
```bash
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
echo "0 8 * * * root /usr/local/bin/pve-diskcheck" > /etc/cron.d/pve-diskcheck
```

**Скрипт 3: Ежедневный отчёт каждое утро:**
```bash
cat > /usr/local/bin/pve-dailyreport << 'EOF'
#!/bin/bash
CT_COUNT=$(pct list | grep running | wc -l)
VM_COUNT=$(qm list | grep running | wc -l)
RAM_USED=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
DISK=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')

tg-notify "📊 <b>Proxmox Daily — $(hostname)</b>
Uptime: $(uptime -p)
RAM: ${RAM_USED}
Disk: ${DISK}
Running: ${CT_COUNT} CT, ${VM_COUNT} VM"
EOF
chmod +x /usr/local/bin/pve-dailyreport
echo "0 9 * * * root /usr/local/bin/pve-dailyreport" > /etc/cron.d/pve-dailyreport
```

---

#### Сценарий 4: После обновления Proxmox не загружается

```bash
# При загрузке: Shift/Esc → GRUB → Advanced → выбрать старое ядро

# После успешной загрузки — не удалять старое ядро:
dpkg --list | grep linux-image    # список установленных ядер
# apt-mark hold pve-kernel-X.Y.Z — заморозить проблемное ядро

# Когда проблема решена:
apt-mark unhold pve-kernel-*
```

---

#### Сценарий 5: Слишком много логов — очистить место

```bash
du -sh /var/log/* | sort -rh | head -10    # найти виновника

journalctl --vacuum-size=200M              # оставить не более 200MB
journalctl --vacuum-time=7d               # или не старше 7 дней

# Настроить лимит навсегда
sed -i 's/#SystemMaxUse=/SystemMaxUse=500M/' /etc/systemd/journald.conf
systemctl restart systemd-journald
```

**Практика:** настроить все три cron-скрипта. Убедиться что в Telegram приходят уведомления.

**Чек-лист для самопроверки:**
- [ ] Восстановил контейнер из бэкапа командой pct restore
- [ ] Провёл тестовое восстановление под ID 999
- [ ] Telegram бот настроен, уведомление приходит
- [ ] Три cron-скрипта работают (healthcheck, diskcheck, dailyreport)
- [ ] Знаю как загрузиться со старым ядром через GRUB

---

### Глава 20: Итоговый проект

**Что вы узнаете:**
- как применить всё из книги на реальном сервере;
- какой должна быть финальная схема домашнего сервера.

**Цель:** с нуля до работающего домашнего сервера.

Сценарий: мини-ПК (Intel NUC, Beelink, Minisforum) с 16GB RAM и 512GB SSD + 2TB HDD.

Задания:
1. Установить Proxmox VE, отключить enterprise репозиторий.
2. Добавить 2TB HDD как Directory-хранилище для бэкапов.
3. Создать LXC с Docker через Community Scripts.
4. Запустить Nextcloud внутри Docker-LXC.
5. Установить Nginx Proxy Manager в отдельном LXC.
6. Получить Let's Encrypt сертификат через DuckDNS.
7. Установить Tailscale на хост.
8. Настроить автоматические бэкапы на HDD с retention 7 daily.
9. Сделать снапшот Docker-LXC, что-то сломать, откатить.
10. Настроить три cron-скрипта (healthcheck + diskcheck + dailyreport).
11. Написать idempotent bash-скрипт создания Docker-LXC.
12. Хранить /etc/pve в git-репозитории.

Финальная схема:
```
Proxmox (192.168.1.100)
├── CT 100: Docker (3GB) — Nextcloud :8080
├── CT 101: Nginx PM (512MB) — :80/:443 + Let's Encrypt
├── CT 102: Uptime Kuma (256MB) — :3001 + Telegram alerts
├── VM 200: Home Assistant OS (2GB balloon)
├── Backup: 2TB HDD — ежедневно 03:00, 7 копий
└── Tailscale → доступ с телефона из любой точки
```

**Чек-лист для самопроверки:**
- [ ] Все сервисы запущены и открываются
- [ ] HTTPS сертификат настроен (зелёный замок)
- [ ] Бэкапы работают по расписанию
- [ ] Telegram уведомления приходят ежедневно
- [ ] /etc/pve в git, последний коммит актуален
- [ ] Idempotent скрипт написан и протестирован

---

## Обязательные сравнения

1. Ubuntu+Docker vs Proxmox+LXC — когда что выбрать.
2. LXC-контейнер vs Docker-контейнер — разница и применение.
3. KVM VM vs LXC — когда нужна полная виртуализация.
4. Снапшот vs Бэкап — разница и когда использовать.
5. LVM-Thin vs ZFS — сравнение с цифрами по RAM, месту, надёжности.
6. DHCP vs Static IP для контейнеров — рекомендации.
7. Открытый порт 8006 в интернет vs Tailscale — безопасность.
8. vzdump vs PBS — когда что выгоднее.
9. Community Scripts vs ручная установка — надёжность и контроль.

---

## Обязательные практические сценарии

**Базовые навыки:**
- Установить Proxmox с нуля.
- Создать LXC-контейнер вручную через CLI.
- Установить Docker в LXC (вручную и через Community Scripts).
- Создать KVM VM с Ubuntu Server, установить qemu-guest-agent.
- Сделать снапшот, изменить что-то, откатить.
- Настроить автоматические бэкапы с расписанием.
- Установить Tailscale на хост Proxmox.
- Запустить реальный сервис через Community Scripts.
- Обновить хост Proxmox и все контейнеры скриптом.

**Реальные проблемы (обязательно практиковать):**
- Намеренно заполнить диск → найти виновника → очистить → расширить диск LXC.
- Добавить новый диск → подключить как хранилище → перенести контейнер.
- Сделать бэкап → уничтожить контейнер → восстановить из бэкапа.
- Провести тестовое восстановление под ID 999, проверить данные, удалить.
- Проверить SMART состояние всех дисков.
- Настроить Telegram: три cron-скрипта + Uptime Kuma.
- Написать idempotent bash-скрипт создания LXC, запустить дважды.
- Хранить /etc/pve в git, сделать 3 коммита.

---

## Особые требования

### Про тон

Не писать "это просто". Для кого-то гипервизор — это страшно. Показывать каждый шаг, объяснять зачем он нужен, а не только как.

### Шаблон каждой главы

Каждая глава начинается с блока **"Что вы узнаете"** (3-4 пункта) и заканчивается **"Чек-листом для самопроверки"** (4-5 пунктов с чекбоксами `[ ]`).

### Про примеры

Примеры должны быть реальными — Home Assistant, Nextcloud, Jellyfin, Docker-стек. Не абстрактные `myvm` и `container1`.

### Про команды

Каждая команда сопровождается объяснением что она делает. Не просто `pct create 100 ...` — а "эта команда создаёт LXC-контейнер с ID 100, 1GB RAM, 2 ядра CPU, диск 8GB на хранилище local-lvm".

### Про ошибки

В каждой главе раздел "Типичные ошибки": что может пойти не так, как проявляется, как исправить.

### Критерии готовности

Книга готова, если читатель после неё:
- установил и настроил Proxmox;
- запустил минимум 2 LXC-контейнера и 1 VM;
- настроил автоматические бэкапы;
- подключил Tailscale и заходит удалённо;
- умеет делать снапшоты и откатываться;
- понимает разницу между LXC, KVM и Docker;
- написал хотя бы один bash-скрипт, idempotently создающий LXC;
- протестировал бэкап восстановлением в тестовый контейнер;
- настроил мониторинг с уведомлениями.

### Не делать

- Не пересказывать официальную документацию страницами.
- Не углубляться в Ceph и кластеры — только обзорно.
- Не объяснять основы Linux — отсылать к книге 01 с коротким напоминанием.
- Не объяснять основы Docker — отсылать к книге 03.
- Не давать команды без объяснения что они делают.
- Не углубляться в Kubernetes, OpenStack — не тема этой книги.

---

## Источники и справочные материалы

- Официальная документация: https://pve.proxmox.com/pve-docs/pve-admin-guide.html
- Community Scripts: https://community-scripts.org/
- Статья Habr (hostkey): https://habr.com/ru/companies/hostkey/articles/970842/
- Tailscale: https://tailscale.com/

---

## Приложения

### Приложение A: Шпаргалка команд

```bash
# LXC контейнеры
pct list                           # список всех LXC
pct start/stop/enter <vmid>        # управление
pct exec <vmid> -- <cmd>           # выполнить команду внутри LXC
pct snapshot <vmid> <name>         # создать снапшот
pct rollback <vmid> <name>         # откатить снапшот
pct restore <vmid> <file.tar.zst>  # восстановить из бэкапа
pct resize <vmid> rootfs +10G      # расширить диск
pct move-volume <vmid> rootfs --storage <dst>  # переместить на другое хранилище
pct template <vmid>                # превратить в шаблон
pct clone <src> <dst>              # клонировать

# KVM виртуальные машины
qm list                            # список VM
qm start/stop/reset <vmid>         # управление
qm snapshot <vmid> <name>          # снапшот
qm rollback <vmid> <name>          # откат
qm guest cmd <vmid> shutdown       # мягкий shutdown через agent

# Хранилища
pvesm status                       # статус всех хранилищ
pvesm list <storage>               # содержимое хранилища
vzdump --all --compress zstd --storage <dst>  # бэкап всего

# Хост
pveversion                         # версия Proxmox
pvesh get /nodes                   # API: список узлов
journalctl -f                      # логи в реальном времени
apt-mark hold <package>            # заморозить пакет
smartctl -H /dev/sda               # SMART статус диска
```

### Приложение B: Рекомендуемые Community Scripts

| Скрипт | Описание |
|--------|---------|
| Docker LXC | LXC + Docker + Portainer |
| Home Assistant OS | VM с официальным HAOS |
| Nginx Proxy Manager | Reverse proxy с UI + ACME |
| Vaultwarden | Self-hosted менеджер паролей |
| Uptime Kuma | Мониторинг сервисов |
| AdGuard Home | DNS + блокировка рекламы |
| Gitea | Self-hosted Git |
| Jellyfin | Медиасервер |
| Netdata | Мониторинг хоста в реальном времени |
| Proxmox Backup Server | Инкрементальные бэкапы |

### Приложение C: Рекомендуемые ресурсы

- **TechnoTim** (YouTube) — практические гайды по Proxmox на английском
- **Learn Linux TV** (YouTube) — Proxmox для начинающих
- **Proxmox Forum** — https://forum.proxmox.com/
- **r/homelab** — Reddit-сообщество домашних серверов

### [ИЗМЕНЕНО] Приложение D: Схемы типовых домашних серверов

#### Вариант 1: Budget — мини-ПК (4-6GB RAM, один SSD 128GB)

```
Proxmox Host
├── VM 200: Home Assistant OS — 1GB balloon, 2 CPU, 32GB
├── CT 101: AdGuard Home — 256MB, 1 CPU, 2GB
└── CT 102: Uptime Kuma — 256MB, 1 CPU, 4GB
```

| Контейнер | RAM лимит | CPU | Диск |
|---|---|---|---|
| HA OS (VM) | 1GB (min 512MB) | 2 | 32GB |
| AdGuard | 256MB | 1 | 2GB |
| Uptime Kuma | 256MB | 1 | 4GB |
| **Итого** | **~1.5GB** | **4** | **38GB** |

Хранилище: local-lvm (SSD). Бэкапы: USB флешка раз в неделю.
Доступ: Tailscale.

---

#### Вариант 2: Standard — 16GB RAM, SSD 512GB + HDD 2TB

```
Proxmox Host
├── CT 100: Docker LXC (3GB) — Nextcloud, Vaultwarden, Gitea
├── CT 101: Nginx Proxy Manager (512MB) — HTTPS + Let's Encrypt
├── VM 200: Home Assistant OS (2GB balloon) — VLAN 30
├── CT 102: AdGuard Home (256MB)
├── CT 103: Uptime Kuma (256MB) — Telegram alerts
└── CT 104: Jellyfin (2GB) — медиа на HDD mount
```

| Контейнер | RAM лимит | CPU | Диск |
|---|---|---|---|
| Docker LXC | 3GB | 4 | 20GB SSD |
| Nginx PM | 512MB | 1 | 5GB SSD |
| HA OS VM | 2GB balloon | 2 | 32GB SSD |
| AdGuard | 256MB | 1 | 2GB SSD |
| Uptime Kuma | 256MB | 1 | 4GB SSD |
| Jellyfin | 2GB | 4 | 10GB SSD + HDD mount |
| **Итого** | **~8GB** | **13** | **73GB SSD** |

Хранилище: LVM-Thin (SSD) + Directory (HDD для бэкапов и медиа).
Бэкапы: HDD ежедневно, 7 daily + 4 weekly.
Доступ: Tailscale + Let's Encrypt через DuckDNS.

---

#### Вариант 3: Advanced — 32GB+ RAM, ZFS mirror SSD + ZFS RAIDZ HDD, GPU

```
Proxmox Host (ZFS mirror: 2×SSD, ZFS RAIDZ: 3×HDD)
├── CT 100: Docker LXC (4GB) — Nextcloud, Gitea, Vaultwarden
├── CT 101: Nginx Proxy Manager (512MB)
├── VM 200: Home Assistant OS (2GB) — VLAN 30
├── VM 201: Windows 11 (8GB balloon + GPU passthrough)
├── CT 102: Jellyfin (2GB + GPU passthrough)
├── CT 103: Netdata + Grafana (2GB) — мониторинг хоста
├── CT 104: Proxmox Backup Server (2GB) — инкрементальные бэкапы
└── CT 105: Tailscale Subnet Router (128MB)
```

| Контейнер | RAM | CPU | Особенности |
|---|---|---|---|
| Docker LXC | 4GB | 4 | ZFS датасет для данных |
| Nginx PM | 512MB | 1 | wildcard Let's Encrypt |
| HA OS VM | 2GB balloon | 2 | VLAN 30 IoT |
| Windows VM | 8GB balloon | 8 | GPU passthrough |
| Jellyfin | 2GB | 4 | GPU passthrough, 4K transcode |
| Monitoring | 2GB | 2 | Netdata + Grafana |
| PBS | 2GB | 2 | Инкрементальные бэкапы |
| **Итого** | **~20GB** | **23** | ZFS mirror + RAIDZ |

Сеть: VLAN 10/20/30 zero-trust изоляция.
Бэкапы: PBS инкрементальные + rsync offsite.
Доступ: Tailscale + wildcard Let's Encrypt сертификат.
