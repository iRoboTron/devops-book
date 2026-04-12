# Инструкция для ИИ-агента: Написание книги по Ansible

> **Это Модуль 9 курса DevOps 2.0.**
> Предварительные требования: пройдены модули 1–8 (включая Terraform).
> Смотри также:
> - [AGENT-INSTRUCTIONS-module-08.md](AGENT-INSTRUCTIONS-module-08.md) — Модуль 8 (Terraform)
> - [AGENT-INSTRUCTIONS-module-05.md](AGENT-INSTRUCTIONS-module-05.md) — Модуль 5 (Инфраструктура)

---

## Контекст проекта

Ученик прошёл Terraform — он умеет создавать серверы кодом. Но серверы создаются пустыми.
Кто устанавливает пакеты, копирует конфиги, запускает сервисы? Раньше — он вручную по SSH. Теперь — Ansible.

**Что он уже умеет** (не повторяй):
- Уверенно работает в Linux: права, процессы, systemctl, journalctl
- Знает SSH-ключи, файловую систему, переменные окружения
- Писал shell-скрипты
- Создавал серверы через Terraform — умеет получить IP сервера из `terraform output`
- Понимает что такое идемпотентность (из книги по Terraform)

**Что его раздражает прямо сейчас:**
- После `terraform apply` — SSH на сервер и руками `apt install`, `nano /etc/nginx/...`, `systemctl enable`
- Если нужно настроить 5 серверов — 5 раз SSH и одно и то же
- Забыл шаг → сервер настроен не так → ищи ошибку

**Что он хочет после этой книги:**
Написать playbook один раз → запустить на любом количестве серверов → серверы настроены идентично. Без ручного SSH. Без shell-скриптов с `if [ ! -f ... ]` проверками.

---

## Что за книга

**Название:** "Ansible: Управление конфигурацией"

**Место в курсе:** Книга 9 из 14

**Целевая аудитория:**
- Прошёл Terraform, умеет создавать серверы
- Устал настраивать серверы вручную по SSH
- Писал shell-скрипты, знает их недостатки

**Объём:** 140-170 страниц

**Стиль:**
- Простой язык, без академизма
- Одна концепция — одно объяснение
- ASCII-схемы для потоков выполнения и структуры ролей
- Много практики, реальные задачи
- Без воды

---

## Главная идея, которую должна передать книга

Ansible решает одну проблему: **"одинаковая конфигурация на всех серверах"**.

```
Shell-скрипт:           Ansible:
./setup.sh              ansible-playbook setup.yml
↓                       ↓
последовательно         параллельно на всех серверах
не идемпотентно         идемпотентно
ломается на второй      работает одинаково каждый раз
  запуск
```

**Главная концепция — идемпотентность:**
> Запусти playbook дважды — результат одинаковый. Ansible не сломается, не переустановит то что уже установлено, не перезапустит то что уже запущено с правильным конфигом.

Это не просто удобство. Это значит playbook = документация состояния сервера. Что описано в playbook — то и настроено.

---

## Что читатель построит к концу книги

```
Terraform output → IP серверов
         │
         ▼
Ansible Inventory
    [web_servers]
    server1 ansible_host=1.2.3.4
    server2 ansible_host=5.6.7.8

         │
ansible-playbook site.yml
         │
         ├── Role: common
         │   ├── apt update, базовые пакеты
         │   ├── часовой пояс, hostname
         │   └── создать deploy-пользователя
         │
         ├── Role: nginx
         │   ├── установить nginx
         │   ├── скопировать конфиг (template)
         │   └── systemctl enable nginx
         │
         └── Role: myapp
             ├── скопировать код
             ├── установить зависимости
             └── systemctl enable myapp
```

Один `ansible-playbook site.yml` → оба сервера настроены одинаково.

---

## Структура книги

### Глава 0: Зачем Ansible и как он работает

**Цель:** читатель понимает модель работы Ansible — agentless, push-модель, SSH.

- Почему shell-скрипты плохи для конфигурации:
  ```
  Shell:                      Ansible:
  if [ ! -f /etc/nginx.conf ] nginx модуль сам проверяет
    cp nginx.conf ...           нужно ли что-то делать
  fi
  (10 строк вместо 3)
  ```
- Как Ansible работает: SSH + Python на удалённом хосте
  ```
  Твой ноутбук                  Сервер
  ansible-playbook ──SSH──→  запустить task
                             вернуть результат
  ```
