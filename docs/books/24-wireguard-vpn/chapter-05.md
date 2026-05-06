# Глава 5: Автозапуск через systemd

> **Цель:** WireGuard поднимается после перезагрузки сам.

---

## 5.1 Сервис wg-quick

> *Systemd для WireGuard — как автозапуск приложения при входе в систему: настроил один раз, и оно само поднимается при каждой перезагрузке сервера.*

WireGuard-конфиг `/etc/wireguard/wg0.conf` можно запускать через systemd:

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
systemctl status wg-quick@wg0
```

```bash
# Пример вывода systemctl status:
● wg-quick@wg0.service - WireGuard via wg-quick(8) for wg0
     Loaded: loaded (/lib/systemd/system/wg-quick@.service; enabled; vendor preset: enabled)
     Active: active (exited) since Mon 2024-01-15 12:34:56 UTC; 2min 10s ago
       Docs: man:wg-quick(8)
             man:wg(8)
             https://www.wireguard.com/
             https://www.wireguard.com/quickstart/
             https://git.zx2c4.com/wireguard-tools/about/src/man/wg-quick.8
             https://git.zx2c4.com/wireguard-tools/about/src/man/wg.8
    Process: 1234 ExecStart=/usr/bin/wg-quick up wg0 (code=exited, status=0/SUCCESS)
   Main PID: 1234 (code=exited, status=0/SUCCESS)

Jan 15 12:34:56 myserver systemd[1]: Starting WireGuard via wg-quick(8) for wg0...
Jan 15 12:34:56 myserver wg-quick[1234]: [#] ip link add wg0 type wireguard
Jan 15 12:34:56 myserver wg-quick[1234]: [#] ip -4 address add 10.0.0.1/24 dev wg0
Jan 15 12:34:56 myserver wg-quick[1234]: [#] ip link set mtu 1420 up dev wg0
Jan 15 12:34:56 myserver systemd[1]: Finished WireGuard via wg-quick(8) for wg0.
```

Статус `active (exited)` — это нормально для wg-quick. Сервис запустил интерфейс и завершился, сам интерфейс `wg0` продолжает работать.

---

## 5.2 Безопасное изменение конфига

Перед перезапуском:

```bash
sudo wg-quick strip wg0
sudo wg show
```

После правок:

```bash
sudo systemctl restart wg-quick@wg0
sudo wg show
```

Если это удалённый сервер, не меняй firewall и WireGuard одновременно.

---

## 5.3 Проверка после reboot

```bash
sudo reboot
```

После возвращения сервера:

```bash
ssh user@server
sudo wg show
```

```bash
# Пример вывода после reboot — туннель поднялся автоматически:
interface: wg0
  public key: 8J3vQkLmN2+XpR7tYwZ5aB1cDfGhIjKoMnOpQrSt4U=
  private key: (hidden)
  listening port: 51820

peer: mB4nRsT1qWoP9uYiL6jKxZ3cFvGhDeNaE8sCpA2lO=
  endpoint: 192.0.2.45:49182
  allowed ips: 10.0.0.2/32
  latest handshake: 37 seconds ago
  transfer: 820 B received, 652 B sent
```

```bash
systemctl status wg-quick@wg0
```

> **Если что-то пошло не так: сервис не стартует после reboot**
>
> Симптом: `sudo wg show` возвращает ошибку «Cannot find device wg0», а `systemctl status wg-quick@wg0` показывает `failed`.
>
> Диагностика:
> ```bash
> journalctl -u wg-quick@wg0 --since "10 minutes ago"
> ```
>
> Типичные причины в логах:
> - `RTNETLINK answers: File exists` — интерфейс уже поднят вручную или дублирующий сервис. Выполни `sudo wg-quick down wg0` и перезапусти сервис.
> - `PrivateKey: invalid key` — конфиг изменился или повреждён. Проверь `/etc/wireguard/wg0.conf`.
> - `Cannot open /etc/wireguard/wg0.conf: No such file or directory` — конфиг не существует или не то имя. Проверь `ls /etc/wireguard/`.

---

## 5.4 Практика

Включи автозапуск, перезагрузи сервер в удобное время и проверь VPN. Практика завершена, если после reboot клиент снова подключается без ручного `wg-quick up`.