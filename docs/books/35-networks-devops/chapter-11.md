# Глава 11: Kubernetes networking — CNI, Service, Ingress

## Что вы узнаете

- Как Kubernetes организует сеть между подами через CNI
- Разница между ClusterIP, NodePort, LoadBalancer
- Что такое Ingress и зачем он нужен
- Как диагностировать сетевые проблемы в K8s

**Цель главы:** когда под не достучался до сервиса, вы знаете почему и как исправить.

---

## Подготовка — Kind

Для примеров потребуется локальный K8s-кластер. Рекомендуем Kind (Kubernetes in Docker):

```bash
# Установка Kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/

# Создать кластер
kind create cluster

# Проверить
kubectl cluster-info
kubectl get nodes
```

---

## 1. Pod networking и CNI

### Основной принцип

В Kubernetes каждый Pod получает **уникальный IP-адрес** из pod CIDR. Поды общаются напрямую без NAT — независимо от того, на какой ноде они запущены.

```
Нода 1 (192.168.1.10)         Нода 2 (192.168.1.11)
┌────────────────────────┐    ┌────────────────────────┐
│ Pod A: 10.244.1.2      │    │ Pod C: 10.244.2.2      │
│ Pod B: 10.244.1.3      │◄──►│ Pod D: 10.244.2.3      │
└────────┬───────────────┘    └────────┬───────────────┘
         │                             │
         └──────────┬──────────────────┘
                    │
         CNI overlay (VXLAN / BGP / etc.)
```

### CNI (Container Network Interface)

CNI — стандарт, определяющий как контейнерная среда (K8s) настраивает сеть для Pod'ов.

**Как работает:** kubelet при создании Pod'а вызывает CNI-плагин. Плагин:

1. Создаёт veth pair (как Docker)
2. Назначает IP из pod CIDR
3. Настраивает маршрутизацию

### Популярные CNI-плагины

| Плагин | Тип | Особенности |
|--------|-----|-------------|
| **Flannel** | Overlay (VXLAN) | Простой, настройка одной командой |
| **Calico** | BGP / IPIP | Network Policies, производительность |
| **Cilium** | eBPF | Безопасность, observability, Hubble |
| **Weave** | Overlay | Простая установка, шифрование |

```bash
# Установка Calico
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27/manifests/calico.yaml

# Посмотреть CNI-поды
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Схема CNI на ноде

```
┌──────────────────────────────────────────┐
│               Нода                        │
│                                          │
│  ┌─────┐  ┌─────┐  ┌─────┐             │
│  │Pod A│  │Pod B│  │Pod C│             │
│  │eth0 │  │eth0 │  │eth0 │             │
│  └──┬──┘  └──┬──┘  └──┬──┘             │
│     │       │       │                   │
│  ┌──┴───────┴───────┴──┐                │
│  │      cni0 (bridge)   │               │
│  └──────────┬───────────┘               │
│             │                            │
│  ┌──────────┴───────────┐                │
│  │      eth0 (хост)     │ ◄── маршрут до │
│  └──────────────────────┘     pod CIDR   │
└──────────────────────────────────────────┘
```

### Важные факты

- Pod'ы видят друг друга по IP напрямую (без NAT)
- Каждый Pod имеет свой network namespace
- CNI-плагин отвечает за маршрутизацию между нодами

```bash
# Посмотреть CIDR подов
kubectl get nodes -o jsonpath='{.items[*].spec.podCIDR}'

# Посмотреть IP подов
kubectl get pods -o wide

# Залогиниться в под
kubectl exec -it mypod -- ip addr
```

---

## 2. Service — стабильный адрес для набора подов

### Зачем нужен Service

Pod'ы эфемерны: они создаются, удаляются, пересоздаются с новыми IP. Service даёт стабильную точку входа (ClusterIP), которая распределяет трафик между подами по selector'у.

### Типы Service

| Тип | IP/Port | Доступность | Пример |
|-----|---------|-------------|--------|
| **ClusterIP** | Виртуальный IP внутри кластера | Только внутри кластера | Бэкенд-сервисы |
| **NodePort** | ClusterIP + порт на каждой ноде | Снаружи по nodeIP:nodePort | Тестирование, деплой |
| **LoadBalancer** | ClusterIP + внешний балансировщик | Снаружи через LB | Продакшн |
| **ExternalName** | CNAME-запись | Внутри кластера | Алиас внешнего сервиса |

### Пример ClusterIP

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: myapp
  ports:
    - port: 80        # порт сервиса (ClusterIP:80)
      targetPort: 8080 # порт пода (Pod IP:8080)
  type: ClusterIP
```

