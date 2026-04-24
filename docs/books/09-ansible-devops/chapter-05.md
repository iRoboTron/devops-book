# Глава 5: Templates (Jinja2)

> **Запомни:** Template = конфиг с переменными. Один шаблон — разные серверы с разными значениями.

---

## 5.1 Проблема статических конфигов

```yaml
- name: Скопировать конфиг
  copy:
    src: files/nginx.conf
    dest: /etc/nginx/nginx.conf
```

Один файл для всех серверов. Но у dev `server_name dev.myapp.ru`, у prod `server_name myapp.ru`.

**Решение:** Template.

---

## 5.2 Шаблон Jinja2

```
templates/
└── nginx.conf.j2
```

```jinja2
server {
    listen {{ http_port | default(80) }};
    server_name {{ domain | default('localhost') }};

    location / {
        proxy_pass http://127.0.0.1:{{ app_port }};
    }

{% if enable_ssl | default(false) %}
    ssl_certificate /etc/letsencrypt/live/{{ domain }}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{ domain }}/privkey.pem;
{% endif %}
}
```

### Синтаксис

| Синтаксис | Значение |
|-----------|----------|
| `{{ variable }}` | Вставить переменную |
| `{% if condition %}` | Условие |
| `{% for item in list %}` | Цикл |
| `\| default(val)` | Значение по умолчанию |

---

## 5.3 Использовать template

```yaml
- name: Настроить Nginx
  template:
    src: templates/nginx.conf.j2
    dest: /etc/nginx/sites-enabled/myapp.conf
    owner: root
    group: root
    mode: '0644'
  notify: reload nginx
  vars:
    domain: "{{ ansible_hostname }}.example.com"
    app_port: 8000
```

---

## 5.4 Facts в шаблонах

```jinja2
# Автоматически используем IP сервера
server_name {{ ansible_default_ipv4.address }};

# Или имя хоста
server_name {{ ansible_hostname }}.example.com;
```

---

## 5.5 Циклы в шаблонах

```yaml
# group_vars/web.yml
allowed_ips:
  - 192.168.1.0/24
  - 10.0.0.0/8
```

```jinja2
{% for ip in allowed_ips %}
allow {{ ip }};
{% endfor %}
```

Результат:

```
allow 192.168.1.0/24;
allow 10.0.0.0/8;
```

---

## 📝 Упражнения

### Упражнение 5.1: Создать template
**Задача:**
1. Создай `templates/nginx.conf.j2` с `{{ domain }}` и `{{ app_port }}`
2. Используй `template` модуль в playbook
3. `ansible-playbook site.yml` — конфиг сгенерирован?

### Упражнение 5.2: Условия
**Задача:**
1. Добавь `{% if enable_ssl %}` блок в template
2. Запусти с `enable_ssl: false` — SSL блока нет?
3. Запусти с `enable_ssl: true` — SSL блок появился?

---

## 📋 Чеклист главы 5

- [ ] Я могу создать Jinja2 template
- [ ] Я использую `{{ variable }}` и `{% if %}`
- [ ] Я могу использовать facts в templates
- [ ] Я могу использовать циклы в templates
- [ ] Template модуль копирует с переменными

**Всё отметил?** Переходи к Главе 6 — Roles.
