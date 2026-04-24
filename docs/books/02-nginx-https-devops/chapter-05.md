# Глава 5: HTTPS с Let's Encrypt

> **Запомни:** Без HTTPS твои пользователи передают данные открытым текстом. Пароли, куки, личная информация — всё видно любому кто стоит посередине. Let's Encrypt даёт бесплатный HTTPS за 5 минут.

---

## 5.1 Что такое TLS/SSL и зачем он нужен

### Без TLS (HTTP)

```
Браузер ───→ "POST /login" ───→ Сервер
              "password=12345"
              
              👁️ Провайдер видит
              👁️ Админ Wi-Fi видит
              👁️ Хакер в кафе видит
```

### С TLS (HTTPS)

```
Браузер ───→ 🔒 зашифровано 🔒 ───→ Сервер
              
              👁️ Никто не видит содержимое
              👁️ Видят только: IP сервера + факт соединения
```

### Что даёт TLS

| Что | Без TLS | С TLS |
|-----|---------|-------|
| Данные запроса | Видны всем | Зашифрованы |
| Данные ответа | Видны всем | Зашифрованы |
| Куки сессии | Можно украсть | Нельзя украсть |
| Пароли | Видны | Зашифрованы |
| Подтверждение сервера | Нет | Есть (сертификат) |

### Сертификат: подтверждение личности

TLS не только шифрует. Он ещё подтверждает что ты общаешься с **тем самым** сервером.

```
Браузер: "Ты действительно myapp.ru?"

Без сертификата:
  Сервер: "Да"  ← Браузер верит на слово? Нет!

С сертификатом:
  Сервер: "Вот сертификат от Let's Encrypt"
  Браузер: "Проверяю... Да, это myapp.ru. Подпись валидная. Верю."
```

> **Запомни:** TLS делает две вещи:
> 1. **Шифрует** данные между браузером и сервером
> 2. **Подтверждает** что сервер — это тот за кого себя выдаёт

---

## 5.2 Как работает Let's Encrypt

**Let's Encrypt** — бесплатный центр сертификации (CA).

### Процесс получения

```
1. Ты: "Хочу сертификат для myapp.ru"
         ↓
2. Certbot: "Докажи что ты владелец myapp.ru"
         ↓
3. Let's Encrypt: "Положи файл по адресу http://myapp.ru/.well-known/acme-challenge/xyz"
         ↓
4. Certbot: "Вот файл"
         ↓
5. Let's Encrypt: "Проверяю... Да, файл на месте. myapp.ru = твой"
         ↓
6. Let's Encrypt: "Вот сертификат ✓"
```

Этот процесс называется **ACME challenge**.

> **Порядок важен:** Для получения сертификата порт 80 **должен быть открыт**.
> Let's Encrypt подключается к `http://myapp.ru/.well-known/...` чтобы проверить.
> Закроешь порт 80 в ufw — certbot не сработает.

### Что получает certbot

Три файла:

```
/etc/letsencrypt/live/myapp.ru/
├── cert.pem      ← Сертификат (публичный ключ)
├── privkey.pem   ← Приватный ключ (НИКОМУ НЕ ДАВАТЬ)
├── chain.pem     ← Цепочка доверия (промежуточные CA)
└── fullchain.pem ← cert.pem + chain.pem (это используем в Nginx)
```

> **Запомни:** В Nginx используешь `fullchain.pem` + `privkey.pem`.
> Не `cert.pem` — без chain.pem браузер может не доверять.

---

## 5.3 Certbot — установка и получение сертификата

### Установка

```bash
sudo apt install -y certbot python3-certbot-nginx
```

`python3-certbot-nginx` — плагин который сам правит конфиг Nginx.

### Автоматический режим (рекомендуемый)

```bash
sudo certbot --nginx -d myapp.ru -d www.myapp.ru
```

Certbot:
1. Проверит что домен доступен
2. Пройдёт ACME challenge
3. Получит сертификат
4. **Сам изменит конфиг Nginx** для HTTPS
5. Настроит редирект HTTP → HTTPS

### Интерактивный режим

```bash
sudo certbot --nginx
```

Certbot спросит:
1. Для какого домена?
2. Хочешь редирект на HTTPS? (рекомендуется)