```bash
# Создать деплоймент (для подов)
kubectl create deployment myapp --image=nginx --replicas=3

# Создать сервис
kubectl expose deployment myapp --port=80 --target-port=80

# Проверить
kubectl get svc
kubectl describe svc myapp

# Внутри кластера — доступ по имени сервиса
kubectl run test --image=alpine -it --rm -- sh
/ # wget -q -O- http://myapp:80
```

### Как работает ClusterIP — kube-proxy и iptables

Схема:

```
Клиент (другой под)
     │
     ▼
ClusterIP 10.96.0.1:80
     │
     ▼
kube-proxy (iptables / IPVS / eBPF)
     │
     ├──► Pod A (10.244.1.2:8080)
     ├──► Pod B (10.244.1.3:8080)
     └──► Pod C (10.244.2.2:8080)
```

```bash
# Проверить iptables правила kube-proxy
sudo iptables -t nat -L -n | grep my-service

# Если включён IPVS
sudo ipvsadm -Ln
```

> ☠️ **Осторожно:** ClusterIP доступен **только внутри кластера**. Снаружи (с хоста, из браузера) обратиться к ClusterIP напрямую нельзя.

### Пример NodePort

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service-nodeport
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080  # если не указать — K8s выберет случайный
```

```bash
# Создать NodePort
kubectl expose deployment myapp --type=NodePort --port=80

# Узнать порт
kubectl get svc myapp

# Доступ с ноды
curl http://localhost:30080

# Доступ с другой машины
curl http://<node-ip>:30080
```

### Пример LoadBalancer

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-lb
spec:
  type: LoadBalancer
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```

```bash
# В Kind: LoadBalancer без cloud-провайдера будет в состоянии <pending>
kubectl get svc myapp-lb

# MetalLB — решение для bare-metal LoadBalancer
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14/manifests/metallb-native.yaml
```

### Поток трафика (внешний доступ)

```
Браузер / клиент
     │
     ▼
LoadBalancer (внешний IP:80)
     │
     ▼
NodePort (каждая нода:30080)
     │
     ▼
kube-proxy → iptables DNAT
     │
     ▼
ClusterIP (10.96.0.1:80)
     │
     ▼
Pod (10.244.1.2:8080)
```

---

## 3. Ingress — HTTP-роутинг

### Зачем нужен Ingress

Если у вас 10 сервисов — создавать 10 LoadBalancer'ов расточительно. Ingress даёт:

- Один внешний LoadBalancer
- Маршрутизацию по Host и Path
- TLS-терминацию
- Virtual hosting

### Архитектура

```
Пользователь
     │
     ▼
DNS: app.example.com ──► LoadBalancer (внешний IP)
                             │
                             ▼
                        Ingress Controller
                        (nginx / traefik / haproxy)
                             │
                     ┌───────┴───────┐
                     │               │
                     ▼               ▼
                   Service A       Service B
                   app.example.com  api.example.com/v1
```

### Ingress Controller (обязательный компонент)

Ingress-ресурс — это только правила. **Ingress Controller** — компонент, который их реализует. Без него Ingress не работает.

```bash
# Установить NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10/manifests/deploy.yaml

# Проверить
kubectl get pods -n ingress-nginx
```

### Пример Ingress-ресурса

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
    - host: api.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: api-v1
                port:
                  number: 8080
          - path: /v2
            pathType: Prefix
            backend:
              service:
                name: api-v2
                port:
                  number: 8080
```

```bash
# Применить
kubectl apply -f ingress.yaml

# Проверить
kubectl get ingress
kubectl describe ingress myapp-ingress

