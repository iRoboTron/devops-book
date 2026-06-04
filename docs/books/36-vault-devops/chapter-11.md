# Глава 11: Production — Raft HA, Seal/Unseal, Backup

## Что вы узнаете

- Raft HA cluster: несколько нод для отказоустойчивости.
- Автоматический unseal при перезапуске.
- generate-root: восстановление утерянного root token.
- rekey: смена unseal keys.
- Резервное копирование и восстановление.
- DR: перенос Vault на другой сервер.
- Мониторинг Vault.

---

### Схема 5 — Seal/Unseal

```text
Vault запустился / перезагрузился
        │
        ▼
   [SEALED] ← данные зашифрованы, ничего не работает
        │
        │  vault operator unseal <key-1>
        │  vault operator unseal <key-2>
        │  vault operator unseal <key-3>  (threshold из N)
        ▼
  [UNSEALED] ← работает нормально
```

---

## 1. Raft HA

Vault использует Raft consensus protocol для синхронизации данных между нодами. Все ноды хранят полную копию данных, но пишет только leader.

### 1.1. Кворум

```text
3 ноды — терпит 1 сбой (quorum = 2)
5 нод  — терпит 2 сбоя (quorum = 3)

vault-1 (leader), vault-2 (standby), vault-3 (standby)
Потеря vault-1 → vault-2 становится leader
Потеря 2 нод → quorum потерян, Vault перестаёт отвечать
```

### 1.2. Инициализация кластера

Первая нода инициализируется как raft-лидер:

```bash
# На vault-1: инициализация и unseal
vault operator init -key-shares=5 -key-threshold=3
vault operator unseal <key-1>
vault operator unseal <key-2>
vault operator unseal <key-3>

# Запись конфига storage raft
```

```hcl
# vault-config.hcl (vault-1)
storage "raft" {
  path = "/opt/vault/data"
  node_id = "vault-1"

  retry_join {
    leader_api_addr = "http://vault-1:8200"
  }
  retry_join {
    leader_api_addr = "http://vault-2:8200"
  }
  retry_join {
    leader_api_addr = "http://vault-3:8200"
  }
}
```

### 1.3. Подключение follower нод

```bash
# На vault-2, vault-3: присоединяемся к кластеру
vault operator raft join http://vault-1:8200

# Unseal (теми же ключами)
vault operator unseal <key-1>
vault operator unseal <key-2>
vault operator unseal <key-3>
```

### 1.4. Проверка состояния кластера

```bash
# Список пиров
vault operator raft list-peers

# Пример вывода
Node      Address            State       Voter
vault-1   10.0.0.1:8200      leader      true
vault-2   10.0.0.2:8200      follower    true
vault-3   10.0.0.3:8200      follower    true
```

### 1.5. Failover

```text
При потере leader ноды:
1. Follower ноды обнаруживают отсутствие heartbeat (10s)
2. Запускается выборы нового leader
3. Новый leader выбирается через Raft consensus
4. Vault продолжает работать (unsealed, все данные доступны)

Время простоя: ~5-15 секунд (зависит от сетевой задержки)
```

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `retry_join` | Список нод для повторного подключения | — |
| `node_id` | Уникальный идентификатор ноды | hostname |
| `path` | Директория для хранения Raft данных | — |
| `performance_multiplier` | Множитель таймаутов (для медленных дисков) | 1 |

> ☠️ **Осторожно:** если потерян кворум (больше половины нод недоступны), Vault перестаёт отвечать на запросы. Восстановление требует ручного вмешательства через `raft remove-peer` или `raft restore`.

> **Dev vs Production:** в dev достаточно 1 ноды с Raft. В production — минимум 3 ноды, разнесённые по разным availability zones (AWS AZ, K8s node pools). Никогда не используй 2 ноды — при потере одной теряется кворум.

---

## 2. Recovery: generate-root

Если root token утерян (удалён, истёк, не сохранён), единственный способ восстановить доступ — generate-root.

### 2.1. Когда это нужно

- Root token не был сохранён после `vault operator init`.
- Root token удалён или истёк (по умолчанию root token не имеет TTL, но его можно изменить).
- Администратор с root token уволился и не передал токен.

