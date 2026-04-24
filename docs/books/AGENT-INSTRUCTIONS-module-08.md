# Инструкция для ИИ-агента: Написание книги по Terraform

> **Это Модуль 8 курса DevOps 2.0.**
> Предварительные требования: пройдены все модули DevOps 1.0 (1–7).
> Смотри также:
> - [AGENT-INSTRUCTIONS-module-04.md](AGENT-INSTRUCTIONS-module-04.md) — Модуль 4 (CI/CD, GitHub Actions)
> - [AGENT-INSTRUCTIONS-module-05.md](AGENT-INSTRUCTIONS-module-05.md) — Модуль 5 (Инфраструктура)

---

## Контекст проекта

Ученик прошёл DevOps 1.0. Он умеет поднимать сервисы вручную — Nginx, Docker, systemd, GitHub Actions.
Проблема: всё что он делает, он делает руками. Если сервер умрёт — он будет делать всё заново.

**Что он уже умеет** (не повторяй):
- Уверенно работает в Linux-терминале
- Поднимает Docker-контейнеры и пишет docker-compose.yml
- Настраивал Nginx, certbot, ufw, fail2ban
- Настраивал GitHub Actions: тесты → сборка → деплой
- Знает что такое SSH-ключи, переменные окружения, secrets в CI

**Что его раздражает прямо сейчас:**
- Каждый новый сервер он настраивает вручную по памяти
- Нет документации что именно настроено (только голова)
- Если нужно второй сервер — копирует первый вручную, с ошибками
- Если удалить и поднять заново — часа 3 работы

**Что он хочет после этой книги:**
Написать код один раз → выполнить одну команду → получить готовый сервер. Через неделю удалить всё и воссоздать за 5 минут. Это и есть Infrastructure as Code.

---

## Что за книга

**Название:** "Terraform: Инфраструктура как код"

**Место в курсе:** Книга 8, первая в DevOps 2.0

**Целевая аудитория:**
- Прошёл DevOps 1.0
- Устал настраивать серверы вручную
- Хочет понять IaC не как модный термин, а как реальный инструмент

**Объём:** 140-170 страниц

**Стиль:**
- Простой язык, без академизма
- Одна концепция — одно объяснение
- ASCII-схемы для потоков данных и зависимостей ресурсов
- Много практики, реальные задачи
- Без воды

---

## Главная идея, которую должна передать книга

Terraform решает одну проблему: **"я не помню как это было настроено"**.

Код Terraform — это документация, которая ещё и работает. Если код в Git, значит инфраструктура в Git.

```
Без Terraform:          С Terraform:
Сервер упал             terraform destroy
↓                       terraform apply
3 часа вспоминать       ↓
что настраивал          5 минут — всё готово
```

**Ключевое понимание, которое должна сформировать книга:**
- IaC — не про скорость. Про воспроизводимость.
- `terraform plan` — самый важный шаг (видишь что изменится ДО изменения)
- State-файл — сердце Terraform, его нужно беречь
- `terraform destroy` — такой же легитимный инструмент как `apply`

---

## Что читатель построит к концу книги

### Сначала — локально (главы 1–2, не нужен облачный аккаунт)

```
main.tf (null provider)
    │
    ├── null_resource.example    ← создание файла
    ├── local_file.hosts         ← генерация Ansible inventory
    └── local_file.report        ← отчёт о ресурсах
```

Первые две главы работают без облачного аккаунта. Читатель сразу практикует синтаксис, plan/apply цикл.

### Потом — реальный сервер (главы 3–8)

```
GitHub (dev branch)           GitHub (main branch)
       │                              │
  terraform plan               terraform apply
  (показывает план)            (применяет изменения)
       │                              │
       └─────────────────────────────┘
                       │
              Hetzner / YandexCloud
                       │
         ┌─────────────┴─────────────┐
         │                           │
    [VPS: Ubuntu]              [VPS: Ubuntu]
    [Firewall rules]           [Firewall rules]
    [SSH key]                  [SSH key]
    environment: dev           environment: prod
         │
    [DNS A-record]
    myapp.ru → IP сервера
         │
    [Ansible inventory]  ← сгенерирован из terraform output
```

