# Глава 7b (бонус): Transit Engine — шифрование как сервис

## Что вы узнаете

- Как использовать Vault для шифрования данных без их хранения.
- Разница между encryption в покое (KV) и encryption как сервис (Transit).
- Шифрование/дешифрование через CLI и API.
- Как приложение шифрует PII-данные через Vault, не имея доступа к ключам.

---

## 1. Transit vs KV — разница

KV Secrets Engine хранит зашифрованные данные на стороне Vault. Transit Engine не хранит данные — он предоставляет криптографические операции как сервис.

```
KV v2:         Приложение → plaintext → Vault (хранит encrypted blob)
               Vault отвечает за хранение и расшифровку

Transit:       Приложение → plaintext → Vault → ciphertext → приложение (хранит)
               Ключ НИКОГДА не покидает Vault
               Vault только шифрует/дешифрует, но не хранит результат
```

| Характеристика | KV v2 | Transit |
|---|---|---|
| Что хранит Vault | Encrypted data | Только ключ |
| Кто хранит данные | Vault | Приложение |
| Ключ доступен приложению | Да (в ответе) | Нет (только внутри Vault) |
| Шифрование в покое | Да | Нет (шифрование на лету) |
| Ротация ключа | Нужно перезаписывать данные | Ключ ротируется, ciphertext может быть перешифрован через `rewrap` |
| Аудит данных | Кто читал | Кто шифровал/дешифровал |
| Use-case | Config-файлы, .env | PII, credit cards, API tokens |

```
Жизненный цикл данных с Transit:

  PII → Base64 → Vault encrypt → ciphertext → база данных приложения
                                            → Vault decrypt → Base64 decode → PII

  Злоумышленник украл БД: видит ciphertext, но расшифровать не может
  — ключ в Vault, доступа нет
```

> **Dev vs Production:** в dev можно тестировать с одним ключом без ротации. В production — обязательная ротация + разные ключи для разных типов данных (PII, payment, credentials).

---

## 2. Настройка Transit

### 2.1. Включение engine

```bash
vault secrets enable transit
```

### 2.2. Создание ключа шифрования

```bash
vault write -f transit/keys/myapp-encryption-key
```

Параметры ключа (опционально):

```bash
# Ключ с регулярной ротацией и поддержкой export (только для dev!)
vault write transit/keys/myapp-encryption-key \
  type=aes256-gcm96 \
  deletion_allowed=false \
  exportable=false \
  auto_rotate_period=2160h  # 90 дней
```

| Параметр | Описание | Dev | Production |
|---|---|---|---|
| `type` | Алгоритм: `aes256-gcm96` (по умолчанию), `chacha20-poly1305`, `ecdsa-p256`, `ed25519` | `aes256-gcm96` | `aes256-gcm96` |
| `exportable` | Разрешить экспорт ключа | `true` | **`false`** |
| `deletion_allowed` | Разрешить удаление ключа | `true` | **`false`** |
| `auto_rotate_period` | Автоматическая ротация | `0` (нет) | `2160h` (90d) |

> ☠️ **Осторожно:** никогда не включайте `exportable=true` в production. Смысл Transit в том, что ключ **никогда не покидает Vault**. Если ключ экспортирован — весь смысл шифрования как сервиса теряется.

### 2.3. Шифрование данных

```bash
export PLAINTEXT=$(echo "s3ns1t1v3-data" | base64)

vault write transit/encrypt/myapp-encryption-key \
  plaintext="$PLAINTEXT"
```

Ответ:

```
Key           Value
---           -----
ciphertext    vault:v1:abc123def456...
```

> Plaintext **всегда** передаётся в base64. Vault не принимает сырые строки — это гарантирует, что любые бинарные данные (JSON, protobuf, изображения) могут быть зашифрованы.

### 2.4. Дешифрование

```bash
vault write transit/decrypt/myapp-encryption-key \
  ciphertext="vault:v1:abc123def456..."
```

Ответ:

```
Key           Value
---           -----
plaintext    czNuczF0MXYzLWRhdGE=
```

```bash
echo "czNuczF0MXYzLWRhdGE=" | base64 -d
# → s3ns1t1v3-data
```

### 2.5. API-запросы

Шифрование через API:

```bash
curl -s --header "X-Vault-Token: $VAULT_TOKEN" \
  --request POST \
  --data '{"plaintext":"'$(echo -n "s3ns1t1v3-data" | base64)'"}' \
  http://127.0.0.1:8200/v1/transit/encrypt/myapp-encryption-key \
  | jq -r '.data.ciphertext'
```

Дешифрование через API:

```bash
curl -s --header "X-Vault-Token: $VAULT_TOKEN" \
  --request POST \
  --data '{"ciphertext":"vault:v1:abc123..."}' \
  http://127.0.0.1:8200/v1/transit/decrypt/myapp-encryption-key \
  | jq -r '.data.plaintext' | base64 -d
```

