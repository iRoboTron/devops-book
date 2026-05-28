# Приложение B: Таблица совместимости Docker → Podman

## Команды

Большинство команд идентичны — достаточно заменить `docker` на `podman`.

| Docker | Podman | Примечание |
|--------|--------|------------|
| `docker run` | `podman run` | Идентично |
| `docker build` | `podman build` | Идентично |
| `docker pull` | `podman pull` | Идентично |
| `docker push` | `podman push` | Идентично |
| `docker ps` | `podman ps` | Идентично |
| `docker images` | `podman images` | Идентично |
| `docker logs` | `podman logs` | Идентично |
| `docker exec` | `podman exec` | Идентично |
| `docker stop` | `podman stop` | Идентично |
| `docker rm` | `podman rm` | Идентично |
| `docker rmi` | `podman rmi` | Идентично |
| `docker volume ls` | `podman volume ls` | Идентично |
| `docker network ls` | `podman network ls` | Идентично |
| `docker inspect` | `podman inspect` | Идентично |
| `docker stats` | `podman stats` | Идентично |
| `docker top` | `podman top` | Идентично |
| `docker cp` | `podman cp` | Идентично |
| `docker diff` | `podman diff` | Идентично |
| `docker tag` | `podman tag` | Идентично |
| `docker login` | `podman login` | Идентично |
| `docker logout` | `podman logout` | Идентично |
| `docker search` | `podman search` | Идентично |
| `docker save` | `podman save` | Идентично |
| `docker load` | `podman load` | Идентично |
| `docker history` | `podman history` | Идентично |
| `docker port` | `podman port` | Идентично |
| `docker pause` | `podman pause` | Идентично |
| `docker unpause` | `podman unpause` | Идентично |
| `docker kill` | `podman kill` | Идентично |
| `docker rename` | `podman rename` | Идентично |
| `docker restart` | `podman restart` | Идентично |
| `docker create` | `podman create` | Идентично |
| `docker start` | `podman start` | Идентично |
| `docker wait` | `podman wait` | Идентично |
| `docker events` | `podman events` | Идентично |
| `docker system df` | `podman system df` | Идентично |
| `docker system prune` | `podman system prune` | Идентично |
| `docker image prune` | `podman image prune` | Идентично |
| `docker container prune` | `podman container prune` | Идентично |
| `docker network prune` | `podman network prune` | Идентично |
| `docker volume prune` | `podman volume prune` | Идентично |
| `docker swarm init` | — | Swarm не поддерживается |
| `docker service create` | — | Swarm не поддерживается |
| `docker stack deploy` | — | Swarm не поддерживается |
| `docker compose` | `podman-compose` | Отдельный пакет, см. ниже |
| `docker buildx` | `podman build --platform` | Встроено в podman build |

---

## docker-compose vs podman-compose

| Директива | docker-compose | podman-compose | Примечание |
|-----------|---------------|----------------|------------|
| `services` | ✅ | ✅ | |
| `image` | ✅ | ✅ | |
| `build` | ✅ | ✅ | |
| `ports` | ✅ | ✅ | rootless: не < 1024 |
| `volumes` (named) | ✅ | ✅ | |
| `volumes` (bind) | ✅ | ✅ | права могут отличаться |
| `environment` | ✅ | ✅ | |
| `env_file` | ✅ | ✅ | |
| `depends_on` | ✅ | ✅ | |
| `networks` | ✅ | ✅ | |
| `restart` | ✅ | ✅ | |
| `command` | ✅ | ✅ | |
| `entrypoint` | ✅ | ✅ | |
| `healthcheck` | ✅ | ✅ | |
| `labels` | ✅ | ✅ | |
| `user` | ✅ | ✅ | |
| `working_dir` | ✅ | ✅ | |
| `sysctls` | ✅ | ✅ | |
| `cap_add/cap_drop` | ✅ | ✅ | |
| `ulimits` | ✅ | ✅ | |
| `tmpfs` | ✅ | ✅ | |
| `stdin_open/tty` | ✅ | ✅ | |
| `secrets` (файловые) | ✅ | ⚠️ | частично |
| `deploy` (Swarm) | ✅ | ❌ | не поддерживается |
| `configs` (Swarm) | ✅ | ❌ | не поддерживается |
| `secrets` (Swarm) | ✅ | ❌ | не поддерживается |
| `extensions` (x-*) | ✅ | ⚠️ | не все |
| Broadcast/multicast | ✅ | ❌ | не поддерживается |

---

## Пути и файлы конфигурации

