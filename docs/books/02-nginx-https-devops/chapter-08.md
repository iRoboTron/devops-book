# Глава 8: Caddy — твой реальный сервер

> **Запомни:** Ты только что вручную настроил SSL, редиректы и заголовки безопасности через Nginx. Именно поэтому сейчас самый правильный момент познакомиться с Caddy.

---

## 8.1 Почему Caddy существует

Вспомни что ты делал в предыдущих главах:

- Установил certbot, запустил challenge, получил сертификат
- Написал в конфиге `return 301 https://$host$request_uri`
- Добавил `add_header Strict-Transport-Security ...`
- Настроил `certbot.timer` для автопродления

Это несколько часов работы и несколько файлов конфига.

Caddy делает всё это **автоматически**. Посмотри:

```
Nginx (вручную):                     Caddy (автоматически):
─────────────────────────────────    ──────────────────────
certbot --nginx -d domain.ru         (получает сертификат сам)
return 301 https://$host$request_uri (редирект HTTP→HTTPS сам)
add_header Strict-Transport-Security (заголовки безопасности сам)
ssl_certificate /etc/letsencrypt/... (обновляет сертификат сам)
certbot.timer                        (таймер не нужен)
```

Теперь ты понимаешь **что** именно Caddy делает за тебя — и **почему** это работает. Не магия, а автоматизация того, что ты делал руками.

---

## 8.2 Caddyfile — синтаксис

Главный файл конфигурации Caddy — **Caddyfile**.

Синтаксис принципиально другой, чем у Nginx:

```caddy
domain.ru {
    reverse_proxy localhost:8000
}
```

Это полноценный конфиг для HTTPS reverse proxy. Три строки вместо тридцати.

### Что происходит автоматически

Когда Caddy видит `domain.ru { ... }`:

```
1. Проверяет DNS: domain.ru → IP сервера?
2. Запрашивает сертификат Let's Encrypt через ACME
3. Настраивает HTTPS на порту 443
4. Добавляет редирект HTTP (80) → HTTPS (443)
5. Обновляет сертификат до истечения (за 30 дней)
```

> **Запомни:** Для этого нужен открытый порт 80 — Caddy делает ACME challenge так же как certbot. Если порт 80 закрыт в ufw, сертификат не получится.

---

## 8.3 Реальный Caddyfile

Посмотрим на настоящий Caddyfile с реального сервера:

```caddy
{
    servers {
        protocols h1 h2 h3
        trusted_proxies static 192.168.13.1
    }
}

nc.npcbasto.ru {
    reverse_proxy 127.0.0.1:11000
}

static.npcbasto.ru {
    root * /srv/static
    file_server
}

old.npcbasto.ru {
    redir https://nc.npcbasto.ru{uri} permanent
}
```

Разберём каждую часть:

### Глобальный блок `{ ... }`

```caddy
{
    servers {
        protocols h1 h2 h3
        trusted_proxies static 192.168.13.1
    }
}
```

- `protocols h1 h2 h3` — поддерживать HTTP/1.1, HTTP/2 и HTTP/3 (QUIC)
- `trusted_proxies static 192.168.13.1` — доверять заголовкам `X-Forwarded-For` от этого IP. Нужно если перед Caddy стоит роутер или другой прокси — иначе приложение не увидит реальный IP клиента.

### Блок сайта

```caddy
nc.npcbasto.ru {
    reverse_proxy 127.0.0.1:11000
}
```

- `nc.npcbasto.ru` — имя домена. Caddy автоматически получит на него сертификат.
- `reverse_proxy 127.0.0.1:11000` — проброс на локальный порт 11000.

### Статический файловый сервер

```caddy
static.npcbasto.ru {
    root * /srv/static
    file_server
}
```

- `root * /srv/static` — корневая директория для всех путей (`*`)
- `file_server` — раздавать файлы из этой директории

Эквивалент Nginx:
```nginx
server {
    listen 443 ssl;
    server_name static.npcbasto.ru;
    root /srv/static;
    location / { try_files $uri $uri/ =404; }
    # + ssl_certificate, ssl_certificate_key, certbot...
}
```

### Редирект

```caddy
old.npcbasto.ru {
    redir https://nc.npcbasto.ru{uri} permanent
}
```

- `redir` — перенаправить запрос
- `{uri}` — плейсхолдер: путь и query string из исходного запроса
- `permanent` — код 301 (постоянный редирект)

---

## 8.4 Caddy в Docker

На реальных серверах Caddy часто запускают в Docker. Так проще обновлять и изолировать.

### docker-compose.yml

```yaml
services:
  caddy:
    image: caddy:2.10-alpine
    restart: always
    container_name: my-edge-proxy
    network_mode: host          # сидит прямо на сетевом стеке хоста
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro   # конфиг только для чтения
      - ./data:/data                           # сертификаты здесь
      - ./config:/config                       # кеш конфигурации
      - ./site:/srv                            # статические файлы
```

### Почему `network_mode: host`

```
Без host:                    С host:
────────────────────         ────────────────
[Caddy контейнер]            [Caddy контейнер]
  :80 → хост :80               напрямую :80, :443
  :443 → хост :443
[Хост]                       [Хост]
  :80 пробрасывает             (один стек)
  :443 пробрасывает
```

