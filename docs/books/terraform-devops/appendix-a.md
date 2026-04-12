# Приложение A: Шпаргалка команд

| Команда | Назначение |
|---------|-----------|
| `terraform init` | Инициализация, скачать провайдеры |
| `terraform plan` | Показать что изменится |
| `terraform apply` | Применить изменения |
| `terraform destroy` | Удалить все ресурсы |
| `terraform show` | Показать текущее состояние |
| `terraform state list` | Список ресурсов в state |
| `terraform state show res` | Детали ресурса |
| `terraform state mv old new` | Переименовать в state |
| `terraform state rm res` | Удалить из state |
| `terraform import res id` | Импортировать ресурс |
| `terraform taint res` | Пометить для пересоздания |
| `terraform untaint res` | Отменить taint |
| `terraform output` | Показать outputs |
| `terraform workspace list` | Список workspaces |
| `terraform workspace new NAME` | Создать workspace |
| `terraform workspace select NAME` | Переключить workspace |
| `terraform fmt` | Форматировать код |
| `terraform validate` | Проверить синтаксис |
| `terraform refresh` | Синхронизировать state |

# Приложение B: Готовые конфиги

## Минимальный main.tf (null/local)

```hcl
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

resource "local_file" "hello" {
  content  = "Hello!"
  filename = "${path.module}/hello.txt"
}
```

## Hetzner: VPS + Firewall + SSH-ключ

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

resource "hcloud_ssh_key" "main" {
  name       = "my-key"
  public_key = file("~/.ssh/id_ed25519.pub")
}

resource "hcloud_firewall" "main" {
  name = "myapp-fw"
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

data "hcloud_image" "ubuntu" {
  name                     = "ubuntu-24.04"
  with_deprecation_checker = true
}

resource "hcloud_server" "main" {
  name        = "myapp"
  image       = data.hcloud_image.ubuntu.id
  server_type = "cx11"
  location    = "fsn1"
  ssh_keys    = [hcloud_ssh_key.main.name]
}

resource "hcloud_firewall_attachment" "main" {
  firewall_id = hcloud_firewall.main.id
  server_ids  = [hcloud_server.main.id]
}

output "server_ip" {
  value = hcloud_server.main.ipv4_address
}
```

## .gitignore

```
.terraform/
*.tfstate
*.tfstate.backup
*.tfvars
.terraform.lock.hcl
```

## .tfvars.example

```hcl
hcloud_token = ""
```

## GitHub Actions: plan + apply

```yaml
name: Terraform
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  plan:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform plan -no-color
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}

  apply:
    if: github.event_name == 'push'
    needs: plan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform apply -auto-approve
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
```

# Приложение C: Диагностика

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `No valid credential sources` | Токен не задан | Проверь `TF_VAR_` или `terraform.tfvars` |
| `Error acquiring state lock` | Другой процесс держит lock | Подожди или `terraform force-unlock` |
| `Resource already exists` | Ресурс есть в облаке но не в state | `terraform import` |
| `provider not installed` | Забыл `terraform init` | `terraform init` |
| После ручных изменений | State не совпадает с облаком | `terraform plan` (автоматически refresh'ит) |
| `Module not installed` | Новый модуль добавлен | `terraform init` |
