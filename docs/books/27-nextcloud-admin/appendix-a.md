# Приложение A: Команды occ

```bash
# Статус и диагностика
occ status
occ system:check

# Приложения
occ app:list
occ app:install <name>
occ app:enable <name>
occ app:disable <name>
occ app:remove <name>
occ app:update --all

# Пользователи
occ user:list
occ user:info <username>
occ user:add --password-from-env --display-name="Name" <username>
occ user:disable <username>
occ user:enable <username>
occ user:delete <username>
occ user:resetpassword <username>
occ user:setting <username> files quota 10GB

# Группы
occ group:list
occ group:add <group>
occ group:adduser <group> <username>

# Maintenance
occ maintenance:mode --on
occ maintenance:mode --off
occ maintenance:repair

# База данных
occ db:add-missing-indices
occ db:add-missing-columns
occ db:convert-filecache-bigint

# Файлы
occ files:scan --all --unscanned
occ files:scan --user <username>

# Конфигурация
occ config:system:get trusted_domains
occ config:system:get trusted_proxies
occ config:system:get overwriteprotocol
occ config:system:set trusted_domains 1 --value="nextcloud.yourdomain.com"
occ config:system:set trusted_proxies 0 --value="172.17.0.0/16"
occ config:system:set overwriteprotocol --value="https"
occ config:system:get redis
```

## Функция

```bash
occ() {
  docker exec --user www-data nextcloud-aio-nextcloud php occ "$@"
}
```

Замени имя контейнера на своё, если оно отличается. Добавить в `~/.bashrc` после проверки вручную.

## Пример добавления в ~/.bashrc

```bash
# Nextcloud occ shortcut
occ() {
  docker exec --user www-data nextcloud-aio-nextcloud php occ "$@"
}
```

После добавления: `source ~/.bashrc`, затем проверить: `occ status`.
