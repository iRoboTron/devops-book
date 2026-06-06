# Глава 7: PKI Engine — генерация сертификатов

## Что вы узнаете

- Как настроить Vault как внутренний CA.
- Как выпускать TLS-сертификаты для внутренних сервисов.
- Как настроить автоматическое обновление сертификатов.
- Зачем нужен промежуточный CA и как его создать.

---

## 1. Зачем PKI Engine

Каждое внутреннее взаимодействие между микросервисами должно быть зашифровано. TLS — стандарт, но управление сертификатами — боль.

| Проблема | Без Vault | С Vault PKI |
|---|---|---|
| Self-signed сертификаты | Нужно распространять CA-сертификат на все серверы | Vault — доверенный CA, сертификаты подписываются централизованно |
| Let's Encrypt | Только публичные домены, нет wildcard для `.svc.cluster.local` | Любые внутренние домены и IP |
| Срок жизни | 90-365 дней, нужно помнить о продлении | Минуты-часы (короткоживущие) |
| Ротация | Ручная: `openssl x509 -req ...` + SCP на сервер | Автоматическая: `vault write pki_int/issue/...` |
| Revocation | CRL никто не ведёт | Vault публикует CRL, сертификаты отзываются за секунду |
| Audit | Кто и когда выпустил — неизвестно | Все операции логируются |
| Промежуточные CA | Нет, root CA используется напрямую (опасно) | Root CA подписывает intermediate, intermediate — сертификаты |

```
Без Vault:

  openssl req -x509 ... → server.crt → SCP → /etc/ssl/
  Вспомнить через 11 месяцев: "ой, сертификат протух"
  Продлить, снова SCP, перезапустить nginx

С Vault:

  systemd timer → vault write pki_int/issue/server → /etc/ssl/server.crt
  Сертификат живёт 24 часа — протухание не проблема
  Продление — автоматический скрипт
```

> **Dev vs Production:** в dev можно использовать один root CA напрямую. В production обязательна цепочка: Root CA (офлайн/подписант) → Intermediate CA (онлайн, выпускает сертификаты) → Leaf сертификаты.

---

## 2. Настройка Root CA

Root CA — корневой центр сертификации. Его сертификат нужно распространить на все серверы как доверенный (trusted CA). Root CA подписывает только Intermediate CA, **никогда** — конечные сертификаты.

### 2.1. Включение PKI engine

```bash
# Включаем engine для root CA
vault secrets enable pki

# Устанавливаем максимальный TTL — срок жизни root CA (10 лет)
vault secrets tune -max-lease-ttl=87600h pki
```

### 2.2. Генерация корневого сертификата

```bash
vault write -field=certificate pki/root/generate/internal \
  common_name="My Internal Root CA" \
  issuer_name="root-2026" \
  ttl=87600h > /tmp/root-ca.pem
```

| Параметр | Описание |
|---|---|
| `common_name` | Имя CA (отображается в сертификате) |
| `issuer_name` | Идентификатор issuer (для управления несколькими) |
| `ttl` | Срок жизни сертификата (10 лет = 87600h) |

Сертификат сохранён в `/tmp/root-ca.pem`. Его нужно распространить как доверенный CA во все сервисы:

```bash
# Для Debian/Ubuntu
sudo cp /tmp/root-ca.pem /usr/local/share/ca-certificates/root-ca.crt
sudo update-ca-certificates

# Для Red Hat / CentOS
sudo cp /tmp/root-ca.pem /etc/pki/ca-trust/source/anchors/root-ca.crt
sudo update-ca-trust
```

### 2.3. Настройка URL-адресов для сертификатов и CRL

```bash
vault write pki/config/urls \
  issuing_certificates="http://vault:8200/v1/pki/ca" \
  crl_distribution_points="http://vault:8200/v1/pki/crl"
```

Эти URL попадают в сертификаты как поля `CA Issuers` и `CRL Distribution Points`. Клиенты используют их для проверки цепочки доверия и статуса отзыва.

