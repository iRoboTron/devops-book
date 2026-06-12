# Kubernetes: Основы

> Книга 10 курса DevOps

---

## Оглавление

### Подготовка

- [**Глава 0: Зачем Kubernetes**](chapter-00.md)
  - Проблемы docker-compose, архитектура, k3s

### Часть 1: Базовые объекты

- [**Глава 1: Pod**](chapter-01.md)
  - Минимальная единица, почему не запускают напрямую

- [**Глава 2: Deployment**](chapter-02.md)
  - Реплики, самовосстановление, rolling update

- [**Глава 3: Service**](chapter-03.md)
  - ClusterIP, NodePort, стабильный адрес для Pods

- [**Глава 4: ConfigMap и Secret**](chapter-04.md)
  - Конфигурация и секреты (аналог .env)

### Часть 2: Данные и организация

- [**Глава 5: Volume и PVC**](chapter-05.md)
  - Постоянное хранение данных

- [**Глава 6: Namespace**](chapter-06.md)
  - Изоляция окружений (dev/prod)

### Часть 3: Практика

- [**Глава 7: Деплой Python-приложения**](chapter-07.md)
  - Полный стек + docker-compose → K8s мост

- [**Глава 8: kubectl шпаргалка**](chapter-08.md)
  - Справочник команд

- [**Глава 9: Rolling update и откат**](chapter-08.md)
  - Обновление без даунтайма

- [**Глава 10: Ресурсы (limits, requests)**](chapter-08.md)
  - Limits, requests, quotas, OOM, QoS-классы

### Часть 4: Диагностика и развитие

- [**Глава 11: Диагностика — когда что-то сломалось**](chapter-11.md)
  - get/describe/logs, Pending/CrashLoop/ImagePull, «Service не работает», kubectl debug, упражнение «найди баг»

- [**Глава 12: Куда дальше — карта продвинутых тем**](chapter-12.md)
  - RBAC, NetworkPolicy, scheduling, DaemonSet/Job/CronJob, etcd, kubeadm vs managed

### Приложения

- [**Приложение A: Шпаргалка kubectl**](appendix-a.md)
  - Внутри: шпаргалка, готовые манифесты и диагностика

- [**Глоссарий**](glossary.md)
  - Ключевые термины книги с указанием глав

---

## Главная идея

K8s решает 3 проблемы docker-compose:

```
docker-compose:          Kubernetes:
1 хост                   Много хостов
Нет авто-восстановления  Упал Pod → поднялся сам
Нет масштабирования      Нагрузка ×10 → добавь реплики
```

K8s = платформа которая следит за желаемым состоянием.

---

## Предварительные требования

- Модули 1–9 (включая Docker и Ansible)
- VirtualBox (для k3s на виртуалке) или VPS

---

*Kubernetes: Основы — Курс DevOps, Модуль 10*
