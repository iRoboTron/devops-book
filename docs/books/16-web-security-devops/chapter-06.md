# Глава 6: Секреты, .env и безопасность reverse proxy

> **Запомни:** секреты редко утекут сами по себе. Обычно их сдает плохой процесс: длинноживущий .env, логирование, широкие права и неверная граница между proxy и приложением.

---

## 6.1 Контекст и границы

Большинство приложений начинают с .env, и это нормально. Проблема начинается, когда .env становится постоянным складом всех ключей, копируется на staging, попадает в бэкапы и случайно светится в логах и CI.

Reverse proxy завершает TLS и формирует доверенную границу перед приложением. Если эта граница описана плохо, приложение ошибается в схеме, IP клиента, хосте и политике секретов.

Эта глава особенно полезна для всех веб-сервисов за nginx, caddy или traefik, особенно в Docker и на VPS.

---

## 6.2 Как выглядит риск

Типовые слабые места:
- секреты лежат в репозитории или .env.example содержит реальные значения;
- переменные окружения печатаются в startup logs;
- backend считает любой X-Forwarded-Proto доверенным;
- TLS заканчивается на proxy, но backend продолжает считать себя HTTP-сервисом;
- доступ к .env, резервным конфигам и debug endpoints не закрыт.

### Где особенно важно
- один VPS
- docker compose
- small business reverse proxy
- internal apps behind VPN

---

## 6.3 Что строит защитник

Защита здесь строится не из лозунга "секреты важны", а из конкретных границ: что можно хранить в шаблоне, кто читает реальный `.env`, и откуда backend доверяет proxy-заголовкам.

Плохой `.env.example`:

```ini
APP_ENV=production
DATABASE_URL=postgresql://myapp:SuperSecret123@db:5432/myapp
SECRET_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ123456
STRIPE_SECRET_KEY=sk_live_AbCdEfGhIjKlMnOpQrStUv
```

Такой шаблон уже содержит реальные ключи. Если файл попадает в Git, резервные копии или support-архив, секрет считается скомпрометированным.

Правильный `.env.example`:

```ini
APP_ENV=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
SECRET_KEY=REPLACE_WITH_RANDOM_64_CHARS
STRIPE_SECRET_KEY=REPLACE_WITH_STRIPE_KEY
```

Реальный `.env` должен жить отдельно от шаблона, не попадать в Git и читаться только приложением или его владельцем.

```bash
git status .env 2>/dev/null || echo "not a git repo or .env not tracked"
cat .gitignore | grep ".env"
git log --all --full-history -- '*.env' | head -5
ls -la .env
```

Как читать результат:
- если `git log` что-то показывает, секрет уже был в истории и простой правки файла недостаточно;
- права должны быть `-rw-------`, а не `-rw-r--r--`;
- владелец файла должен быть пользователем приложения, а не кем попало.

Исправление прав:

```bash
chmod 600 .env
chown app:app .env
```

### Практический результат главы
- ты можешь показать хороший и плохой `.env.example`;
- понимаешь, как проверить, был ли `.env` в Git раньше;
- умеешь подтвердить, что reverse proxy действительно завершает TLS и передаёт доверенные заголовки.

---

## 6.4 Практика

### Шаг 1: Приведи .env к нормальному виду
- оставь в .env.example только шаблонные значения и пояснения;
- убедись, что реальный .env не попадает в git и не читается посторонними.

```bash
nano .env.example
nano .env
nano .gitignore
ls -l .env*
git status .env 2>/dev/null || echo "not a git repo or .env not tracked"
git log --all --full-history -- '*.env' | head -5
```

Ожидаемая картина:

```
-rw------- 1 app app 412 Apr 25 10:20 .env
-rw-r--r-- 1 app app 198 Apr 25 10:18 .env.example
```

Проблема выглядит так:

```
-rw-r--r-- 1 app app 412 Apr 25 10:20 .env
```

Здесь секреты читаются любым локальным пользователем системы.

### Шаг 2: Проверь reverse proxy boundary
- сними полный конфиг nginx или caddy и зафиксируй, где заканчивается TLS;
- проверь redirect на HTTPS, HSTS и передачу forwarded headers.

```bash
curl -I http://HOST
curl -sI https://HOST | grep -i strict
sudo nginx -T | grep -E 'proxy_set_header|X-Forwarded|X-Real|real_ip'
```

Ожидаемо:

```
HTTP/1.1 301 Moved Permanently
Location: https://HOST/
```

И отдельно:

```
strict-transport-security: max-age=31536000; includeSubDomains
```

Если backend пишет в логах только `127.0.0.1`, а не реальный client IP, значит доверенная граница proxy описана неполно.

### Шаг 3: Найди утечки секретов в коде и логах
- поиск по ключевым словам SECRET, TOKEN, PASSWORD, API_KEY;
- проверь startup logs и debug endpoints.

```bash
rg -n "SECRET|TOKEN|PASSWORD|API_KEY|DATABASE_URL" . --type py --type js
journalctl -u myapp -n 50 --no-pager | grep -i "secret\|token\|password\|key"
git log --all -p | grep -E "SECRET_KEY|API_KEY|PASSWORD" | head -20
```

Если последняя команда находит строки, секрет уже ушёл в историю коммитов. Тогда нужна не только правка файла, но и ротация ключей.

## 6.4а Проверка backup-файлов

Боты часто спрашивают не только `.env`, но и его резервные копии.

```bash
for f in .env .env.bak .env.old config.php.bak database.yml.bak; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://HOST/$f")
  echo "$code $f"
done
```

Правильный результат:

```
404 .env
404 .env.bak
404 .env.old
```

Если любой файл вернул `200`, веб-сервер раздаёт конфигурацию напрямую.

Минимальная защита в nginx:

```nginx
location ~* \.(env|bak|old|orig|backup)$ {
    deny all;
    return 404;
}
```

### Что нужно явно показать
- разницу между .env.example и .env;
- права на файл секретов;
- конфиг reverse proxy с TLS и forwarded headers;
- результат поиска возможных утечек в логах.

---

## 6.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- сделай controlled check: запроси типичные backup-имена вроде .env.bak на своем стенде и убедись, что они не выдаются веб-сервером;
- проверь, что приложение за прокси генерирует HTTPS-ссылки и видит корректный client IP;
- убедись, что секреты не отображаются в /debug, health-check и логах старта.

---

## 6.6 Типовые ошибки

- держать production secrets в .env.example;
- разрешать world-readable права на .env;
- не различать trusted proxy и произвольного клиента;
- логировать весь process environment при старте.

---

## 6.7 Чеклист главы

- [ ] Я отделил шаблоны конфигурации от реальных секретов
- [ ] Я проверил права и git-ignore для .env
- [ ] Reverse proxy корректно завершает TLS и передает trusted headers
- [ ] Я убедился, что секреты не светятся в логах и HTTP-ответах
