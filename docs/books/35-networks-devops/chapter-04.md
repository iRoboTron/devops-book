# Глава 4: DNS — от запроса до ответа

## Что вы узнаете

- как работает DNS-разрешение от браузера до авторитарного сервера;
- какие бывают DNS-записи и что они означают;
- как использовать `dig` для диагностики DNS;
- как устроен `/etc/resolv.conf` и `/etc/hosts`.

**Цель главы:** когда «имя не резолвится» — вы знаете, где искать за 2 минуты.

---

## Схема 5 — полный DNS-запрос

```
Браузер         Резолвер          Root NS       TLD NS         Auth NS
  │                │                 │              │               │
  │─ api.example.com? ─►│            │              │               │
  │               │─ api.example.com? ─►│           │               │
  │               │     │◄─ .com NS ──┘             │               │
  │               │─────────────── api.example.com? ─►│             │
  │               │               │  │◄─ example.com NS ─────────── │
  │               │───────────────────────── api.example.com? ──────►│
  │               │◄──────────────────────── 93.184.216.34 ──────────┘
  │◄─ 93.184.216.34 ──┘
```

1. Браузер спрашивает у системного резолвера: «где `api.example.com`?»
2. Резолвер не знает → идёт к корневому (root) NS-серверу.
3. Root отвечает: «спроси у `.com` TLD, вот его NS».
4. Резолвер идёт к TLD-серверу `.com`.
5. TLD отвечает: «спроси у `example.com` — вот его авторитарные NS».
6. Резолвер идёт к авторитарному NS `example.com`.
7. Auth NS возвращает A-запись: `93.184.216.34`.
8. Резолвер кэширует и отдаёт ответ браузеру.

---

## 4.1 Как работает рекурсивный резолвер

Рекурсивный резолвер — это DNS-сервер, который выполняет всю цепочку запросов от имени клиента. Он начинает с корневых NS-серверов, затем идёт к TLD, затем к авторитарному — и возвращает готовый ответ.

**Локальный резолвер** (stub resolver) — это библиотека в ОС (например, `glibc` или `systemd-resolved`), которая отправляет запросы рекурсивному резолверу. Она не ходит по цепочке сама — она просто шлёт вопрос upstream.

```
┌─────────────┐   запрос    ┌────────────────┐   рекурсия    ┌──────────────┐
│  Приложение  │ ──────────► │  Stub resolver  │ ────────────► │  Recursive   │
│  (браузер)   │ ◄────────── │  (libc/resolved)│ ◄──────────── │  resolver    │
└─────────────┘   ответ     └────────────────┘               │  8.8.8.8     │
                                                              └──────────────┘
```

### Кэширование и TTL

Каждая DNS-запись имеет TTL (Time To Live) — время в секундах, в течение которого резолвер может хранить запись в кэше.

```
example.com.  3600  IN  A  93.184.216.34
              ↑ TTL = 3600 секунд = 1 час
```

- **Пока TTL не истёк** — резолвер отвечает из кэша, мгновенно.
- **После истечения TTL** — резолвер повторяет запрос upstream.
- **NS-записи кэшируются отдельно** и обычно с бóльшим TTL (сутки-двое).

> ☠️ **Осторожно:** Если вы изменили A-запись у провайдера DNS, старый IP будет в кэше резолверов по всему миру, пока не истечёт TTL. Перед сменой IP всегда уменьшайте TTL до 60–300 секунд за 48 часов до миграции.

---

## 4.2 Типы DNS-записей

| Тип  | Назначение                          | Пример                              |
|------|--------------------------------------|--------------------------------------|
| A    | IPv4-адрес хоста                     | `api.example.com.  A  93.184.216.34` |
| AAAA | IPv6-адрес хоста                     | `api.example.com.  AAAA  2606:2800:...` |
| CNAME| Каноническое имя (алиас)             | `www.example.com.  CNAME  example.com.` |
| MX   | Почтовый сервер домена (с priority)  | `example.com.  MX  10  mail.example.com.` |
| TXT  | Произвольный текст (SPF, DKIM, DMARC)| `example.com.  TXT  "v=spf1 include:_spf.google.com"` |
| NS   | Авторитарный сервер имён             | `example.com.  NS  ns1.example.com.` |
| PTR  | Обратная запись (IP → имя)          | `34.216.184.93.in-addr.arpa.  PTR  example.com.` |
| SOA  | Start of Authority — параметры зоны  | (см. ниже)                           |
| SRV  | Сервис-специфическая запись          | `_sip._tcp.example.com.  SRV  10 60 5060 sip.example.com.` |

