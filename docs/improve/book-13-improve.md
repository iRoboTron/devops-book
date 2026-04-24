# Инструкция агенту: улучшение книги 13 «GitLab CI + GitOps ArgoCD»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/13-gitops-devops/
```

Книга: **407 строк** — самая короткая во всём курсе 2.0. Только 5 глав + appendix. Нет упражнений ни в одной главе. ArgoCD UI и ключевые рабочие операции (sync, diff, rollback) не описаны.

**Главная проблема:** книга объясняет концепцию GitOps, но не объясняет как работать с ArgoCD в ежедневной практике — как смотреть статус, как откатить, что делать при рассинхронизации.

---

## Что НЕ трогать

- Существующие CI конфиги (GitHub Actions, GitLab CI)
- Application CRD манифест (глава 3)
- Progressive Delivery концепцию (глава 5)
- Схему Push vs Pull (глава 2)

---

## Добавить упражнения во все главы

Ни одной главе нет блока «📝 Упражнения». Добавить в каждую.

---

## Задачи по главам

---

### Глава 1 (`chapter-01.md`) — CI пайплайн

**Глава достаточно хорошая.** Добавить только упражнения и вывод успешного pipeline.

**Добавить** пример успешного вывода GitHub Actions:

```
✅ test        2m 14s
✅ build       1m 42s
  → pushed: ghcr.io/user/myapp:abc123def
```

**Добавить** упражнения:

```
### Упражнение 1.1: Первый CI
1. Создай .github/workflows/ci.yml с jobs: test и build
2. git push → проверь Actions tab в GitHub
3. Образ появился в ghcr.io?

### Упражнение 1.2: Сломать и починить
1. Добавь намеренно падающий тест
2. git push — CI упал?
3. Исправь — CI прошёл, образ собран?
```

---

### Глава 2 (`chapter-02.md`) — GitOps идея

**Проблема:** 32 строки — просто концепция. Нет объяснения как выглядит рассинхронизация и auto-heal.

**Добавить** раздел **2.3 «Что значит Self-Heal»:**

```
Кто-то вручную изменил реплики в кластере:
kubectl scale deployment myapp --replicas=1  ← обход Git

ArgoCD видит: Git говорит 2, кластер показывает 1
                              ↓
                 Auto-heal: восстанавливает до 2
```

Именно для этого `selfHeal: true` в syncPolicy. Без него изменения накапливаются и Git перестаёт быть источником истины.

**Добавить** раздел **2.4 «Два репозитория — почему»:**

```
app-code/    → разработчики коммитят код
app-infra/   → CI обновляет image tag автоматически
```

Если оба в одном репозитории — CI будет коммитить в тот же repo что пушит разработчик. Это создаёт цикл и мусорные коммиты в истории.

**Добавить** упражнения:

```
### Упражнение 2.1: Понять auto-heal
1. Создай Application с autoSync + selfHeal
2. Вручную измени реплики: kubectl scale deployment myapp --replicas=0
3. ArgoCD восстановил реплики обратно через ~30 секунд?
```

---

### Глава 3 (`chapter-03.md`) — ArgoCD установка

**Проблема:** Установка и Application показаны, но нет объяснения как работать с ArgoCD UI.

**Добавить** раздел **3.4 «ArgoCD UI: основные экраны»:**

После `kubectl port-forward svc/argocd-server -n argocd 8080:443` открыть `https://localhost:8080`:

- **Applications** — список приложений со статусами
  - `Synced` + `Healthy` — всё хорошо
  - `OutOfSync` — в Git есть изменения которые не применены
  - `Degraded` — Pod'ы падают

- **Кликнуть на Application** → видно:
  - Граф ресурсов (Deployment → ReplicaSet → Pods)
  - Статус каждого ресурса
  - Кнопки `Sync`, `Refresh`, `Delete`

- **Вкладка Diff** — что изменится при sync (до применения)

**Добавить** раздел **3.5 «argocd CLI: основные команды»:**

```bash
# Статус всех приложений
argocd app list

# Детали приложения
argocd app get myapp

# Принудительный sync
argocd app sync myapp

# Откат к предыдущей версии
argocd app history myapp
argocd app rollback myapp 2  # откат к ревизии 2

# Diff: что изменится
argocd app diff myapp
```

**Добавить** упражнения:

