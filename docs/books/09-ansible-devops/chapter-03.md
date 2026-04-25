# Глава 3: Переменные

> **Запомни:** Переменные = код без хардкода. Правильное место хранения = порядок в проекте.
>
> **Проект этой главы:** выносим параметры деплоя в переменные: `domain`, `app_port`, `deploy_user`.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 3.1 Иерархия переменных

Приоритет (от низкого к высокому):

```text
role defaults      ← самый низкий
inventory vars
group_vars
host_vars
playbook vars
role vars
task vars
extra-vars (-e)    ← самый высокий
```

Чем выше приоритет, тем легче переменная переопределяет значения снизу.

В нашем проекте это выглядит так:

- `group_vars/web.yml` хранит обычные настройки приложения.
- `host_vars/web1.yml` хранит исключения только для одного сервера.
- `-e` удобно использовать в CI/CD и для временных запусков.

---

## 3.2 group_vars и host_vars

```text
inventory/
├── hosts.yml
├── group_vars/
│   ├── all.yml
│   └── web.yml
└── host_vars/
    └── web1.yml
```

### group_vars/all.yml

```yaml
deploy_user: deploy
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
app_root: /opt/myapp
```

### host_vars/web1.yml

```yaml
server_role: primary
domain: web1.myapp.ru
```

Идея простая:

- `group_vars/all.yml` для всего проекта.
- `group_vars/web.yml` для всех веб-серверов.
- `host_vars/web1.yml` только для одного конкретного хоста.

---

## 3.3 Facts — автоматические переменные

Ansible сам собирает информацию о каждом хосте:

```bash
ansible web -m setup
```

### Популярные facts

| Fact | Значение |
|------|----------|
| `ansible_hostname` | Имя хоста |
| `ansible_default_ipv4.address` | IP адрес |
| `ansible_os_family` | `Debian` или `RedHat` |
| `ansible_distribution` | `Ubuntu`, `Debian`, `CentOS` |
| `ansible_memory_mb.real.total` | RAM в МБ |
| `ansible_processor_vcpus` | Количество CPU |

### Фильтровать facts

```bash
ansible web -m setup -a "filter=ansible_default_ipv4"
```

Это удобнее полного вывода, когда нужна одна конкретная часть.

---

## 3.4 `register` — сохранить результат

```yaml
- name: Проверить статус nginx
  command: systemctl is-active nginx
  register: nginx_status
  changed_when: false

- name: Показать результат
  debug:
    var: nginx_status.stdout
```

Если сервис работает, `nginx_status.stdout` будет `active`.

`register` нужен, когда следующий шаг зависит от результата предыдущего: статуса сервиса, вывода команды, HTTP-проверки или факта наличия файла.

---

## 3.5 `when` — условное выполнение

```yaml
- name: Установить nginx только на Debian
  apt:
    name: nginx
  when: ansible_os_family == "Debian"

- name: Перезапустить только если nginx уже запущен
  service:
    name: nginx
    state: restarted
  when: nginx_status.stdout == "active"
```

`when` помогает не писать отдельные playbook под каждый случай.

---

## 3.6 `debug` — вывод

```yaml
- debug:
    msg: "Сервер {{ inventory_hostname }}, IP: {{ ansible_default_ipv4.address }}"

- debug:
    var: nginx_status
```

`debug` особенно полезен, когда нужно быстро проверить:

- какая переменная реально подставилась;
- что вернул `register`;
- какой факт увидел Ansible на конкретном хосте.

---

## 3.7 Что побеждает при конфликте

Если одна и та же переменная определена в двух местах, выиграет источник с более высоким приоритетом.

Пример:

```yaml
# group_vars/web.yml
http_port: 80

# host_vars/web1.yml
http_port: 8080   # переопределяет для конкретного хоста
```

Проверим, какое значение увидит Ansible:

```bash
ansible web -m debug -a "msg={{ http_port }}"
```

```text
web1 | SUCCESS => {
    "msg": "8080"
}
web2 | SUCCESS => {
    "msg": "80"
}
```

Итог:

- для `web1` победил `host_vars/web1.yml`;
- для остальных хостов группы `web` осталось значение из `group_vars/web.yml`.

> **Запомни:** если переменная "не та", сначала ищи дубликаты в `group_vars`, `host_vars` и `-e`.

---

## 3.8 `extra-vars` для разового переопределения

Иногда нужно временно переопределить параметры без правки файлов.

```bash
ansible-playbook site.yml -e "domain=staging.myapp.ru app_port=9000"
```

Это удобно для:

- staging и production из одного playbook;
- временной проверки другого домена;
- CI/CD, где параметры приходят из pipeline.

Важно: `-e` имеет самый высокий приоритет. Если передал значение через `extra-vars`, оно перекроет `group_vars`, `host_vars` и `defaults` роли.

---

## 📝 Упражнения

### Упражнение 3.1: group_vars
**Задача:**
1. Создай `group_vars/web.yml` с `http_port: 80`
2. Добавь туда `domain` и `app_port`
3. Используй переменную в `debug: var=http_port`
4. `ansible-playbook` — значение правильное?

### Упражнение 3.2: Facts
**Задача:**
1. `ansible web -m setup -a "filter=ansible_hostname"`
2. `ansible web -m setup -a "filter=ansible_memory_mb"`
3. Выведи через `debug` имя хоста и объём RAM в playbook

### Упражнение 3.3: when
**Задача:**
1. Создай задачу которая работает только на Ubuntu
2. Создай `host_vars/web1.yml` и переопредели `http_port`
3. Запусти `ansible web -m debug -a "msg={{ http_port }}"`
4. Убедись что `host_vars` победил `group_vars`

---

## 📋 Чеклист главы 3

- [ ] Я понимаю иерархию переменных
- [ ] Я могу использовать group_vars и host_vars
- [ ] Я могу посмотреть facts (`ansible -m setup`)
- [ ] Я могу использовать `register` для сохранения результата
- [ ] Я могу использовать `when` для условий
- [ ] Я могу выводить через `debug`

**Всё отметил?** Переходи к Главе 4 — Первый playbook.
