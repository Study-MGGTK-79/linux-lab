#!/usr/bin/env bash
# ==============================================================================
# Скрипт тестирования Nginx Reverse Proxy, SSL, Балансировки и Кэширования
# Использование: ./test_requests.sh [all|balance|ssl|cache|ratelimit]
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/ssl"
CA_CERT="${SSL_DIR}/rootCA.crt"
MODE="${1:-all}"

echo "=========================================================="
echo " [TEST-SUITE] Тестирование Nginx Reverse Proxy"
echo " Режим: ${MODE}"
echo "=========================================================="

test_balance() {
    echo "[*] 1. Проверка балансировки нагрузки между бэкендами (10 запросов)..."
    for i in {1..10}; do
        local resp
        resp=$(curl -s -H "Host: portal.lab.local" http://127.0.0.1/api/ || true)
        local instance
        instance=$(echo "$resp" | grep -o '"instance": "[^"]*"' | head -1 || echo "unknown")
        local port
        port=$(echo "$resp" | grep -o '"port": [0-9]*' | head -1 || echo "unknown")
        echo "  [Запрос $i] Ответ от: $instance ($port)"
        sleep 0.1
    done
    echo "[+] Тест балансировки завершен."
}

test_ssl() {
    echo "[*] 2. Проверка SSL/TLS соединения и валидации сертификата..."
    if [[ ! -f "$CA_CERT" ]]; then
        echo "[!] Внимание: CA сертификат $CA_CERT не найден. Запустите сначала generate_ssl.sh"
        return
    fi
    # Запрос с проверкой CA
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --cacert "$CA_CERT" --resolve portal.lab.local:443:127.0.0.1 https://portal.lab.local/ || true)
    echo "  [HTTPS Request] Статус-код ответа: $http_code"
    
    # Проверка редиректа 80 -> 443
    local redirect_header
    redirect_header=$(curl -s -I -H "Host: portal.lab.local" http://127.0.0.1/ | grep -i "Location" || true)
    echo "  [HTTP->HTTPS Redirect] Заголовок редиректа: $redirect_header"
    echo "[+] Тест SSL завершен."
}

test_cache() {
    echo "[*] 3. Проверка кэширования ответов (заголовок X-Cache-Status)..."
    for i in 1 2 3; do
        local status_hdr
        status_hdr=$(curl -s -I -H "Host: portal.lab.local" http://127.0.0.1/cached/api/info 2>/dev/null | grep -i "X-Cache-Status" || echo "X-Cache-Status: Not Found")
        echo "  [Запрос $i] $status_hdr"
        sleep 0.2
    done
    echo "[+] Тест кэширования завершен."
}

test_ratelimit() {
    echo "[*] 4. Проверка Rate Limiting (отправка 20 быстрых запросов на /login)..."
    local count_200=0
    local count_429=0
    local count_503=0
    for i in {1..20}; do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: portal.lab.local" http://127.0.0.1/login || true)
        if [[ "$code" == "200" ]]; then
            count_200=$((count_200 + 1))
        elif [[ "$code" == "429" ]]; then
            count_429=$((count_429 + 1))
        elif [[ "$code" == "503" ]]; then
            count_503=$((count_503 + 1))
        fi
    done
    echo "  Результаты: 200 OK: $count_200 | Ограничено (429/503): $((count_429 + count_503))"
    echo "[+] Тест Rate Limiting завершен."
}

case "$MODE" in
    balance)
        test_balance
        ;;
    ssl)
        test_ssl
        ;;
    cache)
        test_cache
        ;;
    ratelimit)
        test_ratelimit
        ;;
    all)
        test_balance
        test_ssl
        test_cache
        test_ratelimit
        ;;
    *)
        echo "Неизвестный режим: $MODE"
        echo "Использование: $0 [all|balance|ssl|cache|ratelimit]"
        exit 1
        ;;
esac
