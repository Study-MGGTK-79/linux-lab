#!/usr/bin/env bash
# ==============================================================================
# Скрипт автоматизированной генерации инфраструктуры сертификатов (PKI)
# Создает локальный доверенный CA и выпускает сертификат сервера с SAN
# ==============================================================================

set -euo pipefail

TARGET_DIR="${1:-./ssl}"
mkdir -p "$TARGET_DIR"

echo "=========================================================="
echo " [PKI-GENERATOR] Генерация SSL/TLS сертификатов с SAN"
echo " Каталог назначения: ${TARGET_DIR}"
echo "=========================================================="

# 1. Генерация приватного ключа корневого удостоверяющего центра (Root CA)
echo "[*] 1. Генерация ключа и сертификата Root CA (RSA 4096)..."
openssl genrsa -out "${TARGET_DIR}/rootCA.key" 4096 2>/dev/null

openssl req -x509 -new -nodes -key "${TARGET_DIR}/rootCA.key" -sha256 -days 3650 \
    -out "${TARGET_DIR}/rootCA.crt" \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=Linux College Lab CA/OU=DevOps/CN=College-Root-CA" 2>/dev/null

echo "    [+] Создан Root CA: ${TARGET_DIR}/rootCA.crt"

# 2. Генерация приватного ключа сервера
echo "[*] 2. Генерация приватного ключа веб-сервера (RSA 2048)..."
openssl genrsa -out "${TARGET_DIR}/server.key" 2048 2>/dev/null

# 3. Создание запроса на подпись (CSR)
echo "[*] 3. Создание CSR для доменов *.lab.local..."
openssl req -new -key "${TARGET_DIR}/server.key" -out "${TARGET_DIR}/server.csr" \
    -subj "/C=RU/ST=Moscow/O=Enterprise Web/CN=portal.lab.local" 2>/dev/null

# 4. Создание файла конфигурации расширений SAN (Subject Alternative Names)
cat > "${TARGET_DIR}/san.ext" << 'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = portal.lab.local
DNS.2 = api.lab.local
DNS.3 = *.lab.local
DNS.4 = localhost
IP.1 = 127.0.0.1
EOF

# 5. Выпуск и подпись сертификата сервера корневым CA
echo "[*] 4. Подпись сертификата сервера корневым CA..."
openssl x509 -req -in "${TARGET_DIR}/server.csr" \
    -CA "${TARGET_DIR}/rootCA.crt" \
    -CAkey "${TARGET_DIR}/rootCA.key" \
    -CAcreateserial \
    -out "${TARGET_DIR}/server.crt" \
    -days 365 -sha256 -extfile "${TARGET_DIR}/san.ext" 2>/dev/null

# 6. Проверка валидности цепочки
echo "[*] 5. Валидация сертификата через openssl verify..."
openssl verify -CAfile "${TARGET_DIR}/rootCA.crt" "${TARGET_DIR}/server.crt"

# Установка безопасных прав на приватные ключи
chmod 600 "${TARGET_DIR}"/*.key
chmod 644 "${TARGET_DIR}"/*.crt

echo "=========================================================="
echo "[SUCCESS] Сертификаты успешно сгенерированы в ${TARGET_DIR}:"
echo "  - Корневой CA:         ${TARGET_DIR}/rootCA.crt"
echo "  - Приватный ключ CA:   ${TARGET_DIR}/rootCA.key"
echo "  - Сертификат сервера:  ${TARGET_DIR}/server.crt"
echo "  - Приватный ключ серв: ${TARGET_DIR}/server.key"
echo "=========================================================="
echo "Пример проверки через curl:"
echo "curl --cacert ${TARGET_DIR}/rootCA.crt https://portal.lab.local"
