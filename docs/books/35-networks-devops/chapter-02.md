# Глава 2: Сетевые интерфейсы Linux — ip addr, ip route, ip link

## Что вы узнаете

- Как просматривать и управлять сетевыми интерфейсами через `ip`
- Как читать таблицу маршрутизации
- Что такое loopback, физический и виртуальный интерфейс
- Как временно и постоянно настроить IP-адрес

Цель главы — чтобы вы увидели `ip addr show` и поняли **каждую** строку вывода.

---

## 2.1. Команда ip — замена ifconfig / route

В современных дистрибутивах пакет `net-tools` (ifconfig, route, netstat) считается устаревшим и часто не установлен по умолчанию. Его место занял пакет `iproute2` — команда `ip`.

| Старая команда | Новая команда |
|---|---|
| `ifconfig` | `ip addr show` |
| `ifconfig eth0 up` | `ip link set eth0 up` |
| `ifconfig eth0 down` | `ip link set eth0 down` |
| `route -n` | `ip route show` |
| `netstat -rn` | `ip route show` |
| `arp -n` | `ip neigh show` |

```bash
# если ip вдруг нет (редкость)
sudo apt install iproute2
```

> ☠️ **Осторожно:** не пишите в скриптах `ifconfig` — в Ubuntu 22.04+ его нет по умолчанию, и скрипт упадёт. Всегда используйте `ip`.

---

## 2.2. ip addr show — разбор вывода

Запустите на своей машине:

```bash
ip addr show
```

Вывод будет выглядеть примерно так (я покажу три интерфейса: loopback, физический и виртуальный от Docker):

```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host noprefixroute
       valid_lft forever preferred_lft forever

2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 52:54:00:ab:cd:ef brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0
       valid_lft 86399sec preferred_lft 86399sec
    inet6 fe80::5054:ff:feab:cdef/64 scope link
       valid_lft forever preferred_lft forever

3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default
    link/ether 02:42:ac:11:00:01 brd ff:ff:ff:ff:ff:ff
    inet 172.17.0.1/16 brd 172.17.0.255 scope global docker0
       valid_lft forever preferred_lft forever
```

### Разберём каждое поле на примере eth0

**Строка 1 — номер, имя и флаги:**

```
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
```

- `2:` — **номер интерфейса** (индекс в ядре). `lo` обычно 1, первый физический — 2.
- `eth0` — **имя интерфейса**. На новых системах может быть `enp3s0` (предсказуемые имена).
- `<BROADCAST,MULTICAST,UP,LOWER_UP>` — **флаги**:
  - `UP` — интерфейс включён (административно поднят).
  - `LOWER_UP` — физический уровень работает (кабель подключён, линк есть).
  - `BROADCAST` — поддерживает широковещательные рассылки.
  - `MULTICAST` — поддерживает мультикаст.
  - Если нет `LOWER_UP` — нет линка (кабель выдернут или Wi-Fi не подключён).
- `mtu 1500` — Maximum Transmission Unit. Стандарт для Ethernet — 1500 байт. Для jumbo frames — 9000.
- `qdisc mq` — очередь пакетов (queueing discipline). `mq` — multi-queue для многоядерных систем. `noqueue` — без очереди (как на lo). `pfifo_fast` — классическая.
- `state UP` — то же самое что флаг `UP`, дублирование для читаемости.
- `group default` — группа интерфейсов (по умолчанию `default`). Используется для массовых операций.
- `qlen 1000` — длина очереди передачи (txqueuelen).

**Строка 2 — MAC-адрес:**

```
link/ether 52:54:00:ab:cd:ef brd ff:ff:ff:ff:ff:ff
```

- `link/ether` — тип канального уровня (Ethernet).
- `52:54:00:ab:cd:ef` — **MAC-адрес**. Первые 3 октета — OUI (производитель). `52:54:00` — это QEMU.
- `brd ff:ff:ff:ff:ff:ff` — broadcast MAC (стандартный).

**Строка 3 — IPv4-адрес:**

```
inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0
   valid_lft 86399sec preferred_lft 86399sec
```

