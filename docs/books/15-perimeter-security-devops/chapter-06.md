# Глава 6: Fail2ban и CrowdSec

> **Запомни:** эти инструменты не делают сервер неуязвимым. Они автоматизируют реакцию на шум и массовые попытки злоупотребления.

---

## 6.1 Что решает fail2ban

Fail2ban читает логи и при совпадении шаблона:

- считает повторяющиеся ошибки;
- банит IP на время;
- добавляет сетевое ограничение через firewall backend.

Классический сценарий:

```text
5 неудачных SSH логинов с одного IP
-> бан на 1 час
```

Это полезно против автоматических ботов и дешёвого brute-force.

---

## 6.2 CrowdSec

Чтобы честно сравнивать fail2ban и CrowdSec, сначала нужен рабочий baseline на fail2ban. Тогда видно, какую задачу ты уже решил и за что именно будешь платить усложнением.

Базовая рабочая конфигурация fail2ban обычно лежит в `jail.local`, а не в `jail.conf`.

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 3
```

Что делает каждый параметр:
- `bantime = 1h` — IP останется заблокированным на один час;
- `findtime = 10m` — fail2ban считает ошибки в окне десять минут;
- `maxretry = 5` — пять ошибок в этом окне приводят к бану;
- `backend = systemd` — читать journald, а не текстовые файлы; для Ubuntu 22+ это обычно надёжнее;
- `[sshd]` — включаем защиту для SSH;
- `[nginx-http-auth]` — отдельная jail для HTTP-auth ошибок на фронте nginx.

После изменения файла:

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status
```

Ожидаемый результат:

```
Status
|- Number of jail: 2
`- Jail list: sshd, nginx-http-auth
```

Это значит, что fail2ban подхватил обе jail и реально начал наблюдать логи.

---

## 6.3 Где это полезнее всего

Практически это полезнее всего для:
- SSH;
- веб-логинов;
- noisy probing к чувствительным endpoints;
- повторяющихся 401/403/404 patterns при автоматическом сканировании.

Как выглядит бан в логах:

```bash
sudo journalctl -u fail2ban -n 20 --no-pager
```

Пример строк, которые нужно увидеть:

```
fail2ban.actions: NOTICE  [sshd] Ban 185.234.10.11
fail2ban.actions: NOTICE  [sshd] Unban 185.234.10.11
```

Проверка текущего состояния jail:

```bash
sudo fail2ban-client status sshd
```

Пример вывода:

```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 2
|  |- Total failed:     47
`- Actions
   |- Currently banned: 1
   |- Total banned:     8
   `- Banned IP list: 185.234.10.11
```

Как это читать:
- `Currently failed` — сколько событий уже накопилось, но ещё не дошло до бана;
- `Currently banned` — сколько IP заблокировано сейчас;
- `Total banned` — сколько раз jail уже срабатывала;
- `Banned IP list` — список адресов, которых firewall сейчас не пускает.

---

## 6.4 Практика с fail2ban

### Когда выбирать fail2ban, а когда CrowdSec

| Критерий | fail2ban | CrowdSec |
|---|---|---|
| Один VPS, один человек | да, обычно хватает | часто избыточно |
| Несколько серверов | каждый настраивать отдельно | удобнее централизовать |
| Только SSH | просто и быстро | тоже можно, но тяжелее |
| HTTP + API + SSH | возможно, но конфиги растут | удобнее как платформа |
| Community threat intelligence | нет | есть |
| Сложность старта | низкая | средняя |

Практический вывод:
- для первого VPS fail2ban — правильная отправная точка;
- CrowdSec имеет смысл, когда серверов больше одного или когда ты хочешь единый слой реакции на SSH и HTTP;
- если ты пока не читаешь логи и не умеешь подтвердить бан руками, CrowdSec будет преждевременным усложнением.

### Установить

```bash
sudo apt update
sudo apt install -y fail2ban
```

### Проверить статус

```bash
sudo systemctl status fail2ban
sudo fail2ban-client status
```

---

## 6.5 Практика: не заблокировать себя

Перед тестом:
- добавь свой административный IP в allow/ignore list, если это уместно;
- или тестируй с отдельной lab-машины;
- или будь готов зайти через консоль провайдера/VPS panel.

Это не мелочь. Самоблокировка — классическая ошибка при первом знакомстве с fail2ban.

---

## 6.6 Lab-only проверка

На своей второй машине в lab:

```bash
# Несколько заведомо неверных попыток входа
ssh wronguser@SERVER_IP
ssh wronguser@SERVER_IP
ssh wronguser@SERVER_IP
```

После этого проверь на сервере:

```bash
sudo fail2ban-client status sshd
sudo journalctl -u fail2ban -n 50 --no-pager
```

Ожидаемый результат — IP попадает в бан после configured threshold.

---

## 6.7 CrowdSec как следующий шаг

CrowdSec стоит рассматривать, если тебе нужно:
- гибче обрабатывать события;
- защищать не только SSH, но и HTTP-сценарии;
- иметь более современную модель реакций.

Типовая картина, где он уже оправдан:
- несколько VPS или несколько входных точек;
- есть reverse proxy и публичный HTTP/API;
- хочется учитывать внешнюю threat intelligence и общие сигналы по нескольким узлам.

Но для одного VPS fail2ban уже даёт много пользы, если ты реально читаешь логи и проверяешь результат руками.

---

## 6.8 Типовые ошибки

- ставить fail2ban и ни разу не проверять бан на своей lab;
- не смотреть, какие именно логи он читает;
- банить слишком агрессивно и ломать нормальных пользователей;
- забыть про allowlist для админского доступа;
- считать, что fail2ban заменяет firewall и SSH hardening.

---

## 6.9 Чеклист главы

- [ ] Я понимаю, что fail2ban и CrowdSec решают похожий класс задач
- [ ] Я умею проверить, что ban реально происходит
- [ ] Я знаю, как не заблокировать самого себя
- [ ] Я понимаю, что эти инструменты дополняют firewall и SSH hardening, а не заменяют их
