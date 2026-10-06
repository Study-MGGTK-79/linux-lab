#!/usr/bin/env bash
# ==============================================================================
# Инициализация криминалистических данных для Модуля 08
# Incident Response, Log Tampering & Threat Hunting with Auditd
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [Модуль 08] Инициализация криминалистических данных (DFIR Evidence) ==="

# 1. Права на исполнение
chmod +x "${SCRIPT_DIR}"/*.sh "${SCRIPT_DIR}"/*.py

# 2. Удаление устаревших нерелевантных файлов, если присутствуют
rm -f "${SCRIPT_DIR}/app-production.log" 2>/dev/null || true

# 3. Генерация дампов журналов инцидента
echo "[*] Генерация криминалистических артефактов через Python..."
python3 "${SCRIPT_DIR}/generate_compromised_data.py"

echo "[✔] Лабораторный стенд готов! Подготовленные артефакты:"
ls -lh "${SCRIPT_DIR}/auth_compromised.log" \
       "${SCRIPT_DIR}/audit_tampered.log" \
       "${SCRIPT_DIR}/wtmp_evidence.txt" \
       "${SCRIPT_DIR}/audit_rules.rules"

echo ""
echo "Все материалы готовы к проведению расследования по LABS.md."
