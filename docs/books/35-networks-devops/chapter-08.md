# Глава 8: nmap — сканирование и инвентаризация

> ☠️ **Осторожно:** сканирование сетей без явного разрешения владельца — незаконно. Только своя инфраструктура или письменное разрешение.

## Что вы узнаете

- как сканировать порты в своей инфраструктуре;
- основные режимы nmap и когда что использовать;
- как определять ОС и версии сервисов;
- правовые и этические ограничения.

**Цель главы:** читатель умеет проверить что открыто на своих серверах.

---

## 8.1 Установка

```bash
sudo apt install nmap
```

Проверка:

```bash
nmap --version
```

```
Nmap version 7.80 ( https://nmap.org )
Platform: x86_64-pc-linux-gnu
Compiled with: ...
```

---

## 8.2 Основные режимы сканирования

nmap умеет многое, но в повседневной DevOps-работе нужно всего несколько режимов. Освоив их, вы закроете 95% задач.

### Сканирование одного хоста

```bash
nmap 192.168.1.1
```

Что происходит:
1. nmap отправляет TCP SYN на 1000 самых популярных портов.
2. Ждёт ответ: SYN-ACK (открыт), RST (закрыт) или ничего (filtered).
3. Выводит таблицу открытых портов.

```
Starting Nmap 7.80 ( https://nmap.org )
Nmap scan report for 192.168.1.1
Host is up (0.0021s latency).
Not shown: 995 closed ports
PORT     STATE    SERVICE
22/tcp   open     ssh
80/tcp   open     http
443/tcp  open     https
8080/tcp open     http-proxy
9001/tcp filtered tor-orport

Nmap done: 1 IP address (1 host up) scanned in 3.42 seconds
```

Столбец `STATE` — ключевой:
- **open** — порт слушается (сервис отвечает).
- **closed** — порт закрыт (RST в ответ на SYN).
- **filtered** — nmap не получил ответ (фаервол дропнул пакет).

### Диапазон портов

```bash
# Порты 1-1000
nmap -p 1-1000 192.168.1.1

# Конкретные порты
nmap -p 22,80,443,5432 192.168.1.1

# Все 65535 портов (долго!)
nmap -p- 192.168.1.1
```

**Когда что использовать:**

| Диапазон | Когда |
|----------|-------|
| По умолчанию (1000 портов) | Быстрая проверка |
| `-p 22,80,443,5432` | Проверка конкретных сервисов |
| `-p 1-10000` | Баланс скорости и полноты |
| `-p-` | Полная инвентаризация (редко) |

### Сканирование подсети

```bash
nmap 192.168.1.0/24
```

Эта команда просканирует все 254 хоста в /24 сети. Вывод — список живых хостов с открытыми портами.

```
Nmap scan report for 192.168.1.1
Host is up (0.0010s latency).
...

Nmap scan report for 192.168.1.10
Host is up (0.0020s latency).
Not shown: 997 closed ports
PORT     STATE  SERVICE
22/tcp   open   ssh
...

Nmap scan report for 192.168.1.20
Host is up (0.0015s latency).
All 1000 scanned ports on 192.168.1.20 are filtered
```

Если хост не отвечает — `Host seems down`. nmap сначала делает ping-sweep (ICMP + TCP на 80 + 443), и только потом сканирует ответивших.

### Быстрое сканирование (Fast scan)

```bash
nmap -F 192.168.1.0/24
```

`-F` (Fast) — сканирует только 100 самых популярных портов вместо 1000. В 5-10 раз быстрее.

```
Starting Nmap 7.80 ( https://nmap.org )
Nmap scan report for 192.168.1.0/24
Host is up (0.0015s latency).
Not shown: 97 closed ports
PORT     STATE  SERVICE
22/tcp   open   ssh
80/tcp   open   http
443/tcp  open   https
```

### SYN-сканирование (Stealth scan)

```bash
sudo nmap -sS 192.168.1.1
```

