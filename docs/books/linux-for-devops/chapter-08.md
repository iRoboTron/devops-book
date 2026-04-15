# Глава 8: Логи и диагностика

> **Запомни:** Когда что-то ломается, логи — это первое, куда ты смотришь. Умение читать логи — это 80% диагностики проблем.

---

## 8.1 Где лежат логи

Все логи — в `/var/log/`:

```bash
ls /var/log/
syslog      auth.log     nginx/        postgresql/
kern.log    dmesg        apache2/      mysql/
dpkg.log    fontconfig.log  apt/      dist-upgrade/
```

| Файл | Что пишет |
|------|-----------|
| `syslog` | Системные события |
| `auth.log` | Авторизация (логины, sudo) |
| `kern.log` | Сообщения ядра |
| `dmesg` | Загрузка системы |
| `dpkg.log` | Установка пакетов |
| `nginx/` | Логи Nginx |
| `apache2/` | Логи Apache |

> **Совет:** Когда что-то сломалось — начни с `syslog` и `auth.log`. Там чаще всего причина.

---

## 8.2 Смотреть логи: `tail`

### Последние строки

```bash
tail /var/log/syslog
```

По умолчанию — 10 последних строк.

### Больше строк

```bash
tail -n 50 /var/log/syslog
```

### Следить в реальном времени

```bash
tail -f /var/log/syslog
```

Новые строки появляются сами. `Ctrl+C` чтобы остановить.

> **Запомни:** `tail -f` — твой главный инструмент когда тестируешь работу сервиса.
> Запустил `tail -f` в одном окне терминала, делаешь действия в другом — видишь что происходит.

---

## 8.3 Искать в логах: `grep`

`grep` ищет текст в файлах.

### Найти ошибки

```bash
grep "error" /var/log/syslog
```

### Без учёта регистра

```bash
grep -i "error" /var/log/syslog
```

`-i` = case-insensitive (Error, ERROR, error — всё найдёт)

### Показать строки до и после

```bash
grep -B 2 -A 5 "error" /var/log/syslog
```

- `-B 2` = 2 строки ДО (before)
- `-A 5` = 5 строк ПОСЛЕ (after)
- `-C 3` = 3 строки с обеих сторон (context)

### Посчитать совпадения

```bash
grep -c "error" /var/log/syslog
```

### Искать в нескольких файлах

```bash
grep -r "error" /var/log/
```

`-r` = рекурсивно во всех файлах.

### Инвертировать (показать НЕ совпадения)

```bash
grep -v "debug" /var/log/syslog
```

Покажет все строки КРОМЕ содержащих "debug".

> **Совет:** Комбинируй `tail -f` и `grep`:
> ```bash
> tail -f /var/log/syslog | grep -i "nginx"
> ```
> Будешь видеть только строки про Nginx в реальном времени.

---

## 8.4 `journalctl`: системные логи

`journalctl` читает логи systemd (глава 7).

### Все логи

```bash
sudo journalctl
```

### Логи конкретного сервиса

```bash
sudo journalctl -u nginx
```

### Следить в реальном времени

```bash
sudo journalctl -u nginx -f
```

### Логи за сегодня

```bash
sudo journalctl --since today
```

### Логи за время

```bash
sudo journalctl --since "2026-04-09 10:00:00"
sudo journalctl --since "2 hours ago"
sudo journalctl --since yesterday --until today
```

### Только ошибки

```bash
sudo journalctl -p err
```

### Показать последние N строк

```bash
sudo journalctl -n 20
```

### По PID процесса

```bash
sudo journalctl _PID=1234
```

---

## 8.5 `dmesg`: сообщения ядра

```bash
dmesg
```

Показывает сообщения ядра — железо, диски, сеть, память.

### Полезно когда:

- Диск не определяется
- Сеть не работает
- Нехватает памяти (OOM killer)
- USB не работает

### Фильтровать

```bash
dmesg | grep -i "error"
dmesg | grep -i "memory"
dmesg | grep -i "network"
```

---

## 8.6 Читаем лог: практический пример

Вот строка из `syslog`:

```
Apr  9 14:30:01 ubuntu-server CRON[5678]: (root) CMD (/usr/bin/backup.sh)
```

Разбор:

| Часть | Значение |
|-------|----------|
| `Apr  9 14:30:01` | Дата и время |
| `ubuntu-server` | Имя сервера |
| `CRON[5678]` | Процесс (PID) |
| `(root)` | От какого пользователя |
| `CMD` | Что выполнил |
| `(/usr/bin/backup.sh)` | Конкретная команда |

---

## 8.7 Паттерны ошибок

Типичные ошибки в логах:

### Permission denied

```
Permission denied: '/var/www/myapp/config.ini'
```

**Причина:** Нет прав на файл.
**Решение:** Проверь права (`ls -l`), поправь (`chmod`, `chown`).

### Connection refused

