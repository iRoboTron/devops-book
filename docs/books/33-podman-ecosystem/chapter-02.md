# Глава 2: containerd и CRI-O — что внутри Kubernetes

## Что вы узнаете

- как Kubernetes запускает контейнеры без Docker и почему это лучше;
- что такое CRI и какую роль он играет между K8s и рантаймом;
- в чём разница между containerd и CRI-O на практике;
- как использовать `crictl` для диагностики на K8s-ноде.

---

## Зачем Kubernetes вообще нужен рантайм

Kubernetes — оркестратор. Он решает где запустить Pod, следит за их состоянием, перезапускает упавшие. Но сам Kubernetes не умеет запускать контейнеры — это не его работа.

Для запуска контейнеров K8s делегирует работу рантайму. Общение между K8s и рантаймом стандартизировано через **CRI** — Container Runtime Interface.

```text
kubectl apply -f pod.yaml
        │
        ▼
   kube-apiserver       ← принял задание
        │
        ▼
   kubelet              ← агент на ноде, отвечает за Pod
        │ CRI (gRPC)
        ▼
   containerd           ← высокоуровневый рантайм
        │ OCI Runtime Spec
        ▼
   runc                 ← низкоуровневый рантайм
        │
        ▼
   Контейнер            ← Linux namespaces + cgroups
```

---

## CRI — Container Runtime Interface

**CRI** — это gRPC API который kubelet использует для общения с рантаймом. Он появился в Kubernetes 1.5 (2016) именно чтобы убрать зависимость от конкретного рантайма.

CRI определяет две службы:

**RuntimeService** — управление контейнерами и pod-песочницами:
- `RunPodSandbox` / `StopPodSandbox` — создать/удалить сетевое пространство для Pod
- `CreateContainer` / `StartContainer` / `StopContainer` — жизненный цикл контейнера
- `ExecSync` / `Exec` — выполнить команду внутри (это `kubectl exec`)
- `Attach` — подключиться к процессу (это `kubectl attach`)

**ImageService** — управление образами:
- `PullImage` / `RemoveImage` — скачать/удалить образ
- `ImageStatus` — проверить наличие образа
- `ListImages` — список образов на ноде

До CRI Kubernetes разговаривал с Docker через dockershim — специальный адаптер внутри кода K8s. Dockershim переводил CRI-запросы в Docker API. Это был костыль, который убрали в 1.24.

---

## containerd — основной рантайм современных кластеров

**containerd** — высокоуровневый рантайм с поддержкой CRI. Именно его используют GKE, EKS, AKS и большинство managed Kubernetes по умолчанию.

### История

containerd изначально был внутри Docker — та часть которая управляла жизненным циклом контейнеров. В 2017 году Docker передал containerd в CNCF как самостоятельный проект. Теперь Docker сам использует containerd, и K8s использует containerd — но без Docker.

### Что умеет containerd

- Скачивать образы и управлять ими
- Управлять snapshots (слоями на диске)
- Запускать контейнеры через runc
- Реализовывать CRI для Kubernetes
- Управлять namespace-ами (изоляция клиентов)

### containerd vs Docker

```text
Docker:
  docker CLI → dockerd → containerd → runc → контейнер
                  ↑ dockerd добавляет: API, volumes, networks,
                    docker-compose, build, registry auth, swarm

containerd:
  kubelet → containerd → runc → контейнер
                  ↑ только то что нужно K8s: образы + контейнеры
```

containerd проще Docker намеренно. У него нет docker-compose, нет build, нет Swarm. Он делает одно и делает хорошо.

### Прямая работа с containerd через ctr

`ctr` — встроенный CLI для containerd. Используется для диагностики, не для повседневной работы.

```bash
# Список образов в containerd (если containerd установлен)
ctr images ls

# Список контейнеров
ctr containers ls

# Список запущенных задач (processes)
ctr tasks ls

# Скачать образ
ctr images pull docker.io/library/nginx:latest

# Запустить контейнер (низкоуровнево)
ctr run docker.io/library/nginx:latest nginx-test
```

