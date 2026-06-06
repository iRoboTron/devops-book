# Глава 7: Диагностика — ping, traceroute, mtr, ss, tcpdump, Wireshark

## Что вы узнаете

- как проверить доступность хоста и маршрут до него;
- как читать traceroute и mtr;
- как захватить трафик через tcpdump и анализировать в Wireshark;
- системный подход к диагностике.

**Цель главы:** видя проблему, знать какой инструмент взять на каждом шаге.

---

## 7.1 ping — базовая проверка

`ping` — первый инструмент, когда «не открывается сайт». Он отправляет ICMP Echo Request и ждёт Echo Reply.

> Если команды нет:
> ```bash
> sudo apt install iputils-ping
> ```

### Базовый пинг

```bash
ping 8.8.8.8
```

```
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=12.3 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=12.1 ms
64 bytes from 8.8.8.8: icmp_seq=3 ttl=118 time=12.5 ms
^C
--- 8.8.8.8 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2004ms
rtt min/avg/max/mdev = 12.087/12.300/12.500/0.169 ms
```

### Что значат поля

| Поле | Что это |
|------|---------|
| `icmp_seq=1` | Номер пакета |
| `ttl=118` | Time To Live — сколько хопов осталось (начальный 64/128/255, каждый роутер -1) |
| `time=12.3 ms` | Время туда-обратно (RTT) |

TTL позволяет угадать ОС:
- 64 — Linux
- 128 — Windows
- 255 — сетевые устройства (Cisco, Juniper)

### Пинг с ограничениями

```bash
# 4 пакета и выход
ping -c 4 google.com

# Быстрый пинг (каждые 0.2 сек)
ping -i 0.2 -c 20 google.com

# Крупные пакеты (тест MTU)
ping -s 1400 -c 3 google.com
```

### Что говорит ping

#### 100% loss

```
100% packet loss
```

- Хост не отвечает (выключен, фаервол блокирует ICMP);
- Нет маршрута;
- Неправильный IP.

> ☠️ **Осторожно:** Многие хосты блокируют ICMP. `ping` не отвечает ≠ сервис не работает. Всегда проверяйте и другим способом (curl, nc).

#### Высокий RTT

```
time=250 ms — 300 ms — 1200 ms
```

- Гео-удалённость (Сингапур → США = ~150-200 ms);
- Плохой канал (Wi-Fi с помехами, спутник);
- Перегрузка канала (jitter — разброс времени).

#### Jitter (джиттер)

Разница между соседними RTT. Если пакеты идут то 10 ms, то 500 ms — канал нестабилен. Видеозвонки и VoIP страдают в первую очередь.

```bash
# Чистая статистика RTT в конце вывода
ping -c 20 google.com | tail -1
```

```
rtt min/avg/max/mdev = 10.5/12.3/48.1/8.4 ms
```

`mdev` — mean deviation. Чем выше, тем больше jitter.

#### Нет DNS

```bash
ping nonexistent.example.com
```

```
ping: nonexistent.example.com: Temporary failure in name resolution
```

Проблема в DNS — проверяйте `/etc/resolv.conf` и `dig`.

---

## 7.2 traceroute — маршрут до хоста

`ping` говорит «доходит или нет». `traceroute` говорит **где** проблема — на каком хопе пакеты теряются или растёт задержка.

> Если команды нет:
> ```bash
> sudo apt install traceroute
> ```

### Как работает

```
┌─────┐ TTL=1 ┌─────┐ TTL=2 ┌─────┐ TTL=3 ┌──────┐
│ You │──────>│ R1  │──────>│ R2  │──────>│ Хост │
└─────┘       └─────┘       └─────┘       └──────┘
  ICMP          Time        Time            Echo
  Echo          Exceed      Exceed          Reply
```

1. Отправляет пакет с TTL=1 — первый роутер отбрасывает и шлёт `Time Exceeded`.
2. TTL=2 — второй роутер отвечает.
3. И так до цели.

### Базовое использование

```bash
traceroute google.com
```

```
traceroute to google.com (142.250.185.78), 30 hops max, 60 byte packets
 1  192.168.1.1 (192.168.1.1)  1.023 ms  1.044 ms  1.101 ms
 2  10.0.0.1 (10.0.0.1)  5.234 ms  5.112 ms  5.089 ms
 3  83.220.44.1 (83.220.44.1)  12.342 ms  12.455 ms  12.210 ms
 4  * * *
 5  72.14.215.134 (72.14.215.134)  48.123 ms  48.001 ms  47.889 ms
 ...
```

