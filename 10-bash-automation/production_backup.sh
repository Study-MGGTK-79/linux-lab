#!/usr/bin/env bash
# ==============================================================================
# Скрипт промышленного резервного копирования данных с ротацией и алертингом
# Автор: Senior DevOps / SRE Engineer
# ==============================================================================

# 1. Строгий режим выполнения
set -euo pipefail
IFS=$'\n\t'

# 2. Определение глобальных констант и переменных по умолчанию
readonly SCRIPT_NAME="$(basename "$0")"
readonly HOST_NAME="$(hostname -f 2>/dev/null || hostname)"
readonly LOCK_FILE="/tmp/production_backup.lock"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

SRC_DIR=""
DST_DIR=""
RETENTION_DAYS=7
WEBHOOK_URL=""
DRY_RUN=false
TMP_DIR=""

# 3. Структурированный логгер (вывод только в stderr)
log_info()  { echo -e "\033[0;32m[INFO]  $(date '+%Y-%m-%d %H:%M:%S')\033[0m $*" >&2; }
log_warn()  { echo -e "\033[0;33m[WARN]  $(date '+%Y-%m-%d %H:%M:%S')\033[0m $*" >&2; }
log_error() { echo -e "\033[0;31m[ERROR] $(date '+%Y-%m-%d %H:%M:%S')\033[0m $*" >&2; }

# 4. Справка по использованию
usage() {
    cat << EOF
Использование: ${SCRIPT_NAME} -s <SRC_DIR> -d <DST_DIR> [ОПЦИИ]

Обязательные параметры:
  -s DIR       Каталог-источник данных
  -d DIR       Каталог для сохранения резервных копий

Опциональные параметры:
  -k NUM       Срок хранения архивов в днях (по умолчанию: 7)
  -w URL       URL вебхука для отправки алертов (HTTP POST)
  -n           Режим имитации (dry-run)
  -h           Вывод этой справки
EOF
    exit 1
}

# 5. Отправка алертов через Webhook
send_alert() {
    local -r status="$1"
    local -r message="$2"
    
    if [[ -z "${WEBHOOK_URL}" ]]; then
        return 0
    fi
    
    local -r payload=$(cat << EOF
{
  "host": "${HOST_NAME}",
  "script": "${SCRIPT_NAME}",
  "status": "${status}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "message": "${message}"
}
EOF
)
    log_info "Отправка уведомления на вебхук: ${WEBHOOK_URL}..."
    if ! curl -s -S -X POST -H "Content-Type: application/json" \
         --connect-timeout 5 --max-time 10 \
         -d "${payload}" "${WEBHOOK_URL}" >/dev/null 2>&1; then
        log_warn "Не удалось отправить алерт на ${WEBHOOK_URL}"
    fi
}

# 6. Функция финализации и безопасной очистки (Cleanup)
cleanup() {
    local -r exit_code=$?
    set +e # Отключаем errexit внутри cleanup во избежание сбоя при самой очистке
    
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Скрипт аварийно завершился с кодом ошибки: ${exit_code}"
        send_alert "FAILURE" "Аварийное завершение бэкапа на ${HOST_NAME} с кодом ${exit_code}"
    fi
    
    # Удаление временного каталога
    if [[ -n "${TMP_DIR:-}" && -d "${TMP_DIR}" ]]; then
        log_info "Очистка временного каталога: ${TMP_DIR}"
        rm -rf "${TMP_DIR}"
    fi
    
    # Снятие блокировки
    if [[ -f "${LOCK_FILE}" ]]; then
        rm -f "${LOCK_FILE}"
    fi
    if [[ -n "${LOCK_DIR:-}" && -d "${LOCK_DIR}" ]]; then
        rm -rf "${LOCK_DIR}"
    fi
    
    exit "${exit_code}"
}

# Регистрация перехватчика сигналов и выхода
trap cleanup EXIT INT TERM ERR

# 7. Парсинг параметров командной строки
while getopts ":s:d:k:w:nh" opt; do
    case "${opt}" in
        s) SRC_DIR="${OPTARG}" ;;
        d) DST_DIR="${OPTARG}" ;;
        k) RETENTION_DAYS="${OPTARG}" ;;
        w) WEBHOOK_URL="${OPTARG}" ;;
        n) DRY_RUN=true ;;
        h) usage ;;
        \?) log_error "Неизвестный параметр: -${OPTARG}"; usage ;;
        :)  log_error "Параметр -${OPTARG} требует аргумента!"; usage ;;
    esac
done
shift $((OPTIND - 1))