### 2.2. Процесс generate-root

```bash
# Шаг 1: Инициализация generate-root
vault operator generate-root -init -otp

# Вывод:
# Nonce:      abc123...
# OTP:        xyz456...  ← одноразовый пароль для декодирования
# Started:    true

# Шаг 2: Каждый ключ-холдер (holder) вводит unseal key
vault operator generate-root \
  -nonce=abc123... \
  -otp=xyz456...

# Ответ: ключ-холдер вводит свой unseal key интерактивно.
# Или передать ключ аргументом (только скрипты):
vault operator generate-root \
  -nonce=abc123... \
  -otp=xyz456... \
  <unseal-key-1>

# Повторяем для каждого ключа, пока не наберётся threshold
# После threshold — получаем encoded root token
# Encoded Root Token:  AbCdEfGhIjKlMnOp...

# Шаг 3: Декодируем root token
vault operator generate-root \
  -nonce=abc123... \
  -otp=xyz456... \
  -decode="AbCdEfGhIjKlMnOp..."

# → Root Token восстановлен: hvs.xxx...
```

```text
Упрощённая схема generate-root:

    ┌──────────────┐
    │ Инициатор     │ vault operator generate-root -init -otp
    │ (админ)       │ → nonce + OTP
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ Holder 1     │ вводит unseal key (1 из 3)
    ├──────────────┤
    │ Holder 2     │ вводит unseal key (2 из 3) ← threshold
    ├──────────────┤
    │ Holder 3     │ не обязателен (уже собрали 3)
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ Инициатор     │ получает encoded token
    │               │ decode(encoded, OTP) → Root Token
    └──────────────┘
```

> ☠️ **Осторожно:** generate-root — единственный способ восстановить root token. Храни unseal keys в безопасном месте, физически разнесённом (разные сейфы, разные люди). Если unseal keys утеряны — данные Vault потеряны навсегда.

### 2.3. generate-root через PGP

```bash
# Вместо OTP можно использовать PGP
vault operator generate-root -init -pgp-key=admin@example.com.asc
vault operator generate-root -nonce=NONCE -pgp-key=admin@example.com.asc
# → Token зашифрован PGP-ключом
```

---

## 3. Rekey — смена unseal keys

Unseal keys должны регулярно меняться (рекомендуется раз в 6-12 месяцев или при компрометации ключа).

### 3.1. Когда нужен rekey

- Один из unseal key holders уволился.
- Unseal keys скомпрометированы (утечка, потеря носителя).
- Нужно изменить количество ключей или threshold.
- Регулярная ротация по политике безопасности.

### 3.2. Процесс rekey

```bash
# Шаг 1: Инициализация
vault operator rekey -init \
  -key-shares=5 \
  -key-threshold=3

# Вывод:
# Nonce:   def456...
# Started: true

# Шаг 2: Каждый ключ-холдер вводит СТАРЫЙ unseal key
vault operator rekey -nonce=def456...
# Ввод: старый unseal key
# ...
# После threshold — Vault генерирует НОВЫЕ unseal keys

# Шаг 3: Сохранить новые unseal keys
# Key 1: xxx...
# Key 2: yyy...
# Key 5: zzz...
```

### 3.3. Rekey с изменением threshold

```bash
# Было: 5 ключей, threshold 3
# Стало: 7 ключей, threshold 4
vault operator rekey -init \
  -key-shares=7 \
  -key-threshold=4
```

> **Dev vs Production:** в dev достаточно 1 ключа (key-shares=1, key-threshold=1). В production минимум 5 ключей с threshold 3 (или 7 с threshold 4). Ключи должны храниться у разных людей.

---

## 4. Backup и Restore

### 4.1. Snapshot (Raft)

```bash
# Создание снапшота
vault operator raft snapshot save \
  /tmp/vault-backup-$(date +%Y%m%d).snap

# Восстановление из снапшота
vault operator raft snapshot restore \
  -force /tmp/vault-backup-20260101.snap
```

| Флаг | Описание |
|------|----------|
| `-force` | Принудительное восстановление (замена всех данных) |
| `-output` | Запись в файл (для save) |
| `-retry` | Количество повторов при ошибке (для restore) |

