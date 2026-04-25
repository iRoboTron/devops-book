# Глава 4: Privilege escalation theory

> **Запомни:** эскалация привилегий в защитной оптике — это поиск локальных путей, по которым ошибка или избыточное право превращают обычный доступ в контроль над узлом.

---

## 4.1 Контекст и границы

Privilege escalation интересна защитнику не как техника атаки, а как способ найти misconfig: лишний sudo, root-owned writable path, setuid-бинарник, service account с широкими правами.

Если ты знаешь типовые классы локального усиления прав, то быстрее строишь baseline hardening.

Эта глава особенно полезна для Linux-инженеров, которые хотят понимать локальные риски без offensive-практики.

---

## 4.2 Как выглядит риск

Типовые слабые места:
- слишком широкие sudoers rules — обычный пользователь получает root не через exploit, а через разрешённую команду.
  Признак: `NOPASSWD: ALL` или слишком широкие команды в sudoers.
  Проверить: `sudo -l`, `/etc/sudoers`, `/etc/sudoers.d`.
- неправильные права на каталоги и скрипты служб — непривилегированный пользователь может менять то, что потом выполнит root.
  Признак: world/group writable файлы в systemd/cron paths.
  Проверить: `find` по критичным каталогам.
- неожиданные setuid и setgid бинарники — редкий бинарник с setuid становится лишним путём усиления прав.
  Признак: нестандартные пути в списке `-perm -4000`.
  Проверить: `find / -perm -4000 -type f`.
- службы запускаются от root без причины — компрометация сервиса сразу даёт повышенный impact.
  Признак: systemd unit без выделенного service account.
  Проверить: `systemctl cat SERVICE | grep User=`.
- секреты root-процессов доступны обычному пользователю — локальный доступ можно быстро превратить в административный.
  Признак: world-readable env/config файлов для root-owned сервисов.
  Проверить: права на конфиги и `.env`.

### Где особенно важно
- Linux сервер
- docker host
- jump host
- single app VM

---

## 4.3 Что строит защитник

- минимальный sudo;
- правильные права на файлы и каталоги;
- review setuid, cron и systemd scripts;
- разделение service accounts;
- регулярный hardening review.

### Практический результат главы
- ты понимаешь основные классы локальных misconfig;
- можешь провести безопасный review sudo и file permissions;
- умеешь описать, как ошибка в правах превращается в системный риск.

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
find /etc/systemd /usr/local/bin -maxdepth 2 -type f -perm /022 -ls 2>/dev/null
```

---

## 4.4 Практика

### Шаг 1: Проверь sudo baseline
- посмотри, какие команды разрешены пользователям и группам;
- убери все, что шире фактической задачи.

```bash
sudo -l
sudo cat /etc/sudoers
sudo ls /etc/sudoers.d
```

### Шаг 2: Проверь права и владельцев
- обрати внимание на исполняемые скрипты для cron, systemd и deployment;
- ищи writable paths, которыми владеют не те пользователи.

```bash
find /etc/systemd /usr/local/bin -maxdepth 2 -type f -perm /022 -ls 2>/dev/null
```

### Шаг 3: Составь hardening список
- после review зафиксируй 5 самых опасных локальных misconfig и план исправления;
- не пытайся их эксплуатировать, цель — defensive review.

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null | head -30
find /etc/systemd /usr/local/bin -maxdepth 2 -type f -perm /022 -ls 2>/dev/null
cat > /tmp/local-privilege-risks.txt <<'EOF'
1. broad sudoers entries
2. writable service scripts
3. unexpected setuid binaries
4. root services without dedicated users
5. world-readable secret files
EOF
cat /tmp/local-privilege-risks.txt
```

### Что нужно явно показать
- текущий sudo baseline;
- какие локальные права у service accounts;
- есть ли опасные setuid и writable paths;
- какие hardening-шаги приоритетны.

---

## 4.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- на своей lab найди один локальный misconfig, исправь его и сравни состояние до и после;
- зафиксируй, как именно эта ошибка могла увеличить impact при уже полученном доступе;
- без практики эксплуатации и без запуска опасных цепочек.

---

## 4.6 Типовые ошибки

- считать локальные права второстепенной темой;
- держать слишком широкий sudo на всякий случай;
- не проверять права на служебные скрипты;
- путать review misconfig с offensive exploitation.

---

## 4.7 Чеклист главы

- [ ] Я знаю свой sudo baseline
- [ ] Локальные привилегии service accounts пересмотрены
- [ ] Опасные права на файлы и скрипты ищутся регулярно
- [ ] Я умею описать локальный risk без его эксплуатации
