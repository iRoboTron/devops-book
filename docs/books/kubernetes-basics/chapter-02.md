# Глава 2: Deployment — управление репликами

> **Запомни:** Deployment = контроллер который следит за Pod'ами. Убей Pod → Deployment поднимет новый.

---

## 2.1 Манифест

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
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
        image: python:3.12-slim
        command: ["python", "-m", "http.server", "8000"]
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
```

---

## 2.2 Самовосстановление

```bash
kubectl apply -f deployment.yaml
kubectl get pods
# myapp-xxx  Running
# myapp-yyy  Running
# myapp-zzz  Running

# Убить один Pod
kubectl delete pod myapp-xxx

# Наблюдать в watch:
# myapp-xxx  Terminating
# myapp-aaa  Pending → Running  ← новый!
```

Deployment заметил что Pod'ов стало 2 вместо 3 → создал новый.

---

## 2.3 Масштабирование

```bash
kubectl scale deployment myapp --replicas=5
kubectl get pods
# 5 Pod'ов!
```

---

## 2.4 Rolling update

```bash
kubectl set image deployment/myapp app=python:3.11-slim
kubectl rollout status deployment/myapp
```

K8s обновляет Pod'ы по одному без даунтайма.

---

## 📝 Упражнения

### Упражнение 2.1: Самовосстановление
**Задача:**
1. Создай Deployment с 3 репликами
2. `watch kubectl get pods` — запусти в другом терминале
3. Убей один Pod — новый поднялся?

### Упражнение 2.2: Масштабирование
**Задача:**
1. `kubectl scale deployment myapp --replicas=5`
2. 5 Pod'ов?
3. `kubectl scale deployment myapp --replicas=2`
4. 2 Pod'а остались?

---

## 📋 Чеклист главы 2

- [ ] Я могу создать Deployment
- [ ] Я вижу самовосстановление (убил → поднялся)
- [ ] Я могу масштабировать (`kubectl scale`)
- [ ] Я понимаю rolling update

**Всё отметил?** Переходи к Главе 3 — Service.
