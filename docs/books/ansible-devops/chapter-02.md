# Глава 2: Ad-hoc команды и модули

> **Запомни:** Ad-hoc = быстрая команда без playbook. Для разовых задач. Для повторяющихся — playbook.

---

## 2.1 Синтаксис

```bash
ansible <группа> -m <модуль> -a "<аргументы>" -b
```

| Флаг | Значение |
|------|----------|
| `-m MODULE` | Модуль |
| `-a "ARGS"` | Аргументы |
| `-b` | sudo (become) |

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

> **Правило:** Используй `command` когда можно, `shell` когда нужен pipe/redirect.
> Всегда предпочитай модуль (apt, service) shell-команде.

### shell vs модуль

```yaml
# НЕПРАВИЛЬНО (не идемпотентно):
- shell: apt install nginx

# ПРАВИЛЬНО (идемпотентно):
- apt:
    name: nginx
    state: present
```

---

## 2.3 `ansible-doc` — документация

```bash
ansible-doc apt
ansible-doc systemd
```

Показывает все параметры модуля.

---

## 2.4 Результат: `ok` vs `changed`

```
web1 | SUCCESS => {"changed": false}   # уже было правильно
web2 | SUCCESS => {"changed": true}    # только что изменено
```

| Статус | Значение |
|--------|----------|
| `changed: false` | Ничего не изменилось (уже правильно) |
| `changed: true` | Что-то изменено |
| `failed` | Ошибка |

---

## 📝 Упражнения

### Упражнение 2.1: Ad-hoc команды
**Задача:**
1. `ansible web -m apt -a "name=htop state=present" -b`
2. `ansible web -m command -a "which htop"`
3. Запусти ещё раз — `changed: false`?

### Упражнение 2.2: Модуль vs shell
**Задача:**
1. Установи nginx через shell: `ansible web -m shell -a "apt install -y nginx" -b`
2. Теперь через модуль: `ansible web -m apt -a "name=nginx state=present" -b`
3. Второй раз — `changed: false`?

---

## 📋 Чеклист главы 2

- [ ] Я могу запустить ad-hoc команду
- [ ] Я знаю основные модули (apt, systemd, copy, file, command, shell)
- [ ] Я понимаю разницу `ok` vs `changed`
- [ ] Я использую модуль вместо shell когда можно

**Всё отметил?** Переходи к Главе 3 — Переменные.
