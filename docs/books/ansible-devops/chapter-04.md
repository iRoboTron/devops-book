# Глава 4: Первый playbook

> **Запомни:** Playbook = описание желаемого состояния. Запусти дважды — результат одинаковый (идемпотентность).

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

    - name: Скопировать конфиг
      copy:
        src: files/nginx.conf
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: '0644'
      notify: reload nginx

    - name: Запустить nginx
      service:
        name: nginx
        state: started
        enabled: yes

  handlers:
    - name: reload nginx
      service:
        name: nginx
        state: reloaded
```

### Разбор

| Поле | Значение |
|------|----------|
| `name` | Описание (всегда пиши!) |
| `hosts` | На каких серверах |
| `become: true` | sudo |
| `tasks` | Список задач |
| `notify` | Запустить handler при изменении |
| `handlers` | Задачи которые запускаются по notify |

---

## 4.2 Запустить

```bash
ansible-playbook site.yml
```

```
PLAY [Настроить веб-серver] *************

TASK [Установить nginx] ****************
ok: [web1]
changed: [web2]

TASK [Скопировать конфиг] **************
changed: [web1]
changed: [web2]

RUNNING HANDLER [reload nginx] *********
changed: [web1]
changed: [web2]

PLAY RECAP *****************************
web1 : ok=3  changed=2  unreachable=0  failed=0
web2 : ok=3  changed=2  unreachable=0  failed=0
```

---

## 4.3 Идемпотентность — ОБЯЗАТЕЛЬНАЯ проверка

```bash
ansible-playbook site.yml
```

Второй запуск:

```
TASK [Установить nginx] ****************
ok: [web1]       ← уже установлен
ok: [web2]       ← уже установлен

TASK [Скопировать конфиг] **************
ok: [web1]       ← конфиг не изменился
ok: [web2]

PLAY RECAP *****************************
web1 : ok=2  changed=0  ← НОЛЬ изменений
web2 : ok=2  changed=0
```

**0 changed** = playbook написан правильно.

> **Правило:** Запусти playbook дважды.
> Второй раз = ноль changed.
> Если changed > 0 — playbook неправильный.

---

## 4.4 Dry-run

```bash
ansible-playbook site.yml --check
```

Покажет что изменится БЕЗ применения.

```bash
ansible-playbook site.yml --check --diff
```

Покажет diff файлов.

---

## 4.5 Verbose

```bash
ansible-playbook site.yml -v       # коротко
ansible-playbook site.yml -vv      # подробнее
ansible-playbook site.yml -vvv     # очень подробно
```

`-vvv` = для отладки.

---

## 📝 Упражнения

### Упражнение 4.1: Первый playbook
**Задача:**
1. Создай `site.yml` для установки nginx
2. `ansible-playbook site.yml` — прошло?
3. `curl http://localhost` — nginx работает?

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
3. Без `--check` — применилось?

---

## 📋 Чеклист главы 4

- [ ] Я могу написать playbook с tasks
- [ ] Я использую `name:` для каждой задачи
- [ ] Я понимаю handlers и notify
- [ ] Я проверил идемпотентность (второй запуск = 0 changed)
- [ ] Я могу использовать `--check` и `--diff`
- [ ] Я могу использовать `-vvv` для отладки

**Всё отметил?** Переходи к Главе 5 — Templates.
