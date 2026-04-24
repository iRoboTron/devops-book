# Глава 5: State-файл — сердце Terraform

> **Запомни:** Потеря state = потеря контроля над инфраструктурой. Terraform не знает что уже создано. Бэкапь state.

---

## 5.1 Что такое state

`terraform.tfstate` — JSON-файл который хранит маппинг "ресурс в коде" → "ресурс в облаке".

```
Код (main.tf)              State (.tfstate)              Облако
resource                     ← ID, атрибуты →             реальный ресурс
hcloud_server.main           server_id: 12345678          Hetzner Server #12345678
                             ipv4: 1.2.3.4                IP: 1.2.3.4
```

Без state Terraform не знает что сервер уже существует.

---

## 5.2 Что происходит при `terraform apply`

```
Шаг 1: Читает state (что уже создано)
  ↓
Шаг 2: Читает код (что должно быть)
  ↓
Шаг 3: Сравнивает state с кодом
  ↓
Шаг 4: Вызывает API облака (создать/изменить/удалить)
  ↓
Шаг 5: Обновляет state
```

Если state удалить — Terraform "забудет" про существующие ресурсы.

---

## 5.3 Посмотреть state

```bash
terraform state list
```

```
hcloud_firewall.main
hcloud_firewall_attachment.main
hcloud_server.main
hcloud_ssh_key.main
local_file.ansible_inventory
```

```bash
terraform state show hcloud_server.main
```

```
# hcloud_server.main:
resource "hcloud_server" "main" {
    id          = "12345678"
    name        = "myapp"
    image       = "ubuntu-24.04"
    server_type = "cx11"
    ipv4_address = "1.2.3.4"
    ...
}
```

---

## 5.4 Нельзя редактировать state вручную

`terraform.tfstate` — файл Terraform. Не `nano`.

Если нужно исправить — используй команды:

```bash
# Переименовать ресурс в state
terraform state mv hcloud_server.main hcloud_server.web

# Удалить из state (не из облака!)
terraform state rm hcloud_server.main

# Добавить существующий ресурс в state
terraform import hcloud_server.main 12345678
```

---

## 5.5 Бэкап state

Terraform делает бэкап автоматически:

```
terraform.tfstate         # текущий
terraform.tfstate.backup  # предыдущий
```

### Ручной бэкап

```bash
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d)
```

> **Опасно:** Потеря state = Terraform не знает про инфраструктуру.
> `terraform apply` создаст дубликаты. `terraform destroy` ничего не удалит.

---

## 5.6 Remote state

State на локальной машине — риск (удалил случайно, сжёг диск, украл ноутбук).

**Remote state** — state в облаке с бэкапом и блокировкой.

### S3 backend

```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "myapp/terraform.tfstate"
    region = "eu-central-1"
  }
}
```

После добавления backend:

```bash
terraform init
# Terraform спросит: скопировать local state в remote?
# Ответ: yes
```

Теперь state читается из S3.

### Locking

Когда два человека запускаят `apply` одновременно:

```
Person A: terraform apply → acquire lock → apply → release lock
Person B: terraform apply → wait... → acquire lock → apply → release lock
```

Без locking — одновременные apply ломают инфраструктуру.

### Альтернативы S3

| Backend | Locking | Когда |
|---------|---------|-------|
| S3 + DynamoDB | ✅ | AWS |
| Terraform Cloud | ✅ | Бесплатно для команд до 5 человек |
| GCS | ✅ | Google Cloud |
| GitLab | ✅ | Если используешь GitLab |
| HTTP | ✅ | Свой сервер |

---

## 5.7 `terraform refresh` — синхронизировать state

Если кто-то изменил ресурс вручную (в консоли хостинга):

```bash
terraform refresh
```

Обновит state чтобы соответствовал реальному состоянию.

> **Совет:** `refresh` встроен в `plan`. Обычно не нужно запускать отдельно.
> `terraform plan` автоматически.refresh'ит state.

---

## 📝 Упражнения

### Упражнение 5.1: Посмотреть state
**Задача:**
1. `terraform state list` — какие ресурсы?
2. `terraform state show hcloud_server.main` — детали?
3. Открой `terraform.tfstate` в редакторе — что внутри? (JSON)

### Упражнение 5.2: Бэкап state
**Задача:**
1. `ls terraform.tfstate*` — есть backup?
2. Сделай ручной бэкап
3. Поменяй ресурс через Terraform
4. `cat terraform.tfstate.backup` — старый state?

### Упражнение 5.3: Import существующего ресурса
**Задача:**
1. Создай сервер вручную в Hetzner Console
2. Запиши его ID
3. `terraform import hcloud_server.manual <ID>`
4. `terraform state show hcloud_server.manual` — появился?

### Упражнение 5.4: State rm
**Задача:**
1. `terraform state rm local_file.ansible_inventory`
2. `terraform state list` — файл исчез из state?
3. Но файл на диске остался?
4. `terraform apply` — Terraform хочет создать снова?

### Упражнение 5.5: DevOps Think
**Задача:** «Коллега удалил terraform.tfstate. Инфраструктура работает, но Terraform «не знает» про неё. Что делаешь?»

Ответ:
1. НЕ запускай `terraform apply` — создаст дубликаты!
2. Импортируй каждый ресурс: `terraform import resource_type.id`
3. Или восстанови из `terraform.tfstate.backup`
4. Или из ручного бэкапа
5. Урок: remote state с locking и версионированием

---

## 📋 Чеклист главы 5

- [ ] Я понимаю что такое state (маппинг код → облако)
- [ ] Я знаю что происходит при apply (5 шагов)
- [ ] Я могу посмотреть state (`state list`, `state show`)
- [ ] Я знаю что нельзя редактировать state вручную
- [ ] Я знаю команды: mv, rm, import
- [ ] Я делаю бэкапы state
- [ ] Я понимаю зачем remote state
- [ ] Я понимаю locking (защита от одновременного apply)
- [ ] Я знаю что `plan` автоматически refresh'ит state

**Всё отметил?** Переходи к Главе 6 — Modules.
