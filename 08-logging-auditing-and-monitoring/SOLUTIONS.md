# 🎯 Решения и эталонные материалы к Модулю 08
## Incident Response, Log Tampering & Threat Hunting with Auditd

---

## 1. Отчет о цифровом расследовании инцидента (DFIR Incident Report)

### 📋 Сводка инцидента (Executive Summary)
- **Имя пострадавшего хоста**: `srv-fintech-gw01`
- **Классификация инцидента**: Несанкционированный доступ, компрометация учетной записи, эскалация привилегий до `root`, создание скрытого бэкдора и попытка уничтожения доказательств (Log Tampering & Anti-Forensics).
- **Период атаки**: 04 октября 2026 года, `22:10:00 – 23:15:42 UTC`.
- **Вектор первоначального проникновения**: Подбор пароля (SSH Brute-Force) к сервисной сервисной учетной записи `svc_backup`.
- **Уровень критичности**: **CRITICAL (P1)**.
- **Статус инцидента**: Сдержан, скомпрометированные учетные записи заблокированы, бэкдор удален.

---

### ⏱️ Хронологическая шкала событий (Incident Timeline)

| Точное время (UTC) | Источник события | Субъект / Процесс | Выполненное действие и технические детали | MITRE ATT&CK ID |
| :--- | :--- | :--- | :--- | :--- |
| **22:10:00 – 22:13:45** | `auth_compromised.log` | IP: `198.51.100.42` | Массовый подбор паролей по словарю (80+ неудачных попыток входа) | `T1110.001` (Brute Force) |
| **22:14:02** | `auth_compromised.log` | `sshd[4120]` | Успешная аутентификация по паролю пользователя **`svc_backup`** с IP `198.51.100.42` на порт 49152 | `T1078.003` (Valid Accounts) |
| **22:14:30** | `auth_compromised.log` & `audit_tampered.log` | `cat` (PID: 4510, auid: 1002) | Выполнение команды через sudo: `cat /etc/shadow` (извлечение хэшей паролей) | `T1003.008` (Credential Access) |
| **22:14:49** | `auth_compromised.log` & `audit_tampered.log` | `sudo` -> `bash` (PID: 4580) | Эскалация до интерактивной сессии `root` через команду `/bin/bash` | `T1548.003` (Sudo Abuse) |
| **22:15:24** | `auth_compromised.log` & `audit_tampered.log` | `useradd` (PID: 4890, auid: 1002) | Создание учетной записи бэкдора **`backdoor_admin`** (UID 1008) с шеллом `/bin/bash` | `T1136.001` (Create Account) |
| **22:15:24** | `auth_compromised.log` | `usermod[4895]` | Включение учетной записи `backdoor_admin` в группу `sudo` | `T1098` (Account Manipulation) |
| **22:16:26** | `audit_tampered.log` | `rm` (PID: 4950, auid: 1002) | Системный вызов `unlink` (`syscall=87`) для файла `/var/log/auth.log` | `T1070.002` (Clear System Logs) |
| **22:16:38** | `audit_tampered.log` | `rm` (PID: 4980, auid: 1002) | Системный вызов `unlink` для файла `/home/svc_backup/.bash_history` | `T1070.003` (Clear History) |
| **23:15:42** | `wtmp_evidence.txt` | `init` / `sshd` | Завершение сессии терминала `pts/2` (DEAD_PROCESS) без парной записи о входе | `T1070` (Log Tampering) |

---

### 🔍 Анализ техник анти-форензики (Log Tampering Evidence)

#### 1. Выявление аномалии в `wtmp_evidence.txt`:
При анализе дампа `utmpdump starter_data/wtmp_evidence.txt` обнаружена критическая аномалия:
```text
[8] [04120] [pts/2] [vt03] [svc_backup  ] [                    ] [0.0.0.0        ] [2026-10-04T23:15:42,880000+00:00]
```
- Запись типа `[8]` обозначает завершение процесса сессии (`DEAD_PROCESS`) на терминале `pts/2`.
- **Факт манипуляции**: В файле **полностью отсутствует предшествующая запись типа `[7]` (`USER_PROCESS`)** с открытием сессии `svc_backup` на `pts/2` с адреса `198.51.100.42`.
- **Вывод**: Злоумышленник использовал бинарный редактор или специализированную утилиту зачистки `wtmp` для хирургического удаления записи о своем входе с внешнего IP-адреса, но допустил ошибку и не удалил запись о закрытии сессии при выходе из системы.

