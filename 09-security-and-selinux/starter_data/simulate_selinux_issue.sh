#!/usr/bin/env bash
# Скрипт симуляции и проверки инцидента блокировки SELinux / AppArmor
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT_LOG="${SCRIPT_DIR}/audit_selinux_denials.log"

echo "================================================================="
echo "  [SELinux / AppArmor Security Incident Simulator & Inspector]   "
echo "================================================================="

# 1. Проверка наличия файла с AVC-отказами
if [ ! -f "${AUDIT_LOG}" ]; then
    echo "[-] Ошибка: Файл ${AUDIT_LOG} не найден!"
    exit 1
fi

echo "[*] Анализ инцидентов в журнале аудита: ${AUDIT_LOG}"
echo "-----------------------------------------------------------------"

# 2. Подсчет зафиксированных отказов AVC
DENIALS_COUNT=$(grep -c "type=AVC" "${AUDIT_LOG}" || true)
echo "[+] Найдено блокировок SELinux AVC: ${DENIALS_COUNT}"

# 3. Извлечение заблокированных процессов и системных вызовов
echo "[*] Заблокированные процессы и операции:"
grep "type=AVC" "${AUDIT_LOG}" | while IFS= read -r line; do
    comm=$(echo "$line" | sed -n 's/.*comm="\([^"]*\)".*/\1/p')
    denied=$(echo "$line" | sed -n 's/.*denied[[:space:]]*{\([^}]*\)}.*/\1/p' | tr -d ' ')
    sctx=$(echo "$line" | sed -n 's/.*scontext=\([^ ]*\).*/\1/p')
    tctx=$(echo "$line" | sed -n 's/.*tcontext=\([^ ]*\).*/\1/p')
    echo "  • Процесс: [${comm}] операция: {${denied}} | ${sctx} -> ${tctx}"
done

echo "-----------------------------------------------------------------"
# 4. Проверка реального статуса SELinux в текущей ОС
if command -v getenforce >/dev/null 2>&1; then
    CURRENT_MODE=$(getenforce || echo "Unknown")
    echo "[i] Текущий статус SELinux на этой машине: ${CURRENT_MODE}"
else
    echo "[i] Утилита getenforce не обнаружена (система работает в среде без SELinux или в контейнере)."
    echo "    Используйте журнал starter_data/audit_selinux_denials.log для разбора инцидентов."
fi

echo "================================================================="
echo "[✔] Симуляция завершена. Изучите вывод и приступайте к LABS.md."
