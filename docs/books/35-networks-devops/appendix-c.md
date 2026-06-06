# Приложение C: Алгоритмы диагностики — флоучарты

## 1. Общий алгоритм диагностики сетевой проблемы

```mermaid
flowchart TD
    START[Сервис недоступен] --> L3_PING{ping до хоста?}
    
    L3_PING -->|Нет| L3_CHECK[Проверить L3]
    L3_CHECK --> IP_ROUTE{ip route get host}
    IP_ROUTE -->|Нет маршрута| GW[Проверить default gateway<br/>ip route | grep default]
    IP_ROUTE -->|Есть маршрут| TRACE[traceroute -n host]
    TRACE -->|Обрыв на хопе N| HOP[Проверить хоп N:<br/>файрвол, маршрутизатор, кабель]
    TRACE -->|Все хопы проходят| IFACE[Проверить интерфейс:<br/>ip link, ethtool]
    GW --> FIX_GW[Настроить default gateway<br/>или проверить ISP]
    IFACE --> LINK{Link detected?}
    LINK -->|Нет| CABLE[Проверить кабель/коммутатор<br/>sudo ethtool eth0]
    LINK -->|Да| FIX_L3[Проверить IP/маску<br/>ip addr, DHCP]
    
    L3_PING -->|Да| L4_NC{nc -zv host port?}
    
    L4_NC -->|Нет| L4_CHECK[Проверить L4]
    L4_CHECK --> SS{ss -tlnp | grep :PORT}
    SS -->|Процесс есть| FW[iptables -L -n -v]
    SS -->|Нет процесса| PROC[Проверить сервис:<br/>systemctl status, journalctl]
    FW -->|Есть DROP правило| DROP[Разрешить порт в iptables]
    FW -->|Нет DROP| SG[Проверить Security Group /<br/>UFW / cloud firewall]
    PROC --> START_PROC[sudo systemctl start service]
    
    L4_NC -->|Да| L7_CURL{curl -v URL?}
    
    L7_CURL -->|Ошибка TLS| TLS_CHECK[Проверить SSL/TLS]
    L7_CURL -->|Ошибка HTTP 4xx/5xx| HTTP_CHECK[Проверить конфиг веб-сервера<br/>и логи приложения]
    L7_CURL -->|Ошибка DNS| DNS_CHECK[Проверить DNS]
    L7_CURL -->|OK| CORRECT{Ответ правильный?}
    
    CORRECT -->|Да| NOT_NETWORK[Проблема не в сети:<br/>смотри метрики, БД, код]
    CORRECT -->|Нет| APP_LOGIC[Проверить логику приложения:<br/>API, данные, кэш]
    
    TLS_CHECK --> TLS_DATES{Дата истекла?}
    TLS_DATES -->|Да| RENEW[sudo certbot renew]
    TLS_DATES -->|Нет| TLS_CHAIN{Цепочка полная?}
    TLS_CHAIN -->|Нет| FIX_CHAIN[Проверить fullchain.pem<br/>в конфиге nginx]
    TLS_CHAIN -->|Да| TLS_HOST{CN/SAN совпадает?}
    TLS_HOST -->|Нет| FIX_HOST[Перевыпустить сертификат<br/>на правильное имя]
    TLS_HOST -->|Да| TLS_OCSP{OCSP — не отозван?}
    TLS_OCSP -->|Отозван| REISSUE[Срочно перевыпустить]
    TLS_OCSP -->|OK| NOT_NETWORK
    
    DNS_CHECK --> DIG{dig @8.8.8.8 работает?}
    DIG -->|Нет| L3_PING
    DIG -->|Да| RESOLV{dig без @ работает?}
    RESOLV -->|Нет| RESOLVER[Проверить /etc/resolv.conf<br/>и resolvectl]
    RESOLV -->|Да| HOSTS{Запись в /etc/hosts?}
    HOSTS -->|Да, неверная| FIX_HOSTS[Исправить /etc/hosts]
    HOSTS -->|Нет| DNS_OK[DNS работает]
    RESOLVER --> FIX_RESOLV[Настроить DNS<br/>resolvectl dns eth0 8.8.8.8]
    
    DOCKER{Контейнерный<br/>сценарий?} --- L4_NC
    DOCKER --> NET_INSPECT[docker network inspect]
    NET_INSPECT --> SAME_NET{Контейнеры<br/>в одной сети?}
    SAME_NET -->|Нет| CONNECT[docker network connect]
    SAME_NET -->|Да| DOCKER_DNS{docker exec nslookup name?}
    DOCKER_DNS -->|Не резолвит| DOCKER_COMPOSE[Проверить docker-compose.yml<br/>docker-compose v1 vs v2]
    DOCKER_DNS -->|OK| DOCKER_SS{docker exec ss -tlnp?}
    DOCKER_SS -->|Порт не слушается| DOCKER_SVC[Запустить сервис внутри]
    DOCKER_SS -->|OK| DOCKER_OK[Сеть в порядке]
    
    style START fill:#f66,stroke:#333,color:#fff
    style NOT_NETWORK fill:#6f6,stroke:#333,color:#000
    style FIX_GW fill:#ff9,stroke:#333
    style CABLE fill:#ff9,stroke:#333
    style DROP fill:#ff9,stroke:#333
    style RENEW fill:#ff9,stroke:#333
    style FIX_RESOLV fill:#ff9,stroke:#333
```