### 4.2. Автоматизация backup

```bash
#!/bin/bash
# backup-vault.sh

BACKUP_DIR="/backups/vault"
DATE=$(date +%Y-%m-%d-%H%M)
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

# Snapshot
vault operator raft snapshot save \
  "$BACKUP_DIR/vault-$DATE.snap"

# Удаление старых бекапов
find "$BACKUP_DIR" -name "*.snap" -mtime +$KEEP_DAYS -delete

# Отправка в S3 (опционально)
aws s3 cp "$BACKUP_DIR/vault-$DATE.snap" \
  s3://my-bucket/vault-backups/
```

> ☠️ **Осторожно:** restore заменяет все данные Vault на данные из снапшота. Все изменения после создания снапшота будут потеряны. Перед restore убедись, что это действительно то, что нужно.

### 4.3. Разница snapshot vs физический backup

| Аспект | Raft snapshot | Физический backup (копия файлов) |
|--------|---------------|----------------------------------|
| Консистентность | Консистентные данные | Может быть неконсистентным |
| Скорость | Быстро (внутренний механизм Raft) | Медленно |
| Простота | Одна команда | Нужно остановить Vault |
| Кроссплатформенность | Переносится на другую ОС | Зависит от архитектуры |

---

## 5. DR: перенос Vault на другой сервер

Disaster Recovery — восстановление Vault на новом сервере (другая локация, другой облачный провайдер).

### 5.1. Полный перенос

```bash
# ===== Старый сервер =====
# 1. Создаём снапшот
vault operator raft snapshot save /tmp/vault-transfer.snap

# 2. Копируем на новый сервер
scp /tmp/vault-transfer.snap admin@new-server:/tmp/

# ===== Новый сервер =====
# 3. Устанавливаем Vault (та же версия!)
# apt install vault

# 4. Настраиваем storage raft
cat > /etc/vault.d/vault.hcl << 'EOF'
storage "raft" {
  path = "/opt/vault/data"
  node_id = "vault-dr-1"
}
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}
api_addr = "http://new-server:8200"
EOF

# 5. Запускаем Vault
systemctl start vault

# 6. Восстанавливаем из снапшота
vault operator raft snapshot restore -force \
  /tmp/vault-transfer.snap

# 7. Unseal (теми же unseal keys!)
vault operator unseal <key-1>
vault operator unseal <key-2>
vault operator unseal <key-3>
```

### 5.2. Что должно совпадать

| Элемент | Требование |
|---------|------------|
| Версия Vault | Одинаковая (минорные версии — обычно OK, мажорные — проверить changelog) |
| Unseal keys | Те же самые |
| Seal mechanism | Тот же (shamir / transit / cloud kms) |
| Конфигурация auth | Восстанавливается из снапшота |
| Конфигурация audit | Настроить заново (audit log не в снапшоте) |

> ☠️ **Осторожно:** unseal keys должны храниться отдельно от Vault. Если Vault и unseal keys находятся на одном сервере, злоумышленник получает доступ к зашифрованным данным. **Vault шифрует данные, но не защищает unseal keys.**

---

## 6. Auto-unseal через Transit

### 6.1. Как это работает

Вместо ручного ввода unseal keys при каждом перезапуске, Vault использует другой Vault (или облачный KMS) для автоматического unseal.

```text
┌──────────────┐     auto-unseal     ┌──────────────────┐
│ Vault nodes  │ ◄────────────────── │ Vault Primary     │
│ (dev-vault-1)│                    │ (vault-primary)    │
│ (dev-vault-2)│  запрос ключа      │ seal "transit"    │
│ (dev-vault-3)│  через API         │ key = "autounseal"│
└──────────────┘                    └──────────────────┘
```

### 6.2. Настройка Transit seal

```hcl
# На Vault Primary (vault-primary:8200)
# Включаем Transit engine
vault secrets enable transit

# Создаём ключ для auto-unseal
vault write -f transit/keys/autounseal-key

# Политика для сервисного токена
vault policy write autounseal-policy - <<EOF
path "transit/encrypt/autounseal-key" {
  capabilities = ["create", "update"]
}
path "transit/decrypt/autounseal-key" {
  capabilities = ["create", "update"]
}
EOF

# Создаём сервисный токен
vault token create -policy=autounseal-policy \
  -orphan=true -period=24h
```