# Обновить /etc/hosts для теста локально
echo "127.0.0.1 app.example.com api.example.com" | sudo tee -a /etc/hosts
```

> ☠️ **Осторожно:** без Ingress Controller kubectl apply на Ingress-ресурс не даст эффекта — он создаст ресурс, но маршрутизации не будет.

### TLS в Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-tls
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - app.example.com
      secretName: app-tls-secret
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

```bash
# Создать самоподписанный сертификат для теста
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt -subj "/CN=app.example.com"

kubectl create secret tls app-tls-secret --key=tls.key --cert=tls.crt
```

### Сравнение Service vs Ingress

| | ClusterIP | NodePort | LoadBalancer | Ingress |
|---|---|---|---|---|
| L4/L7 | L4 | L4 | L4 | L7 (HTTP/HTTPS) |
| Внешний доступ | Нет | Да | Да | Да |
| Один IP на сервис | Да | Да | Да | Нет (один на все) |
| TLS | Нет | Нет | На LB | Да |
| Virtual hosting | Нет | Нет | Нет | Да |
| Сложность | Низкая | Низкая | Средняя | Выше |

---

## 4. Диагностика K8s networking

### Базовые команды

```bash
# Статус подов
kubectl get pods -o wide

# Статус сервисов
kubectl get svc
kubectl get svc -o wide

# Детали сервиса
kubectl describe svc my-service

# Endpoints (IP:Port подов за сервисом)
kubectl get endpoints my-service

# Проверить CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
```

### Диагностика из подов

```bash
# Запустить debug-под
kubectl run debug --image=busybox --restart=Never -it --rm -- sh

# Внутри debug-пода:
# DNS
nslookup my-service
nslookup kubernetes.default.svc.cluster.local

# HTTP
wget -q -O- http://my-service:80
wget -q -O- http://10.96.0.1  # ClusterIP kubernetes

# Сеть
ip addr
ip route

# Связность
ping 8.8.8.8
```

### Диагностика Endpoints

Самая частая проблема — пустые Endpoints:

```bash
# Есть поды?
kubectl get pods --selector=app=myapp

# Совпадает selector?
kubectl describe svc my-service
# В выводе: поле "Selector: app=myapp"

# Какие Endpoints?
kubectl get endpoints my-service
```

Если `kubectl get endpoints` показывает `<none>`:

1. Проверьте, что поды с лейблом `app=myapp` существуют и Ready
2. Проверьте, что targetPort в сервисе совпадает с containerPort в поде
3. Проверьте, что поды не в Pending/CrashLoopBackOff

### Диагностика CoreDNS

```bash
# Поды CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Логи
kubectl logs -n kube-system -l k8s-app=kube-dns

# Тест DNS
kubectl run dns-test --image=busybox -it --rm -- \
  nslookup kubernetes.default.svc.cluster.local

# Если DNS не отвечает — проверить сервис
kubectl get svc -n kube-system kube-dns
```

### Проверка Network Policy

```bash
# Есть ли NetworkPolicy, блокирующие трафик?
kubectl get networkpolicies --all-namespaces

# Детали
kubectl describe networkpolicy -n default

# Временно убрать политику
kubectl delete networkpolicy --all
```

### Продвинутая диагностика

```bash
# Запуск netshoot-контейнера
kubectl run netshoot --image=nicolaka/netshoot -it --rm -- bash

# В netshoot доступны:
#   tcpdump, curl, ping, dig, nslookup, netstat, ss
#   iperf, iftop, traceroute
tcpdump -i eth0
```

---

## Типичные ошибки

> ☠️ **Ошибка 1: пустые Endpoints (selector не совпадает)**

Симптом: `kubectl get endpoints my-service` показывает `<none>`.

Причина: selector в сервисе не соответствует лейблам на подах.

```bash
kubectl describe svc my-service   # Selector: app=myapp
kubectl get pods --show-labels    # Нужен app=myapp
```

> ☠️ **Ошибка 2: ClusterIP недоступен снаружи**

Симптом: curl к ClusterIP с хоста не работает.

Причина: ClusterIP — виртуальный IP, маршрутизируемый только внутри кластера (kube-proxy). Снаружи использовать NodePort, LoadBalancer или Ingress.

Решение:

```bash
# Сменить тип на NodePort
kubectl edit svc my-service # type: NodePort

# Или создать порт-форвард
kubectl port-forward svc/my-service 8080:80
```

> ☠️ **Ошибка 3: CoreDNS не работает**

Симптом: `nslookup my-service` возвращает `server can't find my-service`.

