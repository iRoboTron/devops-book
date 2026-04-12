# Глава 6: Modules — переиспользуемые блоки

> **Запомни:** Модуль = DRY для инфраструктуры. Один раз написал — используешь для dev, staging, prod.

---

## 6.1 Зачем модули

Без модулей:

```
/dev/main.tf     ← 50 строк
/prod/main.tf    ← 50 строк (copy-paste с ошибками)
```

С модулем:

```
modules/server/  ← один раз написан
/dev/main.tf     → module "server" { ... }
/prod/main.tf    → module "server" { ... }
```

---

## 6.2 Структура модуля

```bash
mkdir -p modules/web-server
```

```
modules/
└── web-server/
    ├── main.tf       # ресурсы
    ├── variables.tf  # входные переменные
    └── outputs.tf    # выходные значения
```

### modules/web-server/variables.tf

```hcl
variable "server_name" {
  type        = string
  description = "Имя сервера"
}

variable "server_type" {
  type        = string
  description = "Тип сервера"
  default     = "cx11"
}

variable "environment" {
  type        = string
  description = "Окружение"
  default     = "dev"
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}
```

### modules/web-server/main.tf

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

resource "hcloud_server" "this" {
  name        = var.server_name
  image       = "ubuntu-24.04"
  server_type = var.server_type
  location    = "fsn1"
}

resource "hcloud_firewall" "this" {
  name = "${var.server_name}-fw"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0"]
  }
}
```

### modules/web-server/outputs.tf

```hcl
output "server_ip" {
  value = hcloud_server.this.ipv4_address
}

output "server_id" {
  value = hcloud_server.this.id
}
```

---

## 6.3 Вызов модуля

### dev/main.tf

```hcl
module "dev_server" {
  source      = "../modules/web-server"
  server_name = "dev-myapp"
  server_type = "cx11"
  environment = "dev"
  hcloud_token = var.hcloud_token
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

output "dev_ip" {
  value = module.dev_server.server_ip
}
```

### prod/main.tf

```hcl
module "prod_server" {
  source      = "../modules/web-server"
  server_name = "prod-myapp"
  server_type = "cx31"
  environment = "prod"
  hcloud_token = var.hcloud_token
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

output "prod_ip" {
  value = module.prod_server.server_ip
}
```

Один модуль — разные параметры.

---

## 6.4 `terraform init` после добавления модуля

```bash
cd dev/
terraform init
```

```
Initializing modules...
- dev_server in ../modules/web-server
```

`terraform init` сканирует модули и скачивает их провайдеры.

---

## 6.5 Когда делать свой модуль

| Делай модуль | НЕ делай модуль |
|-------------|----------------|
| 3+ ресурсов которые всегда вместе | Один ресурс |
| Используют 2+ раза | Используют 1 раз |
| Разные параметры (dev/prod) | Параметры не меняются |

---

## 6.6 Публичные модули

[registry.terraform.io](https://registry.terraform.io) — готовые модули.

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "my-vpc"
  cidr = "10.0.0.0/16"
}
```

> **Совет:** Для начинающих — пиши свои модули.
> Публичные модули удобны но нужно разбираться в их параметрах.

---

## 📝 Упражнения

### Упражнение 6.1: Создать модуль
**Задача:**
1. Создай `modules/web-server/` с main.tf, variables.tf, outputs.tf
2. Модуль создаёт сервер + firewall
3. Переменные: server_name, server_type, environment

### Упражнение 6.2: Вызвать модуль
**Задача:**
1. Создай dev/main.tf с вызовом модуля (cx11)
2. Создай prod/main.tf с вызовом модуля (cx31)
3. `terraform init` в dev → `terraform apply`
4. Сервер создался?

### Упражнение 6.3: Outputs модуля
**Задача:**
1. Добавь output `server_ip` в модуль
2. Используй `module.dev_server.server_ip` в dev/main.tf
3. `terraform output dev_ip` — IP сервера?

### Упражнение 6.4: DevOps Think
**Задача:** «У тебя модуль создаёт сервер. Нужно добавить SSH-ключ. Менять модуль или передавать снаружи?»

Ответ:
- Передавать снаружи через переменную:
  ```hcl
  variable "ssh_key_id" {
    type = string
  }

  resource "hcloud_server" "this" {
    ssh_keys = [var.ssh_key_id]
  }
  ```
- Модуль не должен хардкодить SSH-ключи.
- Хороший модуль = настраиваемый через переменные.

---

## 📋 Чеклист главы 6

- [ ] Я понимаю зачем нужны модули (DRY)
- [ ] Я знаю структуру модуля (main.tf, variables.tf, outputs.tf)
- [ ] Я могу создать модуль
- [ ] Я могу вызвать модуль с разными параметрами
- [ ] Я знаю что `terraform init` нужен после добавления модуля
- [ ] Я знаю когда делать модуль а когда нет
- [ ] Я могу получить output модуля (`module.name.output`)

**Всё отметил?** Переходи к Главе 7 — Workspaces.