- `inet` — семейство адресов (IPv4).
- `192.168.1.100/24` — сам адрес с маской в CIDR-нотации. `/24` = `255.255.255.0`.
- `brd 192.168.1.255` — широковещательный адрес сети.
- `scope global` — область видимости. `global` — адрес видим везде. `host` — только на этом хосте (127.0.0.1). `link` — только в этом сегменте (link-local).
- `dynamic eth0` — адрес получен по DHCP. `eth0` — имя интерфейса, к которому привязан.
- `valid_lft 86399sec` — время жизни адреса (DHCP-аренда). После этого адрес становится недоступен.
- `preferred_lft 86399sec` — время предпочтительной жизни. Обычно совпадает с valid_lft.

**Строка 4 — IPv6-адрес:**

```
inet6 fe80::5054:ff:feab:cdef/64 scope link
```

- `fe80::/64` — link-local адрес (автоматически назначается всем интерфейсам с IPv6).
- `scope link` — действует только в пределах данного канала (линка).

### Loopback (lo)

```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    inet 127.0.0.1/8 scope host lo
```

- `LOOPBACK` — виртуальный интерфейс, указывающий на себя.
- `mtu 65536` — максимальный MTU (нет физических ограничений).
- `127.0.0.1/8` — стандартная петля. Вся сеть `127.0.0.0/8` направлена на localhost, но обычно используется только `.1`.
- `scope host` — доступен только на этом хосте.

### Docker / виртуальные интерфейсы (docker0)

```
3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN
    inet 172.17.0.1/16 brd 172.17.0.255 scope global docker0
```

- `NO-CARRIER` — нет физического подключения (мост создан, но к нему ничего не подключено).
- `state DOWN` — интерфейс административно поднят (`UP` есть), но линка нет.
- Docker создаёт мост `docker0` и выдаёт контейнерам адреса из `172.17.0.0/16`.

### Управление адресами

```bash
# показать конкретный интерфейс
ip addr show eth0

# показать только статистику (переданные/принятые пакеты)
ip -s link show eth0

# добавить временный адрес
sudo ip addr add 192.168.1.200/24 dev eth0

# удалить адрес
sudo ip addr del 192.168.1.200/24 dev eth0
```

> ☠️ **Осторожно:** `sudo ip link set eth0 down` — отключит интерфейс. Если вы подключены по SSH через этот интерфейс, соединение оборвётся. Никогда не делайте этого на удалённом сервере без консольного доступа.

---

## 2.3. Таблица маршрутизации

```bash
ip route show
```

Типичный вывод:

```
default via 192.168.1.1 dev eth0 proto dhcp src 192.168.1.100 metric 100
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100 metric 100
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown
```

### Разбор строк

**Строка 1 — маршрут по умолчанию (default gateway):**

```
default via 192.168.1.1 dev eth0 proto dhcp src 192.168.1.100 metric 100
```

- `default` — `0.0.0.0/0` (все сети).
- `via 192.168.1.1` — шлюз, куда отправлять пакеты, если сеть назначения неизвестна.
- `dev eth0` — через какой интерфейс.
- `proto dhcp` — маршрут добавлен DHCP-клиентом.
- `src 192.168.1.100` — исходный адрес по умолчанию для пакетов.
- `metric 100` — метрика. Если есть несколько default-маршрутов, выигрывает с меньшей метрикой.

**Строка 2 — локальная сеть:**

```
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100 metric 100
```

- `192.168.1.0/24` — сеть назначения.
- `scope link` —直达 (directly connected), без шлюза.
- Пакеты для `192.168.1.1`–`192.168.1.254` уходят напрямую через `eth0`, без шлюза.

**Строка 3 — Docker-сеть:**

```
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown
```

- `scope link` — connected network.
- `linkdown` — интерфейс `docker0` в состоянии DOWN. Маршрут есть, но пакеты не уйдут, пока интерфейс не поднимется.

### Полезные команды

```bash
# проверить, куда уйдёт пакет до заданного IP
ip route get 8.8.8.8
# 8.8.8.8 via 192.168.1.1 dev eth0 src 192.168.1.100 uid 1000

ip route get 192.168.1.50
# local 192.168.1.50 dev lo src 192.168.1.50 uid 1000
#   cache <local>
```

`ip route get` — лучшая команда для диагностики. Она показывает реальный путь пакета с учётом политик маршрутизации.