```hcl
# На Vault nodes (dev-vault-1, 2, 3)
# /etc/vault.d/vault.hcl
seal "transit" {
  address     = "http://vault-primary:8200"
  token       = "hvs.SERVICE_TOKEN"
  key_name    = "autounseal-key"
  mount_path  = "transit/"
}
```

### 6.3. Инициализация с Transit seal

```bash
vault operator init -recovery-shares=5 -recovery-threshold=3
# No unseal keys! Только recovery keys (для смены конфигурации)

# Vault автоматически unseal через Transit
# При перезапуске не нужно вводить ключи
```

### 6.4. Seal backends сравнение

| Seal type | Описание | Unseal | Когда использовать |
|-----------|----------|--------|-------------------|
| Shamir | Unseal keys разделены между людьми | Ручной | Dev, small prod |
| Transit | Через другой Vault | Авто | Большой prod, HA |
| AWS KMS | Через Amazon KMS | Авто | AWS production |
| Azure Key Vault | Через Azure Key Vault | Авто | Azure production |
| GCP Cloud KMS | Через GCP KMS | Авто | GCP production |
| PKCS11 | HSM-модули | Авто | High-security ентерпрайз |

> **Dev vs Production:** в dev используй Shamir — проще, не требует внешней инфраструктуры. В production используй Auto-unseal (Transit / Cloud KMS) — при перезагрузке или масштабировании не нужно ждать админов с ключами.

> ☠️ **Осторожно:** при использовании Transit seal, если Vault Primary недоступен, Vault не сможет unseal после перезапуска. Делай Vault Primary тоже кластером из 3 нод.

---

## 7. Мониторинг Vault

### 7.1. Prometheus метрики

Vault предоставляет метрики в формате Prometheus:

```bash
curl http://vault:8200/v1/sys/metrics?format=prometheus
# Или если включен token:
curl -H "X-Vault-Token: hvs.xxx" \
  http://vault:8200/v1/sys/metrics?format=prometheus
```

### 7.2. Ключевые метрики

| Метрика | Описание | Alarm при |
|---------|----------|-----------|
| `vault_core_unsealed` | 1 = unsealed, 0 = sealed | `== 0` |
| `vault_core_leadership` | 1 = leader, 2 = standby | `== 3` (unknown) |
| `vault_expire_num_leases` | Количество активных lease | Рост без падения |
| `vault_raft_leader_last_contact` | Время с последнего контакта с leader | `> 5s` |
| `vault_raft_peers` | Количество пиров в кластере | Меньше ожидаемого |
| `vault_token_count` | Количество активных токенов | Рост без падения |
| `vault_audit_log_request_failure` | Ошибки записи audit log | `> 0` |

### 7.3. Пример Prometheus config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'vault'
    scrape_interval: 15s
    metrics_path: '/v1/sys/metrics'
    params:
      format: ['prometheus']
    scheme: http
    static_configs:
      - targets:
        - vault-1:8200
        - vault-2:8200
        - vault-3:8200
```

### 7.4. Пример правил алертов

```yaml
# vault-alerts.yml
groups:
  - name: vault
    rules:
      - alert: VaultSealed
        expr: vault_core_unsealed == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Vault {{ $labels.instance }} is sealed"

      - alert: VaultNoLeader
        expr: vault_core_leadership == 3
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Vault cluster has no leader"

      - alert: VaultRaftQuorumRisk
        expr: vault_raft_peers < 3
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Raft cluster has fewer than 3 peers"
```

### 7.5. Health check

```bash
# /v1/sys/health — возвращает HTTP status
curl -f http://vault:8200/v1/sys/health

