# GitOps — Приложения

---

## A: ArgoCD шпаргалка

| Команда | Назначение |
|---------|-----------|
| `argocd app list` | Список приложений |
| `argocd app get myapp` | Статус |
| `argocd app sync myapp` | Синхронизация |
| `argocd app history myapp` | История деплоев |
| `argocd app rollback myapp 5` | Откат к ревизии 5 |
| `argocd app diff myapp` | Разница Git vs кластер |
| `kubectl argo rollouts get rollout myapp --watch` | Canary статус |
| `kubectl argo rollouts promote myapp` | Продвинуть Canary |
| `kubectl argo rollouts abort myapp` | Откат Canary |

## B: Готовые конфиги

### ArgoCD Application
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/user/app-infra.git
    targetRevision: main
    path: helm/myapp
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### ApplicationSet
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-envs
spec:
  generators:
  - list:
      elements:
      - env: dev
        namespace: dev
        values: values.dev.yaml
      - env: prod
        namespace: prod
        values: values.prod.yaml
  template:
    metadata:
      name: "myapp-{{env}}"
    spec:
      source:
        repoURL: https://github.com/user/app-infra.git
        path: helm/myapp
        helm:
          valueFiles: ["{{values}}"]
      destination:
        namespace: "{{namespace}}"
```

## C: Диагностика

| Проблема | Причина | Решение |
|----------|---------|---------|
| ArgoCD OutOfSync | Ручные изменения в кластере | `argocd app sync` или убери ручные изменения |
| ArgoCD не видит репо | Неправильные credentials | Settings → Repositories |
| CI не может push в infra | Нет deploy token | Создай GitLab deploy token |
| Rollout застрял | Analysis fail | `kubectl describe analysisrun` |
| selfHeal откатывает ручные изменения | Это правильное поведение | Меняй только через Git |
