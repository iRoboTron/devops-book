# Глава 4: Firewall и безопасный порядок действий

> **Цель:** разрешить VPN и не заблокировать себе SSH.

---

## 4.1 Безопасный порядок

1. Открыть второй SSH-сеанс.
2. Разрешить WireGuard UDP-порт.
3. Проверить подключение клиента.
4. Только потом закрывать или ограничивать сервисы.

```bash
sudo ufw allow 51820/udp
```

```bash
# Пример вывода:
Rules updated
Rules updated (v6)
```

```bash
sudo ufw status verbose
```

```bash
# Пример вывода:
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
51820/udp                  ALLOW IN    Anywhere
22/tcp (v6)                ALLOW IN    Anywhere (v6)
51820/udp (v6)             ALLOW IN    Anywhere (v6)
```

---

## 4.2 Учебный простой вариант

```bash
sudo ufw allow in on wg0
sudo ufw allow out on wg0
```

Это удобно для старта, но широко. На реальном сервере лучше разрешать только нужное.

---

## 4.3 Более аккуратный вариант

```bash
sudo ufw allow in on wg0 to any port 22 proto tcp
sudo ufw allow in on wg0 to any port 443 proto tcp
sudo ufw allow in on wg0 to any port 3000 proto tcp
```

Так сервисы доступны через VPN, но не обязательно открыты всем.

---

## 4.4 Nginx только на VPN-IP

```nginx
server {
    listen 10.0.0.1:80;
    server_name grafana.internal;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

Это сильнее, чем просто firewall: сервис физически слушает только VPN-адрес.

---

---

## 4.6 Самая частая ошибка — заблокировать SSH

> **Если что-то пошло не так: потерян SSH-доступ после изменений ufw**

Симптом: после `sudo ufw enable` или добавления правил терминал завис, новый SSH не открывается.

Причина: SSH (порт 22) не был явно разрешён до включения ufw, или случайно удалено правило `22/tcp`.

**Восстановление через консоль провайдера:**

1. Открой веб-консоль (VNC/KVM) сервера в панели провайдера — она не зависит от SSH и firewall.
2. Залогинься как root.
3. Проверь текущее состояние: `sudo ufw status numbered`.
4. Разрешь SSH: `sudo ufw allow 22/tcp`.
5. Проверь, что правило появилось: `sudo ufw status verbose`.
6. Попробуй открыть новый SSH-сеанс.

**Профилактика:**
```bash
# ПЕРЕД включением ufw — убедись, что SSH уже разрешён:
sudo ufw allow 22/tcp
sudo ufw enable
# ufw enable спросит подтверждение, нажми y
```

---

## 4.5 Практика

Выбери один внутренний сервис и сделай так, чтобы он открывался через VPN. Проверка: с телефона через LTE и включённый VPN сервис открывается, без VPN — нет.