# 8. Строгая валидация аргументов
[[ -z "${SRC_DIR}" ]] && { log_error "Не задан обязательный параметр -s (источник)"; usage; }
[[ -z "${DST_DIR}" ]] && { log_error "Не задан обязательный параметр -d (назначение)"; usage; }
[[ ! -d "${SRC_DIR}" ]] && { log_error "Директория источника не существует: ${SRC_DIR}"; exit 2; }
[[ ! "${RETENTION_DAYS}" =~ ^[0-9]+$ ]] && { log_error "Параметр -k должен быть положительным числом!"; exit 2; }

# 9. Предотвращение параллельного запуска (flock с fallback на mkdir lock)
LOCK_DIR="${LOCK_FILE}.dir"
if command -v flock >/dev/null 2>&1; then
    exec 200>"${LOCK_FILE}"
    if ! flock -n 200; then
        log_error "Другой экземпляр скрипта уже запущен (файл блокировки: ${LOCK_FILE})!"
        exit 1
    fi
    echo "$$" > "${LOCK_FILE}"
else
    # Fallback для окружений без утилиты flock (POSIX атомарный mkdir)
    if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
        if [[ -f "${LOCK_DIR}/pid" ]] && kill -0 "$(cat "${LOCK_DIR}/pid" 2>/dev/null)" 2>/dev/null; then
            log_error "Другой экземпляр скрипта уже запущен (PID: $(cat "${LOCK_DIR}/pid"))!"
            exit 1
        fi
        rm -rf "${LOCK_DIR}"
        mkdir -p "${LOCK_DIR}"
    fi
    echo "$$" > "${LOCK_DIR}/pid"
fi

log_info "Запуск бэкапа: ${SRC_DIR} -> ${DST_DIR}"
log_info "Политика хранения: ${RETENTION_DAYS} дн., Dry-run: ${DRY_RUN}"

if [[ "${DRY_RUN}" == "true" ]]; then
    log_warn "Режим DRY-RUN включен. Физические изменения производиться не будут."
fi

# Создание целевой директории, если её нет
if [[ ! -d "${DST_DIR}" ]]; then
    log_info "Создание целевого каталога ${DST_DIR}..."
    [[ "${DRY_RUN}" == "false" ]] && mkdir -p "${DST_DIR}"
fi

# 10. Создание временного изолированного рабочего каталога
TMP_DIR=$(mktemp -d -t backup_stage_XXXXXX)
log_info "Создан рабочий каталог: ${TMP_DIR}"

ARCHIVE_NAME="backup_${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="${DST_DIR}/${ARCHIVE_NAME}"
CHECKSUM_PATH="${ARCHIVE_PATH}.sha256"

# 11. Создание архива
log_info "Упаковка и архивация данных (tar + gzip)..."
if [[ "${DRY_RUN}" == "false" ]]; then
    # Архивируем содержимое каталога SRC_DIR относительно него самого (-C)
    tar -czf "${ARCHIVE_PATH}" -C "${SRC_DIR}" .
    
    # 12. Генерация контрольной суммы
    log_info "Вычисление контрольной суммы SHA-256..."
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${ARCHIVE_PATH}" | awk '{print $1}' > "${CHECKSUM_PATH}"
    else
        shasum -a 256 "${ARCHIVE_PATH}" | awk '{print $1}' > "${CHECKSUM_PATH}"
    fi
    
    local_size=$(du -h "${ARCHIVE_PATH}" | awk '{print $1}')
    log_info "Архив успешно создан: ${ARCHIVE_PATH} (${local_size})"
    log_info "SHA-256: $(cat "${CHECKSUM_PATH}")"
else
    log_info "[DRY-RUN] Будет создан архив: ${ARCHIVE_PATH}"
fi

# 13. Ротация старых бэкапов
log_info "Выполнение ротации (удаление копий старше ${RETENTION_DAYS} дн.)..."
if [[ "${DRY_RUN}" == "false" ]]; then
    # Находим и удаляем устаревшие архивы и их суммы
    find "${DST_DIR}" -type f -name "backup_*.tar.gz" -mtime +"${RETENTION_DAYS}" -print0 | while IFS= read -r -d '' old_archive; do
        log_info "Удаление устаревшего архива: ${old_archive}"
        rm -f "${old_archive}"
        rm -f "${old_archive}.sha256"
    done
else
    find "${DST_DIR}" -type f -name "backup_*.tar.gz" -mtime +"${RETENTION_DAYS}" -exec echo "[DRY-RUN] Будет удален:" {} \;
fi

# 14. Успешное завершение и алерт
log_info "Процесс резервного копирования успешно завершен."
send_alert "SUCCESS" "Бэкап ${SRC_DIR} успешно создан: ${ARCHIVE_NAME} на ${HOST_NAME}"

exit 0
