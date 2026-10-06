#!/usr/bin/env python3
"""
Скрипт генерации стартовых данных для Модуля 08:
- auth.log (реалистичный журнал атак SSH brute-force и privilege escalation)
- app-production.log (большой неротированный лог-файл ~50 МБ)
- metrics_dump.txt (вывод vmstat и iostat при аварийной нагрузке)
"""

import os
import random
import datetime

STARTER_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_auth_log():
    auth_file = os.path.join(STARTER_DIR, "auth.log")
    print(f"[*] Генерация {auth_file}...")
    
    start_time = datetime.datetime(2026, 10, 4, 18, 0, 0)
    lines = []
    
    # 1. Фоновый легитимный трафик
    base_users = ["alice", "bob", "sysadmin", "deploy"]
    for i in range(25):
        t = start_time + datetime.timedelta(minutes=i*12, seconds=random.randint(0, 59))
        ts_str = t.strftime("%b %d %H:%M:%S")
        user = random.choice(base_users)
        ip = "10.0.10.15"
        port = random.randint(40000, 60000)
        pid = random.randint(2000, 3000)
        lines.append(f"{ts_str} bastion sshd[{pid}]: Accepted publickey for {user} from {ip} port {port} ssh2: RSA SHA256:m0k8Vn1+GZ7")
        lines.append(f"{ts_str} bastion sshd[{pid}]: pam_unix(sshd:session): session opened for user {user} by (uid=0)")
        if random.random() > 0.5:
            lines.append(f"{ts_str} bastion sudo: {user} : TTY=pts/0 ; PWD=/home/{user} ; USER=root ; COMMAND=/usr/bin/systemctl status nginx")
            lines.append(f"{ts_str} bastion sudo: pam_unix(sudo:session): session opened for user root by {user}(uid=1000)")
            lines.append(f"{ts_str} bastion sudo: pam_unix(sudo:session): session closed for user root")

    # 2. Массовый Brute-Force с атакующих IP (198.51.100.42, 203.0.113.88, 192.0.2.15)
    attacker_ips = {
        "203.0.113.88": ["root", "admin", "test", "oracle", "postgres", "ubuntu", "user", "guest"],
        "192.0.2.15": ["ftpuser", "git", "jenkins", "ansible", "support", "nagios", "minecraft"],
        "198.51.100.42": ["root", "admin", "manager", "operator", "developer"]
    }
    
    attack_time = datetime.datetime(2026, 10, 4, 21, 15, 0)
    
    # Симуляция атаки от 203.0.113.88 и 192.0.2.15 (неудачные)
    for _ in range(350):
        ip = random.choice(["203.0.113.88", "192.0.2.15"])
        user = random.choice(attacker_ips[ip])
        attack_time += datetime.timedelta(seconds=random.randint(1, 4))
        ts_str = attack_time.strftime("%b %d %H:%M:%S")
        port = random.randint(30000, 65000)
        pid = random.randint(3100, 8900)
        
        if user in ["oracle", "minecraft", "ftpuser", "nagios"]:
            lines.append(f"{ts_str} bastion sshd[{pid}]: Invalid user {user} from {ip} port {port}")
            lines.append(f"{ts_str} bastion sshd[{pid}]: pam_unix(sshd:auth): check pass; user unknown")
            lines.append(f"{ts_str} bastion sshd[{pid}]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost={ip}")
            lines.append(f"{ts_str} bastion sshd[{pid}]: Failed password for invalid user {user} from {ip} port {port} ssh2")
        else:
            lines.append(f"{ts_str} bastion sshd[{pid}]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost={ip}  user={user}")
            lines.append(f"{ts_str} bastion sshd[{pid}]: Failed password for {user} from {ip} port {port} ssh2")
        lines.append(f"{ts_str} bastion sshd[{pid}]: Received disconnect from {ip} port {port}:11: Bye Bye [preauth]")

    # 3. Таргетированная атака с 198.51.100.42 и компрометация developer
    target_ip = "198.51.100.42"
    target_time = datetime.datetime(2026, 10, 4, 22, 45, 10)
    for attempt in range(5):
        target_time += datetime.timedelta(seconds=3)
        ts_str = target_time.strftime("%b %d %H:%M:%S")
        pid = 9100 + attempt
        lines.append(f"{ts_str} bastion sshd[{pid}]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost={target_ip}  user=developer")
        lines.append(f"{ts_str} bastion sshd[{pid}]: Failed password for developer from {target_ip} port {45100+attempt} ssh2")

    # Успешный взлом по паролю
    target_time += datetime.timedelta(seconds=12)
    ts_str = target_time.strftime("%b %d %H:%M:%S")
    pid = 9120
    lines.append(f"{ts_str} bastion sshd[{pid}]: Accepted password for developer from {target_ip} port 45115 ssh2")
    lines.append(f"{ts_str} bastion sshd[{pid}]: pam_unix(sshd:session): session opened for user developer by (uid=0)")
    lines.append(f"{ts_str} bastion systemd-logind[780]: New session 142 of user developer.")

    # Нелегитимные действия взломщика
    target_time += datetime.timedelta(seconds=45)
    ts_str = target_time.strftime("%b %d %H:%M:%S")
    lines.append(f"{ts_str} bastion sudo: developer : TTY=pts/2 ; PWD=/home/developer ; USER=root ; COMMAND=/usr/bin/cat /etc/shadow")
    lines.append(f"{ts_str} bastion sudo: pam_unix(sudo:session): session opened for user root by developer(uid=1001)")
    lines.append(f"{ts_str} bastion sudo: pam_unix(sudo:session): session closed for user root")

    target_time += datetime.timedelta(seconds=20)
    ts_str = target_time.strftime("%b %d %H:%M:%S")
    lines.append(f"{ts_str} bastion sudo: developer : TTY=pts/2 ; PWD=/home/developer ; USER=root ; COMMAND=/bin/bash")
    lines.append(f"{ts_str} bastion sudo: pam_unix(sudo:session): session opened for user root by developer(uid=1001)")

    # Создание бэкдора
    target_time += datetime.timedelta(seconds=15)
    ts_str = target_time.strftime("%b %d %H:%M:%S")
    lines.append(f"{ts_str} bastion useradd[9180]: new group: name=backdoor_admin, GID=1005")
    lines.append(f"{ts_str} bastion useradd[9180]: new user: name=backdoor_admin, UID=1005, GID=1005, home=/home/backdoor_admin, shell=/bin/bash, from=/dev/pts/2")
    lines.append(f"{ts_str} bastion usermod[9185]: add 'backdoor_admin' to group 'sudo'")

    # Сортировка по времени
    lines.sort(key=lambda x: datetime.datetime.strptime(x[:15], "%b %d %H:%M:%S"))

    with open(auth_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[+] Сгенерировано {len(lines)} строк в {auth_file}")

def generate_large_app_log(target_size_mb=50):
    log_file = os.path.join(STARTER_DIR, "app-production.log")
    print(f"[*] Генерация неротированного лог-файла {log_file} (~{target_size_mb} МБ)...")
    
    endpoints = ["/api/v1/auth/login", "/api/v1/payments/charge", "/api/v1/users/profile", "/api/v1/orders/create", "/healthz"]
    ep_weights = [30, 25, 20, 15, 10]
    statuses = [200, 200, 200, 201, 400, 401, 403, 500, 502]
    status_weights = [60, 15, 10, 5, 4, 3, 1, 1, 1]
    
    line_template = '{"timestamp":"2026-10-05T08:%02d:%02d.%03dZ","level":"%s","service":"fintech-gateway","client_ip":"198.51.100.%d","endpoint":"%s","status":%d,"duration_ms":%.2f,"trace_id":"trace-%08x%08x","message":"Transaction handled successfully with payload validation"}\n'
    
    levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
    
    # Генерация блоками для высокой скорости
    chunk_lines = []
    for _ in range(5000):
        m = random.randint(0, 59)
        s = random.randint(0, 59)
        ms = random.randint(0, 999)
        lvl = random.choice(levels)
        ip_last = random.randint(1, 254)
        ep = random.choices(endpoints, weights=ep_weights, k=1)[0]
        st = random.choices(statuses, weights=status_weights, k=1)[0]
        dur = random.uniform(1.5, 450.0)
        t1 = random.randint(0, 0xFFFFFFFF)
        t2 = random.randint(0, 0xFFFFFFFF)
        chunk_lines.append(line_template % (m, s, ms, lvl, ip_last, ep, st, dur, t1, t2))
    
    chunk_str = "".join(chunk_lines).encode("utf-8")
    chunk_len = len(chunk_str)
    target_bytes = target_size_mb * 1024 * 1024
    
    written = 0
    with open(log_file, "wb") as f:
        while written < target_bytes:
            to_write = min(chunk_len, target_bytes - written)
            f.write(chunk_str[:to_write])
            written += to_write
            
    actual_size = os.path.getsize(log_file) / (1024 * 1024)
    print(f"[+] Лог-файл создан: {actual_size:.2f} МБ")

def generate_metrics_dump():
    dump_file = os.path.join(STARTER_DIR, "metrics_dump.txt")
    print(f"[*] Генерация дампа метрик {dump_file}...")
    
    content = """# ==============================================================================
# Linux Performance Incident Capture: Production Node srv-fintech-db02
# Kernel: 6.8.0-40-generic x86_64 | 8 vCPU | 32 GB RAM | Root on NVMe, Data on SATA HDD
# Issue: Application requests timing out, response latency jumped from 20ms to 4500ms
# ==============================================================================

# --- СРЕЗ 1: vmstat 1 10 (Снято в момент деградации сервиса) ---
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 2  4 345020  98240  12140 184500 2450 1890  8920 14500 4520 8900 12 28  0 60  0
 1  5 348100  94120  12144 182100 3100 2150  9410 16200 4890 9200 14 31  0 55  0
 3  6 352400  91040  12148 179900 3800 2800 11200 18400 5120 9850 10 35  0 55  0
 2  4 358900  89450  12150 178200 4200 3100 10800 15900 4980 9100 15 29  0 56  0
 4  7 364200  88100  12156 176500 4900 3800 12500 19800 5400 10200 11 34  0 55  0
 2  5 371000  86900  12160 174900 5200 4100 13100 21000 5600 10500 13 32  0 55  0
 1  4 378400  85400  12164 173200 5600 4450 12800 18900 5300 9900 12 30  0 58  0
 3  6 385100  84100  12168 171800 5900 4900 14200 22400 5750 10900 14 36  0 50  0
 2  5 391400  83200  12170 170400 6100 5200 13900 21800 5580 10600 13 33  0 54  0
 2  4 398200  82100  12174 169100 6400 5600 14500 23100 5820 11100 15 35  0 50  0

# --- СРЕЗ 2: iostat -xz 1 5 (Расширенная статистика по накопителям) ---
Device            r/s     w/s     rkB/s     wkB/s   rrqm/s  wrqm/s  %rrqm  %wrqm  r_await w_await aqu-sz  %util
nvme0n1 (OS)     4.00   18.00     32.00    240.00     0.00    1.00   0.00   5.26     0.25    0.60   0.01   1.20
sdb (DB_DATA)  185.00  420.00  38500.00  84200.00    12.00   45.00   6.09   9.68    84.50  145.20  24.80  99.80
sdc (BACKUP)     1.00    0.00      4.00      0.00     0.00    0.00   0.00   0.00     1.20    0.00   0.00   0.10

# --- СРЕЗ 3: sar -q 1 3 (Очереди процессов и Load Average) ---
08:30:01 AM   runq-sz  plist-sz   ldavg-1   ldavg-5  ldavg-15   blocked
08:30:02 AM         3       842     14.20      8.45      4.12         6
08:30:03 AM         2       845     15.80      9.10      4.35         5
08:30:04 AM         4       846     16.50      9.80      4.60         7
Average:            3       844     15.50      9.12      4.36         6
"""
    with open(dump_file, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"[+] Дамп метрик сохранен в {dump_file}")

if __name__ == "__main__":
    generate_auth_log()
    generate_large_app_log(50)
    generate_metrics_dump()
    print("[✔] Генерация стартовых данных завершена успешно!")
