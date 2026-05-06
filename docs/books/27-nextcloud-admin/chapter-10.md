# Глава 10: Итоговая документация

> **Цель:** оставить после книги не знания в голове, а рабочую документацию своей установки.

---

## 10.1 Пример заполненной документации

Ниже — пример с реальными (анонимизированными) данными. Не шаблон с пустыми полями, а то, что должно быть заполнено.

```markdown
# Nextcloud — моя установка

## Компоненты

| Component                        | Container / path                                  | How to check                                  |
|----------------------------------|---------------------------------------------------|-----------------------------------------------|
| Nextcloud app                    | nextcloud-aio-nextcloud                           | `docker ps`, `occ status`                     |
| PostgreSQL                       | nextcloud-aio-database                            | `docker ps`, `docker logs ...database`        |
| Redis                            | nextcloud-aio-redis                               | `docker exec ... redis-cli ping`              |
| AIO mastercontainer              | nextcloud-aio-mastercontainer                     | http://server-ip:8080                         |
| Data directory                   | /var/lib/docker/volumes/nextcloud_aio_nextcloud_data/_data | `df -h`, `docker inspect nextcloud-aio-nextcloud` |
| Nginx config                     | /etc/nginx/sites-enabled/nextcloud.conf           | `nginx -t`                                    |
| Backups                          | /data/backups/nextcloud/                          | `ls -lh /data/backups/nextcloud/`             |

## Versions (последнее обновление: 2024-04-28)

- Nextcloud: 28.0.4
- PostgreSQL: 15.5
- Redis: 7.2
- AIO: 7.12.0
- OS: Ubuntu 22.04 LTS
- Docker: 24.0.7

## Important paths

- Data: /var/lib/docker/volumes/nextcloud_aio_nextcloud_data/_data
- Backups: /data/backups/nextcloud/
- Nginx config: /etc/nginx/sites-enabled/nextcloud.conf
- AIO config: /var/lib/docker/volumes/nextcloud_aio_mastercontainer/_data
- Backup script: /opt/scripts/nextcloud-backup.sh (cron: 0 3 * * *)

## Backup

- Method: pg_dump (автоматически) + AIO backup (перед обновлениями)
- Schedule: pg_dump — каждую ночь в 03:00 (cron)
- Retention: 7 дней локально, offsite — Backblaze B2
- Restore drill: выполнен 2024-03-15 на тестовой VM — успешно

## Update checklist

1. Проверить `df -h` — достаточно места (>15 GB свободно)
2. Запустить `occ status` — записать текущую версию
3. Запустить резервный бэкап: `pg_dump` + VPS snapshot
4. Включить maintenance: `occ maintenance:mode --on`
5. Выполнить обновление через AIO interface
6. После обновления: `occ status` — проверить новую версию
7. `occ db:add-missing-indices`
8. `occ maintenance:repair`
9. Выключить maintenance: `occ maintenance:mode --off`
10. Проверить логи: `docker logs nextcloud-aio-nextcloud --tail=50`
11. Проверить, что сайт открывается, работает загрузка файлов

## Diagnostics (runbook)

### Nextcloud не открывается

1. `curl -I https://nextcloud.example.com` — DNS и внешний доступ
2. `sudo nginx -t && sudo journalctl -u nginx --since "30 min ago"` — Nginx
3. `docker ps -a | grep nextcloud` — статус контейнеров
4. `docker logs nextcloud-aio-nextcloud --tail=50` — логи Nextcloud
5. `docker logs nextcloud-aio-database --tail=20` — логи PostgreSQL
6. `df -h` — место на диске
7. `occ status` → если `maintenance: true`: `occ maintenance:mode --off`
```

---

## 10.2 Критерии готовности

- Таблица контейнеров заполнена.
- `occ` работает.
- Backup plan описан.
- Restore drill запланирован или выполнен.
- Update checklist есть.
- Runbook аварии есть.
- Секреты не попали в документ.

---

## 10.3 Self-audit

Ты должен уметь объяснить:

- где лежат файлы и где метаданные;
- зачем PostgreSQL;
- зачем Redis;
- как включить/выключить maintenance mode;
- где смотреть логи;
- почему backup без restore drill не считается проверенным;
- как безопасно обновляться.

---

## 10.4 Runbook «Nextcloud не открывается» (итоговый)

Этот runbook — выжимка из главы 7, финальная версия для реальной аварии.

```bash
# Шаг 1: Внешний доступ
curl -I https://nextcloud.yourdomain.com
# Ожидаемо: HTTP/2 200. Если timeout — проблема в сети/DNS/Nginx.

# Шаг 2: Nginx
sudo nginx -t
sudo journalctl -u nginx --since "1 hour ago" | tail -20
# Ожидаемо: "test is successful". Ошибки — исправить конфиг.

# Шаг 3: Контейнеры
docker ps -a | grep nextcloud
# Ожидаемо: все "Up". Если "Exited" — читать логи этого контейнера.

# Шаг 4: Логи Nextcloud
docker logs nextcloud-aio-nextcloud --tail=100 2>&1 | grep -E "error|fatal|exception"
# Ожидаемо: пусто. Если есть ошибка — найти приложение, отключить через occ app:disable <name>

# Шаг 5: База данных
docker logs nextcloud-aio-database --tail=20
docker exec -it nextcloud-aio-database psql -U nextcloud -c "SELECT 1;"
# Ожидаемо: ?column? = 1

# Шаг 6: Диск
df -h
docker system df
# Ожидаемо: <90% использования. Если полный — чистить логи, старые образы.

# Шаг 7: Maintenance mode
occ status | grep maintenance
# Если "maintenance: true":
occ maintenance:mode --off
```
