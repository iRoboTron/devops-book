# Глава 0: Зачем Ansible и как он работает

> **Запомни:** Ansible не хранит состояние. Каждый раз читает playbook и сравнивает с реальностью. Совпадает — ничего не делает.

---

## 0.1 Проблема shell-скриптов

```bash
#!/bin/bash
# setup.sh — настроить Nginx

if [ ! -f /etc/nginx/nginx.conf ]; then
    cp nginx.conf /etc/nginx/nginx.conf
fi

if ! systemctl is-active nginx > /dev/null; then
    systemctl start nginx
fi

systemctl enable nginx
```

**Проблемы:**
- 10 строк вместо 3 в Ansible
- Не идемпотентно (запустишь на Debian — сломается)
- Нет параллелизма (5 серверов = 5 запусков)
- Обработка ошибок = `if/else` хаос

### Ansible

```yaml
- name: Настроить Nginx
  hosts: web
  become: true
  tasks:
    - name: Установить nginx
      apt:
        name: nginx
        state: present

    - name: Включить и запустить
      service:
        name: nginx
        state: started
        enabled: yes
```

3 задачи. Параллельно на всех серверах. Идемпотентно.

---

## 0.2 Как Ansible работает

```
Твой ноутбук                  Сервер
ansible-playbook ──SSH──→  запустить task
setup.yml                   вернуть результат
```

- **Agentless** — не нужно ставить агент на серверы
- Только SSH + Python
- Push-модель: ты отправляешь задачи на серверы

---

## 0.3 Ansible vs Terraform

| Terraform | Ansible |
|-----------|---------|
| Создаёт инфраструктуру | Настраивает конфигурацию |
| Серверы, сети, DNS | Пакеты, файлы, сервисы |
| `terraform apply` | `ansible-playbook` |

```
Полный workflow:
terraform apply  →  серверы созданы
     │
     ▼
ansible-playbook site.yml  →  серверы настроены
```

---

## 0.4 Установка

```bash
# Вариант 1: pip (рекомендуется)
pip3 install ansible

# Вариант 2: apt
sudo apt install -y ansible
```

### Проверить

```bash
ansible --version
ansible [core 2.16.0]
```

---

## 0.5 Структура проекта

```
ansible/
├── ansible.cfg            # конфигурация по умолчанию
├── inventory/
│   └── hosts.yml          # список серверов
├── group_vars/
│   └── all.yml            # переменные для всех
├── roles/
│   └── nginx/             # роль nginx
├── site.yml               # главный playbook
└── files/
    └── nginx.conf         # статические файлы
```

---

## 📋 Чеклист главы 0

- [ ] Я понимаю почему shell-скрипты плохи для конфигурации
- [ ] Я понимаю как Ansible работает (SSH + Python)
- [ ] Я понимаю разницу Terraform (создаёт) vs Ansible (настраивает)
- [ ] Ansible установлен (`ansible --version`)

**Всё отметил?** Переходи к Главе 1 — Inventory.
