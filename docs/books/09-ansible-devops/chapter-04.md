# Глава 4: Первый playbook

> **Запомни:** Playbook = описание желаемого состояния. Запусти дважды — результат одинаковый (идемпотентность).
>
> **Проект этой главы:** пишем первый `site.yml`: ставим Nginx и создаём пользователя `deploy`.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 4.1 Структура

```yaml
---
- name: Настроить веб-сервер
  hosts: web
  become: true

  tasks:
    - name: Установить nginx
      apt:
        name: nginx
        state: present
        update_cache: yes
      tags: [nginx, packages]

    - name: Создать пользователя deploy
      user:
        name: "{{ deploy_user }}"
        shell: /bin/bash
        create_home: yes
      tags: [app, users]

    - name: Создать директорию приложения
      file:
        path: "{{ app_root }}"
        state: directory
        owner: "{{ deploy_user }}"
        group: "{{ deploy_user }}"
        mode: '0755'
      tags: [app]

    - name: Скопировать базовый конфиг
      copy:
        src: files/nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: '0644'
      notify: reload nginx
      tags: [nginx]

    - name: Запустить nginx
      service:
        name: nginx
        state: started
        enabled: yes
      tags: [nginx]

  handlers:
    - name: reload nginx
      service:
        name: nginx
        state: reloaded
```

### Разбор

| Поле | Значение |
|------|----------|
| `name` | Описание задачи или play |
| `hosts` | На каких серверах запускать |
| `become: true` | Выполнять задачи через sudo |
| `tasks` | Основные действия |
| `notify` | Сообщить handler при изменении |
| `handlers` | Действия "после изменения" |
| `tags` | Запускать только часть playbook |

Здесь мы уже строим основу проекта:

- ставим Nginx;
- создаём пользователя `deploy`;
- готовим директорию для Flask-приложения;
- подготавливаем перезагрузку Nginx через handler.

---

## 4.2 Запустить

```bash
ansible-playbook site.yml
```

```text
PLAY [Настроить веб-сервер] ************************

TASK [Установить nginx] ****************************
changed: [web1]

TASK [Создать пользователя deploy] *****************
changed: [web1]

TASK [Создать директорию приложения] ***************
changed: [web1]

TASK [Скопировать базовый конфиг] ******************
changed: [web1]

TASK [Запустить nginx] *****************************
changed: [web1]

RUNNING HANDLER [reload nginx] *********************
changed: [web1]

PLAY RECAP *****************************************
web1 : ok=6  changed=6  unreachable=0  failed=0
```

Нормально, что первый запуск меняет почти всё: пакет ставится впервые, пользователь создаётся впервые, конфиг копируется впервые.

---

## 4.3 Идемпотентность — ОБЯЗАТЕЛЬНАЯ проверка

```bash
ansible-playbook site.yml
```

Второй запуск:

```text
TASK [Установить nginx] ****************************
ok: [web1]       ← уже установлен

TASK [Создать пользователя deploy] *****************
ok: [web1]       ← пользователь уже есть

TASK [Создать директорию приложения] ***************
ok: [web1]       ← директория уже создана

TASK [Скопировать базовый конфиг] ******************
ok: [web1]       ← файл не изменился

PLAY RECAP *****************************************
web1 : ok=5  changed=0  unreachable=0  failed=0
```

**0 changed** = playbook написан правильно.

> **Правило:** Запусти playbook дважды.
> Второй раз = ноль changed.
> Если `changed > 0` — ищи неидемпотентную задачу.

---

## 4.4 Dry-run

```bash
ansible-playbook site.yml --check
```

Покажет, что изменится БЕЗ применения.

```bash
ansible-playbook site.yml --check --diff
```

Покажет diff файлов до применения.

Пример вывода:

```text
TASK [Скопировать конфиг] **************************
--- before: /etc/nginx/nginx.conf
+++ after: /home/user/.ansible/tmp/nginx.conf
@@ -1,5 +1,5 @@
 server {
-    listen 80;
+    listen 8080;
     server_name localhost;
 }
```

Красное `-` показывает, что сейчас на сервере. Зелёное `+` показывает, что будет после применения. Если убрать `--check`, изменения уже реально попадут на сервер.

---

## 4.5 Verbose

```bash
ansible-playbook site.yml -v       # коротко
ansible-playbook site.yml -vv      # подробнее
ansible-playbook site.yml -vvv     # очень подробно
```

`-vvv` полезен для отладки SSH, переменных и проблемных задач.

---

## 4.6 Запустить только часть playbook

Иногда не нужно крутить весь playbook целиком.

```bash
# Только задачи с тегом nginx
ansible-playbook site.yml --tags nginx

# Пропустить медленные задачи
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

Это особенно полезно, когда playbook вырос: можно быстро обновить только конфиг Nginx или отдельно прогнать задачи приложения.

---

## 📝 Упражнения

### Упражнение 4.1: Первый playbook
**Задача:**
1. Создай `site.yml` для установки nginx и создания пользователя `deploy`
2. `ansible-playbook site.yml` — прошло?
3. `ansible web -m command -a "systemctl is-active nginx"` — сервис активен?

### Упражнение 4.2: Идемпотентность
**Задача:**
1. Запусти `ansible-playbook site.yml` ещё раз
2. `changed=0` у всех?
3. Если нет — ищи неидемпотентную задачу

### Упражнение 4.3: Handler
**Задача:**
1. Измени `files/nginx.conf`
2. Запусти playbook — handler `reload nginx` сработал?
3. Без изменений — handler НЕ сработал?

### Упражнение 4.4: --check
**Задача:**
1. `ansible-playbook site.yml --check --diff`
2. Что изменилось бы?
3. Запусти `ansible-playbook site.yml --tags nginx`

---

## 📋 Чеклист главы 4

- [ ] Я могу написать playbook с tasks
- [ ] Я использую `name:` для каждой задачи
- [ ] Я понимаю handlers и notify
- [ ] Я проверил идемпотентность (второй запуск = 0 changed)
- [ ] Я могу использовать `--check` и `--diff`
- [ ] Я могу использовать `-vvv` для отладки

**Всё отметил?** Переходи к Главе 5 — Templates.
