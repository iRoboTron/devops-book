# Приложение A: Шпаргалка команд + Матрица симптомов

## Матрица симптомов

| Симптом | Инструмент | Что искать в выводе |
|---------|-----------|---------------------|
| Connection refused | `ss -tlnp \| grep :PORT` | `LISTEN` в первой колонке? |
| Connection timed out | `iptables -L -n -v` | `DROP`/`REJECT` правила? |
| Connection timed out | `traceroute -n host` | Где обрыв (звёздочки)? |
| DNS не резолвит | `dig @8.8.8.8` | `NXDOMAIN` vs `SERVFAIL`? |
| Сертификат истёк | `openssl s_client` | `notAfter` дата |
| Сервис медленный | `curl -w "%{time_total}"` | Тайминги по фазам |
| Потери пакетов | `mtr --report` | Потери на последнем хопе? |
| Порт занят | `ss -tlnp` | Process колонка |
| Docker не видит другой | `docker network inspect` | Общая сеть? |
| K8s сервис не отвечает | `kubectl get endpoints` | Пустой список? |

---

## IP и интерфейсы

```bash
# Показать все интерфейсы
ip addr

# Показать только UP интерфейсы
ip link show up

# Показать IP конкретного интерфейса
ip addr show eth0

# Показать MAC-адреса
ip link

# Поднять/опустить интерфейс
sudo ip link set eth0 up
sudo ip link set eth0 down

# Добавить IP на интерфейс
sudo ip addr add 192.168.1.100/24 dev eth0

# Удалить IP
sudo ip addr del 192.168.1.100/24 dev eth0

# Посмотреть таблицу маршрутизации
ip route

# Посмотреть только default gateway
ip route | grep default

# Куда пойдёт пакет до хоста
ip route get 8.8.8.8
ip route get 10.0.1.50

# Добавить статический маршрут
sudo ip route add 10.0.0.0/16 via 192.168.1.1

# Удалить статический маршрут
sudo ip route del 10.0.0.0/16

# Посмотреть ARP-таблицу (соседи по L2)
ip neigh
```

---

## TCP/UDP и порты

```bash
# Все слушающие TCP сокеты с процессами
sudo ss -tlnp

# Все слушающие UDP сокеты с процессами
sudo ss -ulnp

# Все сокеты (включая соединения), слушающие и установленные
sudo ss -tlnpa

# Фильтр по порту
sudo ss -tlnp | grep :80

# Активные соединения на порт
sudo ss -tnp dst :443

# Статистика сокетов
ss -s

# Открытые порты (альтернатива)
sudo lsof -i :80
```

---

## DNS

```bash
# Базовый запрос
dig example.com

# Короткий ответ (только IP)
dig +short example.com

# Запрос к конкретному DNS-серверу
dig @8.8.8.8 example.com

# Запрос MX-записи
dig mx example.com

# Обратный DNS-запрос
dig -x 8.8.8.8

# Трассировка DNS (пошагово от корневых серверов)
dig +trace example.com

# nslookup (если нет dig)
nslookup example.com
nslookup example.com 8.8.8.8

# host (упоротый минимум)
host example.com
host 8.8.8.8

# Кто резолвер?
cat /etc/resolv.conf

# systemd-resolved
resolvectl status
sudo resolvectl flush-caches

# /etc/hosts
cat /etc/hosts
```

---

## HTTP

```bash
# GET запрос с заголовками
curl -v http://example.com

# Только заголовки
curl -I http://example.com

# POST с данными
curl -X POST -d '{"key":"value"}' -H 'Content-Type: application/json' http://example.com/api

# Следовать редиректам
curl -L http://example.com

# Тайминги детально
curl -w "\nTCP: %{time_connect}\nSSL: %{time_appconnect}\nTTFB: %{time_starttransfer}\nTotal: %{time_total}\n" -o /dev/null -s https://example.com

# Смотреть только response code
curl -s -o /dev/null -w "%{http_code}" http://example.com

# Базовый тест с таймаутом
curl --connect-timeout 5 --max-time 10 http://example.com

# Свой User-Agent
curl -A "Mozilla/5.0 (X11; Linux x86_64)" http://example.com
```

