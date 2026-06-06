# Глава 6: HTTPS и TLS — сертификаты, openssl, проверка

## Что вы узнаете

- как работает TLS-рукопожатие и зачем нужен сертификат;
- что такое CA, цепочка доверия и self-signed сертификат;
- как проверить сертификат через `openssl s_client`;
- как создать self-signed сертификат для тестирования.

**Цель главы:** быстро проверить сертификат, выяснить когда истекает и почему ошибка.

---

## 6.1 Что такое TLS

**TLS (Transport Layer Security)** — протокол, который даёт три вещи поверх TCP:

```
┌─────────────────────────────────────────────┐
│          HTTPS = HTTP + TLS                 │
├─────────────────────────────────────────────┤
│ 🔒 Шифрование      — никто не читает трафик │
│ 🆔 Аутентификация  — это точно тот сервер   │
│ 📦 Целостность     — данные не подменили    │
└─────────────────────────────────────────────┘
```

### TLS-рукопожатие (TLS handshake) — упрощённо

```
Клиент                          Сервер
  │                                │
  │ 1. ClientHello                  │
  │    └─ поддерживаемые версии,    │
  │       шифры, random             │
  │───────────────────────────────>│
  │                                │
  │ 2. ServerHello                 │
  │    └─ выбранная версия, шифр,  │
  │       random, сертификат       │
  │<───────────────────────────────│
  │                                │
  │ 3. Проверка сертификата       │
  │    └─ CA, срок, имя хоста     │
  │                                │
  │ 4. Key Exchange (Pre-Master)   │
  │───────────────────────────────>│
  │                                │
  │ 5. Finished                    │
  │<───────────────────────────────│
  │                                │
  │      🔐 Зашифрованный канал    │
  │         (симметричное шифро-   │
  │          вание + session keys)  │
```

Ключевой момент: **сертификат передаётся на шаге 2**, а проверка происходит на стороне клиента. Если сертификат невалиден — клиент сам решает, прерывать соединение или нет.

### Как это выглядит в curl

```bash
curl -v https://google.com 2>&1 | grep -i "TLS\|SSL\|certificate"
```

Вы увидите:
```
*   Trying 142.250.185.78:443...
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, Certificate verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.3 (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
```

---

## 6.2 Сертификат и цепочка доверия

### Что такое сертификат

Сертификат X.509 — это цифровой документ, который связывает **публичный ключ** с **именем (CN/SAN)** и подписан **удостоверяющим центром (CA)**.

```
Сертификат (упрощённо):
┌──────────────────────────────────┐
│ Subject: CN=example.com          │
│ Issuer:  CN=R3, O=Let's Encrypt │
│ Not Before: Jan 1 00:00:00 2026 │
│ Not After : Apr 1 00:00:00 2026 │
│ Public Key: 04:a1:b2:c3...       │
│ Signature: [подпись CA]          │
│ SAN: example.com, www.example.com│
│ Fingerprint (SHA256): ABC123...  │
└──────────────────────────────────┘
```

### Цепочка доверия

```
┌──────────────────────────────────────────────┐
│         Root CA (сам себе хозяин)            │
│         🗝️ Ключ встроен в ОС/браузер       │
│              Подписывает:                    │
│              ┌──────────────────────┐        │
│              │  Intermediate CA    │        │
│              │  (промежуточный)    │        │
│              └──────────────────────┘        │
│              Подписывает:                    │
│              ┌──────────────────────┐        │
│              │  Сертификат сервера │        │
│              │  example.com        │        │
│              └──────────────────────┘        │
└──────────────────────────────────────────────┘
```

- **Root CA** — корневой центр. Его сертификат встроен в ОС, браузер. Если его скомпрометируют — весь интернет в опасности.
- **Intermediate CA** — промежуточный. Их используют, чтобы не светить корневой ключ.
- **Leaf (end-entity)** — сертификат вашего сайта.

При проверке клиент строит цепочку от сертификата сайта до Root CA, который знает и доверяет.

### Проверка через openssl

```bash
# Показать всю цепочку
openssl s_client -connect example.com:443 -showcerts </dev/null 2>/dev/null
```

В выводе — несколько блоков `-----BEGIN CERTIFICATE-----`. Первый — сертификат сайта, последующие — промежуточные.

### Получение сертификата сайта

