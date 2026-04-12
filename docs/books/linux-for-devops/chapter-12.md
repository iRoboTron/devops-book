# Глава 12: Shell-скрипты

> **Запомни:** Всё что ты делаешь больше двух раз — автоматизируй. Скрипты — это способ превратить рутину в одну команду.

---

## 12.1 Зачем скрипты

**Без скрипта:**
```bash
mkdir /var/log/myapp
chown www-data:www-data /var/log/myapp
chmod 755 /var/log/myapp
cp config.ini /etc/myapp/
systemctl restart myapp
systemctl status myapp
```

6 команд. Каждый раз при деплое. Можно ошибиться.

**Со скриптом:**
```bash
./deploy.sh
```

Одна команда. Всегда одинаково. Меньше ошибок.

> **Правило DevOps:** Если ты делаешь что-то третий раз — напиши скрипт.

---

## 12.2 Первый скрипт

Создай файл:

```bash
nano ~/hello.sh
```

Содержимое:
```bash
#!/bin/bash
echo "Hello from DevOps!"
echo "Today is $(date)"
echo "Server: $(hostname)"
```

### Shebang

Первая строка `#!/bin/bash` — называется **shebang**.

Она говорит Linux'у: «Запусти этот файл через bash».

Без shebang Linux не знает чем выполнять файл.

### Сделать выполняемым

```bash
chmod +x ~/hello.sh
```

### Запустить

```bash
./hello.sh
Hello from DevOps!
Today is Thu Apr  9 14:30:00 UTC 2026
Server: ubuntu-server
```

> **Запомни:** `./` означает «запусти из текущей директории».
> Без `./` Linux будет искать команду в `$PATH` и не найдёт.

---

## 12.3 Переменные

```bash
#!/bin/bash

# Создать переменную (без пробелов вокруг =)
APP_NAME="myapp"
APP_PORT=8000
DEPLOY_DIR="/var/www/$APP_NAME"

# Использовать (с $)
echo "Deploying $APP_NAME on port $APP_PORT"
echo "Directory: $DEPLOY_DIR"

# Команда в переменной
CURRENT_DATE=$(date +%Y-%m-%d)
echo "Backup date: $CURRENT_DATE"
```

### Разница между `'` и `"`

```bash
NAME="World"
echo "Hello $NAME"    # Hello World  (переменная раскрывается)
echo 'Hello $NAME'    # Hello $NAME  (буквально)
```

> **Совет:** Используй `"` почти всегда. `'` когда точно не хочешь раскрытия переменных.

---

## 12.4 Аргументы скрипта

```bash
#!/bin/bash

echo "Имя скрипта: $0"
echo "Первый аргумент: $1"
echo "Второй аргумент: $2"
echo "Все аргументы: $@"
echo "Количество: $#"
```

Запуск:
```bash
./deploy.sh myapp production
Имя скрипта: ./deploy.sh
Первый аргумент: myapp
Второй аргумент: production
Все аргументы: myapp production
Количество: 2
```

### Проверить количество аргументов

```bash
#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 <app_name> <environment>"
    exit 1
fi

APP_NAME=$1
ENV=$2
echo "Deploying $APP_NAME to $ENV"
```

---

## 12.5 Условия

### Базовый if

```bash
#!/bin/bash

if [ -f "/etc/nginx/nginx.conf" ]; then
    echo "Nginx config exists"
else
    echo "Nginx config NOT found"
fi
```

### Проверки

| Проверка | Значение |
|----------|----------|
| `-f file` | Файл существует |
| `-d dir` | Директория существует |
| `-z str` | Строка пустая |
| `-n str` | Строка НЕ пустая |
| `a -eq b` | Числа равны |
| `a -gt b` | a больше b |
| `a -lt b` | a меньше b |
| `a == b` | Строки равны |
| `a != b` | Строки не равны |

### Пример: проверка сервиса

```bash
#!/bin/bash

if systemctl is-active --quiet nginx; then
    echo "Nginx is running"
else
    echo "Nginx is NOT running"
    echo "Starting..."
    sudo systemctl start nginx
fi
```

### Множественные условия

```bash
#!/bin/bash

ENV=$1

if [ "$ENV" == "production" ]; then
    echo "Deploying to PRODUCTION"
elif [ "$ENV" == "staging" ]; then
    echo "Deploying to STAGING"
elif [ "$ENV" == "development" ]; then
    echo "Deploying to DEVELOPMENT"
else
    echo "Unknown environment: $ENV"
    exit 1
fi
```

---

## 12.6 Циклы

### for: перебор элементов

```bash
#!/bin/bash

# Перебор списка
for app in nginx postgres docker; do
    echo "Checking $app..."
    systemctl is-active --quiet $app && echo "  Running" || echo "  Stopped"
done
```

### for: файлы

```bash
#!/bin/bash

# Все .log файлы
for file in /var/log/*.log; do
    echo "$file: $(wc -l < $file) lines"
done
```

### while: пока условие верно

```bash
#!/bin/bash

# Ждать пока сервис запустится
MAX_WAIT=30
COUNTER=0

while ! systemctl is-active --quiet myapp; do
    echo "Waiting for myapp to start... ($COUNTER/$MAX_WAIT)"
    sleep 1
    COUNTER=$((COUNTER + 1))
    
    if [ $COUNTER -ge $MAX_WAIT ]; then
        echo "Timeout! myapp didn't start"
        exit 1
    fi
done

echo "myapp is running!"
```

