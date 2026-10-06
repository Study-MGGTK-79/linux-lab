#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/tmp/linux_lab11"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================"
echo "🚨 СИМУЛЯТОР ПРОИЗВОДСТВЕННЫХ СБОЕВ: МОДУЛЬ 11 (ТРАБЛШУТИНГ)"
echo "======================================================================"

# 1. Очистка старого состояния
bash "${SCRIPT_DIR}/cleanup_incident.sh" 2>/dev/null || true
mkdir -p "${BASE_DIR}/data"

# 2. Инцидент 1: Запуск генератора утечки дискового пространства
echo "[1/3] Запуск сервиса с открытым удаленным дескриптором (leak_space.py)..."
python3 "${SCRIPT_DIR}/leak_space.py" > "${BASE_DIR}/leak_space.log" 2>&1 &
LEAK_PID=$!
sleep 2

# 3. Инцидент 2: Запуск зависшего микросервиса
echo "[2/3] Запуск зависшего демона без таймаута (hanging_daemon.py)..."
python3 "${SCRIPT_DIR}/hanging_daemon.py" > "${BASE_DIR}/hanging_daemon.log" 2>&1 &
HANG_PID=$!
sleep 1

# 4. Инцидент 3: Запуск критического сервиса и симуляция случайного удаления файла
echo "[3/3] Запуск сервиса транзакций и случайное удаление активного лога..."
python3 "${SCRIPT_DIR}/critical_app.py" > "${BASE_DIR}/critical_app.log" 2>&1 &
CRIT_PID=$!
sleep 2

# Симуляция случайного rm со стороны неопытного администратора:
if [[ -f "${BASE_DIR}/data/critical_transactions.log" ]]; then
    rm -f "${BASE_DIR}/data/critical_transactions.log"
    echo "⚠️  [АКТ САБОТАЖА]: Файл /tmp/linux_lab11/data/critical_transactions.log был удален через rm!"
    echo "   Процесс PID ${CRIT_PID} продолжает писать новые транзакции в пустоту..."
fi

echo ""
echo "✅ Окружение инцидентов успешно развернуто!"
echo "----------------------------------------------------------------------"
echo "Сводка активных инцидентов:"
echo " • Утечка диска (PID ${LEAK_PID})   : файл удален из каталога, но дескриптор открыт."
echo " • Зависший сервис (PID ${HANG_PID}): потребляет 0% CPU, застрял на системном вызове."
echo " • Спасение файла (PID ${CRIT_PID}) : удален critical_transactions.log, нужно восстановить."
echo "----------------------------------------------------------------------"
echo "Для завершения работы и очистки стенда выполните: bash starter_data/cleanup_incident.sh"
