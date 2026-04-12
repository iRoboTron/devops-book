# Глава 2: Переменные, outputs и data sources

> **Запомни:** Хардкод = плохо. Переменные = код который можно использовать повторно без изменений.

---

## 2.1 Проблема хардкода

```hcl
resource "local_file" "hello" {
  content  = "Hello from Terraform!"
  filename = "./hello.txt"
}
```

Хочешь другой текст? Меняй main.tf. Хочешь другой файл? Меняй main.tf.

**Решение:** вынеси в переменные.

---

## 2.2 `variable` — входные параметры

```hcl
variable "greeting" {
  type        = string
  description = "Текст приветствия"
  default     = "Hello"
}

variable "name" {
  type    = string
  default = "World"
}

resource "local_file" "hello" {
  content  = "${var.greeting}, ${var.name}!"
  filename = "${path.module}/${var.name}.txt"
}
```

### `variable` блок

```hcl
variable "greeting" {
  type        = string       # тип
  description = "..."        # описание
  default     = "Hello"      # значение по умолчанию
}
```

| Поле | Обязательно? | Зачем |
|------|-------------|-------|
| `type` | Нет, но рекомендуется | Валидация типа |
| `description` | Нет | Документация |
| `default` | Нет | Если не передано — использовать это |

Без `default` — Terraform спросит значение при `apply`.

### Использовать переменную

```hcl
${var.greeting}    # в строке
var.greeting       # вне строки
```

---

## 2.3 Типы переменных

### Простые

```hcl
variable "count" {
  type    = number
  default = 3
}

variable "enabled" {
  type    = bool
  default = true
}
```

### Список (list)

```hcl
variable "tags" {
  type    = list(string)
  default = ["web", "app", "production"]
}
```

```hcl
# Использовать
${var.tags[0]}    # "web"
```

### Карта (map)

```hcl
variable "server_sizes" {
  type = map(string)
  default = {
    dev  = "cx11"
    prod = "cx31"
  }
}
```

```hcl
# Использовать
${var.server_sizes["dev"]}    # "cx11"
```

### Объект (object)

```hcl
variable "server" {
  type = object({
    name = string
    size = string
    tags = list(string)
  })
  default = {
    name = "myapp"
    size = "cx11"
    tags = ["web"]
  }
}
```

```hcl
# Использовать
${var.server.name}    # "myapp"
${var.server.size}    # "cx11"
```

---

## 2.4 Откуда берутся значения

Приоритет (от низкого к высокому):

```
1. default в variable блоке
2. terraform.tfvars файл
3. *.auto.tfvars файл
4. -var="key=value" в командной строке
5. TF_VAR_name переменная окружения
```

### terraform.tfvars

```hcl
# terraform.tfvars
greeting = "Привет"
name     = "Мир"
```

Загружается автоматически при `terraform plan` и `apply`.

### .tfvars.example

```hcl
# .tfvars.example — шаблон, можно коммитить
greeting = ""
name     = ""
```

### Командная строка

```bash
terraform apply -var="greeting=Hola" -var="name=Amigo"
```

### Переменные окружения

```bash
export TF_VAR_greeting="Hola"
terraform apply
```

---

## 2.5 `output` — выходные значения

```hcl
output "file_path" {
  value       = local_file.hello.filename
  description = "Путь к созданному файлу"
}

output "content" {
  value     = local_file.hello.content
  sensitive = true    # скрыть в выводе (для паролей)
}
```

После `apply`:

```
Outputs:

file_path = "./World.txt"
```

### Получить output

```bash
terraform output file_path
# ./World.txt

terraform output -raw file_path
# ./World.txt (без кавычек)
```

---

## 2.6 Data sources — читать существующее

```hcl
data "local_file" "existing" {
  filename = "${path.module}/existing.txt"
}

output "existing_content" {
  value = data.local_file.existing.content
}
```

`data` читает существующий ресурс. Не создаёт.

---

## 2.7 `.gitignore` для Terraform

```
.terraform/
*.tfstate
*.tfstate.backup
*.tfvars
.terraform.lock.hcl
```

| Файл | В git? | Почему |
|------|--------|--------|
| `.terraform/` | ❌ | Кэш провайдеров |
| `*.tfstate` | ❌ | Состояние, может содержать секреты |
| `*.tfstate.backup` | ❌ | Бэкап state |
| `*.tfvars` | ❌ | Может содержать секреты |
| `.terraform.lock.hcl` | ✅ | Версии провайдеров (рекомендуется) |

> **Опасно:** `*.tfvars` ВСЕГДА в `.gitignore`.
> Используй `.tfvars.example` как шаблон без значений.

---

## 📝 Упражнения

### Упражнение 2.1: Переменные
**Задача:**
1. Создай `main.tf` с переменными `greeting` и `name`
2. `terraform init` → `terraform apply`
3. Использовались значения по умолчанию?
4. Запусти с `-var="greeting=Привет"` — изменилось?

### Упражнение 2.2: tfvars
**Задача:**
1. Создай `terraform.tfvars`:
   ```hcl
   greeting = "Hola"
   name     = "Amigo"
   ```
2. `terraform plan` — значения подставились?
3. Создай `.tfvars.example` (пустой)
4. Добавь `*.tfvars` в `.gitignore`

### Упражнение 2.3: Outputs
**Задача:**
1. Добавь output для пути файла
2. `terraform apply` — output показался?
3. `terraform output file_path` — получил значение?
4. Добавь `sensitive = true` для content — скрылся в выводе?

### Упражнение 2.4: Типы переменных
**Задача:**
1. Создай переменные всех типов (string, number, bool, list, map, object)
2. Используй их в ресурсе
3. `terraform plan` — валидация типов работает?

### Упражнение 2.5: DevOps Think
**Задача:** «Ты закоммитил terraform.tfvars с токеном провайдера в git. Что делаешь?»

Ответ:
1. НЕМЕДЛЕНО отозвать токен и создать новый
2. Удалить файл из git: `git rm --cached terraform.tfvars`
3. Добавить в `.gitignore`: `*.tfvars`
4. Токен в истории git — считай скомпрометированным
5. Урок: `.tfvars.example` в git, `.tfvars` — никогда

---

## 📋 Чеклист главы 2

- [ ] Я могу создать переменные с типами и default
- [ ] Я знаю все типы переменных (string, number, bool, list, map, object)
- [ ] Я знаю откуда Terraform берёт значения (5 источников)
- [ ] Я могу создать `.tfvars` и `.tfvars.example`
- [ ] Я могу создать outputs и получить их через `terraform output`
- [ ] Я знаю `sensitive = true` для скрытия значений
- [ ] Я понимаю data sources (чтение существующего)
- [ ] Правильный `.gitignore` для Terraform
- [ ] `*.tfvars` ВСЕГДА в `.gitignore`

**Всё отметил?** Переходи к Главе 3 — locals и функции.
