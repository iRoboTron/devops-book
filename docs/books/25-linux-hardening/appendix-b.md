# Приложение B: Чеклист отката

Перед каждым изменением заполни:

| Изменение | Где меняю | Как проверить | Как откатить |
|---|---|---|---|
| SSH config | `/etc/ssh/sshd_config` | `sshd -t`, новый вход | вернуть файл, restart ssh |
| UFW | `ufw` rules | `ufw status`, SSH | `ufw delete`, консоль провайдера |
| sysctl | `/etc/sysctl.d/...` | `sysctl`, сервисы | удалить строку, `sysctl -p` |
| Docker ports | `compose.yml` | `docker compose ps`, curl | вернуть ports, up -d |

## Красные флаги

- Нет второго SSH-сеанса.
- Нет доступа к консоли провайдера.
- Меняется SSH и firewall одновременно.
- Команда скопирована без понимания.
- Нет проверки после изменения.

## Быстрые команды отката

**Разблокировать себя в fail2ban:**
```bash
sudo fail2ban-client unban ВАШ_IP
```

**Восстановить sudo для пользователя:**
```bash
pkexec usermod -aG sudo yourusername
# или через recovery mode / консоль провайдера
```

**Откатить sysctl без перезагрузки:**
```bash
# Закомментируй строку в файле, затем:
sudo sysctl -p /etc/sysctl.d/99-hardening.conf
```

**Временно выключить firewall:**
```bash
sudo ufw disable
# восстановить SSH, затем:
sudo ufw enable
```

**Восстановить dpkg после зависшего обновления:**
```bash
sudo dpkg --configure -a
sudo apt -f install
```

## План внедрения

### За 1 день

SSH, firewall, fail2ban.

### За 1 неделю

Обновления, пользователи, lynis до/после.

### За 1 месяц

Docker hardening, sysctl, документация и регулярный пересмотр.