> ☠️ **Осторожно:** если не настроить `crl_distribution_points`, клиенты не смогут проверить статус сертификата при revocation. В enterprise-среде это нарушение compliance. Всегда настраивайте оба URL.

---

## 3. Промежуточный CA (Intermediate CA)

Root CA никогда не подписывает конечные сертификаты напрямую. Вместо этого root CA подписывает один или несколько Intermediate CA, а уже они выпускают сертификаты для сервисов. Если Intermediate CA скомпрометирован — вы отзываете только его, а root CA остаётся нетронутым.

### 3.1. Создание Intermediate CA

```bash
# Включаем второй PKI engine для intermediate CA
vault secrets enable -path=pki_int pki

# TTL intermediate — меньше, чем root (5 лет)
vault secrets tune -max-lease-ttl=43800h pki_int
```

### 3.2. Генерация CSR

```bash
vault write -format=json pki_int/intermediate/generate/internal \
  common_name="My Internal Intermediate CA" \
  | jq -r '.data.csr' > /tmp/int-ca.csr
```

### 3.3. Подписание CSR корневым CA

```bash
vault write -format=json pki/root/sign-intermediate \
  csr=@/tmp/int-ca.csr \
  format=pem_bundle \
  ttl=43800h \
  | jq -r '.data.certificate' > /tmp/int-ca.pem
```

### 3.4. Импорт подписанного сертификата

```bash
vault write pki_int/intermediate/set-signed certificate=@/tmp/int-ca.pem
```

### 3.5. Весь процесс в одной диаграмме

```
  ┌───────────────────┐       ┌───────────────────┐
  │  Root CA (pki)    │       │  Intermediate (pki_int) │
  │  ttl: 10 лет      │       │  ttl: 5 лет              │
  │  issuer: root-2026│       └─────────┬─────────────┘
  └─────────┬─────────┘                 │
            │                           │
            │  1. generate CSR          │
            │◄──────────────────────────│
            │                           │
            │  2. sign CSR              │
            │──────────────────────────►│
            │                           │
            │  3. set-signed            │
            │  (импорт сертификата)     │
            │                           │
            │                    ┌──────▼──────┐
            │                    │  Leaf certs │
            │                    │  (24h TTL)  │
            │                    └─────────────┘
```

### 3.6. Публикация цепочки сертификатов

Клиенты должны видеть полную цепочку: Leaf → Intermediate → Root. Настройка URL для Intermediate:

```bash
vault write pki_int/config/urls \
  issuing_certificates="http://vault:8200/v1/pki_int/ca" \
  crl_distribution_points="http://vault:8200/v1/pki_int/crl"
```

---

## 4. Роль и выпуск сертификатов

### 4.1. Создание роли

Роль определяет, для каких доменов можно выпускать сертификаты и с какими параметрами.

```bash
vault write pki_int/roles/internal-services \
  allowed_domains="internal.example.com,svc.cluster.local" \
  allow_subdomains=true \
  max_ttl=720h
```

| Параметр | Описание |
|---|---|
| `allowed_domains` | Список разрешённых доменов (через запятую) |
| `allow_subdomains` | Разрешить поддомены (myapp.internal.example.com) |
| `max_ttl` | Максимальный TTL выпускаемого сертификата |
| `allow_any_name` | ☠️ Осторожно: разрешить любые имена (только для dev) |
| `allow_ip_sans` | Разрешить IP-адреса в Subject Alternative Name |
| `key_type` | Тип ключа: `rsa` (2048/4096) или `ec` (256/384) |
| `require_cn` | Обязательное указание common_name |
| `basic_constraints_valid_for_non_ca` | Разрешить basic constraints для конечных сертификатов |

Дополнительные параметры для production:

