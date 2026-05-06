# Глава 7: Диагностика

> **Цель:** не гадать, почему VPN не работает, а идти по шагам.

---

## 7.1 Алгоритм

1. Проверить сервис.
2. Проверить UDP-порт.
3. Проверить ключи и AllowedIPs.
4. Проверить handshake.
5. Проверить маршруты, DNS и MTU.

---

## 7.2 Команды

```bash
sudo wg show
```

```bash
# Пример вывода — handshake давно (клиент не переподключился):
interface: wg0
  public key: 8J3vQkLmN2+XpR7tYwZ5aB1cDfGhIjKoMnOpQrSt4U=
  private key: (hidden)
  listening port: 51820

peer: mB4nRsT1qWoP9uYiL6jKxZ3cFvGhDeNaE8sCpA2lO=
  endpoint: 192.0.2.45:49182
  allowed ips: 10.0.0.2/32
  latest handshake: 2 minutes, 1 second ago
  transfer: 1.23 KiB received, 652 B sent

peer: pL7wVcX9yNqR2mFtS4kJ1bDhGzUoAeIi6nBsYjOp3Q=
  endpoint: 85.172.33.10:61903
  allowed ips: 10.0.0.3/32
  latest handshake: 3 hours, 41 minutes, 22 seconds ago
  transfer: 228 KiB received, 185 KiB sent
```

Строка `latest handshake: 3 hours, 41 minutes` означает, что клиент давно не отправлял трафик. Если `PersistentKeepalive` не настроен, клиент за NAT может «молчать» часами. Это не обязательно ошибка — телефон мог просто уйти в сон.

```bash
systemctl status wg-quick@wg0
journalctl -u wg-quick@wg0 --since "1 hour ago"
sudo ss -ulnp | grep 51820
```

```bash
# Пример вывода ss — порт слушается:
UNCONN 0      0            0.0.0.0:51820      0.0.0.0:*    users:(("wireguard",pid=1452,fd=1))
```

Если вывод пустой — WireGuard не запущен или слушает другой порт.

```bash
sudo ufw status verbose
ip route
```

Если нужен tcpdump:

```bash
sudo tcpdump -i eth0 udp port 51820
```

```bash
# Пример вывода tcpdump при активном подключении:
12:45:01.234567 IP 192.0.2.45.49182 > 95.216.10.5.51820: UDP, length 148
12:45:01.234891 IP 95.216.10.5.51820 > 192.0.2.45.49182: UDP, length 92
12:45:26.445123 IP 192.0.2.45.49182 > 95.216.10.5.51820: UDP, length 32
```

Если пакеты идут только в одну сторону — проверь firewall на обоих концах.

`eth0` замени на свой внешний интерфейс из `ip route show default`.

---

## 7.3 Типовые симптомы

| Симптом | Вероятная причина | Проверка |
|---|---|---|
| нет handshake | порт закрыт или неверный endpoint | `ufw`, `ss`, IP сервера |
| handshake старый | клиент не подключается | клиентский лог |
| ping есть, сайта нет | firewall или сервис слушает не там | `ss -tlnp`, Nginx |
| интернет через VPN не работает | NAT/forwarding | `sysctl`, iptables/nftables |
| часть сайтов висит | MTU | попробовать MTU 1420 или 1380 |
| DNS не тот | DNS leak | проверить DNS на клиенте |

---

## 7.4 MTU: симптом и решение

**Симптом:** VPN работает, ping проходит, но часть сайтов не открывается — особенно HTTPS. Крупные страницы виснут, мелкие (например, `curl http://example.com`) работают.

**Причина:** MTU по умолчанию в WireGuard — 1420 байт. Некоторые провайдеры или туннели требуют меньше. Крупные TCP-пакеты фрагментируются или отбрасываются.

**Решение:** добавь `MTU` явно в конфиг клиента:

```ini
[Interface]
PrivateKey = <CLIENT_PRIVATE_KEY>
Address = 10.0.0.2/24
DNS = 1.1.1.1
MTU = 1420
```

Если `MTU = 1420` не помогает, попробуй `1380`, а потом `1280`.

**Быстрая проверка без изменения конфига:**

```bash
# На клиенте — проверить, какой MTU реально работает:
ping -M do -s 1372 10.0.0.1
```

```bash
# Пример вывода при неправильном MTU (пакет слишком большой):
ping: local error: message too long, mtu=1420

# Пример вывода при правильном MTU:
PING 10.0.0.1 (10.0.0.1) 1372(1400) bytes of data.
64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=19.2 ms
```

---

## 7.5 Практика

Специально выключи клиент и посмотри, как выглядит старый handshake. Потом включи и сравни. Это учит читать `wg show` не как магический вывод, а как состояние туннеля.

Попробуй запустить `sudo tcpdump -i eth0 udp port 51820` на сервере и одновременно подключить клиент — увидишь handshake-пакеты в реальном времени.