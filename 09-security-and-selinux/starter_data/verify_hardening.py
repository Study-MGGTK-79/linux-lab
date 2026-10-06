#!/usr/bin/env python3
"""
Скрипт аудита и верификации настроек безопасности по CIS Benchmark
Проверяет конфигурации sudoers, sshd_config и sysctl.conf на соответствие стандартам.
"""

import os
import sys
import re

STARTER_DIR = os.path.dirname(os.path.abspath(__file__))
VULN_DIR = os.path.join(STARTER_DIR, "vulnerable_system_config")

# GTFOBins опасные бинарники, дающие шелл при NOPASSWD в sudoers
GTFOBINS_DANGEROUS = {
    "find": "Позволяет выполнить 'find . -exec /bin/sh \\;'",
    "vim": "Позволяет выполнить ':!/bin/sh'",
    "vi": "Позволяет выполнить ':!/bin/sh'",
    "less": "Позволяет выполнить '!/bin/sh' прямо из пейджера",
    "more": "Позволяет запустить оболочку при отображении файла",
    "awk": "Позволяет выполнить 'awk \"BEGIN {system(\\\"/bin/sh\\\")}\"'",
    "gawk": "Позволяет выполнить шелл через system()",
    "python": "Позволяет запустить pty.spawn('/bin/bash')",
    "python3": "Позволяет запустить pty.spawn('/bin/bash')",
    "bash": "Прямой запуск командной оболочки root",
    "sh": "Прямой запуск командной оболочки root",
    "perl": "Позволяет выполнить 'perl -e \"exec \\\"/bin/sh\\\";\"'",
    "ruby": "Позволяет выполнить exec '/bin/sh'",
    "env": "Позволяет запустить 'env /bin/sh'",
    "tar": "Позволяет выполнить checkpoint-action: '--checkpoint-action=exec=/bin/sh'"
}

def audit_sudoers(file_path):
    print(f"\n[*] Аудит файла sudoers: {file_path}")
    issues = []
    if not os.path.exists(file_path):
        print(f"[-] Файл {file_path} не существует.")
        return False
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Поиск NOPASSWD с опасными утилитами
            if "NOPASSWD" in line:
                for bin_name, desc in GTFOBINS_DANGEROUS.items():
                    pattern = rf"(^|/){bin_name}(\s+|$|\*)"
                    if re.search(pattern, line):
                        issues.append((line_no, line, f"КРИТИЧЕСКИЙ РИСК GTFOBins: утилита '{bin_name}'. {desc}"))
                
                if "*" in line:
                    issues.append((line_no, line, "ОШИБКА: Использование символа подстановки '*' в строке NOPASSWD"))

    if issues:
        print(f"[!] Обнаружено нарушений безопасности: {len(issues)}")
        for lno, lcontent, msg in issues:
            print(f"  Строка {lno}: {lcontent}")
            print(f"    --> {msg}")
        return False
    else:
        print("[✔] Файл sudoers соответствует принципу наименьших привилегий (PoLP)!")
        return True

def audit_sshd(file_path):
    print(f"\n[*] Аудит конфигурации SSHD (CIS Benchmark): {file_path}")
    if not os.path.exists(file_path):
        print(f"[-] Файл {file_path} не существует.")
        return False
        
    rules = {
        "PermitRootLogin": ("no", "Запрет прямого входа root по SSH (CIS 5.2.10)"),
        "PasswordAuthentication": ("no", "Вход исключительно по SSH-ключам (CIS 5.2.11)"),
        "PermitEmptyPasswords": ("no", "Запрет пустых паролей (CIS 5.2.9)"),
        "MaxAuthTries": ("3", "Максимум 3-4 попытки подбора пароля (CIS 5.2.7)"),
        "X11Forwarding": ("no", "Отключение проброса графического интерфейса (CIS 5.2.6)")
    }
    
    config = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                config[parts[0].lower()] = parts[1].strip()

    violations = []
    for param, (expected, desc) in rules.items():
        val = config.get(param.lower())
        if val is None:
            violations.append(f"Параметр {param} НЕ задан (ожидается: {expected}). Требование: {desc}")
        elif val.lower() != expected.lower():
            if param == "MaxAuthTries" and int(val) <= 4:
                continue
            violations.append(f"Небезопасное значение {param} = {val} (ожидается: {expected}). Требование: {desc}")

    if violations:
        print(f"[!] Найдено несоответствий CIS: {len(violations)}")
        for v in violations:
            print(f"  [-] {v}")
        return False
    else:
        print("[✔] Конфигурация SSHD полностью соответствует CIS Benchmark!")
        return True

def audit_sysctl(file_path):
    print(f"\n[*] Аудит параметров ядра sysctl (CIS Benchmark): {file_path}")
    if not os.path.exists(file_path):
        print(f"[-] Файл {file_path} не существует.")
        return False

    required = {
        "net.ipv4.ip_forward": ("0", "Отключение транзитной маршрутизации"),
        "net.ipv4.conf.all.accept_source_route": ("0", "Запрет Source Routing"),
        "net.ipv4.conf.all.accept_redirects": ("0", "Игнорирование ICMP Redirects"),
        "net.ipv4.tcp_syncookies": ("1", "Защита от SYN Flood"),
        "fs.suid_dumpable": ("0", "Запрет core dump для SUID-процессов")
    }

    params = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                params[k.strip()] = v.strip()

    fails = []
    for k, (req, desc) in required.items():
        val = params.get(k)
        if val is None:
            fails.append(f"Параметр {k} отсутствует (ожидается: {req}). {desc}")
        elif val != req:
            fails.append(f"Небезопасное значение {k} = {val} (ожидается: {req}). {desc}")

    if fails:
        print(f"[!] Найдено уязвимых параметров ядра: {len(fails)}")
        for fl in fails:
            print(f"  [-] {fl}")
        return False
    else:
        print("[✔] Параметры ядра sysctl защищены по стандарту CIS!")
        return True

if __name__ == "__main__":
    target_sudoers = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VULN_DIR, "sudoers_insecure")
    target_sshd = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VULN_DIR, "sshd_config_insecure")
    target_sysctl = sys.argv[3] if len(sys.argv) > 3 else os.path.join(VULN_DIR, "sysctl_insecure.conf")

    print("==================================================================")
    print("  CIS Benchmark & Least Privilege Hardening Security Verifier     ")
    print("==================================================================")
    
    s_res = audit_sudoers(target_sudoers)
    sh_res = audit_sshd(target_sshd)
    sy_res = audit_sysctl(target_sysctl)

    print("\n==================================================================")
    if s_res and sh_res and sy_res:
        print("[🎉] ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ: Система полностью защищена!")
        sys.exit(0)
    else:
        print("[⚠️] ОБНАРУЖЕНЫ УЯЗВИМОСТИ: Сверьтесь с SOLUTIONS.md и устраните замечания.")
        sys.exit(1)
