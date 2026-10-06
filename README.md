# 🛡️ Linux Security, Exploitation & Administration Course: From Fundamentals to Advanced Defense

> **Практический курс системного администрирования, информационной безопасности и эксплуатации уязвимостей в Linux**  
> Фокус: **Red Team (Exploitation, Privilege Escalation, Pivoting) + Blue Team (Hardening, Threat Hunting, Incident Response, Forensics)**.  
> Соответствие международным программам: **RHCSA / RHCE**, **LPIC-1 / LPIC-2 Security**, **OffSec KLCP / OSCP (Linux fundamentals)**, **Linux Foundation LFCS**.

---

## 🎯 О курсе

Этот курс сочетает глубокое понимание системного администрирования Linux с практическими навыками анализа защищенности, эксплуатации архитектурных недочетов и построения эшелонированной обороны (Defense-in-Depth).

Каждая тема содержит:
1. **Подробную теоретическую базу (`THEORY.md`)** — архитектурные принципы ядра, системные вызовы, матрицы MITRE ATT&CK, анализ уязвимостей, механизмы защиты компилятора и ядра, схемы `mermaid` и продакшн-грабли.
2. **Практические лабораторные работы (`LABS.md`)** — сценарии эксплуатации, форензики, расследования инцидентов и системного харденинга.
3. **Готовые стартовые данные (`starter_data/`)** — реальные уязвимые программы на C/Python, поврежденные конфиги, сетевые дампы PCAP, журналы взломов и скрипты автоматизации.
4. **Эталонные решения и критерии проверки (`SOLUTIONS.md`)** — готовые эксплойт-пейлоады, команды расследования, защищенные конфигурации и критерии валидации.

---

## 🗺️ Структура курса

