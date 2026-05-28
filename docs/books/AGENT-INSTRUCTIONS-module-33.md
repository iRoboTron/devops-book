# Инструкция для ИИ-агента: Модуль 33 — Podman и контейнерная экосистема

> **Роль агента:** Ты — технический писатель и DevOps-инженер с опытом работы на Linux, знающий Docker, Podman, Kubernetes, CI/CD. Ты пишешь обучающий материал для практикующих инженеров: конкретно, без воды, с реальными примерами. Ты объясняешь не только «как», но и «зачем» — и честно говоришь о trade-offs.

> **Это Модуль 33, книга части 4 "Прочее".**
> Предварительные требования: книга 03 (Docker), желательно — книга 10 (Kubernetes Basics).
> Читатель уже работает с Docker, знает `docker-compose`, собирает образы через Dockerfile.

---

## Контекст проекта

Читатель познакомился с контейнерами через Docker — это был правильный первый шаг. Но теперь он сталкивается с ситуациями, которые Docker не решает хорошо:

- Запускает контейнеры на сервере под root — и это ощущается как проблема.
- Читал про Kubernetes и увидел что там "Docker deprecated" — непонятно что это значит.
- Хочет запускать контейнеры без фонового демона, который всё время висит и потребляет ресурсы.
- Слышал про Podman, но не понимает — это замена Docker или что-то другое?
- Начал разбираться в CI/CD и видит что GitLab Runner, rootless режимы, RHEL-сервера — везде Podman.
- Хочет понять как устроена экосистема изнутри: что за OCI, почему containerd, как это всё связано.

**Что он хочет после книги:**
Понять как устроена контейнерная экосистема — кто за что отвечает. Перейти с Docker на Podman на рабочем сервере, настроить rootless-контейнеры, использовать `podman-compose` как замену `docker-compose`, и сгенерировать первый K8s YAML из работающих контейнеров.

---

## Что за книга

**Название:** "Podman и контейнерная экосистема: OCI, rootless и жизнь после Docker"

**Каталог:** `33-podman-ecosystem`

**Место в курсе:** Книга 33, часть 4 "Прочее".

**Объём:** 120–150 страниц.

**Версии ПО:** все примеры команд рассчитаны на Podman 4.4+ (Quadlet) и Podman 5.x. Там, где есть различия между версиями — указывать явно.

**Формат файлов:** каждая глава — отдельный файл `chapter-XX.md`, приложения — `appendix-a.md` и т.д. Кодировка UTF-8. Файл оглавления — `book.md`.

**Особенность книги:**
Книга не против Docker — она объясняет почему появилось несколько рантаймов, как они стандартизировались через OCI, и зачем это знать практикующему DevOps-инженеру. Podman — главный инструмент книги, потому что он одновременно Docker-совместим, rootless, без демона, и генерирует K8s YAML.

**Стиль:**
- Простой язык, без академизма.
- Каждая глава начинается с блока «Что вы узнаете» и заканчивается «Чек-листом для самопроверки» и блоком «Попробуйте сами».
- Сравнения «Docker → Podman»: что поменялось, что осталось, почему.
- Пары "так было → стало лучше" для типичных ошибок безопасности.
- Конкретные команды с объяснением что они делают.
- Реальные сценарии: CI/CD, RHEL-сервер, миграция с Docker, Kubernetes-мост.

---

## Таблица объёмов глав

| Глава | Тема | Страниц |
|-------|------|---------|
| 0 | Жизнь после Docker | 6–8 |
| 1 | OCI изнутри | 8–10 |
| 2 | containerd и CRI-O | 6–8 |
| 3 | Установка и первые шаги | 6–8 |
| 4 | Podman vs Docker | 8–10 |
| 5 | Rootless | 12–14 |
| 6 | Podman Compose | 10–12 |
| 7 | podman kube | 8–10 |
| 8 | Реестры | 8–10 |
| 9 | Systemd и Quadlet | 8–10 |
| 10 | buildah | 8–10 |
| 11 | Миграция | 8–10 |
| 12 | CI/CD | 8–10 |
| 13 | Диагностика | 6–8 |
| 14 | Итоговый проект | 6–8 |
| Приложения A–E | | 12–14 |

Общий объём: 120–150 страниц.

---

## Требования к иллюстрациям

В книге обязательны минимум 3 текстовые схемы (ASCII). Каждая сопровождается описанием что показывает.

**Схема 1 — Архитектура OCI-рантаймов** (Глава 1):
```text
                 Kubernetes           CLI (podman/docker)
                     │                       │
              CRI (gRPC)                     │
                     │                       │
          containerd / CRI-O            Podman / dockerd
                     │                       │
              OCI Runtime Spec         OCI Runtime Spec
                     │                       │
                    runc ←─────────────────── runc
                     │
            Linux Namespaces + cgroups
                     │
                Контейнер
```
Разместить: начало главы 1.

**Схема 2 — Маппинг UID в rootless** (Глава 5):
```text
Внутри контейнера          /etc/subuid              На хосте
UID 0 (root)         →    user:100000:65536   →    UID 100000
UID 1 (daemon)       →                        →    UID 100001
UID 1000 (appuser)   →                        →    UID 101000

Результат: "root" в контейнере = обычный пользователь на хосте
```
Разместить: раздел "Как работает rootless изнутри" главы 5.

**Схема 3 — Процессная модель Docker vs Podman** (Глава 4):
```text
Docker:
systemd → dockerd (root) → containerd → containerd-shim → container
             ↑ демон всегда запущен, SPOF

Podman:
shell → podman → conmon → container
         ↑ каждый запуск — отдельный процесс, нет SPOF
```
Разместить: раздел "Ключевые концептуальные отличия" главы 4.

Дополнительно: в каждой главе с несколькими инструментами или уровнями — добавлять текстовую таблицу или схему связей.

---

## Правило маркировки опасных команд

Ввести единую маркировку для команд, которые удаляют данные или нарушают работу без возможности восстановления:

```markdown
> ☠️ **Осторожно:** [описание что именно удаляется/ломается и почему нельзя отменить]
```

Применять к:
- `podman system prune --all --volumes` — удаляет всё без исключений
- `podman volume rm --force` — удаляет данные тома
- `podman rmi -f` — принудительное удаление, даже если образ используется
- `podman system reset` — сброс всего состояния Podman

---

## Антипаттерны подачи (агент должен избегать)

**Плохо:** "Podman лучше Docker."
**Хорошо:** "Podman — другой подход с trade-offs: лучше для безопасности, сложнее для привычных Docker-сценариев."

**Плохо:** "Просто введите команду..."
**Хорошо:** "Следующая команда создаёт rootless сервис; обратите внимание на флаг `--new` — без него systemd unit ссылается на существующий контейнер, а не создаёт его при каждом старте."

**Плохо:** "OCI — это стандарт." (и ничего больше)
**Хорошо:** объяснить что именно стандартизирует OCI и как это проявляется на практике.

**Плохо:** давать опасные команды без предупреждения.
**Хорошо:** ☠️-маркировка + объяснение что именно будет удалено.

**Плохо:** "podman kube generate создаёт K8s манифест для деплоя в продакшн."
**Хорошо:** явное предупреждение что `generate` создаёт `kind: Pod`, не `Deployment`, и нужна ручная адаптация.

---

## Главная идея

Docker сделал контейнеры популярными. OCI превратил их в стандарт. Теперь рантаймов много — и это хорошо.

```text
Раньше:
Docker = всё.
Docker daemon запущен → всё работает.
Docker упал → ничего не работает.
Контейнеры запускаются от root → любая уязвимость = полный доступ к хосту.

Сейчас:
OCI-стандарт → образ собрал Podman, запустил containerd, хранит Harbor.
Podman:
- без демона (каждый контейнер — отдельный процесс)
- rootless (контейнер не видит root хоста)
- Docker-совместим (alias docker=podman)
- генерирует K8s YAML из работающего стека
```

**Ключевое понимание:**
- OCI Image Spec — стандарт на формат образа. Docker образ = OCI образ.
- OCI Runtime Spec — стандарт на запуск. runc запускает контейнер и в Docker, и в containerd, и в Podman.
- containerd — рантайм который использует Kubernetes. Не Docker.
- Podman — не замена Docker "потому что лучше". Это инструмент где безопасность не жертва удобства.

