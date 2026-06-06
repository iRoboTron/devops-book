# Глава 10: Docker networking — bridge, host, overlay, network namespaces

## Что вы узнаете

- Как Docker изолирует сетевые пространства контейнеров через network namespaces
- Разница между bridge, host, none и overlay сетями
- Как контейнеры находят друг друга по имени
- Как диагностировать проблемы сети в Docker

**Цель главы:** когда контейнер «не видит» другой, вы знаете почему и как исправить.

---

## Схема — Docker bridge topology

```
Хост
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  docker0 (172.17.0.1)      br-abc123 (172.18.0.1)          │
│      │                           │                          │
│   ┌──┴──────┐               ┌────┴────┐                     │
│   │ eth0    │               │ eth0    │                     │
│   │ c1      │               │ c2   c3 │                     │
│   │172.17.  │               │172.18.  │                     │
│   │0.2      │               │0.2  0.3 │                     │
│   └─────────┘               └─────────┘                     │
│                                                             │
│  eth0 хоста (192.168.1.10) ──► внешняя сеть                │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Network namespaces — основа изоляции

Каждый контейнер работает в собственном network namespace. Это значит, что у контейнера собственный стек TCP/IP: свои интерфейсы, таблицы маршрутизации, правила iptables, сокеты.

### Схема изоляции namespace

```
┌─────────────────────────────────────────────────┐
│                   Хост (root ns)                 │
│  lo: 127.0.0.1        eth0: 192.168.1.10        │
│  ┌──────────────┐     ┌──────────────┐          │
│  │  c1 (ns1)    │     │  c2 (ns2)    │          │
│  │  lo: 127.0.0.1│    │  lo: 127.0.0.1│         │
│  │  eth0@if5    │     │  eth0@if7    │          │
│  └──────┬───────┘     └──────┬───────┘          │
│         │ veth pair         │ veth pair         │
│    ┌────┴──────┐       ┌────┴──────┐           │
│    │  veth5    │       │  veth7    │           │
│    └───────────┘       └───────────┘           │
│         │                   │                   │
│    ┌────┴───────────────────┴────┐             │
│    │       docker0 (bridge)      │             │
│    └─────────────────────────────┘             │
└─────────────────────────────────────────────────┘
```

### На чём это основано

Docker использует **veth pair** (virtual Ethernet) — две виртуальные сетевые карты, соединённые «кабелем»: один конец в namespace контейнера, второй — в namespace хоста, подключён к мосту (bridge).

### Посмотреть namespace

```bash
# Список всех network namespace
sudo lsns -t net

# Узнать PID контейнера и войти в его namespace
docker inspect --format '{{.State.Pid}}' mycontainer
sudo nsenter -t $(docker inspect --format '{{.State.Pid}}' mycontainer) -n ip addr
```

### Проверка изоляции

```bash
# Внутри контейнера — свои интерфейсы
docker exec -it mycontainer ip addr

# На хосте — другие
ip addr
```

> ☠️ **Осторожно:** `iptables -F` на хосте полностью ломает сеть всем работающим контейнерам, потому что Docker полагается на правила iptables для NAT и фильтрации.

### Почему это важно

Понимание network namespaces объясняет:

- Почему у контейнера нет доступа к интерфейсам хоста
- Почему `iptables -F` на хосте роняет сеть контейнерам
- Как veth pair связывает изолированное пространство с внешним миром

---

## 2. Типы Docker-сетей

| Тип | Описание | Когда использовать |
|-----|----------|-------------------|
| **bridge** | Виртуальный мост на хосте, стандартная для изолированных контейнеров | Большинство случаев, несколько контейнеров на одном хосте |
| **host** | Контейнер использует сетевой стек хоста без изоляции | Максимальная производительность, сервисы на портах хоста |
| **none** | Только loopback, без внешнего доступа | Аудит-контейнеры, задачи без сети |
| **overlay** | Мост через несколько хостов (Swarm) | Multi-host кластеры |
| **macvlan** | Контейнеру назначается MAC-адрес из подсети | Интеграция с существующей сетевой инфраструктурой |

```bash
# Список сетей
docker network ls

# Детальная информация
docker network inspect bridge
```

---

## 3. Bridge-сеть по умолчанию

### Default bridge (docker0)

При установке Docker создаёт мост `docker0` с подсетью `172.17.0.0/16`.

```bash
# Посмотреть информацию о bridge-сети
docker network inspect bridge
```

В сети `bridge` по умолчанию контейнеры общаются по **IP**, но **НЕ** по имени. Docker не добавляет DNS-резолвинг для контейнеров в default bridge.

```bash
# Пример: контейнеры видят друг друга по IP, но не по имени
docker run -d --name web1 nginx
docker run -it --name web2 alpine sh

