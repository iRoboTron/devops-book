# Глава 3: pg_hba.conf, SSL и безопасное подключение

## Что вы узнаете

- как работает pg_hba.conf: порядок правил, типы соединений, методы аутентификации;
- как настроить SSL для шифрования соединений;
- как ограничить доступ к PostgreSQL по IP и методу;
- типичные ошибки подключения и их диагностика.

**Цель главы:** PostgreSQL принимает соединения только от доверенных клиентов, пароли не передаются в открытом виде. Никаких `trust`, никакого `listen_addresses = '*'` без пароля.

---

## 1. Как работает pg_hba.conf

Файл `pg_hba.conf` (Host-Based Authentication) — это firewall подключений к PostgreSQL. Он лежит в `$PGDATA/pg_hba.conf`. Типичный путь:

```
/etc/postgresql/16/main/pg_hba.conf   # нативная установка
/var/lib/postgresql/data/pg_hba.conf  # Docker / pg_basebackup
```

PostgreSQL проверяет правила **сверху вниз** и применяет **первое совпавшее**. Если ни одно правило не подошло — соединение отклоняется.

Формат строки:

```
# TYPE  DATABASE  USER      ADDRESS         METHOD
```

### 1.1. Типы соединений (TYPE)

| Тип | Описание |
|-----|----------|
| `local` | Unix-сокет (соединение с той же машины без TCP) |
| `host` | TCP/IP-соединение (с SSL или без) |
| `hostssl` | Только SSL-соединение |
| `hostnossl` | Только без SSL |

`local` и `host` — разные каналы. Если приложение подключается через `host`, правило `local` на него не действует, и наоборот.

### 1.2. Методы аутентификации (METHOD)

| Метод | Безопасность | Когда использовать |
|-------|-------------|-------------------|
| `trust` | Нулевая | Только localhost для отладки |
| `peer` | Высокая | Только local — OS user = PG user |
| `scram-sha-256` | Высокая | Production, парольная аутентификация |
| `md5` | Низкая | Устарел, только для совместимости со старыми клиентами |
| `reject` | — | Явный запрет (хорошая практика — закрыть всё в конце) |
| `cert` | Высокая | Аутентификация по SSL-сертификату |
| `pam` | Средняя | Интеграция с PAM системы |
| `ldap` | Высокая | Интеграция с LDAP/AD |

**scram-sha-256** — современный стандарт (PostgreSQL 10+). Пароль не передаётся по сети даже в зашифрованном виде — только salted challenge-response. `md5` устарел и небезопасен.

**trust** — пускает без пароля любого кто достучался. Никогда не использовать в production.

> ☠️ **Осторожно:** `trust` в правиле `host all all 0.0.0.0/0 trust` открывает PostgreSQL всему миру без пароля. Это одна из самых частых причин взлома PostgreSQL.

### 1.3. DATABASE и USER

В полях DATABASE и USER можно указывать:
- конкретное имя: `myapp`, `appuser`;
- `all` — все базы / все пользователи;
- `replication` — только соединения для репликации;
- `@filename` — список из внешнего файла (например, `@users.txt`);
- `sameuser` — только если имя пользователя совпадает с именем БД.

### 1.4. ADDRESS

Формат: `IP-адрес/маска`. Примеры:

```
127.0.0.1/32          # только localhost
192.168.1.0/24        # вся подсеть 192.168.1.x
10.0.0.0/8            # подсеть 10.x.x.x
0.0.0.0/0             # любой IPv4
::1/128               # IPv6 localhost
```

### 1.5. Примеры конфигураций

**Минимальная production-конфигурация:**

```text
# /etc/postgresql/16/main/pg_hba.conf

# Администратор через Unix-сокет — peer
local   all             postgres                          peer

# Приложение — только с разрешённых IP
host    myapp           appuser         192.168.1.0/24    scram-sha-256

# Только localhost
host    all             all             127.0.0.1/32      scram-sha-256
host    all             all             ::1/128           scram-sha-256

# Репликация (отдельное правило!)
host    replication     replicator      192.168.1.0/24    scram-sha-256

# Запретить всё остальное
host    all             all             0.0.0.0/0         reject
host    all             all             ::/0              reject
```

**Docker-окружение (только localhost внутри контейнера):**

```text
# pg_hba.conf для Docker
local   all             all                               trust
host    all             all             127.0.0.1/32      scram-sha-256
host    all             all             ::1/128           scram-sha-256
host    all             all             172.17.0.0/16     scram-sha-256
```