```bash
# добавить маршрут
sudo ip route add 10.0.0.0/16 via 192.168.1.1 dev eth0
sudo ip route add 10.0.0.0/16 via 192.168.1.1 dev eth0 metric 50

# удалить маршрут
sudo ip route del 10.0.0.0/16

# заменить шлюз по умолчанию
sudo ip route replace default via 192.168.1.254 dev eth0
```

> ☠️ **Осторожно:** `sudo ip route del default` удалит маршрут по умолчанию. Вы потеряете доступ к интернету (но не SSH в локальной сети). Восстановить: `sudo ip route add default via <правильный-шлюз> dev eth0`.

---

## 2.4. Постоянная настройка

Временные изменения (`ip addr add`, `ip route add`) исчезают после перезагрузки. Чтобы сделать настройки постоянными, используется Netplan (Ubuntu 18.04+) или `/etc/network/interfaces` (Debian legacy).

### Netplan

Конфиги лежат в `/etc/netplan/`:

```yaml
# /etc/netplan/00-installer-config.yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
```

```bash
# проверить синтаксис
sudo netplan generate

# применить
sudo netplan apply
```

> ☠️ **Осторожно:** `sudo netplan apply` применяет конфигурацию немедленно. Если вы ошиблись в IP — SSH оборвётся. Всегда держите открытым второй SSH-сеанс с запасным доступом, либо тестируйте через `sudo netplan try` — он откатит изменения через 120 секунд, если вы не подтвердите.

```bash
# безопасное применение с таймаутом
sudo netplan try
# ... подтвердить Enter, иначе откат через 2 минуты
```

### /etc/network/interfaces (Debian, старый стиль)

```ini
# /etc/network/interfaces
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8 1.1.1.1
```

```bash
sudo systemctl restart networking
```

### DHCP

Если интерфейс получает адрес по DHCP — в Netplan это выглядит так:

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
```

---

## Типичные ошибки

1. **Временные изменения теряются при перезагрузке.** Вы добавили IP через `ip addr add`, через час перезагрузили сервер — IP пропал. Всегда проверяйте, есть ли постоянная конфигурация в `/etc/netplan/` или `/etc/network/interfaces`.

2. **`ip addr add` добавляет второй адрес, а не заменяет.** Если на интерфейсе уже есть `192.168.1.100/24` и вы выполняете `ip addr add 192.168.1.200/24 dev eth0`, у интерфейса будет **два** адреса. Для замены нужно сначала удалить старый: `ip addr del 192.168.1.100/24 dev eth0 && ip addr add 192.168.1.200/24 dev eth0`.

3. **`ip link set eth0 down` на удалённом сервере.** Самая частая причина потери доступа к серверу. Если у вас нет iLO/iDRAC/IPMI или физического доступа — сервер придётся перезагружать через дата-центр.

4. **Путаница между `state DOWN` и `NO-CARRIER`.** `state DOWN` — интерфейс выключен административно (`ip link set eth0 down`). `NO-CARRIER` — кабель не подключён, но интерфейс UP. Лечится по-разному: `ip link set eth0 up` vs подключение кабеля.

---

## Чек-лист

- [ ] Умею читать `ip addr show`: флаги, MTU, MAC, IP, scope
- [ ] Знаю разницу между `ip addr add` (добавить) и netplan (постоянно)
- [ ] Могу прочитать `ip route show` и объяснить маршрут по умолчанию и connected-сети
- [ ] Не выполняю `ip link set eth0 down` на удалённом сервере

---

## Попробуйте сами

1. **Исследуйте свои интерфейсы.** Выполните `ip addr show` и `ip route show`. Найдите loopback, физический интерфейс, виртуальные (docker, tun, bridge). Запишите, какие сети видит ваш хост.

2. **Добавьте временный IP.** Выполните `sudo ip addr add 10.0.0.1/24 dev lo`. Проверьте `ip addr show lo`. Удалите лишний адрес. Попробуйте `ping 10.0.0.1` — он должен работать (петля через lo).

3. **Сымитируйте потерю линка.** Если у вас есть физический интерфейс с подключённым кабелем, выполните `sudo ip link set eth0 down`. Наблюдайте изменения в `ip addr show`. **Верните обратно:** `sudo ip link set eth0 up`. Если работаете по SSH — пропустите это задание.
