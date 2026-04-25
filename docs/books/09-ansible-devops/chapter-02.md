# Глава 2: Ad-hoc команды и модули

> **Запомни:** Ad-hoc = быстрая команда без playbook. Для разовых задач. Для повторяющихся — playbook.
>
> **Проект этой главы:** проверяем, что сервер жив, доступен и готов к будущему деплою.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 2.1 Синтаксис

```bash
ansible <группа> -m <модуль> -a "<аргументы>" -b
```

| Флаг | Значение |
|------|----------|
| `-m MODULE` | Модуль |
| `-a "ARGS"` | Аргументы |
| `-b` | sudo (`become`) |

Примеры:

```bash
ansible web -m ping
ansible web -m command -a "uptime"
ansible web -m apt -a "name=nginx state=present" -b
```

Ad-hoc команды хороши для быстрой диагностики, проверки фактов и одноразовых действий. Но если ту же команду хочется сохранить, повторять или коммитить в git, пора переносить её в playbook.

---

## 2.2 Основные модули

### ping — проверить соединение

```bash
ansible all -m ping
```

### apt — пакеты

```bash
ansible web -m apt -a "name=nginx state=present update_cache=yes" -b
```

`state=present` = установить. `state=absent` = удалить.

Проверка идемпотентности:

```bash
# Первый запуск
ansible web -m apt -a "name=nginx state=present" -b
# web1 | CHANGED => {"changed": true}

# Второй запуск
ansible web -m apt -a "name=nginx state=present" -b
# web1 | SUCCESS => {"changed": false}
```

Первый запуск меняет систему. Второй подтверждает: пакет уже в нужном состоянии.

### service / systemd — сервисы

```bash
ansible web -m systemd -a "name=nginx state=started enabled=yes" -b
```

### copy — скопировать файл

```bash
ansible web -m copy -a "src=./nginx.conf dest=/etc/nginx/nginx.conf" -b
```

### file — директории и права

```bash
ansible web -m file -a "path=/var/www/myapp state=directory owner=deploy mode=0755" -b
```

### command — выполнить команду

```bash
ansible web -m command -a "uptime"
```

### shell — выполнить в shell (с pipe, redirect)

```bash
ansible web -m shell -a "echo 'hello' > /tmp/test.txt" -b
```

> **Правило:** Используй `command` когда можно, `shell` когда нужен pipe, redirect или shell-синтаксис.
> Всегда предпочитай модуль (`apt`, `systemd`, `copy`) shell-команде.

### shell vs модуль

```yaml
# НЕПРАВИЛЬНО: логика пакетов спрятана внутри shell
- shell: apt install -y nginx

# ПРАВИЛЬНО: Ansible понимает состояние и умеет быть идемпотентным
- apt:
    name: nginx
    state: present
```

---

## 2.3 `ansible-doc` — документация

```bash
ansible-doc apt
ansible-doc systemd
ansible-doc template
```

Показывает все параметры модуля, примеры и значения по умолчанию.

Если не помнишь, нужен `service` или `systemd`, сначала открой `ansible-doc`. Это быстрее, чем гадать по памяти.

---

## 2.4 Результат: `ok` vs `changed`

```text
web1 | SUCCESS => {"changed": false}
web2 | SUCCESS => {"changed": true}
```

| Статус | Значение |
|--------|----------|
| `changed: false` | Ничего не изменилось, уже было правильно |
| `changed: true` | Ansible внёс изменение |
| `failed` | Задача завершилась ошибкой |
| `unreachable` | Хост недоступен по SSH |

Для деплоя это критично:

- `changed: true` на первом запуске ожидаем.
- `changed: false` на повторном запуске означает идемпотентность.
- `unreachable` значит, что проблема ещё до playbook: сеть, SSH, ключ, пользователь.

---

## 2.5 Полезные однострочники для диагностики

Перед деплоем полезно быстро понять, жив ли сервер и в каком он состоянии.

### Свободное место

```bash
ansible web -m command -a "df -h /"
```

Если на корневом разделе почти нет места, новый релиз, логи или пакеты могут не влезть.

### Нагрузка

```bash
ansible web -m command -a "uptime"
```

Полезно проверить load average перед выкладкой.

### Статус сервиса

```bash
ansible web -m command -a "systemctl is-active nginx"
```

Быстро отвечает: `active`, `inactive`, `failed`.

### Последние логи

```bash
ansible web -m shell -a "journalctl -u nginx -n 20 --no-pager" -b
```

Если Nginx не стартует после конфигурации, первые 20 строк журнала обычно сразу показывают причину.

### Открытые порты

```bash
ansible web -m command -a "ss -tulpn"
```

Так можно увидеть, слушает ли сервис нужный порт, например `80` для Nginx или `8000` для Flask.

> **Практика:** Ad-hoc команды особенно полезны до playbook и после него.
> До playbook — проверить сервер. После — быстро подтвердить результат.

---

## 📝 Упражнения

### Упражнение 2.1: Ad-hoc команды
**Задача:**
1. `ansible web -m apt -a "name=htop state=present" -b`
2. `ansible web -m command -a "which htop"`
3. Запусти ещё раз — `changed: false`?

### Упражнение 2.2: Идемпотентность модуля apt
**Задача:**
1. Запусти `ansible web -m apt -a "name=nginx state=present" -b`
2. Посмотри результат первого запуска — был `changed: true`?
3. Запусти команду второй раз
4. Получил `changed: false`?

---

## 📋 Чеклист главы 2

- [ ] Я могу запустить ad-hoc команду
- [ ] Я знаю основные модули (apt, systemd, copy, file, command, shell)
- [ ] Я понимаю разницу `ok` vs `changed`
- [ ] Я использую модуль вместо shell когда можно

**Всё отметил?** Переходи к Главе 3 — Переменные.