### Только сертификат, без правки Nginx

```bash
sudo certbot certonly --nginx -d myapp.ru
```

`certonly` = только получить сертификат. Nginx не трогает.

> **Зачем:** Когда хочешь сам настроить Nginx для HTTPS.
> Или когда Nginx плагин не работает.

---

## 5.4 Что certbot меняет в конфиге Nginx

### До certbot

```nginx
server {
    listen 80;
    server_name myapp.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### После certbot

```nginx
server {
    listen 80;
    server_name myapp.ru;

    # Редирект HTTP → HTTPS
    if ($host = myapp.ru) {
        return 301 https://$host$request_uri;
    }

    return 404;
}

server {
    listen 443 ssl;
    server_name myapp.ru;

    # Сертификат
    ssl_certificate /etc/letsencrypt/live/myapp.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.ru/privkey.pem;

    # TLS настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Что изменилось

| Что | Зачем |
|-----|-------|
| Второй `server` блок на 443 | HTTPS |
| `ssl_certificate` | Публичный сертификат |
| `ssl_certificate_key` | Приватный ключ |
| `ssl_protocols TLSv1.2 TLSv1.3` | Только современные версии |
| `return 301 https://...` | Редирект HTTP → HTTPS |

> **Запомни:** Certbot создал два server блока.
> Один для HTTP (редиректит на HTTPS).
> Второй для HTTPS (обрабатывает запросы).

---

## 5.5 Автопродление сертификата

Let's Encrypt сертификаты живут **90 дней**.

Certbot устанавливает таймер который обновляет их автоматически.

### Проверить таймер

```bash
systemctl status certbot.timer
● certbot.timer - Run certbot twice daily
     Active: active (waiting)
```

### Посмотреть когда следующий запуск

```bash
systemctl list-timers certbot.timer
NEXT                         LEFT
Mon 2026-04-20 06:00:00 UTC  10 days left
```

### Проверить продление (dry-run)

```bash
sudo certbot renew --dry-run
```

`--dry-run` = проверить но не продлевать реально.

> **Совет:** Запускай `--dry-run` раз в месяц.
> Так ты узнаешь что автопродление работает.

### Что будет если не продлить

```
День 0:    Получил сертификат (живёт 90 дней)
День 80:   certbot автоматически продлевает
День 85:   Если не продлил — браузеры начинают ругаться
День 90:   Сертификат истёк — ERR_CERT_DATE_INVALID
```

> **Запомни:** Автопродление — must have.
> Не надейся на память. Настраивай сразу.

---

## 5.6 Редирект HTTP → HTTPS вручную

Если certbot не настроил редирект — сделай сам.

```nginx
server {
    listen 80;
    server_name myapp.ru;

    # Редирект ВСЕХ HTTP запросов на HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name myapp.ru;

    ssl_certificate /etc/letsencrypt/live/myapp.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Проверить редирект

```bash
curl -I http://myapp.ru
HTTP/1.1 301 Moved Permanently
Location: https://myapp.ru/
```

301 = навсегда. Браузер запомнит и будет сразу ходить на HTTPS.

---

## 5.7 Что делать если certbot не работает

### Ошибка: "Could not connect to myapp.ru"

```
Problem: The connection to myapp.ru:80 timed out
```

**Причина:** Порт 80 закрыт.

**Решение:**
```bash
sudo ufw allow 80
sudo certbot --nginx -d myapp.ru
```

### Ошибка: "DNS problem"

```
Problem: DNS problem: NXDOMAIN looking up A for myapp.ru
```

**Причина:** Домен не настроен.

**Решение:**
1. Проверь A-запись: `dig myapp.ru +short`
2. Если нет IP — настрой в панели регистратора
3. Подожди 5-15 минут (DNS кэш)
4. Попробуй снова

### Ошибка: "Challenge failed"

```
Problem: The ACME challenge failed
```

**Причина:** Nginx не отдаёт challenge файл.

**Решение:**
1. Проверь что Nginx запущен: `systemctl status nginx`
2. Проверь что server_name правильный: `grep server_name /etc/nginx/sites-enabled/`
3. Попробуй вручную: `curl http://myapp.ru/.well-known/acme-challenge/test`

---

## 5.8 Self-signed сертификат для разработки

Нет домена? Нет публичного IP? Создай самоподписанный сертификат.

> **Запомни:** Self-signed ≠ для продакшена.
> Браузер будет ругаться. Для тестов — ок.

### Создание

```bash
sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/myapp.key \
  -out /etc/ssl/certs/myapp.crt \
  -subj "/CN=myapp.local"
```

| Опция | Значение |
|-------|----------|
| `-x509` | Формат сертификата |
| `-nodes` | Без пароля на приватный ключ |
| `-days 365` | Живёт 1 год |
| `-newkey rsa:2048` | Создать новый RSA ключ |
| `-subj "/CN=myapp.local"` | Домен (Common Name) |

### Настроить Nginx

```nginx
server {
    listen 443 ssl;
    server_name myapp.local;

    ssl_certificate /etc/ssl/certs/myapp.crt;
    ssl_certificate_key /etc/ssl/private/myapp.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Проверить

```bash
curl -k https://myapp.local
```

`-k` = не проверять сертификат (потому что self-signed).

---

## 📝 Упражнения

### Упражнение 5.1: Self-signed сертификат
**Задача:**
1. Создай self-signed сертификат:
   ```bash
   sudo openssl req -x509 -nodes -days 365 \
     -newkey rsa:2048 \
     -keyout /etc/ssl/private/test.key \
     -out /etc/ssl/certs/test.crt \
     -subj "/CN=myapp.local"
   ```
2. Настрой Nginx для HTTPS (как в 5.8)
3. Проверь конфиг: `sudo nginx -t`
4. Перезагрузи: `sudo systemctl reload nginx`
5. Проверь: `curl -kI https://myapp.local`

### Упражнение 5.2: Certbot (если есть домен)
**Задача:**
1. Установи certbot: `sudo apt install -y certbot python3-certbot-nginx`
2. Убедись что порт 80 открыт: `sudo ufw allow 80`
3. Запроси сертификат: `sudo certbot --nginx -d myapp.ru`
4. Проверь что Nginx конфиг изменился: `cat /etc/nginx/sites-enabled/myapp.conf`
5. Проверь HTTPS: `curl -I https://myapp.ru`
6. Проверь редирект: `curl -I http://myapp.ru`

### Упражнение 5.3: Проверка автопродления
**Задача:**
1. Проверь таймер: `systemctl status certbot.timer`
2. Проверь следующий запуск: `systemctl list-timers certbot.timer`
3. Запусти dry-run: `sudo certbot renew --dry-run`
4. Какой результат?

### Упражнение 5.4: Проверка сертификата
**Задача:**
1. Проверь сертификат через curl:
   ```bash
   curl -vI https://myapp.local 2>&1 | grep -E "SSL|subject|expire"
   ```
2. Когда истекает сертификат?
3. Кто выдал?
4. Какой домен (CN)?

### Упражнение 5.5: DevOps Think
**Задача:** «Пользователи жалуются что сайт показывает ERR_CERT_DATE_INVALID. Диагностируй и исправь»

Подсказки:
1. Когда истекал сертификат? `sudo certbot certificates`
2. Работает ли автопродление? `systemctl status certbot.timer`
3. Попробуй продлить вручную: `sudo certbot renew`
4. Что в логах? `sudo journalctl -u certbot -n 50`
5. Если certbot не может продлить — почему? (порт 80, DNS)

---

## 📋 Чеклист главы 5

- [ ] Я понимаю что делает TLS (шифрует + подтверждает личность)
- [ ] Я понимаю как работает ACME challenge
- [ ] Я могу установить certbot и получить сертификат
- [ ] Я понимаю что certbot меняет в Nginx
- [ ] Я знаю где лежат файлы сертификата
- [ ] Я понимаю зачем нужно автопродление
- [ ] Я могу проверить автопродление (`certbot renew --dry-run`)
- [ ] Я могу настроить редирект HTTP → HTTPS вручную
- [ ] Я могу создать self-signed сертификат для тестов
- [ ] Я знаю типичные ошибки certbot и как их чинить
- [ ] Я помню что порт 80 должен быть открыт для certbot

**Всё отметил?** Переходи к Главе 6 — фаервол с ufw.
