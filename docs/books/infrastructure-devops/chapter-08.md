# Глава 8: Управление ресурсами и стабильность сервера

> **Запомни:** Сервер не ложится внезапно. Диск постепенно заполняется, память постепенно утекает. Настрой мониторинг и автоочистку — и сервер будет жить сам.

---

## 8.1 Диск: не дать заполниться

### Проверка

```bash
df -h
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   12G   36G  25% /
```

| Use% | Действие |
|------|----------|
| < 50% | Всё ок |
| 50-70% | Мониторить |
| 70-85% | Чистить |
| > 85% | КРИТИЧНО |

### Что занимает место

```bash
# Топ самых больших директорий
sudo du -sh /* 2>/dev/null | sort -rh | head -5

# Сколько занимает Docker
sudo du -sh /var/lib/docker

# Сколько логи
sudo du -sh /var/log
```

### Docker мусор

```bash
docker system df
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          15        3         2.1GB     1.8GB (85%)
Containers      8         2         0B        0B
Local Volumes   4         2         500MB     200MB (40%)
Build Cache     12        0         800MB     800MB (100%)
```

### Очистка

```bash
# Удалить неиспользуемое (без томов)
docker system prune -f

# Удалить всё включая образы без тега
docker system prune -a -f

# Только кэш сборки
docker builder prune -f
```

### Автоматическая очистка через cron

```bash
# /etc/cron.d/docker-prune
# Еженедельно в 4:00
0 4 * * 0 root docker system prune -f >> /var/log/docker-prune.log 2>&1
```

> **Совет:** Раз в неделю — достаточно.
> Каждый день — слишком агрессивно.

---

## 8.2 Ротация логов Docker

По умолчанию логи контейнеров растут бесконечно.

### Настройка

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
```

| Параметр | Значение |
|----------|----------|
| `max-size` | Максимальный размер одного файла лога |
| `max-file` | Сколько файлов хранить (ротация) |

Итого: максимум `10MB × 3 = 30MB` на контейнер.

### Применить

```bash
sudo systemctl restart docker
```

> **Опасно:** Рестарт Docker = рестарт всех контейнеров.
> Делай в удобное время.

---

## 8.3 Память

### Проверка

```bash
free -h
              total   used   free   available
Mem:          3.9Gi  3.2Gi  0.2Gi  0.4Gi
Swap:         2.0Gi  0.5Gi  1.5Gi  1.5Gi
```

`available` < 500MB = давление памяти.

### Потребление контейнерами

```bash
docker stats --no-stream
CONTAINER   CPU %    MEM USAGE / LIMIT     MEM %
myapp-app   2.5%     450MiB / 512MiB       87.9%
myapp-db    5.1%     340MiB / 1GiB         33.3%
```

### Лимиты памяти в docker-compose

```yaml
services:
  app:
    image: ghcr.io/user/myapp:latest
    deploy:
      resources:
        limits:
          memory: 512m
          cpus: '0.5'
        reservations:
          memory: 256m
    db:
      image: postgres:16
      deploy:
        resources:
          limits:
            memory: 1g
            cpus: '1.0'
```

| Параметр | Значение |
|----------|----------|
| `limits.memory` | Максимум памяти (OOM kill если превысит) |
| `limits.cpus` | Максимум CPU |
| `reservations.memory` | Гарантированный минимум |

> **Совет:** Всегда ставь лимиты.
> Без лимитов один контейнер может съесть всю память.

### Swap

```bash
# Проверить
free -h | grep Swap

# Если нет — создать
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 8.4 Мониторинг ресурсов

### `htop` — процессы

```bash
sudo apt install -y htop
htop
```

Показывает CPU, RAM, процессы в реальном времени.

### `iotop` — диск

```bash
sudo apt install -y iotop
sudo iotop
```

Показывает кто пишет/читает диск.

### `nethogs` — сеть

```bash
sudo apt install -y nethogs
sudo nethogs
```

Показывает кто использует сеть.

---

## 8.5 Автоперезапуск

### `restart: unless-stopped`

```yaml
services:
  app:
    restart: unless-stopped
  db:
    restart: unless-stopped
  nginx:
    restart: unless-stopped
```

| Политика | Когда перезапускает |
|----------|-------------------|
| `no` | Никогда |
| `always` | Всегда |
| `unless-stopped` | Всегда, кроме ручной остановки |
| `on-failure` | Только при ошибке |

### Healthcheck

```yaml
services:
  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myapp"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
```

### Restart loop — что делать

Контейнер постоянно перезапускается:

```bash
# Посмотреть логи
docker compose logs --tail=50 app

# Посмотреть статус
docker inspect myapp-app | grep -A 10 "State"

# Проверить healthcheck
docker inspect --format='{{.State.Health.Status}}' myapp-app
```

---

## 8.6 Итоговый чеклист надёжности

Пройдись перед тем как сказать "сервер готов":

```
□ Бэкапы настроены и проверены
□ Бэкапы отправляются в облако
□ Восстановление проверено на тестовой машине
□ Логи ротируются (Docker + система)
□ Docker мусор чистится автоматически (cron)
□ Лимиты памяти выставлены для контейнеров
□ restart: unless-stopped для всех сервисов
□ healthcheck для базы данных
□ .env с правами 600
□ PostgreSQL не доступна снаружи
□ Swap настроен
□ Алерт если диск > 80% (можно через простой скрипт)
□ Nginx заголовки безопасности добавлены
□ Rate limiting настроен
```

---

## 📝 Упражнения

### Упражнение 8.1: Очистка Docker
**Задача:**
1. Проверь мусор: `docker system df`
2. Почисти: `docker system prune -f`
3. Сколько освободилось?

### Упражнение 8.2: Ротация логов Docker
**Задача:**
1. Создай `/etc/docker/daemon.json` (как в 8.2)
2. Перезапусти Docker: `sudo systemctl restart docker`
3. Проверь: `docker inspect --format='{{.HostConfig.LogConfig}}' myapp-app`

### Упражнение 8.3: Лимиты памяти
**Задача:**
1. Добавь `deploy.resources.limits` в docker-compose.yml
2. Пересоздай: `docker compose up -d`
3. Проверь: `docker stats --no-stream`

### Упражнение 8.4: Автоочистка cron
**Задача:**
1. Создай `/etc/cron.d/docker-prune`
2. Проверь: `cat /etc/cron.d/docker-prune`

### Упражнение 8.5: DevOps Think
**Задача:** «Диск заполнился на 95%. Сервер еле работает. Что чистишь первым?»

Ответ:
1. Docker мусор: `docker system prune -a -f` (самое быстрое)
2. Старые логи: `find /var/log -name "*.gz" -mtime +30 -delete`
3. Старые бэкапы: проверить ротацию в backup.sh
4. Временные файлы: `rm -rf /tmp/*`
5. Потом настроить автоочистку чтобы не повторилось

---

## 📋 Чеклист главы 8

- [ ] Я мониторю диск (`df -h`)
- [ ] Я знаю что занимает место (`du -sh`)
- [ ] Docker мусор чистится автоматически (cron)
- [ ] Логи Docker ротируются (daemon.json)
- [ ] Лимиты памяти выставлены для контейнеров
- [ ] Swap настроен
- [ ] `restart: unless-stopped` для всех сервисов
- [ ] healthcheck для базы данных
- [ ] Я знаю как диагностировать restart loop

**Всё отметил?** Переходи к Главе 9 — итоговый проект.
