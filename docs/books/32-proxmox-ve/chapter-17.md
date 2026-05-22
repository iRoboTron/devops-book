# Глава 17: Безопасность Proxmox

> **Цель:** защитить Proxmox от типичных угроз — от брутфорса и открытых портов до незащищённых IoT-устройств в сети.

---

## Что вы узнаете

- что сделать сразу после установки, чтобы не взломали через неделю;
- как включить двухфакторную аутентификацию через веб-интерфейс;
- как настроить fail2ban для Proxmox — блокировать атаки автоматически;
- схему zero-trust изоляции трёх сетевых сегментов с правилами файрвола.

---

## 17.1 Почему безопасность Proxmox — это серьёзно

Proxmox управляет всем: виртуальными машинами, хранилищами, сетью, бэкапами. Если взломают хост — компрометируется всё, что на нём работает: Nextcloud с документами, Home Assistant с управлением замками, Vaultwarden с паролями.

Типичная картина небезопасного сервера:
```
Плохо:
root@proxmox ~ # ss -tlnp | grep 8006
LISTEN  0   ...   0.0.0.0:8006   *   pveproxy
```

Порт 8006 слушает на всех интерфейсах. Если Proxmox смотрит в интернет — это приглашение для ботов.

```
Лучше:
→ Proxmox недоступен из интернета напрямую
→ Доступ только через Tailscale (WireGuard туннель)
→ Пароль + двухфакторная аутентификация
→ fail2ban блокирует брутфорс автоматически
```

Три уровня защиты, которые разберём в этой главе:

1. Базовая гигиена — пароль, SSH ключи, закрыть root по паролю.
2. Аутентификация — TFA (TOTP) через веб-интерфейс.
3. Сеть — файрвол, Tailscale IP, VLAN zero-trust.

---

## 17.2 Что сделать сразу после установки

### Сменить пароль root

Если вы выбрали простой пароль при установке — исправьте это первым делом.

```bash
# На хосте Proxmox — эта команда меняет пароль пользователя root
passwd
```

Используйте пароль из менеджера паролей (Vaultwarden, Bitwarden). Длина — минимум 20 символов.

### SSH-ключи вместо пароля

Proxmox использует SSH для удалённого доступа к хосту. Аутентификация по паролю — слабое место.

**Шаг 1 — добавить публичный ключ на сервер:**
```bash
# На локальной машине — скопировать ключ на Proxmox-хост
ssh-copy-id root@192.168.1.100

# Или вручную добавить содержимое ~/.ssh/id_ed25519.pub в файл:
# /root/.ssh/authorized_keys
```

**Шаг 2 — отключить вход root по паролю:**
```bash
# Эта команда разрешает root логиниться только по SSH-ключу,
# а не по паролю — брутфорс пароля становится бесполезным
sed -i 's/^#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

# Применить изменение
systemctl restart sshd
```

**Проверить что изменилось:**
```bash
grep PermitRootLogin /etc/ssh/sshd_config
# Должно быть: PermitRootLogin prohibit-password
```

Теперь войти по SSH можно только с ключом — пароль не подойдёт.

### Обновить систему

Непропатченные уязвимости — один из самых частых векторов атак.

```bash
# Обновить Proxmox и все системные пакеты
apt update && apt full-upgrade -y
```

Если не подключён бесплатный репозиторий — перейдите к главе 1.

---

## 17.3 Двухфакторная аутентификация (TFA)

TFA — это второй слой защиты. Даже если пароль утёк — без второго фактора войти нельзя.

Proxmox поддерживает TOTP (Time-based One-Time Password) — это шестизначный код, который меняется каждые 30 секунд. Работает с любым приложением: Google Authenticator, Authy, 2FAS.

### Включение TFA через веб-интерфейс

1. Открыть веб-интерфейс: `https://IP:8006`
2. Перейти: **Datacenter → Users**
3. Выбрать пользователя (например `root@pam`)
4. Нажать кнопку **TFA**
5. Выбрать **TOTP**
6. Отсканировать QR-код приложением-аутентификатором
7. Ввести текущий код для подтверждения настройки

После этого при входе в Proxmox будет запрашиваться:
- пароль
- шестизначный TOTP-код

```
Пример экрана входа после включения TFA:
Username: root
Realm:    Linux PAM standard authentication
Password: ************
TOTP:     847 392    ← код из приложения
```

**Важно:** сохраните резервные коды или QR-код в безопасном месте (например в Vaultwarden). Если потеряете доступ к телефону с TFA — не сможете войти в интерфейс.

**Восстановление доступа если потерян TFA:**
```bash
# На хосте Proxmox через SSH или физический доступ — сбросить TFA
# Открыть файл конфигурации пользователей
cat /etc/pve/user.cfg | grep -A5 "root@pam"

# Удалить строку tfa= вручную через pveum
pveum user modify root@pam --remove-tfa
```

