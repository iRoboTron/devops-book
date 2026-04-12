# Глава 8: Terraform + CI/CD

> **Запомни:** Никто не делает `terraform apply` вручную в production. План на PR → Apply на merge.

---

## 8.1 Идея

```
PR открыт:                    PR merged в main:
  terraform plan                terraform apply
  ↓                             ↓
Комментарий в PR:              Изменения применены
"+ hcloud_server.main"
```

---

## 8.2 GitHub Actions: plan на PR

### .github/workflows/terraform.yml

```yaml
name: Terraform

on:
  pull_request:
    branches: [main]
    paths: ["terraform/**"]

jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: terraform/

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init

      - name: Terraform Plan
        run: terraform plan -no-color
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
```

Результат в логах Actions — видно что изменится.

---

## 8.3 Apply на merge

```yaml
  apply:
    needs: plan
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    defaults:
      run:
        working-directory: terraform/

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init

      - name: Terraform Apply
        run: terraform apply -auto-approve
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
```

`if:` — только из `main` и только при push (merge).

---

## 8.4 Секреты в CI

GitHub → Settings → Secrets → Actions:

```
HCLOUD_TOKEN = твой_токен
```

В workflow:

```yaml
env:
  HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
```

Или через `TF_VAR_`:

```yaml
env:
  TF_VAR_hcloud_token: ${{ secrets.HCLOUD_TOKEN }}
```

Terraform автоматически подхватит `TF_VAR_` переменные.

---

## 8.5 Remote state в CI

Для CI нужен remote state (S3, Terraform Cloud).
Иначе каждый runner будет иметь свой state.

```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "myapp/terraform.tfstate"
    region = "eu-central-1"
  }
}
```

---

## 📝 Упражнения

### Упражнение 8.1: Настроить workflow
**Задача:**
1. Создай `.github/workflows/terraform.yml`
2. Plan на PR в terraform директорию
3. Apply на push в main

### Упражнение 8.2: Проверить
**Задача:**
1. Открой PR с изменением в terraform/
2. Plan запустился?
3. Смерджи — apply запустился?

---

## 📋 Чеклист главы 8

- [ ] Я понимаю идею: plan на PR, apply на merge
- [ ] Я могу настроить GitHub Actions для Terraform
- [ ] Я храню секреты в GitHub Secrets
- [ ] Я понимаю зачем remote state в CI

**Всё отметил?** Переходи к Главе 9 — опасные операции.
