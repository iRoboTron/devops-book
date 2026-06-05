# Глава 9: Helm практика

---

## 9.1 Готовые Charts

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search hub postgresql
```

---

## 9.2 Установка готового Chart

```bash
helm install my-postgres bitnami/postgresql \
  --set auth.postgresPassword=secret \
  -n prod
```

Все параметры:
```bash
helm show values bitnami/postgresql
```

---

## 9.3 Зависимости

```yaml
# Chart.yaml
dependencies:
- name: postgresql
  version: "12.x"
  repository: "https://charts.bitnami.com/bitnami"
  condition: postgresql.enabled
```

```bash
helm dependency update
```

Как chart с зависимостью разворачивает и своё приложение, и subchart:

```mermaid
flowchart TD
    P["Parent chart\nmyapp"] --> DEP["dependencies:\npostgresql"]
    DEP --> DU["helm dependency update\n→ charts/postgresql.tgz"]
    P --> INST["helm install"]
    DU --> INST
    INST --> A["Release: myapp\nDeployment + Service"]
    INST --> PG["Subchart: postgresql\nStatefulSet + PVC"]

    style P fill:#1a5276,color:#fff
    style DEP fill:#7d6608,color:#fff
    style INST fill:#4a235a,color:#fff
    style A fill:#1e8449,color:#fff
    style PG fill:#1e8449,color:#fff
```

---

## 9.4 Rollback

```bash
helm history myapp-dev
helm rollback myapp-dev 1
```

---

## 📝 Упражнения

### 9.1: Установить PostgreSQL
1. `helm install pg bitnami/postgresql --set auth.postgresPassword=test`
2. Проверь: `kubectl get pods`
3. Удали: `helm uninstall pg`

### 9.2: Свой Chart
1. `helm create myapp`
2. Настрой values.yaml
3. `helm template` → проверь YAML
4. `helm install` → проверь Pod'ы

---

## 📋 Чеклист

- [ ] Могу установить готовый Chart
- [ ] Могу создать свой Chart
- [ ] Знаю `helm template`, `install`, `upgrade`, `rollback`, `uninstall`

**Книга 11 завершена!**
