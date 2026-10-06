#!/usr/bin/env bash
# ==============================================================================
# Script: cleanup_disks.sh
# Purpose: Полная безопасная очистка виртуальных томов, LVM, точек монтирования
#          и loop-устройств после выполнения лабораторной работы.
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] Этот скрипт должен быть запущен с правами root (sudo)!${NC}"
   exit 1
fi

STORAGE_DIR="/var/tmp/linux_lab_storage"
STATE_FILE="${STORAGE_DIR}/loop_devices.env"

echo -e "${BLUE}====================================================================${NC}"
echo -e "${BLUE}   Очистка лабораторных дисков и освобождение системных ресурсов    ${NC}"
echo -e "${BLUE}====================================================================${NC}"

# 1. Отмонтирование тестовых каталогов
echo -e "\n${YELLOW}[1/5] Отмонтирование лабораторных файловых систем...${NC}"
for mp in /mnt/snapshot /mnt/mock_db /mnt/analytics /mnt/wal_logs; do
    if mountpoint -q "$mp" 2>/dev/null; then
        echo -e "  - Отмонтирование ${mp}..."
        umount -f "$mp" || true
    fi
    rm -rf "$mp" || true
done

# Отключение тестового swap, если он был создан на loop-диске
echo -e "\n${YELLOW}[2/5] Проверка и деактивация тестового Swap...${NC}"
if [[ -f "${STATE_FILE}" ]]; then
    source "${STATE_FILE}" || true
    for dev in ${LOOP_DISK1:-} ${LOOP_DISK2:-} ${LOOP_DISK3:-}; do
        if [[ -n "${dev}" ]]; then
            swapoff "${dev}*" 2>/dev/null || true
        fi
    done
fi

# 2. Удаление тестовых LVM структур, если они были созданы
echo -e "\n${YELLOW}[3/5] Деактивация и удаление тестовых LVM VG/LV...${NC}"
if vgs vg_storage &>/dev/null; then
    echo -e "  - Удаление Volume Group 'vg_storage'..."
    vgremove -y -f vg_storage || true
fi
if vgs vg_db &>/dev/null; then
    echo -e "  - Удаление Volume Group 'vg_db'..."
    vgremove -y -f vg_db || true
fi

# 3. Удаление PV метаданных
if [[ -f "${STATE_FILE}" ]]; then
    source "${STATE_FILE}" || true
    for dev in ${LOOP_DISK1:-} ${LOOP_DISK2:-} ${LOOP_DISK3:-}; do
        if [[ -n "${dev}" ]] && pvs "${dev}*" &>/dev/null; then
            pvremove -y -ff "${dev}*" 2>/dev/null || true
        fi
    done
fi

# 4. Отключение loop-устройств
echo -e "\n${YELLOW}[4/5] Отключение loop-устройств через losetup...${NC}"
if [[ -f "${STATE_FILE}" ]]; then
    source "${STATE_FILE}" || true
    for dev in ${LOOP_DISK1:-} ${LOOP_DISK2:-} ${LOOP_DISK3:-}; do
        if [[ -n "${dev}" ]] && losetup "${dev}" &>/dev/null; then
            echo -e "  - Отключение ${dev}..."
            losetup -d "${dev}" || true
        fi
    done
    rm -f "${STATE_FILE}"
fi

# Дополнительный поиск зависших loop устройств для disk*.img
for img in "${STORAGE_DIR}"/disk*.img; do
    if [[ -f "$img" ]]; then
        ACTIVE_LOOPS=$(losetup -j "$img" | cut -d: -f1 || true)
        for al in $ACTIVE_LOOPS; do
            echo -e "  - Отключение остаточного ${al}..."
            losetup -d "$al" || true
        done
    fi
done

# 5. Удаление директории со sparse-файлами
echo -e "\n${YELLOW}[5/5] Удаление образов дисков...${NC}"
rm -rf "${STORAGE_DIR}"
rm -rf /var/tmp/mock_db_source

echo -e "\n${GREEN}====================================================================${NC}"
echo -e "${GREEN}✓ Очистка полностью завершена. Система возвращена в исходное состояние!${NC}"
echo -e "${GREEN}====================================================================${NC}"