- Agentless: не нужно устанавливать агент на серверы (только Python + SSH)
- Ansible vs Chef/Puppet: push vs pull, agentless vs agent
- Установка: `pip install ansible` или `apt install ansible`
- Проверка: `ansible --version`
- Структура проекта:
  ```
  ansible/
  ├── inventory/
  │   └── hosts.yml
  ├── roles/
  │   └── nginx/
  ├── site.yml
  └── ansible.cfg
  ```

> **Ключевая идея:** Ansible не хранит состояние. Каждый раз читает желаемое из playbook и сравнивает с реальным. Если совпадает — ничего не делает.

---

### Часть 1: Основы (Главы 1–4)

#### Глава 1: Inventory и ansible.cfg — список серверов

**Цель:** читатель описывает свои серверы и проверяет что Ansible до них достучится.

- Inventory форматы: INI и YAML (YAML предпочтительно)
  ```yaml
  all:
    children:
      web:
        hosts:
          web1:
            ansible_host: 1.2.3.4
    vars:
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/id_rsa
  ```
- `ansible.cfg` — конфигурация по умолчанию
- `ansible all -m ping` — проверить соединение
- **Динамический inventory из Terraform:**
  ```bash
  # Terraform output → Ansible inventory
  terraform output -json | python3 gen_inventory.py > inventory/hosts.yml
  ```
  ```python
  # gen_inventory.py — читает terraform output, пишет hosts.yml
  import json, sys
  tf = json.load(sys.stdin)
  for ip in tf["server_ips"]["value"]:
      print(f"  {ip['name']}:")
      print(f"    ansible_host: {ip['address']}")
  ```
  > **Мост к Модулю 8:** Terraform создал серверы → Ansible получил их IP автоматически.
  > Никакого ручного копирования IP.

**Упражнения:** создать inventory вручную, проверить ping, сгенерировать inventory из terraform output.

#### Глава 2: Ad-hoc команды и модули

**Цель:** читатель умеет выполнять одиночные задачи без playbook.

- Ad-hoc: быстрые одноразовые команды
- `-b` (become) = sudo
- Разница `command` vs `shell`
- Таблица основных модулей (apt, service, copy, template, file, user, command, shell, fetch)
- `ansible-doc MODULE` — документация
- `changed` vs `ok` — результат

> **Правило:** Если есть модуль — используй модуль, не shell.
> `shell` — только когда нет подходящего модуля.

**Упражнения:** установить nginx, проверить статус, остановить — всё ad-hoc.

#### Глава 3: Переменные и переменные окружения

**Цель:** читатель понимает иерархию переменных ДО того как начнёт писать playbook.

> **Исправление порядка:** переменные нужны для templates. Поэтому эта глава ДО playbook.

- Места хранения (от низкого к высокому приоритету):
  ```
  role defaults → inventory vars → playbook vars → role vars → task vars → extra-vars (-e)
  ```
- `group_vars/` и `host_vars/`
- `vars_files` в playbook
- Ansible facts: `ansible_hostname`, `ansible_default_ipv4.address`, `ansible_os_family`
- `ansible web -m setup` — все факты хоста
- `register` — сохранить результат задачи
- `when` — условное выполнение
- `debug` — вывод переменных

**Упражнения:** создать group_vars для web/db, использовать facts в переменных, conditional task.

#### Глава 4: Первый playbook

**Цель:** читатель пишет playbook и понимает его структуру.

- Структура playbook (play → tasks → handlers)
- `ansible-playbook site.yml`
- `--check` (dry-run), `-v`, `-vvv`
- Handlers и notify

> **ОБЯЗАТЕЛЬНОЕ УПРАЖНЕНИЕ: Проверка идемпотентности**
> Запустить playbook дважды. Второй раз — только `ok`, ноль `changed`.

**Упражнения:** playbook для nginx с config copy + handler, проверить идемпотентность.

---

### Часть 2: Шаблоны и роли (Главы 5–7)

#### Глава 5: Templates — динамические конфиги

**Цель:** читатель создаёт конфиги с переменными через Jinja2.

- Проблема: разные серверы требуют разных значений в конфиге (domain, port, workers)
- Template модуль + Jinja2:
  ```jinja2
  # templates/nginx.conf.j2
  server {
      listen 80;
      server_name {{ server_name }};

      location / {
          proxy_pass http://127.0.0.1:{{ app_port }};
      }
  }
  ```
  ```yaml
  - name: Настроить Nginx
    template:
      src: templates/nginx.conf.j2
      dest: /etc/nginx/sites-enabled/myapp.conf
    vars:
      server_name: "{{ ansible_hostname }}.example.com"
      app_port: 8000
  ```