---

## 17.4 fail2ban — автоматическая блокировка брутфорса

fail2ban следит за логами и блокирует IP-адреса, которые делают слишком много неудачных попыток входа. После 3 провальных попыток — IP банится на час.

### Установка

```bash
# Установить fail2ban — менеджер автоматических банов по логам
apt install fail2ban -y
```

### Настройка jail для Proxmox

Proxmox использует демон `pvedaemon` для веб-аутентификации. Его логи пишутся в `/var/log/daemon.log`.

```bash
# Создать конфиг jail для Proxmox
# Этот файл говорит fail2ban: смотри логи Proxmox, банить после 3 попыток на час
cat > /etc/fail2ban/jail.d/proxmox.conf << 'EOF'
[proxmox]
enabled  = true
port     = https,8006
filter   = proxmox
logpath  = /var/log/daemon.log
maxretry = 3
bantime  = 3600
findtime = 600
EOF
```

### Создать фильтр для распознавания ошибок входа

```bash
# Этот фильтр описывает как выглядит ошибка аутентификации в логах Proxmox
cat > /etc/fail2ban/filter.d/proxmox.conf << 'EOF'
[Definition]
failregex = pvedaemon\[.*\]: authentication failure; rhost=<HOST> user=.* msg=.*
ignoreregex =
EOF
```

### Запустить и проверить

```bash
# Перезапустить fail2ban с новыми настройками
systemctl restart fail2ban

# Проверить что jail активен
fail2ban-client status proxmox
```

Пример вывода статуса:
```
Status for the jail: proxmox
|- Filter
|  |- Currently failed: 0
|  |- Total failed:     7
|  `- File list:        /var/log/daemon.log
`- Actions
   |- Currently banned: 1
   |- Total banned:     2
   `- Banned IP list:   203.0.113.45
```

**Проверить забаненные IP:**
```bash
fail2ban-client status proxmox | grep "Banned IP"
```

**Разбанить конкретный IP (если случайно попали свои):**
```bash
fail2ban-client set proxmox unbanip 203.0.113.45
```

---

## 17.5 Файрвол Proxmox — закрыть всё лишнее

Proxmox имеет встроенный файрвол, который управляется через веб-интерфейс. Он работает на уровне хоста, VM и LXC.

### Включить файрвол

1. Перейти: **Datacenter → Firewall**
2. Нажать **Options**
3. Установить **Firewall: Yes**

**Важно:** включайте файрвол только если вы зашли через Tailscale или напрямую к серверу. Не включайте удалённо через открытый порт без заранее добавленных правил разрешения — иначе заблокируете себе доступ.

### Логика правил

Файрвол Proxmox работает по принципу: всё запрещено, кроме явно разрешённого.

```
Правила читаются сверху вниз.
Первое совпавшее правило применяется.
Если ни одно не совпало — действует политика по умолчанию (DROP).
```

### Добавить правила через веб-интерфейс

Перейти: **Datacenter → Firewall → Add**

```
Правило 1: разрешить Proxmox веб-интерфейс с Tailscale-сети
  Direction:  in
  Action:     ACCEPT
  Protocol:   tcp
  Dest. port: 8006
  Source:     100.0.0.0/8    ← весь диапазон Tailscale IP (100.x.x.x)
  Comment:    Proxmox WebUI from Tailscale

Правило 2: разрешить SSH с Tailscale-сети
  Direction:  in
  Action:     ACCEPT
  Protocol:   tcp
  Dest. port: 22
  Source:     100.0.0.0/8
  Comment:    SSH from Tailscale

Правило 3: разрешить SSH из локальной сети (запасной вариант)
  Direction:  in
  Action:     ACCEPT
  Protocol:   tcp
  Dest. port: 22
  Source:     192.168.1.0/24
  Comment:    SSH from LAN
```

Итоговая схема правил:
```
IN  ACCEPT  tcp dport=8006  src=100.0.0.0/8     # Proxmox UI через Tailscale
IN  ACCEPT  tcp dport=22    src=100.0.0.0/8     # SSH через Tailscale
IN  ACCEPT  tcp dport=22    src=192.168.1.0/24  # SSH из LAN
IN  DROP    all                                  # всё остальное — блокировать
```

Теперь Proxmox недоступен из интернета напрямую. Только через Tailscale VPN — и только по авторизованным портам.

---

## 17.6 VLAN zero-trust — три сегмента сети

Zero-trust — это принцип: каждый сегмент сети не доверяет другому по умолчанию. Трафик разрешается явно, а не запрещается выборочно.

### Зачем изолировать Home Assistant и IoT

Home Assistant управляет физическими устройствами: умными розетками, замками, камерами. IoT-устройства часто имеют уязвимости и годами не получают обновлений. Без изоляции взломанная умная лампочка может получить доступ к Nextcloud с документами или к Proxmox.

```
Без изоляции:
Умная лампочка (VLAN нет) → arp-scan → видит Proxmox → атака на порт 8006