---

## Что читатель получит к концу книги

- Понимание как устроена экосистема: OCI → runc → containerd/Podman → K8s.
- Установленный и настроенный Podman на Linux-сервере.
- Rootless-контейнеры без единой команды под root.
- Работающий `podman-compose` с реальным стеком (приложение + БД).
- Первый K8s YAML, сгенерированный из работающих контейнеров командой `podman kube generate`.
- Понимание разницы между Docker Hub, Quay.io, GHCR — и как работать с несколькими реестрами.
- Готовый план миграции с Docker на Podman для существующего проекта.
- Настроенный systemd-сервис на базе контейнера через Quadlet.

---

## Структура книги

### Глава 0: Жизнь после Docker — зачем нужен ещё один рантайм

**Что вы узнаете:**
- почему появилось несколько контейнерных рантаймов и что их объединяет;
- что такое OCI и зачем он нужен практикующему инженеру;
- чем rootless-контейнеры принципиально отличаются от обычных.

**Цель:** показать что Podman — это не "Docker, только другой", а другой подход к безопасности контейнеров.

Объяснить:
- Краткая история: Docker появился, стал стандартом, Kubernetes сначала использовал Docker, потом отказался — почему?
- OCI (Open Container Initiative, 2015): Linux Foundation, стандартизация форматов образов и рантаймов. Теперь образ — не "Docker образ", а OCI-совместимый образ.
- Архитектура Docker изнутри: `docker` CLI → `dockerd` (демон) → `containerd` → `runc` → контейнер.
- Kubernetes убрал dockershim (1.24): теперь K8s работает напрямую с containerd или CRI-O через CRI интерфейс.
- Главная проблема Docker-демона: один SPOF, работает под root, socket `/var/run/docker.sock` = root-доступ ко всему хосту.

Сравнение:
```text
Docker:
+ Огромная экосистема, документация, примеры
+ docker-compose
- Демон работает под root
- /var/run/docker.sock — дыра в безопасности при монтировании в CI
- Один демон = единая точка отказа

Podman:
+ rootless из коробки
+ без демона (fork-exec модель)
+ Docker-совместимые команды
+ генерирует K8s YAML
- Меньше документации на русском
- podman-compose менее зрелый чем docker-compose
```

**Когда оставить Docker:** Если вся команда на Docker, всё работает, рефакторинг не нужен. Podman не серебряная пуля.

**Чек-лист для самопроверки:**
- [ ] Понимаю что такое OCI и зачем он появился
- [ ] Знаю из каких компонентов состоит Docker изнутри
- [ ] Понимаю почему Kubernetes отказался от Docker в 1.24
- [ ] Могу объяснить чем rootless отличается от обычных контейнеров

**Попробуйте сами:**
1. Найдите в выводе `docker info` строку с `Runtimes:` — что там написано и что это означает?
2. Проверьте права на `/var/run/docker.sock` командой `ls -la /var/run/docker.sock`. Что означает `srw-rw----`?
3. Найдите в официальном ченджлоге K8s версию где убрали dockershim и прочитайте одно предложение объяснения.

---

### Глава 1: OCI изнутри — стандарты которые объединяют экосистему

**Что вы узнаете:**
- что конкретно стандартизирует OCI;
- что такое runc и почему он есть и в Docker, и в Podman;
- как образы хранятся и передаются между рантаймами.

**Цель:** демистифицировать OCI — понять не "зачем аббревиатура", а что реально происходит когда ты пишешь `FROM ubuntu`.

Разместить в начале главы Схему 1 (архитектура OCI-рантаймов).

Темы:
- OCI Image Spec: образ = набор слоёв (tar-архивов) + манифест + конфигурация.
  ```text
  my-app:latest
  ├── manifest.json         ← что входит в образ
  ├── config.json           ← CMD, ENV, ENTRYPOINT
  ├── layer-1.tar.gz        ← ubuntu:22.04 (base)
  ├── layer-2.tar.gz        ← apt install python3
  └── layer-3.tar.gz        ← COPY . /app
  ```
- OCI Runtime Spec: как должен работать рантайм. `runc` — эталонная реализация.
- Distribution Spec: как образы передаются через реестры. HTTP API, digest, registry v2.
- Практически: `skopeo inspect docker://nginx:latest` — посмотреть манифест образа без скачивания.
- `buildah` — сборщик OCI-образов без Docker daemon.
- Почему `docker build` и `podman build` делают совместимые образы: они оба следуют OCI Image Spec.

Команды:
```bash
# Посмотреть манифест образа не скачивая его
skopeo inspect docker://nginx:latest

# Скопировать образ из одного реестра в другой
skopeo copy docker://nginx:latest docker://localhost:5000/nginx:latest

# Посмотреть слои образа
podman inspect --format '{{.RootFS.Layers}}' nginx:latest
```

**Типичные ошибки:**
- Путать "образ" и "контейнер": образ неизменяем, контейнер — запущенный экземпляр.
- Думать что Docker Hub — единственный реестр. Quay.io, GHCR, Harbor — полноценные альтернативы с тем же API.
- Думать что "Docker-образ" и "OCI-образ" — разные вещи. Это одно и то же: Docker перешёл на OCI ещё в 2017.

**Чек-лист для самопроверки:**
- [ ] Понимаю из чего состоит OCI-образ
- [ ] Знаю что такое runc и что он делает
- [ ] Выполнил `skopeo inspect` для любого образа
- [ ] Понимаю что Docker образ и Podman образ — одно и то же

**Попробуйте сами:**
1. Установите `skopeo` и выполните `skopeo inspect docker://alpine:latest`. Найдите в выводе количество слоёв.
2. Командой `podman pull nginx:latest && podman inspect nginx:latest | python3 -m json.tool | grep -A5 Layers` посмотрите слои образа.
3. Найдите на сайте opencontainers.org страницу OCI Image Spec и запишите одно предложение — что именно она стандартизирует.

---

### Глава 2: containerd и CRI-O — что внутри Kubernetes

**Что вы узнаете:**
- как Kubernetes запускает контейнеры без Docker;
- зачем нужен CRI (Container Runtime Interface);
- в чём разница между containerd и CRI-O на практике.

**Цель:** объяснить "K8s убрал Docker" так, чтобы это стало понятно, а не пугало.

Темы:
- CRI (Container Runtime Interface): стандартный интерфейс K8s к рантайму. gRPC API.
- containerd: высокоуровневый рантайм, используется в большинстве managed K8s (GKE, EKS, AKS). Работает под root, но это не проблема на уровне кластера K8s.
- CRI-O: рантайм специально для K8s (Red Hat). Используется в OpenShift.
- runc: низкоуровневый рантайм, общий для всех. containerd использует runc, CRI-O использует runc, Podman использует runc.

```text
Kubernetes
    │ CRI (gRPC)
    ▼
containerd (или CRI-O)
    │ OCI Runtime Spec
    ▼
runc
    │ Linux namespaces + cgroups
    ▼
Контейнер
```

`crictl` — CLI для диагностики CRI-совместимого рантайма:
```bash
# Важно: crictl требует явного указания сокета рантайма
# containerd (большинство K8s-дистрибутивов):
crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps

# CRI-O (OpenShift и RHEL-based K8s):
crictl --runtime-endpoint unix:///run/crio/crio.sock ps

# Посмотреть образы
crictl images

# Посмотреть логи контейнера
crictl logs <container-id>
```

> **Примечание:** `crictl` устанавливается отдельно (пакет `cri-tools`) и может отсутствовать на нодах. Если недоступен — для локальных экспериментов подойдёт `podman --runtime=/usr/bin/runc`.

- Почему Podman НЕ используется как K8s рантайм: у него нет CRI интерфейса. Зато `podman kube play` позволяет запускать K8s YAML локально.

**Типичные ошибки:**
- "K8s убрал Docker — значит мои Docker образы не работают": не верно. Образы OCI-совместимы, они работают везде.
- Путать containerd и Docker: Docker использует containerd внутри, но сам Docker не нужен K8s.
- Запускать `crictl` без указания `--runtime-endpoint` — команда зависнет или выдаст ошибку подключения.

