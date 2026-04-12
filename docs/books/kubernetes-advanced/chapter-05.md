# Глава 5: NetworkPolicy — фаервол для Pod'ов

> **Проблема:** По умолчанию любой Pod видит любой Pod. БД доступна из всех namespace.

---

## 5.1 По умолчанию: всё разрешено

```
Pod в default → Pod в prod → PostgreSQL
Любой Pod → Redis → все данные
```

---

## 5.2 Deny All

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

Теперь весь входящий и исходящий трафик в namespace prod заблокирован.

---

## 5.3 Разрешить конкретный трафик

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-postgres
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - port: 5432
```

Только Pod с label `app=api` может обратиться к PostgreSQL на порт 5432.

---

## 5.4 CNI

NetworkPolicy требует CNI который его поддерживает:
- k3s по умолчанию: Flannel (НЕ поддерживает)
- Для NetworkPolicy: Calico или Cilium

```bash
# k3s с Calico
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --flannel-backend=none" sh -
```

---

## 📋 Чеклист

- [ ] CNI поддерживает NetworkPolicy
- [ ] Deny-all policy создан
- [ ] Разрешён только нужный трафик
- [ ] Проверено: заблокированный трафик не проходит

**Переходи к Главе 6 — RBAC.**
