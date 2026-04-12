# Глава 1: Inventory и ansible.cfg

> **Запомни:** Inventory = список серверов. Ansible должен знать куда подключаться.

---

## 1.1 Inventory в YAML

Создай `inventory/hosts.yml`:

```yaml
all:
  children:
    web:
      hosts:
        web1:
          ansible_host: 1.2.3.4
        web2:
          ansible_host: 5.6.7.8
    db:
      hosts:
        db1:
          ansible_host: 9.10.11.12
  vars:
    ansible_user: deploy
    ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

### Группы

| Группа | Серверы |
|--------|---------|
| `all` | Все серверы |
| `web` | web1, web2 |
| `db` | db1 |

---

## 1.2 ansible.cfg

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

```bash
ansible all -m ping
```

```
web1 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
web2 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

---

## 1.3 Динамический inventory из Terraform

Terraform создал серверы → Ansible получил их IP.

### Terraform output

```hcl
output "server_ips" {
  value = {
    for s in hcloud_server.main : s.name => s.ipv4_address
  }
}
```

### Генератор inventory

```python
#!/usr/bin/env python3
# gen_inventory.py
import json, sys

tf = json.load(sys.stdin)

inventory = {
    "all": {
        "children": {
            "web": {"hosts": {}},
        },
        "vars": {
            "ansible_user": "deploy",
            "ansible_ssh_private_key_file": "~/.ssh/id_ed25519"
        }
    }
}

for name, ip in tf["server_ips"]["value"].items():
    inventory["all"]["children"]["web"]["hosts"][name] = {
        "ansible_host": ip
    }

print(json.dumps(inventory, indent=2))
```

### Использовать

```bash
terraform output -json | python3 gen_inventory.py > inventory/hosts.yml
ansible all -m ping
```

> **Мост к Модулю 8:** Terraform создал → Ansible настроил. Никакого ручного копирования IP.

---

## 📝 Упражнения

### Упражнение 1.1: Создать inventory
**Задача:**
1. Создай `inventory/hosts.yml` с 2 серверами
2. Создай `ansible.cfg`
3. `ansible all -m ping` — оба ответили?

### Упражнение 1.2: Динамический inventory
**Задача:**
1. Запусти Terraform (Модуль 8) — получи серверы
2. `terraform output -json \| python3 gen_inventory.py > inventory/hosts.yml`
3. `ansible all -m ping` — работает?

---

## 📋 Чеклист главы 1

- [ ] Я создал inventory с группами
- [ ] Я создал ansible.cfg
- [ ] `ansible all -m ping` работает
- [ ] Я могу сгенерировать inventory из Terraform output

**Всё отметил?** Переходи к Главе 2 — Ad-hoc команды.
