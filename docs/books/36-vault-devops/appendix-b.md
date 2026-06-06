# Приложение B: Типичные ошибки и диагноз

| Симптом | Причина | Проверка | Решение |
|---|---|---|---|
| `403 Forbidden` | Нет прав на path | `vault token capabilities TOKEN secret/data/myapp` | Расширить политику |
| `sealed vault` | Vault после перезапуска | `vault status` | `vault operator unseal` |
| `token expired` | TTL истёк | `vault token lookup TOKEN` | Создать новый токен |
| `lease expired` | Dynamic credentials истекли | `vault lease renew LEASE_ID` | Получить новые creds |
| `database credentials rejected` | vault_admin без CREATEROLE | `psql -c "\du" vault_admin` | `ALTER ROLE vault_admin CREATEROLE` |
| `K8s auth failed` | Namespace не совпадает | `vault read auth/kubernetes/role/NAME` | Исправить `bound_service_account_namespaces` |
| `Agent не рендерит шаблон` | Agent не может читать секрет | `vault token capabilities TOKEN secret/data/…` | Дать права на path |
| `secret not found` | Неверный path (secret vs data) | `vault kv get secret/…` | Исправить на `secret/data/…` |
| `connection refused` | VAULT_ADDR не установлен | `echo $VAULT_ADDR` | `export VAULT_ADDR=http://…` |
| `root token lost` | Не сохранён | — | `vault operator generate-root` |
| `error writing data: unexpected EOF` | Standby узел не в HA-режиме | `vault read sys/ha-status` | Перенаправить запрос на active node |
| `permission denied: namespace` | Не передан namespace | `echo $VAULT_NAMESPACE` | `export VAULT_NAMESPACE=ns1` |
