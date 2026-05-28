# Приложение A: Шпаргалка команд

Все команды сгруппированы по задаче. Флаги которые нужны чаще всего — выделены.

---

## Образы

```bash
# Скачать образ
podman pull docker.io/library/nginx:latest
podman pull nginx               # если docker.io в unqualified-search-registries

# Список образов
podman images
podman images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Удалить образ
podman rmi nginx:latest
podman rmi --force nginx:latest   # если используется контейнером

# Удалить все неиспользуемые образы
podman image prune
podman image prune --all          # включая образы без тега

# Собрать образ
podman build -t myapp:latest .
podman build -f Dockerfile.prod -t myapp:prod .
podman build --no-cache -t myapp:fresh .
podman build --platform linux/arm64 -t myapp:arm64 .

# Тегировать
podman tag myapp:latest registry.example.com/myapp:v1.0

# Инспектировать
podman inspect myapp:latest
podman inspect myapp:latest --format '{{.Config.Cmd}}'
podman inspect myapp:latest --format '{{.Config.Entrypoint}}'

# История слоёв
podman history myapp:latest

# Сохранить/загрузить в tar
podman save -o myapp.tar myapp:latest
podman load -i myapp.tar
```

---

## Контейнеры — запуск

```bash
# Запустить и удалить после завершения
podman run --rm alpine echo hello

# Запустить в фоне (detached)
podman run -d --name web nginx:latest

# Интерактивный shell
podman run -it --rm ubuntu:22.04 bash
podman run -it --rm --entrypoint sh nginx:latest

# С пробросом портов
podman run -d -p 8080:80 nginx
podman run -d -p 127.0.0.1:8080:80 nginx    # только localhost

# С переменными окружения
podman run -d -e POSTGRES_PASSWORD=secret postgres:16

# С env-файлом
podman run -d --env-file .env myapp:latest

# С именованным томом
podman run -d -v pgdata:/var/lib/postgresql/data postgres:16

# С bind-mount
podman run -d -v /host/path:/container/path myapp
podman run -d -v /host/path:/container/path:ro myapp    # только чтение
podman run -d -v /host/path:/container/path:z myapp     # SELinux relabel

# Rootless: сохранить UID
podman run -d -v /host/path:/data --userns=keep-id myapp

# С ограничениями ресурсов
podman run -d --memory=512m --cpus=1.5 myapp

# С сетью
podman run -d --network mynetwork myapp
podman run -d --network host myapp

# С конкретным пользователем
podman run -d --user 1000:1000 myapp
```

---

## Контейнеры — управление

```bash
# Список запущенных
podman ps
podman ps -a                          # включая остановленные
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Остановить / убить
podman stop web
podman stop --time 30 web             # таймаут 30 секунд
podman kill web                       # SIGKILL

# Запустить / перезапустить
podman start web
podman restart web
podman restart --time 10 web

# Удалить
podman rm web
podman rm --force web                 # без предварительной остановки
podman rm $(podman ps -aq)            # удалить все остановленные

# Войти в запущенный контейнер
podman exec -it web bash
podman exec -it web sh                # если bash нет
podman exec web cat /etc/nginx/nginx.conf

# Логи
podman logs web
podman logs -f web                    # следить
podman logs --tail 50 web             # последние 50 строк
podman logs --since "1h" web          # за последний час

# Статистика
podman stats                          # все контейнеры
podman stats web                      # конкретный
podman top web                        # процессы внутри

# Копировать файлы
podman cp web:/etc/nginx/nginx.conf ./nginx.conf
podman cp ./nginx.conf web:/etc/nginx/nginx.conf

# Diff — что изменилось
podman diff web

# Порты
podman port web
podman port web 80
```

---

## Тома (volumes)

