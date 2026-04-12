# Глава 14: Итоговый проект

> **Запомни:** Эта глава объединяет всё что ты выучил. Ты разворачиваешь Python-приложение на сервере полностью самостоятельно.

---

## 14.1 Цель

Развернуть Python-приложение (Flask/FastAPI) на сервере с:
- ✅ systemd сервисом
- ✅ Nginx как reverse proxy
- ✅ Логами
- ✅ Автозапуском
- ✅ Правильными правами
- ✅ Пользователем для приложения

---

## 14.2 Шаг 1: Подготовка сервера

### Обновить систему

```bash
sudo apt update && sudo apt upgrade -y
```

### Установить необходимое

```bash
sudo apt install -y nginx python3 python3-pip python3-venv git
```

### Включить сервисы

```bash
sudo systemctl enable --now nginx
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## 14.3 Шаг 2: Создать приложение

### Простое Flask-приложение

```bash
# Создать директорию
sudo mkdir -p /var/www/myapp
cd /var/www/myapp

# Создать файл приложения
sudo nano /var/www/myapp/app.py
```

`app.py`:
```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "<h1>Hello from DevOps!</h1><p>Server is running.</p>"

@app.route('/health')
def health():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

---

## 14.4 Шаг 3: Создать пользователя для приложения

```bash
# Создать пользователя без логина
sudo useradd -r -s /usr/sbin/nologin myapp

# Передать каталог приложению
sudo chown -R myapp:myapp /var/www/myapp
```

| Опция | Значение |
|-------|----------|
| `-r` | Системный пользователь |
| `-s /usr/sbin/nologin` | Не может войти |

---

> **Запомни:** Сначала создай пользователя и отдай ему каталог.
> Виртуальное окружение и зависимости ставь от имени этого пользователя, иначе потом легко словить проблемы с правами.

---

## 14.5 Шаг 4: Виртуальное окружение

```bash
# Создать виртуальное окружение от имени пользователя приложения
sudo -u myapp python3 -m venv /var/www/myapp/venv

# Установить Flask и Gunicorn в это окружение
sudo -u myapp /var/www/myapp/venv/bin/pip install flask gunicorn

# Проверить
sudo -u myapp /var/www/myapp/venv/bin/pip list
```

---

## 14.6 Шаг 5: Тестовый запуск

```bash
# Переключиться на пользователя myapp
sudo su -s /bin/bash myapp

# Активировать venv
source /var/www/myapp/venv/bin/activate

# Запустить
cd /var/www/myapp
python app.py
```

В другом терминале:
```bash
curl http://localhost:8000
```

Должно вернуть HTML.

Останови: `Ctrl+C`
Выйди из myapp: `exit`

---

## 14.7 Шаг 6: Создать systemd сервис

```bash
sudo nano /etc/systemd/system/myapp.service
```

```ini
[Unit]
Description=My Flask Application
After=network.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/var/www/myapp
Environment="PATH=/var/www/myapp/venv/bin"
ExecStart=/var/www/myapp/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=5

# Логи
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target
```

### Разбор ExecStart

```
/var/www/myapp/venv/bin/gunicorn   ← полный путь к gunicorn
--workers 3                         ← 3 рабочих процесса
--bind 127.0.0.1:8000              ← только localhost
app:app                             ← файл app.py, объект app
```

> **Запомни:** Gunicorn — production сервер для Python.
> `python app.py` — только для разработки.

---

## 14.8 Шаг 7: Запустить сервис

```bash
# Перечитать конфиги
sudo systemctl daemon-reload

# Включить и запустить
sudo systemctl enable --now myapp

# Проверить
systemctl status myapp

# Посмотреть логи
sudo journalctl -u myapp -f
```

Проверь:
```bash
curl http://127.0.0.1:8000
```

---

## 14.9 Шаг 8: Настроить Nginx

Nginx будет принимать запросы на порт 80 и передавать Gunicorn на порт 8000.

```bash
sudo nano /etc/nginx/sites-available/myapp
```

```nginx
server {
    listen 80;
    server_name myapp.example.com;  # Поменяй на свой домен или IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Логи
    access_log /var/log/nginx/myapp-access.log;
    error_log /var/log/nginx/myapp-error.log;
}
```

### Активировать сайт

```bash
# Создать ссылку
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/

# Удалить дефолтный сайт (если мешает)
sudo rm /etc/nginx/sites-enabled/default

# Проверить конфиг
sudo nginx -t

# Перезапустить Nginx
sudo systemctl restart nginx
```

Проверь:
```bash
curl http://localhost
```

---

## 14.10 Шаг 9: Создать скрипт деплоя

```bash
nano ~/deploy-myapp.sh
```