Каждая строка — один хоп (роутер). Три значения — три попытки измерения RTT.

### Варианты traceroute

```bash
# ICMP (по умолчанию UDP на Linux)
traceroute -I google.com

# TCP на конкретный порт (проходит через многие фаерволы)
sudo traceroute -T -p 443 google.com
```

- По умолчанию `traceroute` использует UDP на высоких портах.
- `-I` — ICMP (как ping).
- `-T -p 443` — TCP SYN на 443 порт (имитирует HTTPS). Часто единственное, что не блокируют фаерволы.

### Что означают `* * *`

```
4  * * *
```

Три звёздочки — роутер не ответил. Это **не обязательно проблема**:

- Роутер не шлёт ICMP Time Exceeded (настройки безопасности);
- Роутер перегружен;
- Пакет ушёл в никуда (тогда дальше тоже будут звёзды).

Смотрите на следующий хоп: если дальше пакеты идут — всё нормально, этот роутер просто «молчит».

### Задержка на хопе растёт

```
 5  72.14.215.134  48 ms  47 ms  49 ms
 6  216.239.43.112  142 ms  145 ms  141 ms
 7  142.250.225.129  148 ms  150 ms  147 ms
```

Резкий скачок задержки на хопе 6 — это, скорее всего, **спутниковый канал** или **межконтинентальный линк** (например, Европа → США). Не проблема, а физика.

---

## 7.3 mtr — traceroute в реальном времени

`mtr` (My TraceRoute) совмещает `ping` и `traceroute` — показывает каждый хоп и статистику потерь в реальном времени.

> Если команды нет:
> ```bash
> sudo apt install mtr
> ```

### Интерактивный режим

```bash
mtr google.com
```

```
                               My traceroute  [v0.95]
                                (140.142.0.2) -> (google.com)
 Keys:  Help   Display mode   Restart statistics   Order of fields   quit
                                          Packets               Pings
 Host                                   Loss%   Snt   Last   Avg  Best  Wrst StDev
 1. 192.168.1.1                         0.0%    10    1.2   1.1   0.9   1.5   0.2
 2. 10.0.0.1                            0.0%    10    5.1   5.3   4.9   5.8   0.3
 3. 83.220.44.1                         0.0%    10   12.3  12.5  11.9  13.1   0.4
 4. 72.14.215.134                      0.0%    10   48.0  48.2  47.5  49.1   0.5
 5. 216.239.43.112                     5.0%    10  150.2 151.1 148.3 155.2   2.1
 6. 142.250.225.129                   10.0%    10  152.0 152.3 151.0 154.0   1.1
```

### Что смотреть

| Столбец | Что |
|---------|-----|
| `Loss%` | Потеря пакетов на хопе (важно!) |
| `Last` | Последний RTT |
| `Avg` | Средний RTT |
| `Best/Wrst` | Лучший/худший |
| `StDev` | Стандартное отклонение (jitter) |

### Отчёт без интерактива

```bash
mtr --report --report-cycles 100 google.com
```

Отправит 100 пакетов на каждый хоп и выведит итоговую таблицу. Идеально для скриптов и быстрой диагностики.

### Когда mtr незаменим

- **Периодические потери:** ping показывает 0% loss, но сайт тормозит. mtr покажет 2-5% потерь на одном из хопов.
- **Выявление узкого места:** видно, на каком хопе скачок задержки и начинаются потери.
- **Спор с провайдером:** «На 4-м хопе 30% потерь — чините ваш upstream».

---

## 7.4 tcpdump — захват трафика

`tcpdump` — главный инструмент для захвата сетевого трафика в Linux. Работает на уровне пакетов.

> Если команды нет:
> ```bash
> sudo apt install tcpdump
> ```

### Первое правило: нужен sudo

```bash
sudo tcpdump -i eth0
```

Без `sudo` — `tcpdump: no suitable device found`.

### Синтаксис

```
sudo tcpdump [опции] -i <интерфейс> [фильтр]
```

### Базовые команды

```bash
# Весь трафик на интерфейсе (сырой — много!)
sudo tcpdump -i eth0

# Только пакеты с/на хост
sudo tcpdump -i eth0 host 8.8.8.8

# Только порт 80 (HTTP)
sudo tcpdump -i eth0 port 80

# Только порт 53 (DNS)
sudo tcpdump -i any port 53

# Вывод в ASCII (читабельно для HTTP)
sudo tcpdump -i eth0 -A port 80

# HEX + ASCII
sudo tcpdump -i eth0 -X port 80
```

### Фильтры BPF (Berkeley Packet Filter)

