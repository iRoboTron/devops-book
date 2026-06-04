# Приложение A: Шпаргалка команд

## Базовые операции
| Комментарий | Команда |
|---|---|
| Статус Vault | `vault status` |
| Список включённых secrets engines | `vault secrets list` |
| Список включённых auth methods | `vault auth list` |

## KV v2
| Комментарий | Команда |
|---|---|
| Записать секрет | `vault kv put secret/data/myapp key=value` |
| Прочитать секрет | `vault kv get secret/data/myapp` |
| Обновить отдельное поле | `vault kv patch secret/data/myapp key=newvalue` |
| Удалить последнюю версию | `vault kv delete secret/data/myapp` |
| Восстановить удалённую версию | `vault kv undelete -versions=2 secret/data/myapp` |
| Полностью стереть версию | `vault kv destroy -versions=2 secret/data/myapp` |
| Метаданные секрета | `vault kv metadata get secret/data/myapp` |
| Удалить метаданные | `vault kv metadata delete secret/data/myapp` |
| Список ключей по пути | `vault kv list secret/data/` |

## Политики
| Комментарий | Команда |
|---|---|
| Создать/обновить политику из HCL | `vault policy write myapp -<<EOF` … `EOF` |
| Прочитать политику | `vault policy read myapp` |
| Список политик | `vault policy list` |
| Удалить политику | `vault policy delete myapp` |
| Проверить capabilities токена | `vault token capabilities TOKEN secret/data/myapp` |

## Auth Methods
| Комментарий | Команда |
|---|---|
| Создать токен | `vault token create -policy=myapp -ttl=1h` |
| Продлить токен | `vault token renew TOKEN` |
| Отозвать токен | `vault token revoke TOKEN` |
| Информация о токене | `vault token lookup TOKEN` |
| AppRole: login | `vault write auth/approle/login role_id=… secret_id=…` |
| AppRole: создать/прочитать роль | `vault write auth/approle/role/myapp …` / `vault read auth/approle/role/myapp` |
| AppRole: сгенерировать secret-id | `vault write -f auth/approle/role/myapp/secret-id` |
| Userpass: создать пользователя | `vault write auth/userpass/users/alice password=pass policies=myapp` |
| Userpass: обновить пользователя | `vault write auth/userpass/users/alice policies=myapp,admin` |

## AppRole
| Комментарий | Команда |
|---|---|
| Создать AppRole-роль | `vault write auth/approle/role/myapp token_policies=myapp` |
| Получить RoleID | `vault read auth/approle/role/myapp/role-id` |
| Создать SecretID | `vault write -f auth/approle/role/myapp/secret-id` |
| Залогиниться через AppRole | `vault write auth/approle/login role_id=… secret_id=…` |

## Kubernetes Auth
| Комментарий | Команда |
|---|---|
| Включить k8s auth | `vault auth enable kubernetes` |
| Настроить конфиг | `vault write auth/kubernetes/config token_reviewer_jwt=… kubernetes_host=… kubernetes_ca_cert=@ca.crt` |
| Создать роль | `vault write auth/kubernetes/role/myapp bound_service_account_names=myapp bound_service_account_namespaces=default policies=myapp ttl=1h` |

## Database Engine
| Комментарий | Команда |
|---|---|
| Включить database engine | `vault secrets enable database` |
| Настроить подключение | `vault write database/config/my-pg plugin_name=postgresql-db-plugin allowed_roles=myapp connection_url="postgresql://{{username}}:{{password}}@host:5432/db" username=vault_admin password=…` |
| Создать роль | `vault write database/roles/myapp db_name=my-pg creation_statements=… default_ttl=1h max_ttl=24h` |
| Получить dynamic credentials | `vault read database/creds/myapp` |

## PKI Engine
| Комментарий | Команда |
|---|---|
| Сгенерировать корневой сертификат | `vault secrets enable -path=pki pki` + `vault write pki/root/generate/internal common_name=example.com ttl=87600h` |
| Создать промежуточный CSR | `vault write pki_int/intermediate/generate/internal common_name=example.com Intermediate` |
| Подписать промежуточный CSR корнем | `vault write pki/root/sign-intermediate csr=@csr.pem` |
| Установить подписанный сертификат | `vault write pki_int/intermediate/set-signed certificate=@signed.pem` |
| Выпустить сертификат | `vault write pki_int/issue/internal-services common_name=svc.example.com ttl=24h` |

## Transit
| Комментарий | Команда |
|---|---|
| Зашифровать данные | `vault write transit/encrypt/mykey plaintext=$(base64 <<<"data")` |
| Расшифровать данные | `vault write transit/decrypt/mykey ciphertext=…` |
| Ротация ключа | `vault write -f transit/keys/mykey/rotate` |
| Перешифровка (rewrap) | `vault write transit/rewrap/mykey ciphertext=…` |

## Vault Agent
| Комментарий | Команда |
|---|---|
| Запустить Agent | `vault agent -config=agent.hcl` |
| Шаблон (template) | `{{ with secret "secret/data/myapp" }}{{ .Data.data.key }}{{ end }}` |

## HA / Operator
| Комментарий | Команда |
|---|---|
| Инициализировать кластер | `vault operator init -key-shares=5 -key-threshold=3` |
| Распечатать unseal key | `vault operator unseal KEY` |
| Присоединить Raft-узел | `vault operator raft join http://leader:8200` |
| Список Raft-пиров | `vault operator raft list-peers` |
| Сохранить snapshot | `vault operator raft snapshot save backup.snap` |
| Восстановить snapshot | `vault operator raft snapshot restore backup.snap` |
| Сгенерировать root-токен | `vault operator generate-root -init` |
| Перевыпустить unseal keys | `vault operator rekey -init` |

## Audit
| Комментарий | Команда |
|---|---|
| Включить audit | `vault audit enable file file_path=/var/log/vault_audit.log` |
| Отключить audit | `vault audit disable file` |
| Запись audit с HMAC accessor | `hmac_accessor=true` (по умолчанию включено) |
