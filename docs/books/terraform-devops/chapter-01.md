# Глава 1: Первый ресурс — читаем terraform plan

> **Запомни:** ВСЕГДА `terraform plan` перед `terraform apply`. Читай вывод. Понимай что изменится. Только потом `apply`.

---

## 1.1 Провайдеры: что это

**Провайдер** — плагин который позволяет Terraform общаться с сервисом (Hetzner, AWS, локальные файлы).

В этой главе — `null` и `local` провайдеры. Они работают локально, не нужен аккаунт.

---

## 1.2 Первый ресурс: создать файл

Создай директорию проекта:

```bash
mkdir ~/terraform-basics && cd ~/terraform-basics
```

Создай `main.tf`:

```hcl
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "local" {}

resource "local_file" "hello" {
  content  = "Hello from Terraform!"
  filename = "${path.module}/hello.txt"
}
```

### Разбор

```hcl
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"   # откуда скачать
      version = "~> 2.5"             # версия
    }
  }
}
```
Говорит Terraform: "нужен провайдер local версии 2.5+".

```hcl
provider "local" {}
```
Инициализирует провайдер.

```hcl
resource "local_file" "hello" {
  content  = "Hello from Terraform!"
  filename = "${path.module}/hello.txt"
}
```
Создаёт файл. `${path.module}` = директория где лежит main.tf.

---

## 1.3 `terraform init`

```bash
terraform init
```

```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/local versions matching "~> 2.5"...
- Installing hashicorp/local v2.5.2...
- Installed hashicorp/local v2.5.2

Terraform has been successfully initialized!
```

Скачал провайдер `local` в `.terraform/`.

---

## 1.4 `terraform plan` — самый важный шаг

```bash
terraform plan
```

```
Terraform used the selected providers to generate the following execution
plan. Resource actions are indicated with the following symbols:
  + create

Terraform will perform the following actions:

  # local_file.hello will be created
  + resource "local_file" "hello" {
      + content              = "Hello from Terraform!"
      + directory_permission = "0777"
      + file_permission      = "0777"
      + filename             = "./hello.txt"
      + id                   = (known after apply)
    }

Plan: 1 to add, 0 to change, 0 to destroy.
```

### Читаем вывод

```
+ create
```
`+` = будет создан новый ресурс.

```
+ resource "local_file" "hello" {
```
Тип ресурса: `local_file`, имя: `hello`.

```
+ content = "Hello from Terraform!"
```
Каждое `+` = новое значение.

```
+ id = (known after apply)
```
ID будет известен только после создания (облако его выдаст).

```
Plan: 1 to add, 0 to change, 0 to destroy.
```
Итого: 1 создать, 0 изменить, 0 удалить.

> **Запомни:** Символы плана:
> - `+` создать
> - `~` изменить
> - `-` удалить
> - `-/+` удалить и создать заново
>
> Всегда читай план перед apply.

---

## 1.5 `terraform apply`

```bash
terraform apply
```

Покажет тот же план и спросит:

```
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value:
```

Набери `yes`:

```
local_file.hello: Creating...
local_file.hello: Creation complete after 0s [id=./hello.txt]

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

### Проверить

```bash
cat hello.txt
Hello from Terraform!
```

Файл создан!

---

## 1.6 Идемпотентность: запусти дважды

```bash
terraform apply
```

```
No changes. Your infrastructure matches the configuration.

Terraform has compared your real infrastructure against your configuration
and found no differences, so no changes are needed.

Apply complete! Resources: 0 added, 0 changed, 0 destroyed.
```

**0 добавлено, 0 изменено, 0 удалено.**

Файл уже есть с правильным содержимым → Terraform ничего не делает.

> **Это и есть идемпотентность.**
> Запусти сколько хочешь — результат одинаковый.
> В отличие от shell-скрипта который создаст файл заново.

---

## 1.7 Изменить ресурс

Поменяй содержимое файла в `main.tf`:

```hcl
resource "local_file" "hello" {
  content  = "Hello, updated!"
  filename = "${path.module}/hello.txt"
}
```

```bash
terraform plan
```

```
Terraform will perform the following actions:

  # local_file.hello will be updated in-place
  ~ resource "local_file" "hello" {
      ~ content = "Hello from Terraform!" -> "Hello, updated!"
        id      = "./hello.txt"
    }

