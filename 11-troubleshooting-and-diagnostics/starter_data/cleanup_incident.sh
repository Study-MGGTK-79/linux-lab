#!/usr/bin/env bash
set -e

BASE_DIR="/tmp/linux_lab11"

echo "Остановка сервисов симуляции инцидентов..."

for pidfile in "${BASE_DIR}"/*.pid; do
    if [[ -f "${pidfile}" ]]; then
        pid=$(cat "${pidfile}" 2>/dev/null || true)
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            echo "Остановка процесса PID ${pid}..."
            kill -TERM "${pid}" 2>/dev/null || kill -9 "${pid}" 2>/dev/null || true
        fi
        rm -f "${pidfile}"
    fi
done

# Дополнительная зачистка по шаблонам имени
pkill -f "leak_space.py" 2>/dev/null || true
pkill -f "hanging_daemon.py" 2>/dev/null || true
pkill -f "critical_app.py" 2>/dev/null || true

# Удаление временной директории
if [[ -d "${BASE_DIR}" ]]; then
    rm -rf "${BASE_DIR}"
fi

echo "Окружение лабораторной работы 11 очищено."