**Чек-лист для самопроверки:**
- [ ] Могу объяснить что такое CRI и зачем он нужен
- [ ] Понимаю разницу между containerd и runc
- [ ] Знаю что K8s убрал Docker-шим, но НЕ убрал поддержку Docker-образов
- [ ] Понимаю где в стеке живёт CRI-O

**Попробуйте сами:**
1. Найдите в описании релиза Kubernetes 1.24 (changelog) один абзац про удаление dockershim и пересвоими словами объясните почему это сделали.
2. Если есть доступ к K8s-ноде — выполните `crictl ps` и сравните вывод с `kubectl get pods`. Соответствуют ли они?
3. Нарисуйте на бумаге (или в тексте) стек от `kubectl apply` до запущенного процесса в контейнере.

---

### Глава 3: Установка и первые шаги с Podman

**Что вы узнаете:**
- как установить Podman на Ubuntu/Debian и RHEL/Fedora;
- как проверить rootless-режим;
- в чём отличие хранилища образов Podman от Docker.

**Цель:** установить Podman, убедиться что rootless работает, запустить первый контейнер.

Установка:
```bash
# Ubuntu 22.04 / Debian 12
sudo apt update && sudo apt install -y podman

# Fedora / RHEL 9
sudo dnf install -y podman

# Проверка версии
podman --version

# Информация о конфигурации (включая rootlessness)
podman info
```

Rootless-режим — проверка:
```bash
# Запустить контейнер без sudo
podman run --rm hello-world

# Убедиться что процесс внутри не root на хосте
podman run --rm alpine id
# Вывод: uid=0(root) gid=0(root) — это UID внутри контейнера

# А на хосте этот процесс выглядит иначе — проверить пока контейнер запущен:
podman run -d --name check alpine sleep 60
ps aux | grep "sleep 60"   # покажет UID текущего пользователя, не 0
podman stop check
```

`podman unshare` — войти в user namespace для диагностики прав:
```bash
podman unshare cat /proc/self/uid_map
# 0   1000   1       ← UID 0 внутри = UID 1000 снаружи
```

Хранилища образов:
```bash
# Список реестров по умолчанию (registries.conf)
cat /etc/containers/registries.conf

# Поиск образа сразу во всех настроенных реестрах
podman search nginx

# Явно указать реестр (рекомендуется)
podman pull docker.io/library/nginx:latest
podman pull quay.io/podman/hello
```

Конфигурационные файлы (объяснить назначение каждого):
- `/etc/containers/registries.conf` — список реестров
- `/etc/containers/storage.conf` — где хранятся образы
- `~/.config/containers/` — пользовательские переопределения

**Типичные ошибки:**
- `WARN[0000] "/" is not a shared mount`: запустить `podman system migrate` после обновления пакета.
- Образ не находится без полного пути → добавить `"docker.io"` в `unqualified-search-registries` в `registries.conf`.
- "Permission denied" на порт 80: использовать порт 8080 или `sudo sysctl net.ipv4.ip_unprivileged_port_start=80`.
- `newuidmap` не найден: установить пакет `uidmap` (`sudo apt install uidmap`).

**Чек-лист для самопроверки:**
- [ ] Podman установлен, `podman --version` возвращает результат
- [ ] Запустил `podman run hello-world` без sudo
- [ ] Понимаю где хранятся образы rootless-пользователя (`~/.local/share/containers/`)
- [ ] Знаю что `podman info` показывает и где искать rootlessness

**Попробуйте сами:**
1. Выполните `podman run --rm alpine sleep 60 &` и найдите этот процесс через `ps aux`. Какой UID у него на хосте?
2. Найдите где на диске хранится скачанный образ `alpine`: `podman image inspect alpine --format '{{.GraphDriver.Data}}'`.
3. Сравните размер `~/.local/share/containers/` до и после `podman pull python:3.12-slim`.

---

### Глава 4: Podman vs Docker — команды и концепции

**Что вы узнаете:**
- какие команды Docker работают в Podman без изменений;
- в чём принципиальные различия в поведении;
- как настроить алиас и начать использовать Podman вместо Docker.

**Цель:** существующий Docker-пользователь переходит на Podman за один день.

Разместить в этой главе Схему 3 (процессная модель Docker vs Podman).

Совместимость команд (таблица):
```text
Docker                          Podman                      Статус
docker run                      podman run                  ✅ идентично
docker build                    podman build                ✅ идентично
docker pull / push              podman pull / push          ✅ идентично
docker images                   podman images               ✅ идентично
docker ps / ps -a               podman ps / ps -a           ✅ идентично
docker exec -it                 podman exec -it             ✅ идентично
docker logs                     podman logs                 ✅ идентично
docker inspect                  podman inspect              ✅ идентично
docker volume                   podman volume               ✅ идентично
docker network                  podman network              ✅ идентично
docker-compose up               podman-compose up           ⚠️ нужен podman-compose
docker stats                    podman stats                ✅ идентично
/var/run/docker.sock            /run/user/1000/podman.sock  ⚠️ другой путь
docker system prune             podman system prune         ✅ идентично
```

Алиас:
```bash
# В ~/.bashrc или ~/.zshrc
alias docker=podman
alias docker-compose=podman-compose

# Проверка — должен работать любой docker-скрипт
docker run --rm alpine echo "работает через podman"
```

Ключевые концептуальные отличия:
- **Демон**: Docker имеет `dockerd`, Podman — нет. Каждый `podman run` — отдельный дочерний процесс.
- **Root**: Docker-контейнеры по умолчанию запускаются от root. Podman — от текущего пользователя.
- **Сокет**: Podman предоставляет Docker-совместимый сокет `podman.socket` (через systemd) для совместимости с инструментами работающими с Docker API.

Включить Docker-совместимый сокет:
```bash
# Пользовательский сокет (rootless)
systemctl --user enable --now podman.socket

# Путь сокета:
# /run/user/$(id -u)/podman/podman.sock

# Для совместимости с инструментами использующими Docker SDK:
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
```

**Типичные ошибки:**
- Инструмент падает с "Cannot connect to Docker daemon": настроить `DOCKER_HOST` на podman.sock.
- `podman-compose` не установлен: `pip3 install podman-compose` или `apt install podman-compose`.
- Монтирование `/var/run/docker.sock` в CI-контейнер: с Podman использовать `/run/user/$(id -u)/podman/podman.sock`.

**Чек-лист для самопроверки:**
- [ ] Добавил `alias docker=podman` и проверил что docker-скрипты работают
- [ ] Понимаю что у Podman нет демона и что это значит для надёжности
- [ ] Знаю разницу в путях к сокетам Docker и Podman
- [ ] Включил `podman.socket` и проверил его через `DOCKER_HOST`

**Попробуйте сами:**
1. Добавьте `alias docker=podman` в `~/.bashrc` и перезапустите терминал. Выполните `docker ps` — что показывает?
2. Включите `podman.socket` и выполните `curl -s --unix-socket /run/user/$(id -u)/podman/podman.sock http://localhost/version | python3 -m json.tool`. Что вернулось?
3. Запустите `podman run -d nginx` и найдите процесс `conmon` в `ps aux`. Это и есть "монитор контейнера" вместо демона.

---

### Глава 5: Rootless-контейнеры — безопасность по умолчанию

**Что вы узнаете:**
- почему запуск контейнеров под root — это реальная угроза;
- как именно rootless изолирует контейнер от хоста;
- какие ограничения есть у rootless и как их обойти.

**Цель:** понять rootless не как "ещё одну фичу", а как фундаментальный сдвиг в безопасности.

Разместить в начале главы Схему 2 (маппинг UID).

Почему root-контейнер — это плохо:
```text
Сценарий атаки (Docker):
1. Приложение в контейнере имеет уязвимость
2. Злоумышленник выходит из контейнера (container escape)
3. Он оказывается root на хосте
4. Хост полностью скомпрометирован

Тот же сценарий (rootless Podman):
1. Приложение в контейнере имеет уязвимость
2. Злоумышленник выходит из контейнера
3. Он оказывается непривилегированным пользователем на хосте
4. Хост защищён
```

