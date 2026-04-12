# Глава 9: Итоговый проект — hardened сервер

> **Запомни:** Финал. Примени всё из этой книги к реальному серверу. Без халтуры.

---

## 9.1 Безопасность

### SSH

```bash
# Проверить
grep -E "PermitRootLogin|PasswordAuthentication|MaxAuthTries" /etc/ssh/sshd_config

# Должно быть:
# PermitRootLogin no
# PasswordAuthentication no
# MaxAuthTries 3
```

- [ ] `PermitRootLogin no`
- [ ] `PasswordAuthentication no`
- [ ] `PubkeyAuthentication yes`
- [ ] `MaxAuthTries 3`
- [ ] Вход по ключу работает
- [ ] Вход по паролю заблокирован

### fail2ban

```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

- [ ] fail2ban запущен
- [ ] sshd jail включён
- [ ] nginx-http-auth jail включён
- [ ] Мой IP в `ignoreip`

### ufw

```bash
sudo ufw status verbose
```

- [ ] ufw включён
- [ ] Открыты только 22, 80, 443

### Обновления

```bash
systemctl status unattended-upgrades
```

- [ ] unattended-upgrades включён

### lynis

```bash
sudo lynis audit system
```

- [ ] Hardening Index > 70

---

## 9.2 Мониторинг

### Netdata

```bash
systemctl status netdata
```

- [ ] Netdata установлен
- [ ] Закрыт от интернета (bind to = 127.0.0.1)
- [ ] Доступен через SSH-туннель

### Telegram-алерты

```bash
cat /etc/alerting.env
ls -la /etc/alerting.env
```

- [ ] Бот создан
- [ ] Токен и chat_id в `/etc/alerting.env`
- [ ] Права 600 на `/etc/alerting.env`
- [ ] Тестовое сообщение пришло

### health-monitor.sh

```bash
cat /etc/cron.d/health-monitor
```

- [ ] Скрипт создан и выполняется каждые 5 минут
- [ ] Алерт пришёл при тесте

### Ежедневный отчёт

```bash
cat /etc/cron.d/daily-report
```

- [ ] Отчёт приходит в Telegram в 9:00

### logwatch

```bash
sudo logwatch --output stdout --range today --detail low
```

- [ ] logwatch установлен

---

## 9.3 Документация

- [ ] Runbook написан (`/opt/myapp/RUNBOOK.md`)
- [ ] Контакты и доступы записаны
- [ ] Минимум 3 сценария описаны

---

## 9.4 Финальная проверка

### Тест 1: Вход по паролю заблокирован

```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no deploy@server
# Permission denied (publickey)
```

### Тест 2: fail2ban блокирует

```bash
# С другого IP — 3 неудачных попытки
ssh wronguser@server  # × 3

# На сервере:
sudo fail2ban-client status sshd
# Banned IP list: должен быть IP
```

### Тест 3: Telegram-алерт при заполнении диска

```bash
# Временно создать большой файл
dd if=/dev/zero of=/tmp/fill bs=1M count=1000

# Подождать 5 минут — должен прийти алерт

# Убрать
rm /tmp/fill
```

### Тест 4: Алерт при остановке приложения

```bash
docker compose stop app

# Подождать 5 минут — должен прийти алерт

docker compose start app
```

### Тест 5: lynis score

```bash
sudo lynis audit system | grep "Hardening Index"
# Должно быть > 70
```

---

## 9.5 Поздравляю! Курс завершён

Ты прошёл все 6 модулей. Вот что ты умеешь:

### Модуль 1: Linux
- ✅ Терминал, файловая система, права
- ✅ Процессы, сервисы, логи
- ✅ Пользователи, SSH-ключи
- ✅ Shell-скрипты

### Модуль 2: Сеть
- ✅ HTTP/HTTPS, DNS
- ✅ Nginx reverse proxy
- ✅ SSL-сертификаты (Let's Encrypt)
- ✅ Фаервол (ufw)

### Модуль 3: Docker
- ✅ Dockerfile, образы, контейнеры
- ✅ docker-compose, volumes, сети
- ✅ Переменные окружения, секреты

### Модуль 4: CI/CD
- ✅ GitHub Actions
- ✅ Тесты в пайплайне
- ✅ Сборка и публикация Docker-образов
- ✅ Автодеплой по SSH

### Модуль 5: Инфраструктура
- ✅ PostgreSQL: пользователи, права, параметры
- ✅ Миграции (Alembic)
- ✅ Бэкапы и восстановление
- ✅ Стабильность сервера

### Модуль 6: Безопасность и мониторинг
- ✅ SSH hardening, fail2ban
- ✅ Автообновления
- ✅ Netdata, Telegram-алерты
- ✅ Runbook для аварий

---

## 9.6 Финальная фраза

> Ты начал с 3 команд консоли Linux.
>
> Теперь ты можешь:
> - Развернуть Python-проект на сервере
> - Настроить автодеплой из Git
> - Защитить сервер от атак
> - Настроить мониторинг и алерты
> - Восстановиться из бэкапа
> - Написать runbook для аварий
>
> **Это уровень настоящего DevOps.**
>
> Иди и строй.