---

## CRI-O — рантайм специально для Kubernetes

**CRI-O** разработан Red Hat именно как минимальный CRI-рантайм для Kubernetes. Девиз: «только то что нужно для CRI, ничего лишнего».

CRI-O используется в:
- OpenShift (Red Hat Kubernetes)
- RHEL-based Kubernetes кластерах
- MicroShift

### containerd vs CRI-O

```text
containerd:
  + Универсальный: работает и как CRI для K8s, и напрямую (ctr)
  + Поддерживается большинством managed K8s (GKE, EKS, AKS)
  + Большое сообщество, CNCF graduated
  - Больше функций → немного сложнее

CRI-O:
  + Минимальный: только CRI для K8s, ничего лишнего
  + Тесно интегрирован с OpenShift
  + Обновляется синхронно с K8s (одинаковые версии)
  - Меньше распространён за пределами Red Hat экосистемы
  - Нет прямого CLI для работы с образами вне K8s
```

На практике для большинства DevOps-инженеров разница незаметна. Если вы на OpenShift — у вас CRI-O. Если на AKS/GKE/EKS — containerd. Команды `kubectl` работают одинаково.

---

## Стек целиком: от kubectl до контейнера

Теперь можно нарисовать полный путь от команды до запущенного контейнера:

```text
Разработчик
    │ kubectl apply -f deployment.yaml
    ▼
kube-apiserver
    │ сохранил в etcd, уведомил Scheduler
    ▼
kube-scheduler
    │ выбрал ноду → уведомил kubelet на ноде
    ▼
kubelet (на выбранной ноде)
    │ CRI gRPC: RunPodSandbox, CreateContainer, StartContainer
    ▼
containerd (или CRI-O)
    │ скачал образ если нет, создал snapshot
    │ OCI Runtime Spec: config.json + rootfs
    ▼
runc
    │ clone() → новые namespaces
    │ cgroups → ограничения ресурсов
    │ pivot_root() → изолированная ФС
    ▼
Контейнер (процесс в namespace-е)
```

---

## crictl — диагностика на K8s-ноде

`crictl` — CLI для работы с CRI-совместимым рантаймом напрямую. Полезен когда `kubectl` недоступен или нужно посмотреть на контейнеры на уровне ноды.

### Установка

```bash
# crictl устанавливается отдельно (пакет cri-tools)
# Ubuntu/Debian:
VERSION="v1.30.0"
curl -L https://github.com/kubernetes-sigs/cri-tools/releases/download/$VERSION/crictl-$VERSION-linux-amd64.tar.gz \
  | sudo tar -C /usr/local/bin -xz

# Fedora/RHEL:
sudo dnf install cri-tools
```

### Настройка

`crictl` нужно указать куда подключаться. Путь зависит от рантайма:

```bash
# containerd (большинство K8s дистрибутивов):
crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps

# CRI-O (OpenShift, RHEL K8s):
crictl --runtime-endpoint unix:///run/crio/crio.sock ps

# Удобнее записать в конфиг чтобы не повторять:
cat > /etc/crictl.yaml << 'EOF'
runtime-endpoint: unix:///run/containerd/containerd.sock
image-endpoint: unix:///run/containerd/containerd.sock
timeout: 10
EOF

# Теперь можно просто:
crictl ps
```

### Основные команды

```bash
# Список запущенных контейнеров
crictl ps

# Список всех контейнеров (включая остановленные)
crictl ps -a

# Список pod-песочниц (инфра-контейнеры)
crictl pods

# Список образов на ноде
crictl images

# Логи контейнера
crictl logs <container-id>

# Выполнить команду внутри контейнера
crictl exec -it <container-id> sh

# Инспектировать контейнер
crictl inspect <container-id>

# Статистика ресурсов
crictl stats
```

### Сравнение crictl и kubectl