С изоляцией VLAN 30:
Умная лампочка → ограничена сегментом 192.168.30.0/24
→ не может достучаться до 192.168.10.x (Management) или 192.168.20.x (Services)
```

### Три VLAN-сегмента

```
VLAN 10 — Management (192.168.10.0/24)
  Что здесь: Proxmox :8006, SSH :22
  Кто имеет доступ: только с Tailscale IP или доверенных устройств
  Правило: входящий трафик из VLAN 20 и 30 — запрещён

VLAN 20 — Services (192.168.20.0/24)
  Что здесь: Nextcloud, Gitea, Vaultwarden
  Кто имеет доступ: из локальной сети и через Nginx Proxy Manager + HTTPS
  Правило: не имеет доступа к VLAN 10 (Management)

VLAN 30 — IoT (192.168.30.0/24)
  Что здесь: Home Assistant, умные розетки, IP-камеры
  Кто имеет доступ: только внутри VLAN 30 + явно разрешённые порты
  Правило: не может ходить в VLAN 10 или 20
```

### Настройка VLAN на мосту Proxmox

Редактировать `/etc/network/interfaces` на хосте Proxmox:

```
# Основной мост — разрешить все VLAN теги
auto vmbr0
iface vmbr0 inet manual
    bridge-ports enp3s0
    bridge-stp off
    bridge-fd 0
    bridge-vids 2-4094

# Management VLAN — для доступа к Proxmox
auto vmbr0.10
iface vmbr0.10 inet static
    address 192.168.10.1/24

# Services VLAN — для рабочих сервисов
auto vmbr0.20
iface vmbr0.20 inet static
    address 192.168.20.1/24

# IoT VLAN — изолированный сегмент
auto vmbr0.30
iface vmbr0.30 inet static
    address 192.168.30.1/24
```

Применить:
```bash
# Эта команда применит изменения сети без перезагрузки
ifreload -a
```

### Назначить VLAN контейнеру

```bash
# Home Assistant LXC — поместить в IoT VLAN 30
# Редактировать /etc/pve/lxc/200.conf или через веб:
# CT → Network → Edit → VLAN Tag: 30

# В файле конфига это выглядит так:
# net0: name=eth0,bridge=vmbr0,tag=30,ip=192.168.30.10/24,gw=192.168.30.1,type=veth
```

Через веб-интерфейс:
1. Выбрать контейнер с Home Assistant
2. **Hardware → Network Device → Edit**
3. Поле **VLAN Tag**: указать `30`

### Правила файрвола для VLAN 30 (IoT — максимальная изоляция)

Перейти к контейнеру Home Assistant: **CT 200 → Firewall → Add**

```
# Что разрешаем для IoT контейнера:
IN  ACCEPT  tcp dport=8123           # Home Assistant веб-интерфейс
IN  ACCEPT  tcp dport=1883           # MQTT брокер (если используется)
IN  ACCEPT  udp dport=5353           # mDNS для обнаружения устройств

# Что ЗАПРЕЩАЕМ — IoT не должен ходить в другие VLAN:
OUT DROP    dest=192.168.10.0/24     # нет доступа к Management
OUT DROP    dest=192.168.20.0/24     # нет доступа к Services
OUT ACCEPT  dest=0.0.0.0/0           # интернет разрешён (для обновлений HA)
```

Итоговая схема взаимодействия:
```
Интернет
    │
    ▼
Tailscale (WireGuard туннель)
    │
    ▼
VLAN 10 — Management (192.168.10.0/24)
    │  Proxmox :8006, SSH :22
    │  Доступ: только Tailscale IP
    │
    ├── VLAN 20 — Services (192.168.20.0/24)
    │       Nextcloud, Gitea, Vaultwarden
    │       ↓ может обращаться к интернету
    │       ✗ не может → VLAN 10
    │
    └── VLAN 30 — IoT (192.168.30.0/24)
            Home Assistant, умные устройства
            ↓ может обращаться к интернету
            ✗ не может → VLAN 10
            ✗ не может → VLAN 20
```

---

## 17.7 Мониторинг попыток входа

### Просмотр логов Proxmox вручную

```bash
# Неудачные попытки входа в Proxmox (pvedaemon)
grep "authentication failure" /var/log/daemon.log

# Пример вывода:
# May 23 03:47:12 proxmox pvedaemon[1234]: authentication failure;
#   rhost=203.0.113.45 user=root@pam msg=invalid credentials

# Неудачные попытки по SSH
journalctl -u sshd | grep "Failed password" | tail -20

# Пример вывода:
# May 23 04:12:07 proxmox sshd[5678]: Failed password for root
#   from 185.220.101.12 port 44231 ssh2

