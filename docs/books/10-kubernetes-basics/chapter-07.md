# Глава 7: Деплой реального Python-приложения

> **Мост от Docker Compose:** Каждый блок docker-compose → K8s манифест.

---

## 7.1 Docker Compose → K8s

```
docker-compose.yml              K8s
─────────────────              ─────
services: app           →      deployment.yaml
services: db            →      postgres.yaml
volumes: pgdata         →      pvc.yaml
environment:            →      configmap.yaml + secret.yaml
```

---

## 7.2 Полный стек

### namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp
```

### configmap.yaml
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
  namespace: myapp
data:
  DB_HOST: postgres-svc
  DB_PORT: "5432"
  DB_NAME: myapp_prod
```

### secret.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secrets
  namespace: myapp
type: Opaque
data:
  DB_PASSWORD: cGFzc3dvcmQ=
```

### pvc.yaml
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pgdata
  namespace: myapp
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
```

### postgres.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: myapp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        envFrom:
        - configMapRef:
            name: myapp-config
        - secretRef:
            name: myapp-secrets
        volumeMounts:
        - name: pgdata
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: pgdata
        persistentVolumeClaim:
          claimName: pgdata
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-svc
  namespace: myapp
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
```

### app.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    spec:
      containers:
      - name: app
        image: ghcr.io/user/myapp:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: myapp-config
        - secretRef:
            name: myapp-secrets
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-svc
  namespace: myapp
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8000
    nodePort: 30080
```

---

## 7.3 Запустить

```bash
kubectl apply -f k8s/
kubectl get all -n myapp
```

```text
NAME                          READY   STATUS    RESTARTS
pod/postgres-xxx              1/1     Running   0
pod/myapp-yyy                 1/1     Running   0
pod/myapp-zzz                 1/1     Running   0

NAME                 TYPE       CLUSTER-IP     PORT(S)
service/postgres-svc ClusterIP  10.43.100.1    5432/TCP
service/myapp-svc    NodePort   10.43.100.2    80:30080/TCP

NAME                     READY   UP-TO-DATE   AVAILABLE
deployment.apps/postgres 1/1     1            1
deployment.apps/myapp    2/2     2            2
```

---

## 7.4 Проверить что приложение работает

Сначала узнай IP ноды:

```bash
kubectl get nodes -o wide
```

```text
NAME        STATUS   ROLES                  AGE   VERSION   INTERNAL-IP
k3s-node1   Ready    control-plane,master   12d   v1.30.0   192.168.1.100
```

Теперь можно проверить приложение:

```bash
curl http://192.168.1.100:30080
```

Если пришёл ответ приложения, значит цепочка `Deployment -> Pod -> Service -> NodePort` работает правильно.

---

## 📋 Чеклист главы 7

- [ ] Я понимаю как docker-compose переводится в K8s
- [ ] Я могу создать полный стек манифестов
- [ ] Приложение доступно через NodePort

**Всё отметил?** Переходи к Главе 8 — kubectl шпаргалка.