```bash
# Скачать сертификат в файл
openssl s_client -connect example.com:443 </dev/null 2>/dev/null \
  | sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' \
  > example-cert.pem

# Или через sed -n /-BEGIN CERT-/,/-END CERT-/p
openssl s_client -connect example.com:443 -showcerts </dev/null 2>/dev/null \
  | awk '/-----BEGIN CERTIFICATE-----/{flag=1; file="cert"++count".pem"} flag{print > file; if(/-----END CERTIFICATE-----/) flag=0}'
```

---

## 6.3 openssl s_client — диагностика TLS

`openssl s_client` — главный инструмент для диагностики TLS. Он подключается к серверу и показывает весь процесс рукопожатия.

### Базовая проверка

```bash
openssl s_client -connect example.com:443 -servername example.com </dev/null
```

Флаг `-servername` — для SNI (Server Name Indication). Если на IP несколько сайтов, без SNI сервер не знает, какой сертификат отдать.

> Без `-servername` некоторые CDN (Cloudflare, Akamai) вернут default-сертификат — не того сайта.

### Даты сертификата

```bash
openssl s_client -connect example.com:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -dates
```

Вывод:
```
notBefore=Jan  1 00:00:00 2026 GMT
notAfter=Apr  1 00:00:00 2026 GMT
```

### Кто выдал и кому

```bash
openssl s_client -connect example.com:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -subject
```

```
issuer=C = US, O = Let's Encrypt, CN = R3
subject=CN = example.com
```

### Полная информация

```bash
openssl s_client -connect example.com:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -text | head -40
```

Покажет Subject, Issuer, Validity, Public Key, **SAN** (Subject Alternative Names), расширения.

### SAN — почему сертификат не подходит

```bash
openssl s_client -connect example.com:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName
```

Если имя хоста не в SAN — браузер покажет ошибку.

### Проверка конкретного файла сертификата

```bash
openssl x509 -in cert.pem -noout -text
openssl x509 -in cert.pem -noout -dates
openssl x509 -in cert.pem -noout -issuer -subject
```

### Диагностика за 10 секунд

```bash
# Всё в одной строке
echo | openssl s_client -connect github.com:443 -servername github.com 2>/dev/null \
  | openssl x509 -noout -dates -issuer -subject
```

### Ошибки s_client и их значения

| Симптом | Что скорее всего |
|---------|------------------|
| `verify error:num=10` | Сертификат истёк |
| `verify error:num=20` | Неизвестный issuer (не хватает intermediate) |
| `verify error:num=18` | Самоподписанный сертификат |
| `verify error:num=62` | Имя хоста не совпадает с SAN |
| `connect: Connection refused` | Порт закрыт |
| `connect: Connection timed out` | Фаервол / маршрут |
| `SSL_ERROR_RX_RECORD_TOO_LONG` | Порт не TLS (например, HTTP на 443) |

#### SSL_ERROR_RX_RECORD_TOO_LONG

```
140735227255872:error:1408F10B:SSL routines:ssl3_get_record:wrong version number
```

Означает, что вы стучитесь TLS-клиентом на порт, где работает обычный HTTP без TLS. Проверьте: может сервер слушает HTTP на стандартном HTTPS-порту?

```bash
# Проверить, что на порту
curl http://example.com:443
# vs
curl https://example.com:443
```

---

## 6.4 Создать self-signed сертификат

Для тестов и локальной разработки не обязательно покупать сертификат — можно создать самоподписанный.

### RSA (4096 бит)

```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=localhost/O=Test/C=RU"
```

- `-x509` — сразу сертификат (без CSR);
- `-newkey rsa:4096` — создать новый ключ RSA 4096 бит;
- `-keyout key.pem` — куда сохранить приватный ключ;
- `-out cert.pem` — куда сохранить сертификат;
- `-days 365` — срок действия;
- `-nodes` — без пароля на ключ (no DES);
- `-subj` — subject (CN — Common Name).

### Ed25519 (современнее и быстрее)

```bash
openssl req -x509 -newkey ed25519 \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=myserver.local"
```

Ed25519 даёт те же 128 бит безопасности, что RSA-3072, но ключи короче и генерация быстрее.

### Для нескольких доменов (SAN)

```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:myserver.local,IP:127.0.0.1"
```

### Просмотр созданного сертификата

```bash
openssl x509 -in cert.pem -noout -text
```

### Использование с nginx

```
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ...
}
```

### Проверка curl

```bash
# Без проверки — только для тестов
curl -k https://localhost

# С указанием CA (если в --cacert указать сам cert.pem)
curl --cacert cert.pem https://localhost
```

