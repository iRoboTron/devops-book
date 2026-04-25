# Глава 6: Roles

> **Запомни:** Role = переиспользуемый набор задач. Один playbook на 500 строк = проблема. 5 ролей по 100 строк = порядок.
>
> **Проект этой главы:** выносим Nginx и приложение в отдельные роли `nginx` и `myapp`.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 6.1 Структура роли

```bash
ansible-galaxy init nginx
```

```text
roles/
└── nginx/
    ├── tasks/
    │   └── main.yml       # задачи
    ├── handlers/
    │   └── main.yml       # handlers
    ├── templates/
    │   └── myapp.conf.j2  # шаблоны
    ├── files/
    │   └── nginx.conf     # статические файлы
    ├── vars/
    │   └── main.yml       # переменные (высокий приоритет)
    ├── defaults/
    │   └── main.yml       # переменные (низкий приоритет)
    └── meta/
        └── main.yml       # зависимости
```

Идея простая: всё, что относится к Nginx, живёт внутри роли `nginx`. Всё, что относится к приложению, живёт внутри `myapp`.

---

## 6.2 Содержимое роли

### `roles/nginx/tasks/main.yml`

```yaml
- name: Установить nginx
  apt:
    name: nginx
    state: present

- name: Сгенерировать конфиг сайта
  template:
    src: myapp.conf.j2
    dest: /etc/nginx/sites-enabled/myapp.conf
  notify: reload nginx

- name: Запустить nginx
  service:
    name: nginx
    state: started
    enabled: yes
```

### `roles/nginx/handlers/main.yml`

```yaml
- name: reload nginx
  service:
    name: nginx
    state: reloaded
```

### `roles/nginx/defaults/main.yml`

```yaml
http_port: 80
app_port: 8000
domain: localhost
```

### `roles/myapp/tasks/main.yml`

```yaml
- name: Создать пользователя deploy
  user:
    name: "{{ deploy_user }}"
    shell: /bin/bash
    create_home: yes

- name: Создать директорию приложения
  file:
    path: "{{ app_root }}"
    state: directory
    owner: "{{ deploy_user }}"
    group: "{{ deploy_user }}"
    mode: '0755'
```

Теперь `site.yml` становится коротким, а логика раскладывается по модулям проекта.

---

## 6.3 Вызов роли

### `site.yml`

```yaml
- hosts: web
  become: true
  roles:
    - common
    - nginx
    - myapp
```

Или через `roles:` в playbook с переопределением:

```yaml
- hosts: web
  become: true
  roles:
    - role: nginx
      http_port: 8080
```

Реальный вывод запуска:

```bash
ansible-playbook site.yml
```

```text
PLAY [web] **********************************************

ROLE [common] *******************************************
TASK [common : Обновить apt кэш] ************************
ok: [web1]
TASK [common : Установить базовые пакеты] ***************
changed: [web1]

ROLE [nginx] ********************************************
TASK [nginx : Установить nginx] *************************
changed: [web1]
TASK [nginx : Сгенерировать конфиг сайта] ***************
changed: [web1]
RUNNING HANDLER [nginx : reload nginx] ******************
changed: [web1]

ROLE [myapp] ********************************************
TASK [myapp : Создать пользователя deploy] **************
changed: [web1]
TASK [myapp : Создать директорию приложения] ************
changed: [web1]

PLAY RECAP **********************************************
web1 : ok=8  changed=6  unreachable=0  failed=0
```

Так уже видно, какая часть деплоя за что отвечает.

---

## 6.4 Зависимости

### `meta/main.yml`

```yaml
dependencies:
  - role: common
```

При вызове `nginx` Ansible сначала запустит `common`.

Это полезно, если роль зависит от базовых пакетов, пользователя, директории или общей системной подготовки.

---

## 6.5 defaults vs vars

| | defaults | vars |
|--|----------|------|
| **Приоритет** | Низкий (легко переопределить) | Высокий (константа) |
| **Когда** | Значения по умолчанию | Внутренние константы роли |

> **Правило:** Используй `defaults` для того, что пользователь роли может захотеть поменять.
> `vars` — для внутренних констант роли.

Для нашей роли `nginx` в `defaults` логично держать `domain`, `http_port`, `app_port`. А, например, внутренний путь до служебного файла роли можно держать в `vars`.

---

## 6.6 Ansible Galaxy — готовые роли

Не все роли нужно писать с нуля.

```bash
# Найти роль
ansible-galaxy search nginx

# Установить роль
ansible-galaxy install geerlingguy.nginx

# Список установленных
ansible-galaxy list
```

Роль ставится в `~/.ansible/roles/` или в `roles/` проекта.

Использовать в playbook:

```yaml
- hosts: web
  become: true
  roles:
    - geerlingguy.nginx
    - myapp
```

Когда это полезно:

- сложный продукт вроде PostgreSQL, Redis или Docker;
- роль уже проверена сообществом;
- не хочется поддерживать тонкую настройку вручную.

---

## 📝 Упражнения

### Упражнение 6.1: Создать роль
**Задача:**
1. `ansible-galaxy init nginx`
2. Перенеси задачи из playbook в `roles/nginx/tasks/main.yml`
3. Добавь `roles/nginx/handlers/main.yml`
4. Запусти `ansible-playbook site.yml` — работает?

### Упражнение 6.2: Разбить на роли
**Задача:**
1. Создай роли: `common`, `nginx`, `myapp`
2. `site.yml` вызывает все три
3. Проверь вывод ролей в `ansible-playbook site.yml`
4. Идемпотентность: 0 changed при втором запуске?

---

## 📋 Чеклист главы 6

- [ ] Я знаю структуру роли
- [ ] Я могу создать роль через `ansible-galaxy init`
- [ ] Я могу вызвать роль в playbook
- [ ] Я понимаю разницу defaults vs vars
- [ ] Я могу добавить зависимости через meta/main.yml

**Всё отметил?** Переходи к Главе 7 — Vault.