### SOA-запись (пример)

```
example.com.  3600  IN  SOA  ns1.example.com. admin.example.com. (
                2026010101  ; serial
                7200        ; refresh (2h)
                3600        ; retry (1h)
                1209600     ; expire (2w)
                3600        ; minimum TTL (1h)
)
```

- **serial** — номер версии зоны (инкремент при изменениях);
- **refresh** — как часто slave проверяет обновления;
- **retry** — через сколько повторять при неудаче;
- **expire** — через сколько slave перестаёт отвечать, если не смог обновить зону.

---

## 4.3 dig — основной инструмент диагностики DNS

`dig` (Domain Information Groper) — стандартный DNS-клиент для Linux/macOS.

### Простейший запрос

```bash
dig example.com
```

Вывод:

```
; <<>> DiG 9.18.28-1~deb12u2-Debian <<>> example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 65468

;; QUESTION SECTION:
;example.com.                   IN      A

;; ANSWER SECTION:
example.com.            3600    IN      A       93.184.216.34

;; Query time: 12 msec
;; SERVER: 127.0.0.53#53(127.0.0.53) (UDP)
;; WHEN: Thu Jan 01 12:00:00 MSK 2026
;; MSG SIZE  rcvd: 56
```

### Разбор секций вывода

| Секция         | Что содержит                                                |
|----------------|-------------------------------------------------------------|
| QUESTION       | что спросили (домен, тип записи, класс IN)                  |
| ANSWER         | ответ — запрошенные записи                                  |
| AUTHORITY      | NS-серверы, которые могут авторитетно ответить по домену    |
| ADDITIONAL     | дополнительные записи (часто A/AAAA для NS)                 |
| Stats          | Query time, SERVER, WHEN, MSG SIZE                          |

### Полезные варианты

```bash
# Только IP-адрес
dig +short example.com

# Конкретный тип записи
dig example.com MX
dig example.com TXT
dig example.com NS
dig example.com AAAA

# Запрос к конкретному DNS-серверу
dig @8.8.8.8 example.com

# Обратный просмотр (PTR)
dig -x 8.8.8.8

# Трассировка полной цепочки (как в схеме выше)
dig +trace example.com

# Показать TTL каждой записи
dig +ttlid example.com
```

### Разбор ключевой строки ответа

```
example.com.            3600    IN      A       93.184.216.34
```

| Поле            | Значение                  |
|-----------------|---------------------------|
| `example.com.`  | Полное доменное имя (FQDN)|
| `3600`          | TTL в секундах = 1 час    |
| `IN`            | Класс — Internet          |
| `A`             | Тип записи                |
| `93.184.216.34` | Значение                  |

### Секция статистики

```
;; Query time: 12 msec        ← сколько времени занял запрос
;; SERVER: 127.0.0.53#53      ← какой сервер ответил (локальный)
;; WHEN: ...                  ← время запроса
;; MSG SIZE  rcvd: 56         ← размер ответа в байтах
```

> Если Query time = 0 msec — ответ пришёл из локального кэша.

---

## 4.4 /etc/resolv.conf и /etc/hosts

### /etc/resolv.conf

Файл, который указывает, какие DNS-серверы использовать:

```bash
cat /etc/resolv.conf
```

```
nameserver 127.0.0.53
options edns0 trust-ad
search example.com
```

- **nameserver** — IP-адрес DNS-сервера (до 3 штук);
- **search** — домены для поиска, если имя не FQDN (например, `ping api` → `ping api.example.com`);
- **options** — настройки: timeout, attempts, rotate, edns0.

> ☠️ **Осторожно:** Во многих современных дистрибутивах `/etc/resolv.conf` — это симлинк на файл, управляемый `systemd-resolved` или NetworkManager. Прямое редактирование может быть перезаписано.

```bash
ls -la /etc/resolv.conf
# lrwxrwxrwx 1 root root 39 ... /etc/resolv.conf -> ../run/systemd/resolve/stub-resolv.conf
```

### /etc/hosts

Локальная таблица соответствия имён IP-адресам — проверяется ДО DNS:

```bash
cat /etc/hosts
```

```
127.0.0.1       localhost
127.0.1.1       myhost
93.184.216.34   example.com

# IPv6
::1             ip6-localhost ip6-loopback
fe00::0         ip6-localnet
```

Приоритет определяется в `/etc/nsswitch.conf`:

```bash
grep ^hosts /etc/nsswitch.conf
```

```
hosts:          files dns
```

- `files` — сначала `/etc/hosts`;
- `dns` — потом DNS-запрос.

> Если в `/etc/hosts` есть запись — DNS даже не будет опрошен.

---

## 4.5 systemd-resolved

`systemd-resolved` — современный DNS-стек в systemd-дистрибутивах. Он работает как локальный DNS-прокси (stub resolver на 127.0.0.53).

### Основные команды

```bash
# Статус и текущие DNS-серверы
resolvectl status

# Статистика кэша
resolvectl statistics

# Очистить кэш
sudo resolvectl flush-caches

# Посмотреть DNS-сервер для конкретного интерфейса
resolvectl dns

# Установить DNS-сервер для интерфейса
sudo resolvectl dns eth0 8.8.8.8 1.1.1.1

# Выполнить DNS-запрос через systemd-resolved
resolvectl query example.com
```

Пример вывода `resolvectl statistics`:

```
DNSSEC supported by current servers: no
Transactions
Current Transactions: 0
  Total Transactions: 1569
  Cache
    Current Cache Size: 78
          Cache Hits: 487
        Cache Misses: 1082
```

---

## 4.6 nslookup — простая альтернатива

`nslookup` проще, но считается устаревшим. Тем не менее он всё ещё широко используется:

```bash
nslookup example.com
nslookup example.com 8.8.8.8
```

Для быстрой проверки сгодится, но для серьёзной диагностики используйте `dig`.

---

## Типичные ошибки

### 1. NXDOMAIN vs SERVFAIL vs REFUSED

| Статус      | Что значит                                                   |
|-------------|--------------------------------------------------------------|
| NOERROR     | Запись найдена                                               |
| NXDOMAIN    | Домен НЕ существует (опечатка в имени)                       |
| SERVFAIL    | Сервер не смог обработать (проблема у upstream/авторитарного)|
| REFUSED     | Сервер отказал (нет прав на зону, ACL)                       |

### 2. TTL после изменения записи

Изменили A-запись, а старый IP всё ещё приходит → кэш на клиенте или резолвере. Ждите TTL или используйте `dig @8.8.8.8` для обхода локального кэша.

### 3. /etc/resolv.conf в контейнере

В Docker контейнере `/etc/resolv.conf` генерируется автоматически из `/etc/docker/daemon.json` или опций `--dns`. Ручное редактирование внутри контейнера перезапишется при перезапуске.

### 4. CNAME и TTL

`dig example.com` возвращает CNAME, но не показывает A-запись, если не добавить `+short` или не указать тип. CNAME не может сосуществовать с другими записями того же имени.

---

## Чек-лист

- [ ] `dig +trace <домен>` — показывает полный путь разрешения;
- [ ] `dig @8.8.8.8 <домен>` — обходит локальный кэш;
- [ ] `cat /etc/resolv.conf` — какой сервер используется;
- [ ] `resolvectl statistics` — сколько попаданий в кэш.

---

## Попробуйте сами

**Задание 1. Трассировка Google**

```bash
dig +trace google.com
```

Проследите цепочку: корневые NS → TLD `.com` → авторитарные NS `google.com` → A-запись. Обратите внимание на AUTHORITY и ADDITIONAL секции.

**Задание 2. Сравнение времени ответа**

```bash
# Локальный резолвер
dig example.com | grep "Query time"

# Публичный DNS
dig @8.8.8.8 example.com | grep "Query time"
```

Повторите 3 раза. Какой быстрее? Попробуйте `@1.1.1.1` и `@9.9.9.9`.

**Задание 3. /etc/hosts vs DNS**

```bash
# Добавьте в /etc/hosts
echo "127.0.0.1   test-local.example.com" | sudo tee -a /etc/hosts

# Проверьте
ping -c 1 test-local.example.com
dig test-local.example.com
```

Почему `ping` идёт на 127.0.0.1, а `dig` показывает другой адрес (или NXDOMAIN)?
