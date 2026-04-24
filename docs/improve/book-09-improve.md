# Инструкция агенту: улучшение книги 09 «Ansible для DevOps»

## Контекст

Книга находится в директории:
```
/home/adelfos/Documents/lessons/dev-ops/docs/books/09-ansible-devops/
```

Файлы: `chapter-01.md` … `chapter-09.md`, `appendix-a.md`

Эталон качества для этой части курса — книга 08 (Terraform): 2930 строк, ~270 строк/глава, реальный вывод команд, 4–5 упражнений на главу, сквозной проект. Книга 09 сейчас: 1465 строк, ~130 строк/глава, 2–3 упражнения. Нужно привести её к тому же уровню.

**Главная структурная проблема:** нет сквозного проекта. В книге 08 Terraform строит один сервер от начала до конца — читатель всегда знает куда идёт. В Ansible главы существуют изолированно. Добавь сквозной проект: **деплой Flask-приложения за Nginx** — каждая глава добавляет следующий слой.

---

## Что НЕ трогать

- Нумерацию и названия разделов
- Чеклисты в конце глав
- Блоки «Упражнения»
- Общий стиль (краткие блоки, таблицы, `> **Запомни:**`)

---

## Сквозной проект — добавить в каждую главу

В начало каждой главы (после `> **Запомни:**`) добавить врезку:

```
> **Проект этой главы:** [что именно строим в этой главе]
> К концу книги: Flask-приложение за Nginx, деплой одной командой.
```

| Глава | Что строим в этой главе |
|-------|------------------------|
| 1 | Inventory: описываем наш сервер |
| 2 | Ad-hoc: проверяем что сервер жив и доступен |
| 3 | Переменные: domain, app_port, deploy_user |
| 4 | Playbook: устанавливаем Nginx, создаём пользователя deploy |
| 5 | Template: генерируем nginx.conf из переменных |
| 6 | Roles: выносим nginx и app в отдельные роли |
| 7 | Vault: прячем DB_PASSWORD и SECRET_KEY |
| 8 | Loops: устанавливаем все пакеты разом, создаём всех пользователей |
| 9 | Тестирование: проверяем что deploy идемпотентен |

---

## Задачи по каждой главе

---

### Глава 1 (`chapter-01.md`) — Inventory и ansible.cfg

**Проблема 1:** Раздел 1.3 «Динамический inventory из Terraform» — слишком сложно для главы 1. Читатель ещё не понял статический inventory, а его уже учат Python-генераторам. Перенести этот раздел в appendix или убрать из главы 1.

**Проблема 2:** Нет примера что реально происходит при `ansible all -m ping` — что значит `"ping": "pong"` и что значит если оно не работает.

Добавить в раздел 1.2 что делать если ping не прошёл:

```
web1 | UNREACHABLE! => {
    "changed": false,
    "msg": "Failed to connect to the host via ssh: ssh: connect to host 1.2.3.4 port 22: Connection refused",
    "unreachable": true
}
```

Это значит: либо сервер недоступен, либо неверный IP в inventory, либо не тот SSH-ключ. Проверить:

```bash
ssh deploy@1.2.3.4 -i ~/.ssh/id_ed25519
```

**Проблема 3:** Нет объяснения зачем `host_key_checking = False` в `ansible.cfg` — это важно для новых серверов.

Добавить объяснение: при первом подключении к новому серверу SSH спрашивает «добавить в known_hosts?». В автоматизации это ломает работу. `host_key_checking = False` отключает вопрос. В production для известных серверов лучше держать `True`.

---

### Глава 2 (`chapter-02.md`) — Ad-hoc команды

**Проблема:** Упражнение 2.2 учит устанавливать nginx через `shell: apt install -y nginx` — это плохой пример который потом нужно «исправить». Показывать плохие практики без немедленного исправления путает читателя.

Переписать упражнение 2.2: вместо shell-примера — сравнение `changed: true` при первом запуске и `changed: false` при повторном через `apt` модуль:

```bash
# Первый запуск
ansible web -m apt -a "name=nginx state=present" -b
# web1 | CHANGED => {"changed": true}

# Второй запуск
ansible web -m apt -a "name=nginx state=present" -b
# web1 | SUCCESS => {"changed": false}  ← идемпотентность
```