```bash
vault write pki_int/roles/internal-services \
  allowed_domains="internal.example.com,svc.cluster.local" \
  allow_subdomains=true \
  allow_ip_sans=true \
  max_ttl=720h \
  key_type=ec \
  key_bits=256 \
  require_cn=true \
  server_flag=true \
  client_flag=true
```

### 4.2. Выпуск сертификата

```bash
vault write pki_int/issue/internal-services \
  common_name="myapp.internal.example.com" \
  ttl=24h \
  alt_names="myapp.svc.cluster.local" \
  ip_sans="10.0.0.1"
```

Ответ:

```
Key                 Value
---                 -----
certificate         -----BEGIN CERTIFICATE-----...
issuing_ca          -----BEGIN CERTIFICATE-----... (intermediate)
ca_chain            [root + intermediate]
private_key         -----BEGIN EC PRIVATE KEY-----...
private_key_type    ec
serial_number       3f:2b:1a:9c...
```

### 4.3. Сохранение сертификата и ключа

```bash
# Сохраняем сертификат
vault write -field=certificate pki_int/issue/internal-services \
  common_name="myapp.internal.example.com" ttl=720h > /etc/ssl/certs/myapp.crt

# Сохраняем ключ
vault write -field=private_key pki_int/issue/internal-services \
  common_name="myapp.internal.example.com" ttl=720h > /etc/ssl/private/myapp.key

# Сохраняем цепочку CA
vault write -field=ca_chain pki_int/issue/internal-services \
  common_name="myapp.internal.example.com" ttl=720h > /etc/ssl/certs/ca-chain.crt

# Защищаем ключ
chmod 600 /etc/ssl/private/myapp.key
```

### 4.4. Проверка сертификата

```bash
# Проверка срока действия
openssl x509 -in /etc/ssl/certs/myapp.crt -text -noout | grep -E "Not Before|Not After|Subject|DNS"

# Проверка цепочки
openssl verify -CAfile /etc/ssl/certs/ca-chain.crt /etc/ssl/certs/myapp.crt

# Проверка subject и alt_names
openssl x509 -in /etc/ssl/certs/myapp.crt -noout -ext subjectAltName
```

### 4.5. nginx + сертификат из Vault

```nginx
server {
    listen 443 ssl;
    server_name myapp.internal.example.com;

    ssl_certificate     /etc/ssl/certs/myapp.crt;
    ssl_certificate_key /etc/ssl/private/myapp.key;
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.crt;
}
```

---

## 5. Политика для PKI

Приложениям нужна политика, разрешающая только выпуск сертификатов через конкретную роль, без доступа к Root CA.

### 5.1. Политика для сервиса

```hcl
# pki-myapp.hcl
path "pki_int/issue/internal-services" {
  capabilities = ["create", "update"]
}

# Опционально — чтение CRL и CA-сертификата
path "pki_int/cert/ca" {
  capabilities = ["read"]
}

path "pki_int/crl" {
  capabilities = ["read"]
}
```

### 5.2. Загрузка политики

```bash
vault policy write pki-myapp pki-myapp.hcl
```

### 5.3. Политика для оператора (полный доступ к PKI)

