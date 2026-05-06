# Глава 8: Docker hardening

> **Цель:** контейнеры не должны открывать лишнее и работать с лишними правами.

---

## 8.1 Что проверить

```bash
docker ps
docker inspect <container> | grep -A5 '"User"'
```

# Пример вывода `docker inspect`:
```json
            "User": "1000",
            "AttachStdin": false,
            "AttachStdout": false,
            "AttachStderr": false,
            "ExposedPorts": {
```

`"User": "1000"` — контейнер работает от непривилегированного пользователя. Если видишь `"User": ""` или `"User": "root"` — контейнер работает от root внутри (риск).

```bash
sudo iptables -t nat -L DOCKER --line-numbers
```

# Пример вывода:
```
Chain DOCKER (2 references)
num  target     prot opt source               destination
1    RETURN     all  --  anywhere             anywhere
2    DNAT       tcp  --  anywhere             anywhere             tcp dpt:8080 to:172.17.0.2:8080
```

Docker может публиковать порты в обход твоего ощущения от ufw. Поэтому всегда проверяй `ss -tlnp` и публикацию ports в compose.

---

## 8.2 Безопасные привычки

```yaml
services:
  app:
    image: example/app:stable
    ports:
      - "127.0.0.1:8080:8080"
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
```

Если приложение поддерживает:

```yaml
    user: "1000:1000"
    read_only: true
    cap_drop:
      - ALL
```

Но это может сломать приложение. Сначала тестируй на стенде.

---

## 8.3 Как проверить что cap_drop: ALL не сломало контейнер

После добавления `cap_drop: ALL` и `security_opt: no-new-privileges:true` нужно убедиться, что контейнер работает корректно.

```bash
# Смотри логи сразу после запуска
docker compose up -d
docker logs <container> --tail 50
```

# Пример вывода при проблеме:
```
Error: EPERM: operation not permitted, open '/app/data/config.json'
failed to bind socket: permission denied
```

Если в логах ошибки с `permission denied` или `operation not permitted` — контейнеру нужны capabilities.

```bash
# Проверь, что приложение отвечает
docker exec <container> curl -s http://localhost:8080/health
```

Если тест функциональности проходит — `cap_drop: ALL` не сломал контейнер. Если нет — добавляй только нужные capabilities по одной:

```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE   # если нужно слушать порты < 1024
  - CHOWN              # если нужно менять владельца файлов
```

---

## 8.4 read_only: true и tmpfs

`read_only: true` запрещает запись в файловую систему контейнера. Многие приложения при этом падают, потому что пишут временные файлы, сокеты или pid-файлы.

> **Аналогия:** `read_only: true` — как дать сотруднику только читающий бейдж. Он может работать, если все нужные данные уже на месте. Но если работа требует сделать заметки — нужен блокнот. tmpfs — это этот блокнот: в памяти, при перезапуске исчезает.

Решение — добавить tmpfs для директорий с временными файлами:

```yaml
services:
  app:
    image: example/app:stable
    read_only: true
    tmpfs:
      - /tmp
      - /run
      - /var/run
    volumes:
      - ./data:/app/data   # постоянные данные через volume
```

Как найти, какие директории нужны: запусти без `read_only`, потом добавь, смотри в логи что упало. Чаще всего это `/tmp`, `/run`, `/var/run`, иногда `/var/cache`.

---

## 8.5 Образы и обновления

Не используй `latest` без понимания. Для важных сервисов лучше фиксировать версию и обновлять осознанно.

Сканирование образов подробно будет в книге 26, здесь минимум:

```bash
docker images
docker compose pull
docker compose up -d
```

---

## 8.6 Если что-то пошло не так

> **Если что-то пошло не так:**
>
> **Симптом:** Контейнер не стартует после добавления `cap_drop: ALL`.
>
> 1. Смотри логи: `docker logs <container> 2>&1 | tail -30`
> 2. Если ошибка `operation not permitted` — найди, какая операция требует capability.
> 3. Запусти временно без cap_drop и с `strace` (или через `--cap-add ALL`) чтобы понять, что нужно.
> 4. Добавляй capabilities по минимуму через `cap_add`.
>
> **Симптом:** После `read_only: true` контейнер стартует, но через время падает.
>
> 1. `docker logs <container>` — ищи ошибки записи.
> 2. Добавь нужную директорию в tmpfs.
> 3. Если нужна постоянная запись — используй volume, а не tmpfs.

---

## 8.7 Практика

Выбери один контейнер и проверь:

- под каким user он работает;
- какие порты публикует;
- нужен ли ему доступ наружу;
- можно ли привязать порт к `127.0.0.1`.

Не меняй все контейнеры сразу.