`-sS` — самый популярный режим. nmap отправляет SYN и:

| Ответ nmap | Состояние порта |
|------------|-----------------|
| SYN-ACK → RST | open |
| RST | closed |
| Нет ответа / ICMP Unreachable | filtered |

Требует `sudo`, потому что создаёт сырые (raw) сокеты. Не завершает трёхстороннее рукопожатие полностью — считается «полу-открытым» (half-open). Быстрее обычного TCP-скана.

> Зачем `sudo`? Обычный `nmap` работает через системный вызов `connect()` — как curl. `-sS` шлёт сырые IP-пакеты своими руками. Без root это запрещено.

### UDP-сканирование

```bash
sudo nmap -sU -p 53,67,68,123,161 192.168.1.1
```

TCP — не единственный протокол. DNS (53), DHCP (67/68), NTP (123), SNMP (161) работают через UDP.

UDP-сканирование **медленное**:
- nmap шлёт UDP-пакет.
- Если в ответ ICMP Port Unreachable — порт закрыт.
- Если ответ есть — открыт.
- Если ничего — порт filtered или open (nmap не может различить без дополнительных данных).

> ☠️ **Осторожно:** UDP-сканирование может занять часы на /24 сети. Сканируйте только конкретные порты.

---

## 8.3 Обнаружение сервисов и ОС

Мало знать, что порт открыт. Надо знать, **что** там слушается — nginx или Apache, какая версия, какая ОС.

### Версии сервисов

```bash
nmap -sV 192.168.1.1
```

`-sV` (Version detection) — nmap подключается к каждому открытому порту, анализирует ответ и определяет сервис и версию.

```
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 8.9p1 Ubuntu 3ubuntu0.6
80/tcp   open  http        nginx 1.24.0
443/tcp  open  ssl/http    nginx 1.24.0
5432/tcp open  postgresql  PostgreSQL 15.4
```

**Чем полезно:**
- Узнать, не пора ли обновить OpenSSH;
- Найти забытый Apache на нестандартном порту;
- Убедиться, что на 443 стоит nginx, а не что-то ещё.

### Определение ОС

```bash
sudo nmap -O 192.168.1.1
```

`-O` (OS detection) — nmap анализирует TTL, окна TCP, опции и другие признаки, чтобы угадать ОС.

```
Device type: general purpose
Running: Linux 5.x|6.x
OS CPE: cpe:/o:linux:linux_kernel:5
OS details: Linux 5.15.0-91-generic
Network Distance: 1 hop
```

Как nmap узнаёт ОС? По fingerprint'ам TCP/IP-стека:
- начальное значение TTL;
- размер TCP window;
- поддерживаемые TCP-опции (MSS, WScale, Timestamp, SACK);
- поведение при фрагментации.

База данных nmap содержит тысячи сигнатур для Linux, Windows, macOS, Cisco, Juniper, FreeBSD.

> ☠️ **Осторожно:** Определение ОС — вероятностное (accuracy ~80-90%). Опытный администратор может подделать fingerprint (через `sysctl` на Linux).

### Агрессивное сканирование

```bash
sudo nmap -A 192.168.1.1
```

`-A` (Aggressive) — включает всё сразу:
- `-sS` — SYN-сканирование;
- `-sV` — версии сервисов;
- `-O` — определение ОС;
- traceroute до цели;
- NSE-скрипты по умолчанию.

**Итог:** одна команда — полный профиль хоста.

```
Nmap scan report for 192.168.1.1
Host is up (0.0012s latency).
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 8.9p1 Ubuntu 3ubuntu0.6
80/tcp   open  http        nginx 1.24.0
443/tcp  open  ssl/http    nginx 1.24.0
Device type: general purpose
Running: Linux 5.x
OS details: Linux 5.15.0-91-generic
TRACEROUTE
HOP RTT     ADDRESS
1   1.21ms  192.168.1.1
```

### Сохранение результатов