| Модуль | Тема | Ключевые концепции | Практика |
| :--- | :--- | :--- | :--- |
| **[01-architecture-and-shell](01-architecture-and-shell/)** | Linux Internals, Reconnaissance & Shell Security | Системные вызовы ядра, псевдо-ФС `/proc` (procfs recon: `/proc/$PID/environ`, сокеты в hex), утечки в shell-истории, Wildcard Injection, побег из Restricted Bash (`rbash`) | Расследование инцидента в веб-логах, извлечение секретов из `/proc`, обход rbash, эксплуатация wildcard |
| **[02-users-groups-and-permissions](02-users-groups-and-permissions/)** | Linux Privilege Escalation: SUID, Capabilities & Sudoers | Модель DAC, специальные биты (SUID/SGID/Sticky), Linux Capabilities (`cap_setuid`, `cap_dac_read_search`), SUID PATH Hijacking, векторы GTFOBins, sudoers `env_keep` и `LD_PRELOAD` | Эксплуатация SUID-бинарника через PATH Hijacking, получение root через опасные capabilities, обход sudoers |
| **[03-storage-and-lvm](03-storage-and-lvm/)** | Storage Security, Forensics & Disk Encryption (LUKS2) | MBR/GPT, ext4/XFS, LVM, полнодисковое шифрование LUKS2 / dm-crypt (detached header), утечка паролей в unencrypted swap, восстановление удаленных файлов, неизменяемость (`chattr +i/a`) | Развертывание LVM на loop-дисках, извлечение открытых паролей из дампа Swap, настройка неизменяемости файлов |
| **[04-processes-and-systemd](04-processes-and-systemd/)** | Process Memory Scavenging, Persistence & Systemd Sandboxing | Жизненный цикл процессов, дамп памяти процессов (`/proc/$PID/mem`, `gcore`), техники закрепления (Persistence via Systemd Timers/Services), песочницы Systemd (`ProtectSystem=strict`, `NoNewPrivileges`) | Дамп учетных данных из памяти активного сервиса, выявление скрытого Systemd бэкдора, харденинг службы |
| **[05-package-management](05-package-management/)** | Supply Chain Attacks, Dynamic Linking & Binary Protections | Атаки на цепочки поставок (троянизация maintainer scripts: `preinst`/`postinst`), перехват функций через `LD_PRELOAD`, защита бинарников (Stack Canary, NX, PIE, Full RELRO, `checksec`) | Компиляция утилиты на C, инъекция разделяемой библиотеки через `LD_PRELOAD`, разбор механизма `AT_SECURE` для SUID |
| **[06-networking-and-firewalls](06-networking-and-firewalls/)** | Network Attacks, Pivoting, Sniffing & Firewall Defense | Анализ трафика (`tcpdump`, BPF фильтры), SSH Pivoting & Tunneling (Local, Remote, Dynamic SOCKS5 с Proxychains), сокрытие портов (Port Knocking), Stateful фаерволы (iptables/nftables) | Перехват паролей из PCAP дампа, построение цепочки SSH Pivot туннелей, настройка защиты от SYN-flood и Port Scan |
| **[07-web-services-and-reverse-proxy](07-web-services-and-reverse-proxy/)** | Web Infrastructure Exploitation, Nginx Misconfigurations & SSL Hardening | Alias Traversal (LFI), SSRF через `proxy_pass`, спуфинг IP через `X-Forwarded-For`, POODLE/BEAST/Heartbleed, Perfect Forward Secrecy, TLS 1.3, Rate Limiting, Security Headers, WAF | Эксплуатация Alias Traversal и обход IP-списков, аудит и миграция на TLS 1.3 с PFS, DoS Hardening |
| **[08-logging-auditing-and-monitoring](08-logging-auditing-and-monitoring/)** | Incident Response, Log Tampering & Threat Hunting with Auditd | Методология NIST/MITRE ATT&CK, анти-форензика (utmp/wtmp, bash history tampering), Linux Auditd (`execve`, `ptrace`, `setuid`), Syslog over TLS | DFIR расследование взлома и зачистки логов, разработка боевых правил Auditd, Threat Hunting, неизменяемый Syslog |
| **[09-security-and-selinux](09-security-and-selinux/)** | Mandatory Access Control: SELinux & AppArmor Bypass and Hardening | Модель LSM, обход через опасные SELinux Booleans (`httpd_can_network_connect`, `httpd_execmem`), слепой `audit2allow`, AppArmor режимы (enforce vs complain), профилирование, Fail2ban | Разбор блокировок SELinux AVC, аудит опасных переключателей, создание строгого профиля AppArmor в режиме enforce |
| **[10-bash-automation](10-bash-automation/)** | Defensive Bash, Incident Automation & Detection Engineering | Уязвимости Bash (Command Injection, `eval`, TOCTOU race conditions в `/tmp`), сборщик энергозависимых доказательств (RFC 3227 Order of Volatility), Host Integrity Monitoring | Эксплуатация и устранение Command Injection в скрипте, разработка сборщика форензик-улик с SHA-256 хэшированием |
| **[11-troubleshooting-and-diagnostics](11-troubleshooting-and-diagnostics/)** | Kernel Security, Container Isolation & Rootkit Detection | Архитектура LKM Rootkits, перехват `getdents64` и сокрытие процессов, векторы побега из контейнеров (`--privileged`, Capabilities, `/var/run/docker.sock`), харденинг ядра через `sysctl` | Аудит привилегий контейнера (`capsh`), запуск детектора скрытых процессов ядра, применение строгих sysctl-параметров |

---

## 🛠️ Подготовка окружения для выполнения практических работ

Для безопасного проведения экспериментов и отработки сценариев рекомендуется использовать изолированный Docker-контейнер или виртуальную машину.

### Запуск в Docker:
```bash
# Запуск лабораторного контейнера с правами администратора
docker compose up -d

# Подключение к терминалу
docker compose exec linux-lab bash
```

### Запуск на виртуальной машине (Ubuntu 24.04 LTS или Rocky Linux 9):
```bash
./check_environment.sh
```

---

## 📌 Методика прохождения курса

1. **Теория (`THEORY.md`)**: Изучите архитектурные основы, векторы атак и механизмы защиты.
2. **Практика (`LABS.md`)**: Выполните задания в роли атакующего (Red Team) для понимания вектора угрозы, а затем в роли защитника (Blue Team) для устранения уязвимости и настройки мониторинга.
3. **Стартовые данные (`starter_data/`)**: Используйте подготовленные скрипты, программы и дампы трафика.
4. **Самопроверка (`SOLUTIONS.md`)**: Сверьте результаты с эталонным решением и отчетом расследования.
