# Инструкция агенту: улучшение книги 10 «Kubernetes основы»

## Контекст

Книга находится в директории:
```
/home/adelfos/Documents/lessons/dev-ops/docs/books/10-kubernetes-basics/
```

Файлы: `chapter-01.md` … `chapter-08.md` (внимание: в файле chapter-08.md фактически три главы: 8, 9, 10), `appendix-a.md`

Эталон: книга 08 (Terraform) — 2930 строк, реальный вывод команд, отдельная глава на каждую тему. Книга 10 сейчас: **1048 строк**, главы по 56–107 строк. Самая короткая книга во всём курсе 2.0.

**Две структурные проблемы:**
1. Нет вывода команд — читатель не знает что должен увидеть в терминале
2. Нет раздела диагностики — CrashLoopBackOff, Pending, ImagePullBackOff встретятся при первом же деплое, но книга молчит

---

## Что НЕ трогать

- Нумерацию и названия существующих разделов
- Манифесты YAML — они правильные
- Чеклисты
- Упражнения (только дополнять, не убирать)

---

## Задачи по каждой главе

---

### Глава 1 (`chapter-01.md`) — Pod

**Проблема:** Команды перечислены без вывода. Читатель не знает как выглядит работающий Pod и как выглядит сломанный.

**Добавить** в раздел 1.2 вывод команд:

```bash
kubectl get pods
```

```
NAME      READY   STATUS    RESTARTS   AGE
myapp     1/1     Running   0          12s
```

Что значат колонки:
- `READY 1/1` — 1 из 1 контейнеров готов
- `STATUS Running` — Pod работает
- `RESTARTS 0` — ни разу не перезапускался

```bash
kubectl get pods -o wide
```

```
NAME    READY  STATUS   RESTARTS  AGE  IP           NODE
myapp   1/1    Running  0         2m   10.42.0.15   k3s-node1
```

**Добавить** раздел **1.4 «Диагностика: Pod не запускается»:**

Три самых частых статуса ошибок:

```
NAME    READY  STATUS             RESTARTS
myapp   0/1    CrashLoopBackOff   4
```
Что делать: `kubectl logs myapp` — приложение падает при старте.

```
NAME    READY  STATUS             RESTARTS
myapp   0/1    ImagePullBackOff   0
```
Что делать: `kubectl describe pod myapp` — неверный образ или нет доступа к registry.

```
NAME    READY  STATUS    RESTARTS
myapp   0/1    Pending   0
```
Что делать: `kubectl describe pod myapp` → Events → недостаточно ресурсов на ноде.

Пример вывода `kubectl describe pod myapp` в секции Events:

```
Events:
  Type     Reason     Message
  ----     ------     -------
  Warning  Failed     Failed to pull image "ghcr.io/user/myapp:v1": not found
  Warning  BackOff    Back-off pulling image "ghcr.io/user/myapp:v1"
```

> **Правило:** При любой проблеме с Pod — сначала `kubectl describe pod NAME`, смотри секцию Events внизу. Там объяснение.

---

### Глава 2 (`chapter-02.md`) — Deployment

**Проблема:** Rolling update упомянут в двух строках без вывода. Читатель не знает как это выглядит.

**Добавить** в раздел 2.4 вывод `kubectl rollout status`:

```bash
kubectl set image deployment/myapp app=python:3.11-slim
kubectl rollout status deployment/myapp
```

```
Waiting for deployment "myapp" rollout to finish: 1 out of 3 new replicas updated...
Waiting for deployment "myapp" rollout to finish: 2 out of 3 new replicas updated...
Waiting for deployment "myapp" rollout to finish: 1 old replicas are pending termination...
deployment "myapp" successfully rolled out
```

K8s обновляет по одному: сначала поднял новый Pod, потом убил старый.

**Добавить** раздел **2.5 «Откат»:**

```bash
kubectl rollout undo deployment/myapp
```

```
deployment.apps/myapp rolled back
```

```bash
kubectl rollout history deployment/myapp
```

```
REVISION  CHANGE-CAUSE
1         kubectl apply --filename=deployment.yaml
2         kubectl set image deployment/myapp app=python:3.11-slim
```

---

### Глава 3 (`chapter-03.md`) — Service

**Проблема:** Нет вывода `kubectl describe service` — непонятно как проверить что Service нашёл Pods.

**Добавить** в раздел 3.1 как проверить что Service нашёл нужные Pods:

```bash
kubectl describe service myapp-svc
```

```
Name:              myapp-svc
Selector:          app=myapp
Endpoints:         10.42.0.15:8000,10.42.0.16:8000,10.42.0.17:8000
                   ↑ три Pod'а нашлись
```

Если `Endpoints: <none>` — labels не совпадают. Проверить:

```bash
kubectl get pods --show-labels
# myapp-xxx  Running  app=myapp   ← должны совпадать с selector
```

**Добавить** раздел **3.4 «Тестировать Service изнутри кластера»:**

```bash
# Запустить временный Pod и проверить доступность Service
kubectl run test --image=curlimages/curl --rm -it --restart=Never \
  -- curl http://myapp-svc:80

# Ответ приложения означает что Service работает
```

---

### Глава 4 (`chapter-04.md`) — ConfigMap и Secret

**Проблема:** Нет упражнений (единственная глава без них). Нет объяснения как проверить что переменные попали в Pod.