```bash
# Человекочитаемый
nmap -oN output.txt 192.168.1.1

# XML (для парсинга и автоматизации)
nmap -oX output.xml 192.168.1.1

# grep-friendly (одна строка на хост)
nmap -oG output.grep 192.168.1.1
```

**Форматы:**

| Флаг | Формат | Для чего |
|------|--------|----------|
| `-oN` | Normal text | Чтение человеком |
| `-oX` | XML | Автоматизация, интеграция с SIEM |
| `-oG` | Grepable | Быстрый grep по портам |
| `-oS` | Script kiddie | Шутка (вывод в leet-speak) |
| `-oA` | All | Все три формата сразу |

Пример `-oG`:

```
Host: 192.168.1.1 (router)  Status: Up
Host: 192.168.1.1 (router)  Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
Host: 192.168.1.10 (webserver)  Status: Up
Host: 192.168.1.10 (webserver)  Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 443/open/tcp//https///
```

Парсить grep-формат можно одной строкой:

```bash
nmap -oG - 192.168.1.0/24 | grep -E "22/open" | awk '{print $2}'
```

Выведет все хосты с открытым SSH.

---

## 8.4 NSE — Nmap Scripting Engine

NSE — встроенный скриптовый движок на Lua. Тысячи готовых скриптов для проверки уязвимостей, аудита конфигураций, брутфорса.

### Запуск скрипта

```bash
# HTTP-заголовки сервера
nmap --script http-headers 192.168.1.10

# Проверка уязвимости Heartbleed
nmap --script ssl-heartbleed -p 443 192.168.1.10
```

### Популярные скрипты

| Скрипт | Что делает |
|--------|-----------|
| `http-headers` | Показывает HTTP-заголовки ответа |
| `ssl-enum-ciphers` | Перечисляет поддерживаемые TLS-шифры |
| `ssl-heartbleed` | Проверяет уязвимость Heartbleed (CVE-2014-0160) |
| `dns-zone-transfer` | Пытается сделать DNS zone transfer |
| `ssh2-enum-algos` | Перечисляет алгоритмы SSH |
| `mysql-info` | Информация о MySQL-сервере |
| `smb-os-discovery` | Определяет ОС через SMB |

```bash
# Все скрипты категории safe
nmap --script safe 192.168.1.10

# Аудит SSL/TLS
nmap --script ssl-enum-ciphers -p 443 192.168.1.10
```

```
PORT    STATE SERVICE
443/tcp open  https
| ssl-enum-ciphers:
|   TLSv1.2:
|     ciphers:
|       TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 (ecdh_x25519) - A
|       TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 (ecdh_x25519) - A
|       TLS_RSA_WITH_AES_128_CBC_SHA (rsa 2048) - C
|     compressors:
|       NULL
|   TLSv1.3:
|     ciphers:
|       TLS_AES_256_GCM_SHA384 (ecdh_x25519) - A
|_  least strength: C
```

Видно, что сервер поддерживает слабый шифр (C-grade) — пора убирать.

### Категории скриптов

```
auth       — проверка аутентификации
broadcast  — широковещательные запросы
brute      — брутфорс паролей
default    — скрипты по умолчанию
discovery  — обнаружение сервисов
dos        — проверка DoS-уязвимостей
exploit    — эксплуатация уязвимостей
external   — запросы к внешним сервисам
fuzzer     — фаззинг
intrusive  — может повлиять на работу сервиса
malware    — поиск заражения
safe       — безопасные (не влияют на сервис)
version    — определение версий
vuln       — проверка уязвимостей
```

> ☠️ **Осторожно:** Скрипты категорий `intrusive`, `dos`, `exploit` могут нарушить работу сервиса. Не запускайте на production без согласования.

---

## 8.5 Практический сценарий: аудит сервера

Допустим, вы DevOps-инженер. Вам нужно проверить новый сервер перед вводом в эксплуатацию.