# HTTP status по состоянию
# 200 — initialized, unsealed, active
# 429 — unsealed, standby
# 501 — not initialized
# 503 — sealed
```

### 7.6. Health check для load balancer

```yaml
# Пример health check для NLB / HAProxy
# Target: http://vault:8200/v1/sys/health
# Expect: HTTP 200 (для leader) или 429 (для standby)
# 
# AWS NLB: можно использовать custom health check
# с ожиданием кода 200 или 429
```

### 7.7. Структура лога Vault

```json
{
  "@level": "error",
  "@message": "error writing data: unexpected error",
  "@timestamp": "2026-01-15T10:30:00.000Z",
  "error": "connection refused",
  "source": "storage/raft"
}
```

| Уровень | Когда появляется |
|---------|------------------|
| `trace` | Детальная отладка (не включать в prod) |
| `debug` | Отладка запросов |
| `info` | Нормальная работа (init, seal/unseal, leader election) |
| `warn` | Потенциальная проблема (slow request) |
| `error` | Ошибка (failed request, storage error) |

---

## Типичные ошибки

- ❌ **Не делать backup** — если Raft кластер потеряет все ноды (пожар, кража, случайное удаление), данные Vault будут потеряны безвозвратно. Snapshot — это дешёвая страховка.

- ❌ **Хранить unseal keys на том же сервере** — если злоумышленник получит доступ к серверу, он получит и ключи, и зашифрованные данные. Unseal keys должны быть у разных людей, в разных сейфах или в менеджере паролей.

- ❌ **Не мониторить `vault_core_unsealed`** — если Vault перешёл в sealed state, приложения перестают получать секреты. Мониторинг sealed state — это базовая метрика, которая должна быть настроена первой.

- ❌ **Single point of failure (1 нода)** — одна нода Raft — это не HA. При любой проблеме (сеть, диск, обновление) Vault становится недоступен.

- ❌ **Ручной unseal в production** — при перезапуске кластера из 5 нод нужно ввести unseal keys 5 раз × 3 ключа = 15 операций. Используйте auto-unseal через Transit или Cloud KMS.

- ❌ **Игнорировать версию Vault при restore** — снапшот, сделанный в Vault 1.16, может не восстановиться в Vault 1.15. Всегда проверяйте совместимость версий.

- ❌ **Забыть про audit log при DR** — снапшот не содержит audit log. При переносе на другой сервер настройте audit заново и объедините с архивом audit log со старого сервера.

---

## Чек-лист

- [ ] Raft HA кластер: минимум 3 ноды (разные AZ / физические стойки), каждая настроена с `retry_join` на все остальные ноды. Проверено `vault operator raft list-peers` — все ноды в статусе `voter`.
- [ ] Auto-unseal настроен (Transit seal на Vault Primary или Cloud KMS). Vault автоматически unseal после перезапуска без ручного ввода ключей.
- [ ] Резервное копирование: ежедневный `vault operator raft snapshot save`, хранение минимум 30 дней, копия вне сервера (S3, другой дата-центр). Процедура restore протестирована.
- [ ] Мониторинг: Prometheus собирает метрики со всех нод. Алерты на `vault_core_unsealed == 0`, `vault_core_leadership == 3`, `vault_raft_peers < 3`. Health check настроен на `/v1/sys/health`.

---

## Попробуйте сами

1. **Соберите Raft кластер из 3 нод.** Запустите 3 инстанса Vault (через Docker Compose или отдельные процессы). Первую ноду инициализируйте, остальные подключите через `vault operator raft join`. Проверьте `vault operator raft list-peers`. Выключите leader ноду (kill процесс) — убедитесь, что standby стал leader. Поднимите ноду обратно — она вернётся как follower.

2. **Настройте Auto-unseal через Transit seal.** Запустите Vault Primary (с Shamir для простоты), включите Transit engine, создайте ключ `autounseal-key` и сервисный токен. Настройте второй Vault с `seal "transit"`. Инициализируйте второй Vault — убедитесь, что он unseal автоматически. Перезапустите второй Vault — проверьте, что unseal произошёл без ввода ключей.

3. **Сымитируйте Disaster Recovery.** Создайте снапшот (`vault operator raft snapshot save`), удалите все данные Vault (`rm -rf /opt/vault/data`), восстановите из снапшота (`vault operator raft snapshot restore`). Проверьте, что все секреты, политики и auth methods на месте.