Как работает rootless изнутри:
- User namespaces: UID 0 внутри = UID 1000 снаружи.
- `/etc/subuid` и `/etc/subgid` — диапазоны UID для маппинга.
  ```bash
  # Посмотреть маппинг для своего пользователя
  cat /etc/subuid
  # user:100000:65536  означает: пользователь получает UIDs 100000-165535

  # Что видит хост когда контейнер запускает процесс как root:
  podman run -d --name sleeper alpine sleep 100
  ps aux | grep "sleep 100"  # покажет UID 100000, не 0
  podman stop sleeper
  ```
- `newuidmap` / `newgidmap` — утилиты для настройки маппинга (пакет `uidmap`).

Ограничения rootless и решения:
```bash
# Порты < 1024 — три варианта решения:
# Вариант 1: использовать порты > 1024 (рекомендуется)
podman run -p 8080:80 nginx

# Вариант 2: разрешить через sysctl
sudo sysctl net.ipv4.ip_unprivileged_port_start=80

# Вариант 3: через CAP_NET_BIND_SERVICE
sudo setcap 'cap_net_bind_service=ep' /usr/bin/rootlessport
```

Монтирование томов и UID:
```bash
# Проблема: файлы в томе принадлежат другому UID
# Решение: --userns=keep-id (маппировать текущего пользователя как себя внутри)
podman run -v /home/user/data:/data --userns=keep-id myapp

# Также SELinux-метки: добавить :z для перемаркировки
podman run -v /home/user/data:/data:z myapp
```

Когда rootless не подходит:
- Загрузка модулей ядра (`modprobe`)
- NFS mount
- Изменение сетевых интерфейсов хоста
- Работа с cgroups v1 (устаревшие системы)

**Типичные ошибки:**
- "rootless не работает": нужен Linux 5.x+ с user_namespaces. Проверка: `cat /proc/sys/user/max_user_namespaces` (должно быть > 0).
- Том монтируется с неверными правами: использовать `--userns=keep-id`.
- "newuidmap не найден": `sudo apt install uidmap`.

**Чек-лист для самопроверки:**
- [ ] Понимаю разницу между UID 0 внутри rootless-контейнера и root на хосте
- [ ] Знаю что такое `/etc/subuid` и зачем он нужен
- [ ] Запустил контейнер и проверил его UID на хосте через `ps aux`
- [ ] Знаю в каких случаях rootless не подходит

**Попробуйте сами:**
1. Выполните `podman run --rm alpine id` — запомните вывод. Теперь найдите этот же процесс через `ps aux` пока он запущен. Сравните UID внутри и снаружи.
2. Создайте файл `/tmp/testdata/hello.txt` и смонтируйте `/tmp/testdata` в контейнер без `--userns=keep-id`. Какие права на файл внутри? Теперь добавьте `--userns=keep-id` — что изменилось?
3. Проверьте содержимое `/etc/subuid` для вашего пользователя и посчитайте диапазон UID которые он получает.

---

### Глава 6: Podman Compose — многоконтейнерные приложения

**Что вы узнаете:**
- как использовать `docker-compose.yml` с Podman без изменений;
- чем `podman-compose` отличается от `docker-compose`;
- что такое Podman Pods и чем они отличаются от Compose.

**Цель:** поднять реальный стек (приложение + БД + reverse proxy) через `podman-compose`.

Установка:
```bash
# Вариант 1: через pip
pip3 install podman-compose

# Вариант 2: через пакетный менеджер
sudo apt install podman-compose   # Ubuntu/Debian
sudo dnf install podman-compose   # Fedora/RHEL
```

Совместимость с docker-compose.yml:
- `podman-compose` читает стандартный `docker-compose.yml` — файл менять не нужно.
- Поддерживаются: `services`, `volumes`, `networks`, `environment`, `depends_on`, `healthcheck`.

Пример стека (Python + PostgreSQL + Nginx):
```yaml
# docker-compose.yml — работает и с docker-compose, и с podman-compose
version: '3.8'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 5

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:secret@db:5432/myapp
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app

volumes:
  pgdata:
```

```bash
# Запустить стек
podman-compose up -d

# Посмотреть логи
podman-compose logs -f

# Остановить и удалить
podman-compose down

# Пересобрать образы
podman-compose build
```

### Известные проблемы podman-compose

- **Производительность:** работает медленнее чем `docker-compose`, особенно на macOS/Windows через Podman Machine (сетевой стек проксируется через VM).
- **Неподдерживаемые директивы:** `profiles`, `configs`, `secrets` (из Swarm), `deploy` — игнорируются или вызывают ошибку.
- **Сеть:** в некоторых сценариях (broadcast, multicast) требуется `--network=host`, что ломает rootless.
- **Альтернатива:** для серьёзной работы использовать `podman pod` + индивидуальные `podman run`, либо `podman kube play` из K8s YAML — это стабильнее.

Podman Pods — нативный способ группировки:
```bash
# Pod = группа контейнеров с общим сетевым пространством (как в K8s)
podman pod create --name myapp -p 8080:80

# Запустить контейнеры в pod
podman run -d --pod myapp nginx
podman run -d --pod myapp myapp-backend

# Список pods
podman pod list

# Остановить и удалить pod вместе с контейнерами
podman pod stop myapp
podman pod rm myapp
```

**Типичные ошибки:**
- `podman-compose` не видит образы собранные через `docker build`: разные хранилища. Собирать через `podman build`.
- `depends_on` с `condition: service_healthy` не работает в старых версиях podman-compose: обновить до последней версии.

**Чек-лист для самопроверки:**
- [ ] Установил `podman-compose` и проверил версию
- [ ] Поднял стек из 2+ сервисов через `podman-compose up`
- [ ] Создал pod вручную и запустил в нём контейнеры
- [ ] Понимаю разницу между `podman-compose` и `podman pod`

**Попробуйте сами:**
1. Поднимите стек из примера через `podman-compose up -d`. Проверьте что приложение доступно на `localhost:8080`.
2. Попробуйте добавить в `docker-compose.yml` директиву `profiles: [dev]` — что происходит при `podman-compose up`?
3. Создайте pod вручную через `podman pod create`, запустите в нём nginx и проверьте через `curl`.

---

### Глава 7: От контейнеров к Kubernetes — podman kube

**Что вы узнаете:**
- как сгенерировать K8s YAML из работающих контейнеров;
- как запустить K8s YAML локально через Podman без кластера;
- в чём ограничения `podman kube generate` и как их обойти.

**Цель:** показать Podman как мост между локальной разработкой и Kubernetes — и честно объяснить где этот мост заканчивается.

> ⚠️ **Важно:** `podman kube generate` создаёт ресурс `kind: Pod`, а **не** `kind: Deployment`.
> Pod подходит для локального тестирования, но для продакшена в Kubernetes нужен Deployment (репликация, rolling update, самовосстановление при падении).
> После генерации — вручную адаптировать манифест: заменить `kind: Pod` на `kind: Deployment` и добавить `replicas:`, `selector:`.
> Пример трансформации — в Приложении D.

Главная идея:
```text
Локально: podman-compose up
    → всё работает
    → podman kube generate → K8s YAML (Pod)
    → адаптировать в Deployment
    → kubectl apply (в кластере)

Тестирование K8s YAML:
    → podman kube play (локально, без кластера)
    → быстрая итерация без деплоя
```

`podman kube generate` — экспорт в K8s YAML:
```bash
# Создать pod и контейнеры
podman pod create --name webapp -p 8080:80
podman run -d --pod webapp --name web nginx
podman run -d --pod webapp --name api myapp:latest

# Сгенерировать K8s YAML
podman kube generate webapp > webapp.yaml

# Посмотреть что получилось
cat webapp.yaml
```

Пример сгенерированного YAML (что получится и что нужно исправить):
```yaml
# Это то, что генерирует podman kube generate:
apiVersion: v1
kind: Pod          # ← для продакшна нужен Deployment
metadata:
  name: webapp
spec:
  containers:
  - name: web
    image: docker.io/library/nginx:latest
    ports:
    - containerPort: 80
      hostPort: 8080
  - name: api
    image: localhost/myapp:latest   # ← localhost не работает в K8s, нужен реестр
```

