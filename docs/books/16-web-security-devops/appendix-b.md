# Приложение B: Лаборатория, конфиги и правила безопасности

> Практика этой книги должна быть воспроизводимой и безопасной.

---

## Минимальная лаборатория

Варианты:

- одна VM для простых глав;
- 2-3 VM для разделения ролей client / gateway / server;
- VPS + отдельная test-VM;
- виртуальные сети внутри hypervisor.

---

## Что нельзя делать

- тестировать чужие хосты;
- использовать production как lab;
- применять destructive сценарии без отката;
- хранить реальные секреты в учебных конфигах;
- подменять defensive validation offensive экспериментом ради интереса.

---

## Что нужно фиксировать

Перед началом каждой крупной практики запиши:

- какой сервис проверяешь;
- какой защитный контроль вводишь;
- какой сигнал должен появиться;
- как выглядит успешный результат;
- как откатиться назад.

---

## Snapshot discipline

Хорошие точки сохранения:

- после базовой настройки системы;
- после включения ключевого защитного слоя;
- перед controlled test;
- после финального проекта.

---

## Готовый `nginx` baseline для lab

```nginx
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location ~* \.(env|bak|old|orig|backup)$ {
        deny all;
        return 404;
    }

    location /login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Шпаргалка по `curl`

```bash
curl -sI https://HOST | grep -Ei 'content-security|x-content|x-frame|strict-transport'
curl -vk https://HOST/login 2>&1 | grep -i set-cookie
curl -I -H 'Origin: https://evil.example' https://HOST/api/me
curl -s "https://HOST/fetch?url=http://127.0.0.1:5432"
```

Эти четыре команды быстро показывают headers, cookie, CORS и реакцию на базовую SSRF-проверку.

## Учебное приложение для lab

Для безопасной практики можно поднять намеренно уязвимое приложение только у себя:

```bash
docker run --rm -p 3000:3000 bkimminich/juice-shop
```

После запуска открывай `http://localhost:3000` и проводи все проверки глав 1-8 только на этом локальном контейнере или своей lab-инфраструктуре.
