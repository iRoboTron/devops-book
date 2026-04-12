# Глава 4: ConfigMap и Secret

> **Запомни:** ConfigMap = .env для K8s. Secret = то же но base64 (не шифрование!).

---

## 4.1 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
data:
  APP_ENV: production
  DB_HOST: postgres-svc
  DB_PORT: "5432"
```

```bash
kubectl apply -f configmap.yaml
kubectl get configmaps
```

---

## 4.2 Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secrets
type: Opaque
data:
  DB_PASSWORD: cGFzc3dvcmQ=   # base64
```

```bash
# Кодировать
echo -n "password" | base64
# cGFzc3dvcmQ=

# Создать через kubectl
kubectl create secret generic myapp-secrets \
  --from-literal=DB_PASSWORD=password
```

> **Запомни:** base64 ≠ шифрование. Любой может декодировать.
> Для реального шифрования: Sealed Secrets, Vault.

---

## 4.3 Использовать в Deployment

```yaml
spec:
  containers:
  - name: app
    envFrom:
    - configMapRef:
        name: myapp-config
    - secretRef:
        name: myapp-secrets
```

---

## 📋 Чеклист главы 4

- [ ] Я могу создать ConfigMap
- [ ] Я могу создать Secret
- [ ] Я могу подключить их к Pod через envFrom
- [ ] Я знаю что base64 ≠ шифрование

**Всё отметил?** Переходи к Главе 5 — Volume и PVC.