**Добавить** раздел **2.5 «Полезные однострочники для диагностики»:**

```bash
# Свободное место
ansible web -m command -a "df -h /"

# Нагрузка
ansible web -m command -a "uptime"

# Статус сервиса
ansible web -m command -a "systemctl is-active nginx"

# Последние логи
ansible web -m shell -a "journalctl -u nginx -n 20 --no-pager"

# Открытые порты
ansible web -m command -a "ss -tulpn"
```

Это то, что реально нужно при деплое — убедиться что сервер жив до запуска playbook.

---

### Глава 3 (`chapter-03.md`) — Переменные

**Проблема:** Иерархия переменных показана в виде списка, но нет примера конфликта — что происходит когда одна переменная определена в двух местах.

**Добавить** раздел **3.7 «Что побеждает при конфликте»:**

```yaml
# group_vars/web.yml
http_port: 80

# host_vars/web1.yml
http_port: 8080   # ← переопределяет для конкретного хоста
```

Проверить что победило:

```bash
ansible web -m debug -a "msg={{ http_port }}"
# web1 | SUCCESS => {"msg": "8080"}  ← host_vars победил
# web2 | SUCCESS => {"msg": "80"}    ← group_vars для остальных
```

**Добавить** раздел **3.8 «extra-vars для разового переопределения»:**

```bash
# Запустить с другим доменом без правки файлов
ansible-playbook site.yml -e "domain=staging.myapp.ru app_port=9000"
```

Это важно для CI/CD — один playbook, разные параметры для разных окружений.

---

### Глава 4 (`chapter-04.md`) — Первый playbook

**Глава хорошая** — реальный вывод, идемпотентность, `--check --diff`. Нужно только добавить пример вывода `--diff`:

**Добавить** в раздел 4.4 пример что показывает `--diff`:

```bash
ansible-playbook site.yml --check --diff
```

```
TASK [Скопировать конфиг] ****
--- before: /etc/nginx/nginx.conf
+++ after: /home/user/.ansible/tmp/nginx.conf
@@ -1,5 +1,5 @@
 server {
-    listen 80;
+    listen 8080;
     server_name localhost;
 }
```

Объяснить: красное (`-`) = что сейчас на сервере, зелёное (`+`) = что будет после apply. Без `--check` это уже применится.

**Добавить** раздел **4.6 «Запустить только часть playbook»:**

```bash
# Запустить только задачи с тегом nginx
ansible-playbook site.yml --tags nginx

# Пропустить задачи с тегом slow
ansible-playbook site.yml --skip-tags slow

# Только для одного хоста
ansible-playbook site.yml --limit web1
```

Как добавить тег к задаче:

```yaml
- name: Установить nginx
  apt:
    name: nginx
  tags: [nginx, packages]
```

---

### Глава 5 (`chapter-05.md`) — Templates

**Проблема:** Нет примера что реально генерируется из шаблона. Читатель пишет `.j2` файл но не видит результат на сервере.

**Добавить** раздел **5.6 «Проверить что сгенерировалось»:**

```bash
# Посмотреть результат на сервере
ansible web -m command -a "cat /etc/nginx/sites-enabled/myapp.conf"
```

Ожидаемый вывод (после подстановки переменных):

```
server {
    listen 80;
    server_name myapp.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

И как увидеть diff перед применением:

```bash
ansible-playbook site.yml --check --diff
```

```
--- before: /etc/nginx/sites-enabled/myapp.conf
+++ after: template rendered
@@ -2,7 +2,7 @@
     listen 80;
-    server_name localhost;
+    server_name myapp.ru;
```

**Добавить** раздел **5.7 «Отладка шаблона локально»:**

```bash
# Установить jinja2
pip install jinja2-cli

# Проверить шаблон локально с переменными
jinja2 templates/nginx.conf.j2 \
  --format=json \
  -D domain=myapp.ru \
  -D app_port=8000 \
  -D http_port=80
```

Это позволяет проверить логику шаблона без подключения к серверу.

---

### Глава 6 (`chapter-06.md`) — Roles

**Проблема 1:** Роль показана как структура папок, но нет примера реального деплоя через роли — что происходит при запуске, как выглядит вывод.

**Добавить** в раздел 6.3 реальный вывод запуска с ролями:

```bash
ansible-playbook site.yml
```

```
PLAY [web] **********************************************

