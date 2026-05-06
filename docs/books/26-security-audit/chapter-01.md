# Глава 1: nmap и периметр

> **Цель:** увидеть свой сервер снаружи: какие порты открыты и какие сервисы видны.

---

## 1.1 Простое сканирование

```bash
nmap <YOUR_SERVER_IP> -oN audits/2026-05-06/nmap-basic.txt
```

**Пример вывода:**

```
# Пример вывода:
Starting Nmap 7.94 ( https://nmap.org ) at 2026-05-06 14:23 UTC
Nmap scan report for 203.0.113.42
Host is up (0.031s latency).
Not shown: 996 filtered tcp ports (no-response)
PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https
8080/tcp open  http-proxy

Nmap done: 1 IP address (1 host up) scanned in 12.43 seconds
```

**Как читать вывод:**

- `Host is up (0.031s latency)` — сервер отвечает на ping, задержка 31 мс. Если очень высокая (>200 мс) — сервер перегружен или далеко.
- `Not shown: 996 filtered tcp ports (no-response)` — 996 портов не ответили (firewall молча их дропает). Это нормально.
- `PORT STATE SERVICE` — таблица открытых портов.
- `22/tcp open ssh` — порт 22, протокол TCP, **открыт**, сервис — SSH. Ожидается.
- `443/tcp open https` — HTTPS, ожидается.
- `8080/tcp open http-proxy` — **это неожиданно!** Откуда взялся 8080?

**Неожиданный порт 8080 — как расследовать:**

```bash
# Смотрим, какой процесс слушает порт 8080
ss -tlnp | grep 8080
```

```
# Пример вывода:
LISTEN 0 511 0.0.0.0:8080 0.0.0.0:* users:(("node",pid=1842,fd=18))
```

Порт слушает Node.js-процесс (pid 1842). Скорее всего это dev-сервер, который забыли остановить. Нужно закрыть через ufw или остановить процесс.

---

Состояния портов:

| State | Значение |
|---|---|
| open | сервис отвечает — видно снаружи |
| closed | порт закрыт, но IP отвечает TCP RST — видно что порт существует |
| filtered | firewall фильтрует, ответа нет — снаружи непонятно есть ли сервис |

---

## 1.2 Версии сервисов

```bash
nmap -sV <YOUR_SERVER_IP> -oN audits/2026-05-06/nmap-versions.txt
```

**Пример вывода:**

```
# Пример вывода:
Starting Nmap 7.94 ( https://nmap.org ) at 2026-05-06 14:27 UTC
Nmap scan report for 203.0.113.42
Host is up (0.030s latency).
Not shown: 996 filtered tcp ports (no-response)
PORT    STATE SERVICE  VERSION
22/tcp  open  ssh      OpenSSH 8.9p1 Ubuntu 3ubuntu0.6 (Ubuntu Linux; protocol 2.0)
80/tcp  open  http     nginx 1.24.0
443/tcp open  ssl/http nginx 1.24.0
8080/tcp open http     Node.js Express framework

Nmap done: 1 IP address (1 host up) scanned in 18.72 seconds
```

**Как читать вывод с версиями:**

- `OpenSSH 8.9p1 Ubuntu 3ubuntu0.6` — версия SSH. Проверь, нет ли для неё CRITICAL CVE в базе (команда `trivy` или сайт nvd.nist.gov).
- `nginx 1.24.0` — актуальная версия nginx. Если увидишь `nginx/1.14.0` — это старая версия из Ubuntu 18.04, нужно обновить.
- `Node.js Express framework` — nmap опознал фреймворк. Это значит порт открыт и сервис реально отвечает.

Ищи неожиданное: `8080`, `3000`, `5432`, `6379`, панели администрирования, тестовые сервисы.

---

## 1.3 Проблемы при сканировании

**Если nmap показывает «host seems down»:**

```
Note: Host seems down. If it is really up, but blocking our ping probes, try -Pn
Nmap done: 1 IP address (1 host up) scanned in 3.05 seconds
```

Сервер блокирует ICMP (ping). Добавь `-Pn` чтобы пропустить проверку доступности:

```bash
nmap -Pn <YOUR_SERVER_IP> -oN audits/2026-05-06/nmap-basic.txt
```

**Если nmap идёт очень долго** — сканирует по одному порту. Для базовой проверки достаточно топ-1000 портов (по умолчанию). Для полного сканирования:

```bash
# Только если реально нужно — займёт 5-20 минут
nmap -p- <YOUR_SERVER_IP>
```

---

## 1.4 Расширенные флаги

```bash
sudo nmap -O <YOUR_SERVER_IP>
nmap -p- <YOUR_SERVER_IP>
```

`-O` определяет операционную систему — требует root и генерирует больше трафика. `-p-` сканирует все 65535 портов и идёт дольше. Используй только для своего IP.

---

## 1.5 Практика

Сделай таблицу:

| Порт | Сервис | Ожидался? | Что сделать |
|---|---|---|---|
| 22 | ssh | да | оставить/ограничить |
| 443 | https | да | проверить TLS |
| 3000 | unknown | нет | закрыть |

Проверка: каждый open-порт объяснён.
