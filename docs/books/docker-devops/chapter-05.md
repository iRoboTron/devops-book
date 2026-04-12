# Глава 5: Сети Docker

> **Запомни:** Контейнеры по умолчанию изолированы. Custom bridge-сеть позволяет им общаться по имени. И это критически важно для multi-container приложений.

---

## 5.1 Проблема: контейнеры не видят друг друга

Ты запустил два контейнера:

```bash
docker run -d --name app myapp
docker run -d --name db postgres
```

**Вопрос:** Может ли `app` подключиться к `db`?

**Ответ:** Зависит от сети.

В сети **по умолчанию** (bridge):
- Контейнеры видят друг друга только по IP
- IP меняется при перезапуске
- Неудобно и ненадёжно

В **custom bridge** сети:
- Контейнеры видят друг друга **по имени**
- `app` подключается к `db:5432` — всегда работает
- Docker сам разрешает имена

---

## 5.2 Типы сетей Docker

```
┌─────────────────────────────────┐
│          Хост                   │
│                                 │
│  bridge (по умолчанию)          │
│    └── NAT выход в интернет     │
│    └── Контейнеры по IP         │
│                                 │
│  host                           │
│    └── Контейнер = сеть хоста   │
│    └── Нет изоляции             │
│                                 │
│  none                           │
│    └── Без сети вообще          │
│                                 │
│  custom bridge (рекомендуется)  │
│    └── Контейнеры по имени      │
│    └── Изолирована от других    │
└─────────────────────────────────┘
```

### bridge (по умолчанию)

```bash
docker run -d --name app myapp
```

Без указания сети — попадает в `bridge`.

| Плюс | Минус |
|------|-------|
| Работает сразу | Контейнеры видят друг друга только по IP |
| NAT выход в интернет | IP меняется при рестарте |

### host

```bash
docker run -d --network host myapp
```

Контейнер использует сеть хоста напрямую.

| Плюс | Минус |
|------|-------|
| Нет overhead | Нет изоляции |
| Порты не нужно пробрасывать | Конфликты портов |
| | Не работает на Mac/Windows (Docker Desktop) |

### none

```bash
docker run -d --network none myapp
```

Без сети вообще. Только loopback (127.0.0.1).

| Когда использовать |
|-------------------|
| Контейнеру не нужен интернет |
| Максимальная изоляция |

### custom bridge (рекомендуется)

```bash
docker network create mynet
docker run -d --network mynet --name app myapp
docker run -d --network mynet --name db postgres
```

| Плюс | Минус |
|------|-------|
| Контейнеры видят друг друга **по имени** | Нужно создать сеть |
| DNS разрешает имена → IP | |
| Изоляция от других контейнеров | |
| IP стабильный | |

> **Запомни:** Всегда создавай custom bridge для multi-container приложений.
> Default bridge — только для тестов одного контейнера.

---

## 5.3 Создание и использование custom bridge

### Создать сеть

```bash
docker network create backend
```

### Посмотреть сети

```bash
docker network ls
NETWORK ID     NAME      DRIVER
abc123         bridge    bridge
def456         host      host
ghi789         backend   bridge    ← наша сеть
```

### Запустить контейнеры в сети

```bash
docker run -d --network backend --name db \
  -e POSTGRES_PASSWORD=secret \
  postgres

docker run -d --network backend --name app \
  myapp
```

### Подключиться по имени

Из контейнера `app`:

```python
import psycopg2
conn = psycopg2.connect(
    host="db",        # ← имя контейнера!
    port=5432,
    user="postgres",
    password="secret"
)
```

Не нужно знать IP. Docker сам разрешает `db` → IP контейнера.

> **Запомни:** В custom сети имя контейнера = hostname.
> Это работает потому что Docker запускает встроен DNS-сервер.

---

## 5.4 Подключить/отключить контейнер к сети

### Подключить работающий контейнер

```bash
docker network connect backend app
```

### Отключить

```bash
docker network disconnect backend app
```

### Посмотреть кто в сети

```bash
docker network inspect backend
```

```json
{
    "Name": "backend",
    "Containers": {
        "abc123...": {
            "Name": "app",
            "IPv4Address": "172.18.0.2/16"
        },
        "def456...": {
            "Name": "db",
            "IPv4Address": "172.18.0.3/16"
        }
    }
}
```

---

## 5.5 Схема сетей в типичном стеке