- Встроенные переменные Ansible (facts):
  - `ansible_hostname` — имя хоста
  - `ansible_default_ipv4.address` — IP адрес
  - `ansible_os_family` — "Debian", "RedHat"
  - `ansible_distribution_version` — версия ОС
- `ansible web -m setup` — посмотреть все факты хоста
- `ansible web -m setup -a "filter=ansible_default_ipv4"` — отфильтровать
- Условия в шаблонах:
  ```jinja2
  {% if enable_ssl %}
  ssl_certificate /etc/letsencrypt/live/{{ domain }}/fullchain.pem;
  {% endif %}
  ```
- Циклы в шаблонах:
  ```jinja2
  {% for port in allowed_ports %}
  allow {{ port }};
  {% endfor %}
  ```

**Упражнения:** создать template для nginx.conf с переменными, применить к разным серверам с разными значениями.

#### Глава 6: Roles — структура для переиспользования

**Цель:** читатель организует playbook в roles — переиспользуемые блоки.

- Зачем roles: один playbook на 500 строк — это проблема
- Стандартная структура role
- `ansible-galaxy init nginx` — создать scaffolding роли
- Вызов роли в playbook
- `defaults/main.yml` vs `vars/main.yml`
- Зависимости между ролями в `meta/main.yml`
- Ansible Galaxy: готовые роли сообщества (упомянуть, не углубляться)

**Упражнения:** разбить существующий playbook на роли: `common`, `nginx`, `myapp`. Убедиться что `ansible-playbook site.yml` работает как раньше.

---

### Часть 3: Продвинутые практики (Главы 7–9)

#### Глава 7: Vault — шифрование секретов

**Цель:** читатель не хранит пароли в git в открытом виде.

- Проблема: пароли от БД, API-ключи в `group_vars/all.yml` — коммитишь в git → секрет виден всем
- Ansible Vault: шифрует файлы симметричным шифрованием
  ```bash
  # Зашифровать файл
  ansible-vault encrypt group_vars/all/secrets.yml

  # Редактировать зашифрованный файл
  ansible-vault edit group_vars/all/secrets.yml

  # Просмотреть без расшифровки
  ansible-vault view group_vars/all/secrets.yml

  # Расшифровать
  ansible-vault decrypt group_vars/all/secrets.yml

  # Зашифровать строку (вставить в yaml)
  ansible-vault encrypt_string 'mysecret' --name 'db_password'
  ```
- Запуск playbook с vault-паролем:
  ```bash
  ansible-playbook site.yml --ask-vault-pass
  ansible-playbook site.yml --vault-password-file .vault_pass
  ```
- `.vault_pass` файл в `.gitignore` — никогда не коммитить
- В CI: передать vault-пароль через переменную окружения:
  ```bash
  ANSIBLE_VAULT_PASSWORD_FILE=/tmp/vault_pass ansible-playbook site.yml
  ```
- Структура: secrets.yml (зашифрован) + vars.yml (ссылки на переменные из secrets)

> **Правило:** зашифрованные файлы vault можно и нужно коммитить в git. Расшифровать без пароля — невозможно.

#### Глава 8: Loops и conditions — управление потоком

**Цель:** читатель не пишет 10 одинаковых задач.

- `loop` — цикл по списку:
  ```yaml
  - name: Установить пакеты
    apt:
      name: "{{ item }}"
      state: present
    loop:
      - nginx
      - python3
      - git
  ```
- `loop` со словарями:
  ```yaml
  - name: Создать пользователей
    user:
      name: "{{ item.name }}"
      groups: "{{ item.groups }}"
    loop:
      - { name: alice, groups: sudo }
      - { name: bob, groups: www-data }
  ```
- `when` — условное выполнение:
  ```yaml
  - name: Установить nginx только на Ubuntu
    apt:
      name: nginx
    when: ansible_os_family == "Debian"

  - name: Установить nginx только на CentOS
    yum:
      name: nginx
    when: ansible_os_family == "RedHat"
  ```
- `failed_when` и `changed_when` — переопределить когда задача считается failed/changed
- `ignore_errors: true` — продолжить при ошибке (использовать осторожно)
- `block` / `rescue` / `always` — try/catch/finally для Ansible

