#!/usr/bin/env python3
"""
Critical Transaction Service
Пишет важные финансовые транзакции в лог-файл.
Используется для отработки сценария спасения случайно удаленного открытого файла.
"""
import os
import sys
import time
import datetime

TARGET_DIR = "/tmp/linux_lab11/data"
LOG_FILE = os.path.join(TARGET_DIR, "critical_transactions.log")
PID_FILE = "/tmp/linux_lab11/critical_app.pid"

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    pid = os.getpid()
    
    with open(PID_FILE, "w") as f:
        f.write(str(pid))
        
    print(f"[PID {pid}] Сервис транзакций запущен. Ведется запись в {LOG_FILE}...")
    
    # Открываем файл на запись в режиме append
    f = open(LOG_FILE, "a", buffering=1, encoding="utf-8")
    
    # Записываем стартовые записи
    f.write(f"=== DATABASE INITIALIZED AT {datetime.datetime.now()} ===\n")
    f.write("TXN_001: USER_ALICE -> TRANSFER -> 15000 USD -> APPROVED\n")
    f.write("TXN_002: USER_BOB   -> TRANSFER -> 42000 EUR -> APPROVED\n")
    f.write("TXN_003: USER_CLARA -> TRANSFER -> 89000 RUB -> APPROVED\n")
    f.flush()
    
    txn_id = 4
    try:
        while True:
            time.sleep(3)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = f"TXN_{txn_id:03d}: TIMESTAMP={now} AMOUNT={txn_id * 1250} RUB -> PROCESSED\n"
            f.write(record)
            f.flush()
            txn_id += 1
    except KeyboardInterrupt:
        f.close()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

if __name__ == '__main__':
    main()
