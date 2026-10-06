#!/usr/bin/env bash
#
# Уязвимый административный скрипт обработки задач
# Содержит уязвимости Command Injection и небезопасной работы с временными файлами
#

ACTION="$1"
TARGET="$2"

TEMP_FILE="/tmp/admin_job.tmp"

echo "Инициализация задачи: $ACTION для $TARGET" > "$TEMP_FILE"

# Уязвимость 1: Использование eval с внешним вводом
eval "RESULT_CODE=\$$ACTION"

# Уязвимость 2: Небезопасная конкатенация в системный вызов
cat "$TEMP_FILE"
echo "Завершено."
