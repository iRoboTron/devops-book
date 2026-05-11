# Глава 11: Итоговый проект — operability review

> **Цель:** провести ревизию своего приложения как эксплуатационного объекта.

---

## 11.1 Что нужно сделать

Создай документ `OPERABILITY-REVIEW.md`.

Он должен содержать:

1. схему приложения;
2. карту stateful-частей;
3. config inventory;
4. healthcheck/readiness proposal;
5. shutdown/startup checklist;
6. migration checklist;
7. timeout/retry policy;
8. logging checklist;
9. rollback plan;
10. operability score.

---

## 11.2 Шаблон

```markdown
# Operability review

## Сервис
Что делает, кто пользователь.

## Архитектура
ASCII-схема компонентов.

## State
| State | Где хранится | Backup | Restore |

## Config/secrets
| Переменная | Secret? | Где задаётся |

## Health/readiness
- /healthz:
- /readyz:

## Deploy/rollback
Как деплоим:
Как откатываем:

## Database migrations
Как запускаются:
Как проверяются:

## Dependencies and timeouts
| Dependency | Timeout | Retry |

## Logs/metrics
Какие логи, какие request_id, какие метрики.

## Top risks
| Риск | Что сделать |

## Improvements
### 1 день
### 1 неделя
### 1 месяц
```

---

## 11.2а Заполненный пример: Nextcloud на одном сервере

Учебный сервис: Nextcloud (файловое хранилище), развёрнутый на одном VPS с Docker Compose. Компоненты: Nextcloud (PHP-FPM), PostgreSQL, Nginx (reverse proxy). Пользователи: команда 5–20 человек, хранение файлов и заметок.

```markdown
# Operability review — Nextcloud (one-server Docker Compose)

## Сервис
Nextcloud — self-hosted файловое хранилище для команды.
Пользователи: сотрудники компании (5–20 человек).
Критичность: средняя — потеря файлов недопустима, даунтайм несколько часов терпим.

## Архитектура

```text
Internet
  │
  ▼
[Nginx :443]  ← TLS termination, Let's Encrypt
  │
  ▼
[Nextcloud :9000]  ← PHP-FPM в Docker-контейнере
  │           │
  ▼           ▼
[PostgreSQL]  [/data volume]  ← файлы пользователей (bind mount /srv/nextcloud/data)
```

Все контейнеры управляются одним `docker-compose.yml`.
Нет балансировщика нагрузки, нет кластера — один сервер.

## State

| State | Где хранится | Backup | Restore |
|---|---|---|---|
| Файлы пользователей | /srv/nextcloud/data (bind mount) | rsync → S3 ночью | Копируем обратно из S3 |
| База данных | Docker volume `pgdata` | pg_dump → S3 ночью | pg_restore из S3 |
| Конфиг Nextcloud | /srv/nextcloud/config/config.php | Включён в rsync | Копируем вручную |
| TLS-сертификаты | /etc/letsencrypt | Не бэкапятся | certbot renew |

## Config/secrets

| Переменная | Secret? | Где задаётся |
|---|---|---|
| POSTGRES_PASSWORD | Да | .env (не в git) |
| NEXTCLOUD_ADMIN_PASSWORD | Да | .env (не в git) |
| NEXTCLOUD_TRUSTED_DOMAINS | Нет | docker-compose.yml |
| SMTP_HOST / SMTP_PASSWORD | Да | .env (не в git) |
| S3_BUCKET / S3_KEY | Да | .env на сервере |

## Health/readiness

- /healthz: нет встроенного endpoint. Используем `curl -sf https://cloud.example.com/status.php` — возвращает JSON `{"installed":true,"maintenance":false}`. Проверяется каждые 60 сек через UptimeRobot.
- /readyz: отдельного readiness endpoint нет. Проблема: при старте контейнер отвечает 502 пока PHP-FPM не поднялся. Nginx даёт ошибку пользователям в этот момент (~15–30 сек).

## Deploy/rollback

Как деплоим:
1. `git pull` на сервере (обновляем docker-compose.yml и .env если нужно)
2. `docker compose pull nextcloud`
3. `docker compose up -d nextcloud`
4. Проверяем `curl -sf https://cloud.example.com/status.php`
5. Проверяем `docker compose logs nextcloud --tail=50`

Как откатываем:
- Для кода: `docker compose up -d nextcloud` с пинингом предыдущего тега образа в docker-compose.yml.
- Для БД: если миграция Nextcloud применилась — нужен pg_restore из последнего backup. Это занимает ~10–30 минут. Плана автоматического rollback нет — делается вручную.

## Database migrations

