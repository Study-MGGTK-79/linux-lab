#!/usr/bin/env bash
# ==============================================================================
# Скрипт симуляции контролируемой активности для Threat Hunting и проверки Auditd
# Модуль 08: Incident Response, Log Tampering & Threat Hunting with Auditd
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE} [SIMULATOR] Генерация тестовой активности для проверки правил Auditd  ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Симуляция запуска исполняемого файла из временного каталога /tmp (T1059 / T1036)
echo -e "${YELLOW}[*] Симуляция 1: Запуск тестового скрипта из каталога /tmp...${NC}"
TEMP_SCRIPT="/tmp/threat_hunt_test_worker.sh"
cat << 'EOF' > "$TEMP_SCRIPT"
#!/usr/bin/env bash
# Тестовый фоновый процесс симулятора
echo "[SIMULATION-PROC] Тестовый процесс активен (PID: $$)"
exit 0
EOF
chmod +x "$TEMP_SCRIPT"
bash "$TEMP_SCRIPT"
rm -f "$TEMP_SCRIPT"

# 2. Симуляция обращения к защищенному файлу учетных данных (T1003.008)
echo -e "${YELLOW}[*] Симуляция 2: Симуляция обращения к /etc/shadow...${NC}"
if [ -r /etc/shadow ]; then
    # Если запущен от root или в контейнере с правами
    head -n 1 /etc/shadow > /dev/null 2>&1 || true
    echo "  [+] Выполнено чтение /etc/shadow (сгенерировано событие mitre_credential_access)"
else
    echo "  [!] Нет прав на чтение /etc/shadow (будет зафиксировано событие отказа: success=no)"
    cat /etc/shadow > /dev/null 2>&1 || true
fi

# 3. Симуляция манипуляций с логами в /var/log (T1070)
echo -e "${YELLOW}[*] Симуляция 3: Создание и удаление тестового файла лога в /var/log...${NC}"
TEST_LOG="/var/log/test_tamper_target.log"
if touch "$TEST_LOG" 2>/dev/null; then
    rm -f "$TEST_LOG"
    echo "  [+] Сгенерирован системный вызов unlink в /var/log (метка: mitre_log_tampering)"
else
    echo "  [!] Нет прав на запись в /var/log (пропущено без root)"
fi

# 4. Вывод инструкций по Threat Hunting
echo -e "\n${GREEN}[SUCCESS] Симуляция активности завершена!${NC}"
echo -e "Теперь выполните команды для охоты за сгенерированными событиями:"
echo -e "  1. Поиск выполнения из /tmp:"
echo -e "     ausearch -k mitre_execve -i | grep '/tmp'"
echo -e "  2. Поиск обращений к учетным файлам:"
echo -e "     ausearch -k mitre_credential_access -i"
echo -e "  3. Просмотр сводного отчета по исполняемым файлам:"
echo -e "     aureport -x --summary"
echo -e "${BLUE}======================================================================${NC}"