**Добавить** раздел **4.4 «Проверить что переменные видны в Pod»:**

```bash
kubectl exec -it myapp-xxx -- env | grep DB_
```

```
DB_HOST=postgres-svc
DB_PORT=5432
DB_PASSWORD=password    ← Secret тоже виден как plaintext внутри Pod
```

Это подтверждает что `envFrom` работает.

**Добавить** упражнения:

```
### Упражнение 4.1: ConfigMap
1. Создай ConfigMap с APP_ENV=production
2. Подключи через envFrom
3. kubectl exec — переменная видна?

### Упражнение 4.2: Secret
1. kubectl create secret generic --from-literal=DB_PASSWORD=secret123
2. Подключи через envFrom
3. kubectl exec — DB_PASSWORD видна?
4. kubectl get secret myapp-secrets -o yaml — что видишь в data?
```

---

### Глава 5 (`chapter-05.md`) — Volume и PVC

**Проблема:** 66 строк — самая короткая содержательная глава. Нет объяснения `AccessModes` и `StorageClass`.

**Добавить** раздел **5.3 «AccessModes — что значат»:**

| AccessMode | Что значит | Типичное использование |
|---|---|---|
| `ReadWriteOnce` | Один Pod пишет | PostgreSQL, одиночные БД |
| `ReadOnlyMany` | Много Pod'ов читают | Shared assets |
| `ReadWriteMany` | Много Pod'ов пишут | NFS, distributed storage |

> **Правило:** Для PostgreSQL всегда `ReadWriteOnce` — БД не должна писаться с нескольких Pod'ов одновременно.

**Добавить** в раздел 5.2 что делать если PVC завис в Pending:

```bash
kubectl get pvc
# pgdata  Pending   # ← не Bound!
```

```bash
kubectl describe pvc pgdata
```

```
Events:
  Warning  ProvisioningFailed  storageclass.storage.k8s.io "standard" not found
```

Что делать: проверить доступные StorageClass:

```bash
kubectl get storageclass
```

В k3s по умолчанию есть `local-path`. Добавить `storageClassName: local-path` в PVC.

---

### Глава 6 (`chapter-06.md`) — Namespace

**Проблема:** 56 строк — минимальная. Нет объяснения системных namespace и DNS-формата.

**Добавить** раздел **6.4 «Системные namespace»:**

```bash
kubectl get namespaces
```

```
NAME              STATUS
default           Active    ← сюда попадает всё без -n
kube-system       Active    ← системные компоненты K8s
kube-public       Active    ← публичные ConfigMap
local-path-storage Active   ← StorageClass провайдер (k3s)
```

Не деплоить своё в `kube-system` — там работает K8s.

**Добавить** раздел **6.5 «DNS между namespace»:**

Сервис из одного namespace к другому:

```bash
# Из namespace dev обратиться к сервису в namespace prod
curl http://myapp-svc.prod.svc.cluster.local:80

# Формат: <service>.<namespace>.svc.cluster.local
```

Внутри одного namespace — просто `http://myapp-svc:80`.

---

### Глава 7 (`chapter-07.md`) — Деплой Python-приложения

**Глава хорошая** — хорошее сравнение docker-compose → K8s, полные манифесты. Нужно одно добавление.

**Добавить** в раздел 7.3 вывод после `kubectl apply`:

```bash
kubectl apply -f k8s/
kubectl get all -n myapp
```

```
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

**Добавить** раздел **7.4 «Проверить что приложение работает»:**

```bash
# Получить IP ноды
kubectl get nodes -o wide
# k3s-node1  192.168.1.100

# Открыть в браузере или curl
curl http://192.168.1.100:30080
```

---

### Глава 8 (`chapter-08.md`) — Шпаргалка + Главы 9, 10

**Проблема:** В одном файле три независимые темы. Переименовать не нужно — просто добавить содержание.

**Добавить в главу 9 (Rolling update)** реальный вывод rollout status (уже описан выше в гл.2 — сослаться или повторить).

**Добавить в главу 10 (Resources)** объяснение единиц:

```yaml
resources:
  requests:
    cpu: "50m"       # 50 millicores = 1/20 ядра (5% от CPU)
    memory: "64Mi"   # 64 мегабайта
  limits:
    cpu: "100m"      # максимум 1/10 ядра
    memory: "128Mi"  # превышение = Pod убит (OOMKilled)
```

**Добавить** раздел **«Liveness и Readiness probes»** в главу 10:

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
- `livenessProbe` — если упал, перезапустить Pod
- `readinessProbe` — если не готов, убрать из Service (не слать трафик)

Без probes K8s шлёт трафик в Pod сразу после старта, даже если приложение ещё не поднялось.

---

## Общий объём

Цель: 1800–2000 строк (сейчас 1048). Особое внимание на добавление реальных выводов команд — это главный дефицит книги.

## Приоритет

1. Глава 1 (Pod) — диагностика CrashLoopBackOff/Pending/ImagePullBackOff
2. Глава 2 (Deployment) — вывод rolling update
3. Глава 3 (Service) — `kubectl describe service`, тест изнутри кластера
4. Глава 4 (ConfigMap) — добавить упражнения
5. Глава 10 (Resources) — liveness/readiness probes, объяснение единиц

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-10-improve.md`*
*Проект: dev-ops / книга 10*
