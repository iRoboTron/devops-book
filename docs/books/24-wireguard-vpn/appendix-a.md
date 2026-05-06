# Приложение A: Команды WireGuard

## Управление ключами

```bash
# Сгенерировать пару ключей
wg genkey | tee privatekey | wg pubkey > publickey

# Пример приватного ключа (base64, 44 символа):
# kNq1WsE2rTy3uIoP4aS5dFgH6jKlZ7xC8vBnMqR0wA=

# Пример публичного ключа:
# 8J3vQkLmN2+XpR7tYwZ5aB1cDfGhIjKoMnOpQrSt4U=
```

## Управление туннелем

```bash
sudo wg show
sudo wg-quick up wg0
sudo wg-quick down wg0
```

```bash
# Пример вывода sudo wg show:
# interface: wg0
#   public key: 8J3vQkLmN2+XpR7tYwZ5aB1cDfGhIjKoMnOpQrSt4U=
#   private key: (hidden)
#   listening port: 51820
#
# peer: mB4nRsT1qWoP9uYiL6jKxZ3cFvGhDeNaE8sCpA2lO=
#   endpoint: 192.0.2.45:49182
#   allowed ips: 10.0.0.2/32
#   latest handshake: 14 seconds ago
#   transfer: 1.23 KiB received, 652 B sent
```

## Systemd

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
sudo systemctl restart wg-quick@wg0
systemctl status wg-quick@wg0
journalctl -u wg-quick@wg0 --since "1 hour ago"
```

## Firewall

```bash
sudo ufw allow 51820/udp
sudo ufw allow in on wg0 to any port 22 proto tcp
sudo ufw status verbose
```

```bash
# Пример вывода ufw status verbose (после разрешения):
# 51820/udp                  ALLOW IN    Anywhere
# 51820/udp (v6)             ALLOW IN    Anywhere (v6)
```

## Диагностика

```bash
ip route show default
sudo ss -ulnp | grep 51820
sudo tcpdump -i eth0 udp port 51820
sysctl net.ipv4.ip_forward
```

```bash
# Пример вывода ss (порт слушается):
# UNCONN 0  0  0.0.0.0:51820  0.0.0.0:*  users:(("wireguard",pid=1452,fd=1))

# Пример вывода tcpdump (активное соединение):
# 12:45:01.234 IP 192.0.2.45.49182 > 95.216.10.5.51820: UDP, length 148
# 12:45:01.234 IP 95.216.10.5.51820 > 192.0.2.45.49182: UDP, length 92
```