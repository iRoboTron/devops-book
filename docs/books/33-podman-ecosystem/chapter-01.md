# Глава 1: OCI изнутри — стандарты которые объединяют экосистему

## Что вы узнаете

- из чего физически состоит OCI-образ — что лежит на диске;
- что такое runc и почему он один для Docker, Podman и containerd;
- как образы передаются между реестрами и что такое digest;
- как `skopeo` позволяет работать с образами без их скачивания.

---

## Архитектура контейнерной экосистемы

Прежде чем разбирать OCI по частям — посмотрим на общую картину. Контейнерная экосистема устроена слоями, и каждый слой знает только о соседнем.

```text
                 Kubernetes           CLI (podman / docker)
                     │                        │
              CRI (gRPC)                      │
                     │                        │
          containerd / CRI-O             Podman / dockerd
                     │                        │
              OCI Runtime Spec          OCI Runtime Spec
                     │                        │
                    runc ←──────────────────── runc
                     │
            Linux namespaces + cgroups
                     │
                Контейнер
```

Обратите внимание: `runc` — общий для всех. Kubernetes через containerd использует runc. Podman использует runc. Docker использует runc через containerd. OCI Runtime Spec описывает именно это: как должен вести себя `runc` и любой другой совместимый рантайм.

---

## OCI Image Spec — что внутри образа

Когда вы выполняете `docker pull nginx` или `podman pull nginx`, на диске появляется OCI-образ. Посмотрим что это такое.

### Структура образа

OCI-образ — это не один файл. Это набор объектов:

```text
OCI-образ nginx:latest
├── index.json           ← точка входа: какие манифесты есть для каких платформ
├── oci-layout           ← метафайл: версия спецификации
└── blobs/
    └── sha256/
        ├── abc123...    ← manifest.json: список слоёв и конфигурация
        ├── def456...    ← config.json: CMD, ENV, ENTRYPOINT, история
        ├── 111aaa...    ← слой 1: базовая ОС (debian:bookworm-slim)
        ├── 222bbb...    ← слой 2: apt install nginx
        └── 333ccc...    ← слой 3: конфиги nginx
```

Каждый слой — это `tar.gz`-архив с изменениями файловой системы. Слои накладываются один на другой через union filesystem (overlay2).

### Манифест

Манифест — это JSON-файл который описывает образ: какие слои входят, какая конфигурация, для какой платформы.

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "digest": "sha256:def456...",
    "size": 7682
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:111aaa...",
      "size": 29148928
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:222bbb...",
      "size": 64512
    }
  ]
}
```

### Конфигурация образа

Конфигурация (`config.json`) хранит метаданные запуска: что выполнять при старте, какие переменные окружения, на каком порту слушать.

```json
{
  "Cmd": ["nginx", "-g", "daemon off;"],
  "Env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
          "NGINX_VERSION=1.27.0"],
  "ExposedPorts": {"80/tcp": {}},
  "WorkingDir": ""
}
```

### Digest — адресация по содержимому

Каждый объект в OCI-образе адресуется не по имени, а по SHA256-хешу содержимого. Это означает:

- Если содержимое не изменилось — digest одинаковый на любом компьютере в мире.
- Если digest совпадает — образ точно такой же, без исключений.
- Тег (`nginx:latest`) — это просто ссылка на digest. Digest неизменен, тег может переехать на новый digest в любой момент.

```bash
# Тег может измениться, digest — нет
podman pull nginx:latest
podman images --digests nginx
# REPOSITORY  TAG     DIGEST              IMAGE ID
# nginx       latest  sha256:a4d4..3f1c   e784f4560448
```

**Вывод:** в продакшне фиксируйте образы по digest, не по тегу:
```
nginx@sha256:a4d4...3f1c  ← воспроизводимо
nginx:latest               ← может измениться в любой момент
```

---

## OCI Runtime Spec — как запускать контейнер

Runtime Spec описывает что должен делать рантайм когда получает задание «запустить контейнер». `runc` — эталонная реализация этой спецификации.

### Что делает runc

Когда Podman (или Docker, или containerd) запускает контейнер, он:
1. Распаковывает слои образа в директорию на диске (rootfs).
2. Создаёт файл `config.json` по Runtime Spec — описание контейнера.
3. Вызывает `runc run` с этим конфигом.
4. `runc` создаёт Linux namespaces и cgroups, запускает процесс.

```bash
# runc работает напрямую с rootfs и config.json
# Podman/Docker делают это за вас, но под капотом именно так:
runc run --bundle /path/to/bundle my-container
```

### Почему это важно

Раньше каждый рантайм реализовывал запуск контейнеров по-своему. Теперь все используют `runc` (или совместимый рантайм — `crun`, `youki`). Это значит: поведение контейнера одинаково независимо от того, кто его запустил.

```text
podman run nginx  →  runc  →  контейнер ведёт себя так же как при
docker run nginx  →  runc  →  containerd/ctr run nginx
```

---

## OCI Distribution Spec — как образы путешествуют по реестрам

Distribution Spec стандартизирует HTTP API для реестров. Это позволяет `podman push` отправлять образы в Docker Hub, Quay.io, GHCR, Harbor и любой другой совместимый реестр одной командой.

### Как работает push

```text
podman push myapp:latest docker.io/myuser/myapp:latest

1. Podman смотрит какие слои уже есть в реестре (HEAD запрос по digest)
2. Загружает только отсутствующие слои (POST + PUT)
3. Загружает конфигурацию
4. Загружает манифест — последним, это «публикует» образ
```

Именно поэтому повторный push одного и того же образа быстрый — реестр уже имеет все слои, загружается только манифест.

---

## skopeo — работа с образами без скачивания

`skopeo` — инструмент для работы с OCI-образами на уровне реестров. Он не запускает контейнеры, не кэширует образы локально — только перемещает и инспектирует.

### Установка

```bash
# Ubuntu/Debian
sudo apt install skopeo

