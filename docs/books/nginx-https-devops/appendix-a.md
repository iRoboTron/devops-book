# Приложение A: Шпаргалка команд

> Все команды из книги в одной таблице. Распечатай и держи под рукой.

---

## Nginx

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `nginx -v` | Показать версию | `nginx -v` |
| `nginx -t` | Проверить конфиг | `sudo nginx -t` |
| `systemctl status nginx` | Статус сервиса | `systemctl status nginx` |
| `systemctl reload nginx` | Перечитать конфиг | `sudo systemctl reload nginx` |
| `systemctl restart nginx` | Перезапустить | `sudo systemctl restart nginx` |
| `tail access.log` | Логи запросов | `tail /var/log/nginx/access.log` |
| `tail error.log` | Логи ошибок | `tail /var/log/nginx/error.log` |

## Certbot

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `certbot --nginx` | Получить сертификат + настроить Nginx | `sudo certbot --nginx -d myapp.ru` |
| `certbot certonly` | Только сертификат | `sudo certbot certonly --nginx -d myapp.ru` |
| `certbot renew` | Продлить все сертификаты | `sudo certbot renew` |
| `certbot renew --dry-run` | Тест продления | `sudo certbot renew --dry-run` |
| `certbot certificates` | Список сертификатов | `sudo certbot certificates` |

## ufw

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `ufw status` | Показать статус | `sudo ufw status` |
| `ufw status verbose` | Подробно | `sudo ufw status verbose` |
| `ufw status numbered` | С номерами | `sudo ufw status numbered` |
| `ufw allow PORT` | Разрешить порт | `sudo ufw allow 22` |
| `ufw allow NAME` | Разрешить сервис | `sudo ufw allow OpenSSH` |
| `ufw allow from NET` | Разрешить сети | `sudo ufw allow from 10.0.0.0/8 to any port 5432` |
| `ufw delete N` | Удалить правило | `sudo ufw delete 3` |
| `ufw enable` | Включить | `sudo ufw enable` |
| `ufw disable` | Выключить | `sudo ufw disable` |
| `ufw default deny` | Политика | `sudo ufw default deny incoming` |
| `ufw app list` | Профили | `sudo ufw app list` |

## curl

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `curl URL` | GET запрос | `curl http://localhost` |
| `curl -I URL` | Только заголовки | `curl -I https://google.com` |
| `curl -v URL` | Подробно | `curl -v https://myapp.ru` |
| `curl -X METHOD` | Метод | `curl -X POST https://api.myapp.ru` |
| `curl -d DATA` | Тело | `curl -d '{"name":"Ivan"}' https://api.myapp.ru` |
| `curl -H HEADER` | Заголовок | `curl -H "Authorization: Bearer xyz" https://api.myapp.ru` |
| `curl -w FORMAT` | Формат вывода | `curl -w "TTFB: %{time_starttransfer}s" -o /dev/null -s URL` |
| `curl -k URL` | Без проверки SSL | `curl -k https://myapp.local` |

## DNS

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `dig DOMAIN` | DNS-запрос | `dig google.com` |
| `dig +short` | Кратко | `dig google.com +short` |
| `dig TYPE` | Тип записи | `dig google.com MX` |
| `dig @SERVER` | Конкретный сервер | `dig @8.8.8.8 google.com` |
| `dig +trace` | Полный трейс | `dig myapp.ru +trace` |

## Сеть

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `ss -tlnp` | Слушающие порты | `ss -tlnp` |
| `nc -zv HOST PORT` | Проверить порт | `nc -zv 127.0.0.1 8000` |
| `ping HOST` | Доступность | `ping google.com` |
| `tcpdump -i IFACE` | Пакеты | `sudo tcpdump -i eth0 port 80` |

## systemd

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `systemctl status NAME` | Статус | `systemctl status nginx` |
| `systemctl start NAME` | Запустить | `sudo systemctl start myapp` |
| `systemctl stop NAME` | Остановить | `sudo systemctl stop myapp` |
| `systemctl restart NAME` | Перезапустить | `sudo systemctl restart myapp` |
| `systemctl reload NAME` | Перечитать конфиг | `sudo systemctl reload nginx` |
| `systemctl enable NAME` | Автозапуск | `sudo systemctl enable myapp` |
| `systemctl enable --now` | Включить + запустить | `sudo systemctl enable --now myapp` |
| `journalctl -u NAME` | Логи сервиса | `sudo journalctl -u myapp -f` |

## Полезные пути

| Путь | Что там |
|------|---------|
| `/etc/nginx/nginx.conf` | Главный конфиг Nginx |
| `/etc/nginx/sites-available/` | Конфиги сайтов |
| `/etc/nginx/sites-enabled/` | Включённые сайты |
| `/var/log/nginx/` | Логи Nginx |
| `/etc/letsencrypt/live/` | SSL-сертификаты |
| `/etc/ufw/` | Конфиги ufw |
| `/var/log/ufw.log` | Логи фаервола |
| `/etc/hosts` | Локальный DNS |
