# Глава 4: Nikto без паники

> **Цель:** использовать nikto как шумный, но полезный индикатор типовых проблем.

---

## 4.1 Запуск

```bash
nikto -h https://yourdomain.com -o audits/2026-05-06/nikto.txt -Format txt
```

Только свой домен.

---

## 4.2 Полный пример вывода

```bash
nikto -h https://yourdomain.com
```

```
# Пример вывода:
- Nikto v2.1.6
---------------------------------------------------------------------------
+ Target IP:          203.0.113.42
+ Target Hostname:    yourdomain.com
+ Target Port:        443
+ SSL Info:           Subject:  /CN=yourdomain.com
                      Ciphers:  TLS_AES_256_GCM_SHA384
                      Issuer:   /C=US/O=Let's Encrypt/CN=R3
+ Start Time:         2026-05-06 14:40:01 (GMT0)
---------------------------------------------------------------------------
+ Server: nginx
+ The anti-clickjacking X-Frame-Options header is not present.
+ The X-XSS-Protection header is not defined. This header can hint to the
  user agent to protect against some forms of XSS.
+ The X-Content-Type-Options header is not set. This could allow the user
  agent to render the content of the site in a different fashion to the MIME type.
+ Server leaks inforamtion via "X-Powered-By" HTTP response header field
  with value of "PHP/8.1.0". See:
  http://www.exploit-db.com/ghdb/1288
+ OSVDB-3092: /admin/: This might be interesting.
+ OSVDB-3268: /phpmyadmin/: phpMyAdmin was found on this server.
+ OSVDB-3268: /backup/: A backup directory was found.
+ Cookie PHPSESSID created without the httponly flag
+ 8045 requests: 0 error(s) and 8 item(s) reported on remote host
+ End Time:           2026-05-06 14:52:33 (GMT1) (752 seconds)
---------------------------------------------------------------------------
+ 1 host(s) tested
```

---

## 4.3 Разбор находок

**Находка 1: X-Powered-By: PHP/8.1.0**

```
+ Server leaks inforamtion via "X-Powered-By" HTTP response header field with value of "PHP/8.1.0"
```

**Severity: Low.** Сервер раскрывает технологию стека. Атакующий знает, что ищет в CVE-базах для PHP 8.1. Реальной уязвимости здесь нет — только информация.

Как исправить в Nginx + PHP-FPM:

```nginx
fastcgi_hide_header X-Powered-By;
```

Или в `php.ini`:
```ini
expose_php = Off
```

---

**Находка 2: X-XSS-Protection не задан**

```
+ The X-XSS-Protection header is not defined.
```

**Severity: Info / False positive** — этот заголовок устарел и удалён из современных браузеров (Chrome, Firefox). Не паниковать. Добавлять его не нужно — это не улучшит безопасность.

Nikto предупреждает о нём, потому что использует старые правила. Документируй как принятый информационный шум.

---

**Находка 3: /phpmyadmin/ найден**

```
+ OSVDB-3268: /phpmyadmin/: phpMyAdmin was found on this server.
```

**Severity: High** — если phpMyAdmin действительно доступен снаружи, это серьёзно. Нужно проверить:

```bash
curl -o /dev/null -s -w "%{http_code}" https://yourdomain.com/phpmyadmin/
```

- Ответ `200` — phpMyAdmin открыт. Нужно закрыть через nginx (allow only from trusted IP) или убрать с продакшн-сервера.
- Ответ `404` — nikto ошибся, или путь не существует. **False positive.**
- Ответ `403` — доступ закрыт на уровне конфига. Норм, но убедись, что не обходится.

---

**Находка 4: /admin/ найден**

```
+ OSVDB-3092: /admin/: This might be interesting.
```

```
# False positive — объяснение:
# nikto проверяет стандартные пути по словарю (/admin/, /login/, /backup/).
# На этом сервере /admin/ возвращает 301 редирект на /dashboard/login — это
# легитимный путь к авторизации приложения. Он не отдаёт листинг директории
# и защищён паролем. Проверено: curl -I https://yourdomain.com/admin/
# → HTTP/2 301, Location: /dashboard/login
```

Как проверить — это false positive или реальная проблема:

```bash
curl -I https://yourdomain.com/admin/
```

Если `301` или `302` на страницу логина — это нормально. Если `200` и видишь панель без авторизации — проблема реальная.

---

**Находка 5: /backup/ найден**

```
+ OSVDB-3268: /backup/: A backup directory was found.
```

**Severity: High** — публичная директория с бэкапами может содержать дампы базы данных, конфиги с паролями. Проверь:

```bash
curl https://yourdomain.com/backup/
```

Если видишь листинг файлов (`Index of /backup/`) — закрой немедленно через nginx:

```nginx
location /backup/ {
    deny all;
    return 404;
}
```

---

## 4.4 Если nikto зависает

Nikto может зависнуть на медленном соединении или при анализе большого сайта.

```bash
# Добавь таймаут
nikto -h https://yourdomain.com -timeout 10

# Или проверь доступность сайта сначала
curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com
# Должен вернуть 200, не 000 или 5xx
```

Если таймаут не помогает — попробуй без HTTPS:

```bash
nikto -h http://yourdomain.com -timeout 10
```

---

## 4.5 Практика

Выбери 3-5 находок nikto и оформи:

| Находка | Реальна? | Доказательство | Действие |
|---|---|---|---|

Проверка: нет реакции "всё горит" только из-за количества строк.
