# Приложение A: Шаблон отчёта

## A.1 Пустой шаблон

```markdown
# Аудит сервера — YYYY-MM-DD

## Scope
- IP:
- Domain:
- Owner:
- What is included:
- What is excluded:

## Периметр
| Port | Service | Expected | Evidence | Action |

## TLS
| Check | Result | Evidence | Action |

## Headers
| Header | Present | Action |

## Web scan
| Finding | Real? | Evidence | Action |

## Docker
| Image | Critical | High | Action |

## Lynis
- Hardening index:
- Top warnings:

## Logs
| Fact | Source | Action |

## Findings
| Priority | Finding | Evidence | Action | Status |

## Next audit
- Date:
```

---

## A.2 Заполненный пример отчёта

```markdown
# Аудит сервера — 2026-05-06

## Scope
- IP: 203.0.113.42
- Domain: myapp.example.com
- Owner: Иван Петров (ivan@example.com)
- Включено: внешний периметр (nmap), TLS, HTTP headers, web scan (nikto),
            Docker образы (trivy), системный аудит (lynis), SSH и nginx логи
- Исключено: внутренняя сеть, база данных, код приложения

## Периметр
| Port | Service | Expected | Evidence | Action |
|---|---|---|---|---|
| 22/tcp | OpenSSH 8.9p1 | yes | nmap-versions.txt | ограничить по IP в ufw |
| 80/tcp | nginx 1.24.0 | yes | nmap-versions.txt | redirect to HTTPS, ok |
| 443/tcp | nginx 1.24.0 | yes | nmap-versions.txt | проверить TLS |
| 8080/tcp | Node.js dev server | **no** | nmap-versions.txt | **закрыть немедленно** |

## TLS
| Check | Result | Evidence | Action |
|---|---|---|---|
| TLS 1.0 | **enabled** | testssl.txt line 12 | убрать из ssl_protocols |
| TLS 1.1 | disabled | testssl.txt | ок |
| TLS 1.2 | enabled | testssl.txt | ок |
| TLS 1.3 | enabled | testssl.txt | ок |
| Cert expiry | 2027-03-15 | testssl.txt | добавить напоминание |
| HSTS | not set | testssl.txt | включить после проверки |
| Grade | B → ожидается A после TLS 1.0 fix | testssl.txt | — |

## Headers
| Header | Present | Action |
|---|---|---|
| X-Frame-Options | нет | добавить SAMEORIGIN |
| X-Content-Type-Options | нет | добавить nosniff |
| Referrer-Policy | нет | добавить strict-origin-when-cross-origin |
| X-Powered-By | PHP/8.1.0 — раскрывает версию | скрыть fastcgi_hide_header |
| Server | nginx/1.24.0 | server_tokens off |

## Web scan (nikto)
| Finding | Real? | Evidence | Action |
|---|---|---|---|
| X-Powered-By: PHP/8.1.0 | yes | nikto.txt, headers.txt | скрыть |
| X-XSS-Protection отсутствует | false positive (устарел) | — | игнорировать |
| /phpmyadmin/ | no (404) | curl -I → 404 | false positive |
| /admin/ | partial (302 → login) | curl -I → 302 | ок, авторизация есть |
| /backup/ (листинг) | **yes (200)** | curl → Index of /backup/ | **закрыть немедленно** |

## Docker
| Image | Critical | High | Action |
|---|---|---|---|
| nginx:latest | 1 (CVE-2024-0727) | 3 | обновить до nginx:1.27-alpine |
| myapp:v1.2 | 0 | 1 (libexpat1) | rebuild при следующем релизе |
| postgres:15 | 0 | 0 | ок |

## Lynis
- Hardening index: 58 (цель после исправлений: 70+)
- SSH PermitRootLogin: yes → исправить
- ufw: не настроен → включить
- Pending updates: 12 пакетов → apt upgrade

## Logs
| Fact | Source | Action |
|---|---|---|
| 847 Failed SSH от 185.220.101.47 | auth.log | fail2ban активен, ок |
| /backup/ запрошен ботом, вернул 200 | nginx/access.log | закрыть /backup/ |
| Успешные SSH только с 203.0.113.100 | auth.log | ок |

## Итоговые находки
| Priority | Finding | Evidence | Action | Status |
|---|---|---|---|---|
| **Critical** | /backup/ открыт с листингом | nikto.txt, nginx access.log | nginx deny all /backup/ | ✅ 2026-05-06 |
| **High** | 8080 открыт (dev server) | nmap-versions.txt | ufw deny 8080, kill pid 1842 | ✅ 2026-05-06 |
| **High** | TLS 1.0 включён | testssl.txt | убрать TLSv1 из nginx ssl_protocols | 🔄 |
| **High** | CVE-2024-0727 CRITICAL nginx:latest | trivy-nginx.txt | обновить образ | 📅 2026-05-07 |
| **Medium** | SSH PermitRootLogin yes | lynis.txt | PermitRootLogin no | 📅 |
| **Medium** | Отсутствуют security headers | headers.txt | добавить в nginx.conf | 📅 |
| **Low** | X-Powered-By раскрывает PHP | headers.txt | fastcgi_hide_header | 📅 |
| **Info** | X-XSS-Protection отсутствует | nikto.txt | false positive, не делать | ✅ принят |

## Next audit
- Date: 2026-08-06
- Цель: hardening index ≥ 70, Grade A в testssl, все headers настроены
```
