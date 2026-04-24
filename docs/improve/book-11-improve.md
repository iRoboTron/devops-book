# Инструкция агенту: улучшение книги 11 «Kubernetes продвинутый + Helm»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/11-kubernetes-advanced/
```

Книга: 1050 строк. По структуре лучше книги 10 — главы 2 (HPA), 8-9 (Helm) содержат реальные примеры и упражнения. Слабые места: нет вывода команд в главах 1, 3, 5, 6, нет способа протестировать NetworkPolicy, StatefulSet не объяснён (используется в книге 10 главе 7 без объяснения).

---

## Что НЕ трогать

- Главы 2 (HPA), 7, 8, 9 (Helm) — они хорошие
- Чеклисты
- Существующие YAML-манифесты

---

## Задачи по главам

---

### Глава 1 (`chapter-01.md`) — Ingress

**Проблема:** После `kubectl apply -f ingress.yaml` нет вывода — непонятно что должно получиться.

**Добавить** в раздел 1.3 вывод после применения:

```bash
kubectl get ingress
```

```
NAME            CLASS    HOSTS        ADDRESS         PORTS
myapp-ingress   traefik  myapp.local  192.168.1.100   80
```

Если ADDRESS пустой — Ingress Controller не нашёл или не запустился:
```bash
kubectl get pods -n kube-system | grep -E "traefik|ingress"
```

**Добавить** раздел **1.6 «Тестирование без реального домена»** (для lab):

```bash
# Имитировать домен через /etc/hosts или через заголовок Host
curl -H "Host: myapp.local" http://192.168.1.100

# Или добавить в /etc/hosts (только на своей машине)
echo "192.168.1.100 myapp.local" | sudo tee -a /etc/hosts
curl http://myapp.local
```

**Добавить** раздел **1.7 «TLS через cert-manager»** (краткий):

```bash
# Установить cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Проверить
kubectl get pods -n cert-manager
```

```yaml
# ClusterIssuer для Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your@email.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
```

Добавить в Ingress манифест:
```yaml
annotations:
  cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - myapp.ru
    secretName: myapp-tls
```

---

### Глава 2 (`chapter-02.md`) — HPA

**Глава хорошая.** Одно дополнение — показать вывод `kubectl get hpa` при работающей нагрузке:

**Добавить** в раздел 2.5 что видно в `watch kubectl get hpa`:

```
NAME        REFERENCE         TARGETS   MINPODS   MAXPODS   REPLICAS
myapp-hpa   Deployment/myapp  78%/70%   2         10        4
            ↑ CPU выше 70%             ↑ увеличил до 4
```

После остановки нагрузки (через ~5 минут):
```
NAME        REFERENCE         TARGETS   MINPODS   MAXPODS   REPLICAS
myapp-hpa   Deployment/myapp  12%/70%   2         10        2
            ↑ CPU упал                  ↑ уменьшил обратно до 2
```

---

### Глава 3 (`chapter-03.md`) — Resources

**Глава хорошая** — LimitRange и ResourceQuota объяснены. Добавить одно:

**Добавить** в раздел 3.2 проверку ResourceQuota — что происходит при превышении:

```bash
kubectl describe resourcequota -n prod
```

```
Name:     prod-quota
Resource  Used  Hard
--------  ----  ----
cpu       450m  500m    ← близко к лимиту
memory    200Mi 512Mi
pods      4     10
```

Попытка создать Pod при исчерпанном лимите:
```
Error: pods "myapp-xxx" is forbidden: exceeded quota: prod-quota,
       requested: cpu=100m, used: cpu=450m, limited: cpu=500m
```

---

### Глава 4 (`chapter-04.md`) — StatefulSet

**Глава нуждается в проверке.** Если StatefulSet ещё не описан — добавить главу:

StatefulSet используется в книге 10 (глава 7) для PostgreSQL, но нигде не объяснён. Добавить раздел **«Когда StatefulSet вместо Deployment»**:

| | Deployment | StatefulSet |
|--|------------|-------------|
| Порядок создания | Случайный | Строгий (0, 1, 2...) |
| Имена Pod'ов | Случайные суффиксы | Предсказуемые: `pg-0`, `pg-1` |
| PVC | Общий или без | Свой PVC на каждый Pod |
| Применение | Stateless apps | БД, очереди, кластерные сервисы |

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        volumeMounts:
        - name: pgdata
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: pgdata
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 5Gi
```

Ключевое: `volumeClaimTemplates` — каждый Pod получает свой PVC (`pgdata-postgres-0`, `pgdata-postgres-1`).

---

### Глава 5 (`chapter-05.md`) — NetworkPolicy

**Проблема:** Нет способа проверить что политика работает.

**Добавить** раздел **5.4 «Как протестировать NetworkPolicy»:**

```bash
# Запустить тестовый Pod с label app=api (разрешён)
kubectl run test-allowed --image=curlimages/curl \
  --labels="app=api" --rm -it --restart=Never -n prod \
  -- curl http://postgres-svc:5432
# Должен получить ответ от PostgreSQL (или connection refused — это нормально,
# главное не "connection timed out")

# Запустить Pod без label (должен быть заблокирован)
kubectl run test-blocked --image=curlimages/curl \
  --rm -it --restart=Never -n prod \
  -- curl --max-time 5 http://postgres-svc:5432
```

Разница в ответе:
- `connection refused` — пакет дошёл до PostgreSQL, тот отказал (политика пропустила — это нормально для TCP)
- `connection timed out` — пакет отброшен NetworkPolicy ✅

**Добавить** раздел **5.5 «Важно: поддержка CNI»:**

NetworkPolicy работает только если CNI-плагин её поддерживает. В k3s по умолчанию Flannel — **NetworkPolicy НЕ работает**. Нужен Calico или Cilium.

```bash
# Проверить CNI
kubectl get pods -n kube-system | grep -E "calico|cilium|flannel"

# Установить Calico для k3s
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.0/manifests/calico.yaml
```

---

### Глава 6 (`chapter-06.md`) — RBAC

**Глава хорошая** — `kubectl auth can-i` показан. Добавить практический сценарий:

**Добавить** раздел **6.6 «Читатель только для monitoring»:**

```yaml
# Роль: только смотреть pods и logs
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-viewer
rules:
- apiGroups: [""]
  resources: ["pods", "nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
```

Это типичный кейс: дать доступ к логам DevOps-инженеру без права что-либо менять.

---

## Общий объём

Цель: 1600–1800 строк (сейчас 1050).

## Приоритет

1. Глава 4 (StatefulSet) — объяснить концепт, он используется в книге 10 без объяснений
2. Глава 5 (NetworkPolicy) — добавить тест и предупреждение про CNI
3. Глава 1 (Ingress) — вывод `kubectl get ingress` и cert-manager
4. Глава 3 (ResourceQuota) — что происходит при превышении

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-11-improve.md`*
