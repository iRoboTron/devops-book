# Глава 2: Установка и подготовка сервера

> **Цель:** поставить WireGuard и подготовить сервер, не потеряв доступ.

---

## 2.1 Перед началом

Перед изменениями на реальном сервере:

- открой второй SSH-сеанс и не закрывай первый;
- проверь доступ к консоли провайдера;
- запиши текущие правила firewall;
- не меняй SSH и firewall одновременно.

---

## 2.2 Установка

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install wireguard
```

```bash
# Пример вывода:
Reading package lists... Done
Building dependency tree... Done
The following additional packages will be installed:
  wireguard-tools wireguard-dkms
The following NEW packages will be installed:
  wireguard wireguard-dkms wireguard-tools
0 upgraded, 3 newly installed, 0 to remove and 0 not upgraded.
Setting up wireguard-tools (1.0.20210914-1) ...
Setting up wireguard (1.0.20210914-1) ...
```

Проверка:

```bash
wg --version
```

```bash
# Пример вывода:
wireguard-tools v1.0.20210914 - https://git.zx2c4.com/wireguard-tools/
```

```bash
sudo modprobe wireguard
lsmod | grep wireguard
```

```bash
# Пример вывода:
wireguard              98304  0
ip6_udp_tunnel         16384  1 wireguard
udp_tunnel             28672  1 wireguard
```

> **Если что-то пошло не так:**
>
> **Ошибка: «Module wireguard not found»** — ядро слишком старое (< 5.6). Варианты:
> - Ubuntu 18.04/20.04: установить `linux-modules-extra-$(uname -r)` или обновить ядро через `linux-generic-hwe-20.04`.
> - Debian 10 (Buster): добавить репозиторий backports: `echo "deb http://deb.debian.org/debian buster-backports main" | sudo tee /etc/apt/sources.list.d/backports.list && sudo apt update && sudo apt install -t buster-backports wireguard`.
> - Если ни один из вариантов не помогает — обновить сервер до Ubuntu 22.04 (WireGuard встроен в ядро 5.15+).

---

## 2.3 IP forwarding

Если VPN нужен только для доступа к самому серверу, forwarding может не понадобиться. Если клиент должен ходить через сервер дальше, нужен forwarding.

Временно:

```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```

Постоянно:

```bash
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl -p /etc/sysctl.d/99-wireguard.conf
```

```bash
# Пример вывода:
net.ipv4.ip_forward = 1
```

Проверка:

```bash
sysctl net.ipv4.ip_forward
```

```bash
# Пример вывода:
net.ipv4.ip_forward = 1
```

---

## 2.4 Внешний интерфейс

Не всегда он называется `eth0`.

```bash
ip route show default
```

```bash
# Пример вывода:
default via 95.216.10.1 dev eth0 proto static
```

В строке `dev eth0` имя после `dev` — внешний интерфейс. Его нужно использовать в NAT-правилах, если делаешь full tunnel. На облачных серверах он может называться `ens3`, `ens4`, `enp1s0` или `ens160` — всё зависит от гипервизора.