# Приложение E: Podman Machine — Windows и macOS

## Зачем нужна Podman Machine

Podman — Linux-инструмент. Он использует Linux-ядро для namespaces, cgroups и контейнерной изоляции. На Windows и macOS Linux-ядра нет, поэтому Podman запускает легковесную виртуальную машину с Linux внутри — это и есть Podman Machine.

Та же проблема у Docker Desktop: под капотом там тоже Linux VM (HyperKit на macOS, WSL2 на Windows). Разница в том, что Docker Desktop скрывает это полностью, а Podman Machine даёт вам прямой доступ к VM.

---

## macOS

### Установка

```bash
# Через Homebrew (рекомендуется)
brew install podman

# Проверить версию
podman --version
```

### Создать и запустить Machine

```bash
# Создать машину с настройками по умолчанию
podman machine init

# Создать с нестандартными параметрами
podman machine init \
  --cpus 4 \
  --memory 4096 \
  --disk-size 50 \
  myvm

# Запустить
podman machine start
# или
podman machine start myvm

# Статус
podman machine list
# NAME        VM TYPE     CREATED       LAST UP         CPUS  MEMORY  DISK SIZE
# podman-machine-default  qemu   3 minutes ago  Currently running  2   2048MB  10GiB

# Информация о машине
podman machine inspect
```

### Работа с Machine

После запуска Machine команды `podman` работают прозрачно — вы не замечаете что они выполняются внутри VM:

```bash
# Работает как обычно
podman run --rm alpine echo hello
podman build -t myapp:latest .
podman images
```

### SSH в Machine

```bash
# Войти в Linux VM напрямую
podman machine ssh

# Выполнить команду внутри VM
podman machine ssh ls /etc/containers/

# Скопировать файл в Machine
podman machine ssh -- cat /etc/os-release
```

### rootful vs rootless режим

По умолчанию Podman Machine запускает rootless режим внутри VM. Для некоторых операций нужен rootful:

```bash
# Создать rootful Machine
podman machine init --rootful

# Переключить существующую Machine в rootful
podman machine stop
podman machine set --rootful
podman machine start
```

Когда нужен rootful на Mac:
- Монтирование папок с точным UID mapping
- Некоторые порты < 1024 без дополнительной настройки

### Остановить и удалить

```bash
# Остановить
podman machine stop

# Удалить Machine (данные внутри потеряются)
podman machine rm
podman machine rm --force myvm

# Список всех Machine
podman machine list
```

---

## Windows

### Установка

**Способ 1: Podman Desktop (рекомендуется для начинающих)**

Скачать с [podman-desktop.io](https://podman-desktop.io) — включает GUI и Podman CLI.

**Способ 2: через winget**

```powershell
winget install RedHat.Podman
```

**Способ 3: через Chocolatey**

```powershell
choco install podman-desktop
```

### Требования для Windows

- Windows 10 version 2004+ или Windows 11
- WSL2 включён: `wsl --install` (если не был)
- Hyper-V или WSL2 provider

### Инициализация на Windows

```powershell
# Создать Machine (использует WSL2 под капотом)
podman machine init

# Запустить
podman machine start

# Проверить
podman machine list
podman info
```

### PowerShell vs WSL2 Terminal

На Windows команды Podman можно запускать:

1. **В PowerShell / CMD** — через `podman.exe`, работает прозрачно
2. **В WSL2 terminal** — нативно, если Podman установлен внутри WSL2

```powershell
# В PowerShell
podman run --rm alpine echo hello
podman images
```

```bash
# В WSL2 Ubuntu терминале (если Podman установлен в Ubuntu)
podman run --rm alpine echo hello
```

---

## Docker-совместимость на Mac/Windows

Если у вас есть инструменты которые ожидают Docker socket — Podman Machine его эмулирует:

```bash
# На macOS: узнать путь к сокету Podman Machine
podman machine inspect --format '{{.ConnectionInfo.PodmanSocket.Path}}'
# /Users/user/.local/share/containers/podman/machine/qemu/podman.sock

# Указать переменную для Docker-совместимых инструментов
export DOCKER_HOST=unix:///Users/user/.local/share/containers/podman/machine/qemu/podman.sock

# Проверить что testcontainers, docker-compose или другой инструмент работает
docker-compose ps   # если настроен alias
```

На Windows:

```powershell
# PowerShell
$env:DOCKER_HOST = "npipe:////./pipe/docker_engine"
# или через WSL2 socket, зависит от конфигурации
```

---

## Podman Desktop

Podman Desktop — графический интерфейс для управления контейнерами, образами и Machine. Доступен для macOS, Windows и Linux.

```text
Что умеет Podman Desktop:
├── Запускать и останавливать Podman Machine
├── Просматривать контейнеры и образы
├── Просматривать логи контейнеров
├── Управлять томами и сетями
├── Собирать образы (через Dockerfile)
├── Работать с Kubernetes (kubectl, kube play)
└── Расширения: Docker Desktop extensions compatibility
```

Скачать: podman-desktop.io

---

## Ограничения Podman Machine

По сравнению с native Linux:

| Особенность | Podman Machine (Mac/Win) | Podman native (Linux) |
|-------------|--------------------------|----------------------|
| Производительность I/O | Медленнее (VM overhead) | Нативная |
| Монтирование файлов | Через 9p/virtiofs | Прямо |
| Сеть | Через VM NAT | Нативная |
| Поддержка GPU | Ограничена | Через NVIDIA CDK |
| rootless контейнеры | Да (в VM) | Да |
| Потребление RAM | +1-2 ГБ для VM | Минимально |

Для разработки этих ограничений обычно достаточно. Для production — Podman на Linux-сервере.

---

## Сравнение с Docker Desktop

| Аспект | Docker Desktop | Podman Desktop / Machine |
|--------|---------------|--------------------------|
| Цена | Бесплатно для личного / платно для бизнеса | Бесплатно (OSS) |
| Лицензия | Proprietary | Apache 2.0 |
| GUI | Docker Desktop | Podman Desktop |
| Подкапот | HyperKit/WSL2 | QEMU/WSL2 |
| Docker API совместимость | Полная | Через socket эмуляцию |
| rootless | Rootless mode | Нативно |
| Поды | Нет | Да |
| Systemd в VM | Нет | Да |
| K8s built-in | Docker Kubernetes | Через kubeconfig |

---

## Быстрый старт на macOS

```bash
# 1. Установить
brew install podman

# 2. Создать и запустить VM
podman machine init
podman machine start

# 3. Убедиться что работает
podman run --rm hello-world

# 4. Работать как на Linux
podman build -t myapp:latest .
podman run -d -p 8080:80 --name web nginx
podman ps
podman logs web
podman stop web
podman rm web

# 5. Когда закончили работу (опционально)
podman machine stop
```

После этих шагов у вас полноценный Podman на macOS — с теми же командами что на Linux.
