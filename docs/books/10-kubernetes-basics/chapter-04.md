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

## 4.4 Проверить что переменные видны в Pod

```bash
kubectl exec -it myapp-xxx -- env | grep DB_
```

```text
DB_HOST=postgres-svc
DB_PORT=5432
DB_PASSWORD=password
```

Это подтверждает, что `envFrom` работает.

Важно: Secret внутри Pod тоже виден как plaintext. Kubernetes не шифрует его автоматически внутри контейнера, он просто подставляет значение в переменную окружения.

---

## 📝 Упражнения

### Упражнение 4.1: ConfigMap
**Задача:**
1. Создай ConfigMap с `APP_ENV=production`
2. Подключи через `envFrom`
3. `kubectl exec` — переменная видна?

### Упражнение 4.2: Secret
**Задача:**
1. `kubectl create secret generic myapp-secrets --from-literal=DB_PASSWORD=secret123`
2. Подключи через `envFrom`
3. `kubectl exec` — `DB_PASSWORD` видна?
4. `kubectl get secret myapp-secrets -o yaml` — что видишь в `data`?

---

## 📋 Чеклист главы 4

- [ ] Я могу создать ConfigMap
- [ ] Я могу создать Secret
- [ ] Я могу подключить их к Pod через envFrom
- [ ] Я знаю что base64 ≠ шифрование

**Всё отметил?** Переходи к Главе 5 — Volume и PVC.
