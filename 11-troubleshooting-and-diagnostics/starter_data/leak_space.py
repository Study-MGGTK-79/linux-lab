#!/usr/bin/env python3
"""
Leak Space Daemon (Учебная симуляция инцидента "Черная дыра на диске")
Создает крупный файл на диске, удаляет его имя из файловой системы через unlink,
но продолжает удерживать дескриптор открытым и циклически дописывать данные.
"""
import os
import sys
import time

TARGET_DIR = "/tmp/linux_lab11"
LEAK_FILE = os.path.join(TARGET_DIR, "phantom_database_wal.log")
PID_FILE = os.path.join(TARGET_DIR, "leak_space.pid")
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB за порцию
INITIAL_SIZE_CHUNKS = 15       # 150 MB стартовый размер

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))
        
    print(f"[PID {pid}] Запуск сервиса-виновника утечки дискового пространства...")
    print(f"[PID {pid}] Создание служебного файла: {LEAK_FILE}...")
    
    # 1. Открываем файл на низкоуровневый дескриптор
    fd = os.open(LEAK_FILE, os.O_CREAT | os.O_RDWR | os.O_TRUNC)
    
    # Записываем стартовые ~150 МБ данных
    dummy_payload = b"X" * CHUNK_SIZE
    for i in range(INITIAL_SIZE_CHUNKS):
        os.write(fd, dummy_payload)
        
    print(f"[PID {pid}] Файл первично заполнен ({INITIAL_SIZE_CHUNKS * 10} МБ).")
    print(f"[PID {pid}] Симуляция ошибки администратора: вызов unlink() (удаление имени файла из ФС)...")
    
    # 2. Удаляем файл из каталога!
    # Имя файла исчезнет из директории, i_nlink станет 0!
    os.unlink(LEAK_FILE)
    
    print(f"[PID {pid}] Файл удален из каталога! Но дескриптор (FD={fd}) удерживается процессом.")
    print(f"[PID {pid}] Сервис продолжает фоновую запись в открытый дескриптор...")
    
    # 3. Бесконечный цикл с периодической записью
    try:
        while True:
            # Каждые 5 секунд дописываем 5 МБ
            time.sleep(5)
            os.write(fd, b"Z" * (5 * 1024 * 1024))
    except KeyboardInterrupt:
        print(f"\n[PID {pid}] Остановка сервиса, закрытие дескриптора...")
        os.close(fd)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

if __name__ == '__main__':
    main()
