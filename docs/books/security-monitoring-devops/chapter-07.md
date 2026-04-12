# Глава 7: Логи и logwatch

> **Запомни:** `/var/log/auth.log` за неделю = тысячи строк. logwatch превращает это в одну страницу с главным.

---

## 7.1 Проблема сырых логов

```bash
wc -l /var/log/auth.log
15420 /var/log/auth.log
```

15 000 строк. Искать глазами — бессмысленно.

logwatch делает одно: читает все логи, находит главное, присылает дайджест.

---

## 7.2 Установка и запуск

```bash
sudo apt install -y logwatch
```

### Запустить

```bash
sudo logwatch --output stdout --range today --detail low
```

### Что покажет

```
################### Logwatch 7.5.6 (2026-04-11) ####################

###################### Summary ########################

  Total requests: 15420
  Unique IPs: 234
  Failed logins: 847
  Successful logins: 12

###################### SSHD ###########################

  Failed logins:
    root: 423 attempts from 89 IPs
    admin: 156 attempts from 45 IPs

  Top attacking IPs:
    1.2.3.4 - 127 attempts
    5.6.7.8 - 89 attempts

###################### Nginx ##########################

  Total requests: 45234
  200 OK: 42100
  404 Not Found: 2890
  500 Error: 244
```

---

## 7.3 Уровни детализации

| Уровень | Что показывает |
|---------|---------------|
| `low` | Только суммы |
| `med` | Суммы + топ IP |
| `high` | Всё подробно |

```bash
sudo logwatch --output stdout --range today --detail med
```

---

## 7.4 Период

| Период | Что показывает |
|--------|---------------|
| `today` | Сегодня |
| `yesterday` | Вчера |
| `all` | Всё что есть в логах |

```bash
sudo logwatch --output stdout --range yesterday --detail low
```

---

## 7.5 Ключевые логи и что искать

### /var/log/auth.log

```bash
# Неудачные входы
grep "Failed password" /var/log/auth.log | wc -l

# Успешные входы
grep "Accepted" /var/log/auth.log

# sudo действия
grep "sudo" /var/log/auth.log
```

### /var/log/syslog

```bash
# Системные события
grep -i "error" /var/log/syslog | tail -20

# Перезагрузки
grep "reboot" /var/log/syslog
```

### /var/log/nginx/access.log

```bash
# Топ IP
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# Топ URL
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# 404 ошибки
awk '$9 == 404' /var/log/nginx/access.log | awk '{print $7}' | sort | uniq -c | sort -rn | head -10
```

### /var/log/nginx/error.log

```bash
# Ошибки
tail -50 /var/log/nginx/error.log

# 502 ошибки
grep "502" /var/log/nginx/error.log
```

---

## 7.6 goaccess — анализ Nginx в реальном времени

```bash
sudo apt install -y goaccess
sudo goaccess /var/log/nginx/access.log --log-format=COMBINED
```

Показывает:
- Топ IP
- Топ URL
- Коды ответов (200, 404, 500...)
- Трафик по часам
- Браузеры и ОС

> **Совет:** goaccess = Google Analytics для своего сервера.
> Запусти когда хочешь понять кто и что смотрит на сайте.

---

## 7.7 Признаки атаки в логах

### Брутфорс SSH

```bash
grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -5
```

Один IP с сотнями попыток = брутфорс. fail2ban должен был заблокировать.

### Сканирование сайта

```bash
awk '$9 == 404' /var/log/nginx/access.log | awk '{print $7}' | grep -E "wp-admin|phpMyAdmin|\.env|\.git" | head -10
```

Запросы к `/wp-admin`, `/.env`, `/.git` = бот сканирует уязвимости.

### Подозрительные User-Agent

```bash
awk -F'"' '{print $6}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10
```

Пустые User-Agent или `sqlmap`, `nikto` = инструменты хакера.

---

## 📝 Упражнения

### Упражнение 7.1: logwatch
**Задача:**
1. Установи: `sudo apt install -y logwatch`
2. Запусти: `sudo logwatch --output stdout --range today --detail low`
3. Сколько неудачных входов сегодня?
4. Топ атакующих IP?

### Упражнение 7.2: Анализ логов
**Задача:**
1. Посмотри auth.log: `grep "Failed password" /var/log/auth.log | wc -l`
2. Топ IP: `awk '{print $(NF-3)}' ... | sort | uniq -c | sort -rn | head -5`
3. Эти IP в fail2ban banned? `sudo fail2ban-client banned`

### Упражнение 7.3: goaccess
**Задача:**
1. Установи: `sudo apt install -y goaccess`
2. Запусти: `sudo goaccess /var/log/nginx/access.log --log-format=COMBINED`
3. Топ IP? Топ URL? Сколько 404?

### Упражнение 7.4: DevOps Think
**Задача:** «В логах Nginx видишь 1000 запросов к `/.env` за 5 минут с одного IP. fail2ban не заблокировал. Почему и что делать?»

Ответ:
1. fail2ban не имеет фильтра для этого паттерна
2. Создай кастомный фильтр или добавь в nginx-req-limit
3. Заблокируй IP вручную: `sudo ufw deny from IP`
4. Добавь в ignoreip если это твой IP (тестирование)

---

## 📋 Чеклист главы 7

- [ ] logwatch установлен
- [ ] Могу запустить с разными уровнями детализации
- [ ] Знаю где искать auth.log, syslog, nginx логи
- [ ] Могу найти топ IP и URL в логах Nginx
- [ ] Знаю признаки атаки (брутфорс, сканирование)
- [ ] goaccess установлен и работает

**Всё отметил?** Переходи к Главе 8 — аварийное восстановление.
