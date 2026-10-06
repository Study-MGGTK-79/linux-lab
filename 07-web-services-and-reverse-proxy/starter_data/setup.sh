#!/usr/bin/env bash
# ==============================================================================
# Скрипт инициализации окружения Модуля 07
# Web Infrastructure Exploitation, Nginx Misconfigurations & SSL Hardening
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/ssl"
WEBROOT="/tmp/college_linux_lab7/www"

stop_services() {
    echo "[*] Остановка фонового бэкенда..."
    pkill -f "backend_app.py" 2>/dev/null || true
    echo "[+] Службы остановлены."
}

if [[ "${1:-}" == "stop" ]]; then
    stop_services
    exit 0
fi

stop_services

echo "======================================================================"
echo " [SETUP] Развертывание лабораторного стенда Модуля 07"
echo "======================================================================"

# 1. Сделать скрипты исполняемыми
chmod +x "${SCRIPT_DIR}"/*.sh "${SCRIPT_DIR}"/*.py

# 2. Создание каталогов и файлов веб-приложения для проверки Alias Traversal
echo "[*] Подготовка файловой структуры веб-приложения в ${WEBROOT}..."
rm -rf "/tmp/college_linux_lab7"
mkdir -p "${WEBROOT}/static"

# Публичная статика
cat << 'EOF' > "${WEBROOT}/static/main.css"
/* Публичная таблица стилей приложения */
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; }
.card { border-radius: 8px; padding: 20px; background: #1e293b; border: 1px solid #334155; }
EOF

# Секретный файл конфигурации в корне приложения (родительский каталог для /static)
cat << 'EOF' > "${WEBROOT}/config.py"
# ==============================================================================
# КОНФИДЕНЦИАЛЬНАЯ КОНФИГУРАЦИЯ БЭКЕНДА (PRODUCTION SECRETS)
# ВНИМАНИЕ: Данный файл не должен быть доступен через веб-сервер!
# ==============================================================================
FLAG = "FLAG{nginx_alias_traversal_lfi_source_code_leak_2026}"
APP_SECRET_KEY = "sec_live_k98a12938fd89123bca01283"
DATABASE_URI = "postgresql://fintech_prod_user:SuperSecretDbPass2026!@10.0.100.5:5432/core_banking"
ADMIN_SESSION_SALT = "ea458129cbf9012351239aa8"
MASTER_ENCRYPTION_KEY = "0x89abf102394812a00019283746"
EOF

# Файл переменных окружения (.env)
cat << 'EOF' > "${WEBROOT}/.env"
# ENVIRONMENT SECRETS
ENVIRONMENT=production
DB_HOST=10.0.100.5
DB_PORT=5432
DB_NAME=core_banking
DB_USER=fintech_prod_user
DB_PASSWORD=SuperSecretDbPass2026!
JWT_SECRET=super_secret_jwt_signing_token_fintech_774
ADMIN_RECOVERY_EMAIL=security-lead@company.local
FLAG_ENV="FLAG{env_credentials_extracted_successfully}"
EOF

cat << 'EOF' > "${WEBROOT}/index.html"
<!DOCTYPE html>
<html>
<head><title>Fintech Portal</title><link rel="stylesheet" href="/static/main.css"></head>
<body><div class="card"><h1>Fintech Enterprise Portal</h1><p>Система функционирует в штатном режиме.</p></div></body>
</html>
EOF

# 3. Выпуск сертификатов SSL/TLS (если отсутствуют)
mkdir -p "${SSL_DIR}"
if [[ ! -f "${SSL_DIR}/server.crt" ]]; then
    echo "[*] Генерация SSL/TLS сертификатов..."
    "${SCRIPT_DIR}/generate_ssl.sh" "${SSL_DIR}"
fi

# 4. Запуск защищенного бэкенда в фоновом режиме на порту 8081
echo "[*] Запуск бэкенда на 127.0.0.1:8081..."
python3 "${SCRIPT_DIR}/backend_app.py" 8081 > /tmp/backend_lab7.log 2>&1 &
echo $! > /tmp/backend_lab7.pid

sleep 1

# 5. Проверка бэкенда
if curl -s http://127.0.0.1:8081/api/public | grep -q "UP"; then
    echo "  [+] Бэкенд успешно запущен и отвечает на http://127.0.0.1:8081"
else
    echo "  [!] Ошибка запуска бэкенда! Проверьте /tmp/backend_lab7.log"
    exit 1
fi

echo "======================================================================"
echo "[SUCCESS] Лабораторный стенд Модуля 07 инициализирован!"
echo "  - Веб-корень:        ${WEBROOT}"
echo "  - Секретные файлы:   ${WEBROOT}/config.py и ${WEBROOT}/.env"
echo "  - Сертификаты SSL:   ${SSL_DIR}"
echo "  - Уязвимый Nginx:    ${SCRIPT_DIR}/vulnerable_nginx.conf"
echo "  - Скрипт проверки:   ${SCRIPT_DIR}/exploit_test.sh"
echo ""
echo "Для запуска Nginx с уязвимой конфигурацией выполните:"
echo "  sudo nginx -c ${SCRIPT_DIR}/vulnerable_nginx.conf"
echo ""
echo "Для остановки стенда выполните: ${SCRIPT_DIR}/setup.sh stop"
echo "======================================================================"