| Задача | kubectl | crictl |
|--------|---------|--------|
| Список Pod-ов | `kubectl get pods -A` | `crictl pods` |
| Логи | `kubectl logs <pod>` | `crictl logs <container-id>` |
| Exec | `kubectl exec -it <pod> -- sh` | `crictl exec -it <container-id> sh` |
| Образы | `kubectl get nodes` (нет) | `crictl images` |
| Доступ | Нужен kube-apiserver | Прямо на ноде, без API |

`crictl` полезен когда:
- kube-apiserver недоступен (bootstrapping, нода изолирована)
- Нужно посмотреть что реально запущено на уровне рантайма
- Отлаживаете почему Pod не стартует (ImagePullBackOff, CrashLoopBackOff)

> **Примечание:** `crictl` работает только там где установлен CRI-рантайм (K8s-нода). На обычном сервере с Podman для экспериментов используйте `podman ps` — оно лучше подходит для не-K8s окружений.

---

## Почему Podman не используется как K8s-рантайм

Это распространённый вопрос: раз Podman такой хороший — почему его не используют в Kubernetes вместо containerd?

Ответ простой: **у Podman нет CRI-интерфейса**.

Podman спроектирован как CLI-инструмент для пользователей. containerd и CRI-O спроектированы как daemon-ы которыми управляет другой процесс (kubelet) через gRPC. Это разные задачи.

Зато Podman умеет то чего нет у containerd:
- `podman kube play` — запустить K8s YAML локально без кластера
- `podman kube generate` — экспортировать контейнеры в K8s YAML
- `podman-compose` — управлять многоконтейнерными приложениями

Podman — мост между локальной разработкой и K8s, а не замена K8s-рантайму.

---

## Типичные ошибки

**«Раз K8s убрал Docker — надо удалить Docker с нод»**
На K8s-нодах Docker обычно не устанавливают — там containerd или CRI-O. Если Docker был установлен — после перехода на containerd его действительно можно убрать. Но это не значит что Docker вообще нигде не нужен (он может быть на CI-машинах для сборки).

**«crictl ps и docker ps должны показывать одно и то же»**
`crictl ps` показывает контейнеры которыми управляет K8s-рантайм. `docker ps` показывает контейнеры которыми управляет dockerd. На K8s-ноде без Docker — `docker ps` просто не работает, это нормально.

**«Запустить crictl ps без указания сокета»**
Без `--runtime-endpoint` или конфига `crictl` пробует стандартные пути. Если рантайм в нестандартном месте — команда зависнет или выдаст ошибку подключения. Всегда указывайте endpoint явно или пишите конфиг.

**«containerd и dockerd — одно и то же»**
Нет. dockerd включает containerd, но добавляет много своего поверх. containerd без dockerd — это именно то что использует Kubernetes: без volume-драйверов Docker, без Docker networks, без docker-compose.

---

## Чек-лист для самопроверки

- [ ] Могу объяснить что такое CRI и какие два gRPC-сервиса он включает
- [ ] Понимаю полный путь от `kubectl apply` до запущенного контейнера
- [ ] Знаю разницу между containerd и CRI-O — где используется каждый
- [ ] Понимаю почему Podman не является K8s-рантаймом
- [ ] Знаю как указать runtime-endpoint для `crictl` (containerd и CRI-O)

## Попробуйте сами

1. Нарисуйте (на бумаге или в тексте) стек от `kubectl apply` до запущенного контейнера. Включите: kube-apiserver, scheduler, kubelet, containerd, runc, namespaces. Сравните с диаграммой в главе.

2. Если есть доступ к K8s-ноде (minikube, kind, или облачный кластер):
   ```bash
   # Зайти на ноду
   minikube ssh   # или kubectl node-shell
   
   # Посмотреть запущенные контейнеры через containerd напрямую
   crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps
   
   # Сравнить с kubectl
   kubectl get pods -A
   ```
   Совпадают ли контейнеры? Почему их больше в `crictl ps` (подсказка: infra-контейнеры)?

3. Найдите в документации Kubernetes страницу про CRI и прочитайте список сертифицированных рантаймов. Какие кроме containerd и CRI-O есть в списке?
