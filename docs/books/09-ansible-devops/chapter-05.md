# Глава 5: Templates (Jinja2)

> **Запомни:** Template = конфиг с переменными. Один шаблон — разные серверы с разными значениями.
>
> **Проект этой главы:** генерируем `nginx`-конфиг для Flask-приложения из переменных.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 5.1 Проблема статических конфигов

```yaml
- name: Скопировать конфиг
  copy:
    src: files/nginx.conf
    dest: /etc/nginx/nginx.conf
```

Один файл для всех серверов. Но у staging `server_name staging.myapp.ru`, у production `server_name myapp.ru`, а у локального стенда может быть вообще другой порт приложения.

**Решение:** Template.

---

## 5.2 Шаблон Jinja2

```text
templates/
└── myapp.conf.j2
```

```jinja2
server {
    listen {{ http_port | default(80) }};
    server_name {{ domain | default('localhost') }};

    location / {
        proxy_pass http://127.0.0.1:{{ app_port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
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
- name: Сгенерировать конфиг Nginx для приложения
  template:
    src: templates/myapp.conf.j2
    dest: /etc/nginx/sites-enabled/myapp.conf
    owner: root
    group: root
    mode: '0644'
  notify: reload nginx
```

Здесь уже не нужно хардкодить `domain` и `app_port` прямо в задаче. Ansible возьмёт значения из `group_vars` и `host_vars`.

---

## 5.4 Facts в шаблонах

```jinja2
# Автоматически используем IP сервера
server_name {{ ansible_default_ipv4.address }};

# Или имя хоста
server_name {{ ansible_hostname }}.example.com;
```

Facts полезны, когда шаблон должен зависеть от реального сервера, а не только от статических переменных.

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

```text
allow 192.168.1.0/24;
allow 10.0.0.0/8;
```

Так удобно генерировать whitelist, upstream-блоки, список серверов или набор location-правил.

---

## 5.6 Проверить что сгенерировалось

После применения playbook проверь итоговый файл на сервере:

```bash
ansible web -m command -a "cat /etc/nginx/sites-enabled/myapp.conf"
```

Ожидаемый результат:

```text
server {
    listen 80;
    server_name myapp.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Перед применением можно посмотреть diff:

```bash
ansible-playbook site.yml --check --diff
```

```text
--- before: /etc/nginx/sites-enabled/myapp.conf
+++ after: template rendered
@@ -2,7 +2,7 @@
     listen 80;
-    server_name localhost;
+    server_name myapp.ru;
```

Это лучший способ убедиться, что переменные действительно подставились как ожидается.

---

## 5.7 Отладка шаблона локально

Иногда проблема не в Ansible, а в самом шаблоне. Удобно проверить его локально:

```bash
pip install jinja2-cli
```

```bash
jinja2 templates/myapp.conf.j2 \
  --format=json \
  -D domain=myapp.ru \
  -D app_port=8000 \
  -D http_port=80
```

Это позволяет проверить логику шаблона без подключения к серверу и без запуска полного playbook.

---

## 📝 Упражнения

### Упражнение 5.1: Создать template
**Задача:**
1. Создай `templates/myapp.conf.j2` с `{{ domain }}` и `{{ app_port }}`
2. Используй `template` модуль в playbook
3. `ansible-playbook site.yml` — конфиг сгенерирован?
4. Проверь итог через `ansible web -m command -a "cat /etc/nginx/sites-enabled/myapp.conf"`

### Упражнение 5.2: Условия
**Задача:**
1. Добавь `{% if enable_ssl %}` блок в template
2. Запусти с `enable_ssl: false` — SSL блока нет?
3. Запусти с `enable_ssl: true` — SSL блок появился?
4. Посмотри diff через `ansible-playbook site.yml --check --diff`

---

## 📋 Чеклист главы 5

- [ ] Я могу создать Jinja2 template
- [ ] Я использую `{{ variable }}` и `{% if %}`
- [ ] Я могу использовать facts в templates
- [ ] Я могу использовать циклы в templates
- [ ] Template модуль копирует с переменными

**Всё отметил?** Переходи к Главе 6 — Roles.
