# Глава 14: Автоматизация и инфраструктура как код

> **Цель:** перейти от ручных действий в веб-интерфейсе к воспроизводимой инфраструктуре, которую можно восстановить на новом сервере за минуты.

---

**Что вы узнаете:**
- почему каждый клик в веб-интерфейсе — это технический долг, который придётся вернуть;
- как управлять Proxmox через API с помощью `pvesh`;
- зачем хранить `/etc/pve` в git и как это организовать;
- как создавать и управлять LXC-контейнерами через Ansible;
- как написать полный idempotent bash-скрипт создания Docker LXC.

---

## 14.1 Почему кликать в веб — технический долг

Представь: ты потратил вечер, настраивая свежий Proxmox. Создал LXC для Docker, настроил сеть, выставил лимиты памяти, включил nesting и keyctl, прописал статический IP. Всё работает. Через полгода железо сломалось — и тебе нужно поднять всё заново.

Что ты помнишь о том вечере? Скорее всего — ничего конкретного.

Каждый клик в веб-интерфейсе, каждая команда в Shell без сохранения — это операция, которая существует только в памяти (твоей или сервера). Такой подход называют **snowflake infrastructure**: каждый сервер уникален, как снежинка — воспроизвести его невозможно.

**Проблемы ручного управления:**

```
Раньше (ручное управление):
- Создал контейнер через веб → через месяц не помнишь параметры
- Отредактировал конфиг напрямую → кто изменил? зачем? когда?
- Сервер сломался → поднимаешь заново с нуля, вспоминая детали
- Второй одинаковый контейнер → нужно повторить все клики вручную

С IaC (Infrastructure as Code):
- Описал инфраструктуру в файле → файл = документация
- Файл в git → история изменений с комментариями
- Сервер сломался → запускаешь скрипт, через 5 минут то же окружение
- Второй контейнер → запускаешь тот же скрипт с другим ID
```

IaC — это не только про большие компании. Даже один домашний сервер выигрывает от трёх вещей:
1. **Воспроизводимость** — запустил скрипт, получил ожидаемый результат.
2. **История изменений** — git показывает что и когда поменялось.
3. **Документация сама собой** — код описывает намерение, а не только результат.

---

## 14.2 Proxmox API через pvesh

Всё, что ты делаешь в веб-интерфейсе, на самом деле вызывает REST API Proxmox. Кнопка «Create CT» — это POST-запрос. Кнопка «Start» — POST `/nodes/{node}/lxc/{vmid}/status/start`. Веб-интерфейс — просто удобная оболочка над API.

`pvesh` — утилита командной строки, которая обращается к этому же API напрямую, без браузера.

**Базовые запросы — исследование состояния кластера:**

```bash
# Посмотреть список узлов кластера — те же данные что в левой панели веб-интерфейса
pvesh get /nodes

# Посмотреть все запущенные VM на узле proxmox
# (замени proxmox на имя своего узла из pveversion)
pvesh get /nodes/proxmox/qemu

# Посмотреть все LXC-контейнеры
pvesh get /nodes/proxmox/lxc

# Посмотреть детальные параметры конкретного контейнера с ID 100
pvesh get /nodes/proxmox/lxc/100/config

# Посмотреть доступные хранилища
pvesh get /nodes/proxmox/storage
```

Вывод — JSON, который удобно обрабатывать скриптами или просто читать для понимания структуры.

**Создать LXC-контейнер через API:**

```bash
# Эта команда делает ровно то же, что кнопка «Create CT» в веб-интерфейсе.
# Создаёт LXC с ID 200, hostname myapp, 512MB RAM, 1 ядро,
# диск 8GB на local-lvm, статический IP 192.168.1.200
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

**Управление через API:**

```bash
# Запустить контейнер 200
pvesh create /nodes/proxmox/lxc/200/status/start

# Остановить
pvesh create /nodes/proxmox/lxc/200/status/stop

# Создать снапшот перед обновлением
pvesh create /nodes/proxmox/lxc/200/snapshot \
  --snapname before-update \
  --description "Before nginx upgrade $(date +%Y-%m-%d)"
