# Глава 2: HPA — автомасштабирование

> **Проблема:** 1 реплика всегда. Трафик вырос — приложение не справляется.

---

## 2.1 Что делает HPA

```
CPU > 70%:  2 реплики → 4 реплики (автоматически)
CPU < 30%:  4 реплики → 2 реплики (через 5 минут)
```

---

## 2.2 Установка metrics-server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Для k3s — уже встроен
kubectl top pods
```

---

## 2.3 Манифест HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

```bash
kubectl apply -f hpa.yaml
kubectl get hpa
```

---

## 2.4 Обязательно: resources.requests

Без `requests` HPA не работает:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"
```

---

## 2.5 Тест нагрузки

```bash
# Генератор нагрузки
kubectl run loadgen --image=busybox --restart=Never -- \
  sh -c "while true; do wget -q -O- http://myapp-svc/; done"

# Наблюдать
watch kubectl get hpa

# Убрать нагрузку
kubectl delete pod loadgen
```

---

## 📋 Чеклист

- [ ] metrics-server установлен (`kubectl top pods` работает)
- [ ] HPA создан и показывает текущие реплики
- [ ] resources.requests заданы в Deployment
- [ ] При нагрузке реплики растут

**Переходи к Главе 3 — Resources.**
