#!/usr/bin/env bash
# ==============================================================================
# Скрипт симуляции сетевой активности и атак для отладки фаерволов и tcpdump
# Использование: ./simulate_traffic.sh [scan|flood|ssh_bruteforce|http_traffic] [TARGET_IP]
# ==============================================================================

set -euo pipefail

TARGET_IP="${2:-127.0.0.1}"
MODE="${1:-all}"

echo "=========================================================="
echo " [TRAFFIC-SIMULATOR] Целевой хост: ${TARGET_IP}"
echo " Режим: ${MODE}"
echo "=========================================================="

simulate_scan() {
    echo "[*] Запуск симуляции SYN/TCP сканирования портов..."
    local ports=(21 22 23 25 53 80 443 3306 5432 8080 8443)
    for p in "${ports[@]}"; do
        (timeout 0.3 nc -z -v "$TARGET_IP" "$p" 2>/dev/null || true) &
    done
    wait
    echo "[+] Сканирование завершено."
}

simulate_ssh_bruteforce() {
    local ssh_port="${SSH_PORT:-22}"
    echo "[*] Запуск симуляции брутфорса SSH на порт ${ssh_port} (10 попыток подключения)..."
    for i in {1..10}; do
        echo -n "SSH-2.0-ExploitTool_v1" | timeout 1 nc -w 1 "$TARGET_IP" "$ssh_port" >/dev/null 2>&1 || true
        echo "  [Попытка $i] Соединение инициировано..."
        sleep 0.2
    done
    echo "[+] Тест подбора SSH завершен."
}

simulate_http_traffic() {
    local http_port="${HTTP_PORT:-80}"
    echo "[*] Генерация HTTP-трафика (нормальный и подозрительный)..."
    # Обычный GET
    printf "GET / HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0\r\n\r\n" "$TARGET_IP" | \
        timeout 2 nc "$TARGET_IP" "$http_port" >/dev/null 2>&1 || true
    
    # Подозрительный User-Agent (сканер уязвимостей sqlmap)
    printf "GET /admin.php?id=1'OR'1'='1 HTTP/1.1\r\nHost: %s\r\nUser-Agent: sqlmap/1.6#stable\r\n\r\n" "$TARGET_IP" | \
        timeout 2 nc "$TARGET_IP" "$http_port" >/dev/null 2>&1 || true
    echo "[+] HTTP-запросы отправлены."
}

simulate_flood() {
    local target_port="${3:-80}"
    echo "[*] Генерация серии быстрых TCP-соединений (SYN burst)..."
    for i in {1..50}; do
        (timeout 0.2 nc -z "$TARGET_IP" "$target_port" 2>/dev/null || true) &
    done
    wait
    echo "[+] Всплеск трафика отправлен."
}

case "$MODE" in
    scan)
        simulate_scan
        ;;
    ssh_bruteforce)
        simulate_ssh_bruteforce
        ;;
    http_traffic)
        simulate_http_traffic
        ;;
    flood)
        simulate_flood
        ;;
    all)
        simulate_scan
        simulate_ssh_bruteforce
        simulate_http_traffic
        ;;
    *)
        echo "Неизвестный режим: $MODE"
        echo "Доступные режимы: scan, ssh_bruteforce, http_traffic, flood, all"
        exit 1
        ;;
esac

echo "[SUCCESS] Симуляция успешно выполнена."
