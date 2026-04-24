# Глава 3: Locals, выражения и функции

> **Запомни:** `variable` = вход извне. `local` = вычисление внутри. Используй locals чтобы не повторять выражения.

---

## 3.1 `locals` — вычисляемые значения

```hcl
locals {
  env  = "dev"
  name = "${local.env}-myapp"
  tags = {
    Environment = local.env
    ManagedBy   = "terraform"
    Project     = "myapp"
  }
}

resource "local_file" "report" {
  content  = "App: ${local.name}\nEnv: ${local.env}\nTags: ${jsonencode(local.tags)}"
  filename = "${path.module}/${local.name}.txt"
}
```

### `variable` vs `local`

| | variable | local |
|--|----------|-------|
| **Кто задаёт** | Пользователь | Сам код |
| **Можно переопределить** | Да | Нет |
| **Зачем** | Входные параметры | Внутренние вычисления |

```hcl
variable "env" {
  default = "dev"
}

locals {
  # Вычисляемое на основе переменной
  name = "${var.env}-myapp"
  is_prod = var.env == "prod"
}
```

---

## 3.2 Строковые функции

### `join` — соединить список

```hcl
join("-", ["dev", "myapp", "server"])
# → "dev-myapp-server"
```

### `upper` / `lower`

```hcl
upper("hello")    # → "HELLO"
lower("HELLO")    # → "hello"
```

### `replace`

```hcl
replace("hello-world", "-", "_")
# → "hello_world"
```

### `substr`

```hcl
substr("abcdef", 0, 3)
# → "abc" (начало, длина)
```

### `format`

```hcl
format("Server: %s, Port: %d", "myapp", 8080)
# → "Server: myapp, Port: 8080"
```

---

## 3.3 Функции для коллекций

### `length`

```hcl
length(["a", "b", "c"])    # → 3
length("hello")             # → 5
```

### `lookup` — безопасный доступ к map

```hcl
lookup({a = 1, b = 2}, "a", 0)    # → 1
lookup({a = 1, b = 2}, "z", 0)    # → 0 (дефолт)
```

### `try` — попробовать, fallback

```hcl
try(var.optional, "default")
# → "default" если var.optional не задан
```

### `merge` — объединить map

```hcl
merge(
  {a = 1, b = 2},
  {b = 3, c = 4}
)
# → {a = 1, b = 3, c = 4}
```

---

## 3.4 `count` — создать N копий

```hcl
variable "file_count" {
  type    = number
  default = 3
}

resource "local_file" "files" {
  count    = var.file_count
  content  = "File number ${count.index + 1}"
  filename = "${path.module}/file_${count.index + 1}.txt"
}
```

`count.index` = 0, 1, 2...

Результат:
```
file_0.txt  → "File number 1"
file_1.txt  → "File number 2"
file_2.txt  → "File number 3"
```

### Условный ресурс

```hcl
variable "debug" {
  type    = bool
  default = false
}

resource "local_file" "debug" {
  count    = var.debug ? 1 : 0
  content  = "Debug info..."
  filename = "${path.module}/debug.txt"
}
```

`var.debug = true` → 1 файл. `false` → 0 файлов.

---

## 3.5 `for` — цикл в выражениях

### В списке

```hcl
variable "names" {
  type    = list(string)
  default = ["alice", "bob", "charlie"]
}

locals {
  upper_names = [for n in var.names : upper(n)]
  # → ["ALICE", "BOB", "CHARLIE"]
}
```

### С условием

```hcl
locals {
  short_names = [for n in var.names : n if length(n) <= 4]
  # → ["bob"]
}
```

### В map

```hcl
locals {
  name_lengths = {for n in var.names : n => length(n)}
  # → {alice = 5, bob = 3, charlie = 7}
}
```

---

## 3.6 Практический пример: полный конфиг

```hcl
variable "environment" {
  type    = string
  default = "dev"
}

variable "app_name" {
  type    = string
  default = "myapp"
}

locals {
  # Вычисляемые значения
  full_name  = "${var.environment}-${var.app_name}"
  is_prod    = var.environment == "prod"

  # Теги
  common_tags = {
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "terraform"
  }

  # Доп. теги для prod
  prod_tags = local.is_prod ? {
    Critical = "true"
    SLA      = "99.9%"
  } : {}

  # Объединить
  all_tags = merge(local.common_tags, local.prod_tags)
}

resource "local_file" "config" {
  content  = jsonencode(local.all_tags)
  filename = "${path.module}/${local.full_name}.json"
}

output "full_name" {
  value = local.full_name
}

output "tags" {
  value     = local.all_tags
  sensitive = false
}
```

При `environment = "dev"`:
- `full_name` = "dev-myapp"
- `all_tags` = `{Environment: "dev", Application: "myapp", ManagedBy: "terraform"}`

При `environment = "prod"`:
- `full_name` = "prod-myapp"
- `all_tags` = `{..., Critical: "true", SLA: "99.9%"}`

---

## 📝 Упражнения

### Упражнение 3.1: Locals
**Задача:**
1. Создай locals с `env`, `name`, `tags`
2. Используй в `local_file`
3. `terraform apply` — файл создался с правильным именем?

### Упражнение 3.2: Функции
**Задача:**
1. Создай locals с `join`, `upper`, `replace`, `substr`
2. Выведи через output
3. `terraform plan` — значения правильные?

### Упражнение 3.3: count
**Задача:**
1. Создай ресурс с `count = 3`
2. `terraform apply` — 3 файла создалось?
3. Поменяй на `count = 5` — ещё 2 добавились?
4. Поменяй на `count = 2` — 3 удалились?

### Упражнение 3.4: for
**Задача:**
1. Создай список имён
2. Через `for` сделай все заглавные
3. Через `for` с условием — только короткие (<= 4 символа)
4. Через `for` в map — имя → длина

### Упражнение 3.5: DevOps Think
**Задача:** «У тебя 10 одинаковых серверов с разными именами. Как не копировать ресурс 10 раз?»

Ответ:
- Использовать `count` с списком имён:
  ```hcl
  variable "server_names" {
    type    = list(string)
    default = ["web1", "web2", "web3", "api1", "api2"]
  }

  resource "hcloud_server" "servers" {
    count    = length(var.server_names)
    name     = var.server_names[count.index]
    ...
  }
  ```
- Или `for_each` (детали в Модуле 11):
  ```hcl
  for_each = toset(var.server_names)
  name     = each.value
  ```

---

## 📋 Чеклист главы 3

- [ ] Я понимаю разницу `variable` (вход) vs `local` (вычисление)
- [ ] Я могу использовать строковые функции (join, upper, replace, substr)
- [ ] Я могу использовать функции коллекций (length, lookup, try, merge)
- [ ] Я могу использовать `count` для создания N копий
- [ ] Я могу использовать условный ресурс через `count` (true/false)
- [ ] Я могу использовать `for` для трансформации списков и map
- [ ] Я могу собрать полный конфиг с locals, функциями и outputs

**Всё отметил?** Переходи к Главе 4 — первый реальный сервер.