### Полная инвентаризация

```bash
sudo nmap -sS -sV -p- --open 192.168.1.10
```

Что делает:
- `-sS` — SYN-сканирование (быстро, требует sudo);
- `-sV` — определение версий;
- `-p-` — все 65535 портов;
- `--open` — показать только открытые порты.

Результат:

```
Starting Nmap 7.80 ...
Nmap scan report for 192.168.1.10
Host is up (0.0015s latency).
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 8.2p1 Ubuntu 4ubuntu0.11
80/tcp   open  http        Apache httpd 2.4.41
443/tcp  open  ssl/http    Apache httpd 2.4.41
3306/tcp open  mysql       MySQL 8.0.35
```

**Вопросы, которые вы должны себе задать:**

1. **MySQL (3306) открыт наружу?** Это почти всегда ошибка. MySQL должен слушать только на localhost или в приватной подсети.
2. **Версия OpenSSH 8.2p1?** Проверьте, нет ли известных уязвимостей (CVE).
3. **Apache 2.4.41?** Актуальная версия? Есть ли патчи безопасности?
4. **Нет ли неожиданных портов?** Redis, Docker API, Elasticsearch — их не должно быть снаружи.

### Аудит безопасности

```bash
# SSL/TLS
nmap --script ssl-enum-ciphers,ssl-heartbleed -p 443 192.168.1.10

# HTTP-заголовки безопасности
nmap --script http-security-headers -p 80,443 192.168.1.10

# Проверка на известные уязвимости
nmap --script vuln -p 22,80,443 192.168.1.10
```

> ☠️ **Осторожно:** `--script vuln` запускает десятки скриптов, в том числе те, что могут негативно повлиять на сервер. Делайте на стейджинге.

### Отчёт в XML

```bash
sudo nmap -sS -sV -p- --open -oA server-audit 192.168.1.10
```

Получите три файла: `server-audit.nmap`, `server-audit.xml`, `server-audit.grep`.

---

## 8.6 Практический сценарий: инвентаризация подсети

```bash
# Кто вообще живёт в сети?
nmap -sn 192.168.1.0/24
```

`-sn` (ping sweep) — только проверка, жив ли хост. Никакого сканирования портов.

```
Nmap scan report for 192.168.1.1
Host is up (0.0010s latency).
Nmap scan report for 192.168.1.10
Host is up (0.0015s latency).
Nmap scan report for 192.168.1.20
Host is up (0.0020s latency).
Nmap scan report for 192.168.1.100
Host is up (0.0012s latency).
Nmap done: 256 IP addresses (4 hosts up) scanned in 2.34 seconds
```

Быстрая инвентаризация сети — найти все живые хосты и их открытые порты:

```bash
# Живые хосты + порты
nmap -sn 192.168.1.0/24 -oG - | grep "Host" | awk '{print $2}' > /tmp/hosts.txt
nmap -iL /tmp/hosts.txt -F -oN /tmp/quick-audit.txt
```

---

## 8.7 Правовые и этические ограничения

### Это не шутка

Сканирование чужих сетей без разрешения — уголовно наказуемо в большинстве стран:

| Страна | Статья | Последствия |
|--------|--------|-------------|
| США | Computer Fraud and Abuse Act (CFAA) | До 10 лет тюрьмы |
| РФ | Ст. 272 УК РФ (Неправомерный доступ) | До 7 лет лишения свободы |
| UK | Computer Misuse Act | До 10 лет тюрьмы |
| EU | Directive 2013/40/EU | До 5 лет |

### Где нельзя сканировать

- Чужие IP-адреса и подсети;
- Облачные мета-IP (AWS metadata: 169.254.169.254);
- Провайдерские маршрутизаторы;
- Без письменного разрешения.

### Где можно

- **Свои серверы** — VPS, домашняя сеть, тестовые стенды;
- **Своя облачная инфраструктура** — AWS, GCP, Azure (аккаунты, которыми вы управляете);
- **Песочницы** — Hack The Box, TryHackMe, VulnHub, DVWA;
- **С письменного разрешения** — пентест по договору.

