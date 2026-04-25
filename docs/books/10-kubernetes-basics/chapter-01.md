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

Что ты должен увидеть после `kubectl apply -f pod.yaml`:

```bash
kubectl get pods
```

```text
NAME      READY   STATUS    RESTARTS   AGE
myapp     1/1     Running   0          12s
```

Что значат колонки:

- `READY 1/1` — 1 из 1 контейнеров готов
- `STATUS Running` — Pod работает
- `RESTARTS 0` — контейнер ни разу не перезапускался

Более подробный вывод:

```bash
kubectl get pods -o wide
```

```text
NAME    READY   STATUS    RESTARTS   AGE   IP           NODE
myapp   1/1     Running   0          2m    10.42.0.15   k3s-node1
```

Здесь уже видно:

- IP Pod внутри кластера
- на какой ноде он запущен

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

## 1.4 Диагностика: Pod не запускается

Три самых частых статуса проблемного Pod:

```text
NAME    READY   STATUS             RESTARTS
myapp   0/1     CrashLoopBackOff   4
```

Что делать: `kubectl logs myapp` — приложение падает при старте.

```text
NAME    READY   STATUS             RESTARTS
myapp   0/1     ImagePullBackOff   0
```

Что делать: `kubectl describe pod myapp` — неверный образ или нет доступа к registry.

```text
NAME    READY   STATUS    RESTARTS
myapp   0/1     Pending   0
```

Что делать: `kubectl describe pod myapp` → `Events` → часто недостаточно ресурсов на ноде.

Пример вывода `kubectl describe pod myapp`:

```text
Events:
  Type     Reason     Message
  ----     ------     -------
  Warning  Failed     Failed to pull image "ghcr.io/user/myapp:v1": not found
  Warning  BackOff    Back-off pulling image "ghcr.io/user/myapp:v1"
```

> **Правило:** При любой проблеме с Pod сначала `kubectl describe pod NAME`.
> Смотри секцию `Events` внизу. Там обычно есть объяснение.

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

### Упражнение 1.3: Сломанный Pod
**Задача:**
1. Замени образ на несуществующий
2. `kubectl get pods` — видишь `ImagePullBackOff`?
3. `kubectl describe pod myapp` — нашёл ошибку в `Events`?
4. Исправь образ и верни Pod в `Running`

---

## 📋 Чеклист главы 1

- [ ] Я понимаю что такое Pod
- [ ] Я могу создать, посмотреть, удалить Pod
- [ ] Я знаю что Pod не поднимается сам после удаления

**Всё отметил?** Переходи к Главе 2 — Deployment.
