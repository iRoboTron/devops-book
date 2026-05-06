# Глава 2: SSL/TLS

> **Цель:** проверить HTTPS без слепого копирования конфигов.

---

## 2.1 Что проверяем

- TLS 1.2/1.3 включены;
- TLS 1.0/1.1 отключены;
- сертификат действителен;
- слабые шифры не используются;
- HSTS включён только там, где это осознанно.

---

## 2.2 testssl.sh

```bash
docker run --rm -ti drwetter/testssl.sh https://yourdomain.com \
  | tee audits/2026-05-06/testssl.txt
```

Или установленный локально `testssl.sh`.

**Пример вывода (сокращённый):**

```
# Пример вывода:
###########################################################
    testssl.sh       3.0.9 from https://testssl.sh/
    ...
###########################################################

 Testing protocols via sockets except NPN+ALPN

 SSLv2      not offered (OK)
 SSLv3      not offered (OK)
 TLS 1      offered (deprecated)           <-- ПРОБЛЕМА
 TLS 1.1    not offered (OK)
 TLS 1.2    offered (OK)
 TLS 1.3    offered (OK)
 NPN/SPDY   not offered
 ALPN/HTTP2 h2, http/1.1 (offered)

 Testing server's cipher preferences

 Hexcode  Cipher Suite Name (OpenSSL)       KeyExch.   Encryption  Bits
 x1302   TLS_AES_256_GCM_SHA384            ECDH 253   AESGCM      256
 x1301   TLS_AES_128_GCM_SHA256            ECDH 253   AESGCM      128
 xc02c   ECDHE-ECDSA-AES256-GCM-SHA384     ECDH 256   AESGCM      256

 Testing vulnerabilities

 Heartbleed (CVE-2014-0160)                not vulnerable (OK)
 CCS (CVE-2014-0224)                       not vulnerable (OK)
 POODLE, SSL (CVE-2014-3566)               not vulnerable (OK)
 BEAST (CVE-2011-3389)                     not vulnerable (OK)
 ROBOT                                     not vulnerable (OK)

 Testing HTTP security headers

 Strict Transport Security      not offered       <-- отсутствует HSTS
 X-Frame-Options                SAMEORIGIN
 X-Content-Type-Options         nosniff

 Rating (experimental)
 Overall Grade                  B
```

**Как читать вывод:**

- `TLS 1 offered (deprecated)` — TLS 1.0 включён, это **проблема**. Современные браузеры его не используют, но он создаёт риски совместимости с атаками.
- `TLS 1.3 offered (OK)` — хорошо, самый современный протокол поддерживается.
- `Heartbleed ... not vulnerable (OK)` — классические атаки не работают.
- `Strict Transport Security not offered` — HSTS не настроен. Это не критично, но желательно.
- `Overall Grade B` — оценка B: есть проблема (TLS 1.0), но в целом неплохо.

**Что значит «Grade A»:**

Grade A от SSL Labs (и testssl.sh) означает: современные протоколы, сильные шифры, нет известных уязвимостей, правильные заголовки. Не означает «взломать невозможно» — это только проверка конфигурации TLS, не всего сервера.

---

## 2.3 Исправление: TLS 1.0 включён → как отключить в Nginx

Если testssl.sh показал `TLS 1 offered`, проверь конфиг Nginx:

```bash
grep ssl_protocols /etc/nginx/nginx.conf /etc/nginx/sites-enabled/*
```

Найди строку вида:
```nginx
ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
```

Исправь: убери `TLSv1` и `TLSv1.1`:

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
```

```bash
nginx -t && systemctl reload nginx
```

После исправления перезапусти testssl.sh — Grade должен подняться до A.

---

## 2.4 Если testssl.sh падает с «connection refused»

```
# Пример вывода при ошибке:
Connect to 203.0.113.42:443 failed: Connection refused
Cannot obtain the server certificate from 203.0.113.42:443
```

Порт 443 закрыт или сервис не слушает. Сначала проверь nmap:

```bash
nmap -p 443 <YOUR_SERVER_IP>
```

Если `443/tcp closed` или `filtered` — настрой HTTPS сначала (сертификат, Nginx listen 443), затем проверяй TLS.

---

## 2.5 SSL Labs

SSL Labs удобен для публичного домена, но ты отправляешь домен внешнему сервису. Для внутреннего сервиса лучше локальный `testssl.sh`.

---

## 2.6 HSTS осторожно

HSTS заставляет браузер ходить на сайт только по HTTPS. На основном домене это полезно. На тестовом домене может мешать, если сертификат или reverse proxy ещё не настроены.

Не включай HSTS механически.

---

## 2.7 Практика

Сохрани отчёт TLS и выпиши:

| Проверка | Результат | Действие |
|---|---|---|
| TLS 1.0 | off | норм |
| TLS 1.3 | on | норм |
| cert expiry | дата | поставить напоминание |
| HSTS | yes/no | решить осознанно |