> ☠️ **Осторожно:** Никогда не используйте самоподписанные сертификаты в production. Браузер покажет страшную красную страницу, пользователи не поверят.

---

## 6.5 Let's Encrypt и certbot

**Let's Encrypt** — бесплатный автоматический CA. Сертификаты живут 90 дней, продление автоматическое. Стандарт де-факто для HTTPS.

### Установка certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### Получение сертификата

```bash
sudo certbot --nginx -d example.com -d www.example.com
```

Certbot автоматически:
1. Проверит, что вы владеете доменом (HTTP-челлендж);
2. Получит сертификат от Let's Encrypt;
3. Пропишет его в nginx.

### Проверка продления

```bash
sudo certbot renew --dry-run
```

### Структура файлов

```
/etc/letsencrypt/live/example.com/
├── cert.pem      # только сертификат сервера
├── chain.pem     # промежуточные CA
├── fullchain.pem # cert.pem + chain.pem (самое нужное)
└── privkey.pem   # приватный ключ (никому не показывать!)
```

В nginx обычно указывают:

```
ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
```

> `fullchain.pem` — то, что нужно. Если указать только `cert.pem`, некоторые клиенты не смогут построить цепочку и выдадут `unable to get local issuer certificate`.

### Статус сертификата

```bash
sudo certbot certificates
```

---

## Типичные ошибки

### 1. Сертификат истёк

```
curl: (60) SSL certificate problem: certificate has expired
```

```bash
openssl s_client -connect example.com:443 </dev/null 2>/dev/null | openssl x509 -noout -dates
```

Решение: обновить сертификат (`certbot renew`).

### 2. unable to get local issuer certificate

```
SSL: certificate verify failed (unable to get local issuer certificate)
```

Причина: сервер не отдаёт промежуточные сертификаты, или клиент указал `cert.pem` вместо `fullchain.pem`.

Решение: проверить конфиг nginx — должен быть `fullchain.pem`.

```bash
openssl s_client -connect example.com:443 -showcerts </dev/null
```

Смотрите, есть ли все звенья цепочки.

### 3. SSL_ERROR_RX_RECORD_TOO_LONG

```
error:1408F10B:SSL routines:ssl3_get_record:wrong version number
```

Вы стучитесь TLS на порт без TLS. Проверьте: http:// vs https://, тот ли порт.

```bash
curl -v http://example.com:443  # может, там HTTP?
```

### 4. Self-signed в production

Самоподписанный сертификат на production-сервере — грубейшая ошибка. Браузер не даст зайти без предупреждения. Используйте Let's Encrypt.

### 5. Нет SNI

```bash
# Без SNI — может вернуть не тот сертификат
openssl s_client -connect example.com:443 </dev/null

# С SNI — правильно
openssl s_client -connect example.com:443 -servername example.com </dev/null
```

---

## Чек-лист

- [ ] `echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -dates` — даты сертификата;
- [ ] `echo | openssl s_client -connect <host>:443 -showcerts </dev/null 2>/dev/null` — цепочка сертификатов;
- [ ] `openssl x509 -in cert.pem -noout -text | grep -A1 "Subject Alternative Name"` — SAN сертификата;
- [ ] `curl --cacert fullchain.pem https://...` — проверка с кастомным CA.

---

## Попробуйте сами

**Задание 1. Проверка сертификата github.com**

```bash
echo | openssl s_client -connect github.com:443 -servername github.com 2>/dev/null \
  | openssl x509 -noout -dates -issuer -subject
```

Определите:
- когда истекает сертификат;
- кто выдал (issuer);
- какой срок остался (посчитайте разницу).

**Задание 2. Self-signed сертификат**

```bash
# Создайте сертификат
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 30 -nodes -subj "/CN=test.local"

# Проверьте curl без и с опцией
curl -k https://localhost:...  # предполагая, что подняли HTTPS-сервер
curl --cacert cert.pem https://localhost:...
```

Сравните сообщения: что говорит curl без `-k`?

**Задание 3. Просроченный сертификат**

Подключитесь к expired.badssl.com:

```bash
echo | openssl s_client -connect expired.badssl.com:443 -servername expired.badssl.com 2>/dev/null \
  | openssl x509 -noout -dates
```

Что показывает curl?

```bash
curl https://expired.badssl.com
```

Какая ошибка? Какой verify error?