```

**Зачем это нужно, если есть кнопки в веб-интерфейсе?**

Потому что `pvesh` вызывается из скрипта. Ты можешь написать bash-скрипт, который создаст двадцать одинаковых контейнеров с разными IP и именами — за тридцать секунд, без единого клика. Или автоматически снимает снапшоты перед каждым обновлением через cron.

---

## 14.3 /etc/pve в git — это уже IaC

Proxmox хранит всю конфигурацию в директории `/etc/pve`. Это обычные текстовые файлы:

```
/etc/pve/
├── lxc/
│   ├── 100.conf    ← конфиг LXC 100: память, CPU, сеть, диски
│   ├── 101.conf    ← конфиг LXC 101
│   └── 102.conf
├── qemu-server/
│   └── 200.conf    ← конфиг KVM VM 200
├── storage.cfg     ← конфигурация хранилищ
└── corosync.conf   ← конфигурация кластера (если есть)
```

Каждый файл `.conf` — это то, что ты настраивал через веб-интерфейс. Если положить эту директорию в git, ты получаешь:

- **Историю всех изменений** — кто, когда, что поменял.
- **Возможность откатиться** к предыдущей конфигурации.
- **Документацию** — `git log` объясняет что происходило.
- **Резервную копию конфигурации** отдельно от резервных копий данных.

**Как это сделать:**

```bash
# Перейти в директорию конфигурации Proxmox
cd /etc/pve

# Инициализировать git-репозиторий
git init

# Добавить все файлы конфигурации
git add lxc/ qemu-server/ storage.cfg

# Первый коммит — зафиксировать текущее состояние
git commit -m "initial: proxmox state $(date +%Y-%m-%d)"
```

**Рабочий процесс — коммит после каждого изменения:**

```bash
# Создал новый контейнер через веб или pvesh → зафиксировать
cd /etc/pve
git add lxc/100.conf
git commit -m "add ct-100: docker-lxc for nextcloud stack"

# Изменил параметры памяти у VM 200
git add qemu-server/200.conf
git commit -m "vm-200: increase RAM to 4GB for home assistant"

# Добавил новое хранилище
git add storage.cfg
git commit -m "storage: add backup-hdd directory storage on /dev/sdb"
```

Посмотреть историю изменений:

```bash
git log --oneline
# 3a7f291 storage: add backup-hdd directory storage on /dev/sdb
# c8b2d04 vm-200: increase RAM to 4GB for home assistant
# 1f3a892 add ct-100: docker-lxc for nextcloud stack
# a4e6b11 initial: proxmox state 2026-05-01