Plan: 0 to add, 1 to change, 0 to destroy.
```

`~` = изменить на месте. Файл перезапишется.

```bash
terraform apply -auto-approve
```

```
local_file.hello: Modifying...
local_file.hello: Modifications complete after 0s
```

```bash
cat hello.txt
Hello, updated!
```

---

## 1.8 `terraform show` — текущее состояние

```bash
terraform show
```

```
# local_file.hello:
resource "local_file" "hello" {
    content              = "Hello, updated!"
    directory_permission = "0777"
    file_permission      = "0777"
    filename             = "./hello.txt"
    id                   = "./hello.txt"
}
```

Показывает текущее состояние ресурса (из state-файла).

---

## 1.9 `terraform destroy` — удалить всё

```bash
terraform destroy
```

```
Terraform will perform the following actions:

  # local_file.hello will be destroyed
  - resource "local_file" "hello" {
      - content              = "Hello, updated!" -> null
      - filename             = "./hello.txt" -> null
      - id                   = "./hello.txt" -> null
    }

Plan: 0 to add, 0 to change, 1 to destroy.

Do you really want to destroy all resources?
```

`-` = удалить. Набери `yes`:

```
local_file.hello: Destroying...
local_file.hello: Destruction complete after 0s

Destroy complete! Resources: 1 destroyed.
```

```bash
cat hello.txt
cat: hello.txt: No such file or directory
```

Файл удалён.

> **Запомни:** `terraform destroy` удаляет ВСЁ что управляется Terraform.
> Всегда проверяй план перед подтверждением.

---

## 1.10 `null_resource` — ресурс который "ничего не делает"

```hcl
resource "null_resource" "greeting" {
  provisioner "local-exec" {
    command = "echo 'Terraform executed at $(date)' >> execution.log"
  }
}
```

`null_resource` — ресурс без реальной инфраструктуры. Но запускает `provisioner`.

```bash
terraform apply
```

```
null_resource.greeting: Creating...
null_resource.greeting: Provisioning with 'local-exec'...
null_resource.greeting: Creation complete
```

```bash
cat execution.log
Terraform executed at Thu Apr 12 14:30:00 UTC 2026
```

> **Зачем:** Тестировать Terraform без реальной инфраструктуры.
> Или запускать локальные скрипты при изменении ресурсов.

---

## 📝 Упражнения

### Упражнение 1.1: Первый ресурс
**Задача:**
1. Создай директорию и `main.tf` с `local_file` ресурсом
2. `terraform init`
3. `terraform plan` — что покажет?
4. `terraform apply` — файл создан?
5. `cat hello.txt` — содержимое правильное?

### Упражнение 1.2: Идемпотентность
**Задача:**
1. Запусти `terraform apply` второй раз
2. `0 added, 0 changed, 0 destroyed`?
3. Это подтверждает идемпотентность ✅

### Упражнение 1.3: Изменение
**Задача:**
1. Поменяй `content` в main.tf
2. `terraform plan` — показывает `~` (изменение)?
3. `terraform apply` — файл обновился?
4. `terraform apply` ещё раз — `No changes`?

### Упражнение 1.4: Удаление
**Задача:**
1. `terraform destroy` — файл удалился?
2. `terraform apply` — файл создался снова?
3. Это подтверждает что код = единственная истина ✅

### Упражнение 1.5: null_resource
**Задача:**
1. Добавь `null_resource` с `local-exec`
2. `terraform apply` — execution.log создался?
3. Запусти снова — log обновился?

---

## 📋 Чеклист главы 1

- [ ] Я понимаю что такое провайдер
- [ ] Я запустил `terraform init`
- [ ] Я прочитал вывод `terraform plan` и понял символы (+, ~, -)
- [ ] Я запустил `terraform apply` и создал ресурс
- [ ] Я проверил идемпотентность (второй запуск = No changes)
- [ ] Я изменил ресурс и увидел `~` в plan
- [ ] Я запустил `terraform destroy`
- [ ] Я использовал `terraform show`
- [ ] Я понимаю правило: ВСЕГДА plan перед apply

**Всё отметил?** Переходи к Главе 2 — переменные и outputs.