# Внутри web2:
ping web1          # ❌ не сработает
ping 172.17.0.2   # ✅ сработает
```

### Пользовательская bridge-сеть

```bash
# Создать свою bridge-сеть
docker network create --driver bridge --subnet 172.20.0.0/16 mynet

# Запустить контейнеры в этой сети
docker run -d --network mynet --name app1 nginx
docker run -d --network mynet --name app2 nginx

# Внутри app2:
ping app1   # ✅ работает — встроенный DNS
```

**Ключевое отличие:** в пользовательской bridge-сети Docker предоставляет встроенный DNS-сервер на `127.0.0.11`. Контейнеры разрешаются по имени.

```bash
# Подключить существующий контейнер к сети
docker network connect mynet container1

# Отключить
docker network disconnect mynet container1
```

---

## 4. Docker DNS — как контейнеры находят друг друга

### Как работает

Docker запускает встроенный DNS-сервер на `127.0.0.11:53` внутри каждого контейнера. Когда контейнер пингует другой по имени, запрос идёт на `127.0.0.11`, Docker определяет IP в той же сети и возвращает ответ.

### Проверка

```bash
# Создаём сеть
docker network create demo

# Запускаем контейнер с именем db
docker run -d --network demo --name db \
  -e POSTGRES_PASSWORD=secret \
  postgres:16-alpine

# Запускаем клиент
docker run -it --network demo --name app alpine sh
```

Внутри контейнера `app`:

```bash
# DNS резолвинг работает
ping db

# Проверить resolv.conf
cat /etc/resolv.conf
# nameserver 127.0.0.11

# Тест DNS
nslookup db
```

### Ограничения

- DNS работает **только в пределах одной пользовательской bridge-сети**
- Контейнеры в разных bridge-сетях не видят друг друга по имени
- Default bridge (`docker0`) **не** имеет встроенного DNS

---

## 5. Host-сеть

Режим `--network host` отключает сетевую изоляцию: контейнер использует сетевой стек хоста напрямую.

```bash
# Запуск nginx в host-режиме
docker run --network host -d nginx

# nginx доступен на порту 80 хоста без -p
curl http://localhost:80
```

| Характеристика | Bridge | Host |
|----------------|--------|------|
| Изоляция | Полная | Нет |
| NAT | Да | Нет |
| Производительность | Ниже (проброс портов) | Максимум |
| Конфликт портов | Нет (маппинг) | Да |
| DNS по имени | Да (user bridge) | Зависит от хоста |

> ☠️ **Осторожно:** в host-режиме каждый порт, который открывает контейнер, сразу доступен на хосте. Два контейнера в host-режиме не могут слушать один и тот же порт.

---

## 6. Порты и NAT

### Проброс портов

```bash
# Пробросить порт 8080 хоста на 80 контейнера
docker run -p 8080:80 nginx

# Привязать к конкретному интерфейсу
docker run -p 127.0.0.1:8080:80 nginx
```

### Как это работает

Docker добавляет DNAT-правило в iptables:

```bash
# Посмотреть правила NAT, созданные Docker
sudo iptables -t nat -L DOCKER -n -v
```

Пример вывода:

```
Chain DOCKER (2 references)
 pkts bytes target     prot opt in     out     source         destination
    0     0 DNAT       tcp  --  !docker0 *       0.0.0.0/0     0.0.0.0/0
                     tcp dpt:8080 to:172.17.0.2:80
```

### Поток трафика

```
Внешний клиент
     │
     ▼
eth0 хоста:8080
     │
     ▼
iptables PREROUTING → DNAT → 172.17.0.2:80
     │
     ▼
docker0 (bridge)
     │
     ▼
Контейнер:80
```

### Важные нюансы

- Если контейнер перезапускается, его IP может измениться — DNAT-правило обновится автоматически
- При `-p 127.0.0.1:8080:80` порт доступен только локально
- Docker автоматически управляет iptables — ручные изменения могут быть сброшены

```bash
# Отобразить все пробросы портов
docker port mycontainer
```

---

## 7. Диагностика сети контейнера

### Базовые проверки изнутри контейнера

```bash
# Зайти в контейнер
docker exec -it mycontainer sh

# Проверить сетевые интерфейсы
ip addr

# Проверить маршрутизацию
ip route

# Проверить DNS
cat /etc/resolv.conf
cat /etc/hosts

# Проверить доступность
ping db
ping 8.8.8.8
curl -v http://db:8080
```

### Проверка снаружи (с хоста)

```bash
# Полная информация о сети контейнера
docker inspect mycontainer \
  --format '{{.NetworkSettings.Networks}}'

# Получить IP контейнера
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' mycontainer

# Просмотр DNS
docker exec mycontainer nslookup db

# Процесс контейнера
docker top mycontainer

