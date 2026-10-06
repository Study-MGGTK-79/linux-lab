#!/usr/bin/env bash
# ==============================================================================
# Сценарий настройки тестового стенда для лабораторных работ по Firewall
# Создает виртуальные сетевые интерфейсы, имитирующие DMZ и внутреннюю сеть
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " [SETUP] Развертывание виртуальной топологии сети"
echo "=========================================================="

# Проверка прав суперпользователя
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] Данный скрипт должен быть запущен с правами root (sudo)."
   exit 1
fi

# 1. Загрузка модуля ядра dummy (если доступно)
modprobe dummy 2>/dev/null || true

# 2. Создание виртуальных интерфейсов для имитации зон
# eth-dmz: 172.16.10.1/24 (DMZ с публичными веб-сервисами)
# eth-internal: 10.10.20.1/24 (Внутренняя защищенная сеть с БД)

clean_interfaces() {
    echo "[*] Очистка предыдущих интерфейсов..."
    ip link del eth-dmz 2>/dev/null || true
    ip link del eth-internal 2>/dev/null || true
}

clean_interfaces

echo "[*] Создание интерфейса DMZ (eth-dmz)..."
ip link add eth-dmz type dummy 2>/dev/null || ip link add dev eth-dmz type veth peer name veth-dmz-peer || true
ip addr add 172.16.10.1/24 dev eth-dmz 2>/dev/null || true
ip link set dev eth-dmz up

echo "[*] Создание интерфейса внутренней сети (eth-internal)..."
ip link add eth-internal type dummy 2>/dev/null || ip link add dev eth-internal type veth peer name veth-int-peer || true
ip addr add 10.10.20.1/24 dev eth-internal 2>/dev/null || true
ip link set dev eth-internal up

# 3. Включение маршрутизации пакетов в ядре (IP Forwarding)
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "----------------------------------------------------------"
echo "[+] Топология успешно создана:"
echo "    - Зона DMZ:      интерфейс eth-dmz      (IP: 172.16.10.1/24)"
echo "    - Зона Internal: интерфейс eth-internal (IP: 10.10.20.1/24)"
echo "    - IP Forwarding: включен"
echo "----------------------------------------------------------"
echo "Для сброса тестовой топологии запустите: sudo ./firewall_scenario.sh clean"

if [[ "${1:-}" == "clean" ]]; then
    clean_interfaces
    echo "[+] Стенд очищен."
fi