# Fedora/RHEL
sudo dnf install skopeo
```

### Инспектировать образ без скачивания

```bash
# Посмотреть манифест образа не скачивая его
skopeo inspect docker://nginx:latest

# Вывод (сокращённо):
{
    "Name": "docker.io/library/nginx",
    "Digest": "sha256:a4d4...",
    "RepoTags": ["1.27.0", "1.27", "1", "latest", "mainline", ...],
    "Created": "2024-05-29T...",
    "DockerVersion": "",
    "Architecture": "amd64",
    "Os": "linux",
    "Layers": [
        "sha256:09f376ebb190...",
        "sha256:5ea9a7018d11...",
        ...
    ]
}
```

### Копировать между реестрами без скачивания на диск

```bash
# Скопировать nginx из Docker Hub в свой GHCR
# Образ идёт напрямую: реестр → реестр, без локального диска
skopeo copy \
  docker://docker.io/library/nginx:latest \
  docker://ghcr.io/myorg/nginx:latest

# Скопировать в локальный реестр
skopeo copy \
  docker://nginx:alpine \
  docker://localhost:5000/nginx:alpine

# Скопировать в локальную директорию (OCI layout)
skopeo copy \
  docker://nginx:latest \
  oci:/tmp/nginx-image:latest
```

### Синхронизировать образы для air-gap окружений

```bash
# Скачать образы для окружения без интернета
skopeo sync \
  --src docker \
  --dest dir \
  nginx:latest \
  /tmp/images/

# Загрузить на изолированный сервер
skopeo sync \
  --src dir \
  --dest docker \
  /tmp/images/ \
  my-internal-registry.example.com/
```

### Проверить что образ не изменился

```bash
# Сравнить digest образа в двух реестрах
skopeo inspect docker://docker.io/library/nginx:latest | grep Digest
skopeo inspect docker://ghcr.io/myorg/nginx:latest | grep Digest
# Если digest одинаковый — образы идентичны побитово
```

---

## buildah — сборка OCI-образов без демона

`buildah` — инструмент для сборки OCI-образов. `podman build` использует buildah под капотом. Но buildah можно использовать и напрямую — особенно в CI, где нет прав на запуск контейнеров.

```bash
# Через Dockerfile (идентично podman build)
buildah bud -t myapp:latest .

# Или через скрипт — без Dockerfile
container=$(buildah from python:3.12-slim)
buildah run $container -- pip install flask
buildah copy $container ./app /app
buildah config --cmd "python /app/main.py" $container
buildah commit $container myapp:latest
buildah rm $container
```

Подробнее о buildah — в главе 10.

---

## Почему Docker-образ и Podman-образ — одно и то же

Этот вопрос возникает у всех кто переходит с Docker на Podman: «нужно ли пересобирать образы?».

Ответ: нет. С 2017 года Docker перевёл свои образы на OCI Image Spec. Docker Hub хранит OCI-образы. `podman pull` скачивает их без конвертации. `docker pull` делает то же самое.

```bash
# Образ скачанный через docker можно запустить через podman и наоборот
docker pull python:3.12-slim
# Теперь скопируем его в Podman storage
skopeo copy \
  docker-daemon:python:3.12-slim \
  containers-storage:python:3.12-slim
# И запустим через Podman
podman run --rm python:3.12-slim python --version
```

---

## Типичные ошибки

**«Образ с тегом `latest` — это всегда последняя версия»**
Тег — это просто строка. Разработчик образа решает что считать `latest`. Некоторые не обновляют его месяцами. Всегда проверяйте дату создания образа: `skopeo inspect docker://nginx:latest | grep Created`.

**«Если образ одинаковый по имени и тегу — он одинаковый»**
Тег может перемещаться на новый digest. `nginx:latest` сегодня и `nginx:latest` завтра могут быть разными образами. Для воспроизводимости — фиксировать по digest.

**«skopeo нужен только для копирования»**
`skopeo inspect` — очень быстрый способ узнать что внутри образа (теги, слои, архитектура) без скачивания 100 MB. Полезно в скриптах и CI.

**«Слои образа хранятся в зашифрованном виде»**
Нет. Слои — это обычные tar-архивы. Если положить секрет в слой образа (даже удалив в следующем слое) — он останется в архиве и будет виден через `skopeo copy ... oci:...`.

---

## Чек-лист для самопроверки

- [ ] Понимаю из чего состоит OCI-образ: слои, манифест, конфигурация
- [ ] Знаю что такое digest и почему он надёжнее тега
- [ ] Знаю что такое runc и что именно он делает при запуске контейнера
- [ ] Установил skopeo и выполнил `skopeo inspect` для любого образа
- [ ] Понимаю что Docker-образ и OCI-образ — одно и то же

## Попробуйте сами

1. Установите `skopeo` и выполните:
   ```bash
   skopeo inspect docker://alpine:latest
   ```
   Найдите в выводе: сколько слоёв у образа? Какая архитектура? Когда создан?

2. Сравните размер двух образов не скачивая их:
   ```bash
   skopeo inspect docker://python:3.12 | grep -i size
   skopeo inspect docker://python:3.12-slim | grep -i size
   ```
   Насколько `slim` меньше?

3. Посмотрите digest образа:
   ```bash
   podman pull nginx:latest
   podman images --digests nginx
   ```
   Запишите digest. Теперь выполните `skopeo inspect docker://nginx:latest | grep Digest`. Совпадает ли?