# Логи
docker logs mycontainer
```

### Диагностика iptables

```bash
# Проверить, что правила Docker существуют
sudo iptables -t nat -L POSTROUTING -n -v

# Проверить форвардинг
sudo iptables -L FORWARD -n -v

# Включить форвардинг (если выключен)
sudo sysctl net.ipv4.ip_forward
sudo sysctl -w net.ipv4.ip_forward=1
```

### Типовой сценарий: контейнер не пингуется

```bash
# 1. Проверить, в одной ли сети контейнеры
docker inspect web1 --format '{{.NetworkSettings.Networks}}'
docker inspect web2 --format '{{.NetworkSettings.Networks}}'

# 2. Проверить, что сервис слушает на 0.0.0.0, а не 127.0.0.1
docker exec web2 netstat -tlnp

# 3. Проверить iptables
sudo iptables -L DOCKER -n -v

# 4. Проверить ip_forward
cat /proc/sys/net/ipv4/ip_forward
```

---

## Типичные ошибки

> ☠️ **Ошибка 1: контейнеры в разных сетях**

Симптом: ping по имени не работает, хотя контейнеры на одном хосте.

Решение: поместите контейнеры в одну пользовательскую bridge-сеть. Default bridge не поддерживает DNS по имени.

```bash
docker network create shared
docker network connect shared web1
docker network connect shared web2
```

> ☠️ **Ошибка 2: сервис слушает на 127.0.0.1 внутри контейнера**

Симптом: curl к контейнеру зависает или connection refused, хотя порт опубликован.

Причина: приложение сконфигурировано на `127.0.0.1` — это loopback внутри контейнера, недоступный снаружи.

Решение: настройте приложение на `0.0.0.0` или `172.x.x.x`.

> ☠️ **Ошибка 3: ручное изменение iptables**

Симптом: после `iptables -F` или `iptables -P FORWARD DROP` контейнеры теряют сеть.

Решение: не редактируйте iptables вручную. Используйте `--iptables=false` в Docker daemon, если нужно ручное управление.

```bash
# Восстановить
sudo systemctl restart docker
```

> ☠️ **Ошибка 4: порт занят на хосте**

Симптом: `docker: Error response from daemon: driver failed programming external connectivity`.

Решение: сменить порт или остановить процесс, занявший порт.

```bash
sudo lsof -i :8080
```

---

## Чек-лист

- [ ] Контейнеры находятся в одной пользовательской bridge-сети (не default)
- [ ] Приложение внутри контейнера слушает на `0.0.0.0`, а не `127.0.0.1`
- [ ] Правила iptables не изменялись вручную; `net.ipv4.ip_forward = 1`
- [ ] Порт на хосте не занят и опубликован через `-p` host:container
- [ ] DNS-резолвинг работает: `cat /etc/resolv.conf` показывает `127.0.0.11`
- [ ] Veth pair создана: оба конца видны (`ip link` на хосте и в контейнере)
- [ ] Контейнеры используют одну версию протокола (IPv4/IPv6)

---

## Попробуйте сами

### Задание 1: Изоляция namespace

```bash
# 1. Запустите контейнер alpine в фоне
docker run -d --name nettest alpine sleep 3600

# 2. Найдите PID контейнера
docker inspect --format '{{.State.Pid}}' nettest

# 3. Сравните ip addr на хосте и внутри namespace
sudo nsenter -t $(docker inspect --format '{{.State.Pid}}' nettest) -n ip addr
ip addr
```

**Вопрос:** какие интерфейсы отличаются? Почему?

---

### Задание 2: Bridge сетевое взаимодействие

```bash
# 1. Создайте пользовательскую bridge-сеть
docker network create --driver bridge --subnet 10.99.0.0/24 testnet

# 2. Запустите два контейнера с именами
docker run -d --network testnet --name server nginx
docker run -d --network testnet --name client alpine sleep 3600

# 3. Проверьте DNS-резолвинг
docker exec client nslookup server

# 4. Сделайте запрос к nginx по имени
docker exec client wget -q -O- http://server:80
```

**Вопрос:** почему в default bridge это не сработало бы?

---

### Задание 3: Диагностика проблемы

Дано:

```bash
# Контейнер database запущен так:
docker run -d --name database postgres:16-alpine -e POSTGRES_PASSWORD=secret

# Контейнер app запущен так:
docker run -d --name app alpine sleep 3600
```

**Проблема:** из контейнера `app` команда `ping database` не работает. Найдите причину и исправьте.

Ожидаемое решение:

```bash
# 1. Создайте общую сеть
docker network create appnet

# 2. Подключите оба контейнера
docker network connect appnet database
docker network connect appnet app

# 3. Проверьте
docker exec app ping database
```

**Бонус:** напишите docker-compose.yml, где эта проблема решена заранее.

---
