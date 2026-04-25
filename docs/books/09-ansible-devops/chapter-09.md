# Глава 9: Тестирование и отладка

> **Запомни:** Хороший playbook доказывает себя повторным запуском: второй запуск = `changed=0`.
>
> **Проект этой главы:** проверяем, что наш деплой идемпотентен и покрыт тестами роли.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 9.1 Финальная проверка идемпотентности playbook

Сначала примени весь проект:

```bash
ansible-playbook site.yml
```

Теперь запусти тот же playbook второй раз:

```bash
ansible-playbook site.yml
```

Ожидаемый результат второго запуска:

```text
PLAY RECAP ********************************
web1 : ok=8  changed=0  unreachable=0  failed=0
```

Вот это и есть правильно написанный playbook: он не делает лишней работы, если сервер уже находится в нужном состоянии.

Если на втором запуске `changed > 0`, ищи неидемпотентную задачу:

```bash
ansible-playbook site.yml -vv 2>&1 | grep "CHANGED"
```

Обычно виноваты:

- `shell` вместо модуля;
- шаблон, который каждый раз генерируется по-разному;
- task без `changed_when: false` для чистой проверки;
- неправильные права или владелец файла.

---

## 9.2 Molecule: полный пример

Molecule тестирует роль в изолированном окружении, обычно в Docker.

### Установить

```bash
pip install molecule molecule-plugins[docker]
```

### Создать scaffold теста для роли

```bash
cd roles/nginx
molecule init scenario
```

После `init` структура будет такой:

```text
molecule/
└── default/
    ├── molecule.yml
    ├── converge.yml
    └── verify.yml
```

- `molecule.yml` описывает тестовое окружение;
- `converge.yml` применяет роль;
- `verify.yml` проверяет результат.

Пример `verify.yml`:

```yaml
- name: Verify nginx роль
  hosts: all
  tasks:
    - name: nginx запущен
      command: systemctl is-active nginx
      register: result
      changed_when: false
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

```text
--> Scenario: default
--> Action: create
--> Action: converge
--> Action: verify
--> Action: destroy

PLAY RECAP
instance: ok=3 changed=0 failed=0
```

Когда нужен Molecule:

- роль используется в нескольких проектах;
- над ней работают несколько человек;
- хочется ловить регрессии до деплоя на реальный сервер.

---

## 9.3 `debug` — вывод переменных

Когда тест или деплой ведут себя странно, сначала проверь входные данные:

```yaml
- debug:
    var: nginx_status

- debug:
    msg: "Сервер: {{ inventory_hostname }}, IP: {{ ansible_default_ipv4.address }}"
```

`debug` помогает быстро увидеть, что именно Ansible знает о хосте и какую переменную реально использует.

---

## 9.4 `assert` — проверка условий

`assert` позволяет остановить playbook с понятной ошибкой до того, как начнётся деплой.

```yaml
- assert:
    that:
      - ansible_memory_mb.real.total > 512
      - app_port is defined
    fail_msg: "Сервер не готов: мало RAM или не задан app_port"
    success_msg: "Проверка пройдена, можно деплоить"
```

Это хороший способ зафиксировать минимальные требования роли или окружения.

---

## 9.5 Что делать если тест не прошёл

Если что-то падает, действуй по порядку:

1. Проверь, это ошибка подключения, конфигурации или логики роли.
2. Запусти playbook с `-vvv`, если не хватает деталей.
3. Посмотри последние логи сервиса на сервере или внутри Molecule-контейнера.
4. Проверь, что повторный запуск не даёт лишний `changed`.

Минимальный набор полезных команд:

```bash
ansible-playbook site.yml -vvv
ansible web -m command -a "systemctl is-active nginx"
ansible web -m shell -a "journalctl -u nginx -n 20 --no-pager" -b
molecule test
```

Отладка Ansible почти всегда сводится к трём вопросам:

- к правильному ли хосту подключились;
- те ли переменные подставились;
- тот ли сервис реально запущен после применения роли.

---

## 📝 Упражнения

### Упражнение 9.1: Идемпотентность
**Задача:**
1. Запусти `ansible-playbook site.yml`
2. Запусти его второй раз
3. Добейся `changed=0` на втором запуске
4. Если нет — найди проблемную задачу через `-vv`

### Упражнение 9.2: assert
**Задача:**
1. Добавь `assert` для проверки `RAM > 256MB`
2. Добавь `assert`, что `domain` определён
3. Запусти playbook — проверки сработали?

### Упражнение 9.3: Molecule
**Задача:**
1. Внутри `roles/nginx` создай `molecule`-сценарий
2. Добавь `verify.yml` с проверкой сервиса и HTTP-ответа
3. Запусти `molecule test`
4. Понял последовательность `create -> converge -> verify -> destroy`?

---

## 📋 Чеклист главы 9

- [ ] Я проверил идемпотентность playbook повторным запуском
- [ ] Я понимаю как использовать Molecule для ролей
- [ ] Я могу использовать `debug` для отладки переменных
- [ ] Я понимаю `assert` для проверок

**Всё отметил?** Книга 9 завершена!