### 2.6. Формат ciphertext

```
vault:v1:abc123def456...
└────┘ └┘ └──────────────
  версия  ключ   encrypted payload
         версии        + nonce + MAC
```

Vault хранит историю версий ключа внутри engine. Старые ciphertext можно расшифровать, пока ключ существует. При ротации создаётся новая версия ключа:

```bash
# Список версий ключа
vault read transit/keys/myapp-encryption-key
```

```
Key                      Value
---                      -----
keys                     map[1:1357924680 2:2468013579]
latest_version           2
min_available_version    1
```

### 2.7. Ротация ключа

```bash
vault write -f transit/keys/myapp-encryption-key/rotate
```

После ротации:
- Новые шифрования используют версию 2 ключа.
- Старые ciphertext (версия 1) всё ещё можно расшифровать.
- Если нужно перешифровать старые данные новым ключом — `rewrap`:

```bash
vault write transit/rewrap/myapp-encryption-key \
  ciphertext="vault:v1:abc123..."
# → возвращает ciphertext с версией 2
```

```
Ротация без rewrap:

  ciphertext_v1 → Vault decrypt (key v1) → OK
  ciphertext_v2 → Vault decrypt (key v2) → OK

Ротация с rewrap:

  ciphertext_v1 → Vault rewrap → ciphertext_v2 (теперь на key v2)
  Старый ciphertext_v1 удалён — данных под v1 больше нет
```

> ☠️ **Осторожно:** ротация ключа **не перешифровывает** существующие ciphertext. Все старые ciphertext остаются на старой версии ключа. Если вы удалите старую версию (через `trim` или `min_decryption_version`), старые ciphertext станут нечитаемы. Используйте `rewrap` для перешифровки старых данных на новую версию.

---

## 3. Дополнительные операции

### 3.1. HMAC — проверка целостности

```bash
vault write transit/hash/myapp-encryption-key \
  input=$(echo -n "message" | base64)
```

Используется для проверки, что данные не были изменены.

### 3.2. Sign / Verify — цифровая подпись

```bash
# Подпись
vault write transit/sign/myapp-encryption-key \
  input=$(echo -n '{"user":"alice","amount":100}' | base64)

# Верификация
vault write transit/verify/myapp-encryption-key \
  input=$(echo -n '{"user":"alice","amount":100}' | base64) \
  signature="vault:v1:abc..."
```

### 3.3. Datakey — сгенерировать ключ на стороне Vault

```bash
vault write transit/datakey/plaintext/myapp-encryption-key \
  bits=256
```

Возвращает `ciphertext` (ключ зашифрован ключом Transit) и `plaintext` (ключ в открытом виде) — для схемы envelope encryption.

```
Envelope encryption:

  ┌─────────────────┐
  │  Data Key (DEK) │ ← получаем из Transit
  │  key: f8a2...   │
  │  wrapped: v1:.. │
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │  Шифруем данные  │
  │  локально AES-256│
  │  ключом DEK     │
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │  Храним:        │
  │  encrypted_data │
  │  wrapped_key    │ ← расшифровка через Transit
  └─────────────────┘
```

### 3.4. Backup / Restore ключа

```bash
vault read transit/keys/myapp-encryption-key/backup \
  > /backup/transit-key.json

vault write transit/keys/myapp-encryption-key/restore \
  backup=@/backup/transit-key.json
```

> ☠️ **Осторожно:** backup ключа содержит материал ключа в открытом виде. Храните backup в безопасном месте (лучше — в другом Vault или encrypted S3). Никогда не храните backup рядом с ciphertext.

---

## 4. Интеграция с приложением

### 4.1. Python + hvac

```python
import hvac, base64

client = hvac.Client(url='http://vault:8200', token='...')

# Шифрование
plaintext_b64 = base64.b64encode(b's3ns1t1v3-data').decode()
encrypted = client.secrets.transit.encrypt_data(
    name='myapp-encryption-key',
    plaintext=plaintext_b64,
)
ciphertext = encrypted['data']['ciphertext']
# → храним ciphertext в БД

# Дешифрование
decrypted = client.secrets.transit.decrypt_data(
    name='myapp-encryption-key',
    ciphertext=ciphertext,
)
plaintext = base64.b64decode(decrypted['data']['plaintext'])
```

### 4.2. Политика для приложения

```hcl
# transit-myapp.hcl
path "transit/encrypt/myapp-encryption-key" {
  capabilities = ["create", "update"]
}

path "transit/decrypt/myapp-encryption-key" {
  capabilities = ["create", "update"]
}

# Без доступа к ключу — только encrypt/decrypt
path "transit/keys/myapp-encryption-key" {
  capabilities = ["deny"]
}
```

```bash
vault policy write transit-myapp transit-myapp.hcl
```

### 4.3. Политика для администратора