**Баланс безопасности и удобства (staging):**

```text
# pg_hba.conf для staging
local   all             all                               peer
host    myapp           appuser         10.0.0.0/8        scram-sha-256
host    myapp           readonly        10.0.0.0/8        scram-sha-256
host    all             postgres        10.0.0.0/8        scram-sha-256
host    all             all             all                reject
```

### 1.6. Перезагрузка после изменений

После любого изменения `pg_hba.conf` нужно перезагрузить конфигурацию — **не перезапускать** PostgreSQL:

```bash
# Правильно — reload (применяет pg_hba.conf и sighup-параметры)
sudo systemctl reload postgresql

# Или из psql (не требует sudo):
SELECT pg_reload_conf();
```

```bash
# Неправильно — restart (разрывает все соединения)
sudo systemctl restart postgresql   # только если меняли параметры restart-группы
```

Проверить что PostgreSQL применил правила:

```sql
-- Список текущих правил (PostgreSQL 10+)
SELECT rulename, database, user_name, address, auth_method
FROM pg_hba_file_rules;

-- Если pg_hba_file_rules пуст — синтаксическая ошибка в pg_hba.conf
```

> ☠️ **Осторожно:** Если сделать синтаксическую ошибку в `pg_hba.conf` и выполнить `reload` — PostgreSQL не применит изменения, но продолжит работать со старыми правилами. Ошибка будет в логе: `LOG: invalid pg_hba.conf file, not reloading`. Всегда проверяйте `pg_hba_file_rules` после reload.

---

## 2. listen_addresses — какие IP слушает PostgreSQL

Параметр в `postgresql.conf` определяет на каких сетевых интерфейсах PostgreSQL принимает TCP-соединения. По умолчанию — `localhost`.

```ini
# /etc/postgresql/16/main/postgresql.conf

listen_addresses = 'localhost'              # только localhost (безопасно)
# listen_addresses = '*'                    # все интерфейсы
# listen_addresses = '192.168.1.10,127.0.0.1'  # конкретные IP
```

Правило безопасности: `listen_addresses = '*'` **обязательно** сопровождать pg_hba.conf с `host ... all ... reject` в конце. Без этого PostgreSQL будет слушать на всех интерфейсах, включая публичные.

Проверить текущие адреса:

```sql
SHOW listen_addresses;
```

И снаружи:

```bash
ss -tlnp | grep 5432
# LISTEN 0 200 127.0.0.1:5432    ← только localhost
# LISTEN 0 200 0.0.0.0:5432      ← все интерфейсы
```

---

## 3. SSL — шифрование соединений

PostgreSQL передаёт данные по сети без шифрования, если не включён SSL. В production SSL обязателен — даже внутри приватной сети.

### 3.1. Включение SSL

PostgreSQL 14+ включает SSL автоматически при наличии сертификатов в `$PGDATA/`. Проверить:

```bash
ls -la $PGDATA/server.{crt,key}
# -rw------- 1 postgres postgres  ... server.crt
# -rw------- 1 postgres postgres  ... server.key
```

Если файлов нет — нужно создать self-signed сертификат для тестирования или получить от CA.

### 3.2. Создание self-signed сертификата

Для разработки и staging — self-signed сертификат:

```bash
# Создать сертификат на 365 дней
openssl req -new -x509 -days 365 -nodes \
  -out /var/lib/postgresql/16/main/server.crt \
  -keyout /var/lib/postgresql/16/main/server.key \
  -subj "/CN=mypostgres"

# Права — строго 600, владелец postgres
chmod 600 /var/lib/postgresql/16/main/server.key
chmod 600 /var/lib/postgresql/16/main/server.crt
chown postgres: /var/lib/postgresql/16/main/server.{crt,key}
```

### 3.3. Настройка postgresql.conf

```ini
# /etc/postgresql/16/main/postgresql.conf

ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
# ssl_ca_file = 'root.crt'          # для взаимной аутентификации
# ssl_ciphers = 'HIGH:MEDIUM:!3DES:!aNULL'  # стойкие шифры
```

### 3.4. Принудительный SSL через pg_hba.conf

Лучшая практика: `hostssl` для продакшен-трафика, `hostnossl` → `reject` для всего что без SSL.

```text
# /etc/postgresql/16/main/pg_hba.conf

# Приложение — только через SSL
hostssl  myapp   appuser   192.168.1.0/24   scram-sha-256

# Всё без SSL — запрещено
hostnossl all     all        0.0.0.0/0        reject
hostnossl all     all        ::/0             reject
```