`podman kube play` — запустить K8s YAML локально:
```bash
# Запустить из YAML (без кластера K8s!)
podman kube play webapp.yaml

# Удалить всё что создал YAML
podman kube down webapp.yaml
```

Что поддерживает `podman kube play`:
- Pod, Deployment, PersistentVolumeClaim
- Не поддерживает: Service (LoadBalancer), Ingress, ConfigMap из Secret

Практический сценарий:
1. Разработчик запускает сервис через `podman-compose up`.
2. Когда готово — `podman kube generate` → получает первоначальный K8s YAML (Pod).
3. DevOps-инженер адаптирует в Deployment (см. Приложение D), добавляет liveness/readiness probes, ConfigMap.
4. Тестирует через `podman kube play` локально, потом деплоит в кластер.

**Типичные ошибки:**
- Деплоить сгенерированный YAML в продакшн без адаптации: Pod без Deployment не перезапустится при падении.
- Сгенерированный YAML содержит `localhost/...` образы: перепушить в реестр перед деплоем в K8s.
- `podman kube generate` для отдельного контейнера (не pod): сначала добавить контейнер в pod.

**Чек-лист для самопроверки:**
- [ ] Сгенерировал K8s YAML из работающего pod командой `podman kube generate`
- [ ] Запустил сгенерированный YAML через `podman kube play`
- [ ] Понимаю разницу между `kind: Pod` и `kind: Deployment` и когда что нужно
- [ ] Знаю что нужно изменить в YAML перед деплоем в реальный K8s

**Попробуйте сами:**
1. Создайте pod с nginx, выполните `podman kube generate`, откройте YAML и найдите строку `kind:`. Что там написано?
2. Запустите сгенерированный YAML через `podman kube play`, проверьте через `curl localhost:8080`, затем удалите через `podman kube down`.
3. Откройте Приложение D и вручную трансформируйте сгенерированный Pod в Deployment.

---

### Глава 8: Реестры образов — за пределами Docker Hub

**Что вы узнаете:**
- какие реестры кроме Docker Hub используются в production;
- как аутентифицироваться в нескольких реестрах одновременно;
- как поднять свой приватный реестр.

**Цель:** уйти от привязки к Docker Hub, знать альтернативы.

Популярные реестры:
```text
docker.io (Docker Hub):   docker pull nginx → docker.io/library/nginx
quay.io (Red Hat):        quay.io/prometheus/prometheus
ghcr.io (GitHub):         ghcr.io/owner/repo:tag
gcr.io (Google):          gcr.io/google-containers/pause
registry.k8s.io (K8s):    registry.k8s.io/pause:3.9
```

Работа с несколькими реестрами:
```bash
# Логин в Docker Hub
podman login docker.io

# Логин в GHCR с GitHub токеном
echo $GITHUB_TOKEN | podman login ghcr.io -u username --password-stdin

# Логин в Quay.io
podman login quay.io

# Список активных логинов
cat ~/.config/containers/auth.json
```

Кросс-реестровое копирование через skopeo (без скачивания на диск):
```bash
# Скопировать образ из Docker Hub в GHCR
skopeo copy \
  docker://docker.io/library/nginx:latest \
  docker://ghcr.io/myorg/nginx:latest

# Скопировать в локальный реестр
skopeo copy \
  docker://nginx:latest \
  docker://localhost:5000/nginx:latest
```

Свой локальный реестр:
```bash
# Запустить реестр через Podman
podman run -d \
  --name registry \
  -p 5000:5000 \
  -v registry-data:/var/lib/registry \
  registry:2

# Пушить образы
podman tag myapp:latest localhost:5000/myapp:latest
podman push localhost:5000/myapp:latest

# Настроить insecure registry (для localhost без TLS)
# В /etc/containers/registries.conf добавить:
# [[registry]]
# location = "localhost:5000"
# insecure = true
```

**Типичные ошибки:**
- `Error: unauthorized`: не выполнен `podman login` для нужного реестра.
- Rate limit на Docker Hub: 100 pulls/6h для анонимов → `podman login docker.io` или переходить на Quay.io.
- `localhost:5000` без `insecure = true` в `registries.conf`: push/pull будет падать с TLS-ошибкой.

**Чек-лист для самопроверки:**
- [ ] Вошёл в два разных реестра и проверил `~/.config/containers/auth.json`
- [ ] Скопировал образ между реестрами через `skopeo copy`
- [ ] Поднял локальный реестр и запушил в него образ
- [ ] Знаю в каком реестре живут официальные K8s-компоненты

**Попробуйте сами:**
1. Выполните `podman search python` — из скольких реестров приходят результаты?
2. Поднимите локальный реестр, запушите `nginx:alpine` под именем `localhost:5000/nginx:local`, затем запустите контейнер из этого образа.
3. Сравните `skopeo inspect docker://nginx:latest` и `skopeo inspect docker://nginx:alpine` — в чём разница в размере слоёв?

---

### Глава 9: Systemd и Podman — контейнеры как сервисы

**Что вы узнаете:**
- как запустить контейнер как systemd-сервис;
- что такое Quadlet и чем он лучше `podman generate systemd`;
- как настроить rootless автозапуск без root.

**Цель:** контейнеры которые стартуют при загрузке, пишут в journald, управляются через `systemctl`.

`podman generate systemd` — классический способ (устаревает в Podman 5.x, знать для понимания):
```bash
# Создать контейнер
podman run -d --name nginx-web nginx

# Сгенерировать unit-файл
podman generate systemd --new --name nginx-web > ~/.config/systemd/user/nginx-web.service

# Включить и запустить
systemctl --user daemon-reload
systemctl --user enable --now nginx-web.service

# Статус и логи
systemctl --user status nginx-web.service
journalctl --user -u nginx-web.service -f
```

Quadlet — современный способ (Podman 4.4+, рекомендуется):
```bash
# Создать файл ~/.config/containers/systemd/nginx.container
mkdir -p ~/.config/containers/systemd/

cat > ~/.config/containers/systemd/nginx.container << 'EOF'
[Unit]
Description=Nginx web server

[Container]
Image=docker.io/library/nginx:latest
PublishPort=8080:80
Volume=/home/user/html:/usr/share/nginx/html:ro

[Service]
Restart=always

[Install]
WantedBy=default.target
EOF

# Применить
systemctl --user daemon-reload

# Podman автоматически создал сервис nginx.service
systemctl --user start nginx.service
systemctl --user status nginx.service
```

Разница Quadlet vs `generate systemd`:
```text
generate systemd:
- на основе существующего контейнера
- deprecated начиная с Podman 5.x
- нужно сначала создать контейнер, потом генерировать

Quadlet:
- декларативный: описываешь желаемое состояние
- образ и контейнер создаются при старте сервиса
- обновление: изменить .container → daemon-reload → restart
- рекомендуется для всех новых систем
```

Автостарт без активного сеанса:
```bash
# Разрешить работу пользовательских сервисов без логина
sudo loginctl enable-linger $USER

# Проверить
loginctl show-user $USER | grep Linger
# Linger=yes — значит сервисы будут запускаться при загрузке
```

**Типичные ошибки:**
- Сервис останавливается при выходе из SSH-сессии: нужен `loginctl enable-linger`.
- `Failed to connect to bus`: экспортировать `XDG_RUNTIME_DIR=/run/user/$(id -u)`.
- Quadlet игнорирует `.container` файл: имя должно заканчиваться на `.container`, `.volume`, `.network`, или `.pod`.

**Чек-лист для самопроверки:**
- [ ] Запустил контейнер как Quadlet-сервис и проверил автостарт после reboot
- [ ] Смотрел логи контейнера через `journalctl --user -u <service>`
- [ ] Включил `linger` для пользователя
- [ ] Понимаю чем Quadlet лучше `generate systemd`

**Попробуйте сами:**
1. Создайте `.container` файл для nginx, примените через `daemon-reload` и убедитесь что сервис запустился.
2. Остановите сервис через `systemctl --user stop`, измените порт в `.container` файле, примените изменения через `daemon-reload` и `start`. Какой порт теперь?
3. Посмотрите логи nginx через `journalctl --user -u nginx.service` — что там написано при первом запуске?

---

### Глава 10: Сборка образов без Docker — buildah