ROLE [common] *******************************************
TASK [common : Обновить apt кэш] ****
ok: [web1]
TASK [common : Установить базовые пакеты] ***
changed: [web1]

ROLE [nginx] ********************************************
TASK [nginx : Установить nginx] ****
changed: [web1]
TASK [nginx : Скопировать конфиг] ***
changed: [web1]
RUNNING HANDLER [nginx : reload nginx] ****
changed: [web1]

ROLE [myapp] ********************************************
TASK [myapp : Создать пользователя deploy] ***
changed: [web1]
TASK [myapp : Скопировать приложение] ***
changed: [web1]

PLAY RECAP **********************************************
web1 : ok=8  changed=6  unreachable=0  failed=0
```

**Проблема 2:** Нет раздела об использовании готовых ролей из Ansible Galaxy.

**Добавить** раздел **6.6 «Ansible Galaxy — готовые роли»:**

```bash
# Найти роль
ansible-galaxy search nginx

# Установить роль
ansible-galaxy install geerlingguy.nginx

# Список установленных
ansible-galaxy list
```

Роль устанавливается в `~/.ansible/roles/` или в `roles/` проекта.

Использовать в playbook:

```yaml
- hosts: web
  become: true
  roles:
    - geerlingguy.nginx   # готовая роль
    - myapp               # своя роль
```

Когда использовать чужую роль: сложный продукт (PostgreSQL, Redis, Docker) с тонкой настройкой — лучше взять проверенную роль чем писать с нуля.

---

### Глава 7 (`chapter-07.md`) — Vault

**Проблема 1:** Показан только `encrypt` целого файла. На практике чаще нужно зашифровать одно значение прямо в YAML.

**Добавить** раздел **7.5 «Зашифровать одно значение (vault_string)»:**

```bash
ansible-vault encrypt_string 'SuperSecret123' --name 'db_password'
```

Вывод:

```yaml
db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63386130663561616662386639613830...
```

Скопировать этот блок прямо в `group_vars/all.yml` рядом с обычными переменными:

```yaml
# group_vars/all.yml
app_port: 8000
domain: myapp.ru
db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63386130663561616662386639613830...
```

Это удобнее чем шифровать весь файл — обычные переменные читаются, секреты зашифрованы.

**Проблема 2:** Нет примера как выглядит зашифрованный файл — читатель не понимает что он коммитит в git.

**Добавить** в раздел 7.2 пример содержимого зашифрованного файла:

```
$ANSIBLE_VAULT;1.1;AES256
38313534363534386162623866613739363564653535303337623231333831656138356439626437
6165333631306561623664373362393262313464393135620a646561366465396234386439383662
...
```

Пояснить: это безопасно коммитить — без vault-пароля прочитать невозможно. Но сам пароль (`.vault_pass`) — никогда в git.

---

### Глава 8 (`chapter-08.md`) — Loops и conditions

**Проблема:** Глава 95 строк — слишком короткая. `block/rescue/always` показан как пример кода без объяснения когда использовать в реальном деплое.

**Добавить** раздел **8.5 «until — ждать пока условие выполнится»:**

```yaml
- name: Подождать пока приложение запустится
  uri:
    url: http://localhost:8000/health
    status_code: 200
  register: result
  until: result.status == 200
  retries: 10
  delay: 5
```

Это реальная задача при деплое: после запуска сервиса нужно подождать пока он поднимется. `retries: 10` и `delay: 5` = максимум 50 секунд ожидания.

**Добавить** раздел **8.6 «Реальный пример block/rescue при деплое»:**

```yaml
- block:
    - name: Остановить приложение
      systemd:
        name: myapp
        state: stopped

    - name: Скопировать новую версию
      copy:
        src: dist/
        dest: /opt/myapp/

    - name: Запустить приложение
      systemd:
        name: myapp
        state: started

    - name: Проверить что запустилось
      uri:
        url: http://localhost:8000/health
        status_code: 200

  rescue:
    - name: ОТКАТ — запустить старую версию
      systemd:
        name: myapp
        state: started

    - name: Уведомить об ошибке
      debug:
        msg: "Деплой упал! Выполнен откат."

  always:
    - name: Записать результат деплоя в лог
      lineinfile:
        path: /var/log/deploy.log
        line: "{{ ansible_date_time.iso8601 }} deploy finished"
