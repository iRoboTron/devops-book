# Приложение B: Runbook аварий

## Nextcloud не открывается

**Шаг 1: Проверить DNS/HTTPS**

```bash
curl -I https://yourdomain.com
```

# Пример вывода (всё хорошо):
```
HTTP/2 200
server: nginx/1.24.0
content-type: text/html; charset=UTF-8
```

# Пример вывода (проблема):
```
curl: (6) Could not resolve host: yourdomain.com
# → проблема DNS
```

```
curl: (7) Failed to connect to yourdomain.com port 443: Connection refused
# → Nginx не слушает или упал
```

**Шаг 2: Проверить Nginx**

```bash
sudo nginx -t
sudo journalctl -u nginx --since "1 hour ago"
```

# Пример вывода (OK):
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

# Пример вывода (ошибка):
```
nginx: [emerg] unknown directive "ssl_certifcate" in /etc/nginx/sites-enabled/nextcloud.conf:12
nginx: configuration file /etc/nginx/nginx.conf test failed
```

**Шаг 3: Проверить контейнеры**

```bash
docker ps -a | grep nextcloud
```

# Пример вывода (проблема):
```
nextcloud-aio-nextcloud   Exited (1) 5 minutes ago
nextcloud-aio-database    Up 3 days
nextcloud-aio-redis       Up 3 days
```

→ `nextcloud-aio-nextcloud` упал. Читать его логи.

**Шаг 4: Проверить Nextcloud logs**

```bash
docker logs nextcloud-aio-nextcloud --tail=100
```

# Пример вывода (ошибка из-за приложения):
```
2024-04-28 11:23:14 [error] [no app in context] Error PHP Fatal error:
  Uncaught Error: Call to undefined method OCA\Deck\Service\...
  in /var/www/html/apps/deck/lib/Service/CardService.php:142
```

→ отключить: `occ app:disable deck`

**Шаг 5: Проверить БД**

```bash
docker logs nextcloud-aio-database --tail=100
```

# Пример вывода (нормально):
```
2024-04-28 03:00:01 UTC [1] LOG:  database system is ready to accept connections
```

# Пример вывода (проблема — нет места):
```
2024-04-28 11:20:01 UTC [856] PANIC: could not write to file "pg_wal/000000010000002A00000014": No space left on device
```

**Шаг 6: Проверить диск**

```bash
df -h
docker system df
```

# Пример вывода (критическое заполнение):
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   50G     0 100% /
```

→ Удалить неиспользуемые образы: `docker image prune -f`

**Шаг 7: Проверить maintenance mode**

```bash
occ status
occ maintenance:mode --off
```

---

## Nextcloud работает медленно

```bash
# Проверить Redis
docker exec nextcloud-aio-redis redis-cli ping
docker exec nextcloud-aio-redis redis-cli info | grep -E "used_memory_human|keyspace_hits|keyspace_misses"

# Проверить место
df -h

# Проверить предупреждения
occ system:check

# Обновить индексы
occ db:add-missing-indices
```

---

## Пользователь не может войти

```bash
# Проверить что пользователь включён
occ user:info username

# Сбросить пароль
occ user:resetpassword username

# Проверить, нет ли блокировки (brute force)
# Admin → Security → Brute-force settings → Whitelist
```

---

## После обновления ошибка 500

```bash
# Смотреть логи
docker logs nextcloud-aio-nextcloud --tail=200 2>&1 | grep -i "error\|exception\|fatal"

# Найти виновное приложение, отключить
occ app:disable <app-name>

# Запустить ремонт
occ maintenance:repair

# Обновить индексы
occ db:add-missing-indices
```

---

## План внедрения

### За 1 день

Инвентаризация (`docker ps`, `docker volume ls`), настройка `occ` функции, просмотр логов.

### За 1 неделю

Backup plan с конкретными путями, update checklist, security checklist (trusted_domains, trusted_proxies, overwriteprotocol).

### За 1 месяц

Restore drill на тестовой VM, финальная документация (`NEXTCLOUD-RUNBOOK.md`), ревизия приложений и пользователей.