Теперь любой клиент без SSL получит ошибку `FATAL: SSL connection is required`.

### 3.5. Проверка SSL

Со стороны сервера:

```sql
-- Какие соединения идут по SSL
SELECT pid, ssl, sslversion, sslbits
FROM pg_stat_ssl
JOIN pg_stat_activity USING (pid);
```

Со стороны клиента:

```bash
# Принудительно SSL
psql "host=myserver dbname=myapp user=appuser sslmode=require"

# Проверка сертификата
psql "host=myserver dbname=myapp user=appuser sslmode=verify-full sslrootcert=/path/to/ca.crt"
```

Режимы `sslmode`:

| Режим | Защита | Описание |
|-------|--------|---------|
| `disable` | Нет | Не использовать SSL |
| `allow` | Низкая | Попробовать SSL, но можно без |
| `prefer` | Низкая | SSL предпочтителен (по умолчанию) |
| `require` | Шифрование | SSL обязателен, сертификат сервера не проверяется |
| `verify-ca` | Проверка | SSL + проверка что сертификат подписан CA |
| `verify-full` | Полная | SSL + проверка что CN соответствует hostname |

В production внутри приватной сети достаточно `sslmode=require`. Если PostgreSQL доступен из интернета — `sslmode=verify-full` с корректным CA.

---

## 4. Диагностика ошибок подключения

### Ошибка 1: no pg_hba.conf entry

```
FATAL: no pg_hba.conf entry for host "192.168.100.50", user "appuser", database "myapp"
```

**Причина:** ни одно правило в pg_hba.conf не подходит под этот IP + пользователь + БД.

**Диагностика:**

```bash
# Проверить какие правила сейчас активны
sudo -u postgres psql -c "SELECT * FROM pg_hba_file_rules;"

# Убедиться что порядок правил корректен — специфичные выше общих
```

**Решение:** добавить правило в pg_hba.conf:

```text
host myapp appuser 192.168.100.0/24 scram-sha-256
```

Проверить нет ли в конце файла `host all all 0.0.0.0/0 reject` — это нормально, но до этого правила должно быть разрешающее для нужного IP.

### Ошибка 2: password authentication failed

```
FATAL: password authentication failed for user "appuser"
```

**Причина:** неверный пароль ИЛИ несовпадение метода аутентификации.

**Диагностика:**

1. Проверить метод в pg_hba.conf для этого соединения
2. Если метод `scram-sha-256`, а пароль задан в md5-формате — ошибка
3. Если метод `md5`, а пароль задан как scram-sha-256 — тоже ошибка

```bash
# Проверить какой метод будет применён для этого соединения
# (мысленно пройти по правилам сверху вниз)
```

**Решение:**

```sql
-- Сменить пароль с явным указанием метода
ALTER USER appuser WITH PASSWORD 'CorrectPassword456';
```

PostgreSQL 16 по умолчанию хранит пароль в scram-sha-256. Если метод в pg_hba.conf — `scram-sha-256`, а пароль старый (md5), то:

```sql
-- Принудительно пересоздать пароль в scram-sha-256
SET password_encryption = 'scram-sha-256';
ALTER USER appuser WITH PASSWORD 'CorrectPassword456';
```

### Ошибка 3: role does not exist

```
FATAL: role "appuser" does not exist
```

**Причина:** пользователь не создан в PostgreSQL.

**Решение:**

```sql
CREATE USER appuser WITH PASSWORD 'StrongPass123';
```

Проверить что пользователь создан:

```sql
\du
-- или
SELECT rolname FROM pg_roles;
```

### Ошибка 4: SSL connection is required

```
FATAL: SSL connection is required. Set sslmode=require in your connection string.
```

**Причина:** в pg_hba.conf стоит `hostssl`, клиент подключается без SSL.

**Решение:** добавить `sslmode=require` в строку подключения:

```bash
psql "host=myserver dbname=myapp user=appuser sslmode=require"
```

Или в URI:

```
postgresql://appuser:pass@myserver:5432/myapp?sslmode=require
```

### Ошибка 5: connection refused

```
could not connect to server: Connection refused
Is the server running on host "myserver" (192.168.1.10) and accepting
TCP/IP connections on port 5432?
```

**Причина:** PostgreSQL не слушает на этом IP/порту или фаервол блокирует порт.

**Диагностика:**

