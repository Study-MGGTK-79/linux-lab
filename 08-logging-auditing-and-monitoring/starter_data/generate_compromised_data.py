#!/usr/bin/env python3
"""
Генератор реалистичных криминалистических артефактов (DFIR Artifacts) для Модуля 08:
- auth_compromised.log : Журнал SSH аутентификации с брутфорсом, проникновением и зачисткой
- audit_tampered.log    : Системный журнал Auditd с фиксацией системных вызовов атакующего
- wtmp_evidence.txt     : Текстовый дамп сессий wtmp с аномалией вырезанной сессии
"""

import os
import random
import datetime

STARTER_DIR = os.path.dirname(os.path.abspath(__file__))

def create_evidence():
    print("[*] Генерация криминалистических логов для Модуля 08...")

    start_date = datetime.datetime(2026, 10, 4, 19, 0, 0)
    
    # --------------------------------------------------------------------------
    # 1. auth_compromised.log
    # --------------------------------------------------------------------------
    auth_lines = []
    
    # Фоновые легитимные события
    legit_users = ["alice", "bob", "sysadmin"]
    for i in range(15):
        t = start_date + datetime.timedelta(minutes=i*14, seconds=random.randint(5, 50))
        ts = t.strftime("%b %d %H:%M:%S")
        u = random.choice(legit_users)
        pid = 1100 + i
        auth_lines.append(f"{ts} srv-fintech-gw01 sshd[{pid}]: Accepted publickey for {u} from 10.0.10.15 port {random.randint(40000, 50000)} ssh2: RSA SHA256:4kM9+v8z1N")
        auth_lines.append(f"{ts} srv-fintech-gw01 sshd[{pid}]: pam_unix(sshd:session): session opened for user {u} by (uid=0)")
        auth_lines.append(f"{ts} srv-fintech-gw01 sudo: {u} : TTY=pts/0 ; PWD=/home/{u} ; USER=root ; COMMAND=/usr/bin/systemctl status nginx")
        auth_lines.append(f"{ts} srv-fintech-gw01 sudo: pam_unix(sudo:session): session opened for user root by {u}(uid=1000)")
        auth_lines.append(f"{ts} srv-fintech-gw01 sudo: pam_unix(sudo:session): session closed for user root")

    # Массовый подбор паролей (Brute-Force) с внешнего IP 198.51.100.42
    attacker_ip = "198.51.100.42"
    attack_time = datetime.datetime(2026, 10, 4, 22, 10, 0)
    wordlist = ["root", "admin", "test", "postgres", "guest", "ubuntu", "operator", "svc_backup", "svc_backup"]
    
    for i in range(80):
        attack_time += datetime.timedelta(seconds=random.randint(1, 3))
        ts = attack_time.strftime("%b %d %H:%M:%S")
        u = random.choice(wordlist)
        port = random.randint(35000, 62000)
        pid = 3400 + i
        if u in ["oracle", "postgres"]:
            auth_lines.append(f"{ts} srv-fintech-gw01 sshd[{pid}]: Invalid user {u} from {attacker_ip} port {port}")
            auth_lines.append(f"{ts} srv-fintech-gw01 sshd[{pid}]: Failed password for invalid user {u} from {attacker_ip} port {port} ssh2")
        else:
            auth_lines.append(f"{ts} srv-fintech-gw01 sshd[{pid}]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost={attacker_ip} user={u}")
            auth_lines.append(f"{ts} srv-fintech-gw01 sshd[{pid}]: Failed password for {u} from {attacker_ip} port {port} ssh2")

    # Точка пробоя: успешный подбор пароля учетной записи svc_backup
    attack_time += datetime.timedelta(seconds=14)
    compromise_ts = attack_time.strftime("%b %d %H:%M:%S")
    pid_comp = 4120
    auth_lines.append(f"{compromise_ts} srv-fintech-gw01 sshd[{pid_comp}]: Accepted password for svc_backup from {attacker_ip} port 49152 ssh2")
    auth_lines.append(f"{compromise_ts} srv-fintech-gw01 sshd[{pid_comp}]: pam_unix(sshd:session): session opened for user svc_backup by (uid=0)")
    auth_lines.append(f"{compromise_ts} srv-fintech-gw01 systemd-logind[612]: New session 42 of user svc_backup.")

    # Действия злоумышленника (sudo, shadow, bash)
    attack_time += datetime.timedelta(seconds=28)
    ts_act = attack_time.strftime("%b %d %H:%M:%S")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 sudo: svc_backup : TTY=pts/2 ; PWD=/home/svc_backup ; USER=root ; COMMAND=/usr/bin/cat /etc/shadow")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 sudo: pam_unix(sudo:session): session opened for user root by svc_backup(uid=1002)")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 sudo: pam_unix(sudo:session): session closed for user root")

    attack_time += datetime.timedelta(seconds=19)
    ts_act = attack_time.strftime("%b %d %H:%M:%S")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 sudo: svc_backup : TTY=pts/2 ; PWD=/home/svc_backup ; USER=root ; COMMAND=/bin/bash")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 sudo: pam_unix(sudo:session): session opened for user root by svc_backup(uid=1002)")

    # Создание бэкдора
    attack_time += datetime.timedelta(seconds=35)
    ts_act = attack_time.strftime("%b %d %H:%M:%S")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 useradd[4890]: new group: name=backdoor_admin, GID=1008")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 useradd[4890]: new user: name=backdoor_admin, UID=1008, GID=1008, home=/home/backdoor_admin, shell=/bin/bash, from=/dev/pts/2")
    auth_lines.append(f"{ts_act} srv-fintech-gw01 usermod[4895]: add 'backdoor_admin' to group 'sudo'")

    # Сортировка по времени
    auth_lines.sort(key=lambda x: datetime.datetime.strptime(x[:15], "%b %d %H:%M:%S"))
    
    auth_path = os.path.join(STARTER_DIR, "auth_compromised.log")
    with open(auth_path, "w", encoding="utf-8") as f:
        f.write("\n".join(auth_lines) + "\n")
    print(f"[+] Файл создан: {auth_path} ({len(auth_lines)} строк)")

    # --------------------------------------------------------------------------
    # 2. wtmp_evidence.txt (Дамп utmpdump с признаками зачистки)
    # --------------------------------------------------------------------------
    # Записи сессий в текстовом формате utmpdump:
    # [type] [pid] [line] [id] [user] [host] [ip] [timestamp]
    wtmp_lines = [
        '[2] [00000] [~~  ] [runl] [runlevel    ] [6.8.0-40-generic   ] [0.0.0.0        ] [2026-10-04T18:30:00,000000+00:00]',
        '[7] [01102] [pts/0] [vt01] [sysadmin    ] [10.0.10.15         ] [10.0.10.15     ] [2026-10-04T19:00:12,120000+00:00]',
        '[8] [01102] [pts/0] [vt01] [sysadmin    ] [10.0.10.15         ] [10.0.10.15     ] [2026-10-04T19:25:40,450000+00:00]',
        '[7] [01450] [pts/1] [vt02] [alice       ] [10.0.10.15         ] [10.0.10.15     ] [2026-10-04T20:10:05,330000+00:00]',
        '[8] [01450] [pts/1] [vt02] [alice       ] [10.0.10.15         ] [10.0.10.15     ] [2026-10-04T21:05:18,910000+00:00]',
        # АНОМАЛИЯ ЗАЧИСТКИ WTMP:
        # Атакующий вырезал запись типа [7] (USER_PROCESS вход svc_backup с 198.51.100.42),
        # но оставил закрытие сессии [8] (DEAD_PROCESS на pts/2) или оставил несогласованный статус!
        # Либо сессия [8] DEAD_PROCESS для pts/2 висит без открывающей записи [7]!
        '[8] [04120] [pts/2] [vt03] [svc_backup  ] [                    ] [0.0.0.0        ] [2026-10-04T23:15:42,880000+00:00]',
        '[7] [05210] [pts/0] [vt01] [bob         ] [10.0.10.15         ] [10.0.10.15     ] [2026-10-05T06:45:00,100000+00:00]'
    ]
    wtmp_path = os.path.join(STARTER_DIR, "wtmp_evidence.txt")
    with open(wtmp_path, "w", encoding="utf-8") as f:
        f.write("\n".join(wtmp_lines) + "\n")
    print(f"[+] Файл создан: {wtmp_path} (Дамп utmpdump с аномалией закрытия сессии)")

    # --------------------------------------------------------------------------
    # 3. audit_tampered.log (Сырые системные вызовы auditd)
    # --------------------------------------------------------------------------
    epoch_base = 1791153920.100
    audit_events = []
    
    # Событие 1: чтение /etc/shadow
    audit_events.append(f"""type=SYSCALL msg=audit({epoch_base:.3f}:5101): arch=c000003e syscall=257 success=yes exit=3 a0=ffffff9c a1=7ffd3a12 a2=80000 a3=0 items=1 ppid=4120 pid=4510 auid=1002 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 tty=pts/2 ses=42 comm="cat" exe="/usr/bin/cat" key="mitre_credential_access"
type=PATH msg=audit({epoch_base:.3f}:5101): item=0 name="/etc/shadow" inode=131075 dev=08:01 mode=0100640 ouid=0 ogid=42
type=PROCTITLE msg=audit({epoch_base:.3f}:5101): proctitle=636174002F6574632F736861646F77""")

    # Событие 2: запуск интерактивного bash под root
    epoch_base += 19.5
    audit_events.append(f"""type=SYSCALL msg=audit({epoch_base:.3f}:5102): arch=c000003e syscall=59 success=yes exit=0 a0=55e100 a1=55e120 a2=55e138 a3=7ffd items=2 ppid=4120 pid=4580 auid=1002 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 tty=pts/2 ses=42 comm="bash" exe="/usr/bin/bash" key="mitre_execve"
type=EXECVE msg=audit({epoch_base:.3f}:5102): argc=1 a0="/bin/bash"
type=PROCTITLE msg=audit({epoch_base:.3f}:5102): proctitle=2F62696E2F62617368""")

    # Событие 3: создание пользователя backdoor_admin
    epoch_base += 35.2
    audit_events.append(f"""type=SYSCALL msg=audit({epoch_base:.3f}:5103): arch=c000003e syscall=257 success=yes exit=4 a0=ffffff9c a1=7ffd a2=241 a3=1b6 items=1 ppid=4580 pid=4890 auid=1002 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 tty=pts/2 ses=42 comm="useradd" exe="/usr/sbin/useradd" key="mitre_account_privesc"
type=PATH msg=audit({epoch_base:.3f}:5103): item=0 name="/etc/passwd" inode=131074 dev=08:01 mode=0100644 ouid=0 ogid=0
type=PROCTITLE msg=audit({epoch_base:.3f}:5103): proctitle=75736572616464002D6D002D73002F62696E2F62617368006261636B646F6F725F61646D696E""")

    # Событие 4: АНТИ-ФОРЕНЗИКА: попытка удаления /var/log/auth.log системным вызовом unlink (syscall=87)
    epoch_base += 62.1
    audit_events.append(f"""type=SYSCALL msg=audit({epoch_base:.3f}:5104): arch=c000003e syscall=87 success=yes exit=0 a0=7ffd5812 a1=0 a2=0 a3=0 items=2 ppid=4580 pid=4950 auid=1002 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 tty=pts/2 ses=42 comm="rm" exe="/usr/bin/rm" key="mitre_log_tampering"
type=PATH msg=audit({epoch_base:.3f}:5104): item=0 name="/var/log/auth.log" inode=145920 dev=08:01 mode=0100640 ouid=0 ogid=4
type=PROCTITLE msg=audit({epoch_base:.3f}:5104): proctitle=726D002D66002F7661722F6C6F672F617574682E6C6F67""")

    # Событие 5: попытка зачистки истории bash
    epoch_base += 12.3
    audit_events.append(f"""type=SYSCALL msg=audit({epoch_base:.3f}:5105): arch=c000003e syscall=87 success=yes exit=0 a0=7ffd6120 a1=0 a2=0 a3=0 items=2 ppid=4580 pid=4980 auid=1002 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 tty=pts/2 ses=42 comm="rm" exe="/usr/bin/rm" key="mitre_log_tampering"
type=PATH msg=audit({epoch_base:.3f}:5105): item=0 name="/home/svc_backup/.bash_history" inode=220114 dev=08:01 mode=0100600 ouid=1002 ogid=1002
type=PROCTITLE msg=audit({epoch_base:.3f}:5105): proctitle=726D002D66002F686F6D652F7376635F6261636B75702F2E626173685F686973746F7279""")

    audit_path = os.path.join(STARTER_DIR, "audit_tampered.log")
    with open(audit_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(audit_events) + "\n")
    print(f"[+] Файл создан: {audit_path} (События auditd с зафиксированным auid=1002 и вызовами unlink)")

if __name__ == "__main__":
    create_evidence()
