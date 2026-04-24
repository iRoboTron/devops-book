# Глава 3: SSH hardening

> **Запомни:** SSH — это дверь администратора. Если она защищена плохо, остальная архитектура уже не так важна.

---

## 3.1 Базовая логика защиты SSH

У SSH три базовых задачи защиты:

- вход только для тех, кому положено;
- вход только надёжным способом;
- ограничение числа попыток и скорости злоупотребления.

Практический baseline:
- логин по ключам;
- `PermitRootLogin no`;
- `PasswordAuthentication no`;
- ограничение пользователей и попыток.

---

## 3.2 Что должно быть до правки конфига

Прежде чем выключать пароли, у тебя уже должен работать вход по ключу в **отдельной** открытой сессии.

Это важный порядок:

1. добавить публичный ключ;
2. проверить новый логин;
3. только потом запрещать пароль;
4. проверять конфиг через `sshd -t`;
5. делать `reload`, а не слепой `restart`, если не уверен.

---

## 3.3 Практический baseline для `sshd_config`

```ini
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 20
AllowUsers deploy
```

Не обязательно копировать всё бездумно. Но смысл у этих строк такой:

- `PermitRootLogin no` — root не логинится напрямую;
- `PasswordAuthentication no` — пароль выключен;
- `PubkeyAuthentication yes` — вход по ключам разрешён;
- `MaxAuthTries 3` — меньше шума и меньше brute-force окна;
- `LoginGraceTime 20` — сессия не висит бесконечно на логине;
- `AllowUsers deploy` — логин только нужному админ-пользователю.

---

## 3.4 Практика

### Посмотреть текущее состояние

```bash
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|pubkeyauthentication|maxauthtries|logingracetime'
```

### Проверить конфиг на синтаксис

```bash
sudo sshd -t
```

### Перечитать логи SSH

```bash
sudo journalctl -u ssh -n 50 --no-pager
# или
sudo tail -n 50 /var/log/auth.log
```

### Перезагрузить конфиг без убийства действующего сеанса

```bash
sudo systemctl reload ssh
```

На некоторых системах служба называется `sshd`:

```bash
sudo systemctl reload sshd
```

---

## 3.5 Дополнительные решения

### Менять ли порт SSH

Смена порта — не замена hardening. Она только уменьшает шум ботов.

Это допустимо как дополнительный слой, если:
- ты умеешь документировать порт;
- не забудешь обновить firewall и свой `~/.ssh/config`;
- понимаешь, что от целенаправленного поиска это не спасает.

### VPN вместо открытого SSH

Для VPS и особенно small business часто лучше:
- SSH только через VPN;
- или через bastion/jump host;
- или через allowlist по IP.

---

## 3.5а Как выглядит атака в логах

После включения hardening важно уметь читать следы brute-force в логах.

Пример из `/var/log/auth.log`:

```
Apr 15 03:12:01 server sshd[12345]: Failed password for invalid user admin from 185.234.10.11 port 44321 ssh2
Apr 15 03:12:03 server sshd[12346]: Failed password for invalid user root from 185.234.10.11 port 44322 ssh2
Apr 15 03:12:05 server sshd[12347]: Failed password for invalid user ubuntu from 185.234.10.11 port 44323 ssh2
```

Что это показывает:
- один и тот же IP перебирает стандартные имена пользователей;
- `Failed password` — событие, по которому fail2ban понимает, что это неудачный логин;
- после `MaxAuthTries 3` одна SSH-сессия даёт только несколько попыток, значит бот быстрее упрётся в лимит.

Быстрый подсчёт самых шумных IP:

```bash
sudo grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn | head -10
```

Пример вывода:

```
124 185.234.10.11
 88 91.240.118.17
 34 203.0.113.41
```

Этот список нужен не для ручной борьбы с каждым IP, а чтобы увидеть масштаб шума до и после fail2ban.

---

## 3.6 Lab-only проверка

На своей lab-машине проверь:

```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no user@server
```

Ожидаемый результат после hardening:

```text
Permission denied (publickey)
```

И отдельно проверь, что вход по ключу продолжает работать.

---

## 3.7 Типовые ошибки

- отключить пароль до проверки входа по ключу;
- редактировать `sshd_config` и не запускать `sshd -t`;
- оставить `root` логин "на всякий случай";
- открыть SSH всему интернету и думать, что на этом работа закончилась;
- забыть, что SSH — это только один слой, а не вся защита.

---

## 3.8 Чеклист главы

- [ ] У меня работает вход по SSH только по ключам
- [ ] `PermitRootLogin` отключён
- [ ] Парольный логин отключён или у меня есть осознанная причина его не отключать
- [ ] Я умею проверять `sshd_config` без риска запереть себя
- [ ] Я вижу следы неудачных входов в логах
