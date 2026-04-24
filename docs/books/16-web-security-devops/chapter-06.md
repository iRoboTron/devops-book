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

- разделение .env.example и реального .env;
- строгий .gitignore, права 600, owner root/app user;
- явное доверие только своему reverse proxy;
- TLS redirect, HSTS и корректная работа X-Forwarded-*;
- миграция критичных секретов в secret manager при росте проекта.

### Практический результат главы
- ты можешь объяснить, что в .env допустимо, а что уже требует отдельного хранения;
- понимаешь, как proxy передает схему, хост и IP;
- умеешь проверить, не торчат ли конфиги и бэкапы наружу.

```text
# .env.example
APP_ENV=production
DATABASE_URL=postgresql://app:change_me@db:5432/app
SECRET_KEY=change_me

chmod 600 .env
chown app:app .env

add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

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
```

### Шаг 2: Проверь reverse proxy boundary
- сними полный конфиг nginx или caddy и зафиксируй, где заканчивается TLS;
- проверь redirect на HTTPS, HSTS и передачу forwarded headers.

```bash
sudo nginx -T | sed -n '1,240p'
curl -I http://HOST
curl -I https://HOST
```

### Шаг 3: Найди утечки секретов в коде и логах
- поиск по ключевым словам SECRET, TOKEN, PASSWORD, API_KEY;
- проверь startup logs и debug endpoints.

```bash
rg -n "SECRET|TOKEN|PASSWORD|API_KEY|DATABASE_URL" .
journalctl -u myapp -n 200 --no-pager
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