Как запускаются: автоматически при старте контейнера Nextcloud (`occ upgrade` внутри entrypoint).
Как проверяются: смотрим логи `docker compose logs nextcloud | grep -i upgrade`. Ручная проверка через `docker exec nextcloud php occ status`.
Риск: миграция может занять несколько минут — в это время Nextcloud показывает режим обслуживания (maintenance mode).

## Dependencies and timeouts

| Dependency | Timeout | Retry |
|---|---|---|
| PostgreSQL | 30 сек (Nextcloud ждёт в entrypoint) | 10 попыток с паузой 3 сек |
| SMTP (почта) | Не настроен явно (default PHP ~30 сек) | Нет retry |
| S3 (backup) | 5 мин (timeout в скрипте aws s3 sync) | Нет retry, ошибка в cron mail |
| Let's Encrypt | Нет (certbot блокирующий) | Нет |

## Logs/metrics

Логи Nextcloud: в stdout контейнера → `docker compose logs nextcloud`. Формат: обычный текст, нет JSON, нет request_id.
Логи Nginx: `/var/log/nginx/access.log` (combined format), нет correlation ID.
Метрики: нет. Только внешний uptime-мониторинг (UptimeRobot).
Проблема: при инциденте сложно сопоставить запрос пользователя с ошибкой в логе.

## Top risks

| Риск | Что сделать |
|---|---|
| Диск заполнился (файлы пользователей) | Мониторинг `df -h` через cron + алерт на email при >80% |
| PostgreSQL volume потерян | Проверять backup restore раз в месяц (сейчас не делается) |
| Certbot не обновил сертификат | Добавить проверку срока сертификата в мониторинг |
| Nextcloud в maintenance mode завис | Вручную: `docker exec nextcloud php occ maintenance:mode --off` |
| Сервер недоступен — нет replicas | Единственный VPS. Failover отсутствует. |

## Improvements

### 1 день
- Добавить `/status.php` в monitoring как healthcheck
- Добавить алерт на заполнение диска >80%
- Закрепить версию образа Nextcloud (сейчас `latest` — это риск)

### 1 неделя
- Настроить структурированные логи (Nextcloud поддерживает JSON-логи через `log_type => json`)
- Проверить restore из backup (создать runbook)
- Добавить `.env.example` в репозиторий

### 1 месяц
- Вынести PostgreSQL на managed DB (Supabase, RDS) или настроить streaming replication
- Настроить offsite backup с проверкой через pg_restore в CI
- Добавить Prometheus + Grafana для метрик (disk, memory, response time)
```

## Operability score — Nextcloud пример

| Критерий | Оценка | Комментарий |
|---|---|---|
| Запускается одной командой | 2 | `docker compose up -d` — работает |
| README с env-переменными | 1 | `.env.example` есть, но устарел |
| Healthcheck / readiness | 1 | Внешний мониторинг есть, встроенного endpoint нет |
| Graceful shutdown | 1 | `docker compose stop` работает, но timeout не настроен |
| Миграции автоматизированы | 2 | Запускаются в entrypoint автоматически |
| Backup и restore проверены | 0 | Backup настроен, но restore ни разу не проверялся |
| Логи структурированы | 0 | Текстовые логи без request_id |
| Timeout/retry для зависимостей | 1 | PostgreSQL ждёт, SMTP и S3 — нет |
| Rollback plan задокументирован | 1 | Есть описание, нет runbook |
| Stateful-части описаны | 2 | Все volume и mount-points документированы |

**Итого: 11/20**

Оценка: **базовая операционная зрелость** (9–14). Сервис работает и бэкапится, но есть критический пробел: restore из backup не проверялся — это означает, что при реальном инциденте восстановление может не сработать.

---

## 11.3 Operability score

Каждый пункт: `0 = нет`, `1 = частично`, `2 = есть`.

```text
[ ] Запускается одной командой           /2
[ ] README с env-переменными             /2
[ ] Healthcheck / readiness              /2
[ ] Graceful shutdown                    /2
[ ] Миграции автоматизированы            /2
[ ] Backup и restore проверены           /2
[ ] Логи структурированы                 /2
[ ] Timeout/retry для зависимостей       /2
[ ] Rollback plan задокументирован       /2
[ ] Stateful-части описаны               /2

Итого: __/20
```

Оценка:

| Баллы | Значение |
|---|---|
| 0–8 | работает у автора, но не готово к продакшену |
| 9–14 | базовая операционная зрелость |
| 15–20 | сервис можно передавать команде |

---

## 11.4 Self-audit

Ответь:

- могу ли я объяснить, где в проекте состояние;
- знаю ли, как восстановить данные;
- есть ли healthcheck;
- есть ли plan rollback;
- знаю ли, как сервис завершает работу;
- есть ли timeout у внешних вызовов;
- могу ли я по логам найти запрос;
- готов ли новый человек поддерживать проект по README.

Если большая часть ответов "нет", это не провал. Это технический backlog.