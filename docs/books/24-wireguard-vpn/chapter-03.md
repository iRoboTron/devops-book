# Глава 3: Первый туннель

> **Цель:** соединить сервер и один клиент.

---

## 3.1 Ключи сервера

```bash
sudo mkdir -p /etc/wireguard
cd /etc/wireguard
umask 077
wg genkey | sudo tee server_private.key | wg pubkey | sudo tee server_public.key
```

Права важны: приватный ключ не должен быть читаем всеми.

---

## 3.2 Конфиг сервера

`/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <SERVER_PRIVATE_KEY>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = <CLIENT_PUBLIC_KEY>
AllowedIPs = 10.0.0.2/32
```

Для первого split tunnel NAT не нужен, если клиенту нужен только доступ к серверу по `10.0.0.1`.

---

## 3.3 Конфиг клиента

```ini
[Interface]
PrivateKey = <CLIENT_PRIVATE_KEY>
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
Endpoint = SERVER_PUBLIC_IP:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

`PersistentKeepalive` полезен для телефона и домашнего интернета за NAT.

---

## 3.4 Запуск и проверка

На сервере:

```bash
sudo wg-quick up wg0
```

```bash
# Пример вывода:
[#] ip link add wg0 type wireguard
[#] wg setconf wg0 /dev/fd/63
[#] ip -4 address add 10.0.0.1/24 dev wg0
[#] ip link set mtu 1420 up dev wg0
[#] iptables -A FORWARD -i wg0 -j ACCEPT
[#] iptables -A FORWARD -o wg0 -j ACCEPT
```

```bash
sudo wg show
```

```bash
# Пример вывода (сразу после запуска, до подключения клиента):
interface: wg0
  public key: 8J3vQkLmN2+XpR7tYwZ5aB1cDfGhIjKoMnOpQrSt4U=
  private key: (hidden)
  listening port: 51820

peer: mB4nRsT1qWoP9uYiL6jKxZ3cFvGhDeNaE8sCpA2lO=
  allowed ips: 10.0.0.2/32
```

```bash
# Пример вывода wg show после handshake клиента:
interface: wg0
  public key: 8J3vQkLmN2+XpR7tYwZ5aB1cDfGhIjKoMnOpQrSt4U=
  private key: (hidden)
  listening port: 51820

peer: mB4nRsT1qWoP9uYiL6jKxZ3cFvGhDeNaE8sCpA2lO=
  endpoint: 192.0.2.45:49182
  allowed ips: 10.0.0.2/32
  latest handshake: 14 seconds ago
  transfer: 1.23 KiB received, 652 B sent
```

На клиенте после подключения:

```bash
ping 10.0.0.1
```

```bash
# Пример вывода:
PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.
64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=18.4 ms
64 bytes from 10.0.0.1: icmp_seq=2 ttl=64 time=17.9 ms
64 bytes from 10.0.0.1: icmp_seq=3 ttl=64 time=18.1 ms
^C
--- 10.0.0.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 17.9/18.1/18.4/0.209 ms
```

> **Если что-то пошло не так:**
>
> **Ошибка: «RTNETLINK answers: Operation not permitted»** — команда выполнена без `sudo`. Всегда используй `sudo wg-quick up wg0`.
>
> **Handshake не происходит** (`latest handshake` отсутствует в `wg show`). Проверяй по порядку:
> 1. Порт открыт на сервере: `sudo ss -ulnp | grep 51820` — должна быть строка с `UNCONN` и `51820`.
> 2. Firewall разрешает UDP 51820: `sudo ufw status verbose | grep 51820`.
> 3. Публичный ключ в конфиге клиента совпадает с ключом сервера: `sudo cat /etc/wireguard/server_public.key` — сравни с `[Peer] PublicKey` в клиентском конфиге.
> 4. `Endpoint` в клиентском конфиге указывает правильный публичный IP сервера: `curl ifconfig.me` на сервере.
> 5. Провайдер или корпоративный firewall блокирует UDP — попробуй другой порт (например, 443/udp).

Если проверяешь с сервера `ping 10.0.0.2`, клиент уже должен быть подключён и разрешать ICMP.

---

## 3.5 Практика

Подними первый туннель. Практика завершена, если клиент пингует `10.0.0.1`, а `sudo wg show` на сервере показывает свежий handshake.