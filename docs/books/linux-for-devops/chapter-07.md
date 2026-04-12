# Глава 7: Системные сервисы и systemd

> **Запомни:** Всё что работает на сервере постоянно (веб-сервер, база данных, SSH) — это сервисы. Управлять ими — твоя основная задача как DevOps'а.

---

## 7.1 Что такое сервис (демон)

**Сервис** (или **демон**) — это программа которая работает в фоне постоянно.

| Сервис | Что делает |
|--------|-----------|
| `ssh` | Принимает SSH-подключения |
| `nginx` | Отдаёт веб-страницы |
| `postgresql` | Работает с базой данных |
| `docker` | Управляет контейнерами |
| `cron` | Запускает задачи по расписанию |
| `ufw` | Фаервол |

**Чем отличается от обычного процесса:**
- Запускается при старте системы
- Работает постоянно
- Управляется через `systemctl`
- Пишет логи в `journalctl`

---

## 7.2 Что такое systemd

**systemd** — это система управления сервисами в Linux.

Это первый процесс который запускается при старте (PID 1).
Он запускает все остальные сервисы.
Он следит чтобы они работали.
Он перезапускает их если они упали.

> **Запомни:** systemd — это «начальник» всех процессов на сервере.
> Ты управляешь сервисами через `systemctl`, а systemd делает остальное.

---

## 7.3 `systemctl`: управление сервисами

### Проверить статус

```bash
systemctl status ssh
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/lib/systemd/system/ssh.service; enabled)
     Active: active (running) since Thu 2026-04-09 10:30:00 UTC
   Main PID: 234 (sshd)
      Tasks: 1 (limit: 2342)
     Memory: 3.2M
        CPU: 12ms
     CGroup: /system.slice/ssh.service
             └─234 "sshd: /usr/sbin/sshd -D"
```

Что здесь важно:

| Строка | Значение |
|--------|----------|
| `Loaded` | Конфиг загружен |
| `Active: active (running)` | Сервис работает |
| `enabled` | Запускается при старте |
| `Main PID` | PID процесса |

### Возможные статусы

| Статус | Значение |
|--------|----------|
| `active (running)` | Работает |
| `inactive (dead)` | Остановлен |
| `failed` | Упал с ошибкой |
| `activating` | Запускается |

---

### Запустить сервис

```bash
sudo systemctl start nginx
```

Сервис запустился. Но при перезагрузке может не запуститься.

### Остановить сервис

```bash
sudo systemctl stop nginx
```

### Перезапустить

```bash
sudo systemctl restart nginx
```

Полезно после изменения конфига — перечитать настройки.

### Перезагрузить конфиг (без остановки)

```bash
sudo systemctl reload nginx
```

Сервис не останавливается — только перечитывает конфиг.

> **Совет:** `reload` лучше чем `restart` — пользователи не заметят перебоев.
> Но не все сервисы поддерживают `reload`.

### Включить автозапуск

```bash
sudo systemctl enable nginx
```

Сервис будет запускаться при каждой загрузке системы.

### Отключить автозапуск

```bash
sudo systemctl disable nginx
```

### Включить и запустить одной командой

```bash
sudo systemctl enable --now nginx
```

`--now` = включи автозапуск И запусти сейчас.

---

## 7.4 Где лежат конфиги сервисов

Файлы сервисов называются `.service` и лежат в:

| Путь | Назначение |
|------|-----------|
| `/lib/systemd/system/` | Системные сервисы (не трогай) |
| `/etc/systemd/system/` | Пользовательские сервисы (сюда клади свои) |

### Посмотреть содержимое сервиса

```bash
systemctl cat ssh
# /lib/systemd/system/ssh.service
[Unit]
Description=OpenBSD Secure Shell server
After=network.target auditd.service

[Service]
ExecStart=/usr/sbin/sshd -D
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Разбор секций

**`[Unit]`** — описание и зависимости
- `Description` — что это
- `After` — после чего запускать

**`[Service]`** — как запускать
- `ExecStart` — команда запуска
- `ExecReload` — команда перезагрузки конфига
- `Restart` — когда перезапускать
- `User` — от какого пользователя
- `WorkingDirectory` — рабочая директория

**`[Install]`** — автозапуск
- `WantedBy` — при какой цели запускать

---

## 7.5 Создать свой сервис

Представь: у тебя есть Python-скрипт который должен работать постоянно.
Ты хочешь чтобы он:
- Запускался при старте системы
- Перезапускался если упал
- Писал логи в journalctl

### Шаг 1: Подготовка

Допустим скрипт лежит здесь:
```
/home/adelfos/myapp/worker.py
```

Проверь что он работает:
```bash
python3 /home/adelfos/myapp/worker.py
```

Останови: `Ctrl+C`

### Шаг 2: Создай файл сервиса

```bash
sudo nano /etc/systemd/system/myapp-worker.service
```

Содержимое:
```ini
[Unit]
Description=MyApp Worker Process
After=network.target

[Service]
Type=simple
User=adelfos
WorkingDirectory=/home/adelfos/myapp
ExecStart=/usr/bin/python3 /home/adelfos/myapp/worker.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Разбор ключевых строк