Фильтры — главная сила tcpdump. Комбинируйте:

```bash
# Трафик от хоста
sudo tcpdump -i eth0 src 192.168.1.100

# Трафик к хосту
sudo tcpdump -i eth0 dst 192.168.1.100

# И/Или
sudo tcpdump -i eth0 host 192.168.1.100 and port 443

# Не порт 22 (исключить SSH)
sudo tcpdump -i eth0 not port 22

# Сложный фильтр
sudo tcpdump -i eth0 'src 10.0.0.0/8 and (port 80 or port 443) and not dst 10.0.0.1'
```

### Сохранение в файл

```bash
# Запись (работает без лишнего вывода на экран)
sudo tcpdump -i eth0 -w /tmp/capture.pcap

# Чтение
tcpdump -r /tmp/capture.pcap

# Чтение с фильтром
tcpdump -r /tmp/capture.pcap host 8.8.8.8
```

- `-w` — запись в pcap (бинарный формат).
- `-r` — чтение pcap.

### Практические примеры

#### HTTP-запрос целиком

```bash
# Терминал 1: захват
sudo tcpdump -i any port 80 -A

# Терминал 2: запрос
curl http://example.com
```

В выводе увидите `GET / HTTP/1.1`, заголовки, ответ сервера.

#### SYN-флуд или подозрительные соединения

```bash
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0 and tcp[tcpflags] & (tcp-ack) == 0'
```

Это покажет только SYN-пакеты (начала соединений). Если их тысячи в секунду — атака.

#### DNS-запросы

```bash
sudo tcpdump -i any port 53 -n
```

```bash
sudo tcpdump -i any -n port 53
```

```
12:34:56.789012 IP 192.168.1.100.54321 > 8.8.8.8.53: 1234+ A? example.com. (29)
12:34:56.789123 IP 8.8.8.8.53 > 192.168.1.100.54321: 1234 1/0/0 A 93.184.216.34 (45)
```

- `1234+` — ID запроса.
- `A? example.com` — запрос A-записи.
- `1/0/0 A 93.184.216.34` — ответ: одна запись, IP.

#### Захват трёхстороннего рукопожатия (3-way handshake)

```bash
sudo tcpdump -i any host example.com and port 443 -c 3
```

Посмотрите SYN → SYN-ACK → ACK.

### Количество пакетов

```bash
# Остановиться после N пакетов
sudo tcpdump -i eth0 -c 100

# Без разрешения имён (быстрее и чище)
sudo tcpdump -i eth0 -n
```

Всегда используйте `-n`, если не нужны имена — без него tcpdump делает обратные DNS-запросы на каждый пакет.

---

## 7.5 Wireshark и tshark — анализ захваченного трафика

`tcpdump` хорош для быстрого захвата. **Wireshark** — для глубокого анализа. Он умеет:
- раскладывать пакеты по протоколам (HTTP, DNS, TLS, TCP);
- фильтровать по любым полям;
- собирать статистику (разговоры, нагрузки, задержки);
- показывать TLS-сессию и даже расшифровывать (если есть ключи).

> Если команды нет:
> ```bash
> sudo apt install wireshark tshark
> ```

### Рабочий процесс

```
Сервер (без GUI)                    Ваш ноутбук
┌─────────────────┐                ┌──────────────────┐
│ tcpdump -w       │                │ Wireshark        │
│ /tmp/dump.pcap   │─── scp/rsync ─>│ /tmp/dump.pcap   │
│ sudo tcpdump ... │                │ Открыть →        │
│ но не tshark     │                │ Анализ           │
└─────────────────┘                └──────────────────┘
```

**Правило:** На сервере — `tcpdump -w`, анализ — локально в Wireshark. Не мучайте сервер.

### tshark — командная строка

`tshark` — консольная версия Wireshark.

```bash
# Первые 20 пакетов из файла
tshark -r /tmp/capture.pcap | head -20

# Только HTTP
tshark -r /tmp/capture.pcap -Y "http" | head -20

# Только DNS
tshark -r /tmp/capture.pcap -Y "dns"

# Захват в реальном времени
tshark -i eth0 -f "port 80"
```

Фильтры:
- **Захвата** (`-f`): такие же BPF, как в tcpdump.
- **Отображения** (`-Y`): мощные wireshark-фильтры (`http.request.method == "GET"`, `tcp.port == 443`).

### Основные фильтры Wireshark (display filters)

