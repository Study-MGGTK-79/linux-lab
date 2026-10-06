#!/usr/bin/env bash
set -e

# Скрипт развертывания окружения для Лабораторной работы 02
echo "=== Инициализация тестового окружения пользователей и каталогов ==="

TARGET_DIR="/tmp/corp_storage"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"/{projects,finance,public_drop,secure_backups}

# Создаем группы, если их нет (для локального тестирования или в контейнере)
for grp in developers security_audit finance; do
    if ! getent group "$grp" > /dev/null 2>&1; then
        echo "Создание группы $grp..."
        groupadd "$grp" 2>/dev/null || true
    fi
done

# Создаем пользователей
declare -A USERS=(
    ["dev_alice"]="developers"
    ["dev_bob"]="developers"
    ["auditor_charlie"]="security_audit"
    ["fin_diana"]="finance"
)

for usr in "${!USERS[@]}"; do
    grp="${USERS[$usr]}"
    if ! id -u "$usr" > /dev/null 2>&1; then
        echo "Создание пользователя $usr в группе $grp..."
        useradd -m -s /bin/bash -g "$grp" "$usr" 2>/dev/null || true
        echo "$usr:password123" | chpasswd 2>/dev/null || true
    fi
done

# Наполнение тестовыми файлами
cat << 'EOF' > "$TARGET_DIR/projects/main.py"
def application():
    print("Core enterprise backend running")

if __name__ == "__main__":
    application()
EOF

cat << 'EOF' > "$TARGET_DIR/finance/payroll_2026.csv"
id,name,bonus
101,dev_alice,50000
102,dev_bob,45000
EOF

cat << 'EOF' > "$TARGET_DIR/secure_backups/database.enc"
ENCRYPTED_BACKUP_BLOB_AAAAB3NzaC1yc2EAAAADAQABAAABAQC
EOF

echo "✓ Стартовое окружение успешно создано в $TARGET_DIR"