Один `terraform apply` поднимает всю инфраструктуру и генерирует inventory для Ansible.

---

## Структура книги

### Глава 0: Зачем Terraform и что такое IaC

**Цель:** читатель понимает проблему, которую решает Terraform — не абстрактно, а на своём опыте.

- Проблема "кликать в панели управления": не воспроизводимо, не версионируется, не масштабируется
- Проблема shell-скриптов: идемпотентность, обработка ошибок, хаос
- IaC — третий путь: декларативное описание желаемого состояния
  ```
  Shell-скрипт:       Terraform:
  "сделай это"        "вот что должно быть"
  один раз            идемпотентно
  процедурный         декларативный
  ```
- Terraform vs Ansible: Terraform создаёт инфраструктуру, Ansible её настраивает (не конкуренты)
- Terraform vs Pulumi: упомянуть, не сравнивать детально
- Установка: официальный способ через HashiCorp APT
- Проверка: `terraform version`
- Первый `terraform init` в пустой директории — что происходит

> **Ключевая идея:** Terraform не знает как "сделать". Он знает что "должно быть". Разницу между желаемым и реальным считает сам.

---

### Часть 1: Основы (Главы 1–4)

#### Глава 1: Первый ресурс — читаем terraform plan

**Цель:** читатель понимает цикл write → plan → apply и НИКОГДА не делает apply без plan.

> **Важно:** Эта глава НЕ требует облачного аккаунта. Используем `null` и `local` провайдеры — они работают локально.

- Провайдер: что это, как подключить
  ```hcl
  terraform {
    required_providers {
      null = {
        source  = "hashicorp/null"
        version = "~> 3.2"
      }
      local = {
        source  = "hashicorp/local"
        version = "~> 2.5"
      }
    }
  }
  ```
- `terraform init` — скачивает провайдеры
- Первый ресурс: создать файл через Terraform
  ```hcl
  resource "local_file" "hello" {
    content  = "Hello from Terraform!"
    filename = "${path.module}/hello.txt"
  }
  ```
- `terraform plan` — **главный шаг этой главы**
  ```
  # Разбираем вывод plan построчно:
  + resource "local_file" "hello" {      # + = будет создан
      + content              = "Hello from Terraform!"
      + directory_permission = "0777"
      + file_permission      = "0777"
      + filename             = "./hello.txt"
      + id                   = (known after apply)
    }

  Plan: 1 to add, 0 to change, 0 to destroy.
  ```
- Читаем символы: `+` создать, `~` изменить, `-` удалить, `-/+` пересоздать
- `terraform apply` — только после понимания plan
- Проверка: файл создан? `cat hello.txt`
- `terraform plan` снова → `No changes. Infrastructure is up-to-date.`
- `terraform destroy` — удалить всё что создали
- `null_resource` — ресурс который "ничего не делает" но вызывает provisioners
  ```hcl
  resource "null_resource" "greeting" {
    provisioner "local-exec" {
      command = "echo 'Terraform just ran on $(date)'"
    }
  }
  ```

> **Правило, которое нужно повторить 3 раза:**
> ВСЕГДА `terraform plan` перед `terraform apply`.
> Читай вывод. Понимай что изменится.
> Только потом `apply`.

**Упражнения:** создать файл, прочитать plan, применить, удалить, снова применить — убедиться что результат одинаковый (идемпотентность).

#### Глава 2: Переменные, outputs и data sources

**Цель:** читатель пишет переносимый код — без хардкода значений.

- Переменные: `variable` блок
  ```hcl
  variable "greeting" {
    type        = string
    description = "Приветствие для файла"
    default     = "Hello"
  }
  ```
