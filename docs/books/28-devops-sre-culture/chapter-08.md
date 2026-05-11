# Глава 8: Runbook, playbook и operational readiness

> **Цель:** понять документацию как часть эксплуатации, а не как бумажную работу.

---

## 8.1 Runbook

Runbook — инструкция, что делать при проблеме.

Пример структуры:

```markdown
# Сервис не открывается

## Симптом
Пользователь видит 502 или timeout.

## Быстрая проверка
curl -I https://example.com
systemctl status nginx
docker ps

## Шаги диагностики
1. Проверить Nginx.
2. Проверить контейнер app.
3. Проверить логи app.
4. Проверить БД.
5. Проверить диск.

## Частые причины
- app не запущен;
- неверный upstream;
- нет env;
- БД недоступна;
- диск заполнен.
```

---

---

## 8.1a Runbook: база данных не запускается

```markdown
# База данных не запускается

## Симптом
Приложение пишет "connection refused" или "database is locked".
`docker ps` не показывает контейнер с БД, или показывает статус "Exited".

## Быстрая проверка
```bash
docker ps -a | grep postgres        # проверить статус контейнера
docker logs postgres --tail 50      # последние ошибки
df -h                               # проверить свободное место на диске
du -sh /var/lib/docker/volumes/     # размер Docker volumes
```

## Шаги диагностики

1. Проверить статус контейнера:
   ```bash
   docker inspect postgres | grep -A5 '"State"'
   ```
   Если `"ExitCode": 1` — смотреть логи дальше.

2. Читать логи с самого начала (там обычно причина):
   ```bash
   docker logs postgres 2>&1 | head -100
   ```
   Искать: `FATAL`, `ERROR`, `Permission denied`, `No space left on device`.

3. Проверить место на диске:
   ```bash
   df -h /
   # Если < 10% свободно — это причина
   docker system df               # что занимает место в Docker
   docker image prune -f          # удалить неиспользуемые образы
   ```

4. Проверить права на volume:
   ```bash
   ls -la /var/lib/docker/volumes/postgres_data/_data/
   # Владелец должен совпадать с UID внутри контейнера (обычно 999 для postgres)
   sudo chown -R 999:999 /var/lib/docker/volumes/postgres_data/_data/
   ```

5. Попробовать запустить снова:
   ```bash
   docker start postgres
   docker logs postgres --tail 20
   ```

## Частые причины

| Причина | Признак в логах | Решение |
|---|---|---|
| Диск заполнен | `No space left on device` | `docker image prune`, очистить логи |
| Неверные права на volume | `Permission denied` | `chown -R 999:999 <volume_path>` |
| Неправильный пароль в env | `password authentication failed` | Проверить `.env`, пересоздать контейнер |
| Повреждённые данные после hard kill | `unexpected EOF` в WAL | Восстановить из бэкапа |
| Занят порт 5432 | `address already in use` | `ss -tlnp \| grep 5432`, убить процесс |

## Как откатиться

Если база повреждена и не поднимается — восстановить из бэкапа:

```bash
# Остановить всё что использует БД
docker stop app

# Убрать повреждённый volume
docker volume rm postgres_data

# Создать новый volume и восстановить дамп
docker volume create postgres_data
docker run --rm -v postgres_data:/var/lib/postgresql/data \
  -v /backups:/backups postgres:15 \
  bash -c "pg_restore -U postgres -d mydb /backups/latest.dump"

# Запустить снова
docker compose up -d
```

## Когда эскалировать

- Бэкап повреждён или отсутствует → немедленно, потеря данных.
- Ошибки в WAL (`PANIC`, `recovery`) без понятной причины → лучше не трогать, обратиться к DBA.
- Диск заполнен, нельзя ничего удалить → нужен доступ к системе хранения.
```

---

## 8.1b Runbook: CI/CD pipeline упал

```markdown
# CI/CD pipeline упал

## Симптом
GitHub Actions показывает красный крест на коммите.
Деплой не произошёл, хотя пуш был сделан.
В Slack/email пришло уведомление о fallen workflow.

## Быстрая проверка
```bash
# Посмотреть последний коммит
git log --oneline -3