---

## SSL/TLS

```bash
# Получить сертификат и даты
echo | openssl s_client -connect example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Полная цепочка сертификатов
echo | openssl s_client -connect example.com:443 -showcerts 2>/dev/null

# Subject и SAN
echo | openssl s_client -connect example.com:443 2>/dev/null | \
  openssl x509 -noout -subject -ext subjectAltName

# Проверить OCSP (не отозван ли?)
echo | openssl s_client -connect example.com:443 -status 2>/dev/null | \
  grep -A 10 "OCSP response"

# Проверить локальный сертификат
openssl x509 -in /etc/letsencrypt/live/example.com/fullchain.pem -noout -dates

# Проверить полную цепочку локального сертификата
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt \
  /etc/letsencrypt/live/example.com/fullchain.pem

# Создать самоподписанный сертификат (для теста)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt -subj "/CN=example.com"
```

---

## Диагностика

```bash
# Проверка связности
ping -c 3 8.8.8.8

# Трассировка маршрута
traceroute -n 8.8.8.8

# Traceroute с потерями и latency
mtr --report -c 10 8.8.8.8

# Проверка MTU
ping -M do -s 1472 8.8.8.8

# Тест пропускной способности
# Сервер: iperf3 -s
# Клиент: iperf3 -c 192.168.1.10

# Проверка порта
nc -zv host 80
nc -zvu host 53  # UDP

# Сканирование портов
nmap -sn 192.168.1.0/24    # Ping scan
nmap -sT -p 22,80,443 host # TCP connect scan
```

---

## iptables (nftables)

```bash
# Все правила
sudo iptables -L -n -v

# Только NAT таблица
sudo iptables -t nat -L -n -v

# Счётчики пакетов по цепочкам
sudo iptables -L -n -v | head -20

# Сохранить и восстановить
sudo iptables-save > /tmp/rules.bak
sudo iptables-restore < /tmp/rules.bak

# Сбросить все правила
sudo iptables -F && sudo iptables -t nat -F

# nftables (современная замена)
sudo nft list ruleset
```

---

## Docker networking

```bash
# Список сетей
docker network ls

# Детали сети (подключенные контейнеры, IP, gateway)
docker network inspect bridge

# Сеть конкретного контейнера
docker inspect container1 --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}: {{$v.IPAddress}}{{"\n"}}{end}}'

# Проверить связность из контейнера
docker exec container1 ping -c 2 container2
docker exec container1 nslookup container2
docker exec container1 nc -zv container2 80

# Прослушка портов внутри контейнера
docker exec container2 ss -tlnp

# Создать сеть
docker network create --driver bridge --subnet 172.20.0.0/16 mynet

# Подключить контейнер к сети
docker network connect mynet container1

# Логи контейнера
docker logs container1

# Трафик контейнера (если нужно tcpdump на хосте)
# Найти veth интерфейс контейнера на хосте
docker exec container1 cat /sys/class/net/eth0/iflink
# Потом tcpdump -i vethXXXXX
```

---

## Kubernetes networking

```bash
# Поды с IP и нодами
kubectl get pods -o wide

# Сервисы
kubectl get svc
kubectl get endpoints
kubectl describe svc my-service

# DNS внутри кластера
kubectl run test --image=busybox -it --rm -- nslookup my-service

# Диагностика из debug-пода
kubectl run debug --image=nicolaka/netshoot -it --rm -- bash

# Проверить Network Policies
kubectl get networkpolicies --all-namespaces

# CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns

# Port-forward для теста
kubectl port-forward svc/my-service 8080:80

# Прослушка портов внутри пода
kubectl exec mypod -- ss -tlnp
```

---

## Установка нужных пакетов

```bash
sudo apt install -y dnsutils netcat-openbsd mtr iperf3 nmap curl openssl
```