#### 2. Доказательства уничтожения логов по `audit_tampered.log`:
Несмотря на попытку удаления `/var/log/auth.log` командой `rm -f`, подсистема Auditd зафиксировала системный вызов ядра `unlink` (`syscall=87`):
```text
type=SYSCALL ... syscall=87 success=yes exit=0 ... ppid=4580 pid=4950 auid=1002 uid=0 euid=0 ... comm="rm" exe="/usr/bin/rm" key="mitre_log_tampering"
type=PATH ... name="/var/log/auth.log"
```
**Ключевое криминалистическое доказательство**: Значение поля **`auid=1002`** неопровержимо доказывает, что команду удаления логов под пользователем `root` (`uid=0`, `euid=0`) отдал пользователь с реальным идентификатором 1002 (`svc_backup`).

---

### 🚨 Индикаторы компрометации (IoC)
- **Внешний IP атакующего**: `198.51.100.42`
- **Скомпрометированная сервисная учетная запись**: `svc_backup` (UID: 1002)
- **Созданная учетная запись бэкдора**: `backdoor_admin` (UID: 1008, GID: 1008, группа `sudo`)
- **Удаленные/модифицированные файлы**:
  - `/var/log/auth.log`
  - `/home/svc_backup/.bash_history`
  - `/var/log/wtmp`

---

## 2. Команды для воспроизведения расследования и Threat Hunting

### 2.1. Анализ журнала аутентификации (`auth_compromised.log`)
1. **Топ атакующих IP-адресов по количеству неудачных попыток**:
   ```bash
   grep -E "Failed password|Invalid user" starter_data/auth_compromised.log | \
   awk '{for(i=1;i<=NF;i++) if($i=="from") print $(i+1)}' | \
   sort | uniq -c | sort -nr
   ```
   **Результат**: `80 198.51.100.42`.

2. **Поиск точки компрометации (успешный вход по паролю)**:
   ```bash
   grep "Accepted password" starter_data/auth_compromised.log
   ```
   **Результат**:
   `Oct 04 22:14:02 srv-fintech-gw01 sshd[4120]: Accepted password for svc_backup from 198.51.100.42 port 49152 ssh2`

3. **Отслеживание всех команд `sudo`, запущенных взломщиком**:
   ```bash
   grep "sudo:" starter_data/auth_compromised.log | grep "svc_backup"
   ```
   **Результат**:
   - `COMMAND=/usr/bin/cat /etc/shadow`
   - `COMMAND=/bin/bash`

4. **Обнаружение созданных бэкдоров**:
   ```bash
   grep -E "useradd|usermod" starter_data/auth_compromised.log
   ```
   **Результат**:
   - `new user: name=backdoor_admin, UID=1008, GID=1008, home=/home/backdoor_admin, shell=/bin/bash`
   - `add 'backdoor_admin' to group 'sudo'`

---

### 2.2. Threat Hunting запросы в подсистеме Auditd (`audit_tampered.log`)
1. **Поиск попыток несанкционированного доступа к учетным данным (`/etc/shadow`)**:
   ```bash
   ausearch -l -f starter_data/audit_tampered.log -k mitre_credential_access -i
   ```
   **Результат**: зафиксировано чтение `/etc/shadow` процессом `cat` с `auid=1002`, `euid=0`.

2. **Поиск интерактивного шелла, запущенного под root**:
   ```bash
   ausearch -l -f starter_data/audit_tampered.log -k mitre_execve -i
   ```
   **Результат**: зафиксирован запуск `/bin/bash` процессом `ppid=4120` с `auid=1002`.

3. **Поиск попыток зачистки логов и системных вызовов `unlink`**:
   ```bash
   ausearch -l -f starter_data/audit_tampered.log -k mitre_log_tampering -i
   ```
   **Результат**: зафиксировано удаление `/var/log/auth.log` и `/home/svc_backup/.bash_history`.

4. **Агрегированный отчет по запущенным бинарникам через `aureport`**:
   ```bash
   aureport -x --summary -if starter_data/audit_tampered.log
   ```

---

## 3. Эталонный конфигурационный файл правил Auditd
### `/etc/audit/rules.d/hardening-mitre.rules`

