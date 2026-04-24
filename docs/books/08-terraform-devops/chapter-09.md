# Глава 9: Опасные операции

> **Запомни:** `terraform destroy` удаляет ВСЁ. `prevent_destroy = true` — страховка для продакшена.

---

## 9.1 `terraform destroy`

```bash
terraform destroy
```

```
Terraform will perform the following actions:

  # hcloud_server.main will be destroyed
  - resource "hcloud_server" "main" {
      - id   = "12345678" -> null
      - name = "myapp"    -> null
    }

Plan: 0 to add, 0 to change, 5 to destroy.

Do you really want to destroy all resources?
```

Удаляет ВСЁ что в state.

### Только один ресурс

```bash
terraform destroy -target=hcloud_server.main
```

### Без подтверждения (ОПАСНО)

```bash
terraform destroy -auto-approve
```

> **Опасно:** Без подтверждения. Один Enter — и серверы удалены.

---

## 9.2 `lifecycle` — защита от удаления

### `prevent_destroy`

```hcl
resource "hcloud_server" "main" {
  name        = "prod-myapp"
  image       = "ubuntu-24.04"
  server_type = "cx31"

  lifecycle {
    prevent_destroy = true
  }
}
```

```bash
terraform destroy
# Error: Instance cannot be destroyed
# Remove prevent_destroy = true first.
```

> **Правило:** `prevent_destroy = true` для production-серверов и баз данных.

### `create_before_destroy`

```hcl
resource "hcloud_server" "main" {
  name = "myapp"

  lifecycle {
    create_before_destroy = true
  }
}
```

При изменении: сначала создаёт новый → потом удаляет старый. Без даунтайма.

---

## 9.3 `taint` — пометить для пересоздания

```bash
terraform taint hcloud_server.main
# Resource hcloud_server.main has been marked as tainted!
```

```bash
terraform plan
```

```
-/+ resource "hcloud_server" "main" {
    # forces replacement
  }
```

`-/+` = удалить и создать заново.

### Отменить

```bash
terraform untaint hcloud_server.main
```

### Когда использовать

- Сервер "заболев" (настроился неправильно)
- Нужно пересоздать с чистого листа
- Изменился базовый образ

---

## 9.4 `terraform import` — импортировать существующий ресурс

Ресурс создан вручную → хочешь управлять через Terraform.

```bash
terraform import hcloud_server.main 12345678
```

```
Import successful!
```

Теперь ресурс в state. Но код в main.tf ещё пустой.

Добавь код:

```hcl
resource "hcloud_server" "main" {
  name = "existing-server"
  # ... параметры как у существующего
}
```

```bash
terraform plan
# No changes — state и код совпали
```

---

## 📝 Упражнения

### Упражнение 9.1: prevent_destroy
**Задача:**
1. Добавь `lifecycle { prevent_destroy = true }` к серверу
2. `terraform destroy` — ошибка?
3. Убери `prevent_destroy` → `destroy` — удалился?

### Упражнение 9.2: taint
**Задача:**
1. Создай сервер
2. `terraform taint hcloud_server.main`
3. `terraform plan` — показывает `-/+`?
4. `terraform apply` — пересоздался?

### Упражнение 9.3: import
**Задача:**
1. Создай сервер вручную в Hetzner Console
2. `terraform import hcloud_server.imported <ID>`
3. Добавь код в main.tf
4. `terraform plan` — `No changes`?

---

## 📋 Чеклист главы 9

- [ ] Я знаю что `destroy` удаляет всё
- [ ] Я могу удалить один ресурс через `-target`
- [ ] Я использую `prevent_destroy` для production
- [ ] Я понимаю `create_before_destroy` (без даунтайма)
- [ ] Я могу `taint` и `untaint` ресурс
- [ ] Я могу `import` существующий ресурс
- [ ] Я знаю что import требует добавления кода в main.tf

**Всё отметил?** Книга 8 завершена! Переходи к следующей.