#### Глава 9: Тестирование и отладка

**Цель:** читатель находит проблемы до деплоя, а не после.

- `--check` (dry-run): показывает что изменится без применения
  ```bash
  ansible-playbook site.yml --check
  ```
- `--diff`: показывает diff для файлов/шаблонов
  ```bash
  ansible-playbook site.yml --check --diff
  ```
- `-v`, `-vv`, `-vvv`: уровни verbose для отладки
- `debug` модуль — вывести переменную:
  ```yaml
  - debug:
      var: nginx_status
  - debug:
      msg: "Сервер: {{ inventory_hostname }}, IP: {{ ansible_default_ipv4.address }}"
  ```
- `assert` — проверить условие:
  ```yaml
  - assert:
      that:
        - ansible_memory_mb.real.total > 512
      fail_msg: "Недостаточно RAM: нужно минимум 512MB"
  ```
- Molecule: фреймворк для тестирования ролей
  - Запускает роль в Docker-контейнере
  - Проверяет результат
  - `molecule init role myapp` — scaffolding
  - `molecule test` — полный цикл: create → converge → verify → destroy
- Когда нужен Molecule: если роль используется на нескольких проектах или несколькими людьми

---

### Мини-проекты

#### Мини-проект 1: Terraform + Ansible — полный цикл

1. `terraform apply` — создать 2 VPS (dev + prod)
2. Сгенерировать inventory: `terraform output -json \| python3 gen_inventory.py > inventory/hosts.yml`
3. `ansible-playbook site.yml` — настроить оба сервера
4. Проверить: nginx работает на обоих, fail2ban запущен
5. `terraform destroy` — удалить оба
6. Снова `terraform apply` + `ansible-playbook` — полный стек за < 10 минут

> **Цель:** доказать что инфраструктура полностью воспроизводима из кода.
> Terraform создаёт → Ansible настраивает → автоматически, без ручного SSH.

#### Мини-проект 2: Production роль для Python-приложения

Создать роль `python-webapp` которая:
- Устанавливает Python, pip, gunicorn
- Создаёт пользователя для приложения
- Копирует код из Git
- Генерирует `.env` из template (секреты через Vault)
- Создаёт systemd-сервис из template
- Включает и запускает сервис
- Healthcheck endpoint `/health`

Проверка: запустить роль на dev и prod серверах с разными переменными (через group_vars). Оба сервера настроены одинаково.

#### Мини-проект 3: GitOps для Ansible

Настроить CI/CD пайплайн для Ansible:
- Playbook в git
- `--check` на каждый PR (dry-run, показывает что изменится)
- `ansible-playbook` на merge в `main`
- Vault password через CI secret
- Inventory генерируется из Terraform output

Проверка: изменить nginx.conf в git → PR → увидеть `--check` результат → merge → сервер обновился.

---

### Приложения

#### Приложение A: Шпаргалка команд

| Команда | Назначение |
|---------|-----------|
| `ansible all -m ping` | Проверить соединение |
| `ansible web -m setup` | Получить факты хоста |
| `ansible-playbook site.yml` | Запустить playbook |
| `ansible-playbook site.yml --check` | Dry-run |
| `ansible-playbook site.yml --diff` | Показать diff |
| `ansible-playbook site.yml -v` | Verbose |
| `ansible-vault encrypt file.yml` | Зашифровать файл |
| `ansible-vault edit file.yml` | Редактировать зашифрованный |
| `ansible-galaxy init rolename` | Создать структуру роли |
| `molecule test` | Тестировать роль |

#### Приложение B: Готовые конфиги
- `ansible.cfg` шаблон
- `inventory/hosts.yml` шаблон
- Playbook: базовая настройка Ubuntu-сервера
- Role структура с объяснениями
- Playbook: Python-приложение + systemd

#### Приложение C: Диагностика
- `UNREACHABLE` → проверить SSH-ключ, IP, открыт ли порт 22
- `FAILED: sudo: ...` → добавить `-b` или `become: true`
- Задача не идемпотентна → использовать правильный модуль вместо `shell`
- Template ошибка → проверить синтаксис Jinja2, имена переменных
- Vault: `ERROR! Decryption failed` → неправильный пароль vault

---

## Принципы написания

### 1. Идемпотентность — рефлекс, не знание

