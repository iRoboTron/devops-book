# Глава 1: Ingress — HTTPS по домену

> **Проблема:** NodePort с портом 30080 — не для продакшна. Нужен домен и HTTPS.

---

## 1.1 NodePort vs Ingress

| NodePort | Ingress |
|----------|---------|
| Порт 30080 | Домен myapp.ru |
| Только HTTP | HTTPS автоматически |
| Один сервис/порт | Много сервисов на одном порту |
| Не для продакшна | Для продакшна |

```
NodePort:              Ingress:
Client → :30080        Client → myapp.ru:443
                            ↓
                       [ Ingress Controller ]
                            ↓
                       [ Service: myapp ]
```

---

## 1.2 Ingress Controller

Ingress = правила роутинга (YAML).
Ingress Controller = программа которая применяет правила.

Для k3s встроен Traefik. Можно заменить на Nginx:

```bash
# Traefik уже есть в k3s — используем его
kubectl get pods -n kube-system | grep traefik
```

---

## 1.3 Манифест Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
spec:
  ingressClassName: traefik
  rules:
  - host: myapp.local
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

```bash
kubectl apply -f ingress.yaml
kubectl get ingress
```

```text
NAME            CLASS     HOSTS        ADDRESS         PORTS
myapp-ingress   traefik   myapp.local  192.168.1.100   80
```

Если `ADDRESS` пустой, Ingress Controller не найден или не запустился:

```bash
kubectl get pods -n kube-system | grep -E "traefik|ingress"
```

---

## 1.4 Локальный тест

```bash
# /etc/hosts
echo "127.0.0.1 myapp.local" | sudo tee -a /etc/hosts

# Тест
curl -H "Host: myapp.local" http://localhost
```

---

## 1.5 Несколько сервисов

```yaml
spec:
  rules:
  - host: myapp.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-svc
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
```

`/` → frontend, `/api` → api. Один домен, много сервисов.

---

## 1.6 Тестирование без реального домена

Для lab не нужен настоящий DNS. Можно имитировать домен:

```bash
curl -H "Host: myapp.local" http://192.168.1.100
```

Или добавить запись в `/etc/hosts` на своей машине:

```bash
echo "192.168.1.100 myapp.local" | sudo tee -a /etc/hosts
curl http://myapp.local
```

---

## 1.7 TLS через cert-manager

Установка cert-manager:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
kubectl get pods -n cert-manager
```

```yaml
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

В Ingress добавить:

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

## 1.8 TLS

Для продакшна — cert-manager + Let's Encrypt:

```yaml
spec:
  tls:
  - hosts:
    - myapp.ru
    secretName: myapp-tls
  rules:
  - host: myapp.ru
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

cert-manager автоматически обновляет сертификат.

> **Для обучения:** self-signed сертификат достаточен.
> cert-manager — когда есть реальный домен.

---

## 📝 Упражнения

### 1.1: Создать Ingress
1. Создай Ingress для своего сервиса
2. Добавь myapp.local в /etc/hosts
3. `curl -H "Host: myapp.local" http://localhost` — работает?

### 1.2: Два сервиса
1. Создай второй сервис
2. Добавь path `/api` в Ingress
3. Проверь оба пути

### 1.3: Тест без DNS
1. Протестируй Ingress через `curl -H "Host: myapp.local"`
2. Добавь запись в `/etc/hosts`
3. `curl http://myapp.local` — работает?

---

## 📋 Чеклист

- [ ] Я понимаю разницу NodePort vs Ingress
- [ ] Я могу создать Ingress для одного сервиса
- [ ] Я могу добавить второй сервис по path
- [ ] Я знаю что Ingress Controller должен быть установлен

**Переходи к Главе 2 — HPA.**
