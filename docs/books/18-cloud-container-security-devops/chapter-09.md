# Глава 9: Итоговый проект

> **Запомни:** итоговый проект этой книги должен показывать, что ты умеешь защищать не только контейнер, но и весь путь от cloud perimeter до runtime.

---

## 9.1 Цель проекта

Собрать hardened container/cloud baseline.

Проект должен включать:
- сетевые ограничения;
- IAM/role hygiene;
- secrets hygiene;
- hardened image;
- runtime restrictions;
- controlled validation после исправлений.

---

## 9.2 Стартовая точка

Подойдёт один из вариантов:
- VPS + Docker Compose;
- VPS + k3s;
- cloud VM или managed environment для личной lab.

Нужно иметь:
- возможность пересобрать образ;
- scanner;
- snapshot или rollback path.

---

## 9.3 Фазы проекта

### Фаза 1: Cloud и network review

Проверь:
- какие сервисы публичные;
- какие security groups/ACL действуют;
- нет ли лишнего admin exposure.

### Фаза 2: Secrets и IAM review

Проверь:
- где лежат секреты;
- какие роли/ключи используются;
- нет ли over-privileged аккаунтов.

### Фаза 3: Image и runtime hardening

Сделай:
- non-root;
- уменьшение image surface;
- scanner run;
- runtime restrictions.

### Фаза 4: Controlled validation

- повторно прогнать scanner;
- проверить публичную экспозицию;
- проверить runtime свойства контейнера/Pod.

---

## 9.4 Варианты проекта

### Основной вариант

Один cloud/container стек с публичным приложением и приватным внутренним сервисом.

### Альтернативный вариант

Один Docker Compose-host, но с реальным baseline по image, secrets и runtime.

---

## 9.5 Финальный чеклист

- [ ] Публичные сервисы осознанно ограничены
- [ ] IAM/roles не шире, чем нужно
- [ ] Секреты не в образе и не в git
- [ ] Образ запускается не под root
- [ ] Scanner findings обработаны и пересмотрены
- [ ] Runtime restrictions применены и проверены
- [ ] У меня есть rebuild/rollback path после изменений