# Текущий статус блокировок fail2ban
fail2ban-client status proxmox
```

### Bash-скрипт: краткий отчёт о попытках взлома

```bash
cat > /usr/local/bin/pve-security-report << 'EOF'
#!/bin/bash
# Этот скрипт собирает краткую сводку по попыткам входа за последние 24 часа
# и выводит её в stdout или отправляет в Telegram

YESTERDAY=$(date -d "yesterday" "+%b %d")

echo "=== Отчёт безопасности Proxmox ==="
echo "Хост: $(hostname), дата: $(date)"
echo ""

echo "--- Неудачные входы в Proxmox (за 24ч) ---"
grep "$YESTERDAY" /var/log/daemon.log 2>/dev/null \
  | grep "authentication failure" \
  | awk '{print $NF}' \
  | sort | uniq -c | sort -rn | head -10

echo ""
echo "--- Заблокировано fail2ban ---"
fail2ban-client status proxmox 2>/dev/null \
  | grep -E "Currently banned|Banned IP"

echo ""
echo "--- Неудачные SSH попытки (топ-5 IP) ---"
journalctl -u sshd --since "24 hours ago" 2>/dev/null \
  | grep "Failed password" \
  | grep -oP 'from \K[\d.]+' \
  | sort | uniq -c | sort -rn | head -5
EOF

chmod +x /usr/local/bin/pve-security-report
```

Запустить вручную:
```bash
/usr/local/bin/pve-security-report
```

Добавить в cron — получать отчёт каждое утро в 08:00:
```bash
echo "0 8 * * * root /usr/local/bin/pve-security-report | \
  /usr/local/bin/tg-notify \"\$(cat)\"" \
  > /etc/cron.d/pve-security-report
```

(Скрипт `tg-notify` описан в главе 19.)

---

## 17.8 Типичные ошибки

| Ошибка | Как проявляется | Решение |
|--------|----------------|---------|
| Включил файрвол и потерял доступ | После включения файрвола не открывается :8006 | Зайти физически на сервер или через KVM-консоль, добавить правило ACCEPT для своего IP |
| Заблокировал себя в fail2ban | Ввёл неверный пароль 3 раза, доступ пропал | SSH на сервер → `fail2ban-client set proxmox unbanip ВАШ_IP` |
| TFA включён, телефон потерян | Не можете войти в веб-интерфейс | SSH на сервер → `pveum user modify root@pam --remove-tfa` |
| VLAN настроен, контейнер не выходит в сеть | Нет интернета в LXC с тегом VLAN | Проверить gateway в конфиге LXC: `cat /etc/pve/lxc/ID.conf` |
| SSH ключ не принимается | Permission denied (publickey) | Проверить права: `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` |

---

## 17.9 Итоговая схема защиты

После всех настроек из этой главы ваш Proxmox выглядит так:

```
Снаружи:
  Internet → порты закрыты → ничего не видно

Легитимный доступ:
  Телефон/ноутбук → Tailscale → Proxmox :8006
  Пароль + TOTP-код (двухфакторка)
  Только с Tailscale IP (файрвол)

Автоматическая защита:
  fail2ban: 3 неудачные попытки → бан на 1 час
  SSH: только по ключу, пароли не принимаются

Сетевая изоляция:
  VLAN 10 (Management) — только для администрирования
  VLAN 20 (Services) — рабочие сервисы, нет доступа в VLAN 10
  VLAN 30 (IoT) — полная изоляция от других сегментов

Мониторинг:
  Ежедневный отчёт в Telegram: кто пытался войти и кого заблокировали
```

---

## Практика

1. Сменить пароль root. Добавить SSH-ключ. Проверить что вход по паролю закрыт (`ssh -o PasswordAuthentication=no root@IP` должен отклонить).

2. Включить TFA для учётной записи. Выйти из системы, зайти снова — убедиться что запрашивается TOTP-код.

3. Установить fail2ban, создать jail для Proxmox. Проверить `fail2ban-client status proxmox`.

4. Включить файрвол Proxmox. Добавить правила для Tailscale IP и заблокировать всё остальное.

5. Запустить скрипт `pve-security-report` и изучить вывод.

---

## Чек-лист для самопроверки

- [ ] SSH root по паролю отключён (`PermitRootLogin prohibit-password` в sshd_config)
- [ ] SSH-ключ добавлен и вход без пароля работает
- [ ] TFA включён для основного пользователя, резервные коды сохранены
- [ ] fail2ban установлен, jail `proxmox` активен (`fail2ban-client status proxmox`)
- [ ] Файрвол Proxmox включён: правила разрешают только Tailscale IP на порты 8006 и 22
- [ ] Понимаю схему zero-trust: три VLAN, что каждый может и что не может
- [ ] Скрипт `pve-security-report` запускается без ошибок
