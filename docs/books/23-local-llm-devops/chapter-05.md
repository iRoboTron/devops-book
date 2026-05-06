# Глава 5: Nginx перед AI-сервисом

> **Цель:** открыть WebUI через понятный HTTPS-адрес и не открыть лишние порты.

---

## 5.1 Что должен делать Nginx

Nginx принимает внешний HTTPS-трафик и проксирует его на локальный Open-WebUI.

```text
internet
  -> 443 Nginx
  -> 127.0.0.1:3000 Open-WebUI
  -> Ollama внутри сервера
```

Ollama API на `11434` не должен быть открыт напрямую наружу.

> **Аналогия:** Nginx — это охранник на входе в здание. Снаружи люди говорят с охранником (HTTPS на 443), а он уже проводит их к нужному кабинету внутри (Open-WebUI на 3000). Прямой доступ в кабинеты с улицы закрыт.

---

## 5.2 Пример server block

```nginx
server {
    listen 80;
    server_name ai.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.example.com;

    ssl_certificate /etc/letsencrypt/live/ai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

`proxy_read_timeout 300s` нужен потому, что модель может отвечать дольше обычного web-сервиса.

После сохранения конфига — всегда проверяй синтаксис:

```bash
sudo nginx -t
```

# Пример вывода:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Если тест прошёл — перезагружай:

```bash
sudo systemctl reload nginx
```

---

## 5.3 Firewall

Минимальная идея:

```bash
sudo ufw allow 443/tcp
sudo ufw deny 11434
sudo ufw deny 3000
sudo ufw status verbose
```

Если сервис нужен только тебе, лучше не публиковать его в интернет вообще, а открыть через WireGuard.

---

## 5.4 Проверка

С сервера:

```bash
curl -I http://127.0.0.1:3000
curl http://127.0.0.1:11434/api/tags
```

Снаружи:

```bash
curl -I https://ai.example.com
```

Проверь, что эти адреса снаружи не отвечают:

```bash
curl http://PUBLIC_IP:11434/api/tags
curl http://PUBLIC_IP:3000
```

---

## 5.5 Практика

Настрой Nginx, проверь HTTPS, войди в Open-WebUI и сделай тестовый запрос. Итог практики: WebUI открывается через домен, но прямые порты модели и интерфейса снаружи закрыты.

---

> **Если что-то пошло не так:**
>
> **Симптом:** чат в Open-WebUI зависает — ответ модели не появляется (streaming не идёт), хотя curl к API работает напрямую.
>
> Причина: WebSocket-соединение разрывается, потому что Nginx не передаёт заголовки `Upgrade` и `Connection` правильно, или слишком маленький таймаут.
>
> Проверь что в конфиге Nginx присутствуют все эти строки:
> ```nginx
> proxy_http_version 1.1;
> proxy_set_header Upgrade $http_upgrade;
> proxy_set_header Connection "upgrade";
> proxy_read_timeout 300s;
> proxy_send_timeout 300s;
> ```
>
> Если `proxy_read_timeout` не задан — Nginx обрывает соединение через 60 секунд по умолчанию. Для длинных ответов LLM нужно минимум 120-300 секунд.
>
> После правки:
> ```bash
> sudo nginx -t && sudo systemctl reload nginx
> ```
>
> **Симптом:** `sudo nginx -t` выдаёт ошибку вроде `unknown directive`.
>
> Диагностика:
> ```bash
> sudo nginx -t 2>&1 | head -5
> # Посмотреть строку с ошибкой и исправить конфиг
> ```
