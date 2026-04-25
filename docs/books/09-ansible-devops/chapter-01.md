# Глава 1: Inventory и ansible.cfg

> **Запомни:** Inventory = список серверов. Ansible должен знать куда подключаться.
>
> **Проект этой главы:** описываем наш сервер в inventory и подготавливаем первое подключение.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 1.1 Inventory в YAML

В этой книге будет один основной сервер: `web1`. Именно на него дальше поставим Nginx, создадим пользователя `deploy`, развернём Flask-приложение и проверим идемпотентность playbook.

Создай `inventory/hosts.yml`:

```yaml
all:
  children:
    web:
      hosts:
        web1:
          ansible_host: 1.2.3.4
  vars:
    ansible_user: deploy
    ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

### Разбор

| Ключ | Что значит |
|------|------------|
| `all` | Все хосты inventory |
| `children` | Группы хостов |
| `web` | Группа веб-серверов |
| `web1` | Логическое имя хоста в Ansible |
| `ansible_host` | Реальный IP или DNS хоста |
| `ansible_user` | Пользователь для SSH |
| `ansible_ssh_private_key_file` | SSH-ключ для подключения |

Если позже появится второй сервер, просто добавь его в ту же группу:

```yaml
web:
  hosts:
    web1:
      ansible_host: 1.2.3.4
    web2:
      ansible_host: 5.6.7.8
```

> **Запомни:** `web1` в inventory и `1.2.3.4` в `ansible_host` — не одно и то же.
> `web1` удобно использовать в playbook и логах, IP можно менять без переписывания задач.

---

## 1.2 ansible.cfg

Создай `ansible.cfg` в корне проекта:

```ini
[defaults]
inventory = inventory/hosts.yml
remote_user = deploy
private_key_file = ~/.ssh/id_ed25519
host_key_checking = False
retry_files_enabled = False

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False
```

### Что делает этот файл

| Параметр | Зачем нужен |
|----------|-------------|
| `inventory` | Где лежит inventory |
| `remote_user` | Пользователь по умолчанию |
| `private_key_file` | Какой SSH-ключ использовать |
| `host_key_checking = False` | Не спрашивать подтверждение нового SSH-host key |
| `retry_files_enabled = False` | Не создавать лишние `.retry` файлы |
| `become = True` | По умолчанию выполнять задачи через sudo |

### Почему `host_key_checking = False`

При первом подключении к новому серверу SSH обычно спрашивает:

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Для ручной работы это нормально. Для автоматизации это ломает запуск: Ansible ждёт ответ и playbook останавливается. Поэтому на новых серверах в учебном проекте удобно отключить этот вопрос.

В production для известных серверов и контролируемого `known_hosts` лучше держать `host_key_checking = True`.

### Первая проверка

```bash
ansible all -m ping
```

Успешный результат:

```text
web1 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

`"ping": "pong"` не означает ICMP ping. Это значит: Ansible смог зайти по SSH, запустить Python на сервере и получить нормальный ответ от модуля `ping`.

### Если ping не прошёл

Пример ошибки:

```text
web1 | UNREACHABLE! => {
    "changed": false,
    "msg": "Failed to connect to the host via ssh: ssh: connect to host 1.2.3.4 port 22: Connection refused",
    "unreachable": true
}
```

Это значит: либо сервер недоступен, либо неверный IP в inventory, либо не тот SSH-ключ.

Проверь подключение вручную:

```bash
ssh deploy@1.2.3.4 -i ~/.ssh/id_ed25519
```

Если SSH не работает руками, Ansible тоже не заработает.

Проверь по шагам:

1. Сервер вообще запущен и доступен по сети.
2. В `ansible_host` указан правильный IP.
3. Пользователь `deploy` существует на сервере.
4. Используется правильный приватный ключ.
5. На сервере открыт порт `22`.

---

## 1.3 Динамический inventory из Terraform

В главе 1 не усложняй процесс. Сначала добейся стабильной работы со статическим `inventory/hosts.yml`.

Когда серверы уже создаёт Terraform, inventory можно генерировать автоматически из его output. Это удобно, потому что IP не придётся копировать руками после каждого `terraform apply`.

Логика простая:

```text
Terraform создал сервер
        ↓
terraform output показал IP
        ↓
inventory получил новый IP
        ↓
Ansible подключился к правильному серверу
```

Минимальная идея выглядит так:

```bash
terraform output server_ip
# 1.2.3.4
```

После этого в inventory должен оказаться тот же адрес:

```yaml
all:
  children:
    web:
      hosts:
        web1:
          ansible_host: 1.2.3.4
```

Подробную автоматическую генерацию inventory лучше добавлять позже, когда уже понятны базовые вещи: группы, `ansible.cfg`, SSH и обычный `ansible all -m ping`.

> **Мост к Модулю 8:** Terraform создаёт сервер, Ansible его настраивает.
> Но сначала научись уверенно работать со статическим inventory.

---

## 📝 Упражнения

### Упражнение 1.1: Создать inventory
**Задача:**
1. Создай `inventory/hosts.yml` с сервером `web1`
2. Создай `ansible.cfg`
3. Запусти `ansible all -m ping`
4. Получил `pong`?

### Упражнение 1.2: Проверить SSH до Ansible
**Задача:**
1. Подключись вручную: `ssh deploy@1.2.3.4 -i ~/.ssh/id_ed25519`
2. Если SSH не работает — исправь IP, ключ или пользователя
3. Повтори `ansible all -m ping`
4. Добейся ответа `SUCCESS`

---

## 📋 Чеклист главы 1

- [ ] Я создал inventory с группами
- [ ] Я создал ansible.cfg
- [ ] `ansible all -m ping` работает
- [ ] Я понимаю разницу между статическим и динамическим inventory

**Всё отметил?** Переходи к Главе 2 — Ad-hoc команды.