# Проверить статус через GitHub CLI (если установлен)
gh run list --limit 5
gh run view <run-id> --log-failed
```

В GitHub UI: вкладка Actions → найти упавший run → раскрыть упавший шаг → читать лог.

## Шаги диагностики

1. Определить на каком шаге упало (build / test / deploy):
   ```
   GitHub → Actions → последний run → смотреть красный шаг
   ```

2. Если упало на **build/test** — проблема в коде:
   ```bash
   # Воспроизвести локально
   npm test           # или pytest, cargo test и т.д.
   # Найти ошибку, исправить, запушить
   ```

3. Если упало на **deploy** (SSH, rsync, docker push) — проблема в окружении:
   ```bash
   # Проверить доступность сервера
   ssh deploy@your-server "echo ok"

   # Проверить секреты в GitHub
   # GitHub → Settings → Secrets and variables → Actions
   # Убедиться что SSH_KEY, HOST, PORT заданы и не истекли
   ```

4. Если ошибка `rate limit` или `timeout` — повторить вручную:
   ```bash
   gh run rerun <run-id>
   # или через UI: кнопка "Re-run all jobs"
   ```

5. Проверить изменения в последнем коммите — возможно сломан конфиг CI:
   ```bash
   git show HEAD -- .github/workflows/
   # Проверить синтаксис YAML
   ```

## Частые причины

| Причина | Где видно | Решение |
|---|---|---|
| Тест упал из-за нового кода | Шаг `test`, сообщение об assertion | Исправить тест или баг, запушить |
| Истёк или сломан секрет (SSH_KEY, токен) | Шаг deploy: `Permission denied` | Перегенерировать, обновить в Settings → Secrets |
| Сервер недоступен | Шаг deploy: `Connection timed out` | Проверить VPS, перезапустить |
| Сломан YAML-синтаксис workflow | Первый же шаг, ошибка парсинга | Проверить `.github/workflows/*.yml` |
| Превышен лимит GitHub Actions | `You've used 100% of included minutes` | Подождать сброса лимита или перейти на платный план |
| Docker Hub rate limit | `toomanyrequests` при `docker pull` | Добавить аутентификацию в workflow |

## Как откатиться

Если нужно срочно задеплоить предыдущую версию, не ждя CI:

```bash
# Найти последний рабочий коммит
git log --oneline -10

# Задеплоить вручную (без CI)
ssh deploy@your-server
cd /opt/app
git fetch origin
git checkout <good-commit-hash>
sudo systemctl restart app
# Проверить
curl -I https://your-site.com
```

Или через revert:
```bash
git revert HEAD          # создать коммит-откат
git push origin main     # CI запустится с откатным коммитом
```

## Когда эскалировать

- Упало в prod и там данные пользователей → откатить вручную немедленно, потом разбираться.
- Секрет скомпрометирован (попал в лог) → немедленно отозвать токен/ключ, затем расследовать.
- GitHub сам упал (status.github.com) → ждать, деплоить вручную если критично.
```

---

## 8.2 Playbook

Playbook — процедура для типового действия. Например, "как обновить сервис".

Runbook отвечает на аварию. Playbook помогает делать повторяемое действие без ошибки.

---

## 8.3 Checklist

Checklist короче. Он не объясняет всю теорию, а помогает не забыть шаги.

Пример перед деплоем:

- [ ] backup свежий;
- [ ] миграции проверены;
- [ ] healthcheck есть;
- [ ] rollback понятен;
- [ ] smoke-test готов.

---

## 8.4 Operational readiness

Operational readiness — готов ли сервис жить в проде.

Минимум:

| Проверка | Есть? |
|---|---|
| healthcheck | |
| логи | |
| backup | |
| rollback | |
| владелец | |
| зависимости описаны | |
| порты известны | |
| runbook есть | |

---

## 8.5 Практика

Напиши runbook "сервис не открывается" для своего проекта. В каждом шаге должна быть команда или конкретная проверка. Фраза "посмотреть, что не так" не считается шагом.