**Что вы узнаете:**
- как buildah собирает OCI-образы без демона;
- как собирать образ пошагово через CLI (не только через Dockerfile);
- как встроить buildah в CI/CD pipeline.

**Цель:** понять что `podman build` и `buildah` — разные уровни одного процесса.

buildah vs podman build:
```text
podman build:
- использует buildah под капотом
- совместим с Dockerfile
- привычный интерфейс

buildah:
- низкоуровневый инструмент
- может собирать образы без Dockerfile
- поддерживает rootless сборку
- полезен в CI когда нет прав на запуск контейнеров
```

Сборка через Dockerfile (так же как docker build):
```bash
# Идентично podman build
buildah bud -t myapp:latest .
```

Сборка без Dockerfile — через shell-скрипт:
```bash
# Создать рабочий контейнер из базового образа
container=$(buildah from ubuntu:22.04)

# Выполнять команды внутри
buildah run $container -- apt-get update -qq
buildah run $container -- apt-get install -y python3 python3-pip

# Копировать файлы
buildah copy $container ./app /app

# Установить метаданные образа
buildah config --cmd "python3 /app/main.py" $container
buildah config --port 8000 $container
buildah config --env PYTHONUNBUFFERED=1 $container

# Сохранить как образ
buildah commit $container myapp:latest

# Удалить рабочий контейнер
buildah rm $container
```

Buildah в GitLab CI — rootless сборка без `--privileged`:
```yaml
build-image:
  image: quay.io/buildah/stable
  script:
    - buildah bud -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - buildah push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  variables:
    BUILDAH_ISOLATION: chroot   # ← важно для работы внутри CI-контейнера
```

**Типичные ошибки:**
- В CI без `BUILDAH_ISOLATION=chroot` сборка может не работать: добавить переменную.
- `buildah bud` и `podman build` имеют разный кэш: они не шарят слои между собой.

**Чек-лист для самопроверки:**
- [ ] Собрал образ через `buildah bud -t myapp:latest .`
- [ ] Собрал образ без Dockerfile через buildah-скрипт
- [ ] Понимаю разницу между `buildah` и `podman build`
- [ ] Знаю зачем нужен `BUILDAH_ISOLATION=chroot` в CI

**Попробуйте сами:**
1. Напишите buildah-скрипт который создаёт образ из `alpine`, устанавливает `curl` и сохраняет под именем `alpine-curl:local`. Проверьте: `podman run --rm alpine-curl:local curl --version`.
2. Сравните `podman images` после сборки через `podman build` и `buildah bud` — в одном ли хранилище образы?
3. Посмотрите рабочие контейнеры buildah командой `buildah containers`. Что показывает если незавершённая сборка прервалась?

---

### Глава 11: Миграция с Docker на Podman

**Что вы узнаете:**
- как перенести работающий Docker-проект на Podman пошагово;
- что проверить перед миграцией;
- как поддерживать совместимость если часть команды остаётся на Docker.

**Цель:** практическое руководство по миграции без простоя.

Чеклист перед миграцией:
```text
[ ] docker-compose.yml не использует Swarm-специфичные фичи (secrets, configs, deploy)
[ ] Образы без привязки к dockershim или Docker-специфичным API
[ ] Нет монтирования /var/run/docker.sock (или готовы заменить на podman.sock)
[ ] Порты: нет портов < 1024 без настройки
[ ] CI/CD скрипты: где используется docker — нужно будет заменить
```

Миграция шаг за шагом:
```bash
# Шаг 1: Установить Podman рядом с Docker (они не конфликтуют)
sudo apt install podman podman-compose

# Шаг 2: Проверить совместимость docker-compose.yml
podman-compose config   # покажет ошибки если есть

# Шаг 3: Запустить стек через podman-compose (не останавливая Docker!)
podman-compose up -d

# Шаг 4: Убедиться что всё работает
podman-compose ps
podman-compose logs

# Шаг 5: Когда всё проверено — остановить Docker стек
docker-compose down

# Шаг 6: Добавить алиасы
alias docker=podman
alias docker-compose=podman-compose
```

Перенос данных из Docker volumes в Podman:
```bash
# Docker-тома и Podman-тома — разные хранилища
# Экспортировать из Docker:
docker run --rm -v pgdata:/data alpine tar czf - /data > pgdata.tar.gz

# Импортировать в Podman:
podman volume create pgdata
podman run --rm -v pgdata:/data alpine tar xzf - -C / < pgdata.tar.gz
```

Совместное использование Docker + Podman в команде:
```bash
# Dockerfile и docker-compose.yml совместимы с обоими — не трогать
# В CI определить рантайм через переменную:
CONTAINER_TOOL=${CONTAINER_TOOL:-docker}
$CONTAINER_TOOL build -t myapp .
```

Что НЕ нужно мигрировать (работает без изменений):
- Образы на Docker Hub: совместимы с Podman.
- Dockerfile: совместим без изменений.
- docker-compose.yml: работает с podman-compose в большинстве случаев.

**Типичные ошибки:**
- Монтирование `-v /var/run/docker.sock`: заменить на `DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`.
- CI скрипт падает: заменить `docker` на `podman` в PATH.
- Данные потеряны: Docker volumes и Podman volumes — разные хранилища. Переносить явно.

**Чек-лист для самопроверки:**
- [ ] Мигрировал реальный docker-compose проект на podman-compose
- [ ] Проверил что данные в томах перенесены корректно
- [ ] Настроил CI для работы с Podman
- [ ] Знаю как поддерживать совместимость Docker/Podman в команде

**Попробуйте сами:**
1. Возьмите любой `docker-compose.yml` из своих проектов и запустите через `podman-compose up`. Что потребовало изменений?
2. Создайте Docker-том с тестовыми данными, экспортируйте его, создайте Podman-том и импортируйте. Проверьте что данные совпадают.
3. Напишите Makefile с целью `run` которая использует `CONTAINER_TOOL ?= podman` и работает как с docker-compose, так и с podman-compose.

---

### Глава 12: Podman в CI/CD — практические сценарии

**Что вы узнаете:**
- как использовать Podman в GitLab CI и GitHub Actions;
- rootless сборка образов без привилегированного режима;
- как кэшировать образы в CI.

**Цель:** настроить CI pipeline который строит и пушит образы через Podman без Docker daemon и без `--privileged`.

GitLab CI — сборка через Podman:
```yaml
variables:
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG

stages:
  - build
  - deploy

build:
  stage: build
  image: quay.io/podman/stable
  before_script:
    - podman login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - podman build --layers --cache-from $IMAGE_TAG -t $IMAGE_TAG .
    - podman push $IMAGE_TAG
  # Важно: не нужен privileged: true
```

GitHub Actions:
```yaml
name: Build and Push
on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Podman
        run: sudo apt-get install -y podman

      - name: Login to GHCR
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | \
          podman login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Build and push
        run: |
          podman build -t ghcr.io/${{ github.repository }}:latest .
          podman push ghcr.io/${{ github.repository }}:latest
```

Кэширование слоёв:
```bash
podman build \
  --cache-from registry.example.com/myapp:cache \
  --cache-to registry.example.com/myapp:cache \
  -t myapp:latest .
```

**Типичные ошибки:**
- `ERRO[0000] Error while loading /etc/containers/registries.conf`: использовать официальный podman-образ `quay.io/podman/stable`.
- Сборка зависает в rootless в CI: настроить `/etc/subuid` в CI-окружении или использовать `BUILDAH_ISOLATION=chroot`.

**Чек-лист для самопроверки:**
- [ ] Написал GitLab CI или GitHub Actions job который собирает образ через Podman
- [ ] CI работает без `privileged: true`
- [ ] Настроил кэширование слоёв
- [ ] Знаю как настроить логин в реестр из CI через secrets

**Попробуйте сами:**
1. Создайте минимальный GitHub Actions workflow который собирает образ из `Dockerfile` (можно пустой `FROM alpine`) и пушит в GHCR. Убедитесь что workflow завершается зелёным.
2. Добавьте кэширование через `--cache-from` и проверьте что повторный build использует кэш (время сборки уменьшится).
3. Найдите в логах CI строку которая подтверждает что privileged-режим не использован.