| Фильтр | Что показывает |
|--------|---------------|
| `http` | Только HTTP |
| `dns` | Только DNS |
| `tcp.port == 443` | Трафик на 443 порт |
| `ip.addr == 1.2.3.4` | Пакеты с/на этот IP |
| `tcp.flags.syn == 1` | SYN-пакеты (начала соединений) |
| `tcp.analysis.retransmission` | Ретрансмиссии (потери!) |
| `http.response.code == 500` | Только 500-е ответы |
| `tls.handshake.type == 11` | TLS Certificate (тип 11) |

### Анализ TLS в Wireshark

Если есть приватный ключ сервера, Wireshark может расшифровать TLS-трафик:

1. Preferences → Protocols → TLS → RSA keys list.
2. Добавить `server.pem` + IP:port.
3. Открыть pcap — трафик будет расшифрован.

### Статистика

```bash
# Разговоры (кто с кем говорил)
tshark -r capture.pcap -z conv,tcp

# Нагрузка по протоколам
tshark -r capture.pcap -z io,phs
```

### Когда Wireshark незаменим

- **Медленный сайт:** Wireshark покажет точное время между SYN, SYN-ACK, HTTP-запросом и ответом.
- **Странные ошибки:** TCP retransmission, duplicate ACK, zero window — Wireshark подсветит красным.
- **Диагностика TLS:** весь handshake, cipher suites, сертификаты — в удобном виде.
- **Разбор конкретного протокола:** не только HTTP, но и MySQL, PostgreSQL, MongoDB, Redis.

---

## 7.6 Алгоритм диагностики «снизу вверх»

Когда что-то не работает — не тыкайте во все инструменты сразу. **Идите по слоям OSI снизу вверх.**

### Флоучарт

```
┌─────────────────────────────────────────────────────────┐
│  Проблема: «не открывается сайт»                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. ping <хост>                              ─── L3?   │
│     ├─ 100% loss → проверьте IP, фаервол               │
│     └─ ОК → дальше                                     │
│                                                         │
│  2. traceroute <хост>                        ─── Где?  │
│     ├─ Звёзды на хопе N → провайдер?                   │
│     └─ Доходит → дальше                                 │
│                                                         │
│  3. nc -zv <хост> <порт>                     ─── L4?   │
│     ├─ Connection refused → сервис не слушает          │
│     └─ Connected → дальше                               │
│                                                         │
│  4. curl -v <URL>                            ─── L7?   │
│     ├─ SSL error → сертификат                          │
│     ├─ 4xx/5xx → HTTP-уровень                          │
│     └─ Не доходит → tcpdump                            │
│                                                         │
│  5. dig <домен>                              ─── DNS?  │
│     ├─ NXDOMAIN → домен не существует                  │
│     └─ Не тот IP → кэш / провайдер                     │
│                                                         │
│  6. sudo tcpdump -i any host <хост>         ─── Сеть?  │
│     ├─ Ничего → трафик не идёт (маршрут?)              │
│     ├─ SYN → SYN-ACK → ... → RST → что-то сбрасывает  │
│     └─ SYN → ... → нет ответа → фаервол дропает        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Каждому слою — свой инструмент

| Уровень OSI | Инструмент | Что проверяем |
|-------------|-----------|---------------|
| L3 (IP) | `ping`, `traceroute`, `mtr` | Доступность, маршрут, потери |
| L4 (TCP) | `nc -zv`, `ss`, `tcpdump` | Порт открыт, handshake |
| L5-L7 | `curl -v`, `openssl s_client` | HTTP, TLS, сертификаты |
| DNS | `dig`, `nslookup`, `host` | Разрешение имён |
| Сеть | `tcpdump`, `Wireshark` | Детальный захват |

### Скрипт быстрой проверки

```bash
#!/bin/bash
HOST="${1:-google.com}"
PORT="${2:-443}"

echo "=== 1. ping $HOST ==="
ping -c 3 "$HOST" 2>&1 | tail -1

echo -e "\n=== 2. traceroute (TCP) $HOST:$PORT ==="
sudo traceroute -T -p "$PORT" "$HOST" 2>&1 | tail -3

echo -e "\n=== 3. nc $HOST:$PORT ==="
nc -zv "$HOST" "$PORT" 2>&1

echo -e "\n=== 4. curl -v https://$HOST:$PORT ==="
curl -v --connect-timeout 5 "https://$HOST:$PORT" 2>&1 | grep -E "SSL|HTTP|error|failed\|Couldn't"

echo -e "\n=== 5. dig $HOST ==="
dig "$HOST" +short
```

---

### 7.7 ss — сокеты и соединения

Часто забываемый, но критически важный инструмент — `ss` (замена устаревшему `netstat`). Он показывает, какие порты слушаются и какие соединения установлены.

```bash
# Все слушающие TCP-сокеты
ss -tlnp

