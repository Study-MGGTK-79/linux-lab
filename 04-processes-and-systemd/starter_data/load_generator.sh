#!/usr/bin/env bash
# ==============================================================================
# Script: load_generator.sh
# Purpose: Генератор управляемой нагрузки (CPU, RAM, сигналы) для практической
#          отработки мониторинга процессов (top, htop, nice, renice, signals).
# ==============================================================================

set -euo pipefail

PID_FILE="/tmp/linux_lab_load_pids.txt"

usage() {
    echo "Использование: $0 [КОМАНДА]"
    echo ""
    echo "Команды:"
    echo "  --cpu [N]       Запустить N фоновых процессов, нагружающих CPU (по умолчанию: 2)"
    echo "  --memory [MB]   Выделить указанный объем памяти через Python"
    echo "  --signals       Отправить последовательность сигналов (SIGHUP, SIGUSR1, SIGTERM) в mock_daemon"
    echo "  --crash         Создать файл /tmp/mock_daemon_crash.flag для аварийного падения демона"
    echo "  --status        Показать статус текущих нагрузочных процессов"
    echo "  --stop          Завершить все сгенерированные нагрузочные процессы"
    echo ""
}

case "${1:-}" in
    --cpu)
        COUNT="${2:-2}"
        echo "Запуск ${COUNT} фоновых вычислительных потоков CPU (SHA256 циклы)..."
        for i in $(seq 1 "${COUNT}"); do
            (
                while true; do
                    echo -n "test" | sha256sum > /dev/null
                done
            ) &
            CPUPID=$!
            echo "${CPUPID}" >> "${PID_FILE}"
            echo "  [+] Поток #${i} запущен с PID: ${CPUPID}"
        done
        echo "Используйте 'top' или 'htop' для наблюдения. Процессы можно приоритизировать через 'renice'."
        ;;

    --memory)
        MB="${2:-200}"
        echo "Выделение ${MB} MB оперативной памяти..."
        python3 -c "
import time, sys
size_mb = int('${MB}')
print(f'Выделяем {size_mb} MB памяти...')
data = bytearray(size_mb * 1024 * 1024)
print('Память выделена. Удерживаем 60 секунд. Наблюдайте в free -m / top...')
time.sleep(60)
" &
        MEMPID=$!
        echo "${MEMPID}" >> "${PID_FILE}"
        echo "  [+] Процесс удержания памяти запущен с PID: ${MEMPID}"
        ;;

    --signals)
        echo "Поиск активного экземпляра mock_daemon.py..."
        DPID=$(pgrep -f "python3.*mock_daemon.py" | head -n 1 || true)
        if [[ -z "${DPID}" ]]; then
            echo "[ОШИБКА] Процесс mock_daemon.py не найден! Запустите сервис перед тестированием."
            exit 1
        fi
        echo "Найден демон с PID: ${DPID}"

        echo "1. Отправка сигнала SIGHUP (перечитывание конфигурации)..."
        kill -HUP "${DPID}"
        sleep 1

        echo "2. Отправка сигнала SIGUSR1 (дамп статистики)..."
        kill -USR1 "${DPID}"
        sleep 1

        echo "Проверьте вывод журнала: sudo journalctl -u mock_daemon -n 5"
        ;;

    --crash)
        echo "Создание триггера падения /tmp/mock_daemon_crash.flag..."
        touch /tmp/mock_daemon_crash.flag
        echo "Флаг создан. Демон перехватит его в течение 3 секунд и завершится с ошибкой."
        ;;

    --status)
        if [[ -f "${PID_FILE}" ]]; then
            echo "Список фоновых нагрузочных процессов:"
            while read -r p; do
                if kill -0 "$p" 2>/dev/null; then
                    ps -p "$p" -o pid,ni,pcpu,pmem,args
                else
                    echo "PID $p уже завершен."
                fi
            done < "${PID_FILE}"
        else
            echo "Активных фоновых нагрузок не зарегистрировано."
        fi
        ;;

    --stop)
        echo "Остановка всех фоновых нагрузочных процессов..."
        if [[ -f "${PID_FILE}" ]]; then
            while read -r p; do
                if kill -0 "$p" 2>/dev/null; then
                    echo "  [-] Остановка PID $p (SIGTERM)..."
                    kill "$p" 2>/dev/null || true
                fi
            done < "${PID_FILE}"
            rm -f "${PID_FILE}"
        fi
        # Принудительная очистка возможных зомби-потоков sha256
        pkill -f "sha256sum" 2>/dev/null || true
        echo "Все нагрузочные процессы остановлены."
        ;;

    *)
        usage
        exit 1
        ;;
esac
