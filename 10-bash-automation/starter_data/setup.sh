#!/usr/bin/env bash
set -euo pipefail

# Каталог развертывания тестового стенда
BASE_DIR="/tmp/linux_lab10"
SRC_DIR="${BASE_DIR}/source_data"
DST_DIR="${BASE_DIR}/backups"
LOG_DIR="${BASE_DIR}/logs"

echo "=== Развертывание тестового стенда для Модуля 10 (Bash Automation) ==="

# Очистка предыдущего состояния при повторном запуске
rm -rf "${BASE_DIR}"
mkdir -p "${SRC_DIR}" "${DST_DIR}" "${LOG_DIR}"

# 1. Создание реалистичной структуры данных для бекапа
echo "Генерация тестовых данных в ${SRC_DIR}..."

# Обычные текстовые файлы и конфиги
cat << 'EOF' > "${SRC_DIR}/app.conf"
# Production Application Config
ENVIRONMENT=production
DATABASE_HOST=10.0.0.15
DATABASE_PORT=5432
CACHE_ENABLED=true
EOF

cat << 'EOF' > "${SRC_DIR}/database_dump.sql"
-- PostgreSQL Dump Sample
CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50), email VARCHAR(100));
INSERT INTO users (username, email) VALUES ('admin', 'admin@corp.internal');
INSERT INTO users (username, email) VALUES ('deploy', 'deploy@corp.internal');
EOF

# Файлы с пробелами и спецсимволами в именах (тестирование word-splitting и кавычек)
echo "Тестовый отчет финансового аудита 2026" > "${SRC_DIR}/Financial Report 2026 Q1.txt"
echo "Служебная заметка с символами & # @" > "${SRC_DIR}/notes [important] & draft.doc"

# Вложенные каталоги
mkdir -p "${SRC_DIR}/certs" "${SRC_DIR}/uploads/2026/05"
echo "CERT_PLACEHOLDER_DATA" > "${SRC_DIR}/certs/server.crt"
echo "KEY_PLACEHOLDER_DATA" > "${SRC_DIR}/certs/server.key"
chmod 600 "${SRC_DIR}/certs/server.key"

# Бинарные данные (1 МБ псевдослучайных байт)
dd if=/dev/urandom of="${SRC_DIR}/uploads/2026/05/avatar_archive.bin" bs=1024 count=1024 status=none

# 2. Создание "старых" архивных копий для проверки алгоритма ротации
echo "Создание эмуляции архивов с историей изменений в ${DST_DIR}..."

touch -d "15 days ago" "${DST_DIR}/backup_20260920_030000.tar.gz" 2>/dev/null || touch -t 202609200300 "${DST_DIR}/backup_20260920_030000.tar.gz"
touch -d "10 days ago" "${DST_DIR}/backup_20260925_030000.tar.gz" 2>/dev/null || touch -t 202609250300 "${DST_DIR}/backup_20260925_030000.tar.gz"
touch -d "5 days ago"  "${DST_DIR}/backup_20260930_030000.tar.gz" 2>/dev/null || touch -t 202609300300 "${DST_DIR}/backup_20260930_030000.tar.gz"
touch -d "2 days ago"  "${DST_DIR}/backup_20261003_030000.tar.gz" 2>/dev/null || touch -t 202610030300 "${DST_DIR}/backup_20261003_030000.tar.gz"
touch -d "1 days ago"  "${DST_DIR}/backup_20261004_030000.tar.gz" 2>/dev/null || touch -t 202610040300 "${DST_DIR}/backup_20261004_030000.tar.gz"

# Делаем скрипты исполняемыми
chmod +x "$(dirname "$0")/broken_backup.sh"

echo "✅ Тестовое окружение готово!"
echo "   Каталог с данными для бекапа : ${SRC_DIR}"
echo "   Каталог целевых архивов      : ${DST_DIR}"
echo "   Лог-директория               : ${LOG_DIR}"