- Использовать переменную: `content = "${var.greeting} from Terraform!"`
- Типы переменных: string, number, bool, list, map, object
- Откуда берутся значения:
  ```
  1. default в variable блоке
  2. terraform.tfvars файл
  3. -var="key=value" в командной строке
  4. TF_VAR_имя переменная окружения  ← для секретов в CI
  ```
- `.tfvars` файл: `greeting = "Привет"`
- `terraform.tfvars` загружается автоматически, `*.auto.tfvars` тоже
- Outputs: что выводить после apply
  ```hcl
  output "file_path" {
    value       = local_file.hello.filename
    description = "Путь к созданному файлу"
  }
  ```
- `terraform output file_path` — получить значение из state
- `sensitive = true` — скрыть значение в выводе (для паролей)
- Data sources: читать существующие данные
  ```hcl
  data "local_file" "existing" {
    filename = "${path.module}/existing.txt"
  }
  ```
- Разница `resource` vs `data`: resource создаёт, data читает существующее
- `.gitignore` для Terraform:
  ```
  .terraform/
  *.tfstate
  *.tfstate.backup
  *.tfvars
  .terraform.lock.hcl    # можно коммитить (версии провайдеров)
  ```

> **Опасно:** `*.tfvars` ВСЕГДА в `.gitignore`. Используй `.tfvars.example` как шаблон без значений.
> Никогда не коммить токены, пароли, ключи.

**Упражнения:** вынести все значения в переменные, добавить output, создать `.tfvars.example`, проверить что `terraform plan` показывает `No changes`.

#### Глава 2.5: Locals, выражения и функции

**Цель:** читатель использует locals для вычислений и функций для трансформаций.

- `locals` — вычисляемые значения внутри модуля
  ```hcl
  locals {
    env        = var.environment
    name       = "${local.env}-${var.app_name}"
    tags       = {
      Environment = local.env
      ManagedBy   = "terraform"
      Project     = var.app_name
    }
  }
  ```
- Разница `variable` vs `local`: variable = вход извне, local = вычисление внутри
- Строковые функции:
  ```hcl
  join("-", ["dev", "app"])        → "dev-app"
  upper("hello")                    → "HELLO"
  replace("hello-world", "-", "_")  → "hello_world"
  substr("abcdef", 0, 3)            → "abc"
  ```
- Коллекции:
  ```hcl
  length(["a", "b", "c"])           → 3
  lookup({a = 1, b = 2}, "a", 0)   → 1
  try(var.optional, "default")      → "default" если var отсутствует
  ```
- Условия в ресурсах:
  ```hcl
  resource "local_file" "debug" {
    count    = var.debug ? 1 : 0
    content  = "Debug info..."
    filename = "debug.txt"
  }
  ```
- `count` — создать N копий ресурса
- `for_each` — создать ресурс для каждого элемента (упомянуть, детали в Модуле 10)

**Упражнения:** создать locals с тегами, использовать функции для имени ресурса, добавить условный ресурс через `count`.

#### Глава 3: Первый сервер — полный ресурс

**Цель:** читатель создаёт VPS с firewall и SSH-ключом.

> Теперь переходим на реальный провайдер. Hetzner — дешёвый, простой API. Альтернативно: YandexCloud, DigitalOcean. Код одинаковый по структуре.

- Провайдер Hetzner:
  ```hcl
  terraform {
    required_providers {
      hcloud = {
        source  = "hetznercloud/hcloud"
        version = "~> 1.45"
      }
    }
  }

  provider "hcloud" {
    token = var.hcloud_token
  }
  ```
- `hcloud_server` ресурс: image, server_type, location, ssh_keys
- `hcloud_firewall` ресурс: правила для SSH, HTTP, HTTPS
- `hcloud_firewall_attachment` — привязать firewall к серверу
- `hcloud_ssh_key` ресурс — добавить SSH-ключ
- Зависимости: Terraform строит граф автоматически
  ```
  hcloud_ssh_key.main
          │
          ▼
  hcloud_server.main ──→ hcloud_firewall_attachment.main
          ↑                          │
  hcloud_firewall.main ──────────────┘
  ```
