#!/usr/bin/env python3
"""
Генератор стартовых данных для Лабораторной работы 01:
- server_access.log: 2500+ реалистичных строк веб-логов с кодами ответов и подозрительной активностью
- employees.csv: файл с данными сотрудников для awk/cut/sort
- messy_filesystem/: дерево файлов с пробелами, спецсимволами и временными метками для find
"""

import os
import random
import datetime

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_web_logs():
    log_file = os.path.join(OUTPUT_DIR, "server_access.log")
    ips = [
        "192.168.1.45", "10.0.4.12", "172.16.50.8", "198.51.100.23",
        "203.0.113.195", "192.168.1.101", "185.220.101.5", "45.154.255.88",
        "10.0.4.55", "192.168.1.15"
    ]
    scanner_ips = ["185.220.101.5", "45.154.255.88"]
    
    normal_paths = [
        "/", "/index.html", "/api/v1/users", "/api/v1/products",
        "/static/css/main.css", "/static/js/bundle.js", "/images/logo.png",
        "/checkout", "/cart", "/login", "/about", "/contact"
    ]
    attack_paths = [
        "/wp-login.php", "/.env", "/admin/phpinfo.php", "/.git/config",
        "/cgi-bin/test-cgi", "/api/v1/debug?token=test", "/shell.php",
        "/actuator/health", "/server-status"
    ]
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        "curl/7.88.1", "Python-urllib/3.10", "sqlmap/1.6.4#stable", "Nikto/2.1.6"
    ]
    
    start_time = datetime.datetime(2026, 10, 5, 0, 0, 0)
    lines = []
    
    for i in range(3000):
        current_time = start_time + datetime.timedelta(seconds=i * random.randint(1, 15))
        time_str = current_time.strftime("%d/%b/%Y:%H:%M:%S +0000")
        
        is_attack = random.random() < 0.15
        if is_attack:
            ip = random.choice(scanner_ips)
            path = random.choice(attack_paths)
            method = random.choice(["GET", "POST"])
            status = random.choice([404, 403, 500])
            size = random.randint(150, 450)
            agent = random.choice(user_agents[3:])
        else:
            ip = random.choice(ips[:6])
            path = random.choice(normal_paths)
            method = random.choice(["GET", "GET", "GET", "POST"])
            status = random.choices([200, 301, 304, 500, 502], weights=[80, 8, 5, 4, 3])[0]
            size = random.randint(300, 15000)
            agent = random.choice(user_agents[:3])
            
        line = f'{ip} - - [{time_str}] "{method} {path} HTTP/1.1" {status} {size} "-" "{agent}"'
        lines.append(line)
        
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Generated: {log_file} ({len(lines)} lines)")

def generate_employees_csv():
    csv_file = os.path.join(OUTPUT_DIR, "employees.csv")
    departments = ["Engineering", "DevOps", "Security", "Marketing", "HR", "Finance"]
    data = [
        "id,name,department,salary,hire_date,email",
        "101,Ivan Ivanov,Engineering,280000,2022-03-15,i.ivanov@corp.local",
        "102,Elena Petrova,DevOps,320000,2021-06-01,e.petrova@corp.local",
        "103,Alexey Sidorov,Security,350000,2020-01-10,a.sidorov@corp.local",
        "104,Maria Smirnova,HR,180000,2023-04-12,m.smirnova@corp.local",
        "105,Dmitry Kozlov,Engineering,250000,2023-08-20,d.kozlov@corp.local",
        "106,Anna Morozova,Finance,220000,2022-11-05,a.morozova@corp.local",
        "107,Sergey Volkov,DevOps,310000,2022-09-17,s.volkov@corp.local",
        "108,Olga Vasilyeva,Engineering,290000,2021-02-14,o.vasilyeva@corp.local",
        "109,Maxim Fedorov,Security,330000,2023-01-25,m.fedorov@corp.local",
        "110,Ekaterina Popova,Marketing,195000,2023-10-01,e.popova@corp.local",
        "111,Pavel Sokolov,Engineering,275000,2024-02-10,p.sokolov@corp.local",
        "112,Tatiana Mikhailova,HR,175000,2022-05-19,t.mikhailova@corp.local",
        "113,Igor Novikov,Finance,240000,2021-08-30,i.novikov@corp.local",
        "114,Ksenia Lebedeva,DevOps,305000,2023-11-15,k.lebedeva@corp.local",
        "115,Roman Semenov,Engineering,260000,2024-05-02,r.semenov@corp.local"
    ]
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("\n".join(data) + "\n")
    print(f"Generated: {csv_file}")

def generate_messy_fs():
    base_dir = os.path.join(OUTPUT_DIR, "messy_filesystem")
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, "backup 2026"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "old_logs", "archived"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "empty_dir"), exist_ok=True)
    
    files = [
        ("backup 2026/database dump 01.sql", "CREATE TABLE users;"),
        ("backup 2026/db_dump_02.sql", "INSERT INTO users VALUES (1);"),
        ("backup 2026/my confidential notes.txt", "Top secret project plans"),
        ("old_logs/archived/app_error_2025.log", "Fatal crash memory overflow"),
        ("old_logs/debug.tmp", "temporary debug info"),
        ("script with spaces.sh", "#!/bin/bash\necho 'Running test'"),
        (".hidden_config", "SECRET_KEY=antigravity_linux_key_2026")
    ]
    for path, content in files:
        full_path = os.path.join(base_dir, path)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    # Большой файл (2 МБ) для поиска по размеру
    large_file = os.path.join(base_dir, "large_archive.bin")
    with open(large_file, "wb") as f:
        f.write(os.urandom(2 * 1024 * 1024))
        
    print(f"Generated messy filesystem in: {base_dir}")

if __name__ == "__main__":
    generate_web_logs()
    generate_employees_csv()
    generate_messy_fs()