---

## 2. Алгоритм диагностики DNS

```mermaid
flowchart TD
    START[Проблема: имя не резолвится] --> PING{ping 8.8.8.8?}
    
    PING -->|Нет| NETWORK[Проблема с сетью<br/>см. общий алгоритм L3]
    PING -->|Да| HOSTS{/etc/hosts содержит<br/>неверную запись?}
    
    HOSTS -->|Да| FIX_HOSTS[Исправить/удалить<br/>строку в /etc/hosts]
    HOSTS -->|Нет| RESOLVECONF{/etc/resolv.conf<br/>корректный?}
    
    RESOLVECONF -->|Нет| FIX_RESOLV[Настроить nameserver<br/>resolvectl dns eth0 8.8.8.8]
    RESOLVECONF -->|Да| RESOLVECTL{resolvectl status<br/>показывает DNS?}
    
    RESOLVECTL -->|Нет| FIX_RESOLV
    RESOLVECTL -->|Да| DIG_PUBLIC{dig @8.8.8.8<br/>example.com?}
    
    DIG_PUBLIC -->|NXDOMAIN| DOMAIN[Запись не существует<br/>Проверить DNS-зону<br/>Проверить имя домена]
    DIG_PUBLIC -->|SERVFAIL| DNS_SERVER[Проблема на DNS-сервере<br/>Проверить авторитативный DNS]
    DIG_PUBLIC -->|NOERROR + IP| DIG_LOCAL{dig example.com<br/>(локальный резолвер)?}
    
    DIG_LOCAL -->|NOERROR| DNS_OK[Проблема не в DNS<br/>Смотри приложение / кэш]
    DIG_LOCAL -->|SERVFAIL| LOCAL_DNS[Проблема локального резолвера]
    DIG_LOCAL -->|NXDOMAIN| LOCAL_DNS
    DIG_LOCAL -->|REFUSED| LOCAL_DNS
    
    LOCAL_DNS --> RESOLVER_CHECK{Какой резолвер?}
    RESOLVER_CHECK -->|systemd-resolved| SYSTEMD[Проверить<br/>resolvectl status<br/>resolvectl dns eth0]
    RESOLVER_CHECK -->|dnsmasq| DNSMASQ[Проверить<br/>systemctl status dnsmasq<br/>journalctl -u dnsmasq]
    RESOLVER_CHECK -->|bind/named| BIND[Проверить<br/>systemctl status named<br/>journalctl -u named]
    RESOLVER_CHECK -->|Вручную<br/>/etc/resolv.conf| MANUAL[Проверить IP nameserver'а<br/>и доступ до него]
    
    SYSTEMD --> FLUSH_CACHE[sudo resolvectl flush-caches]
    DNSMASQ --> RESTART_DNSMASQ[sudo systemctl restart dnsmasq]
    MANUAL --> PING_NS{ping до nameserver?}
    PING_NS -->|Нет| NETWORK
    PING_NS -->|Да| NS_PORT{nc -zuv nameserver 53?}
    NS_PORT -->|Нет| NS_FW[Проверить файрвол<br/>до DNS-сервера]
    NS_PORT -->|Да| NS_BAD[Проблема на DNS-сервере<br/>логи, зоны]
    
    DIG_LOCAL -->|NXDOMAIN<br/>но публичный OK| CACHE[Кэш DNS устарел<br/>Очистить: resolvectl flush-caches]
    
    style START fill:#f66,stroke:#333,color:#fff
    style DNS_OK fill:#6f6,stroke:#333,color:#000
    style FIX_HOSTS fill:#ff9,stroke:#333
    style FIX_RESOLV fill:#ff9,stroke:#333
    style FLUSH_CACHE fill:#ff9,stroke:#333
```

