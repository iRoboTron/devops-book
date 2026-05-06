# Глава 8: Безопасность Nextcloud

> **Цель:** проверить базовые настройки безопасности без фанатизма.

---

## 8.1 Reverse proxy

За Nginx важны:

- `trusted_domains`;
- `trusted_proxies`;
- `overwriteprotocol`;
- корректный HTTPS снаружи;
- реальные IP клиентов в логах.

Не копируй универсальный конфиг. AIO, внешний Nginx и домен могут отличаться.

---

## 8.2 trusted_domains и trusted_proxies — ключевые настройки за Nginx

Когда Nextcloud работает за Nginx как reverse proxy, два параметра критичны. Без них Nextcloud либо показывает «Access through untrusted domain», либо генерирует неправильные ссылки (http вместо https, внутренний IP вместо домена).

### trusted_domains

Nextcloud проверяет, с какого домена пришёл HTTP-запрос. Если домен не в списке — доступ блокируется.

```bash
# Посмотреть текущие trusted_domains
occ config:system:get trusted_domains
```

# Пример вывода:
```
Array
(
    [0] => localhost
    [1] => nextcloud.yourdomain.com
)
```

```bash
# Добавить домен (индекс 1, 2, 3... — порядковый номер)
occ config:system:set trusted_domains 1 --value="nextcloud.yourdomain.com"

# Если нужен IP (например для доступа из локальной сети)
occ config:system:set trusted_domains 2 --value="192.168.1.100"
```

### trusted_proxies

Nextcloud должен знать, что запросы приходят через Nginx, и брать реальный IP клиента из заголовка `X-Forwarded-For`, а не из IP Nginx. Без этого все пользователи будут видны с одного IP, а brute force protection не работает.

```bash
# Добавить IP или подсеть Nginx
occ config:system:set trusted_proxies 0 --value="172.17.0.0/16"

# Если Nginx на хосте (не в Docker) — его IP в docker network
# Узнать: docker network inspect bridge | grep Gateway
occ config:system:set trusted_proxies 0 --value="172.17.0.1"
```

### overwriteprotocol

Если HTTPS терминируется на Nginx, а внутри контейнеры общаются по HTTP — Nextcloud не знает что снаружи HTTPS и генерирует http:// ссылки.

```bash
# Исправить: сказать Nextcloud что снаружи HTTPS
occ config:system:set overwriteprotocol --value="https"
```

```bash
# Проверить все три параметра сразу
occ config:system:get trusted_domains
occ config:system:get trusted_proxies
occ config:system:get overwriteprotocol
```

# Пример вывода overwriteprotocol:
```
https
```

> **Если что-то пошло не так:** Nextcloud показывает «You are accessing the server through an untrusted domain» — добавь домен в `trusted_domains`. Если ссылки в share-письмах начинаются на `http://` — установи `overwriteprotocol=https`. Если в логах все пользователи с IP `172.18.0.x` вместо реальных — настрой `trusted_proxies`.

---

## 8.3 Проверки occ

```bash
occ security:scan
```

# Пример вывода (если команда доступна):
```
Checking for potential security warnings...
- .htaccess file works: OK
- No executable files in data directory: OK
- Strong password policy: OK
```

```bash
occ config:system:get trusted_domains
occ config:system:get trusted_proxies
occ config:system:get overwriteprotocol
```

Не публикуй полный `config:list system`.

---

## 8.4 Пароли и MFA

Проверь:

- есть ли admin-аккаунты без необходимости;
- включена ли 2FA для админов;
- есть ли политика паролей;
- есть ли recovery codes у важных пользователей.

---

## 8.5 Права файлов

```bash
docker exec nextcloud-aio-nextcloud stat -c "%a %U %G" /var/www/html/config/config.php
```

# Пример вывода:
```
640 www-data www-data
```

Права `640` означают:
- `6` (rw-) — владелец `www-data` может читать и писать;
- `4` (r--) — группа `www-data` может только читать;
- `0` (---) — остальные не имеют доступа.

Это корректные права для `config.php`. Если видишь `777` или `644` с другим владельцем — это проблема.

Не меняй права вслепую. Сначала сравни с документацией AIO.

---

## 8.6 Практика

Сделай security checklist без секретов:

| Проверка | Результат | Действие |
|---|---|---|
| HTTPS | | |
| trusted domains | | |
| trusted_proxies | | |
| overwriteprotocol | | |
| 2FA admin | | |
| config permissions | | |