- `depends_on` — явная зависимость когда implicit не работает
- `terraform graph` — визуализация графа зависимостей
- `terraform apply -target=resource_type.name` — применить только один ресурс
- Генерация Ansible inventory из Terraform:
  ```hcl
  resource "local_file" "ansible_inventory" {
    content  = "[servers]\n${hcloud_server.main.ipv4_address}"
    filename = "${path.module}/../ansible/hosts.ini"
  }
  ```
  > **Мост к Модулю 9:** Terraform создаёт серверы, Ansible их настраивает.
  > Output Terraform = inventory Ansible.

**Упражнения:** создать полный стек (SSH-ключ + Firewall + Server + Ansible inventory), проверить SSH-доступ, сделать `terraform destroy` и `apply` снова — убедиться что inventory перегенерировался.

---

### Часть 2: State и организация (Главы 4–5)

#### Глава 4: State-файл — сердце Terraform

**Цель:** читатель понимает что такое state, почему его нельзя терять и почему нельзя редактировать вручную.

- Что такое `terraform.tfstate`: JSON-маппинг "ресурс в коде" → "ресурс в облаке"
  ```
  Код (main.tf)          State (.tfstate)         Облако
  resource               ← ID, атрибуты →          реальный ресурс
  hcloud_server.main     server_id: 12345678
  ```
- Что происходит при `terraform apply`:
  1. Читает state (что есть сейчас)
  2. Читает код (что должно быть)
  3. Вызывает API провайдера (дельта)
  4. Обновляет state
- Почему нельзя редактировать state вручную
- `terraform state list` — список ресурсов в state
- `terraform state show resource_type.name` — детали ресурса
- `terraform state rm` — удалить из state без удаления ресурса
- `terraform import resource_type.name id` — добавить существующий ресурс в state
- Remote state: зачем нужен
  ```hcl
  terraform {
    backend "s3" {
      bucket = "my-terraform-state"
      key    = "prod/terraform.tfstate"
      region = "us-east-1"
    }
  }
  ```
- Locking: защита от одновременного запуска двух `apply`
- Альтернативы S3: Terraform Cloud, GitLab-managed state

> **Опасно:** потеря state = потеря контроля над инфраструктурой. Terraform не знает что уже создано.
> Бэкапить state: `cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d)`

**Упражнения:** переместить state в remote backend (S3 или GitLab), сделать `terraform apply` убедившись что state читается удалённо.

#### Глава 5: Modules — переиспользуемые блоки

**Цель:** читатель не копирует одинаковый код для dev и prod, а использует модули.

- Зачем нужны modules: DRY для инфраструктуры
  ```
  Без модулей:            С модулями:
  /dev/main.tf            /modules/server/main.tf
  /prod/main.tf           /dev/main.tf → module "server"
  (copy-paste с ошибками) /prod/main.tf → module "server"
  ```
- Структура модуля:
  ```
  modules/
  └── web-server/
      ├── main.tf       # ресурсы
      ├── variables.tf  # входные переменные
      └── outputs.tf    # выходные значения
  ```
- Вызов модуля:
  ```hcl
  module "dev_server" {
    source      = "./modules/web-server"
    server_name = "dev"
    server_type = "cx11"
    environment = "dev"
  }
  ```
- `terraform init` после добавления модуля — обязательно
- Публичные модули: registry.terraform.io
- Когда делать свой модуль: 3+ ресурсов которые всегда создаются вместе
- Когда НЕ делать модуль: если используется один раз

**Упражнения:** создать модуль `web-server`, использовать его для создания dev и prod серверов с разными параметрами.

---

### Часть 3: Рабочий процесс (Главы 6–8)

#### Глава 6: Workspaces — dev/staging/prod

**Цель:** читатель разделяет окружения без дублирования кода.

