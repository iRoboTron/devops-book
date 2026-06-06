# Приложение D: Справочник pg_hba.conf

## Формат строки

```
# TYPE  DATABASE  USER  ADDRESS  METHOD  [OPTIONS]
```

Правила применяются сверху вниз. Первое совпадение определяет доступ. Если ни одно правило не подошло — доступ запрещён.

---

## TYPE (тип соединения)

| Значение | Описание |
|----------|----------|
| `local` | Unix-сокет (локальное соединение без TCP) |
| `host` | TCP/IP с SSL или без (в зависимости от настроек на клиенте) |
| `hostssl` | Только TCP/IP с обязательным SSL |
| `hostnossl` | Только TCP/IP без SSL |

---

## DATABASE (база данных)

| Значение | Описание |
|----------|----------|
| `all` | Все базы данных |
| `sameuser` | БД с именем, совпадающим с именем пользователя |
| `samegroup` | БД, чья группа совпадает с именем пользователя |
| `replication` | Соединения для streaming replication (WAL) |
| `имя_бд` | Конкретная база данных |
| `@file` | Список БД из файла |

---

## USER (пользователь)

| Значение | Описание |
|----------|----------|
| `all` | Все пользователи |
| `+group_name` | Все члены указанной группы (роли) |
| `имя_пользователя` | Конкретный пользователь |
| `@file` | Список пользователей из файла |

---

## ADDRESS (адрес)

| Формат | Пример | Описание |
|--------|--------|----------|
| `IPv4/mask` | `127.0.0.1/8` | IPv4 адрес или подсеть |
| `IPv6/mask` | `::1/128` | IPv6 адрес или подсеть |
| `.domain` | `.example.com` | Домен (обратное DNS-разрешение) |
| `0.0.0.0/0` | — | Все IPv4 адреса |
| `::0/0` | — | Все IPv6 адреса |
| `all` | — | Любой адрес (IPv4 + IPv6) |

Для `local` (Unix-сокет) параметр ADDRESS не указывается.

---

## METHOD (метод аутентификации)

| Метод | Описание | Когда использовать |
|-------|----------|-------------------|
| `trust` | Без пароля | Только localhost, тестовые окружения |
| `reject` | Явный запрет доступа | Завершать правила pg_hba.conf |
| `password` | Пароль в открытом виде | Никогда (устарел, небезопасен) |
| `md5` | MD5-хеш пароля | Устарел, но совместимость со старыми клиентами |
| `scram-sha-256` | Salted Challenge Response — современный стандарт | **Рекомендуется** для всех парольных соединений (PG 10+) |
| `peer` | Проверка OS user = PG user (только local) | Для локального администрирования |
| `cert` | Аутентификация по клиентскому SSL-сертификату | Высокозащищённые среды |

---

## OPTIONS (дополнительные параметры)

| Параметр | Описание |
|----------|----------|
| `clientcert=1` | Требовать клиентский SSL-сертификат (только с `hostssl`) |
| `clientname=1` | Использовать имя из сертификата вместо имени пользователя |
| `pamservice=name` | Использовать PAM-сервис |

---

## Примеры конфигураций

### 1. Разработка (локально)

```text
# TYPE  DATABASE  USER       ADDRESS        METHOD
local   all       postgres                  peer
local   all       all                       scram-sha-256
host    all       all        127.0.0.1/32   scram-sha-256
host    all       all        ::1/128        scram-sha-256
```

### 2. Production — приложения и мониторинг

```text
# TYPE  DATABASE     USER           ADDRESS        METHOD
local   all          postgres                      peer
host    myapp        appuser        10.0.1.0/24    scram-sha-256
host    myapp        readonly       10.0.2.0/24    scram-sha-256
host    replication  replicator     10.0.1.0/24    scram-sha-256
host    all          all            0.0.0.0/0      reject
```

### 3. Production + SSL только

```text
# TYPE  DATABASE     USER           ADDRESS        METHOD
local   all          postgres                      peer
hostssl myapp        appuser        10.0.1.0/24    scram-sha-256
hostssl myapp        readonly       10.0.2.0/24    scram-sha-256
hostssl replication  replicator     10.0.1.0/24    scram-sha-256
hostnossl all        all            0.0.0.0/0      reject
```

### 4. Аутентификация по сертификату

```text
# TYPE  DATABASE  USER       ADDRESS        METHOD           OPTIONS
local   all       postgres                 peer
hostssl all        all        10.0.0.0/8   cert             clientcert=1
hostnossl all      all        0.0.0.0/0    reject
```

---

## Проверка и перезагрузка

```sql
-- Посмотреть текущие правила (начиная с PG 10)
TABLE pg_hba_file_rules;

-- Перезагрузить после изменений
SELECT pg_reload_conf();
```

```bash
# Или через systemctl
sudo systemctl reload postgresql
```
