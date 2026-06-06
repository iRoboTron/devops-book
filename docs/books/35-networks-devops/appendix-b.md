# Приложение B: Таблица важных портов

| Порт | Протокол | Сервис | Примечание |
|------|----------|--------|------------|
| 22 | TCP | SSH | Удалённый доступ к серверам |
| 25 | TCP | SMTP | Отправка почты (часто блокируется провайдерами) |
| 53 | TCP+UDP | DNS | Разрешение имён |
| 53 | UDP | DNS | Основной транспорт DNS (запросы) |
| 67/68 | UDP | DHCP | Выдача IP-адресов |
| 80 | TCP | HTTP | Веб-трафик без шифрования |
| 110 | TCP | POP3 | Приём почты (устаревает) |
| 123 | UDP | NTP | Синхронизация времени |
| 143 | TCP | IMAP | Приём почты с папками |
| 389 | TCP+UDP | LDAP | Протокол каталогов (Active Directory) |
| 443 | TCP | HTTPS | Веб-трафик с TLS-шифрованием |
| 465 | TCP | SMTPS | SMTP поверх SSL (устаревший) |
| 587 | TCP | SMTP submission | Отправка почты с аутентификацией |
| 636 | TCP | LDAPS | LDAP поверх SSL |
| 993 | TCP | IMAPS | IMAP поверх SSL |
| 995 | TCP | POP3S | POP3 поверх SSL |
| 1433 | TCP | MSSQL | База данных Microsoft SQL Server |
| 1521 | TCP | Oracle DB | База данных Oracle |
| 2049 | TCP+UDP | NFS | Сетевая файловая система |
| 2379 | TCP | etcd client | Клиентские запросы к etcd (K8s) |
| 2380 | TCP | etcd peer | Рекламация между etcd-нодами |
| 3000 | TCP | Grafana | Визуализация метрик |
| 3306 | TCP | MySQL / MariaDB | База данных |
| 3389 | TCP | RDP | Удалённый рабочий стол Windows |
| 5000 | TCP | Docker Registry | Хранилище Docker-образов |
| 5432 | TCP | PostgreSQL | База данных |
| 6379 | TCP | Redis | Кэш / очередь |
| 6443 | TCP | Kubernetes API | API-сервер K8s |
| 8080 | TCP | HTTP alternative | Альтернативный HTTP (Tomcat, web dev) |
| 8443 | TCP | HTTPS alternative | Альтернативный HTTPS |
| 9090 | TCP | Prometheus | Сбор метрик |
| 9100 | TCP | node_exporter | Метрики сервера (Prometheus) |
| 9200 | TCP | Elasticsearch | Поисковый движок / логи |
| 10250 | TCP | Kubelet API | Агент Kubernetes на ноде |
| 11211 | TCP+UDP | Memcached | Кэш в памяти |
| 27017 | TCP | MongoDB | NoSQL база данных |

---

## Группировка по назначению

### Веб
| Порт | Куда смотреть |
|------|--------------|
| 80 | `ss -tlnp \| grep :80` |
| 443 | `ss -tlnp \| grep :443` |
| 8080 | `ss -tlnp \| grep :8080` |
| 8443 | `ss -tlnp \| grep :8443` |

### Базы данных
| Порт | Куда смотреть |
|------|--------------|
| 3306 | `ss -tlnp \| grep :3306` |
| 5432 | `ss -tlnp \| grep :5432` |
| 6379 | `ss -tlnp \| grep :6379` |
| 27017 | `ss -tlnp \| grep :27017` |
| 9200 | `ss -tlnp \| grep :9200` |

### Kubernetes
| Порт | Куда смотреть |
|------|--------------|
| 6443 | `ss -tlnp \| grep :6443` |
| 2379 | `ss -tlnp \| grep :2379` |
| 10250 | `ss -tlnp \| grep :10250` |

### Мониторинг
| Порт | Куда смотреть |
|------|--------------|
| 9090 | `ss -tlnp \| grep :9090` |
| 9100 | `ss -tlnp \| grep :9100` |
| 3000 | `ss -tlnp \| grep :3000` |

---

## Быстрая проверка: слушается ли порт?

```bash
# Поиск по номеру порта
sudo ss -tlnp | grep -E ":80 |:443 |:5432 "

# Список всех слушающих портов (только номер)
ss -tlnp | awk '{print $4}' | grep -oP ':\K[\d]+' | sort -n | uniq

# Проверка конкретного порта через /proc
cat /proc/net/tcp | awk '{print $2}' | grep -oP ':\K[\dA-Fa-f]+' | \
  while read h; do printf "%d\n" 0x$h; done | sort -n | uniq
```