- Проблема: одинаковый код, разные серверы для dev и prod
- Workspace — изолированный state
  ```bash
  terraform workspace list
  terraform workspace new dev
  terraform workspace new prod
  terraform workspace select dev
  terraform workspace show  # текущий
  ```
- Использование workspace в коде:
  ```hcl
  locals {
    env = terraform.workspace  # "dev" или "prod"

    server_type = {
      dev  = "cx11"   # дешевле
      prod = "cx31"   # мощнее
    }
  }

  resource "hcloud_server" "main" {
    server_type = local.server_type[local.env]
    name        = "${local.env}-app"
  }
  ```
- `terraform apply` в workspace dev — не трогает prod
- Когда workspace не нужен: когда окружения принципиально разные (разные облака)
- Альтернатива: отдельные директории с remote state

**Упражнения:** создать dev и prod workspace, поднять серверы разного размера в каждом.

#### Глава 7: Terraform + CI/CD

**Цель:** читатель автоматизирует plan на PR и apply на merge.

- Идея: никто не делает `terraform apply` вручную с локальной машины в prod
  ```
  PR открыт:
    terraform plan → комментарий в PR с результатом

  PR merged в main:
    terraform apply → изменения в prod
  ```
- GitHub Actions пример:
  ```yaml
  on:
    pull_request:
      paths: ["terraform/**"]

  jobs:
    plan:
      steps:
        - uses: actions/checkout@v4
        - uses: hashicorp/setup-terraform@v3
        - run: terraform init
        - run: terraform plan -no-color
          env:
            TF_VAR_hcloud_token: ${{ secrets.HCLOUD_TOKEN }}
  ```
- Секреты: `TF_VAR_` префикс = автоматически подхватывается Terraform
- Remote state в CI: необходимость (нельзя хранить state в репозитории)
- Atlantis: инструмент для GitOps с Terraform (упомянуть)
- Terraform Cloud: встроенная автоматизация (упомянуть)

**Упражнения:** настроить GitHub Actions: plan на PR → apply на merge в main.

#### Глава 8: Опасные операции

**Цель:** читатель знает что может пойти не так и как это предотвратить.

- `terraform destroy`: удаляет ВСЁ что в state
  ```bash
  terraform destroy -target=hcloud_server.main  # только один ресурс
  terraform destroy  # всё — спросит подтверждение
  terraform destroy -auto-approve  # БЕЗ подтверждения — опасно
  ```
- `lifecycle` блок: защита от случайного удаления
  ```hcl
  resource "hcloud_server" "main" {
    lifecycle {
      prevent_destroy = true  # terraform destroy выдаст ошибку
    }
  }
  ```
- `create_before_destroy`: пересоздать ресурс без даунтайма
- `taint`: пометить ресурс для пересоздания при следующем apply
  ```bash
  terraform taint hcloud_server.main
  terraform plan  # покажет -/+ (удалить и создать)
  terraform untaint hcloud_server.main  # отменить
  ```
- `terraform import`: импортировать существующий ресурс в state
  ```bash
  terraform import hcloud_server.main 12345678
  ```
- Когда импорт нужен: ресурс создан вручную, хочешь управлять через Terraform

**Мини-проект главы:** лаборатория "Безопасное уничтожение":
1. Создать сервер через Terraform
2. Добавить `prevent_destroy = true`
3. Попробовать `terraform destroy` — убедиться в ошибке
4. Убрать `prevent_destroy`, выполнить destroy
5. Восстановить за `terraform apply`

> **Правило:** `prevent_destroy = true` для production-серверов и баз данных.

---

### Мини-проекты (финал курса)

#### Мини-проект 1: Полный стек — dev + prod

Создать конфигурацию которая поднимает два окружения:
- dev: маленький сервер (cx11), без `prevent_destroy`
- prod: средний сервер (cx21), с `prevent_destroy = true`
- Оба через один модуль `web-server` с разными параметрами
- Remote state (S3 или Terraform Cloud)
- Firewall: SSH только с конкретного IP, HTTP/HTTPS открыт
- Output: IP обоих серверов + сгенерированный Ansible inventory

