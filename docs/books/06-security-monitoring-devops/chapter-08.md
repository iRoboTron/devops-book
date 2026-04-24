# Глава 8: Аварийное восстановление — план действий

> **Запомни:** В панике думать сложно. Runbook — пошаговая инструкция которую ты написал заранее, в спокойной обстановке.

---

## 8.1 Зачем runbook до аварии

```
Без runbook:           С runbook:
────────────           ──────────
3:00 — звонок          3:00 — звонок
3:05 — паника          3:05 — открыл runbook
3:30 — думаешь         3:07 — шаг 1
4:00 — нашёл причину   3:10 — шаг 2
4:30 — чинишь          3:15 — решено
```

---

## 8.2 Сценарий 1: Приложение не отвечает

```
Шаг 1: Проверить доступность
  curl -I https://domain.ru
  curl -I http://localhost:8000/health

Шаг 2: Проверить контейнеры
  docker compose ps
  Все Up? Какие нет?

Шаг 3: Посмотреть логи
  docker compose logs --tail=50 app
  docker compose logs --tail=50 db

Шаг 4: Проверить ресурсы
  df -h        — диск не переполнен?
  free -h      — память есть?
  htop         — CPU не 100%?

Шаг 5: Попробовать перезапустить
  docker compose restart app
  curl http://localhost:8000/health  — помогло?

Шаг 6: Если не помогло — полный рестарт
  docker compose down
  docker compose up -d
  curl http://localhost:8000/health

Шаг 7: Если не помогло — rollback
  /opt/myapp/scripts/restore.sh /var/backups/myapp/latest/
```

---

## 8.3 Сценарий 2: Сервер не отвечает на SSH

```
Шаг 1: Проверить доступность
  ping server-ip
  nc -zv server-ip 22

Шаг 2: Консоль провайдера (VNC)
  Зайти через панель хостинга
  Войти в систему

Шаг 3: Что случилось
  journalctl -b     — что при загрузке
  dmesg | tail      — ошибки ядра
  df -h             — диск не переполнен?
  free -h           — память?

Шаг 4: Частые причины
  Диск переполнен:
    find / -size +100M -type f 2>/dev/null | head -10
    rm большие_файлы
    docker system prune -f

 OOM killer:
    dmesg | grep -i "out of memory"
    Увеличить RAM или swap

Шаг 5: Перезапустить сервисы
  systemctl restart sshd
  docker compose restart
```

---

## 8.4 Сценарий 3: База данных не стартует

```
Шаг 1: Логи
  docker compose logs db

Шаг 2: Типичные ошибки
  "could not write to file" → диск полный
    df -h
    Очистить место

  "address already in use" → порт занят
    ss -tlnp | grep 5432
    Убить процесс: kill PID

  "permission denied" → права
    ls -la /var/lib/docker/volumes/pgdata

Шаг 3: Пересоздать контейнер
  docker compose rm -f db
  docker compose up -d db

Шаг 4: Если не помогло — восстановление
  /opt/myapp/scripts/restore.sh /var/backups/myapp/latest/
```

---

## 8.5 Сценарий 4: Диск переполнен

```
Шаг 1: Посмотреть что занимает
  df -h
  sudo du -sh /* | sort -rh | head -5

Шаг 2: Быстрая очистка
  docker system prune -a -f
  find /var/log -name "*.gz" -mtime +30 -delete
  rm -rf /tmp/*

Шаг 3: Бэкапы
  ls -la /var/backups/myapp/
  Удалить старые: find /var/backups -mtime +7 -type d -exec rm -rf {} +

Шаг 4: Проверить
  df -h  — стало лучше?

Шаг 5: Профилактика
  Настроить автоочистку (Модуль 5, Глава 8)
```

---

## 8.6 Шаблон runbook

Создай свой:

```bash
sudo nano /opt/myapp/RUNBOOK.md
```

```markdown
# Runbook: ${PROJECT}

## Контакты
- Разработчик: имя, телефон, Telegram
- Хостинг: логин, URL панели
- Домен: регистратор, логин

## Доступы
- SSH: deploy@IP, ключ в ~/.ssh/
- Бэкапы: /var/backups/myapp/
- Telegram-бот: @myapp_monitor_bot

## Сценарий 1: Приложение упало
...

## Сценарий 2: Сервер недоступен
...

## Сценарий 3: БД не стартует
...

## Сценарий 4: Диск переполнен
...

## Сценарий 5: Подозрение на взлом
...
```

---

## 📝 Упражнения

### Упражнение 8.1: Написать runbook
**Задача:**
1. Создай `/opt/myapp/RUNBOOK.md`
2. Заполни контакты и доступы
3. Напиши 3 сценария для своего проекта
4. Распечатай или сохрани offline

### Упражнение 8.2: Проиграть сценарий
**Задача:**
1. Выбери сценарий "диск переполнен"
2. Создай большой файл: `dd if=/dev/zero of=/tmp/fill bs=1M count=1000`
3. Проверь: `df -h` — диск заполнен?
4. Иди по runbook — получилось очистить?
5. Удали: `rm /tmp/fill`

### Упражнение 8.3: DevOps Think
**Задача:** «3 ночи. Telegram-алерт: "Диск 95%, приложение упало". Ты с телефона. Что делаешь?»

Ответ:
1. Открыть runbook (сохранён offline на телефоне)
2. Сценарий "диск переполнен":
   - SSH на сервер
   - `docker system prune -a -f` (самое быстрое)
   - `df -h` — стало лучше?
   - `docker compose restart app`
   - Проверить: `curl http://localhost/health`
3. Если не помогло — сценарий "приложение упало"
4. Утром — разобраться почему диск заполнился

---

## 📋 Чеклист главы 8

- [ ] Runbook написан для минимум 3 сценариев
- [ ] Контакты и доступы записаны
- [ ] Проиграл минимум 1 сценарий вручную
- [ ] Runbook доступен offline (телефон, распечатка)

**Всё отметил?** Переходи к финальной Главе 9.
