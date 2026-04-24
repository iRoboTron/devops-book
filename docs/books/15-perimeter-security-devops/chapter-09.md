# Глава 9: Итоговый проект

> **Запомни:** здесь важно не просто "включить защиты", а доказать, что они реально уменьшают поверхность атаки и дают сигнал защитнику.

---

## 9.1 Цель проекта

Собрать и проверить первый полноценный defensive baseline для публичного входа.

В этой книге ты выбираешь один из трёх сценариев:

1. один защищённый публичный Linux-сервер;
2. `gateway + DMZ + app server`;
3. изолированная лаборатория, где controlled checks доказывают работу защиты.

---

## 9.2 Вариант 1: Один защищённый публичный Linux-сервер

### Что должно быть в результате

- только нужные открытые порты;
- SSH только по ключам;
- firewall policy `deny incoming`;
- backend не торчит наружу;
- reverse proxy на входе;
- rate limit для чувствительных endpoint'ов;
- fail2ban или CrowdSec для автоматической реакции;
- понятные логи и список того, где искать события.

### Что проверить

```bash
ss -tulpn
sudo ufw status verbose
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|maxauthtries'
nmap -Pn SERVER_IP
curl -I http://HOST
curl -Ik https://HOST
sudo fail2ban-client status
```

---

## 9.3 Вариант 2: Gateway + DMZ + app server

### Минимальная схема

```text
client VM
  -> gateway/firewall VM
  -> app VM
```

### Что должно быть в результате

- административный доступ отделён от пользовательского;
- app server не выставлен напрямую без причины;
- трафик проходит через gateway policy;
- между зонами есть осознанные разрешения, а не "всё всем".

### Что проверить

- какие порты видны с client VM;
- какой трафик проходит между сегментами;
- что происходит при попытке доступа к закрытому сервису;
- что видно в логах gateway.

---

## 9.4 Вариант 3: Лаборатория controlled checks

### Схема

```text
attacker/client VM
  -> target VM
или
client VM -> gateway VM -> server VM
```

### Допустимые проверки

Только на своих системах:

```bash
nmap -Pn TARGET_IP
ssh wronguser@TARGET_IP
for i in $(seq 1 20); do curl -s -o /dev/null https://HOST/login; done
```

### Что должно быть доказано

- лишние порты не видны;
- SSH password login не проходит;
- повторяющиеся ошибки логина дают бан;
- proxy/logs показывают controlled test;
- чувствительные сервисы не торчат наружу.

---

## 9.5 Стартовая точка

До начала проекта должно быть:

- свой стенд или VPS, которым ты владеешь;
- snapshot или backup;
- вторая своя машина для внешней проверки;
- список сервисов, которые должны остаться доступны после hardening.

---

## 9.6 Фазы проекта

### Фаза 1: Инвентаризация

```bash
ss -tulpn
systemctl list-units --type=service --state=running
sudo ufw status verbose
```

Запиши:
- какие порты открыты;
- какие сервисы реально нужны;
- какие endpoints чувствительны.

Ожидаемый результат фазы:

```bash
ss -tulpn
```

```
LISTEN 0.0.0.0:22
LISTEN 0.0.0.0:5432
LISTEN 127.0.0.1:8000
```

Это baseline. Ты ещё ничего не исправляешь, только отмечаешь строки с `0.0.0.0` и решаешь, какие из них действительно должны остаться публичными.

### Фаза 2: Сокращение поверхности атаки

- выключи лишние сервисы;
- закрой лишние порты;
- убери bind на `0.0.0.0`, если не нужен.

Ожидаемый результат фазы:

```bash
ss -tulpn
nmap -Pn -p 22,80,443,5432,3306,6379 SERVER_IP
```

```
22/tcp   open      ssh
80/tcp   open      http
443/tcp  open      https
5432/tcp filtered  postgresql
6379/tcp filtered  redis
```

Если база и внутренние сервисы всё ещё `open`, поверхность атаки реально не сократилась.

### Фаза 3: Усиление административного входа

- SSH только по ключам;
- root login запрещён;
- лимиты логина настроены.

Ожидаемый результат фазы:

```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no user@SERVER
```

```
user@SERVER: Permission denied (publickey).
```

И отдельно:

```bash
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|maxauthtries'
```

```
permitrootlogin no
passwordauthentication no
maxauthtries 3
```

Если парольный вход всё ещё проходит, hardening ещё не применился.

### Фаза 4: Веб-вход и автоматические реакции

- reverse proxy на входе;
- rate limit;
- fail2ban/CrowdSec.

Ожидаемый результат фазы:

```bash
sudo fail2ban-client status sshd
curl -sI https://HOST | grep -Ei 'x-frame|x-content|strict-transport|referrer'
```

```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 0
`- Actions
   |- Currently banned: 0
```

```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

`Currently banned: 0` в спокойном режиме нормально. После controlled test должен появиться адрес в `Banned IP list`.

### Фаза 5: Controlled checks

Проверяй только своими машинами и только то, что реально построил.

Ожидаемый результат фазы:

```bash
ssh wronguser@SERVER_IP
for i in $(seq 1 10); do curl -s -o /dev/null -w "%{http_code}\n" https://HOST/login; done
sudo journalctl -u fail2ban -n 20 --no-pager
```

```
fail2ban.actions: NOTICE  [sshd] Ban 10.0.0.5
```

Итог фазы такой: ты можешь показать не только конфиги, но и следы того, что защита реально сработала на своём стенде.

---

## 9.7 Финальный чеклист

- [ ] Наружу видны только осознанно опубликованные сервисы
- [ ] SSH не принимает парольный вход
- [ ] Root не логинится напрямую по SSH
- [ ] База данных не торчит наружу
- [ ] Backend скрыт за reverse proxy или внутренним адресом
- [ ] Firewall работает по принципу deny by default
- [ ] Fail2ban/CrowdSec реагирует на controlled login storm
- [ ] Rate limit или эквивалент настроен для чувствительных endpoint'ов
- [ ] Я могу показать логи или события по controlled checks
- [ ] У меня есть snapshot/rollback plan после проекта

---

## 9.8 Что сохранить после проекта

Если проект сделан на VM, сделай snapshot.

Подходящее имя:

```text
after-book-15-perimeter-baseline
```

Если проект на VPS:
- сохрани конфиги;
- обнови diagram/runbook;
- зафиксируй baseline в git или в заметках;
- сохрани список открытых портов и сервисов как эталон.

---

## 9.9 Что дальше

После этой книги ты должен уже не гадать, "нужна ли коробка перед сервером", а уметь отвечать инженерно:

- какой класс решения нужен;
- какие у него пределы;
- что ещё обязательно укрепить на самом Linux;
- как безопасно подтвердить, что защита реально работает.
