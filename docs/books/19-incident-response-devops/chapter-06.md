# Глава 6: Ransomware resilience без вредоносной практики

> **Запомни:** устойчивость к разрушительным сценариям строится через бэкапы, сегментацию, least privilege и готовность быстро изолировать проблему, а не через демонстрацию вредоноса.

---

## 6.1 Контекст и границы

В этой теме легко уйти в неправильную сторону. Для инженера полезнее разбирать не “как написать вредонос”, а какие механизмы обычно приводят к массовому impact и как их прерывать заранее.

На практике устойчивость определяется резервным копированием, сетевым разделением, правами доступа, мониторингом и скоростью containment.

Эта глава особенно полезна для всех, кто хочет защитить инфраструктуру от destructive impact без опасной offensive-практики.

---

## 6.2 Как выглядит риск

Типовые слабые места:
- бэкапы доступны на запись из основной среды;
- один скомпрометированный аккаунт видит слишком много файлов и систем;
- массовые file changes и удаления не мониторятся;
- нет плана быстрой изоляции хоста;
- RDP, SSH или admin-plane слишком широко открыты.

### Где особенно важно
- домашняя инфраструктура
- VPS + storage
- малый офис

---

## 6.3 Что строит защитник

- offline или immutable backups либо хотя бы отдельно защищенное хранилище;
- сегментация и минимум прав на файлы и share;
- мониторинг аномальных массовых изменений;
- runbook изоляции хоста и отключения учетки;
- проверка восстановления в изолированной среде.

### Практический результат главы
- ты умеешь оценить resilience без dangerous demos;
- понимаешь, какие элементы защиты реально снижают impact;
- можешь спланировать containment и recovery сценарий.

```
- резкий рост file changes
- массовые delete/rename
- burst неуспешных логинов
- новые admin sessions
```

---

## 6.4 Практика

### Шаг 1: Оцени backup isolation
- проверь, может ли основная среда менять или удалять свои же бэкапы;
- если да, это слабое место.

```bash
ls -la /var/backups/
sudo -u appuser rm /var/backups/db-backup-latest.sql 2>&1
cat /etc/cron.d/backup 2>/dev/null || systemctl list-timers --all | grep -i backup
```

Если `appuser` может удалить backup-файл, бэкап не изолирован от компрометации приложения.

### Шаг 2: Оцени blast radius
- для одного admin и одного app account опиши, какие системы и хранилища им доступны;
- сократи лишнее.

```bash
id
mount
```

Мониторинг аномальных file changes на lab:

```bash
sudo apt install -y inotify-tools
inotifywait -m -r /var/www/myapp -e modify,delete,create,move 2>&1 | \
  awk '{print strftime("[%Y-%m-%d %H:%M:%S]"), $0}' | \
  tee /var/log/file-changes.log
```

Для production-подхода полезен `auditd`:

```bash
sudo auditctl -w /etc/passwd -p wa -k passwd_changes
sudo auditctl -w /var/www -p wax -k webroot_changes
sudo ausearch -k passwd_changes --start today
```

### Шаг 3: Сделай tabletop exercise
- смоделируй destructive incident без запуска вредоносного кода;
- пройди решения: изоляция, отключение доступа, restore, коммуникация.

```bash
cat > /tmp/ransomware-tabletop.md <<'EOF'
signal: mass file rename under /var/www/myapp
containment: isolate host, disable app credentials
recovery: verify backups, restore to isolated environment
communication: notify owners and record timeline
EOF
cat /tmp/ransomware-tabletop.md
```

### Что нужно явно показать
- как защищены бэкапы от основной среды;
- какой runbook изоляции хоста существует;
- какие признаки destructive impact будут видны первыми;
- как проверяется восстановление.

---

## 6.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- на своей lab проведи tabletop-сценарий: массовые изменения файлов на тестовом каталоге и дальнейшая реакция;
- проверь, что бэкапы живут отдельно и доступны для test restore;
- зафиксируй, какие права доступа нужно сократить.

---

## 6.6 Типовые ошибки

- делать risky demo ради наглядности;
- хранить бэкапы в той же trust zone, что и production;
- не иметь runbook на отключение доступа и изоляцию хоста;
- считать, что антивирус решает вопрос один.

---

## 6.7 Чеклист главы

- [ ] Бэкапы у меня отделены от основной среды
- [ ] Есть план быстрой изоляции и отключения доступа
- [ ] Blast radius по учеткам и системам мне понятен
- [ ] Destructive сценарии проверяются через tabletop и restore