```
### Упражнение 3.1: Первое Application
1. Создай app-infra репозиторий с простым Deployment
2. kubectl apply -f application.yaml -n argocd
3. argocd app list — статус Synced?
4. Открой UI — видишь граф ресурсов?

### Упражнение 3.2: OutOfSync
1. Измени replicas в Git, запушь
2. argocd app get myapp — статус OutOfSync?
3. argocd app sync myapp — применилось?
4. kubectl get pods — новые реплики?
```

---

### Глава 4 (`chapter-04.md`) — CI + ArgoCD полный цикл

**Проблема:** `sed -i` для обновления image tag в infra-repo — хрупкий подход. Нет объяснения альтернативы (Image Updater).

**Добавить** раздел **4.3 «Проблемы sed-подхода и альтернативы»:**

`sed -i "s|tag: .*|tag: $CI_COMMIT_SHA|"` — работает, но хрупко:
- Ломается если формат values.yaml изменился
- Создаёт мусорные коммиты в git log infra-репо

Альтернатива — ArgoCD Image Updater:

```bash
# Установить
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml
```

```yaml
# Добавить аннотации к Application
metadata:
  annotations:
    argocd-image-updater.argoproj.io/image-list: myapp=ghcr.io/user/myapp
    argocd-image-updater.argoproj.io/myapp.update-strategy: latest
```

Теперь ArgoCD сам отслеживает новые теги в registry и обновляет — без CI-скрипта для обновления infra-repo.

**Добавить** раздел **4.4 «Что делать когда цикл сломался»:**

Если CI упал при обновлении infra-repo, а приложение задеплоено частично:

```bash
# Проверить статус
argocd app get myapp

# Если Degraded — посмотреть Pod'ы
kubectl get pods -n prod
kubectl describe pod <failing-pod> -n prod | tail -20

# Откатить к последней рабочей версии
argocd app rollback myapp
```

**Добавить** упражнения:

```
### Упражнение 4.1: Полный цикл
1. git push в app-code репо
2. CI: тест прошёл → образ запушен → infra обновлён
3. ArgoCD: обнаружил изменение → синхронизировал
4. kubectl get pods -n prod — новая версия?

### Упражнение 4.2: Откат
1. Задеплой плохую версию (добавь намеренный баг)
2. argocd app history myapp
3. argocd app rollback myapp <revision>
4. Приложение работает снова?
```

---

### Глава 5 (`chapter-05.md`) — Progressive Delivery

**Проблема:** Canary и Blue-Green показаны как YAML без объяснения как наблюдать за прогрессом и как откатить если что-то пошло не так.

**Добавить** раздел **5.3 «Наблюдать за Canary rollout»:**

```bash
# Статус rollout
kubectl argo rollouts get rollout myapp --watch
```

```
Name:            myapp
Status:          ॥ Paused
Strategy:        Canary
  Step:          1/3
  SetWeight:     20
  ActualWeight:  20

Replicas:
  Desired:  5
  Current:  5
  Updated:  1    ← 1 Pod на новой версии (20%)
  Ready:    5

NAME          KIND     STATUS   AGE
myapp-xxx-new Canary   Running  30s   ← новая версия
myapp-xxx-old Stable   Running  5m    ← старая версия (×4)
```

**Добавить** раздел **5.4 «Продолжить или откатить»:**

```bash
# Продолжить (следующий шаг: 50%)
kubectl argo rollouts promote myapp

# Прервать и откатить к стабильной версии
kubectl argo rollouts abort myapp
```

**Добавить** упражнения:

```
### Упражнение 5.1: Canary
1. Установи Argo Rollouts:
   kubectl create namespace argo-rollouts
   kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
2. Создай Rollout с canary: 20% → 50% → 100%
3. kubectl argo rollouts get rollout myapp --watch
4. Дай пройти первую паузу — видишь 20% трафика?
5. promote → abort — оба работают?
```

---

## Общий объём

Цель: 900–1100 строк (сейчас 407). Основной рост за счёт argocd CLI примеров, раздела UI и упражнений.

## Приоритет

1. Глава 3 (ArgoCD UI + CLI) — это самое важное для ежедневной работы
2. Глава 4 (откат, что делать когда сломалось) — практика
3. Упражнения во все главы
4. Глава 5 (наблюдение за canary rollout)

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-13-improve.md`*
