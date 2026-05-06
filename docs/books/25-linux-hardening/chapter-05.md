# Глава 5: Обновления

> **Цель:** сервер получает security-патчи без хаоса.

---

## 5.1 Почему обновления важнее экзотики

Большинство реальных проблем начинается не с сложной атаки, а со старого пакета, открытого сервиса или забытого контейнера.

> **Аналогия:** Поставить экзотический firewall и не обновлять систему месяцами — как установить сигнализацию на машину и оставить окно открытым. Обновления — это закрытое окно.

---

## 5.2 unattended-upgrades

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Dry-run:

```bash
sudo unattended-upgrade --dry-run -v
```

# Пример вывода:
```
Starting unattended upgrades script
Allowed origins are: o=Ubuntu,a=focal, o=Ubuntu,a=focal-security, o=UbuntuESM,a=focal-infra-security
Checking: libssl1.1 (1.1.1f-1ubuntu2.19 -> 1.1.1f-1ubuntu2.22)
Checking: openssh-server (1:8.2p1-4ubuntu0.9 -> 1:8.2p1-4ubuntu0.11)
Checking: linux-image-5.4.0-169-generic (5.4.0-169.187 -> 5.4.0-174.193)
Packages that will be upgraded: libssl1.1 openssh-server linux-image-5.4.0-169-generic
Packages that will NOT be automatically removed: 0
...
This is a dry run, no changes will be applied.
```

Ключевые строки: `Packages that will be upgraded` — что реально обновится. Если вывод пустой — всё уже актуально.

Логи:

```bash
sudo tail -100 /var/log/unattended-upgrades/unattended-upgrades.log
```

# Пример вывода:
```
2025-05-04 06:34:01,215 INFO Starting unattended upgrades script
2025-05-04 06:34:01,892 INFO Packages that will be upgraded: libssl1.1 openssh-server
2025-05-04 06:34:05,441 INFO Fetched 1,240 kB in 2s (558 kB/s)
2025-05-04 06:34:08,112 INFO Installing changes...
2025-05-04 06:34:12,557 INFO Packages that were successfully installed: libssl1.1 openssh-server
2025-05-04 06:34:12,559 INFO All upgrades installed
```

---

## 5.3 Reboot policy

Автоматический reboot удобен, но может перезапустить сервис в неподходящий момент. Для личного сервера часто лучше:

- security updates автоматически;
- reboot вручную в понятное время;
- уведомление, если нужен reboot.

Проверка:

```bash
test -f /var/run/reboot-required && cat /var/run/reboot-required || echo "reboot not required"
```

---

## 5.4 Если что-то пошло не так

> **Если что-то пошло не так:**
>
> **Симптом:** `unattended-upgrade` завис — процесс работает много часов, обновление не заканчивается, apt блокирован.
>
> Частая причина: прерванное предыдущее обновление оставило dpkg в незавершённом состоянии.
>
> **Шаги исправления:**
> 1. Проверь, есть ли зависший процесс:
>    ```bash
>    ps aux | grep -E "apt|dpkg|unattended"
>    ```
> 2. Если процесс завис — дождись завершения или убей осторожно (не kill -9).
> 3. Восстанови dpkg:
>    ```bash
>    sudo dpkg --configure -a
>    ```
> 4. Почини возможные проблемы с зависимостями:
>    ```bash
>    sudo apt -f install
>    ```
> 5. Проверь лог на ошибки:
>    ```bash
>    sudo tail -50 /var/log/dpkg.log
>    ```
> 6. Повтори обновление: `sudo apt upgrade`

---

## 5.5 Практика

Включи security updates, сделай dry-run, проверь логи. Не включай автоматический reboot, пока не понимаешь последствия для своих сервисов.
