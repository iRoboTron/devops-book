# Глава 8: kubectl шпаргалка (справочник)

> Обращайся по необходимости. Не читай подряд.

---

| Команда | Назначение |
|---------|-----------|
| `kubectl get pods` | Список Pod'ов |
| `kubectl get pods -o wide` | С IP и Node |
| `kubectl get all -n NS` | Всё в namespace |
| `kubectl describe pod NAME` | Детали + Events |
| `kubectl logs NAME` | Логи |
| `kubectl logs -f NAME` | Следить за логами |
| `kubectl exec -it NAME -- bash` | Войти внутрь |
| `kubectl apply -f FILE` | Применить манифест |
| `kubectl delete -f FILE` | Удалить по манифесту |
| `kubectl port-forward pod/NAME 8080:8000` | Пробросить порт |
| `kubectl rollout status deploy/NAME` | Статус обновления |
| `kubectl rollout history deploy/NAME` | История ревизий |
| `kubectl rollout undo deploy/NAME` | Откат |
| `kubectl scale deploy NAME --replicas=5` | Масштабировать |
| `kubectl get events --sort-by='.lastTimestamp'` | События |
| `kubectl config set-context --current -n NS` | Сменить namespace |

---

# Глава 9: Rolling update и откат

> **Запомни:** Rolling update = обновление без даунтайма. K8s обновляет Pod'ы по одному.

---

## 9.1 Обновить

```bash
kubectl set image deployment/myapp app=ghcr.io/user/myapp:v2
kubectl rollout status deployment/myapp
```

```text
Waiting for deployment "myapp" rollout to finish: 1 out of 3 new replicas updated...
Waiting for deployment "myapp" rollout to finish: 2 out of 3 new replicas updated...
Waiting for deployment "myapp" rollout to finish: 1 old replicas are pending termination...
deployment "myapp" successfully rolled out
```

Kubernetes обновляет Pod'ы по одному: сначала поднимает новый, потом удаляет старый. Это и даёт rolling update без даунтайма.

## 9.2 История

```bash
kubectl rollout history deployment/myapp
```

```text
REVISION  CHANGE-CAUSE
1         kubectl apply --filename=deployment.yaml
2         kubectl set image deployment/myapp app=ghcr.io/user/myapp:v2
```

## 9.3 Откат

```bash
kubectl rollout undo deployment/myapp
kubectl rollout undo deployment/myapp --to-revision=2
```

---

# Глава 10: Ресурсы — limits, requests

> **Запомни:** Pod без limits съест всю ноду. Всегда ставь resources.

---

## 10.1 requests vs limits

```yaml
resources:
  requests:
    cpu: "50m"       # 50 millicores = 1/20 ядра (5% CPU)
    memory: "64Mi"   # 64 мегабайта
  limits:
    cpu: "100m"      # максимум 1/10 ядра
    memory: "128Mi"  # превышение = Pod убит (OOMKilled)
```

`requests` нужны scheduler'у: он решает, на какую ноду можно поставить Pod. `limits` ограничивают максимум, который контейнер может съесть.

## 10.2 OOM kill

Pod превысил memory limits → K8s убил и перезапустил.

```bash
kubectl get pods
# myapp-xxx  OOMKilled  →  Restarting
```

---

## 10.3 Liveness и Readiness probes

Без probes Kubernetes начинает слать трафик в Pod сразу после старта контейнера, даже если приложение ещё не поднялось.

```yaml
containers:
- name: app
  livenessProbe:
    httpGet:
      path: /health
      port: 8000
    initialDelaySeconds: 10
    periodSeconds: 30
    failureThreshold: 3

  readinessProbe:
    httpGet:
      path: /ready
      port: 8000
    initialDelaySeconds: 5
    periodSeconds: 10
```

Разница:

- `livenessProbe` — если приложение зависло или перестало отвечать, Pod перезапустить
- `readinessProbe` — если приложение ещё не готово, убрать Pod из Service и не слать трафик

Это особенно важно для API и приложений, которые стартуют несколько секунд и зависят от БД или миграций.

---

## 📋 Чеклист глав 8-10

- [ ] Я знаю основные команды kubectl
- [ ] Я могу сделать rolling update
- [ ] Я могу откатить к предыдущей версии
- [ ] Я ставлю resources requests и limits каждому Pod
- [ ] Я понимаю что будет при OOM kill
- [ ] Я понимаю разницу между livenessProbe и readinessProbe

**Всё отметил?** Книга 10 завершена!
