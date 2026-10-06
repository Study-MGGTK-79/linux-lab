#!/usr/bin/env bash
# ==============================================================================
# Скрипт инициализации лабораторного окружения модуля 06
# Подготавливает тестовых пользователей, директории и стартовые файлы
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================================="
echo " [INIT] Подготовка лабораторного стенда Модуля 06"
echo "        Networking and Firewalls"
echo "=========================================================="

# 1. Проверка наличия PCAP дампа
if [[ ! -f "${SCRIPT_DIR}/sample_traffic.pcap" ]]; then
    echo "[*] Генерация эталонного сетевого дампа sample_traffic.pcap..."
    python3 "${SCRIPT_DIR}/generate_pcap.py"
fi

# 2. Создание тестовых учетных записей для аудита SSH (если запущен под root)
if [[ $EUID -eq 0 ]]; then
    echo "[*] Настройка тестовых системных учетных записей..."
    id -u devops &>/dev/null || useradd -m -s /bin/bash devops
    id -u deployer &>/dev/null || useradd -m -s /bin/bash deployer
    echo "devops:DevOps2026Password!" | chpasswd
    echo "deployer:DeployerSecurePass!" | chpasswd
    echo "[+] Пользователи 'devops' и 'deployer' готовы."
else
    echo "[!] Предупреждение: Скрипт запущен без прав root. Пропущен шаг создания системных пользователей."
fi

# 3. Установка прав на исполняемые файлы
chmod +x "${SCRIPT_DIR}"/*.sh "${SCRIPT_DIR}"/*.py 2>/dev/null || true

echo "=========================================================="
echo "[+] Окружение готово к выполнению лабораторных работ!"
echo "    - Стартовый дамп трафика: ${SCRIPT_DIR}/sample_traffic.pcap"
echo "    - Уязвимый конфиг SSH:    ${SCRIPT_DIR}/sshd_config_vulnerable"
echo "    - Генератор трафика:      ${SCRIPT_DIR}/simulate_traffic.sh"
echo "    - Сетевой стенд:          ${SCRIPT_DIR}/firewall_scenario.sh"
echo "=========================================================="