```hcl
# transit-admin.hcl
path "transit/keys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "transit/keys/myapp-encryption-key/rotate" {
  capabilities = ["create", "update"]
}

path "transit/keys/myapp-encryption-key/backup" {
  capabilities = ["read"]
}

path "transit/keys/myapp-encryption-key/restore" {
  capabilities = ["create", "update"]
}

path "transit/keys/myapp-encryption-key/config" {
  capabilities = ["update"]
}
```

> **Dev vs Production:** в dev можно разрешить приложению `transit/keys/*/read` для отладки. В production — приложение имеет права только на `encrypt` и `decrypt`, ротацию и backup делает только администратор.

---

## 5. Backup и Disaster Recovery

Transit-ключи — это критическая инфраструктура. Если ключи потеряны — все зашифрованные данные станут мусором.

### 5.1. Backup ключей

```bash
# Бекап всех ключей (требует sudo)
vault list transit/keys
for key in $(vault list transit/keys | tail -n+3); do
  vault read -format=json transit/keys/$key/backup \
    > "/backup/transit-$key-$(date +%Y%m%d).json"
done
```

### 5.2. Восстановление

```bash
vault write transit/keys/myapp-encryption-key/restore \
  backup=@/backup/transit-myapp-encryption-key-20260604.json
```

### 5.3. Стратегия backup

| Компонент | Частота | Хранение |
|---|---|---|
| Transit key backup | После каждой ротации | Encrypted S3 + офлайн |
| Vault Raft snapshot | Ежечасно | S3 + второй регион |
| Root key (Shamir) | Один раз | Сейф + физический носитель |

> ☠️ **Осторожно:** без backup Transit-ключей вы не сможете расшифровать данные, если Vault будет переустановлен или данные потеряны. Это необратимая потеря данных — никакой support не поможет.

---

## Типичные ошибки

- ❌ **Plaintext не в base64** — Vault возвращает ошибку `invalid base64`. Привыкайте: любой plaintext → base64 → Vault → шифрование. На приёме: Vault → base64 → decode.

- ❌ **Transit ≠ шифрование в покое** — данные не хранятся в Vault. Если приложение потеряет ciphertext — данные потеряны безвозвратно. Transit — это шифрование на лету (encryption in motion), не путайте с KV.

- ❌ **Ротация не перешифровывает старые данные** — после `rotate` ciphertext версии 1 всё ещё расшифровываются ключом v1. Если нужно, чтобы все данные были под новой версией — запустите `rewrap` для каждого ciphertext или фоновый batch-rewrap.

- ❌ **Key exportable=true в production** — если кто-то экспортирует ключ, он сможет расшифровать любые данные вне Vault. В production `exportable` должен быть только `false`.

- ❌ **Не настроена ротация ключей** — если один ключ шифрует терабайты данных годами, при компрометации ключа все данные скомпрометированы. Настройте `auto_rotate_period` или ручную ротацию раз в 90 дней.

- ❌ **Забыли сделать backup ключа** — потеря ключа = потеря всех данных, зашифрованных этим ключом. Backup должен быть после каждой ротации и храниться отдельно от Vault.

---

## Чек-лист

- [ ] Я создал отдельный Transit-ключ для каждого типа данных (PII, payment, credentials) с `exportable=false` и `deletion_allowed=false`.
- [ ] Приложение отправляет plaintext в base64 и не имеет доступа к материалу ключа — политика разрешает только `encrypt`/`decrypt`.
- [ ] Настроена регулярная ротация ключей (auto_rotate или скрипт) и backup ключей после каждой ротации.

---

## Попробуйте сами

1. **Настройте Transit и зашифруйте/расшифруйте данные.** Включите `transit` engine. Создайте ключ `myapp-encryption-key`. Зашифруйте строку `"super-secret-password"` (не забудьте base64). Расшифруйте ciphertext, убедитесь что получили исходную строку.

2. **Проверьте, что ключ не покидает Vault.** Попробуйте `vault read transit/keys/myapp-encryption-key` — убедитесь, что поле `keys` показывает `hmac-key` и `ciphertext` metadata, но не материал ключа. Теперь создайте ключ с `exportable=true` и выполните `vault read -field=exportable transit/keys/exported-key` — убедитесь, что разница только в флаге, но ключ всё равно нельзя прочитать без `/export` endpoint.

3. **Протестируйте ротацию и rewrap.** Создайте ключ, зашифруйте `"data1"` (получите `ct1`). Выполните `rotate`. Зашифруйте `"data2"` (получите `ct2`). Убедитесь, что оба ciphertext расшифровываются. Теперь выполните `rewrap` для `ct1` — получите `ct1-rewrapped`. Убедитесь, что `ct1-rewrapped` расшифровывается в `"data1"`. Установите `min_decryption_version=2` — убедитесь, что `ct1` (версия 1) больше не расшифровывается.