---

## 3. Алгоритм диагностики HTTPS/TLS

```mermaid
flowchart TD
    START[Проблема: SSL/TLS error] --> DATES{openssl s_client<br/>Дата истечения?}
    
    DATES -->|expired| RENEW[sudo certbot renew]
    DATES -->|not yet valid| CLOCK[Проверить дату на сервере<br/>date, timedatectl, ntp]
    DATES -->|OK| CHAIN{Цепочка полная?<br/>openssl s_client -showcerts}
    
    CHAIN -->|Нет| FIX_CHAIN[Исправить nginx:<br/>ssl_certificate = fullchain.pem<br/>(не cert.pem)]
    CHAIN -->|Да| HOSTNAME{CN/SAN совпадает<br/>с доменом?}
    
    HOSTNAME -->|Нет| REISSUE[Перевыпустить сертификат<br/>с правильным CN/SAN]
    HOSTNAME -->|Да| OCSP{OCSP статус —<br/>не отозван?}
    
    OCSP -->|Revoked| REVOKE[Сертификат отозван<br/>Срочно перевыпустить]
    OCSP -->|OK| SELF_SIGNED{Самоподписанный<br/>сертификат?}
    
    SELF_SIGNED -->|Да| TESTING[Это тестовый стенд?<br/>OK — добавь -k в curl<br/>или импортируй CA]
    SELF_SIGNED -->|Нет| INTERMEDIATE{Промежуточные<br/>сертификаты установлены?}
    
    INTERMEDIATE -->|Нет| CHAIN_FIX[Установить полную цепочку:<br/>cat cert.pem chain.pem > fullchain.pem]
    INTERMEDIATE -->|Да| VERIFY_LOCAL{openssl verify<br/>локального fullchain.pem?}
    
    VERIFY_LOCAL -->|Ошибка| BROKEN[Файл сертификата повреждён<br/>Перевыпустить]
    VERIFY_LOCAL -->|OK| NGINX_CHECK{nginx -t?}
    
    NGINX_CHECK -->|Ошибка| NGINX_FIX[Исправить конфиг nginx]
    NGINX_CHECK -->|OK| CURL_CHECK{curl -v https://<br/>локально с сервера?}
    
    CURL_CHECK -->|Ошибка| BIND_CHECK{Правильный порт<br/>в nginx listen?}
    BIND_CHECK -->|Нет| FIX_BIND[sudo ss -tlnp | grep :443<br/>nginx слушает 443?]
    BIND_CHECK -->|Да| FIREWALL{iptables блокирует 443?}
    FIREWALL -->|Да| FW_FIX[sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT]
    FIREWALL -->|Нет| LOGS[Смотреть journalctl -u nginx<br/>и /var/log/nginx/error.log]
    
    CURL_CHECK -->|OK| CTRL_CHECK{curl с другого хоста /<br/>мобильного интернета?}
    CTRL_CHECK -->|Тоже OK| NOT_SSL[Проблема не в SSL<br/>Смотри приложение / кэш браузера]
    CTRL_CHECK -->|Нет| FW_EXT[Проверить Security Group /<br/>файрвол провайдера / CDN]
    
    style START fill:#f66,stroke:#333,color:#fff
    style NOT_SSL fill:#6f6,stroke:#333,color:#000
    style RENEW fill:#ff9,stroke:#333
    style FIX_CHAIN fill:#ff9,stroke:#333
    style REISSUE fill:#ff9,stroke:#333
    style REVOKE fill:#f66,stroke:#333,color:#fff
```