```bash
#!/bin/bash
set -euo pipefail

APP_DIR="/var/www/myapp"
APP_NAME="myapp"

log() {
    echo "[$(date +%H:%M:%S)] $1"
}

log "=== Deploying $APP_NAME ==="

# Проверка директории
if [ ! -d "$APP_DIR" ]; then
    log "ERROR: $APP_DIR not found"
    exit 1
fi

# Обновить код
log "Pulling latest code..."
cd "$APP_DIR"
git pull origin main || log "Not a git repo, skipping pull"

# Обновить зависимости
log "Updating dependencies..."
source "$APP_DIR/venv/bin/activate"
pip install -r requirements.txt 2>/dev/null || log "No requirements.txt"

# Перезапустить сервис
log "Restarting service..."
sudo systemctl restart "$APP_NAME"

# Проверить
sleep 2
if systemctl is-active --quiet "$APP_NAME"; then
    log "✅ Deploy successful!"
else
    log "❌ Service failed to start!"
    sudo journalctl -u "$APP_NAME" -n 20 --no-pager
    exit 1
fi
```

Сделай выполняемым:
```bash
chmod +x ~/deploy-myapp.sh
```

---

## 14.11 Шаг 10: Проверка всего

### Чеклист

- [ ] Приложение запущено: `systemctl status myapp`
- [ ] Nginx работает: `systemctl status nginx`
- [ ] curl работает: `curl http://localhost`
- [ ] Логи пишутся: `sudo journalctl -u myapp -n 10`
- [ ] Nginx логи: `tail /var/log/nginx/myapp-access.log`
- [ ] После перезагрузки всё поднимается: `sudo reboot` → проверить
- [ ] Фаервол включён: `sudo ufw status`
- [ ] Права правильные: `ls -la /var/www/myapp`

### Диагностика если что-то не работает

```bash
# 1. Проверить сервис
systemctl status myapp

# 2. Проверить логи
sudo journalctl -u myapp -n 50

# 3. Проверить Gunicorn напрямую
curl http://127.0.0.1:8000

# 4. Проверить Nginx
sudo nginx -t
curl http://localhost

# 5. Проверить порты
ss -tlnp | grep -E '80|8000'

# 6. Проверить права
ls -la /var/www/myapp
```

---

## 14.12 Что дальше

Ты развернул приложение. Это база. Вот что можно добавить:

### Docker
- Контейнеризовать приложение
- docker-compose для мультиконтейнерных приложений

### CI/CD
- GitHub Actions для автодеплоя
- Push → тесты → сборка → деплой

### HTTPS
- Let's Encrypt через certbot
- Автоматическое обновление сертификатов

### Мониторинг
- Netdata для мониторинга сервера
- Алертинг в Telegram

### Бэкапы
- cron скрипт для бэкапа базы данных
- Отправка бэкапов в облако

Всё это — следующие модули обучения. Ты уже готов к ним.

---

## 📝 Финальное упражнение

### Задание

Разверни приложение с нуля без подсказок:

1. Подготовь сервер (обновления, пакеты, фаервол)
2. Создай приложение (Flask/FastAPI)
3. Создай пользователя
4. Настрой виртуальное окружение
5. Создай systemd сервис
6. Настрой Nginx
7. Напиши скрипт деплоя
8. Проверь всё работает
9. Перезагрузи сервер — убедись что всё поднялось

### Критерии успеха

- [ ] `curl http://localhost` возвращает ответ приложения
- [ ] `systemctl status myapp` показывает active
- [ ] `systemctl status nginx` показывает active
- [ ] Логи пишутся
- [ ] После перезагрузки всё работает
- [ ] Фаервол включён
- [ ] Ты можешь объяснить каждую команду что использовал

---

## 🎉 Поздравляю!

Ты прошёл все 14 глав.

**Что ты теперь умеешь:**
- ✅ Навигация по файловой системе
- ✅ Управление файлами и директориями
- ✅ Права и владельцы
- ✅ Редакторы (nano, vim)
- ✅ Процессы и мониторинг
- ✅ systemd сервисы
- ✅ Логи и диагностика
- ✅ Пользователи и группы
- ✅ Сетевые основы
- ✅ Диски и файловые системы
- ✅ Shell-скрипты
- ✅ Пакетные менеджеры
- ✅ Развёртывание приложения

**Ты готов к следующему модулю: Docker.**

---

## 📋 Финальный чеклист

Пройдись по всем главам и убедись что всё понятно:

- [ ] Глава 0: Подготовка окружения
- [ ] Глава 1: Linux и зачем он
- [ ] Глава 2: Первая команда и файловая система
- [ ] Глава 3: Файлы и директории
- [ ] Глава 4: Права и владельцы
- [ ] Глава 5: Редакторы в терминале
- [ ] Глава 6: Процессы
- [ ] Глава 7: Системные сервисы и systemd
- [ ] Глава 8: Логи и диагностика
- [ ] Глава 9: Пользователи и группы
- [ ] Глава 10: Сетевые основы
- [ ] Глава 11: Диски и файловые системы
- [ ] Глава 12: Shell-скрипты
- [ ] Глава 13: Пакетные менеджеры
- [ ] Глава 14: Итоговый проект

**Если всё отмечено — ты уверенный пользователь Linux.**
**Время для Docker.**