С `network_mode: host` контейнер использует сетевой стек хоста напрямую — порты 80 и 443 открываются без лишних прослоек. Это важно: при проброске портов (`ports: "80:80"`) Docker обходит ufw через iptables, что может создать неожиданные дыры в безопасности.

> **Совет:** `network_mode: host` работает только на Linux. На Mac и Windows используй `ports:`.

### Где хранятся сертификаты

```
./data/
└── caddy/
    └── certificates/
        └── acme-v02.api.letsencrypt.org-directory/
            └── domain.ru/
                ├── domain.ru.crt
                └── domain.ru.key
```

Том `./data` должен **всегда** быть примонтирован. Если удалить — Caddy запросит новые сертификаты. Let's Encrypt имеет лимиты: 5 сертификатов на домен в неделю.

> **Опасно:** Никогда не делай `docker-compose down -v` для Caddy без бэкапа тома `data`. Потеряешь сертификаты — придётся ждать недели до сброса лимита.

---

## 8.5 Управление Caddy

### Применить изменения без остановки

```bash
# Проверить конфиг (аналог nginx -t)
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile

# Применить новый конфиг без даунтайма
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

> **Порядок важен:** Сначала `validate`, потом `reload`. Сломанный Caddyfile после reload не применяется (Caddy откатывается), но лучше проверять заранее.

### Логи

```bash
# Все логи Caddy (включая получение сертификата)
docker compose logs caddy

# Следить в реальном времени
docker compose logs -f caddy

# Искать ошибки сертификата
docker compose logs caddy | grep -i "tls\|cert\|acme"
```

### Добавить новый сайт

1. Открой Caddyfile:
   ```bash
   nano ./Caddyfile
   ```
2. Добавь блок:
   ```caddy
   newsite.domain.ru {
       reverse_proxy localhost:3000
   }
   ```
3. Проверь и применить:
   ```bash
   docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
   docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
   ```

Caddy автоматически получит сертификат для нового домена.

---

## 8.6 Диагностика Caddy

### Сертификат не получается

```bash
docker compose logs caddy | grep -i "error\|failed"
```

Типичные причины — те же что у certbot:

| Проблема | Симптом в логах | Решение |
|----------|----------------|---------|
| DNS не настроен | `no such host` | Проверь A-запись: `dig domain.ru +short` |
| Порт 80 закрыт | `connection refused` | `sudo ufw allow 80` |
| Превышен лимит Let's Encrypt | `too many certificates` | Подожди неделю или используй staging |

### 502 Bad Gateway

```bash
# Посмотреть что отвечает бэкенд
docker compose exec caddy curl -v http://localhost:8000

# Проверить что приложение запущено
ss -tlnp | grep 8000
```

### Caddyfile не применяется

```bash
# validate покажет строку с ошибкой
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
```

---

## 8.7 Nginx vs Caddy: сравнительная таблица

| | Nginx | Caddy |
|---|---|---|
| SSL | certbot отдельно | автоматически |
| Конфиг reverse proxy | 30+ строк | 3 строки |
| Синтаксис | директивы + блоки `{}` | `домен { }` |
| Проверка конфига | `nginx -t` | `caddy validate` |
| Применить изменения | `systemctl reload nginx` | `caddy reload` |
| Логи | `/var/log/nginx/` | `docker logs` |
| HTTP/3 (QUIC) | нужен отдельный модуль | из коробки |
| Сложная логика | гибко | ограниченно |
| Когда выбрать | тонкая настройка, сложные правила location | типичный reverse proxy, быстрый старт |

> **Запомни:** Caddy не лучше Nginx. Caddy быстрее настраивается для типичных задач. Nginx даёт больше контроля для нетипичных. Теперь ты умеешь оба.

---

## 8.8 Упражнения

### Упражнение 1: Первый запуск Caddy

1. Создай директорию:
   ```bash
   mkdir -p ~/caddy-test && cd ~/caddy-test
   ```
2. Создай `docker-compose.yml` с Caddy
3. Создай `Caddyfile` с `reverse_proxy` на `localhost:8000`
4. Запусти Python-приложение из Главы 8 на порту 8000
5. Подними Caddy: `docker compose up -d`
6. Проверь логи: `docker compose logs caddy`

### Упражнение 2: Добавь второй домен

1. Добавь в `/etc/hosts`:
   ```
   127.0.0.1 app1.local
   127.0.0.1 app2.local
   ```
2. Добавь два блока в Caddyfile (оба на один порт)
3. Сделай `caddy reload`
4. Проверь что оба домена работают

> **Для локальной разработки без домена:** используй `localhost` вместо домена. Caddy не будет запрашивать сертификат и будет работать по HTTP.

### Упражнение 3: Сломай и почини

1. Намеренно введи ошибку в Caddyfile (например, пропусти закрывающую `}`)
2. Запусти `caddy validate` — прочитай сообщение об ошибке
3. Исправь, проверь, примени

---

> **Поздравляю:** Ты прошёл путь от "что такое порт 80" до настройки двух разных прокси-серверов.
> Nginx научил тебя что происходит под капотом. Caddy показал как это работает в продакшне.