```bash
# Список томов
podman volume ls
podman volume ls --filter dangling=true

# Создать
podman volume create pgdata
podman volume create --label project=myapp pgdata

# Инспектировать
podman volume inspect pgdata
podman volume inspect pgdata --format '{{.Mountpoint}}'

# Удалить
podman volume rm pgdata
podman volume prune                   # неиспользуемые
podman volume prune --force

# Экспорт/импорт данных тома
podman run --rm \
  -v pgdata:/source:ro \
  -v /tmp:/backup \
  alpine tar czf /backup/pgdata.tar.gz -C /source .

podman run --rm \
  -v pgdata:/dest \
  -v /tmp:/backup \
  alpine sh -c "cd /dest && tar xzf /backup/pgdata.tar.gz"
```

---

## Сети

```bash
# Список сетей
podman network ls

# Создать сеть
podman network create mynetwork
podman network create --subnet 172.20.0.0/16 mynetwork
podman network create --driver bridge mynetwork

# Инспектировать
podman network inspect mynetwork

# Подключить/отключить контейнер
podman network connect mynetwork web
podman network disconnect mynetwork web

# Удалить
podman network rm mynetwork
podman network prune

# Диагностика сети
podman exec web ping db
podman exec web ss -tlnp
podman exec web cat /etc/resolv.conf
```

---

## Поды

```bash
# Создать под
podman pod create --name mypod
podman pod create --name mypod -p 8080:80

# Список подов
podman pod ls
podman pod ps

# Запустить/остановить под
podman pod start mypod
podman pod stop mypod
podman pod restart mypod

# Добавить контейнер в под
podman run -d --pod mypod --name web nginx
podman run -d --pod mypod --name app myapp

# Логи всего пода
podman pod logs mypod

# Удалить под (и все контейнеры)
podman pod rm mypod
podman pod rm --force mypod

# Статистика
podman pod stats mypod

# Инспектировать
podman pod inspect mypod
```

---

## Реестры

```bash
# Войти / выйти
podman login docker.io
podman login docker.io -u myuser --password-stdin
podman logout docker.io

# Посмотреть сохранённые учётные данные
cat ~/.config/containers/auth.json

# Поиск образов
podman search nginx
podman search nginx --limit 5
podman search --filter is-official nginx

# Пушить образ
podman push myapp:latest docker.io/myuser/myapp:latest
podman push myapp:latest
```

---

## skopeo

```bash
# Установить
sudo apt install skopeo

# Инспектировать без скачивания
skopeo inspect docker://docker.io/library/nginx:latest
skopeo inspect docker://nginx:latest --format '{{.Digest}}'

# Список тегов
skopeo list-tags docker://docker.io/library/nginx

# Скопировать между реестрами
skopeo copy docker://nginx:latest docker://my-registry.com/nginx:latest

# Скопировать из Docker в Podman storage
skopeo copy docker-daemon:nginx:alpine containers-storage:nginx:alpine

# Скопировать в tar
skopeo copy docker://nginx:latest docker-archive:nginx.tar

# Синхронизировать реестры
skopeo sync --src docker --dst docker \
  docker.io/library/nginx my-registry.com/mirror
```

---

## buildah

```bash
# Собрать из Dockerfile
buildah bud -t myapp:latest .
buildah bud --no-cache -t myapp:fresh .
buildah bud --layers -t myapp:cached .

# Создать рабочий контейнер
ctr=$(buildah from alpine:latest)

# Выполнить команду в рабочем контейнере
buildah run $ctr -- apk add curl
buildah run -t $ctr -- bash     # интерактивно (для отладки)

# Скопировать файлы в рабочий контейнер
buildah copy $ctr ./app /app

# Настроить метаданные
buildah config --cmd '["python", "main.py"]' $ctr
buildah config --env KEY=value $ctr
buildah config --workingdir /app $ctr
buildah config --port 8080 $ctr
buildah config --user 1000:1000 $ctr

# Зафиксировать как образ
buildah commit $ctr myapp:latest
buildah commit --squash $ctr myapp:squashed   # объединить слои

# Список рабочих контейнеров
buildah containers

# Удалить рабочие контейнеры
buildah rm $ctr
buildah rm --all

# Запушить образ
buildah push myapp:latest docker://registry.example.com/myapp:latest

# Войти в реестр
buildah login registry.example.com -u user --password-stdin
```

