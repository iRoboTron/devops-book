# Глава 1: Pod — минимальная единица

> **Запомни:** Pod ≠ контейнер. Pod может содержать один или несколько контейнеров которые делят сеть и тома.

---

## 1.1 Что такое Pod

Pod — минимальная единица в K8s. Обычно один контейнер.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  labels:
    app: myapp
spec:
  containers:
  - name: app
    image: python:3.12-slim
    command: ["python", "-c", "print('hello')"]
```

---

## 1.2 Основные команды

```bash
kubectl apply -f pod.yaml     # создать
kubectl get pods               # список
kubectl get pods -o wide       # с IP и Node
kubectl describe pod myapp     # детали
kubectl logs myapp             # логи
kubectl logs -f myapp          # следить
kubectl exec -it myapp -- bash # зайти внутрь
kubectl delete pod myapp       # удалить
```

---

## 1.3 Pod не поднимается сам

```bash
kubectl delete pod myapp
kubectl get pods
# No resources found
```

Pod удалён и НЕ создался заново. Нет контроллера.

> **Запомни:** Pod не запускают напрямую в продакшне.
> Используй Deployment — он следит за Pod'ами.

---

## 📝 Упражнения

### Упражнение 1.1: Создать Pod
**Задача:**
1. Создай pod.yaml
2. `kubectl apply -f pod.yaml`
3. `kubectl get pods` — создан?
4. `kubectl logs myapp` — видишь "hello"?

### Упражнение 1.2: Удалить
**Задача:**
1. `kubectl delete pod myapp`
2. `kubectl get pods` — Pod не поднялся сам?

---

## 📋 Чеклист главы 1

- [ ] Я понимаю что такое Pod
- [ ] Я могу создать, посмотреть, удалить Pod
- [ ] Я знаю что Pod не поднимается сам после удаления

**Всё отметил?** Переходи к Главе 2 — Deployment.