```bash
# ==============================================================================
# Production Hardening Ruleset for Auditd (MITRE ATT&CK Mapped)
# ==============================================================================

# Сброс правил и установка буфера памяти ядра
-D
-b 8192
-f 1
-r 0

# T1059.004: Мониторинг запуска команд реальными интерактивными пользователями
-a always,exit -F arch=b64 -S execve,execveat -F auid>=1000 -F auid!=4294967295 -k mitre_execve

# T1003.008: Контроль доступа к базе хэшей паролей
-w /etc/shadow -p rwa -k mitre_credential_access
-w /etc/gshadow -p rwa -k mitre_credential_access
-w /etc/security/opasswd -p rwa -k mitre_credential_access

# T1136 & T1548.003: Контроль модификации учетных записей и прав sudo
-w /etc/passwd -p wa -k mitre_account_privesc
-w /etc/group -p wa -k mitre_account_privesc
-w /etc/sudoers -p wa -k mitre_account_privesc
-w /etc/sudoers.d/ -p wa -k mitre_account_privesc

# T1548.001: Перехват системных вызовов изменения привилегий (setuid)
-a always,exit -F arch=b64 -S setuid,setgid,setreuid,setregid,setresuid,setresgid -F auid>=1000 -F auid!=4294967295 -k mitre_setuid_escalation

# T1070: Перехват удаления файлов и манипуляций с логами в /var/log
-a always,exit -F arch=b64 -S unlink,unlinkat,rename,renameat,truncate,ftruncate -F dir=/var/log -k mitre_log_tampering

# T1053.003: Мониторинг таймеров планировщика cron
-w /etc/crontab -p wa -k mitre_persistence_cron
-w /etc/cron.d/ -p wa -k mitre_persistence_cron
-w /etc/cron.daily/ -p wa -k mitre_persistence_cron
-w /etc/cron.hourly/ -p wa -k mitre_persistence_cron
-w /etc/cron.weekly/ -p wa -k mitre_persistence_cron
-w /etc/cron.monthly/ -p wa -k mitre_persistence_cron
-w /var/spool/cron/ -p wa -k mitre_persistence_cron

# T1055: Контроль инъекций памяти и отладки чужих процессов (ptrace)
-a always,exit -F arch=b64 -S ptrace -k mitre_process_injection

# Защита правил от модификации и выгрузки в рантайме (Immutable Mode)
-e 2
```

---

## 4. Эталонная конфигурация Rsyslog over TLS

### 4.1. Конфигурация клиента (`/etc/rsyslog.d/50-remote-tls.conf`)

```text
# 1. Параметры TLS-драйвера и сертификатов
global(
    DefaultNetstreamDriver="gtls"
    DefaultNetstreamDriverCAFile="/etc/ssl/certs/ca-central-logging.crt"
    DefaultNetstreamDriverCertFile="/etc/ssl/certs/fintech-client.crt"
    DefaultNetstreamDriverKeyFile="/etc/ssl/private/fintech-client.key"
)

# 2. Отказоустойчивая пересылка с локальной дисковой очередью (Disk-Assisted Queue)
action(
    type="omfwd"
    target="logs.central-siem.local"
    port="6514"
    protocol="tcp"
    StreamDriver="gtls"
    StreamDriverMode="1"                     # Только шифрованное соединение TLS
    StreamDriverAuthMode="x509/name"         # Проверка имени узла в сертификате
    StreamDriverPermittedPeers="logs.central-siem.local"

    # Параметры очереди на диске на случай аварии сети:
    queue.filename="remote_log_spool"
    queue.spoolDirectory="/var/spool/rsyslog"
    queue.type="LinkedList"
    queue.maxdiskspace="2g"
    queue.saveonshutdown="on"
    action.resumeRetryCount="-1"
)
```

### 4.2. Конфигурация сервера-коллектора (`/etc/rsyslog.conf`)

```text
# Загрузка модуля приема TLS
module(
    load="imtcp"
    StreamDriver.Name="gtls"
    StreamDriver.Mode="1"
    DefaultNetstreamDriverCAFile="/etc/ssl/certs/ca-central-logging.crt"
    DefaultNetstreamDriverCertFile="/etc/ssl/certs/server-collector.crt"
    DefaultNetstreamDriverKeyFile="/etc/ssl/private/server-collector.key"
)

# Прослушивание порта 6514
input(type="imtcp" port="6514")

# Шаблон динамического сохранения логов по каталогам хостов:
template(name="RemoteHostLogs" type="string" string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")

# Запись всех входящих сетевых сообщений:
if ($fromhost-ip != "127.0.0.1") then {
    action(type="omfile" dirmakeDir="on" template="RemoteHostLogs")
    stop
}
```

### 4.3. Защита логов на коллекторе:
```bash
# Установка атрибута Append-Only на сервере сбора (запрет удаления и изменения):
chattr -R +a /var/log/remote/
```
*Даже если скомпрометированный сервер отправляет команду самоуничтожения, на центральном коллекторе логи защищены ядром сервера и гарантируют непреложные доказательства для суда.*