### Правило одного ping'а

Если вы случайно запустили `nmap` и поняли, что это не ваша сеть — сразу нажмите Ctrl+C. Один ping через `-sn` обычно не считается атакой (но лучше не рисковать).

```bash
# А это — уже недвусмысленное сканирование
sudo nmap -sS -p- -A 203.0.113.0/24
```

> ☠️ **Осторожно:** Даже сканирование своего облачного аккаунта может быть расценено как атака, если вы не владелец. AWS требует разрешение на пентест для некоторых сервисов (EC2 — можно, RDS под NDA — нельзя).

---

## Типичные ошибки

### 1. open vs closed vs filtered — путаница

Новички видят «filtered» и думают «значит открыт, но скрыт». На самом деле:

```
PORT      STATE    SERVICE
22/tcp    open     ssh       ← сервис слушает, соединение возможно
80/tcp    closed   http      ← сервис не слушает (RST в ответ)
443/tcp   filtered https     ← фаервол сбросил пакет без ответа
```

`filtered` — пакет упал (drop). Вы не знаете, открыт порт или нет. Это может значить:
- фаервол с правилом DROP;
- host-based firewall (iptables DROP);
- промежуточный сетевой фаервол.

### 2. Сканирование облака без разрешения

```
nmap amazon.com
nmap 54.xxx.xxx.xxx  # чужой EC2
```

AWS, GCP и Azure фиксируют сканирование в VPC Flow Logs. Если вас заметят — аккаунт могут заблокировать или передать данные в abuse-отдел.

### 3. nmap -p- на всю подсеть

```bash
nmap -p- 192.168.1.0/24
```

Сканирование 65535 портов на 254 хостах = 16 миллионов проверок. Это будет длиться **часами**. Используйте `-p-` только на один хост или добавляйте `--host-timeout 10m`.

### 4. Забыли `sudo` для SYN-сканирования

```bash
nmap -sS 192.168.1.1
# You requested a scan type which requires root privileges.
```

`-sS` требует raw sockets. Либо используйте `sudo`, либо переходите на `-sT` (TCP connect scan, без sudo, но медленнее).

### 5. Сканирование без `--open` — шум

```bash
nmap -p- 192.168.1.1
# 65535 строк: 65533 closed, 2 open
```

Лучше:

```bash
nmap -p- --open 192.168.1.1
# Только 2 открытых порта
```

---

## Чек-лист

- [ ] `sudo apt install nmap` — установка;
- [ ] `nmap -sn <subnet>/24` — обнаружение живых хостов;
- [ ] `sudo nmap -sS -sV -p- --open <host>` — полная инвентаризация портов и версий;
- [ ] `sudo nmap -A <host>` — агрессивное сканирование с ОС и скриптами.

---

## Попробуйте сами

**Задание 1. Инвентаризация своей сети**

```bash
nmap -sn 192.168.1.0/24
```

- Сколько живых хостов нашли?
- Все ли вы узнаёте? Если нет — кто это?

Дополнительно:

```bash
nmap -F 192.168.1.0/24
```

- Какие порты открыты на каждом хосте?
- Есть ли неожиданные?

**Задание 2. Аудит своего сервера**

```bash
sudo nmap -sS -sV -p- --open <IP своего сервера>
```

- Какие порты открыты?
- Какие версии сервисов?
- Есть ли порт, который не должен быть открыт наружу (например, Redis 6379, MongoDB 27017, Docker 2375)?

**Задание 3. Сравнение `-sS` и `-sT`**

```bash
time sudo nmap -sS -p 22,80,443 scanme.nmap.org
time nmap -sT -p 22,80,443 scanme.nmap.org
```

- Какая разница во времени?
- Есть ли разница в результате?
- Зачем нужен `sudo` для SYN?
