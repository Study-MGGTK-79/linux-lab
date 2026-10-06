#!/usr/bin/env python3
"""
Enterprise Mock Application Daemon (mock_daemon.py)
Имитирует микросервис с поддержкой сигналов POSIX, логированием в journald,
обработкой SIGHUP (перезагрузка конфигурации), graceful shutdown по SIGTERM
и управляемыми сбоями для отработки траблшутинга в Systemd.
"""

import os
import sys
import time
import signal
import argparse
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Глобальный флаг работы
RUNNING = True
CONFIG_VERSION = 1
REQUEST_COUNT = 0


def log(level: str, message: str):
    """Вывод структурированного лога в stdout/stderr с отметкой времени"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f"[{timestamp}] [{level.upper()}] [PID:{os.getpid()}] {message}"
    if level.upper() in ["ERROR", "CRITICAL"]:
        print(output, file=sys.stderr, flush=True)
    else:
        print(output, file=sys.stdout, flush=True)


def handle_sigterm(signum, frame):
    """Graceful shutdown при получении SIGTERM"""
    global RUNNING
    log("INFO", "Получен сигнал SIGTERM (15). Начинаем процедуру плавного завершения (Graceful Shutdown)...")
    log("INFO", "Завершение активных транзакций, сброс буферов на диск...")
    time.sleep(1)
    log("INFO", "Все ресурсы освобождены. Демон остановлен корректно.")
    RUNNING = False
    sys.exit(0)


def handle_sighup(signum, frame):
    """Перечитывание конфигурации по сигналу SIGHUP без перезапуска процесса"""
    global CONFIG_VERSION
    CONFIG_VERSION += 1
    log("WARNING", f"Получен сигнал SIGHUP (1). Перечитывание конфигурационных файлов... Успешно! (Конфиг ревизии {CONFIG_VERSION})")


def handle_sigusr1(signum, frame):
    """Вывод системной статистики по SIGUSR1"""
    log("INFO", f"[STATS DUMP] Запросов обработано: {REQUEST_COUNT}, Активных потоков: {threading.active_count()}")


# Регистрация обработчиков сигналов
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGHUP, handle_sighup)
signal.signal(signal.SIGUSR1, handle_sigusr1)


class HealthHandler(BaseHTTPRequestHandler):
    """Простой HTTP обработчик для проверки живости сервиса и сокет-активации"""
    def do_GET(self):
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        if self.path == "/status" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = (
                f'{{"status": "UP", "pid": {os.getpid()}, '
                f'"config_version": {CONFIG_VERSION}, "requests": {REQUEST_COUNT}}}\n'
            )
            self.wfile.write(response.encode("utf-8"))
            log("INFO", f"HTTP 200 GET {self.path} обработан для {self.client_address[0]}")
        elif self.path == "/crash":
            self.send_response(500)
            self.end_headers()
            log("CRITICAL", "Получен запрос на эндпоинт /crash! Имитируем критический сбой...")
            time.sleep(0.5)
            # Искусственное падение процесса
            raise RuntimeError("Fatal Exception: Unhandled segmentation fault simulation in worker thread")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Отключаем стандартный шум BaseHTTPRequestHandler, пишем через нашу функцию log
        pass


def run_http_server(host: str, port: int):
    try:
        server = HTTPServer((host, port), HealthHandler)
        log("INFO", f"HTTP Health-check сервер запущен на http://{host}:{port}/status")
        while RUNNING:
            server.handle_request()
    except Exception as e:
        if RUNNING:
            log("ERROR", f"Сбой в HTTP сервере: {e}")


def main():
    parser = argparse.ArgumentParser(description="Enterprise Mock Daemon for Linux Course")
    parser.add_argument("--port", type=int, default=8088, help="Порт для HTTP healthcheck (default: 8088)")
    parser.add_argument("--crash-on-start", action="store_true", help="Смоделировать падение сразу при инициализации")
    parser.add_argument("--crash-after", type=int, default=0, help="Уронить демон через N секунд работы")
    parser.add_argument("--leak-memory", action="store_true", help="Имитировать утечку памяти для срабатывания cgroups/OOM")
    parser.add_argument("--pidfile", type=str, default="", help="Путь для записи PID файла")
    args = parser.parse_args()

    log("INFO", "Инициализация службы Mock Application Daemon v2.4...")
    log("INFO", f"Рабочий каталог: {os.getcwd()}, Пользователь UID: {os.getuid()}, GID: {os.getgid()}")

    # Проверка намеренного сбоя старта (например, отсутствие прав или битый конфиг)
    if args.crash_on_start or os.environ.get("MOCK_CRASH_ON_START") == "1":
        log("CRITICAL", "Критическая ошибка конфигурации: Не удалось подключиться к upstream database cluster (10.0.0.1:5432)!")
        time.sleep(1)
        sys.exit(2)

    # Запись PID файла, если запрошено
    if args.pidfile:
        try:
            pid_dir = os.path.dirname(args.pidfile)
            if pid_dir and not os.path.exists(pid_dir):
                os.makedirs(pid_dir, exist_ok=True)
            with open(args.pidfile, "w") as f:
                f.write(str(os.getpid()))
            log("INFO", f"PID файл успешно создан: {args.pidfile}")
        except Exception as e:
            log("ERROR", f"Не удалось создать PID файл {args.pidfile}: {e}")

    # Запуск фонового HTTP сервера
    http_thread = threading.Thread(target=run_http_server, args=("0.0.0.0", args.port), daemon=True)
    http_thread.start()

    log("INFO", "Основной рабочий цикл сервиса успешно запущен и готов к работе.")

    start_time = time.time()
    iteration = 0
    memory_leaker = []

    try:
        while RUNNING:
            iteration += 1
            time.sleep(3)

            # Проверка флага аварийного сброса
            if os.path.exists("/tmp/mock_daemon_crash.flag"):
                log("CRITICAL", "Обнаружен триггерный файл /tmp/mock_daemon_crash.flag! Аварийное падение приложения!")
                os.remove("/tmp/mock_daemon_crash.flag")
                raise SystemError("Fatal Hardware/OS signal exception: SIGBUS simulation")

            if args.crash_after > 0 and (time.time() - start_time) > args.crash_after:
                log("CRITICAL", f"Истек таймаут стабильной работы ({args.crash_after}s). Провоцируем падение сервиса!")
                raise ZeroDivisionError("Uncaught division by zero in financial transaction math module")

            if args.leak_memory:
                # Выделяем по 10 МБ каждые 3 секунды
                chunk = b"A" * (10 * 1024 * 1024)
                memory_leaker.append(chunk)
                log("WARNING", f"[LEAK] Выделено памяти: {len(memory_leaker) * 10} MB...")

            if iteration % 5 == 0:
                log("INFO", f"Heartbeat: Служба работает стабильно. Uptime: {int(time.time() - start_time)}s. Запросов: {REQUEST_COUNT}")

    except Exception as exc:
        log("CRITICAL", f"Необработанное исключение: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
