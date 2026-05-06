# Глава 1: SSH hardening

> **Цель:** защитить главный вход на сервер и не заблокировать себя.

---

## 1.1 Перед изменениями

Обязательно:

- открой второй SSH-сеанс;
- проверь, что вход по ключу работает;
- не закрывай текущий сеанс до проверки;
- знай, где консоль провайдера.

> **Аналогия:** Менять замок на входной двери — нужно держать запасной ключ в руке, пока не убедишься, что новый работает. Иначе рискуешь закрыть себя снаружи.

---

## 1.2 Настройки sshd

Файл: `/etc/ssh/sshd_config`.

```text
PasswordAuthentication no
PermitRootLogin no
AllowUsers yourusername
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowAgentForwarding no
```

`AllowUsers` опасен при ошибке в имени. Применяй только если уверен и держишь второй сеанс открытым.

Менять порт SSH можно, но это не настоящая защита. Это снижает шум в логах. Настоящая защита — ключи, запрет паролей, firewall и обновления.

---

## 1.3 Безопасное применение

```bash
sudo sshd -t
```

# Пример вывода (успех — ничего):
```
(нет вывода)
```

# Пример вывода (ошибка синтаксиса):
```
/etc/ssh/sshd_config: line 15: Bad configuration option: PasswordAuthenticaton
/etc/ssh/sshd_config: terminating, 1 bad configuration options
```

Если вывод пустой — файл без ошибок, можно применять. Если есть строки с ошибкой — исправь сначала, рестарт не делай.

```bash
sudo systemctl restart ssh
```

# Пример вывода:
```
(нет вывода — это хорошо, сервис перезапустился без ошибок)
```

Проверка статуса:

```bash
systemctl status ssh
```

# Пример вывода:
```
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/lib/systemd/system/ssh.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-05-05 14:32:11 UTC; 5s ago
    Process: 12481 ExecStartPre=/usr/sbin/sshd -t (code=exited, status=0/SUCCESS)
   Main PID: 12482 (sshd)
      Tasks: 1 (limit: 1141)
     Memory: 2.1M
        CPU: 18ms
     CGroup: /system.slice/ssh.service
             └─12482 sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups
```

`Active: active (running)` — сервис работает. Если видишь `failed` — сразу смотри в старый сеанс.

Проверка в новом окне:

```bash
ssh user@server
```

Только после успешного входа закрывай старую сессию.

---

## 1.4 Если что-то пошло не так

> **Если что-то пошло не так:**
>
> **Симптом:** После `systemctl restart ssh` второе окно не подключается — висит или выдаёт `Connection refused`.
>
> **Шаги исправления (в старом открытом сеансе):**
>
> 1. Проверь синтаксис конфига (если ещё не делал):
>    ```bash
>    sudo sshd -t
>    ```
> 2. Посмотри статус сервиса:
>    ```bash
>    sudo systemctl status ssh
>    ```
>    Ищи строки `failed` или конкретную ошибку в скобках.
> 3. Посмотри свежие логи:
>    ```bash
>    sudo journalctl -u ssh -n 30 --no-pager
>    ```
> 4. Если нашёл проблему — исправь файл и повтори рестарт.
> 5. Если старый сеанс уже закрыт и доступа нет — используй консоль провайдера (VNC/KVM доступ в панели управления VPS). Там можно войти без SSH и исправить конфиг.

---

## 1.5 Как убедиться что парольный вход отключён

```bash
ssh -o PreferredAuthentications=password user@server
```

# Пример вывода:
```
user@server: Permission denied (publickey).
```

Это правильный результат — сервер отказал в парольном входе и предложил только publickey. Если вход по паролю всё ещё работает, значит `PasswordAuthentication no` не применилось — проверь, нет ли конфликтующей директивы в `/etc/ssh/sshd_config.d/`.

---

## 1.6 Практика

Сделай минимум:

- вход по ключу работает;
- парольный вход отключён;
- root login отключён;
- синтаксис `sshd_config` проверен.

Если что-то пошло не так, возвращайся через старый SSH-сеанс или консоль провайдера.