```bash
# На сервере — проверить какие адреса слушает
ss -tlnp | grep 5432

# Проверить listen_addresses
sudo -u postgres psql -c "SHOW listen_addresses;"

# Проверить port
sudo -u postgres psql -c "SHOW port;"

# На клиенте — проверить доступность порта
nc -zv myserver 5432
# или
telnet myserver 5432
```

**Решение:**

```ini
# postgresql.conf
listen_addresses = '192.168.1.10,127.0.0.1'
port = 5432
```

Если порт закрыт фаерволом:

```bash
# Открыть порт 5432 для доверенной подсети
sudo ufw allow from 192.168.0.0/16 to any port 5432 proto tcp
# или через iptables / security group в облаке
```

---

## 5. Комбинации: listen_addresses + pg_hba.conf + SSL

Типичная production-конфигурация:

```ini
# /etc/postgresql/16/main/postgresql.conf

listen_addresses = '10.0.0.10,127.0.0.1'
port = 5432

ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

```text
# /etc/postgresql/16/main/pg_hba.conf

# Админ — только Unix-сокет
local   all             postgres                          peer

# Внутренняя сеть — SSL + пароль
hostssl myapp           appuser         10.0.0.0/8       scram-sha-256

# Мониторинг — только localhost
host    all             monitoring      127.0.0.1/32     scram-sha-256

# Репликация — выделенный пользователь
hostssl replication     replicator      10.0.0.0/8       scram-sha-256

# Без SSL — запрещено
hostnossl all           all             0.0.0.0/0        reject
hostnossl all           all             ::/0             reject

# Всё что не подошло — reject
host    all             all             0.0.0.0/0        reject
host    all             all             ::/0             reject
```

Эта конфигурация:
- принимает соединения только на внутреннем IP и localhost;
- требует SSL для всех внешних подключений;
- пускает приложение только из подсети 10.0.0.0/8;
- явно запрещает всё остальное.

---

## Типичные ошибки

- `trust` для любого пользователя — любой кто достучался до порта 5432 может войти без пароля. Даже `trust` для `127.0.0.1` — плохая практика, если есть другие пользователи на сервере.
- Правило `host all all 0.0.0.0/0 scram-sha-256` открывает PostgreSQL всему интернету (если `listen_addresses = '*'`). Всегда ограничивать по IP или закрывать порт фаерволом.
- Порядок правил: более специфичные правила должны быть выше более общих. Если `reject` стоит раньше разрешающего правила — соединение будет отклонено.
- Забыть перезагрузить pg_hba.conf после изменений — старые правила продолжают действовать.
- Использовать `md5` вместо `scram-sha-256` — метод устарел, подвержен атакам по словарю.
- `host` и `local` — разные типы. Если настроен `host` для localhost, но клиент подключается через Unix-сокет — правило не сработает.
- Не проверять `pg_hba_file_rules` после reload — синтаксическая ошибка останется незамеченной до следующего reload.

---

## Чек-лист для самопроверки

- [ ] Понимаю формат строк pg_hba.conf и порядок применения правил (первое совпадение!)
- [ ] Знаю разницу между `md5`, `scram-sha-256` и `trust`, и почему `trust` опасен
- [ ] Умею включить SSL и требовать его через `hostssl` / `hostnossl reject`
- [ ] Знаю зачем нужен `listen_addresses` и чем `localhost` отличается от `*`
- [ ] Умею диагностировать 5 типичных ошибок подключения
- [ ] Знаю что `reload` ≠ `restart`, и когда что использовать
- [ ] Умею проверить активные правила через `pg_hba_file_rules`

---

## Попробуйте сами

1. Добавьте в pg_hba.conf правило `host myapp appuser 192.168.100.0/24 scram-sha-256`. Попробуйте подключиться с адреса не из этой подсети — должен быть отказ. Убедитесь что с нужного IP работает.

2. Настройте SSL на тестовом PostgreSQL. Подключитесь с `sslmode=require` — работает. С `sslmode=disable` — должен быть отказ (если настроен `hostnossl reject`). Проверьте `pg_stat_ssl` — видно что соединение по SSL.

3. Намеренно введите неверный пароль — запишите ошибку. Подключитесь с несуществующим пользователем — другая ошибка. Попробуйте подключиться к несуществующей БД — ещё одна. Умейте различать эти три случая без чтения документации.

4. Сделайте `listen_addresses = '*'` и проверьте `ss -tlnp | grep 5432` — видно `0.0.0.0:5432`. Закройте порт 5432 фаерволом и убедитесь что снаружи подключиться нельзя. Верните `listen_addresses = 'localhost'`.