---

## Systemd / Quadlet

```bash
# Каталог для Quadlet-файлов (rootless)
~/.config/containers/systemd/

# Каталог для системных Quadlet-файлов
/etc/containers/systemd/

# После изменения .container файлов
systemctl --user daemon-reload

# Управление сервисом
systemctl --user start nginx-web.service
systemctl --user stop nginx-web.service
systemctl --user restart nginx-web.service
systemctl --user status nginx-web.service
systemctl --user enable nginx-web.service

# Логи контейнера через journalctl
journalctl --user -u nginx-web.service
journalctl --user -u nginx-web.service -f         # следить
journalctl --user -u nginx-web.service --since "1h"

# Посмотреть сгенерированный unit
systemctl --user cat nginx-web.service

# Включить linger (чтобы сервисы жили без активного SSH)
sudo loginctl enable-linger $USER
loginctl show-user $USER | grep Linger

# Если нет XDG_RUNTIME_DIR
export XDG_RUNTIME_DIR=/run/user/$(id -u)
```

---

## Диагностика

```bash
# Информация об установке
podman info
podman info --format '{{.Host.Security}}'
podman info --format '{{.Store.GraphDriverName}}'

# Версия
podman version

# События системы
podman events
podman events --since "1h"
podman events --filter container=web
podman events --filter event=die --since "24h"

# Ресурсы
podman system df
podman system df --format "table {{.Type}}\t{{.Total}}\t{{.Size}}\t{{.Reclaimable}}"

# Миграция после обновления
podman system migrate

# Очистка
podman container prune
podman image prune
podman network prune
podman volume prune
podman system prune

# ☠️ Деструктивная очистка
podman system prune --all --volumes   # удаляет ВСЁ включая тома
podman system reset                   # полный сброс как чистая установка

# Debug-логи
podman --log-level=debug run --rm alpine echo hi 2>&1 | head -50

# Rootless диагностика
podman unshare ls -la /path/to/mount
cat /etc/subuid | grep $USER
cat /proc/sys/user/max_user_namespaces
```

---

## podman-compose

```bash
# Запустить стек
podman-compose up -d

# Остановить
podman-compose down

# Остановить и удалить тома
podman-compose down -v

# Логи
podman-compose logs
podman-compose logs -f web

# Статус
podman-compose ps

# Выполнить команду в контейнере
podman-compose exec web bash

# Перезапустить один сервис
podman-compose restart web

# Собрать образы
podman-compose build
podman-compose build --no-cache

# Проверить конфиг
podman-compose config
```

---

## Работа с K8s YAML

```bash
# Генерировать K8s YAML из пода
podman kube generate mypod > pod.yaml
podman kube generate mypod --service > pod-with-svc.yaml

# Запустить из K8s YAML
podman kube play pod.yaml
podman kube play pod.yaml --network mynetwork

# Остановить запущенное из YAML
podman kube down pod.yaml

# ⚠️ kube generate создаёт kind: Pod, не Deployment
# Для K8s production — конвертировать вручную (см. Приложение D)
```

---

## Быстрый старт типичных задач

```bash
# Запустить nginx на 8080
podman run -d --name nginx -p 8080:80 nginx

# Запустить postgres с данными
podman run -d --name pg \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=mydb \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16-alpine

# Подключиться к postgres
podman exec -it pg psql -U postgres -d mydb

# Собрать и запустить своё приложение
podman build -t myapp:dev .
podman run -d --name myapp \
  -p 8000:8000 \
  -v ./app:/app \
  myapp:dev

# Пушить в registry
podman login docker.io
podman tag myapp:dev docker.io/myuser/myapp:latest
podman push docker.io/myuser/myapp:latest

# Скопировать образ между реестрами без скачивания
skopeo copy \
  docker://docker.io/library/nginx:latest \
  docker://my-registry.com/cache/nginx:latest
```