Причина: CoreDNS поды не запущены, не настроен upstream DNS, или сетевой плагин не работает.

```bash
# Проверить поды
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Проверить логи
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20
```

> ☠️ **Ошибка 4: нет Ingress Controller**

Симптом: `kubectl get ingress` показывает ресурс, но трафик не идёт.

Решение: установите Ingress Controller.

```bash
# Для NGINX:
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10/manifests/deploy.yaml

# Проверить
kubectl get pods -n ingress-nginx
```

> ☠️ **Ошибка 5: NetworkPolicy блокирует трафик**

Симптом: поды в одном namespace не пингуются, хотя сервис и endpoints корректны.

Решение: проверить NetworkPolicy. По умолчанию в K8s трафик разрешён, но если хотя бы одна NetworkPolicy существует — применяется white-list подход.

```bash
kubectl get networkpolicies --all-namespaces
kubectl describe networkpolicy -n default my-policy
```

---

## Чек-лист

- [ ] Поды в статусе Running, а не Pending/CrashLoopBackOff
- [ ] Endpoints сервиса не пустые: `kubectl get endpoints my-service`
- [ ] Selector сервиса совпадает с labels подов
- [ ] targetPort в сервисе совпадает с containerPort в поде
- [ ] CoreDNS работает: `nslookup kubernetes.default.svc.cluster.local` успешен
- [ ] Для внешнего доступа используется NodePort/LoadBalancer/Ingress (не ClusterIP)
- [ ] Ingress Controller установлен (если используется Ingress-ресурс)
- [ ] Network Policies не блокируют трафик (или явно разрешают)
- [ ] `kubectl port-forward` работает для теста
- [ ] CNI-плагин работает (поды в `kube-system` в статусе Running)

---

## Попробуйте сами

### Задание 1: Сервис и Endpoints

```bash
# 1. Создайте деплоймент с 3 репликами
kubectl create deployment web --image=nginx --replicas=3

# 2. Создайте ClusterIP-сервис
kubectl expose deployment web --port=80 --target-port=80

# 3. Проверьте Endpoints
kubectl get endpoints web

# 4. Масштабируйте до 5 реплик
kubectl scale deployment web --replicas=5

# 5. Проверьте Endpoints снова
kubectl get endpoints web -w  # watch mode
```

**Вопрос:** как изменились Endpoints после масштабирования?

---

### Задание 2: Ingress с двумя сервисами

Создайте Ingress с двумя правилами:

| Host | Path | Backend Service |
|------|------|-----------------|
| `app.local` | `/` | web (nginx:80) |
| `app.local` | `/api` | api (nginx:8080) |

```yaml
# 1. Два деплоймента
kubectl create deployment web --image=nginx --replicas=2
kubectl create deployment api --image=nginx --replicas=2

# 2. Два сервиса
kubectl expose deployment web --port=80
kubectl expose deployment api --port=8080 --target-port=80

# 3. Ingress-ресурс
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: app.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8080
```

**Бонус:** добавьте TLS с самоподписанным сертификатом.

---

### Задание 3: Диагностика — найдите проблему

Дано:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: broken-service
spec:
  selector:
    app: backend
  ports:
    - port: 80
      targetPort: 8080
```

```bash
kubectl get pods --show-labels
# NAME                     LABELS
# backend-7d9f5c6b8-abc12   app=backend
# backend-7d9f5c6b8-def34   app=backend

kubectl get endpoints broken-service
# NAME             ENDPOINTS   AGE
# broken-service   <none>      1m
```

**Вопрос:** Endpoints пустые, хотя поды с `app=backend` есть. Найдите причину и исправьте.

**Подсказка:** проверьте containerPort в поде и targetPort в сервисе.

Ожидаемое решение:

```bash
# Проверить containerPort
kubectl describe pod backend-7d9f5c6b8-abc12 | grep Ports

# Если containerPort = 80, а targetPort = 8080 — несовпадение
# Исправить targetPort
kubectl edit svc broken-service
# targetPort: 8080 → targetPort: 80

# Или пересоздать
kubectl delete svc broken-service
kubectl expose deployment backend --port=80 --target-port=80
```

---
