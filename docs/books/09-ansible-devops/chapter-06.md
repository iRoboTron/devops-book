# Глава 6: Roles

> **Запомни:** Role = переиспользуемый набор задач. Один playbook на 500 строк = проблема. 5 ролей по 100 строк = порядок.

---

## 6.1 Структура роли

```bash
ansible-galaxy init nginx
```

```
roles/
└── nginx/
    ├── tasks/
    │   └── main.yml       # задачи
    ├── handlers/
    │   └── main.yml       # handlers
    ├── templates/
    │   └── nginx.conf.j2  # шаблоны
    ├── files/
    │   └── nginx.conf     # статические файлы
    ├── vars/
    │   └── main.yml       # переменные (высокий приоритет)
    ├── defaults/
    │   └── main.yml       # переменные (низкий приоритет)
    └── meta/
        └── main.yml       # зависимости
```

---

## 6.2 Содержимое роли

### tasks/main.yml

```yaml
- name: Установить nginx
  apt:
    name: nginx
    state: present

- name: Скопировать конфиг
  template:
    src: nginx.conf.j2
    dest: /etc/nginx/sites-enabled/myapp.conf
  notify: reload nginx

- name: Запустить nginx
  service:
    name: nginx
    state: started
    enabled: yes
```

### handlers/main.yml

```yaml
- name: reload nginx
  service:
    name: nginx
    state: reloaded
```

### defaults/main.yml

```yaml
http_port: 80
app_port: 8000
domain: localhost
```

---

## 6.3 Вызов роли

### site.yml

```yaml
- hosts: web
  become: true
  roles:
    - common
    - nginx
    - myapp
```

Или через `roles:` в playbook:

```yaml
- hosts: web
  become: true
  roles:
    - role: nginx
      http_port: 8080    # переопределить default
```

---

## 6.4 Зависимости

### meta/main.yml

```yaml
dependencies:
  - role: common
```

При вызове `nginx` Ansible сначала запустит `common`.

---

## 6.5 defaults vs vars

| | defaults | vars |
|--|----------|------|
| **Приоритет** | Низкий (легко переопределить) | Высокий (константа) |
| **Когда** | Значения по умолчанию | Внутренние константы роли |

> **Правило:** Используй `defaults` для того что пользователь роли может захотеть поменять.
> `vars` — для внутренних констант роли.

---

## 📝 Упражнения

### Упражнение 6.1: Создать роль
**Задача:**
1. `ansible-galaxy init nginx`
2. Перенеси задачи из playbook в `tasks/main.yml`
3. Запусти `ansible-playbook site.yml` — работает?

### Упражнение 6.2: Разбить на роли
**Задача:**
1. Создай роли: `common`, `nginx`, `myapp`
2. `site.yml` вызывает все три
3. Идемпотентность: 0 changed при втором запуске?

---

## 📋 Чеклист главы 6

- [ ] Я знаю структуру роли
- [ ] Я могу создать роль через `ansible-galaxy init`
- [ ] Я могу вызвать роль в playbook
- [ ] Я понимаю разницу defaults vs vars
- [ ] Я могу добавить зависимости через meta/main.yml

**Всё отметил?** Переходи к Главе 7 — Vault.
