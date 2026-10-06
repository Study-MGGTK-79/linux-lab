#!/usr/bin/env bash
# ==============================================================================
# Script: backup_task.sh
# Purpose: Имитация периодической задачи резервного копирования для отработки
#          настройки Systemd Timers вместо Crontab.
# ==============================================================================

set -euo pipefail

BACKUP_SRC="/var/log"
BACKUP_DEST="/var/tmp/lab_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_NAME="${BACKUP_DEST}/system_logs_${TIMESTAMP}.tar.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Старт процедуры резервного копирования..."
mkdir -p "${BACKUP_DEST}"

# Создаем сжатый архив части системных логов
if tar -czf "${ARCHIVE_NAME}" -C "${BACKUP_SRC}" alternatives.log 2>/dev/null; then
    ARCHIVE_SIZE=$(du -h "${ARCHIVE_NAME}" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Резервная копия успешно создана: ${ARCHIVE_NAME} (Размер: ${ARCHIVE_SIZE})"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] Лог-файлы не найдены, создаем тестовый маркер..."
    echo "Sample backup payload ${TIMESTAMP}" > "${ARCHIVE_NAME}"
fi

# Оставляем только 3 последних бэкапа (ротация)
cd "${BACKUP_DEST}"
ls -t system_logs_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f --
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Ротация выполнена. Старые копии очищены."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] Задача бэкапа завершена успешно."