```hcl
# pki-admin.hcl
path "pki/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

path "pki_int/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

> ☠️ **Осторожно:** не выдавайте обычным сервисам доступ к `pki/*` (Root CA). Если приложение сможет создать новый Intermediate CA с другими политиками, это нарушит весь PKI. Root CA — только для администраторов.

### 5.4. Типичный набор политик

| Роль | Доступ | Путь |
|---|---|---|
| Сервис (myapp) | Выпуск сертификатов | `pki_int/issue/internal-services` |
| CI/CD | Выпуск + отзыв | `pki_int/*` |
| Оператор | Всё, включая Root CA | `pki/*`, `pki_int/*` |

---

## 6. Отзыв сертификата

Если сертификат скомпрометирован, его нужно отозвать до истечения TTL.

### 6.1. Отзыв по серийному номеру

```bash
vault write pki_int/revoke serial_number="3f:2b:1a:9c..."
```

### 6.2. Отзыв всех сертификатов по роли

```bash
# Найти все lease по роли
vault list sys/leases/lookup/pki_int/issue/internal-services

# Отозвать все
vault lease revoke -prefix pki_int/issue/internal-services
```

### 6.3. Генерация обновлённого CRL

```bash
vault write -force pki_int/tidy
vault read pki_int/crl
```

---

## Типичные ошибки

- ❌ **Использовать Root CA напрямую для выпуска сертификатов** — если root CA скомпрометирован, вся PKI-инфраструктура под угрозой. Всегда используйте Intermediate CA. Root CA должен быть офлайн или с минимальным TTL.

- ❌ **Слишком длинный TTL (годы)** — чем дольше живёт сертификат, тем больше ущерб при утечке. В production TTL конечных сертификатов — часы (24-72h). Длинные TTL — только для Root CA (10 лет) и Intermediate CA (3-5 лет).

- ❌ **Не настроен CRL URL** — клиенты не смогут проверить, отозван ли сертификат. При компрометации вы отзовёте сертификат, но клиенты продолжат его принимать. Всегда настраивайте `crl_distribution_points`.

- ❌ **Разные сертификаты на dev и prod с одним CN** — если dev-сертификат утек, его можно переиспользовать в prod. Используйте разные common_name или разные Intermediate CA для окружений.

- ❌ **Не настроен `allow_subdomains`** — запрос на `myapp.internal.example.com` упадёт с ошибкой, если в роли указан `internal.example.com` без `allow_subdomains=true`.

- ❌ **Сертификат на одном сервере, а CRL проверяет другой** — убедитесь, что `ca_chain` включает Root + Intermediate, иначе клиент не построит цепочку доверия.

- ❌ **Забыли `chmod 600` на приватном ключе** — сертификат для всех, приватный ключ — только для приложения. Даже Vault не должен видеть ключи после выдачи.

- ❌ **Не настроили ротацию** — если приложение выпустило сертификат раз и забыло, через 24 часа (или когда TTL истечёт) TLS-handshake упадёт. Настройте systemd timer или cron для автоматического обновления.

---

## Чек-лист

- [ ] Root CA и Intermediate CA находятся на разных engine-путях (`pki` vs `pki_int`). Root CA используется только для подписания intermediate, конечные сертификаты выпускаются через intermediate.
- [ ] Настроены `crl_distribution_points` и `issuing_certificates` для обоих CA.
- [ ] Политики ограничивают доступ к `pki_int/issue/<role>` для приложений; Root CA доступен только администраторам.
- [ ] Настроена автоматическая ротация сертификатов: systemd timer / cron / Vault Agent получает новый сертификат до истечения TTL.

---

## Попробуйте сами

1. **Настройте Root CA и Intermediate CA.** Включите `pki` и `pki_int`. Сгенерируйте Root CA, создайте CSR от Intermediate, подпишите его Root CA, импортируйте подписанный сертификат. Проверьте цепочку: `openssl verify -CAfile /tmp/root-ca.pem /tmp/int-ca.pem`.

2. **Выпустите сертификат для сервиса.** Создайте роль `internal-services` с доменом `internal.example.com` и `allow_subdomains=true`. Выпустите сертификат для `myapp.internal.example.com` с TTL=24h. Сохраните сертификат, ключ и ca_chain. Проверьте openssl-командами: срок действия, subject, DNS-имена, цепочку доверия.

3. **Настройте nginx с сертификатом из Vault.** Напишите минимальный конфиг nginx, использующий сертификат и ключ из шага 2. Убедитесь, что `openssl s_client -connect localhost:443 -CAfile root-ca.pem` возвращает `verify return:1`. Отзовите сертификат через `vault write pki_int/revoke`. Сгенерируйте CRL. Проверьте, что тот же `openssl s_client` с CRL показывает отозванный статус.