---

## 12.7 Проверка ошибок: `set -e`

```bash
#!/bin/bash
set -e  # Остановиться при первой ошибке

mkdir /var/www/myapp      # Если ошибка — скрипт остановится
cp config.ini /var/www/   # Не выполнится если mkdir упал
chown www-data /var/www/  # Не выполнится если cp упал
echo "Deploy successful"
```

> **Запомни:** Всегда ставь `set -e` в начале скриптов для деплоя.
> Без него скрипт продолжит после ошибки и сделает хуже.

### Другие полезные set

```bash
set -e      # Стоп при ошибке
set -u      # Стоп если переменная не определена
set -x      # Печатать каждую команду (для отладки)
set -o pipefail  # Ошибка в пайпе = ошибка скрипта
```

### Комбинация

```bash
#!/bin/bash
set -euo pipefail
```

---

## 12.8 Перенаправление вывода

### `>` — записать в файл (перезаписать)

```bash
echo "Hello" > output.txt
```

### `>>` — дописать в файл

```bash
echo "World" >> output.txt
```

### `2>` — ошибки в файл

```bash
find / -name "secret" 2>/dev/null
```

`/dev/null` — чёрная дыра. Всё что туда попадает — исчезает.

### `&>` — всё (и вывод и ошибки) в файл

```bash
./deploy.sh &> deploy.log
```

### `|` — передать вывод другой команде

```bash
cat /var/log/syslog | grep "error" | wc -l
```

`cat` выдаёт лог → `grep` фильтрует → `wc -l` считает строки.

---

## 12.9 Функции

```bash
#!/bin/bash

log() {
    echo "[$(date +%H:%M:%S)] $1"
}

log "Starting deploy..."
log "Copying files..."
log "Restarting service..."
```

Результат:
```
[14:30:01] Starting deploy...
[14:30:02] Copying files...
[14:30:05] Restarting service...
```

---

## 12.10 Реальный скрипт деплоя

```bash
#!/bin/bash
set -euo pipefail

# Конфигурация
APP_NAME="myapp"
APP_DIR="/var/www/$APP_NAME"
BACKUP_DIR="/var/backups/$APP_NAME"
DATE=$(date +%Y%m%d_%H%M%S)

# Логирование
log() {
    echo "[$(date +%H:%M:%S)] $1"
}

log "=== Deploying $APP_NAME ==="

# Проверка что мы в правильной директории
if [ ! -d "$APP_DIR" ]; then
    log "ERROR: $APP_DIR not found"
    exit 1
fi

# Бэкап текущей версии
log "Creating backup..."
mkdir -p "$BACKUP_DIR"
cp -r "$APP_DIR" "$BACKUP_DIR/${DATE}_backup"

# Обновление из Git
log "Pulling latest code..."
cd "$APP_DIR"
git pull origin main

# Установка зависимостей
log "Installing dependencies..."
pip install -r requirements.txt

# Перезапуск сервиса
log "Restarting service..."
sudo systemctl restart "$APP_NAME"

# Проверка что сервис работает
if systemctl is-active --quiet "$APP_NAME"; then
    log "✅ Deploy successful!"
else
    log "❌ Service failed to start!"
    log "Rolling back..."
    sudo rm -rf "$APP_DIR"
    sudo cp -r "$BACKUP_DIR/${DATE}_backup" "$APP_DIR"
    sudo systemctl restart "$APP_NAME"
    log "🔄 Rollback complete"
    exit 1
fi
```

> **Запомни:** Этот скрипт — шаблон. Ты будешь его адаптировать под свой проект.
> Но структура всегда та же: бэкап → обновление → перезапуск → проверка.

---

## 📝 Упражнения

### Упражнение 12.1: Первый скрипт
**Задача:**
1. Создай `~/hello.sh` как в примере
2. Сделай выполняемым
3. Запусти
4. Добавь вывод текущего пользователя: `echo "User: $(whoami)"`

### Упражнение 12.2: Переменные и условия
**Задача:** Напиши скрипт `check-service.sh`:
```bash
#!/bin/bash
# Принимает имя сервиса как аргумент
# Проверяет работает ли он
# Если нет — пытается запустить
```

### Упражнение 12.3: Цикл
**Задача:** Напиши скрипт который:
1. Перебирает все `.service` файлы в `/etc/systemd/system/`
2. Для каждого показывает статус
3. Подсчитывает сколько активных

### Упражнение 12.4: Скрипт бэкапа
**Задача:** Напиши скрипт `backup.sh` который:
1. Создаёт директорию бэкапа с датой
2. Копирует туда конфиги из `/etc/nginx/`
3. Сжимает в tar.gz
4. Удаляет бэкапы старше 7 дней
5. Пишет лог что сделал

---

## 📋 Чеклист главы 12

- [ ] Я могу создать и запустить скрипт
- [ ] Я понимаю shebang (`#!/bin/bash`)
- [ ] Я могу использовать переменные
- [ ] Я могу принимать аргументы (`$1`, `$2`)
- [ ] Я могу использовать условия (`if`)
- [ ] Я могу использовать циклы (`for`, `while`)
- [ ] Я знаю `set -e` для проверки ошибок
- [ ] Я понимаю перенаправление (`>`, `>>`, `|`, `2>`)
- [ ] Я могу написать скрипт деплоя
- [ ] Я могу написать скрипт бэкапа

**Всё отметил?** Переходи к Главе 13 — пакетные менеджеры.
