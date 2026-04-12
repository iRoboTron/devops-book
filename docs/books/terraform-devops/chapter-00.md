# Глава 0: Зачем Terraform и что такое IaC

> **Запомни:** Terraform не знает как "сделать". Он знает что "должно быть". Разницу между желаемым и реальным считает сам.

---

## 0.1 Проблема ручного сервера

Ты прошёл 7 модулей. Умеешь поднять сервер вручную:

```bash
ssh root@server
apt update && apt upgrade -y
# ... ещё 50 команд ...
```

**Проблема:** через 3 месяца сервер упадёт. Ты вспомнишь 20 команд из 50.

Или понадобится второй сервер. И третий. Каждый — вручную, с ошибками.

### Решение: Infrastructure as Code

```hcl
# main.tf
resource "hcloud_server" "web" {
  name        = "myapp"
  image       = "ubuntu-24.04"
  server_type = "cx11"
}
```

Один файл. Одна команда. Сервер поднимается одинаково каждый раз.

---

## 0.2 Три подхода к настройке

### 1. Кликать в панели управления

```
Зашёл в панель хостинга → нажал "Создать сервер" → выбрал размер → готово
```

| Плюс | Минус |
|------|-------|
| Просто | Не воспроизводимо |
| | Не версионируется |
| | Не масштабируется |

### 2. Shell-скрипты

```bash
#!/bin/bash
hcloud server create --name myapp --type cx11 --image ubuntu-24.04
hcloud firewall create --name myapp-fw
# ... ещё 30 строк ...
```

| Плюс | Минус |
|------|-------|
| Воспроизводимо | Не идемпотентно (запустишь 2 раза = 2 сервера) |
| | Обработка ошибок = if/else хаос |
| | Нет состояния (не знает что уже создано) |

### 3. Terraform (IaC)

```hcl
resource "hcloud_server" "web" {
  name        = "myapp"
  image       = "ubuntu-24.04"
  server_type = "cx11"
}
```

| Плюс | Минус |
|------|-------|
| Идемпотентно (запускаешь сколько хочешь = один результат) | Нужно учить новый язык (HCL) |
| Декларативный (что должно быть, не как сделать) | State-файл нужно беречь |
| Версионируется в git | |
| Знает состояние (что есть vs что должно быть) | |

---

## 0.3 Terraform vs Ansible

Это НЕ конкуренты. Это разные инструменты.

```
Terraform           Ansible
─────────           ───────
Создаёт             Настраивает
инфраструктуру      конфигурацию

Серверы             Пакеты
Сети                Файлы
Firewall            Сервисы
DNS                 Пользователи
```

```
Порядок:
1. Terraform создаёт серверы
2. Ansible настраивает серверы (пакеты, конфиги, сервисы)
```

> **Запомни:** Terraform = "у меня есть сервер". Ansible = "сервер настроен".
> В этой книге — только Terraform. Ansible — Модуль 9.

---

## 0.4 Как работает Terraform

```
main.tf (код)          terraform.tfstate (состояние)     Облако (Hetzner)
resource "сервер"      server_id: 12345                   Реальный сервер
  name = "myapp"       ipv4: 1.2.3.4                     Файрвол
resource "firewall"    fw_id: 67890                       DNS-запись
```

1. `terraform plan` — читает код + state, сравнивает с облаком, показывает план
2. `terraform apply` — выполняет план, обновляет state
3. `terraform plan` снова — `No changes` (идемпотентность)

---

## 0.5 Установка

```bash
# Официальный способ (HashiCorp APT)
sudo apt update
sudo apt install -y gnupg software-properties-common

# Добавить ключ HashiCorp
wget -O- https://apt.releases.hashicorp.com/gpg | \
  gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg

# Добавить репозиторий
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list

# Установить
sudo apt update
sudo apt install -y terraform
```

### Проверить

```bash
terraform version
Terraform v1.8.0
```

---

## 0.6 Первый `terraform init`

```bash
mkdir ~/terraform-test && cd ~/terraform-test
nano main.tf
```

```hcl
terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}
```

```bash
terraform init
```

```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/null versions matching "~> 3.2"...
- Installing hashicorp/null v3.2.2...
- Installed hashicorp/null v3.2.2

Terraform has been successfully initialized!
```

**Что произошло:** Terraform скачал провайдер `null` в `.terraform/`.

> **Запомни:** `terraform init` — первая команда в любом проекте.
> Скачивает провайдеры которые нужны для твоего кода.
> Запускай каждый раз когда добавляешь новый провайдер.

---

## 0.7 Что будет в этой книге

| Глава | Что делаешь | Нужен ли аккаунт? |
|-------|------------|-------------------|
| 1 | Первый ресурс (null/local) | ❌ Нет |
| 2 | Переменные, outputs | ❌ Нет |
| 3 | Locals, функции | ❌ Нет |
| 4 | Первый сервер Hetzner | ✅ Да |
| 5 | State-файл | ✅ Да |
| 6 | Modules | ✅ Да |
| 7 | Workspaces | ✅ Да |
| 8 | CI/CD | ✅ Да |
| 9 | Опасные операции | ✅ Да |

> **Хорошая новость:** первые 3 главы работают БЕЗ облачного аккаунта.
> Ты сразу практикуешь синтаксис и план/апплай цикл.

---

## 📋 Чеклист главы 0

- [ ] Я понимаю проблему ручных серверов
- [ ] Я понимаю разницу между shell-скриптами и Terraform
- [ ] Я понимаю что Terraform ≠ Ansible (создаёт ≠ настраивает)
- [ ] Я понимаю как работает Terraform (код + state → облако)
- [ ] Terraform установлен (`terraform version`)
- [ ] Я запустил `terraform init` в тестовой директории

**Всё отметил?** Переходи к Главе 1 — первый ресурс.