---

### Глава 13: Диагностика и типичные проблемы

**Что вы узнаете:**
- как читать логи Podman и находить причину проблемы;
- как диагностировать проблемы с rootless и правами;
- как очистить зависшее состояние без потери данных.

**Цель:** не теряться когда что-то идёт не так.

Инструменты диагностики:
```bash
# Системная информация
podman info
podman info --format json | python3 -m json.tool | grep -A5 security

# Проверить user namespaces и маппинг UID
podman unshare cat /proc/self/uid_map

# Диагностика конкретного контейнера
podman inspect <container>
podman top <container>
podman diff <container>       # что изменилось в ФС контейнера

# Подробные логи с уровнем debug
podman --log-level=debug run --rm alpine echo hi 2>&1 | head -50

# Статистика ресурсов
podman stats <container>
```

Типичные проблемы и решения:
```text
Проблема: "cannot re-exec process"
Причина: нет newuidmap/newgidmap или /etc/subuid не настроен
Решение: sudo apt install uidmap; podman system migrate

Проблема: контейнер останавливается при выходе из SSH
Причина: нет linger для пользователя
Решение: sudo loginctl enable-linger $USER

Проблема: "network slirp4netns not found"
Причина: отсутствует slirp4netns или pasta
Решение: sudo apt install slirp4netns

Проблема: "permission denied" при монтировании тома
Причина: SELinux label или UID mismatch
Решение: добавить :z (relabel SELinux) или --userns=keep-id

Проблема: образы не находятся без полного пути
Причина: не настроен unqualified-search-registries
Решение: добавить "docker.io" в registries.conf
```

Очистка:
```bash
# Удалить остановленные контейнеры
podman container prune

# Удалить неиспользуемые образы
podman image prune

# Посмотреть использование диска перед очисткой
podman system df
```

> ☠️ **Осторожно:** следующие команды удаляют данные без возможности восстановления.

```bash
# Удалить ВСЕ контейнеры, образы и тома (включая с данными!)
podman system prune --all --volumes

# Полный сброс состояния Podman (как чистая установка)
podman system reset
```

**Типичные ошибки:**
- Запустить `system prune --all --volumes` не проверив `podman volume ls` — можно потерять данные БД.
- `podman system reset` не спрашивает подтверждения в некоторых версиях — убедиться что резервные копии сделаны.

**Чек-лист для самопроверки:**
- [ ] Умею читать `podman inspect` и находить нужную информацию
- [ ] Решил хотя бы одну проблему с правами в rootless
- [ ] Знаю что делает `podman system migrate`
- [ ] Умею смотреть использование диска через `podman system df` перед очисткой

**Попробуйте сами:**
1. Запустите `podman run -d --name broken-app myapp:latest` (несуществующий образ). Найдите ошибку через `podman inspect broken-app` или `podman logs broken-app`.
2. Создайте несколько контейнеров и образов, запустите `podman system df` и посмотрите сколько места занято. Затем `podman container prune` — изменилась ли цифра?
3. Воспроизведите ошибку "permission denied" при монтировании тома, затем исправьте через `--userns=keep-id`.

---

### Глава 14: Итоговый проект — переводим реальный сервис

**Что вы узнаете:**
- как применить всё из книги на реальном проекте;
- как построить полный путь: dev → rootless podman → systemd → CI.

**Цель:** завершить книгу реальным работающим результатом.

Проект: веб-приложение (Python + PostgreSQL + Nginx) от разработки до production-ready сервиса.

**Шаг 1: Разработка**
```bash
# Запустить стек через podman-compose из docker-compose.yml
podman-compose up -d
# Убедиться что приложение доступно
curl http://localhost:8080
```

**Шаг 2: Rootless-проверка**
```bash
# Убедиться что ни одна команда не требует sudo
ps aux | grep "podman\|conmon"   # все процессы от текущего пользователя
```

**Шаг 3: Реестр**
```bash
# Запушить образ в GHCR или локальный реестр
podman tag myapp:latest ghcr.io/$USER/myapp:latest
podman push ghcr.io/$USER/myapp:latest
```

**Шаг 4: Systemd через Quadlet**
```bash
# Создать .container файл, применить daemon-reload
# Убедиться что сервис стартует после reboot
```

**Шаг 5: K8s YAML**
```bash
# Сгенерировать Pod YAML
podman kube generate myapp-pod > myapp-pod.yaml

# Адаптировать в Deployment (Приложение D)
# Проверить через podman kube play
podman kube play myapp-deployment.yaml
podman kube down myapp-deployment.yaml
```

**Шаг 6: CI**
```yaml
# GitHub Actions workflow
# Собрать и запушить образ при каждом push
```

**Критерии готовности:**
- [ ] Стек запускается через `podman-compose up` без ошибок
- [ ] Ни одна команда не требует `sudo`
- [ ] Сервис стартует при загрузке через Quadlet
- [ ] Образы запушены в реестр
- [ ] K8s YAML сгенерирован и проверен через `podman kube play`
- [ ] CI pipeline собирает и пушит образ при каждом push

---

## Приложения

### Приложение A: Шпаргалка команд

```bash
# Основные операции
podman run -d --name nginx-web nginx            # запустить в фоне
podman run -it --rm alpine sh                  # интерактивно, удалить после
podman run -p 8080:80 nginx                    # с пробросом порта
podman run -v /host/path:/container:ro nginx   # монтировать том (read-only)
podman run --env KEY=value myapp               # переменная окружения
podman run --userns=keep-id -v ./data:/data myapp  # rootless с правильными UID

# Управление контейнерами
podman ps                                       # запущенные
podman ps -a                                    # все
podman stop / start / restart <name>
podman rm <name>
podman logs -f <name>                           # логи в реальном времени
podman exec -it <name> bash                    # войти внутрь
podman inspect <name>                           # подробная информация
podman top <name>                               # процессы внутри
podman diff <name>                              # изменения в ФС

# Образы
podman images
podman pull nginx:latest
podman push registry/myapp:tag
podman build -t myapp:latest .
podman tag myapp:latest registry/myapp:v1
podman rmi myapp:latest
podman image prune

# Реестры
podman login docker.io
podman login ghcr.io -u user --password-stdin
podman search nginx

# Тома
podman volume create mydata
podman volume ls
podman volume inspect mydata
podman volume rm mydata

# Pods
podman pod create --name mypod -p 8080:80
podman run -d --pod mypod nginx
podman pod list
podman pod stop / rm mypod

# K8s интеграция
podman kube generate mypod > pod.yaml
podman kube play pod.yaml
podman kube down pod.yaml

# Systemd (Quadlet)
# Создать ~/.config/containers/systemd/myapp.container
systemctl --user daemon-reload
systemctl --user start myapp.service
journalctl --user -u myapp.service -f

# Диагностика
podman info
podman system df
podman unshare cat /proc/self/uid_map
podman stats

# Очистка (безопасная)
podman container prune
podman image prune
podman system df

# Очистка (ДЕСТРУКТИВНАЯ)
# ☠️ podman system prune --all --volumes  ← удаляет ВСЁ включая тома с данными
# ☠️ podman system reset                  ← полный сброс как чистая установка
```

---

### Приложение B: Таблица совместимости Docker → Podman

```text
Концепция          Docker                        Podman
────────────────────────────────────────────────────────────
Демон              dockerd (всегда запущен)       нет демона
Рантайм            runc через containerd          runc напрямую
Root               по умолчанию                   rootless по умолчанию
Socket             /var/run/docker.sock           /run/user/UID/podman.sock
Compose            docker-compose                 podman-compose
Реестр             docker.io (неявно)             нужно указывать явно
Хранилище          /var/lib/docker                ~/.local/share/containers
Systemd            manual unit                    Quadlet (.container файлы)
K8s YAML           нет                            podman kube generate
Build              docker build                   podman build / buildah
Сборка без root    сложно                         встроено
CLI совместимость  —                              100% для базовых команд
```

---

### Приложение C: Карта контейнерной экосистемы