# Все установленные соединения
ss -tnp

# Все сокеты (TCP + UDP)
ss -tulnp

# Фильтр по порту
ss -tlnp 'sport = :443 or dport = :443'

# Состояния
ss -tlnp state listening
ss -tnp state established
ss -tnp state time-wait
```

| Флаг | Что |
|------|-----|
| `-t` | TCP |
| `-u` | UDP |
| `-l` | Listening (слушающие) |
| `-n` | Не резолвить имена |
| `-p` | Показать процесс |

```bash
# Кто слушает 80-й порт?
ss -tlnp | grep ':80'

# Сколько соединений к базе данных?
ss -tnp | grep ':5432'
```

---

## Типичные ошибки

### 1. `* * *` в traceroute — всегда проблема

Нет. Большинство роутеров по умолчанию не отвечают на ICMP Time Exceeded. Если дальше пакеты доходят — всё в порядке.

Смотрите на тренд: если после `* * *` все хопы тоже `* * *` — проблема. Если один хоп молчит, а дальше ОК — это «тихий» роутер.

### 2. tcpdump без фильтра — поток данных

```bash
sudo tcpdump -i eth0
# 100500 строк в секунду, ничего не понять
```

Всегда добавляйте фильтр: `host`, `port`, `and`, `or`. Или сохраняйте в файл и смотрите в Wireshark.

### 3. Пустой вывод tcpdump — неверный интерфейс

```bash
sudo tcpdump -i eth0
tcpdump: listening on eth0, link-type EN10MB ...
# ничего не выводится
```

Проверьте:
- Тот ли интерфейс? `ip link show` или `ip addr`.
- Тот ли хост? Может трафик идёт через `eth1` или `any`.
- Всегда используйте `-i any` если не уверены.

```bash
sudo tcpdump -i any host 8.8.8.8
```

### 4. tcpdump без sudo

```bash
tcpdump -i eth0
# tcpdump: eth0: You don't have permission to capture on that device
```

`tcpdump` требует root для захвата. Используйте `sudo`.

### 5. ping не отвечает — сервер мёртв

ICMP часто блокируют фаерволы. AWS, GCP, Azure — по умолчанию ICMP blocked. `ping` не работает, а HTTP отлично ходит.

**Правило:** проверяйте как минимум двумя способами: ping + curl или ping + nc.

### 6. traceroute из облака — видно не всё

В облачных сетях (AWS, GCP) многие внутренние роутеры не отвечают на traceroute. Вы увидите звёзды на внутренних хопах. Это нормально.

### 7. nc показывает Connected, а curl не работает

```
Connection to example.com 443 port [tcp/https] succeeded!
```

но `curl -v https://example.com`:
```
* TLS handshake failed
```

Проблема не в TCP (nc), а в TLS. Используйте `openssl s_client`.

---

## Чек-лист

- [ ] `ping -c 3 <host>` — базовая доступность (потери, RTT);
- [ ] `mtr --report <host>` — маршрут с потерями в процентах;
- [ ] `nc -zv <host> <port>` — открыт ли порт (TCP);
- [ ] `sudo tcpdump -i any host <host> -c 100 -w /tmp/dump.pcap && tcpdump -r /tmp/dump.pcap` — захват и быстрый просмотр.

---

## Попробуйте сами

**Задание 1. mtr --report google.com**

```bash
mtr --report --report-cycles 20 google.com
```

- Сколько хопов до Google?
- Есть ли потери?
- На каком хопе самый большой RTT?
- Какой хоп можно показать провайдеру, если интернет тормозит?

**Задание 2. tcpdump port 53 + dig**

В одном терминале:

```bash
sudo tcpdump -i any port 53 -n
```

В другом:

```bash
dig example.com
```

- Сколько пакетов обменялось?
- Какой IP вернул DNS?
- Видно ли в tcpdump тип записи (A, AAAA, MX)?

**Задание 3. curl + tcpdump — трёхстороннее рукопожатие**

Захватите три пакета TCP-рукопожатия:

```bash
# Терминал 1
sudo tcpdump -i any host example.com -c 3 -n
# Терминал 2
curl -s https://example.com > /dev/null
```

- Видите SYN → SYN-ACK → ACK?
- Какие номера sequence numbers?
- Какой MSS (Maximum Segment Size) предлагает сервер?
- Попробуйте то же с `tshark` и фильтром `tcp.flags.syn == 1`.
