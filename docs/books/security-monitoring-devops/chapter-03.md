# Глава 3: Обновления и патчи

> **Запомни:** Большинство взломов — через известные уязвимости в устаревшем ПО. Обновление = закрытие дыр до того как их найдут.

---

## 3.1 Почему обновления критичны

Каждый месяц выходят обновления безопасности. Они закрывают уязвимости которые уже известны.

### Реальный сценарий

```
Январь: Найдена уязвимость в OpenSSL
Февраль: Вышло обновление
Март:   Ты не обновил
Апрель: Бот нашёл уязвимый сервер → взлом
```

Ты не обновил → сервер уязвим → боты сканируют весь интернет → находят тебя.

### Ручное обновление (знаешь из Модуля 1)

```bash
sudo apt update && sudo apt upgrade -y
```

Проблема: нужно помнить делать это каждую неделю.

---

## 3.2 unattended-upgrades — автоматические обновления

Устанавливает обновления безопасности автоматически.

### Установка

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### Что делает

- Ежедневно проверяет обновления
- Устанавливает ТОЛЬКО обновления безопасности
- НЕ обновляет мажорные версии (не ломает)

### Конфигурация

```bash
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

### Ключевые настройки

```
// Обновлять только security
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
};

// Автоперезагрузка при обновлении ядра
Unattended-Upgrade::Automatic-Reboot "false";

// Email при обновлении (опционально)
// Unattended-Upgrade::Mail "admin@example.com";

// Логи
Unattended-Upgrade::Log "/var/log/unattended-upgrades/unattended-upgrades.log";
```

> **Совет:** `Automatic-Reboot "false"` — не перезагружай сервер автоматически.
> Перезагрузи вручную в удобное время.

### Проверить что работает

```bash
# Логи
sudo tail /var/log/unattended-upgrades/unattended-upgrades.log

# Что было бы обновлено (dry-run)
sudo unattended-upgrade --dry-run -v

# Запустить вручную с отладкой
sudo unattended-upgrade -d
```

---

## 3.3 needrestart — сервисы после обновления

После обновления библиотеки старые процессы ещё используют старую версию.

```bash
sudo apt install -y needrestart
```

Проверит какие сервисы нужно перезапустить:

```bash
sudo needrestart
```

---

## 3.4 Docker-образы: они не обновляются автоматически

`unattended-upgrades` обновляет пакеты системы. Но НЕ Docker-образы.

### Как обновлять Docker-образы

**Вариант 1: Периодически пересобирать**

```bash
cd /opt/myapp
docker compose build --pull
docker compose up -d
```

`--pull` = скачать последнюю версию базового образа.

**Вариант 2: Через CI/CD**

Добавь в GitHub Actions еженедельный workflow:

```yaml
name: Rebuild Docker Images

on:
  schedule:
    - cron: '0 5 * * 1'  # Каждый понедельник в 5:00

jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build with latest base image
        run: docker compose build --pull
      - name: Push
        run: docker compose push
```

**Вариант 3: Фиксированные теги**

Вместо `python:3.12-slim` → `python:3.12.3-slim-bookworm`.

Знаешь точно какая версия. Обновляешь когда нужно.

> **Запомни:** `latest` тег = неизвестная версия.
> Фиксируй теги для предсказуемости.

---

## 3.5 Сканирование уязвимостей (упоминаю)

### Trivy

```bash
# Сканировать образ
trivy image ghcr.io/user/myapp:latest

# Результат:
# CRITICAL: 0
# HIGH: 2
# MEDIUM: 5
```

### Docker Scout

```bash
docker scout cves ghcr.io/user/myapp:latest
```

> **Совет:** Запускай раз в месяц.
> Критичные уязвимости — обновляй немедленно.

---

## 📝 Упражнения

### Упражнение 3.1: unattended-upgrades
**Задача:**
1. Установи: `sudo apt install -y unattended-upgrades`
2. Настрой: `sudo dpkg-reconfigure --priority=low unattended-upgrades`
3. Проверь статус: `sudo systemctl status unattended-upgrades`
4. Dry-run: `sudo unattended-upgrade --dry-run -v`

### Упражнение 3.2: needrestart
**Задача:**
1. Установи: `sudo apt install -y needrestart`
2. Запусти: `sudo needrestart`
3. Какие сервисы нужно перезапустить?

### Упражнение 3.3: Docker образы
**Задача:**
1. Посмотри какие образы используешь: `docker images`
2. Теги фиксированные или `latest`?
3. Пересобери с `--pull`: `docker compose build --pull`
4. Есть ли обновления базовых образов?

### Упражнение 3.4: DevOps Think
**Задача:** «unattended-upgrades обновил пакет. Приложение перестало работать. Что делать?»

Ответ:
1. Проверь логи: `sudo tail /var/log/unattended-upgrades/unattended-upgrades.log`
2. Посмотри что обновилось: `apt list --upgradable`
3. Откати пакет: `apt install packagename=old_version`
4. В будущем: тестируй обновления на staging перед production
5. Или: отключи auto-upgrade и обновляй вручную раз в неделю

---

## 📋 Чеклист главы 3

- [ ] unattended-upgrades установлен и включён
- [ ] Automatic-Reboot = false
- [ ] needrestart установлен
- [ ] Docker-образы используют фиксированные теги
- [ ] Знаю как пересобрать образы с `--pull`
- [ ] Знаю где логи unattended-upgrades

**Всё отметил?** Переходи к Главе 4 — минимизация поверхности атаки.