После КАЖДОГО playbook/task в книге — обязательное упражнение:
```
Запусти playbook дважды.
Первый раз: несколько changed.
Второй раз: только ok, ноль changed.
Если не так — playbook написан неправильно.
```

### 2. Модуль вместо shell — каждый раз

Когда есть соблазн написать `shell: apt install nginx`:
```yaml
# НЕПРАВИЛЬНО (не идемпотентно):
- shell: apt install nginx

# ПРАВИЛЬНО:
- apt:
    name: nginx
    state: present
```

### 3. Переменные ДО templates

Глава 3 (переменные) идёт ДО Главы 5 (templates).
Templates без переменных — просто копирование файлов.
Сначала читатель понимает переменные — потом использует в шаблонах.

### 4. Terraform → Ansible мост — явно

В Главе 1: показать как `terraform output -json` генерирует inventory.
В мини-проектах: полный цикл Terraform → Ansible.
Читатель видит: инфраструктура создаётся И настраивается автоматически.

### 5. ASCII-схемы для потока выполнения

При каждом playbook с несколькими ролями рисовать:
```
ansible-playbook site.yml
    │
    ├── role: common (все хосты)
    ├── role: nginx (группа web)
    └── role: myapp (группа web)
```

### 6. Всегда показывай вывод ansible-playbook

```
TASK [nginx : Установить nginx] *****
ok: [web1]           ← уже установлен
changed: [web2]      ← только что установлен

PLAY RECAP **************************
web1 : ok=5  changed=0  unreachable=0  failed=0
web2 : ok=5  changed=2  unreachable=0  failed=0
```

### 7. Никакой воды

- Без истории Ansible и Michael DeHaan
- Без сравнения с Chef, Puppet, Salt в деталях
- Без AWX/Tower (упомянуть что существует)
- Без глубокого погружения в Galaxy и коллекции

---

## Что НЕ надо делать

- ❌ Не использовать `shell` или `command` там где есть модуль
- ❌ Не пропускать проверку идемпотентности после примеров
- ❌ Не объяснять Kubernetes — это Модуль 10
- ❌ Не делать задачи без `name:` — всегда именовать
- ❌ Не хардкодить пароли — формируй привычку с первой главы
- ❌ Не показывать ansible без ansible.cfg — всегда с конфигом
- ❌ Не предполагать что читатель знает YAML глубоко — объяснить отступы и списки при первом use
- ❌ Не показывать переменные ПОСЛЕ templates — переменные нужны ДЛЯ templates
- ❌ Не игнорировать мост к Terraform — inventory генерируется автоматически

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-09.md      # Этот файл
└── ansible-devops/                      # Книга 9 (создать)
    ├── book.md
    ├── chapter-00.md                    # Зачем Ansible
    ├── chapter-01.md                    # Inventory + динамический из Terraform
    ├── chapter-02.md                    # Ad-hoc команды и модули
    ├── chapter-03.md                    # Переменные (ДО playbook)
    ├── chapter-04.md                    # Первый playbook
    ├── chapter-05.md                    # Templates (Jinja2)
    ├── chapter-06.md                    # Roles
    ├── chapter-07.md                    # Vault
    ├── chapter-08.md                    # Loops и conditions
    ├── chapter-09.md                    # Тестирование и отладка
    ├── appendix-a.md
    ├── appendix-b.md
    └── appendix-c.md
```

---

## Связь с другими модулями

**Что нужно из DevOps 1.0:**
- Модуль 1 (Linux): systemctl, apt, права файлов — Ansible управляет этим
- Модуль 2 (Nginx): конфиги Nginx — Ansible их копирует через template
- Модуль 5 (Инфраструктура): systemd-сервисы — Ansible их создаёт

**Что нужно из Модуля 8 (Terraform):**
- Terraform создаёт серверы → Ansible их настраивает
- `terraform output` → IP для Ansible inventory
- Идемпотентность: концепция уже знакома из Terraform

**Что даёт Модулю 10–11 (Kubernetes):**
- Концепция декларативности (что есть в Ansible) — та же модель в K8s manifests
- Опыт с YAML — K8s тоже YAML
- Роли и шаблоны — аналог Helm templates

---

*Эта инструкция — для ИИ-агента, который будет писать девятую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Предыдущая: AGENT-INSTRUCTIONS-module-08.md (Terraform)*
*Следующая: AGENT-INSTRUCTIONS-module-10.md (Kubernetes основы)*