Проверка: `terraform destroy` в dev workspace → `terraform apply` → тот же результат. Ansible inventory обновился.

#### Мини-проект 2: Disaster Recovery

Сценарий: всё сломалось, восстанавливаем с нуля.
1. Поднять инфраструктуру через `terraform apply`
2. Записать IP и проверить SSH-доступ
3. `terraform destroy -auto-approve` — уничтожить ВСЁ
4. `terraform apply` — воссоздать из кода
5. Проверить что IP новый, SSH работает, inventory обновился
6. Засечь время: должно быть < 10 минут

> **Цель:** доказать что инфраструктура полностью воспроизводима из кода.

#### Мини-проект 3: Terraform CI/CD пайплайн

Настроить GitHub Actions:
- `terraform fmt -check` и `terraform validate` на каждый push
- `terraform plan` на PR → результат в комментарии
- `terraform apply` на merge в `main`
- Remote state с locking
- Secrets через GitHub Secrets (`TF_VAR_` префикс)
- Защита: apply только из `main`, только после успешного plan

Проверка: открыть PR с изменением сервера → увидеть plan в комментарии → merge → сервер обновился.

---

### Приложения

#### Приложение A: Шпаргалка команд

| Команда | Назначение |
|---------|-----------|
| `terraform init` | Инициализация, скачать провайдеры |
| `terraform plan` | Показать что изменится |
| `terraform apply` | Применить изменения |
| `terraform destroy` | Удалить все ресурсы |
| `terraform state list` | Список ресурсов в state |
| `terraform state show res` | Детали ресурса в state |
| `terraform import res id` | Импортировать существующий ресурс |
| `terraform output` | Показать выходные значения |
| `terraform workspace list` | Список workspace |
| `terraform fmt` | Форматировать код |
| `terraform validate` | Проверить синтаксис |

#### Приложение B: Готовые конфиги
- Минимальный main.tf для Hetzner
- main.tf для Hetzner: VPS + Firewall + SSH-ключ
- .gitignore для Terraform
- .tfvars.example шаблон
- GitHub Actions workflow: plan + apply

#### Приложение C: Диагностика
- `Error: No valid credential sources found` → проверить TF_VAR_ переменные
- `Error acquiring the state lock` → другой процесс держит lock, или зависший процесс
- `Error: Resource already exists` → нужен `terraform import`
- После ручных изменений в консоли → `terraform refresh`, потом `plan`

---

## Принципы написания

### 1. Plan перед apply — каждый раз

В КАЖДОМ примере где есть `terraform apply` — перед ним должен быть `terraform plan` с разбором вывода.
Никогда не показывай `apply` без предшествующего `plan`.
Читатель должен выработать рефлекс: plan → понять → apply.

### 2. Первые две главы БЕЗ облачного аккаунта

Главы 1–2 используют `null` и `local` провайдеры. Читатель практикует синтаксис, plan/apply цикл, идемпотентность — без регистрации в облаке.
Переход на Hetzner — только с Главы 3.

### 3. Один ресурс — полный цикл

После каждого нового ресурса показывай полный цикл:
1. Написали код
2. `terraform plan` — разобрали вывод
3. `terraform apply`
4. Проверили результат (`terraform show`, curl, ssh)
5. `terraform plan` снова — должен показать `No changes`

Шаг 5 критически важен — формирует понимание идемпотентности.

### 4. State — объяснять при каждом упоминании

State — самая непонятная часть Terraform для новичков.
При каждом `terraform apply` напоминать: "state обновился, посмотри `terraform state list`".

### 5. ASCII-схемы для графа зависимостей

Всегда рисуй граф зависимостей когда в примере больше двух ресурсов:
```
resource A → resource B → resource C
```
Читатель должен понимать порядок создания.

### 6. Locals и функции — объяснить явно

Глава 2.5: `locals`, `join`, `lookup`, `try`, `count`.
Без них реальный код невозможен. Не размазывай по другим главам — отдельная глава.

