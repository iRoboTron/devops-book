# Глава 4: Первый сервер — полный ресурс

> **Теперь переходим на реальный провайдер.** Hetzner — дешёвый, простой API. Альтернативно: YandexCloud, DigitalOcean. Код одинаковый по структуре.

---

## 4.1 Провайдер Hetzner

Создай новый проект:

```bash
mkdir ~/terraform-hetzner && cd ~/terraform-hetzner
```

### Токен

1. Зайди на [console.hetzner.cloud](https://console.hetzner.cloud)
2. Создай API Token (Read & Write)
3. Скопируй токен

```bash
export HCLOUD_TOKEN="твой_токен"
```

### main.tf

```hcl
terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

provider "hcloud" {
  token = var.hcloud_token
}
```

### terraform.tfvars

```hcl
hcloud_token = "твой_токен"
```

> **Опасно:** `terraform.tfvars` НЕ коммить в git!
> Добавь `*.tfvars` в `.gitignore`.

---

## 4.2 SSH-ключ

```hcl
resource "hcloud_ssh_key" "main" {
  name       = "my-key"
  public_key = file("~/.ssh/id_ed25519.pub")
}
```

`file()` — читает файл с твоей машины.

```bash
terraform init
terraform plan
```

```
+ resource "hcloud_ssh_key" "main" {
    + fingerprint = (known after apply)
    + id          = (known after apply)
    + name        = "my-key"
    + public_key  = "ssh-ed25519 AAAA..."
  }
```

```bash
terraform apply
```

SSH-ключ загружен в Hetzner.

---

## 4.3 Firewall

```hcl
resource "hcloud_firewall" "main" {
  name = "myapp-fw"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }
}
```

Три правила: SSH (22), HTTP (80), HTTPS (443).

> **Совет:** Для продакшена замени `0.0.0.0/0` на свой IP для SSH:
> `"1.2.3.4/32"` — только твой IP может подключиться по SSH.

---

## 4.4 Сервер

```hcl
data "hcloud_image" "ubuntu" {
  name                = "ubuntu-24.04"
  with_deprecation_checker = true
}

resource "hcloud_server" "main" {
  name        = "myapp"
  image       = data.hcloud_image.ubuntu.id
  server_type = "cx11"
  location    = "fsn1"
  ssh_keys    = [hcloud_ssh_key.main.name]
}
```

### Разбор

| Поле | Значение |
|------|----------|
| `name` | Имя сервера |
| `image` | Образ ОС (data source) |
| `server_type` | Тип (cx11 = 1 CPU, 2GB RAM) |
| `location` | `fsn1` = Фалькенштайн (Германия) |
| `ssh_keys` | SSH-ключи |

---

## 4.5 Привязать Firewall к серверу

```hcl
resource "hcloud_firewall_attachment" "main" {
  firewall_id = hcloud_firewall.main.id
  server_ids  = [hcloud_server.main.id]
}
```

### Граф зависимостей

```
hcloud_image.ubuntu
       │
       ▼
hcloud_ssh_key.main    hcloud_firewall.main
       │               │
       ▼               ▼
    hcloud_server.main
            │
            ▼
hcloud_firewall_attachment.main
```

Terraform создаёт ресурсы в правильном порядке автоматически.

---

## 4.6 Outputs

```hcl
output "server_ip" {
  value       = hcloud_server.main.ipv4_address
  description = "Публичный IP сервера"
}

output "server_name" {
  value = hcloud_server.main.name
}
```

```bash
terraform apply

Outputs:
server_ip = "1.2.3.4"
server_name = "myapp"
```

---

## 4.7 Генерация Ansible inventory

> **Мост к Модулю 9:** Terraform создаёт серверы, Ansible их настраивает.

```hcl
resource "local_file" "ansible_inventory" {
  content = <<-EOT
[webservers]
${hcloud_server.main.name} ansible_host=${hcloud_server.main.ipv4_address}

[all:vars]
ansible_user=root
ansible_ssh_private_key_file=~/.ssh/id_ed25519
  EOT
  filename = "${path.module}/../ansible/hosts.ini"
}
```

После `apply`:

```ini
# ../ansible/hosts.ini
[webservers]
myapp ansible_host=1.2.3.4

[all:vars]
ansible_user=root
ansible_ssh_private_key_file=~/.ssh/id_ed25519
```

Terraform сгенерировал Ansible inventory автоматически.

---

## 4.8 Проверить результат

```bash
terraform apply
```

```
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
server_ip = "1.2.3.4"
server_name = "myapp"
```

Проверить SSH:

```bash
ssh root@1.2.3.4
```

Проверить firewall:

```bash
terraform plan
# No changes — всё на месте
```

---

## 4.9 Полный main.tf

```hcl
terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

provider "hcloud" {
  token = var.hcloud_token
}

# SSH-ключ
resource "hcloud_ssh_key" "main" {
  name       = "my-key"
  public_key = file("~/.ssh/id_ed25519.pub")
}

# Firewall
resource "hcloud_firewall" "main" {
  name = "myapp-fw"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# Образ
data "hcloud_image" "ubuntu" {
  name                     = "ubuntu-24.04"
  with_deprecation_checker = true
}

# Сервер
resource "hcloud_server" "main" {
  name        = "myapp"
  image       = data.hcloud_image.ubuntu.id
  server_type = "cx11"
  location    = "fsn1"
  ssh_keys    = [hcloud_ssh_key.main.name]
}

# Привязать firewall
resource "hcloud_firewall_attachment" "main" {
  firewall_id = hcloud_firewall.main.id
  server_ids  = [hcloud_server.main.id]
}

# Ansible inventory
resource "local_file" "ansible_inventory" {
  content = <<-EOT
[webservers]
${hcloud_server.main.name} ansible_host=${hcloud_server.main.ipv4_address}

[all:vars]
ansible_user=root
ansible_ssh_private_key_file=~/.ssh/id_ed25519
  EOT
  filename = "${path.module}/../ansible/hosts.ini"
}

# Outputs
output "server_ip" {
  value = hcloud_server.main.ipv4_address
}

output "server_name" {
  value = hcloud_server.main.name
}
```

---

## 📝 Упражнения

### Упражнение 4.1: Создать сервер
**Задача:**
1. Создай main.tf (как в 4.9)
2. `terraform init` → `terraform plan` → `terraform apply`
3. Получил IP? SSH работает?

### Упражнение 4.2: Идемпотентность
**Задача:**
1. `terraform apply` ещё раз — `No changes`?
2. Это подтверждает что инфраструктура стабильна ✅

### Упражнение 4.3: Изменить сервер
**Задача:**
1. Поменяй `server_type = "cx21"` (больше CPU/RAM)
2. `terraform plan` — покажет изменение?
3. `terraform apply` — сервер обновился?

### Упражнение 4.4: Ansible inventory
**Задача:**
1. Проверь что hosts.ini создался
2. Содержит правильный IP?
3. Попробуй: `ansible -i hosts.ini all -m ping`

### Упражнение 4.5: Очистить
**Задача:**
1. `terraform destroy` — сервер удалён?
2. `terraform apply` — сервер создался снова?
3. hosts.ini обновился с новым IP?

---

## 📋 Чеклист главы 4

- [ ] Я подключил провайдер Hetzner
- [ ] Я создал SSH-ключ через Terraform
- [ ] Я создал Firewall с правилами (22, 80, 443)
- [ ] Я создал сервер с правильными параметрами
- [ ] Я привязал Firewall к серверу
- [ ] Я получил IP через output
- [ ] Я сгенерировал Ansible inventory автоматически
- [ ] Идемпотентность подтверждена (план = No changes)
- [ ] Я могу `destroy` и `apply` — результат одинаковый

**Всё отметил?** Переходи к Главе 5 — State-файл.
