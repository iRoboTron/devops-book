# Приложение B: Лаборатория и конфиги

---

## Минимальные лабораторные варианты

### Вариант 1: Две VM

```text
client VM
server VM
```

Хватит для:
- SSH hardening;
- firewall;
- reverse proxy;
- fail2ban;
- простых внешних проверок.

### Вариант 2: Три VM

```text
client VM
gateway VM
server VM
```

Хватит для:
- gateway/firewall практики;
- DMZ-like схемы;
- сетевого наблюдения и сегментации.

---

## Что нельзя делать в этой книге

- сканировать чужие IP;
- тестировать чужие веб-сайты;
- воспроизводить destructive flooding за пределами своей lab;
- путать controlled verification с offensive экспериментами.

---

## Полезные точки snapshot

- после установки и обновления системы;
- после настройки SSH;
- после включения firewall;
- после настройки reverse proxy;
- после финального проекта.

---

## Что документировать после каждой главы

- открытые порты;
- активные сервисы;
- где лежат логи;
- какие проверки допустимы;
- как выглядит успешный результат.

---

## Полный `jail.local` для fail2ban

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd
ignoreip = 127.0.0.1/8 10.0.0.0/24

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 3
```

Что здесь важно:
- `ignoreip` защищает от случайного бана своих доверенных адресов;
- `backend = systemd` обычно лучше для современной Ubuntu;
- SSH и nginx наблюдаются отдельно, потому что у них разная частота и разная цена ошибки.

---

## Полный `nginx` server-блок с rate limiting и security headers

```nginx
# /etc/nginx/sites-available/app.conf
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
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location /login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Проверка после сохранения:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -sI https://HOST | grep -Ei 'x-frame|x-content|strict-transport|referrer'
```

---

## Пример `~/.ssh/config` для jump host / bastion

```text
Host bastion
    HostName bastion.example.com
    User deploy
    IdentityFile ~/.ssh/id_ed25519

Host app-server
    HostName 10.0.0.20
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump bastion
```

Как это работает:
- сначала SSH подключается к `bastion`;
- потом через него прокидывает соединение к `app-server`;
- сам внутренний сервер можно вообще не публиковать в интернет.
