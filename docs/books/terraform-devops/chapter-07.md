# Глава 7: Workspaces — dev/staging/prod

> **Запомни:** Workspace = изолированный state для одного и того же кода. Один код — разные серверы.

---

## 7.1 Проблема

Один код для dev и prod. Но серверы разные:

```
dev:  cx11, без prevent_destroy
prod: cx31, с prevent_destroy
```

**Вариант 1:** Две директории (dev/, prod/) — copy-paste.
**Вариант 2:** Workspaces — один код, два state.

---

## 7.2 Создать workspaces

```bash
terraform workspace list
# * default

terraform workspace new dev
# Created and switched to workspace "dev"!

terraform workspace new prod
# Created and switched to workspace "prod"!
```

### Переключиться

```bash
terraform workspace select dev
terraform workspace show
# dev
```

---

## 7.3 Использовать workspace в коде

```hcl
locals {
  env = terraform.workspace

  server_type = {
    dev  = "cx11"
    prod = "cx31"
  }

  name = "${local.env}-myapp"
}

resource "hcloud_server" "main" {
  name        = local.name
  image       = "ubuntu-24.04"
  server_type = local.server_type[local.env]
  location    = "fsn1"
}
```

### Что происходит

```
terraform workspace select dev
terraform apply
  → Сервер: dev-myapp, cx11

terraform workspace select prod
terraform apply
  → Сервер: prod-myapp, cx31
```

Один код. Два сервера. Разные state.

---

## 7.4 State в workspaces

```
terraform.tfstate.d/
├── dev/
│   └── terraform.tfstate    # state для dev
└── prod/
    └── terraform.tfstate    # state для prod
```

Каждый workspace = отдельный state-файл.

`terraform apply` в dev НЕ трогает prod.

---

## 7.5 Когда workspace НЕ нужен

| Ситуация | Решение |
|----------|---------|
| Одинаковый код, разные размеры серверов | ✅ Workspace |
| Разные облака (AWS + Hetzner) | ❌ Отдельные директории |
| Разные провайдеры | ❌ Отдельные директории |
| Принципиально разная инфраструктура | ❌ Отдельные директории |

---

## 📝 Упражнения

### Упражнение 7.1: Создать workspaces
**Задача:**
1. `terraform workspace new dev`
2. `terraform workspace new prod`
3. `terraform workspace list` — оба видны?

### Упражнение 7.2: Разные серверы
**Задача:**
1. Используй `terraform.workspace` в коде
2. `terraform workspace select dev` → `apply` — cx11?
3. `terraform workspace select prod` → `apply` — cx31?
4. Оба сервера работают одновременно?

### Упражнение 7.3: Очистить
**Задача:**
1. `terraform workspace select dev` → `destroy`
2. `terraform workspace select prod` → `destroy`
3. `terraform workspace delete dev`
4. `terraform workspace delete prod`

---

## 📋 Чеклист главы 7

- [ ] Я понимаю зачем workspaces (один код, разные state)
- [ ] Я могу создать и переключить workspace
- [ ] Я использую `terraform.workspace` в коде
- [ ] Я знаю что каждый workspace = отдельный state
- [ ] Я знаю когда НЕ использовать workspaces

**Всё отметил?** Переходи к Главе 8 — CI/CD.
