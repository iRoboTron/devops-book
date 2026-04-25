# Приложение A: Шпаргалка kubectl

| Команда | Назначение |
|---------|-----------|
| `kubectl get pods` | Список Pod'ов |
| `kubectl get pods -o wide` | Pod'ы с IP и нодой |
| `kubectl describe pod NAME` | Детали + Events |
| `kubectl logs NAME` | Логи |
| `kubectl exec -it NAME -- bash` | Войти внутрь |
| `kubectl apply -f FILE` | Применить манифест |
| `kubectl delete -f FILE` | Удалить по манифесту |
| `kubectl get all -n NS` | Всё в namespace |
| `kubectl describe service NAME` | Проверить selector и endpoints |
| `kubectl get pvc` | Список PVC |
| `kubectl describe pvc NAME` | Почему PVC не Bound |
| `kubectl get storageclass` | Доступные StorageClass |
| `kubectl port-forward pod/NAME 8080:8000` | Пробросить порт |
| `kubectl rollout status deploy/NAME` | Статус обновления |
| `kubectl rollout history deploy/NAME` | История ревизий |
| `kubectl rollout undo deploy/NAME` | Откат |
| `kubectl scale deploy NAME --replicas=5` | Масштабировать |
| `kubectl get namespaces` | Список namespace |
| `kubectl get events --sort-by='.lastTimestamp'` | Последние события |

# Приложение B: Готовые манифесты

## Минимальный Deployment + Service

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0
        ports:
        - containerPort: 8000
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
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8000
    nodePort: 30080
```

## PostgreSQL с PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pgdata
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
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
        env:
        - name: POSTGRES_PASSWORD
          value: "password"
        volumeMounts:
        - name: pgdata
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: pgdata
        persistentVolumeClaim:
          claimName: pgdata
```

# Приложение C: Диагностика

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `CrashLoopBackOff` | Контейнер падает | `kubectl logs --previous`, проверить команду |
| `ImagePullBackOff` | Образ не найден | Проверь имя образа, доступ к registry |
| `Pending` | Нет ресурсов | `kubectl describe pod`, Events |
| `PVC Pending` | Нет StorageClass | `kubectl describe pvc`, проверить `storageClassName` |
| Service не отвечает | Labels не совпадают | Проверь selector labels Pod'ов |
| `OOMKilled` | Превышен memory limit | Увеличь limits или оптимизируй приложение |
| `ErrImagePull` | Нет доступа к registry | Проверь imagePullSecrets |
