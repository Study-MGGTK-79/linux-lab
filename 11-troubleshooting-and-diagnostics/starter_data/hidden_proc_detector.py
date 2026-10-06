#!/usr/bin/env python3
"""
Детектор скрытых процессов Linux (Rootkit / Unlinked Task Detection).
Сравнивает список каталогов в /proc со списком процессов, отвечающих на сигналы kill(0).
Если ядро сообщает, что процесс существует, но каталога в /proc нет — это признак LKM руткита!
"""

import os
import sys

def scan_for_hidden_processes():
    print("=== Запуск сканирования скрытых процессов ядра ===")
    
    # Получаем список PID из /proc
    proc_pids = set()
    try:
        for entry in os.listdir("/proc"):
            if entry.isdigit():
                proc_pids.add(int(entry))
    except Exception as e:
        print(f"[-] Ошибка чтения /proc: {e}")
        return

    print(f"[*] В /proc обнаружено активных процессов: {len(proc_pids)}")
    
    # Проверяем диапазон PID на существование через отправку сигнала 0
    max_pid = 32768
    try:
        with open("/proc/sys/kernel/pid_max", "r") as f:
            max_pid = int(f.read().strip())
    except:
        pass

    hidden_pids = []
    
    # Сканируем диапазон
    for pid in range(1, min(max_pid, 10000)):
        if pid not in proc_pids:
            try:
                # Сигнал 0 не убивает процесс, но проверяет его существование в планировщике ядра
                os.kill(pid, 0)
                # Если ошибки нет — процесс существует в планировщике, но отсутствует в /proc!
                hidden_pids.append(pid)
            except PermissionError:
                # Ошибка доступа означает, что процесс существует (принадлежит другому пользователю), но скрыт из /proc!
                hidden_pids.append(pid)
            except ProcessLookupError:
                # Процесса действительно нет — нормальное поведение
                pass

    if hidden_pids:
        print(f"\n[⚠️ ВНИМАНИЕ ⚠️] ОБНАРУЖЕНЫ СКРЫТЫЕ ПРОЦЕССЫ: {hidden_pids}")
        print("Вероятен активный LKM Rootkit, скрывающий процессы из /proc!")
    else:
        print("\n[✓] Аномалий не обнаружено: Все процессы согласованы с /proc.")

if __name__ == "__main__":
    scan_for_hidden_processes()