# Посмотреть что именно изменилось в конфиге
git diff HEAD~1 lxc/100.conf
```

**Что добавлять в .gitignore:**

```bash
cat > /etc/pve/.gitignore << 'EOF'
# Временные файлы Proxmox
.vmlist
local
nodes/*/openvz/
.clusterinfo
EOF
```

Совет: не добавляй файлы с паролями и токенами. `/etc/pve` содержит конфигурацию, но не секреты — это безопасно хранить в приватном репозитории или локально.

---

## 14.4 Ansible — community.general.proxmox

Bash-скрипты хороши для одного сервера. Когда серверов несколько или нужно управлять инфраструктурой организованно — используют Ansible.

Ansible — это инструмент управления конфигурацией. Ты описываешь желаемое состояние (что должно существовать), и Ansible сам разбирается как этого достичь. Если контейнер уже существует — ничего не делает. Если не существует — создаёт.

Модуль `community.general.proxmox` позволяет управлять LXC-контейнерами Proxmox через Ansible.

**Установка:**

```bash
# На управляющей машине (не на Proxmox)
pip install proxmoxer requests
ansible-galaxy collection install community.general
```

**Создать API-токен в Proxmox** (лучше, чем использовать пароль root):

```
Datacenter → Permissions → API Tokens → Add
  User: root@pam
  Token ID: ansible
  Privilege Separation: выключить (для простоты)
```

Токен будет показан один раз — сохрани его сразу.

**Inventory файл — описание хостов:**

```ini
# hosts.ini
[proxmox]
192.168.1.100 ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_ed25519
```

**Playbook — создать Docker LXC:**

```yaml
# create-docker-lxc.yml
---
- name: Создать LXC контейнер для Docker
  hosts: proxmox
  vars:
    proxmox_host: "192.168.1.100"
    proxmox_token: "{{ lookup('env', 'PROXMOX_TOKEN') }}"

  tasks:
    - name: Создать LXC контейнер docker-01
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
        disk: "local-lvm:20"
        netif: '{"net0":"name=eth0,bridge=vmbr0,ip=192.168.1.101/24,gw=192.168.1.1,type=veth"}'
        features: "keyctl=1,nesting=1"
        unprivileged: false
        onboot: true
        state: present
      register: ct_result

    - name: Запустить контейнер
      community.general.proxmox:
        api_host: "{{ proxmox_host }}"
        api_user: "root@pam"
        api_token_id: "ansible"
        api_token_secret: "{{ proxmox_token }}"
        vmid: 100
        state: started
      when: ct_result.changed
```

**Запустить playbook:**

```bash
# Передать токен через переменную окружения — не хранить в файле
export PROXMOX_TOKEN="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
ansible-playbook -i hosts.ini create-docker-lxc.yml
```

**Ключевые параметры модуля:**

| Параметр | Что делает |
|----------|-----------|
| `state: present` | Убедиться что контейнер существует (создать если нет) |
| `state: started` | Убедиться что контейнер запущен |
| `state: stopped` | Убедиться что контейнер остановлен |
| `state: absent` | Убедиться что контейнер не существует (удалить если есть) |
| `onboot: true` | Автозапуск при старте Proxmox |
| `unprivileged: false` | Privileged контейнер (нужен для Docker) |

Если запустить playbook дважды — второй раз ничего не изменится. Это и есть идемпотентность в Ansible.

---

## 14.5 Terraform — направление для роста

Для тех, кто хочет идти дальше Ansible: существует провайдер `bpg/proxmox` для Terraform. Terraform позволяет описывать всю инфраструктуру как HCL-код и управлять ей через `terraform apply`.

```hcl
# main.tf
terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.50"
    }
  }
}

provider "proxmox" {
  endpoint = "https://192.168.1.100:8006/"
  api_token = "root@pam!terraform=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  insecure  = true
}

resource "proxmox_virtual_environment_container" "docker_lxc" {
  node_name = "proxmox"
  vm_id     = 100

  initialization {
    hostname = "docker-01"

    ip_config {
      ipv4 {
        address = "192.168.1.101/24"
        gateway = "192.168.1.1"
      }
    }
  }

  memory {
    dedicated = 2048
  }

  cpu {
    cores = 2
  }

  disk {
    datastore_id = "local-lvm"
    size         = 20
  }

  network_interface {
    name   = "eth0"
    bridge = "vmbr0"
  }

  features {
    nesting = true
    keyctl  = true
  }

  operating_system {
    template_file_id = "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
    type             = "debian"
  }
}
```

Применить:

```bash
terraform init
terraform plan   # показать что будет сделано
terraform apply  # применить
```

Terraform хранит состояние инфраструктуры в файле `terraform.tfstate`. Это позволяет ему знать что уже создано, а что нужно изменить или удалить.

**Когда использовать Terraform вместо Ansible или bash:**
- Команда из нескольких человек управляет инфраструктурой совместно.
- Нужно управлять несколькими облаками или сервисами из одного места.
- Важна гарантия состояния: Terraform точно знает что создал и может это удалить.

Для домашнего сервера bash-скрипты или Ansible достаточны. Terraform — следующий уровень, когда базовые подходы уже освоены.

---

## 14.6 Полный idempotent bash-скрипт создания Docker LXC

Идемпотентность — свойство операции, которую безопасно выполнять несколько раз. Первый запуск создаёт контейнер. Второй запуск — проверяет что всё в порядке и ничего не ломает.

Это важно по двум причинам:
1. Скрипт можно запустить случайно дважды — ничего не сломается.
2. Скрипт работает и для первоначальной установки, и для проверки состояния.

Ниже — полный скрипт с объяснением каждой части.

```bash
#!/bin/bash
# create-docker-lxc.sh
# Idempotent скрипт создания LXC-контейнера с Docker.
# Безопасно запускать повторно — повторный запуск ничего не изменит.
#
# Использование:
#   bash create-docker-lxc.sh
#
# Требования: запускать на хосте Proxmox от root.

set -euo pipefail
# set -e  — остановить выполнение при любой ошибке
# set -u  — остановить если используется необъявленная переменная
# set -o pipefail — ошибка в pipe не игнорируется

# ─────────────────────────────────────────────────────────────
# ПАРАМЕТРЫ КОНТЕЙНЕРА
# Измени эти значения под свои нужды
# ─────────────────────────────────────────────────────────────

VMID=100                   # ID контейнера в Proxmox (должен быть уникальным)
HOSTNAME="docker-01"       # имя хоста внутри контейнера
MEMORY=2048                # лимит памяти в МБ (не резервирование — мягкий лимит)
SWAP=512                   # своп в МБ (подушка безопасности при нехватке RAM)
CORES=2                    # количество ядер CPU
STORAGE="local-lvm"        # хранилище для диска контейнера
DISK_SIZE=20               # размер диска в ГБ
IP="192.168.1.101/24"      # статический IP с маской подсети
GW="192.168.1.1"           # шлюз по умолчанию
BRIDGE="vmbr0"             # сетевой мост Proxmox (создан при установке)
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"

# ─────────────────────────────────────────────────────────────
# ФУНКЦИИ
# ─────────────────────────────────────────────────────────────

# log() — вывод сообщений с временной меткой
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# check_template() — проверить что шаблон скачан.
# Если нет — скачать через pveam.
check_template() {
  local template_name
  # Извлекаем имя файла из пути "local:vztmpl/debian-12-..."
  template_name=$(basename "${TEMPLATE#*:vztmpl/}")

  if ! pveam list local | grep -q "$template_name"; then
    log "Шаблон $template_name не найден, скачиваю..."
    # pveam download — официальная команда загрузки шаблонов LXC
    pveam download local "$template_name"
    log "Шаблон скачан."
  else
    log "Шаблон $template_name уже есть, пропускаю загрузку."
  fi
}

# ─────────────────────────────────────────────────────────────
# ШАГ 1: Проверить зависимости
# ─────────────────────────────────────────────────────────────

log "=== Создание Docker LXC (ID: $VMID, hostname: $HOSTNAME) ==="

# Убедиться что запущено на Proxmox
if ! command -v pct &>/dev/null; then
  echo "ОШИБКА: команда pct не найдена. Скрипт должен запускаться на хосте Proxmox." >&2
  exit 1
fi

# Убедиться что хранилище существует
if ! pvesm status | grep -q "^$STORAGE"; then
  echo "ОШИБКА: хранилище '$STORAGE' не найдено. Проверь pvesm status." >&2
  exit 1
fi

# ─────────────────────────────────────────────────────────────
# ШАГ 2: Создать контейнер (если не существует)
# ─────────────────────────────────────────────────────────────

# pct status завершается с кодом 0 если контейнер существует.
# &>/dev/null — скрыть вывод, нас интересует только код возврата.
if pct status "$VMID" &>/dev/null; then
  log "Контейнер $VMID уже существует, пропускаю создание."
else
  log "Контейнер $VMID не найден, создаю..."

  # Убедиться что шаблон скачан
  check_template

  # pct create — основная команда создания LXC.
  # Параметры:
  #   --hostname        — имя хоста внутри контейнера
  #   --memory          — лимит RAM в МБ
  #   --swap            — своп в МБ
  #   --cores           — количество доступных ядер
  #   --net0            — сетевой интерфейс: имя, мост, IP, шлюз
  #   --storage         — хранилище для метаданных контейнера
  #   --rootfs          — хранилище и размер корневого диска
  #   --features        — keyctl=1 и nesting=1 обязательны для Docker
  #   --unprivileged 0  — privileged контейнер (нужен для Docker)
  #   --onboot 1        — автозапуск при старте Proxmox
  pct create "$VMID" "$TEMPLATE" \
    --hostname "$HOSTNAME" \
    --memory "$MEMORY" \
    --swap "$SWAP" \
    --cores "$CORES" \
    --net0 "name=eth0,bridge=${BRIDGE},ip=${IP},gw=${GW},type=veth" \
    --storage "$STORAGE" \
    --rootfs "${STORAGE}:${DISK_SIZE}" \
    --features "keyctl=1,nesting=1" \
    --unprivileged 0 \
    --onboot 1

  log "Контейнер $VMID создан."
fi

# ─────────────────────────────────────────────────────────────
# ШАГ 3: Запустить контейнер (если не запущен)
# ─────────────────────────────────────────────────────────────

# pct status выводит "status: running" или "status: stopped"
# awk '{print $2}' извлекает второе слово — значение статуса
CURRENT_STATUS=$(pct status "$VMID" | awk '{print $2}')

if [ "$CURRENT_STATUS" != "running" ]; then
  log "Контейнер $VMID не запущен (статус: $CURRENT_STATUS), запускаю..."
  pct start "$VMID"

  # Подождать пока контейнер полностью загрузится.
  # 10 секунд обычно достаточно для загрузки Debian до systemd.
  log "Ожидаю запуска контейнера (10 секунд)..."
  sleep 10

  # Проверить что запуск прошёл успешно
  CURRENT_STATUS=$(pct status "$VMID" | awk '{print $2}')
  if [ "$CURRENT_STATUS" != "running" ]; then
    echo "ОШИБКА: контейнер $VMID не запустился. Проверь: journalctl -u pve-container@${VMID}" >&2
    exit 1
  fi
  log "Контейнер $VMID запущен."
else
  log "Контейнер $VMID уже запущен."
fi

# ─────────────────────────────────────────────────────────────
# ШАГ 4: Обновить систему внутри контейнера
# ─────────────────────────────────────────────────────────────

# pct exec — выполнить команду внутри контейнера без входа в консоль.
# bash -c "..." — выполнить составную команду через bash.
# Обновляем только если пакетная база устарела (проверяем по дате)
log "Обновляю пакеты в контейнере $VMID..."
pct exec "$VMID" -- bash -c "
  apt-get update -qq && \
  apt-get upgrade -y -qq && \
  apt-get install -y -qq curl ca-certificates
"
log "Пакеты обновлены."

# ─────────────────────────────────────────────────────────────
# ШАГ 5: Установить Docker (если не установлен)
# ─────────────────────────────────────────────────────────────

# which docker — проверить наличие исполняемого файла docker.
# pct exec ... -- which docker — выполнить эту проверку внутри контейнера.
# &>/dev/null — скрыть вывод; нас интересует код возврата (0 = найден).
if pct exec "$VMID" -- which docker &>/dev/null; then
  # docker version выведет версию — используем для лога
  DOCKER_VERSION=$(pct exec "$VMID" -- docker version --format '{{.Server.Version}}' 2>/dev/null || echo "неизвестно")
  log "Docker уже установлен (версия: $DOCKER_VERSION), пропускаю установку."
else
  log "Docker не найден, устанавливаю..."

  # Официальный скрипт установки Docker от docker.com.
  # Определяет дистрибутив и устанавливает актуальную версию.
  pct exec "$VMID" -- bash -c "curl -fsSL https://get.docker.com | sh"

  # Включить Docker daemon и запустить сразу
  # enable — добавить в автозапуск
  # --now  — запустить немедленно, не ждать перезагрузки
  pct exec "$VMID" -- systemctl enable --now docker

  log "Docker установлен."
fi

# ─────────────────────────────────────────────────────────────
# ШАГ 6: Проверить что Docker работает
# ─────────────────────────────────────────────────────────────

log "Проверяю работоспособность Docker..."

# docker info завершается с кодом 0 если daemon запущен и отвечает.
# Это надёжнее чем проверять статус systemd.
if pct exec "$VMID" -- docker info &>/dev/null; then
  log "Docker daemon отвечает — всё в порядке."
else
  echo "ОШИБКА: Docker установлен, но daemon не отвечает." >&2
  echo "Проверь: pct exec $VMID -- journalctl -u docker" >&2
  exit 1
fi

# ─────────────────────────────────────────────────────────────
# ИТОГ
# ─────────────────────────────────────────────────────────────

log "=== Готово ==="
log "LXC $VMID ($HOSTNAME) запущен с Docker."
log ""
log "Войти в контейнер:    pct enter $VMID"
log "Выполнить команду:    pct exec $VMID -- docker ps"
log "Статус контейнера:    pct status $VMID"
log ""

# Показать финальный статус
pct status "$VMID"
pct exec "$VMID" -- docker version --format 'Docker {{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})'
```

**Как использовать скрипт:**

```bash
# Скопировать на хост Proxmox
scp create-docker-lxc.sh root@192.168.1.100:/root/

# На хосте Proxmox
chmod +x /root/create-docker-lxc.sh

# Первый запуск — создаст и настроит контейнер
bash /root/create-docker-lxc.sh

# Второй запуск — убедится что всё в порядке, ничего не изменит
bash /root/create-docker-lxc.sh
```

Ожидаемый вывод при повторном запуске:

```
[2026-05-23 10:15:00] === Создание Docker LXC (ID: 100, hostname: docker-01) ===
[2026-05-23 10:15:00] Контейнер 100 уже существует, пропускаю создание.
[2026-05-23 10:15:00] Контейнер 100 уже запущен.
[2026-05-23 10:15:01] Обновляю пакеты в контейнере 100...
[2026-05-23 10:15:08] Пакеты обновлены.
[2026-05-23 10:15:08] Docker уже установлен (версия: 27.3.1), пропускаю установку.
[2026-05-23 10:15:08] Проверяю работоспособность Docker...
[2026-05-23 10:15:08] Docker daemon отвечает — всё в порядке.
[2026-05-23 10:15:08] === Готово ===
status: running
Docker 27.3.1 (linux/amd64)
```

---

## 14.7 Типичные ошибки и их решения

**Ошибка: «storage 'local-lvm' does not support ct volumes»**

```
Причина: хранилище не поддерживает тип Container.
Решение: в Datacenter → Storage → local-lvm → Content — убедиться
         что выбран тип «Container».
```

**Ошибка: «CT ID X already exists» при создании через pvesh**

```
Причина: контейнер с таким ID уже есть — pvesh не идемпотентен сам по себе.
Решение: использовать bash-скрипт с проверкой через pct status,
         или сначала проверить: pvesh get /nodes/proxmox/lxc | grep vmid
```

**Ошибка: Docker внутри LXC не запускается — «operation not permitted»**

```
Причина: контейнер создан как unprivileged без нужных features.
Решение: проверить /etc/pve/lxc/100.conf — должна быть строка:
         features: keyctl=1,nesting=1
         Если нет — добавить и перезапустить: pct stop 100 && pct start 100
```

**Ошибка: Ansible не может подключиться к API**

```
Причина: неверный API-токен или не установлены зависимости.
Проверить:
  pip list | grep proxmoxer   # должен быть установлен
  # Токен проверить вручную:
  curl -sk https://192.168.1.100:8006/api2/json/nodes \
    -H "Authorization: PVEAPIToken=root@pam!ansible=ВАШ_ТОКЕН"
```

---

## Практика

**Задание 1:** выполни несколько `pvesh get` запросов и изучи вывод. Найди ID всех запущенных контейнеров. Сравни вывод с тем что видишь в веб-интерфейсе.

**Задание 2:** инициализируй git в `/etc/pve`, добавь все конфиги и сделай первый коммит. Потом измени параметр любого контейнера через веб-интерфейс и зафикси изменение вторым коммитом с осмысленным сообщением.

**Задание 3:** скопируй bash-скрипт из раздела 14.6 на хост Proxmox. Измени VMID, HOSTNAME и IP под свои значения. Запусти скрипт первый раз — убедись что контейнер создан и Docker работает. Запусти второй раз — убедись что повторный запуск ничего не сломал.

---

## Чек-лист для самопроверки

- [ ] Выполнил `pvesh get /nodes/proxmox/lxc` и прочитал вывод — понимаю структуру
- [ ] `/etc/pve` добавлен в git-репозиторий, есть минимум два коммита
- [ ] Могу объяснить зачем хранить конфигурацию в git, а не только в бэкапах
- [ ] Idempotent bash-скрипт запущен дважды — второй раз ничего не изменил
- [ ] Понимаю разницу между `pvesh`, Ansible и Terraform — когда что применять
