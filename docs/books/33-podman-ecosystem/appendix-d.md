# Приложение D: Из Pod в Deployment — адаптация K8s YAML

## Проблема

`podman kube generate` создаёт `kind: Pod` — это объект который запускает ровно один экземпляр набора контейнеров на конкретной ноде. В production Kubernetes так почти никто не работает: там нужны `Deployment` (реплики, rolling update, история версий) или `StatefulSet` (для stateful приложений).

Этот раздел показывает что именно нужно изменить чтобы превратить Pod YAML из Podman в production-ready Kubernetes манифест.

---

## Исходный YAML из podman kube generate

Возьмём типичный вывод `podman kube generate`:

```yaml
# Сгенерировано: podman kube generate myapp-pod > pod.yaml
# Это НЕ production-ready YAML

apiVersion: v1
kind: Pod
metadata:
  creationTimestamp: "2024-01-15T10:00:00Z"
  labels:
    app: myapp-pod
  name: myapp-pod
spec:
  containers:
  - args:
    - python
    - main.py
    env:
    - name: DATABASE_URL
      value: postgresql://postgres:secret@localhost/mydb
    image: docker.io/myuser/myapp:latest
    name: myapp
    ports:
    - containerPort: 8000
      protocol: TCP
    resources: {}
    securityContext:
      runAsNonRoot: false
    volumeMounts:
    - mountPath: /app/uploads
      name: myapp-pod-uploads-pvc

  - env:
    - name: POSTGRES_PASSWORD
      value: secret
    - name: POSTGRES_DB
      value: mydb
    image: docker.io/library/postgres:16-alpine
    name: postgres
    resources: {}
    volumeMounts:
    - mountPath: /var/lib/postgresql/data
      name: myapp-pod-pgdata-pvc

  restartPolicy: Never
  volumes:
  - name: myapp-pod-uploads-pvc
    persistentVolumeClaim:
      claimName: myapp-pod-uploads
  - name: myapp-pod-pgdata-pvc
    persistentVolumeClaim:
      claimName: myapp-pod-pgdata
```

---

## Что нужно изменить

### Обязательно

**1. Разделить Pod на отдельные Deployment + StatefulSet**

В K8s принято: каждый сервис — отдельный объект. Приложение и БД в одном Pod — антипаттерн (нельзя масштабировать независимо).

**2. `kind: Pod` → `kind: Deployment`** (для stateless приложений)

**3. `restartPolicy: Never` → убрать или поставить `Always`**

Deployment управляет реплика-сетами, `restartPolicy` внутри него должен быть `Always` (значение по умолчанию, можно не писать).

**4. Вынести секреты из plain text в `kind: Secret`**

`DATABASE_URL` и `POSTGRES_PASSWORD` открытым текстом в YAML — недопустимо в production.

**5. Добавить `resources.requests/limits`**

`resources: {}` означает что Pod может занять всю память ноды.

**6. Убрать `creationTimestamp`**

Генерируется Kubernetes, не должно быть в исходном манифесте.

### Желательно

**7. Добавить `readinessProbe` и `livenessProbe`**

Без них K8s не знает когда приложение готово принимать трафик.

**8. Поменять `securityContext`**

`runAsNonRoot: false` разрешает запуск от root — поставить `true` и указать `runAsUser`.

**9. Обновить `image` тег**

`latest` в production — плохая практика. Использовать конкретный тег или digest.

---

## Production-ready версия

### Secret

```yaml
# secrets.yaml
# В реальном проекте: использовать Sealed Secrets, Vault, или ESO
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secret
  namespace: default
type: Opaque
stringData:
  database-url: "postgresql://postgres:secret@postgres-svc/mydb"
  postgres-password: "secret"
```

### PersistentVolumeClaim для PostgreSQL

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pgdata
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### StatefulSet для PostgreSQL

```yaml
# postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: default
spec:
  serviceName: postgres-svc
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: docker.io/library/postgres:16-alpine   # конкретный тег
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: myapp-secret
              key: postgres-password
        - name: POSTGRES_DB
          value: mydb
        ports:
        - containerPort: 5432
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: pgdata
          mountPath: /var/lib/postgresql/data
        securityContext:
          runAsNonRoot: false   # postgres требует root для init
      volumes:
      - name: pgdata
        persistentVolumeClaim:
          claimName: pgdata
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-svc
  namespace: default
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None   # headless service для StatefulSet
```

### Deployment для приложения

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  replicas: 2                    # ← можно масштабировать
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: docker.io/myuser/myapp:v1.2.3   # ← конкретный тег
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: myapp-secret
              key: database-url
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
        - name: tmp
          mountPath: /tmp          # если readOnlyRootFilesystem: true
      volumes:
      - name: uploads
        persistentVolumeClaim:
          claimName: myapp-uploads
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-svc
  namespace: default
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: default
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-svc
            port:
              number: 80
```

---

## Применить в кластере

```bash
# Создать namespace (если нужен)
kubectl create namespace myapp

# Применить секреты
kubectl apply -f secrets.yaml

# Применить хранилище
kubectl apply -f pvc.yaml

# Применить PostgreSQL
kubectl apply -f postgres.yaml

# Проверить что БД готова
kubectl rollout status statefulset/postgres

# Применить приложение
kubectl apply -f deployment.yaml

# Проверить
kubectl get pods
kubectl get svc
kubectl rollout status deployment/myapp
```

---

## Чеклист перед деплоем в K8s

```text
Из Pod в Deployment / StatefulSet:
☐ Каждый сервис — отдельный Deployment или StatefulSet
☐ kind: Pod → kind: Deployment (или StatefulSet для БД)
☐ restartPolicy убран или Always

Секреты:
☐ Все пароли/токены в kind: Secret (не plain text в YAML)
☐ Использовать secretKeyRef в env, не valueFrom.fieldRef

Ресурсы:
☐ resources.requests задан (для scheduler)
☐ resources.limits задан (от OOM)

Проверки здоровья:
☐ readinessProbe: когда принимать трафик
☐ livenessProbe: когда перезапустить

Образы:
☐ Конкретный тег (не latest)
☐ Или digest sha256:... для полной воспроизводимости

Безопасность:
☐ runAsNonRoot: true (где возможно)
☐ runAsUser: конкретный UID
☐ readOnlyRootFilesystem: true (+ emptyDir для tmp)

Сеть:
☐ Service создан для каждого Deployment/StatefulSet
☐ Ingress настроен для внешнего доступа

Хранилище:
☐ PVC создан для stateful данных
☐ StatefulSet использует volumeClaimTemplates (для масштабирования)
```

---

## Что остаётся прежним

После конвертации не нужно переписывать:

- Образы — те же OCI-образы, те же реестры
- Конфигурация через environment variables — тот же принцип, только источник (Secret)
- Порты и маппинги — те же номера портов
- Команды и entrypoint — те же
- Dockerfile — не меняется
