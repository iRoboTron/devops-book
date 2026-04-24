# Глава 7: Kubernetes security basics

> **Запомни:** в Kubernetes ошибки доступа и конфигурации размножаются быстро: один неаккуратный manifest масштабируется на весь кластер.

---

## 7.1 Контекст и границы

Даже если у тебя пока нет production-кластера, стоит понимать namespaces, service accounts, RBAC, network policies, secrets, admission и pod security context.

Kubernetes усиливает последствия шаблонных ошибок: привилегированный контейнер, default service account, отсутствие resource limits и network policy быстро становятся системной проблемой.

Эта глава особенно полезна для тех, кто начинает работать с k8s или читает чужие манифесты и хочет понимать базовый security baseline.

---

## 7.2 Как выглядит риск

Типовые слабые места:
- поды запускаются от root и с broad privileges;
- используется default service account;
- RBAC роли слишком широкие;
- нет network policies;
- секреты лежат в манифестах или ConfigMap.

### Где особенно важно
- локальный k8s lab
- managed cluster
- internal platform

---

## 7.3 Что строит защитник

- отдельные namespaces по средам и командам;
- минимальные service accounts и RBAC;
- pod security context и отсутствие лишних привилегий;
- network policies;
- secret management и image policy.

### Практический результат главы
- ты понимаешь базовый security baseline для пода и namespace;
- умеешь читать manifest как набор прав и ограничений;
- можешь отличить учебный минимальный кластер от production-подхода.

```text
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true

automountServiceAccountToken: false
```

---

## 7.4 Практика

### Шаг 1: Прочитай manifest как policy
- проверь serviceAccountName, securityContext, volumes, hostPath и capabilities;
- отметь, что именно получает под.

```bash
rg -n "serviceAccountName|securityContext|hostPath|privileged|allowPrivilegeEscalation" k8s/ helm/ || true
```

### Шаг 2: Проверь RBAC и identities
- посмотри, какие role и clusterrole связаны с приложением;
- убедись, что поды не используют default service account без причины.

```bash
kubectl get sa -A
kubectl get role,rolebinding,clusterrole,clusterrolebinding -A
```

### Шаг 3: Проверь сетевые ограничения
- найди или добавь network policy между pod groups;
- зафиксируй, какой east-west трафик реально нужен.

```bash
kubectl get networkpolicy -A
```

### Что нужно явно показать
- какой service account использует приложение;
- какие security context и network policies действуют;
- есть ли broad RBAC;
- как хранятся секреты.

---

## 7.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- на своем стенде найди под, который все еще использует default service account, и исправь это;
- сравни manifest до и после добавления runAsNonRoot и readOnlyRootFilesystem;
- зафиксируй, что между namespace нет ненужного сетевого доступа.

---

## 7.6 Типовые ошибки

- использовать default service account по привычке;
- давать broad cluster-admin для приложения;
- игнорировать network policy;
- копировать insecure manifest из примеров без review.

---

## 7.7 Чеклист главы

- [ ] Я умею читать k8s manifest как security policy
- [ ] Service account и RBAC у меня минимальны
- [ ] Поды не работают привилегированно без причины
- [ ] Сетевые и секретные данные описаны осознанно