```
Интернет
    │
    ▼
┌───────────────┐
│    nginx      │  port 443 открыт наружу (-p 443:443)
│  (frontend)   │
└───┬───────┬───┘
    │       │
    │ frontend    │ backend
    │ сеть        │ сеть
    ▼             ▼
┌───────┐   ┌──────────┐    ┌──────────┐
│ nginx │   │ python   │    │ postgres │
│       │   │ app      │    │ db       │
└───────┘   └──────────┘    └──────────┘
```

| Сервис | frontend | backend | Вид снаружи |
|--------|----------|---------|-------------|
| Nginx | ✅ | ✅ | ✅ (порт 443) |
| Python app | ❌ | ✅ | ❌ |
| PostgreSQL | ❌ | ✅ | ❌ |

Nginx в обеих сетях → может общаться и с интернетом и с backend.
Python и DB только в backend → не видны из интернета.

> **Запомни:** Это называется "сегментация сетей".
> База данных не должна быть доступна из интернета. Никогда.

---

## 5.6 Docker и ufw — важный нюанс

**Docker обходит ufw через iptables.**

```bash
# ufw показывает что порт закрыт
sudo ufw status
22/tcp     ALLOW
80/tcp     ALLOW
443/tcp    ALLOW

# Но Docker открыл порт базы данных!
ss -tlnp | grep 5432
LISTEN  0  128  0.0.0.0:5432
```

### Почему

Docker управляет iptables напрямую. ufw — надстройка над iptables.
Docker правила добавляются "ниже" правил ufw.

### Решение

**Не пробрасывай порты сервисов которые не должны быть снаружи.**

```yaml
# Плохо — PostgreSQL доступен из интернета!
services:
  db:
    image: postgres
    ports:
      - "5432:5432"    ← НЕ ДЕЛАЙ ТАК

# Хорошо — только внутри Docker-сети
services:
  db:
    image: postgres
    # ports: нет!    ← правильно
    networks:
      - backend
```

> **Запомни:** `ports:` в docker-compose = проброс на хост = доступно снаружи.
> Для внутренних сервисов (БД, Redis) — не пробрасывай порты.

---

## 📝 Упражнения

### Упражнение 5.1: Создать custom сеть
**Задача:**
1. Создай сеть: `docker network create mynet`
2. Проверь: `docker network ls`
3. Запусти два контейнера в сети:
   ```bash
   docker run -d --network mynet --name web1 nginx
   docker run -d --network mynet --name web2 nginx
   ```

### Упражнение 5.2: Проверить связь
**Задача:**
1. Зайди в web1: `docker exec -it web1 bash`
2. Пингуй web2: `ping web2`
3. Какой IP у web2?
4. Попробуй: `curl http://web2`
5. Выйди из контейнера

### Упражнение 5.3: Сравнить с default bridge
**Задача:**
1. Запусти контейнер БЕЗ custom сети: `docker run -d --name isolated nginx`
2. Зайди в web1: `docker exec -it web1 bash`
3. Попробуй пинговать: `ping isolated`
4. Работает? (не должно в custom сети)
5. Удали: `docker rm -f isolated web1 web2`

### Упражнение 5.4: Подключить/отключить
**Задача:**
1. Запусти: `docker run -d --name app myapp` (без сети)
2. Подключи к mynet: `docker network connect mynet app`
3. Проверь: `docker network inspect mynet` — app в списке?
4. Отключи: `docker network disconnect mynet app`
5. Проверь снова

### Упражнение 5.5: DevOps Think
**Задача:** «Ты запустил PostgreSQL с `-p 5432:5432`. ufw показывает что порт 5432 закрыт. Безопасно ли это?»

Ответ:
- НЕТ! Docker обходит ufw через iptables
- Порт 5432 доступен из интернета несмотря на ufw
- Любой может попробовать подключиться к базе
- Решение: убери `-p 5432:5432`
- База должна быть доступна только из Docker-сети (через имя сервиса)
- Если нужен доступ с хоста — только для отладки, и только `-p 127.0.0.1:5432:5432`

---

## 📋 Чеклист главы 5

- [ ] Я понимаю почему контейнеры не видят друг друга по умолчанию
- [ ] Я знаю типы сетей: bridge, host, none, custom
- [ ] Я понимаю почему custom bridge лучше default bridge (DNS по имени)
- [ ] Я могу создать сеть (`docker network create`)
- [ ] Я могу запустить контейнер в сети (`--network`)
- [ ] Я могу подключить/отключить контейнер от сети
- [ ] Я понимаю сегментацию сетей (frontend/backend)
- [ ] Я понимаю что Docker обходит ufw
- [ ] Я знаю что `ports:` открывает порт наружу (опасно для БД)

**Всё отметил?** Переходи к Главе 6 — docker-compose.
