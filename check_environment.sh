#!/usr/bin/env bash
#
# Скрипт проверки готовности окружения для прохождения курса по Linux
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  Проверка системного окружения для практических работ по Linux ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Проверка ОС и ядра
OS_NAME="Неизвестно"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$PRETTY_NAME
fi
echo -e "Операционная система: ${GREEN}${OS_NAME}${NC}"
echo -e "Версия ядра:         ${GREEN}$(uname -r)${NC}"
echo -e "Архитектура:         ${GREEN}$(uname -m)${NC}"

# 2. Проверка прав суперпользователя
if [ "$EUID" -ne 0 ]; then
    echo -e "\n${YELLOW}[ВНИМАНИЕ] Скрипт запущен не от root. Для настройки LVM, сетевых фильтров и сервисов понадобятся права sudo.${NC}"
else
    echo -e "Права root:          ${GREEN}Да (полный доступ)${NC}"
fi

# 3. Проверка наличия ключевых утилит
echo -e "\n${BLUE}--- Проверка наличия необходимых утилит ---${NC}"

REQUIRED_TOOLS=(
    "bash" "awk" "sed" "grep" "find" "tar"
    "ip" "ss" "ping" "curl"
    "systemctl" "journalctl"
    "losetup" "pvcreate" "vgcreate" "lvcreate"
    "strace" "lsof"
    "python3" "gcc" "make"
)

MISSING=0
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo -e "  [✓] $tool"
    else
        echo -e "  ${RED}[✗] $tool отсутствует${NC}"
        MISSING=$((MISSING + 1))
    fi
done

# 4. Проверка поддержки loop-устройств (для LVM и ФС)
echo -e "\n${BLUE}--- Проверка поддержки виртуальных дисков (loop devices) ---${NC}"
if command -v losetup >/dev/null 2>&1; then
    TEST_IMG=$(mktemp /tmp/test_loop_XXXXXX.img)
    truncate -s 10M "$TEST_IMG"
    if LOOP_DEV=$(losetup -f --show "$TEST_IMG" 2>/dev/null); then
        echo -e "  ${GREEN}[✓] Loopback устройства поддерживаются ($LOOP_DEV)${NC}"
        losetup -d "$LOOP_DEV" 2>/dev/null || true
    else
        echo -e "  ${YELLOW}[!] Не удалось смонтировать loop-устройство. В контейнерах Docker требуется флаг --privileged.${NC}"
    fi
    rm -f "$TEST_IMG"
fi

# 5. Итог
echo -e "\n${BLUE}================================================================${NC}"
if [ "$MISSING" -eq 0 ]; then
    echo -e "${GREEN}Все необходимые системные компоненты найдены! Окружение готово к курсу.${NC}"
else
    echo -e "${YELLOW}Найдено недостающих утилит: $MISSING.${NC}"
    echo -e "Для установки на Ubuntu/Debian выполните:"
    echo -e "  ${BLUE}sudo apt-get update && sudo apt-get install -y build-essential lvm2 strace lsof iproute2 net-tools nginx auditd fail2ban${NC}"
    echo -e "Для установки на RHEL/Rocky Linux выполните:"
    echo -e "  ${BLUE}sudo dnf install -y gcc make lvm2 strace lsof iproute bind-utils nginx audit${NC}"
    echo -e "Или запустите готовую лабораторию через Docker: ${BLUE}docker compose up -d${NC}"
fi
echo -e "${BLUE}================================================================${NC}"
