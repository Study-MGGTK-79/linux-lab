#!/usr/bin/env python3
"""
Hanging Daemon (Учебная симуляция зависшего микросервиса)
Сервис успешно инициализируется, открывает локальные ресурсы, а затем
блокируется на синхронном системном вызове connect() к недоступному узлу без таймаута.
Потребляет 0% CPU, не отвечает на внешние запросы.
"""
import os
import sys
import time
import socket

TARGET_DIR = "/tmp/linux_lab11"
PID_FILE = os.path.join(TARGET_DIR, "hanging_daemon.pid")
CONFIG_FILE = os.path.join(TARGET_DIR, "payment_gateway.conf")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    pid = os.getpid()
    
    with open(PID_FILE, "w") as f:
        f.write(str(pid))
        
    print(f"[PID {pid}] Запуск микросервиса платежного шлюза (Billing Gateway)...")
    
    # 1. Читаем локальный конфиг (в strace будет виден openat / read)
    with open(CONFIG_FILE, "w") as f:
        f.write("GATEWAY_URL=http://192.0.2.1:443\nTIMEOUT=INFINITE\nRETRIES=0\n")
        
    print(f"[PID {pid}] Конфигурация успешно загружена.")
    print(f"[PID {pid}] Инициализация исходящего RPC-соединения с процессингом...")
    sys.stdout.flush()
    
    # 2. Создаем блокирующий сокет БЕЗ таймаута к немаршрутизируемому адресу (RFC 5737 TEST-NET-1)
    # Поведение: постоянно висит на системном вызове connect(), ожидая ответа TCP SYN-ACK
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 192.0.2.1 зарезервирован для документации и гарантированно не отвечает
            s.connect(('192.0.2.1', 443))
        except (socket.error, OSError):
            time.sleep(0.5)
        finally:
            try:
                s.close()
            except Exception:
                pass

if __name__ == '__main__':
    main()