```
Connection refused: localhost:5432
```

**Причина:** Сервис не запущен или не на том порту.
**Решение:** `systemctl status postgresql`, `ss -tlnp | grep 5432`

### Out of memory

```
Out of memory: Kill process 1234 (python3) score 950
```

**Причина:** Кончилась память.
**Решение:** Увеличь RAM, найди утечку, ограничь процесс.

### Address already in use

```
Address already in use: 0.0.0.0:80
```

**Причина:** Порт уже занят другим процессом.
**Решение:** `ss -tlnp | grep 80` — найди кто занял, убей или смени порт.

### File not found

```
FileNotFoundError: '/home/adelfos/myapp/config.ini'
```

**Причина:** Файл не там где ожидается.
**Решение:** Проверь путь, проверь права.

---

## 8.8 Ротация логов: `logrotate`

Логи растут. Если не чистить — забьют весь диск.

**`logrotate`** автоматически:
- Переименовывает старые логи
- Сжимает их
- Удаляет очень старые

### Конфиг

```bash
cat /etc/logrotate.conf
```

И конфиги для отдельных сервисов:
```bash
ls /etc/logrotate.d/
nginx  postgresql  docker  ...
```

### Пример конфига для Nginx

```bash
cat /etc/logrotate.d/nginx
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    prerotate
        if [ -d /etc/logrotate.d/http-prerotate ]; then \
            run-parts /etc/logrotate.d/http-prerotate; \
        fi
    endscript
    postrotate
        invoke-rc.d nginx rotate >/dev/null 2>&1
    endscript
}
```

| Директива | Значение |
|-----------|----------|
| `daily` | Каждый день |
| `rotate 14` | Хранить 14 файлов |
| `compress` | Сжимать старые |
| `notifempty` | Не ротировать пустые |
| `create 0640` | Права нового файла |

> **Совет:** Обычно logrotate работает из коробки. Тебе нужно только знать что логи не растут бесконечно.

---

## 📝 Упражнения

### Упражнение 8.1: Изучить логи
**Задача:**
1. Посмотри последние строки syslog: `tail /var/log/syslog`
2. Посмотри последние 50 строк: `tail -n 50 /var/log/syslog`
3. Найди все ошибки: `grep -i "error" /var/log/syslog`
4. Посмотри логи авторизации: `tail /var/log/auth.log`

### Упражнение 8.2: Следить за логами
**Задача:**
1. Открой два окна терминала
2. В первом: `tail -f /var/log/syslog`
3. Во втором: `sudo systemctl restart ssh`
4. В первом окне увидишь запись о перезапуске
5. Останови `tail -f`: `Ctrl+C`

### Упражнение 8.3: journalctl
**Задача:**
1. Посмотри логи nginx: `sudo journalctl -u nginx`
2. Если nginx не установлен — любой сервис
3. Посмотри логи за сегодня: `sudo journalctl --since today`
4. Посмотри только ошибки: `sudo journalctl -p err`
5. Следить в реальном времени: `sudo journalctl -f`

### Упражнение 8.4: Диагностика
**Задача:** Представь что Nginx не запускается. Пройди по шагам:
1. `systemctl status nginx` — что говорит?
2. `sudo journalctl -u nginx -n 50` — что в логах?
3. `sudo nginx -t` — тест конфига
4. `cat /var/log/nginx/error.log` — лог ошибок Nginx

### Упражнение 8.5: DevOps Think
**Задача 1:** «Диск забит на 95%. Найди виновника за 5 минут»

Подсказки:
1. Общая картина: `df -h`
2. Самые большие директории: `sudo du -sh /* | sort -rh | head -5`
3. Копай глубже: `sudo du -sh /var/* | sort -rh | head -5`
4. Конкретные файлы: `sudo find /var -size +100M 2>/dev/null`
5. Очисти логи: `sudo journalctl --vacuum-size=100M`

**Задача 2:** «Сервис не стартует после перезагрузки. Диагностируй»

Подсказки:
1. Включён ли автозапуск? `systemctl is-enabled myapp`
2. Статус: `systemctl status myapp`
3. Логи: `sudo journalctl -u myapp --since today`
4. Зависимости: смотрим `[Unit]` в `.service` файле
5. Проверь что зависимости запущены

---

## 📋 Чеклист главы 8

- [ ] Я знаю где лежат логи (`/var/log/`)
- [ ] Я умею читать логи (`tail`, `less`)
- [ ] Я умею искать в логах (`grep`)
- [ ] Я умею следить за логами в реальном времени (`tail -f`)
- [ ] Я умею пользоваться `journalctl`
- [ ] Я понимаю типичные ошибки в логах
- [ ] Я знаю про ротацию логов (`logrotate`)
- [ ] Я могу найти причину заполненности диска
- [ ] Я могу диагностировать проблему с сервисом

**Всё отметил?** Переходи к Главе 9 — пользователи и группы.
