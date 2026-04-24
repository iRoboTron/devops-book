# Глава 3: Переменные

> **Запомни:** Переменные = код без хардкода. Правильное место хранения = порядок в проекте.

---

## 3.1 Иерархия переменных

Приоритет (от низкого к высокому):

```
role defaults      ← самый низкий
inventory vars
group_vars
host_vars
playbook vars
role vars
task vars
extra-vars (-e)    ← самый высокий
```

---

## 3.2 group_vars и host_vars

```
inventory/
├── hosts.yml
├── group_vars/
│   ├── all.yml     # для всех
│   ├── web.yml     # только для web
│   └── db.yml      # только для db
└── host_vars/
    └── web1.yml    # только для web1
```

### group_vars/all.yml

```yaml
ansible_user: deploy
timezone: Europe/Moscow
packages:
  - git
  - htop
  - curl
```

### group_vars/web.yml

```yaml
http_port: 80
app_port: 8000
domain: myapp.ru
```

### host_vars/web1.yml

```yaml
server_role: primary
```

---

## 3.3 Facts — автоматические переменные

Ansible собирает информацию о каждом хосте:

```bash
ansible web -m setup
```

### Популярные facts

| Fact | Значение |
|------|----------|
| `ansible_hostname` | Имя хоста |
| `ansible_default_ipv4.address` | IP адрес |
| `ansible_os_family` | "Debian" или "RedHat" |
| `ansible_distribution` | "Ubuntu" |
| `ansible_memory_mb.real.total` | RAM в МБ |
| `ansible_processor_vcpus` | Количество CPU |

### Фильтровать

```bash
ansible web -m setup -a "filter=ansible_default_ipv4"
```

---

## 3.4 `register` — сохранить результат

```yaml
- name: Проверить статус nginx
  command: systemctl is-active nginx
  register: nginx_status

- name: Показать результат
  debug:
    var: nginx_status.stdout
```

`nginx_status.stdout` = "active" или "inactive".

---

## 3.5 `when` — условное выполнение

```yaml
- name: Установить nginx только на Debian
  apt:
    name: nginx
  when: ansible_os_family == "Debian"

- name: Перезапустить только если nginx запущен
  service:
    name: nginx
    state: restarted
  when: nginx_status.stdout == "active"
```

---

## 3.6 `debug` — вывод

```yaml
- debug:
    msg: "Сервер {{ inventory_hostname }}, IP: {{ ansible_default_ipv4.address }}"

- debug:
    var: nginx_status
```

---

## 📝 Упражнения

### Упражнение 3.1: group_vars
**Задача:**
1. Создай `group_vars/web.yml` с `http_port: 80`
2. Используй переменную в debug: `debug: var=http_port`
3. `ansible-playbook` — значение правильное?

### Упражнение 3.2: Facts
**Задача:**
1. `ansible web -m setup -a "filter=ansible_hostname"`
2. `ansible web -m setup -a "filter=ansible_memory_mb"`
3. Выведи через debug в playbook

### Упражнение 3.3: when
**Задача:**
1. Создай задачу которая работает только на Ubuntu
2. Запусти на разных серверах — сработала только где нужно?

---

## 📋 Чеклист главы 3

- [ ] Я понимаю иерархию переменных
- [ ] Я могу использовать group_vars и host_vars
- [ ] Я могу посмотреть facts (`ansible -m setup`)
- [ ] Я могу использовать `register` для сохранения результата
- [ ] Я могу использовать `when` для условий
- [ ] Я могу выводить через `debug`

**Всё отметил?** Переходи к Главе 4 — Первый playbook.
