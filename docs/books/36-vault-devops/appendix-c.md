# Приложение C: Шаблоны HCL

## 1. Read-only для одного сервиса (production)

```hcl
path "secret/data/production/myapp/*" {
  capabilities = ["read"]
}

path "secret/metadata/production/myapp/*" {
  capabilities = ["list"]
}
```

## 2. Read-write для CI/CD (staging)

```hcl
path "secret/data/staging/myapp/*" {
  capabilities = ["create", "update", "patch"]
}
```

## 3. PKI: выпуск сертификатов

```hcl
path "pki_int/issue/internal-services" {
  capabilities = ["create", "update"]
}
```

## 4. Database: получение dynamic credentials

```hcl
path "database/creds/myapp-readonly" {
  capabilities = ["read"]
}
```

## 5. Admin: управление одним namespace

```hcl
path "secret/data/production/*" {
  capabilities = ["create", "read", "update", "patch", "delete", "list"]
}

path "secret/metadata/production/*" {
  capabilities = ["list"]
}

path "auth/approle/role/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```
