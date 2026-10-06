#!/usr/bin/env bash
# ==============================================================================
# Script: setup_disks.sh
# Purpose: Создание изолированных виртуальных дисков через sparse-файлы и losetup
#          для безопасного прохождения лабораторных работ по разметке и LVM.
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Проверка запуска от суперпользователя
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] Этот скрипт должен быть запущен с правами root (sudo)!${NC}"
   exit 1
fi

STORAGE_DIR="/var/tmp/linux_lab_storage"
STATE_FILE="${STORAGE_DIR}/loop_devices.env"

echo -e "${BLUE}====================================================================${NC}"
echo -e "${BLUE}  Инициализация виртуальных блочных устройств для курса Linux Lab   ${NC}"
echo -e "${BLUE}====================================================================${NC}"

# Создаем директорию для хранения образов дисков
mkdir -p "${STORAGE_DIR}"

# 1. Создание разреженных (sparse) файлов дисков
# Sparse-файлы занимают 0 байт на физическом накопителе до момента записи данных!
echo -e "\n${YELLOW}[1/4] Создание sparse-файлов дисков...${NC}"
truncate -s 1G "${STORAGE_DIR}/disk1.img"
truncate -s 1G "${STORAGE_DIR}/disk2.img"
truncate -s 2G "${STORAGE_DIR}/disk3.img"

echo -e "  - ${STORAGE_DIR}/disk1.img (1 GiB)"
echo -e "  - ${STORAGE_DIR}/disk2.img (1 GiB)"
echo -e "  - ${STORAGE_DIR}/disk3.img (2 GiB)"

# 2. Очистка старых loop-привязок, если они существовали в state файле
if [[ -f "${STATE_FILE}" ]]; then
    echo -e "\n${YELLOW}[!] Обнаружен предыдущий state-файл, выполняем предварительную очистку...${NC}"
    source "${STATE_FILE}" || true
    for dev in ${LOOP_DISK1:-} ${LOOP_DISK2:-} ${LOOP_DISK3:-}; do
        if [[ -n "${dev}" ]] && losetup "${dev}" &>/dev/null; then
            losetup -d "${dev}" || true
        fi
    done
    rm -f "${STATE_FILE}"
fi

# 3. Подключение файлов через losetup к loop-устройствам
echo -e "\n${YELLOW}[2/4] Подключение к loop-устройствам через losetup...${NC}"
LOOP1=$(losetup -f --show "${STORAGE_DIR}/disk1.img")
LOOP2=$(losetup -f --show "${STORAGE_DIR}/disk2.img")
LOOP3=$(losetup -f --show "${STORAGE_DIR}/disk3.img")

# Сохранение сопоставления в env-файл для удобства использования студентами
cat <<EOF > "${STATE_FILE}"
export LOOP_DISK1="${LOOP1}"
export LOOP_DISK2="${LOOP2}"
export LOOP_DISK3="${LOOP3}"
export STORAGE_DIR="${STORAGE_DIR}"
EOF
chmod 644 "${STATE_FILE}"

echo -e "  ${GREEN}✓${NC} Диск 1 (1G)  -> ${GREEN}${LOOP1}${NC}"
echo -e "  ${GREEN}✓${NC} Диск 2 (1G)  -> ${GREEN}${LOOP2}${NC}"
echo -e "  ${GREEN}✓${NC} Диск 3 (2G)  -> ${GREEN}${LOOP3}${NC}"

# 4. Подготовка тестовых точек монтирования
echo -e "\n${YELLOW}[3/4] Подготовка стандартных точек монтирования...${NC}"
mkdir -p /mnt/wal_logs
mkdir -p /mnt/analytics
mkdir -p /mnt/mock_db
mkdir -p /mnt/snapshot

# Копирование mock-данных для практики миграции
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "${SCRIPT_DIR}/mock_db_data" ]]; then
    mkdir -p /var/tmp/mock_db_source
    cp -r "${SCRIPT_DIR}/mock_db_data/"* /var/tmp/mock_db_source/
    echo -e "  ${GREEN}✓${NC} Исходные данные MockDB скопированы в /var/tmp/mock_db_source/"
fi

# 5. Вывод текущей топологии блочных устройств
echo -e "\n${YELLOW}[4/4] Текущая топология блочных устройств:${NC}"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS "${LOOP1}" "${LOOP2}" "${LOOP3}"

echo -e "\n${GREEN}====================================================================${NC}"
echo -e "${GREEN}✓ Окружение успешно настроено!${NC}"
echo -e "Переменные окружения сохранены в: ${YELLOW}${STATE_FILE}${NC}"
echo -e "Вы можете загрузить их в терминал: ${BLUE}source ${STATE_FILE}${NC}"
echo -e "Для завершения работы и удаления дисков запустите: ${YELLOW}sudo bash ./cleanup_disks.sh${NC}"
echo -e "${GREEN}====================================================================${NC}"