| Что | Docker | Podman (rootless) | Podman (root) |
|-----|--------|-------------------|---------------|
| Хранилище образов | `/var/lib/docker/` | `~/.local/share/containers/storage/` | `/var/lib/containers/storage/` |
| Сокет | `/var/run/docker.sock` | `/run/user/$(id -u)/podman/podman.sock` | `/run/podman/podman.sock` |
| Конфиг реестров | `/etc/docker/daemon.json` | `~/.config/containers/registries.conf` | `/etc/containers/registries.conf` |
| Конфиг хранилища | `/etc/docker/daemon.json` | `~/.config/containers/storage.conf` | `/etc/containers/storage.conf` |
| Конфиг контейнеров | `/etc/docker/daemon.json` | `~/.config/containers/containers.conf` | `/etc/containers/containers.conf` |
| Учётные данные реестров | `~/.docker/config.json` | `~/.config/containers/auth.json` | `/run/containers/0/auth.json` |
| Docker socket env | `DOCKER_HOST` | `DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock` | |
| Тома | `/var/lib/docker/volumes/` | `~/.local/share/containers/storage/volumes/` | `/var/lib/containers/storage/volumes/` |

---

## Концепции и архитектура

| Концепция | Docker | Podman | Разница |
|-----------|--------|--------|---------|
| Daemon | Да (dockerd) | Нет | Podman fork-exec |
| Процесс-монитор | — | conmon | Следит за контейнером |
| Rootless | Ограничено (rootless mode) | Нативно | Podman с самого начала |
| Namespace | User NS опционально | User NS нативно | |
| Подов | Нет | Да | `podman pod create` |
| Systemd интеграция | Вручную | Quadlet (нативно) | .container файлы |
| K8s YAML | Через compose | `podman kube generate/play` | Нативная поддержка |
| Инструмент сборки | Docker builder | buildah (под капотом) | |
| Compose | docker compose (встроено) | podman-compose (отдельно) | |
| Desktop GUI | Docker Desktop | Podman Desktop | Разные программы |
| Swarm | Да | Нет | Используйте K8s вместо Swarm |

---

## Поведение rootless: отличия от Docker

| Аспект | Docker rootless | Podman rootless |
|--------|----------------|----------------|
| Порты < 1024 | Нет (sysctl нужен) | Нет (тот же sysctl) |
| /etc/subuid | Нужен | Нужен |
| UID внутри = root | Да (маппируется) | Да (маппируется) |
| Bind-mount права | Могут быть проблемы | Те же проблемы |
| `--userns=keep-id` | Нет | Да — удобно для томов |
| Сеть | slirp4netns или pasta | slirp4netns или pasta (pasta в Podman 5+) |
| Performance | Незначительное снижение | То же |

---

## Переменные окружения

| Переменная | Docker | Podman |
|-----------|--------|--------|
| `DOCKER_HOST` | Адрес daemon | Работает (для совместимости) |
| `DOCKER_TLS_VERIFY` | TLS проверка | Работает |
| `DOCKER_CERT_PATH` | Путь к сертам | Работает |
| `BUILDKIT_PROGRESS` | Вывод сборки | Не нужна (нет BuildKit) |
| `COMPOSE_FILE` | Файл compose | Работает в podman-compose |
| `COMPOSE_PROJECT_NAME` | Префикс проекта | Работает в podman-compose |
| `TESTCONTAINERS_RYUK_DISABLED` | Не нужна | Нужна (Ryuk не работает rootless) |
| `STORAGE_DRIVER` | Не нужна | `vfs` для CI в контейнере |
| `BUILDAH_ISOLATION` | Не нужна | `chroot` для buildah в CI |

---

## Аналоги инструментов

| Задача | Docker экосистема | Podman экосистема |
|--------|------------------|------------------|
| Запуск контейнеров | docker | podman |
| Compose | docker compose / docker-compose | podman-compose |
| Сборка образов | docker build / BuildKit | podman build / buildah |
| Копирование между реестрами | docker pull + push | skopeo copy |
| Инспекция без скачивания | — | skopeo inspect |
| Rootless сборка в CI | docker buildx (root) | buildah bud (rootless) |
| Реестр | Docker Hub, Docker Registry | Quay, Harbor, любой OCI-реестр |
| Systemd интеграция | вручную | Quadlet |
| K8s YAML | kubectl, Helm | podman kube |
| Desktop | Docker Desktop | Podman Desktop |
| Swarm | docker swarm | — (используйте K8s) |