### 7. Мост к Ansible — показать явно

В Главе 3: генерация Ansible inventory из Terraform output.
В мини-проектах: полный workflow Terraform → Ansible.

### 8. Никакой воды

- Без истории HashiCorp и Mitchell Hashimoto
- Без сравнения Terraform с CloudFormation, Pulumi, CDK
- Без OpenTofu vs Terraform (только упомянуть что есть open-source форк)
- Без продвинутых тем: dynamic блоки, providers alias, complex for_each

---

## Что НЕ надо делать

- ❌ Не показывать `terraform apply` без предшествующего `terraform plan`
- ❌ Не хардкодить токены и пароли в примерах кода
- ❌ Не начинать с Hetzner — первые 2 главы на `null`/`local` провайдерах
- ❌ Не объяснять Ansible, Kubernetes — это другие книги (но показать мост!)
- ❌ Не использовать Terraform Cloud как основной вариант (дорого для начинающих)
- ❌ Не объяснять все ресурсы провайдера — только нужные для проектов
- ❌ Не делать `terraform apply -auto-approve` без объяснения опасности
- ❌ Не игнорировать `.tfvars` в `.gitignore` — ВСЕГДА игнорить

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-08.md      # Этот файл
└── 08-terraform-devops/                    # Книга 8 (создать)
    ├── book.md                          # Оглавление
    ├── chapter-00.md                    # Зачем Terraform, IaC
    ├── chapter-01.md                    # Первый ресурс, null/local провайдеры
    ├── chapter-02.md                    # Переменные, outputs, data sources
    ├── chapter-02-5.md                  # Locals, выражения, функции
    ├── chapter-03.md                    # Первый сервер (Hetzner) + Ansible inventory
    ├── chapter-04.md                    # State-файл
    ├── chapter-05.md                    # Modules
    ├── chapter-06.md                    # Workspaces
    ├── chapter-07.md                    # CI/CD
    ├── chapter-08.md                    # Опасные операции
    ├── appendix-a.md                    # Шпаргалка
    ├── appendix-b.md                    # Готовые конфиги
    └── appendix-c.md                    # Диагностика
```

---

## Связь с другими модулями

**Что нужно из DevOps 1.0:**
- Модуль 4 (CI/CD) — GitHub Actions: Terraform использует те же пайплайны
- Модуль 5 (Инфраструктура) — SSH-ключи, systemd: Terraform создаёт серверы для этих настроек
- Модуль 6 (Безопасность) — Firewall, fail2ban: Terraform автоматизирует создание правил

**Что даёт Модулю 9 (Ansible) — критически важная связь:**
- Terraform создаёт пустые серверы и генерирует inventory
- Ansible берёт inventory из Terraform output (`local_file.ansible_inventory`)
- Полный workflow:
  ```
  terraform apply  →  серверы созданы
       │
       ▼
  terraform output -raw ansible_inventory  →  hosts.ini
       │
       ▼
  ansible-playbook -i hosts.ini setup.yml  →  серверы настроены
  ```
- В Главе 3 показать генерацию inventory, в финальных проектах — связку с Ansible

**Что даёт Модулям 10–11 (Kubernetes):**
- Terraform создаёт кластер K8s (managed в облаке)
- Или создаёт VM для k3s

---

## Важный нюанс: Terraform и секреты

Токены провайдера, пароли от баз данных — НЕ в `.tf` файлах и НЕ в state-файле.
Три правила:
1. Токены через `TF_VAR_` переменные окружения или CI secrets
2. State с секретами → remote backend с шифрованием
3. Sensitive outputs: `sensitive = true` → Terraform скрывает в логах

Обязательно объяснить в главе 2 (переменные) и напомнить в главе 7 (CI/CD).

---

*Эта инструкция — для ИИ-агента, который будет писать восьмую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Это первая книга DevOps 2.0 — следующая: AGENT-INSTRUCTIONS-module-09.md (Ansible)*