| Строка | Зачем |
|--------|-------|
| `User=adelfos` | Запускать от этого пользователя (не root!) |
| `WorkingDirectory` | Где работает скрипт |
| `ExecStart` | Полная команда запуска |
| `Restart=always` | Перезапускать если упал |
| `RestartSec=5` | Подождать 5 секунд перед перезапуском |
| `StandardOutput=journal` | Логи идут в journalctl |

### Шаг 3: Активируй сервис

```bash
# Перечитать конфиги systemd
sudo systemctl daemon-reload

# Включить и запустить
sudo systemctl enable --now myapp-worker

# Проверить статус
systemctl status myapp-worker
```

---

## 7.6 Смотреть логи сервиса: `journalctl`

```bash
sudo journalctl -u myapp-worker
```

`-u` = unit (имя сервиса)

### Следить за логами в реальном времени

```bash
sudo journalctl -u myapp-worker -f
```

`-f` = follow (как `tail -f`).

### Логи за сегодня

```bash
sudo journalctl -u myapp-worker --since today
```

### Логи за последний час

```bash
sudo journalctl -u myapp-worker --since "1 hour ago"
```

### Логи с конкретным приоритетом

```bash
sudo journalctl -u myapp-worker -p err
```

`-p err` = только ошибки.

Уровни: `emerg`, `alert`, `crit`, `err`, `warning`, `notice`, `info`, `debug`

---

## 7.7 Типичный рабочий процесс

Ты изменил конфиг сервиса. Что делать:

```bash
# 1. Отредактировать конфиг
sudo nano /etc/systemd/system/myapp-worker.service

# 2. Перечитать конфиги
sudo systemctl daemon-reload

# 3. Перезапустить сервис
sudo systemctl restart myapp-worker

# 4. Проверить что работает
systemctl status myapp-worker

# 5. Посмотреть логи
sudo journalctl -u myapp-worker -f
```

> **Запомни:** `daemon-reload` нужен только когда изменился `.service` файл.
> Если изменился конфиг самого приложения (не сервиса) — просто `restart`.

---

## 7.8 Диагностика проблем

Сервис не запускается. Что делать:

### 1. Посмотри статус

```bash
systemctl status myapp-worker
```

Часто там видна ошибка.

### 2. Посмотри логи

```bash
sudo journalctl -u myapp-worker -n 50
```

`-n 50` = последние 50 строк.

### 3. Проверь конфиг сервиса

```bash
systemd-analyze verify /etc/systemd/system/myapp-worker.service
```

### 4. Попробуй запустить вручную

```bash
/usr/bin/python3 /home/adelfos/myapp/worker.py
```

Может ошибка видна сразу.

---

## 📝 Упражнения

### Упражнение 7.1: Изучить сервисы
**Задача:**
1. Посмотри все сервисы: `systemctl list-units --type=service`
2. Какие активные?
3. Посмотри статус ssh: `systemctl status ssh`
4. Посмотри какие сервисы включены: `systemctl list-unit-files --state=enabled`

### Упражнение 7.2: Управление сервисом
**Задача:**
1. Проверь статус cron: `systemctl status cron`
2. Останови: `sudo systemctl stop cron`
3. Проверь: `systemctl status cron` — stopped?
4. Запусти: `sudo systemctl start cron`
5. Проверь: `systemctl status cron` — running?

### Упражнение 7.3: Создать свой сервис
**Задача:**
1. Создай скрипт:
   ```bash
   mkdir -p ~/myapp
   nano ~/myapp/worker.py
   ```
   ```python
   import time
   while True:
       print("Worker is running...")
       time.sleep(10)
   ```
2. Создай сервис: `sudo nano /etc/systemd/system/myapp-worker.service`
3. Заполни как в примере выше
4. Активируй:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now myapp-worker
   ```
5. Проверь: `systemctl status myapp-worker`
6. Посмотри логи: `sudo journalctl -u myapp-worker -f`
7. Останови: `sudo systemctl stop myapp-worker`

### Упражнение 7.4: Автоперезапуск
**Задача:**
1. Убедись что сервис запущен
2. Убей процесс: `sudo kill -9 $(pgrep -f worker.py)`
3. Подожди 5 секунд
4. Проверь: `systemctl status myapp-worker` — перезапустился?

---

## 📋 Чеклист главы 7

- [ ] Я понимаю что такое сервис (демон)
- [ ] Я понимаю роль systemd
- [ ] Я могу посмотреть статус (`systemctl status`)
- [ ] Я могу запустить, остановить, перезапустить сервис
- [ ] Я могу включить/отключить автозапуск (`enable`/`disable`)
- [ ] Я понимаю где лежат `.service` файлы
- [ ] Я могу создать свой сервис
- [ ] Я знаю зачем нужен `daemon-reload`
- [ ] Я могу посмотреть логи сервиса (`journalctl -u`)
- [ ] Я могу диагностировать проблему с сервисом

**Всё отметил?** Переходи к Главе 8 — логи и диагностика.
