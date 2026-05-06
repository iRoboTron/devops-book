# Глава 4: Sysctl без поломки сервера

> **Цель:** применить разумные параметры ядра и проверить, что Docker/WireGuard не сломались.

---

## 4.1 Что такое sysctl

`sysctl` управляет настройками ядра Linux во время работы. Это мощно, но не безобидно: некоторые параметры влияют на маршрутизацию, VPN и контейнеры.

> **Аналогия:** sysctl — это настройки BIOS операционной системы. Можно ускорить работу, а можно случайно отключить сетевой стек. Меняй по одному параметру и сразу проверяй.

---

## 4.2 Базовый файл

`/etc/sysctl.d/99-hardening.conf`:

```ini
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
kernel.randomize_va_space = 2
```

`rp_filter` и forwarding применяй осторожно, если есть WireGuard, Docker NAT или маршрутизация.

---

## 4.3 Применение

```bash
sudo sysctl -p /etc/sysctl.d/99-hardening.conf
```

# Пример вывода:
```
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
kernel.randomize_va_space = 2
```

Каждая строка — параметр, который успешно применился. Если строки нет — параметр не поддерживается на этом ядре (не критично, просто зафиксируй).

Проверка отдельного параметра:

```bash
sysctl net.ipv4.tcp_syncookies
```

# Пример вывода:
```
net.ipv4.tcp_syncookies = 1
```

`= 1` означает включено. Если видишь `= 0` после применения — что-то пошло не так, проверь файл конфига.

Проверка после применения:

```bash
ssh user@server
curl -I https://yourdomain.com
sudo wg show
docker ps
```

---

## 4.4 Если что-то пошло не так

> **Если что-то пошло не так:**
>
> **Симптом:** После применения sysctl Docker-контейнеры потеряли сеть между собой или не могут выйти наружу.
>
> Частая причина: `net.ipv4.conf.all.send_redirects = 0` мешает Docker bridge-сети. Docker использует внутреннюю маршрутизацию через bridge, и запрет redirect-пакетов ломает передачу между контейнерами.
>
> **Шаги исправления:**
> 1. Проверь сеть контейнеров: `docker exec <container> curl -s http://другой-контейнер/`
> 2. Если не работает — закомментируй или удали из конфига строку `send_redirects`:
>    ```bash
>    sudo nano /etc/sysctl.d/99-hardening.conf
>    # закомментируй: # net.ipv4.conf.all.send_redirects = 0
>    ```
> 3. Применить изменения: `sudo sysctl -p /etc/sysctl.d/99-hardening.conf`
> 4. Перезапусти Docker: `sudo systemctl restart docker`
> 5. Проверь снова.
>
> **Симптом:** WireGuard перестал передавать трафик после применения sysctl.
>
> Проверь, не отключил ли ты IP forwarding: `sysctl net.ipv4.ip_forward` должно быть `= 1` если WireGuard маршрутизирует трафик.

---

## 4.5 Практика

Примени только понятный минимум. Запиши, что поменялось, и как откатить: удалить строку из файла и снова выполнить `sysctl -p`.