```

Это паттерн deploy-with-rollback — самое частое применение `block/rescue`.

**Добавить** упражнение 8.3 с использованием `until`:

```
### Упражнение 8.3: until
Задача:
1. Запусти сервис через systemd
2. Добавь задачу с until: жди пока порт откроется (uri или wait_for)
3. retries: 5, delay: 3
4. Что произойдёт если сервис не поднимется за 15 секунд?
```

---

### Глава 9 (`chapter-09.md`) — Тестирование

**Проблема:** Molecule упомянут в 3 строки без вывода и без объяснения что происходит. `--check` и `--diff` уже были в главе 4 — дублирование.

**Переписать разделы 9.1 и 9.2** — убрать дублирование с главой 4, заменить на новое содержание:

**9.1 — Финальная проверка идемпотентности playbook:**

```bash
# Применить всё с нуля
ansible-playbook site.yml

# Применить снова — должно быть 0 changed
ansible-playbook site.yml
```

Ожидаемый результат второго запуска:

```
PLAY RECAP **********************
web1 : ok=8  changed=0  unreachable=0  failed=0
                        ↑ это и есть правильно написанный playbook
```

Если `changed > 0` на втором запуске — найти неидемпотентную задачу:

```bash
# Запустить с подробным выводом чтобы найти проблему
ansible-playbook site.yml -vv 2>&1 | grep "CHANGED"
```

**9.2 — Molecule: полный пример:**

```bash
# Установить
pip install molecule molecule-plugins[docker]

# Создать scaffold теста для роли
cd roles/nginx
molecule init scenario

# Структура после init
molecule/
└── default/
    ├── molecule.yml      # конфигурация (Docker образ)
    ├── converge.yml      # применить роль
    └── verify.yml        # проверки после применения
```

Пример `verify.yml`:

```yaml
- name: Verify nginx роль
  hosts: all
  tasks:
    - name: nginx запущен
      command: systemctl is-active nginx
      register: result
      failed_when: result.stdout != "active"

    - name: Порт 80 открыт
      wait_for:
        port: 80
        timeout: 5

    - name: nginx отвечает
      uri:
        url: http://localhost
        status_code: 200
```

Запустить тест:

```bash
molecule test
```

Что происходит:

```
--> Scenario: default
--> Action: create        # поднять Docker контейнер
--> Action: converge      # применить роль
--> Action: verify        # запустить verify.yml
--> Action: destroy       # удалить контейнер

PLAY RECAP
instance: ok=3 changed=0 failed=0
```

Когда нужен Molecule: роль используется в нескольких проектах или несколькими людьми — тогда автоматический тест обязателен.

---

### Appendix A (`appendix-a.md`)

Проверить что appendix содержит шпаргалку команд. Если нет — добавить:

```bash
# Проверка подключения
ansible all -m ping

# Запустить playbook
ansible-playbook site.yml

# Dry-run с diff
ansible-playbook site.yml --check --diff

# Только для одного хоста
ansible-playbook site.yml --limit web1

# С тегом
ansible-playbook site.yml --tags deploy

# С vault-паролем
ansible-playbook site.yml --ask-vault-pass

# Зашифровать значение
ansible-vault encrypt_string 'value' --name 'var_name'

# Посмотреть факты хоста
ansible web -m setup

# Установить роль из Galaxy
ansible-galaxy install geerlingguy.nginx
```

---

## Общий объём

Цель: 2200–2500 строк (сейчас 1465). Каждая глава должна вырасти до 180–220 строк.

## Приоритет

1. Глава 9 (Molecule) — переписать полностью
2. Глава 8 (until, реальный block/rescue) — добавить практику
3. Глава 6 (вывод ролей, Galaxy) — добавить живые примеры
4. Глава 4 (--diff вывод) — добавить пример
5. Сквозной проект — добавить врезки во все главы

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-09-improve.md`*
*Проект: dev-ops / книга 09*