```text
Уровень            Инструмент          Назначение
───────────────────────────────────────────────────────────────
Пользовательский   podman              запуск контейнеров
                   docker              запуск контейнеров
                   podman-compose      многоконтейнерные приложения
                   docker-compose      многоконтейнерные приложения
                   Podman Desktop      GUI для Podman (Windows/macOS)

Сборка образов     podman build        через Dockerfile
                   buildah             низкоуровневая сборка
                   kaniko              сборка в K8s без root
                   crane               работа с реестрами

Копирование        skopeo              кросс-реестровое копирование

K8s рантаймы       containerd          основной рантайм K8s
                   CRI-O               рантайм K8s от Red Hat

Низкий уровень     runc                OCI-рантайм (запускает контейнер)
                   crun                runc на C (быстрее, RHEL default)

Реестры            Docker Hub          docker.io
                   Quay.io             quay.io (Red Hat)
                   GHCR                ghcr.io (GitHub)
                   Harbor              self-hosted enterprise

Стандарты          OCI Image Spec      формат образа
                   OCI Runtime Spec    запуск контейнера
                   CRI                 интерфейс K8s к рантайму
```

---

### Приложение D: Из Pod в Deployment — адаптация K8s YAML

`podman kube generate` создаёт `kind: Pod`. Для продакшна нужен `kind: Deployment`. Вот пример трансформации.

**До (сгенерировано `podman kube generate`):**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: webapp
spec:
  containers:
  - name: web
    image: docker.io/library/nginx:latest
    ports:
    - containerPort: 80
```

**После (адаптировано в Deployment):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  replicas: 2                         # ← добавить репликацию
  selector:
    matchLabels:
      app: webapp                     # ← добавить selector
  template:
    metadata:
      labels:
        app: webapp                   # ← добавить labels
    spec:
      containers:
      - name: web
        image: ghcr.io/myorg/nginx:latest   # ← заменить localhost на реестр
        ports:
        - containerPort: 80
        resources:                    # ← добавить limits
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        readinessProbe:               # ← добавить probe
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
---
apiVersion: v1
kind: Service                         # ← добавить Service
metadata:
  name: webapp
spec:
  selector:
    app: webapp
  ports:
  - port: 80
    targetPort: 80
```

**Чеклист изменений при трансформации:**
- [ ] `kind: Pod` → `kind: Deployment`
- [ ] Добавить `apiVersion: apps/v1`
- [ ] Добавить `spec.replicas`
- [ ] Добавить `spec.selector.matchLabels`
- [ ] Завернуть `spec.containers` в `spec.template.spec.containers`
- [ ] Добавить `spec.template.metadata.labels` (должны совпадать с `selector`)
- [ ] Заменить `localhost/...` образы на реальный реестр
- [ ] Добавить `resources.requests/limits`
- [ ] Добавить `readinessProbe` и `livenessProbe`
- [ ] Создать отдельный `Service` для доступа к приложению

---

### Приложение E: Podman Machine (Windows и macOS)

> **Для кого:** читатели которые устанавливают Podman на Windows или macOS. На Linux Podman работает нативно и Podman Machine не нужен.

На Windows и macOS Linux-контейнеры запускаются внутри лёгкой виртуальной машины — это и есть Podman Machine.

**Установка:**
```bash
# macOS через Homebrew
brew install podman

# Windows через winget
winget install RedHat.Podman

# Инициализировать и запустить машину
podman machine init
podman machine start

# Проверить
podman info
podman run --rm alpine echo "работает"
```

**Основные команды:**
```bash
podman machine list           # список машин
podman machine start          # запустить
podman machine stop           # остановить
podman machine ssh            # войти в VM
podman machine rm             # удалить VM
podman machine inspect        # подробности
```

**Отличия от нативного Linux:**

| Аспект | Linux (нативный) | macOS/Windows (через Machine) |
|--------|-----------------|-------------------------------|
| Производительность | Нативная | Медленнее (VM overhead) |
| Тома | Прямые пути хоста | Автомонтирование через 9P |
| Порты | Прямые | Проксируются через VM |
| rootless | Нативный | Внутри VM |

**Типичные проблемы:**
- Том не монтируется: путь на хосте должен быть доступен VM. macOS автоматически расшаривает домашнюю директорию. Для других путей: `podman machine set --rootful` или явная конфигурация.
- Порт не доступен снаружи: на macOS порты проксируются, на Windows может потребоваться настройка firewall.
- "Machine does not exist": выполнить `podman machine init` перед первым запуском.
- Медленная первая сборка: VM скачивается при `machine init` (~700 MB).

**Объём: ~3 страницы.**

---

## Обязательные практические сценарии

**Базовые навыки:**
- Установить Podman и запустить первый rootless-контейнер без sudo.
- Настроить `alias docker=podman` и проверить что существующие скрипты работают.
- Поднять docker-compose стек через `podman-compose` без изменений в файле.
- Создать и опубликовать образ в GHCR или Quay.io.
- Сгенерировать K8s YAML из работающих контейнеров и адаптировать Pod в Deployment.
- Настроить автозапуск контейнера через Quadlet.

**Реальные проблемы (обязательно практиковать):**
- Мигрировать реальный docker-compose проект на podman-compose без даунтайма.
- Собрать rootless CI pipeline в GitLab или GitHub Actions без `--privileged`.
- Отладить rootless-проблему с правами на том (userns mismatch).
- Поднять локальный реестр, запушить образ, запустить из него контейнер.
- Настроить `linger` и убедиться что сервис стартует после reboot без логина пользователя.

---

## Особые требования

### Про тон

Читатель знает Docker. Не объяснять Docker с нуля — отсылать к книге 03 при необходимости. Подача: "ты уже умеешь X в Docker — вот как это выглядит в Podman и почему это лучше для безопасности". Не писать "Podman лучше" — показывать trade-offs объективно.

### Шаблон каждой главы (жёстко)

```
1. Блок «Что вы узнаете» (3–4 пункта, конкретные умения)
2. Основной текст с командами и объяснениями
3. «Типичные ошибки» (минимум 3, формат: ошибка → причина → решение)
4. «Чек-лист для самопроверки» (4–5 пунктов с [ ])
5. «Попробуйте сами» (2–3 упражнения с проверяемым результатом)
```

### Про примеры

Реальные имена: не `container1`, а `nginx-web`, `postgres-db`, `myapp-api`. Сценарии — веб-приложение + БД + reverse proxy.

### Про команды

Каждая нетривиальная команда сопровождается комментарием. Особенно: `podman kube generate`, `buildah`, `skopeo`, `podman unshare`, `loginctl enable-linger`.

### Про опасные команды

Каждая команда которая удаляет данные без возможности восстановления — маркировать `☠️ Осторожно:` с объяснением что именно удаляется.

### Про иллюстрации

В каждой главе с архитектурными концепциями — текстовая схема в ASCII. Три обязательные схемы (из раздела "Требования к иллюстрациям") — разместить в главах 1, 4, 5 соответственно.

### Критерии готовности

Книга готова если читатель:
- понимает что такое OCI и из каких компонентов состоит экосистема;
- запускает все контейнеры rootless без единого `sudo`;
- мигрировал реальный docker-compose проект на Podman;
- настроил автозапуск через Quadlet;
- сгенерировал K8s YAML и адаптировал Pod в Deployment;
- написал CI pipeline без Docker daemon и без `--privileged`.

### Не делать

- Не объяснять Docker с нуля — читатель знает его из книги 03.
- Не утверждать что Podman "заменяет Docker в Kubernetes": Podman не K8s-рантайм.
- Не писать "Podman лучше Docker" — объективно показывать trade-offs.
- Не давать опасные команды без ☠️-маркировки.
- Не показывать `podman kube generate` без предупреждения про Pod vs Deployment.
- Не углубляться в Kubernetes дальше `podman kube play`.
- Не описывать Podman Desktop подробно — только упоминание в приложении E.
- Не погружаться во внутренности cgroups и namespaces глубже чем нужно для понимания rootless.

---

## Источники и справочные материалы

- Официальная документация Podman: https://docs.podman.io/
- OCI спецификации: https://opencontainers.org/
- Podman GitHub: https://github.com/containers/podman
- buildah: https://buildah.io/
- skopeo: https://github.com/containers/skopeo
- Quadlet документация: https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html
- Red Hat блог по Podman: https://www.redhat.com/en/topics/containers/what-is-podman
