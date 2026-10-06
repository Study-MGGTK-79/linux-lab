# Решения и эталонные ответы: Лабораторная работа 10

---

## Задание 1: Эксплуатация и исправление `vulnerable_script.sh`

### 1. Демонстрация Command Injection:
```bash
bash starter_data/vulnerable_script.sh "PATH; id; uname -a #" "test_target"
```
Команда `eval` выполнит внедренные команды `id` и `uname -a`.

### 2. Исправленный безопасный скрипт:
```bash
#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
TARGET="${2:-}"

if [[ -z "$ACTION" || -z "$TARGET" ]]; then
    echo "Использование: $0 <action> <target>" >&2
    exit 1
fi

# Безопасное создание изолированного каталога
WORK_DIR=$(mktemp -d /tmp/admin_job_XXXXXX)
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM

TEMP_FILE="$WORK_DIR/job.tmp"
echo "Инициализация задачи: $ACTION для $TARGET" > "$TEMP_FILE"

# Исключение eval: валидация через case/whitelist
case "$ACTION" in
    start|stop|restart|status)
        echo "Выполнение разрешенного действия: $ACTION"
        ;;
    *)
        echo "Ошибка: Недопустимое действие '$ACTION'" >&2
        exit 2
        ;;
esac

cat "$TEMP_FILE"
echo "Завершено безопасно."
```

---

## Задание 2: Эталонный сборщик форензик-артефактов (`ir_collector.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "[-] Сборщик IR должен быть запущен с правами root!" >&2
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="/tmp/ir_evidence_${TIMESTAMP}"
mkdir -p "$EVIDENCE_DIR"
chmod 0700 "$EVIDENCE_DIR"

echo "[+] Начало сбора энергозависимых данных (RFC 3227)..."

# 1. Сетевые сокеты
echo "[*] Сбор сетевых соединений..."
ss -tulnep > "$EVIDENCE_DIR/sockets.txt" 2>&1 || true

# 2. Процессы
echo "[*] Сбор дерева процессов..."
ps auxfww > "$EVIDENCE_DIR/processes.txt" 2>&1 || true

# 3. Пользователи и сессии
echo "[*] Сбор информации о сессиях..."
who > "$EVIDENCE_DIR/who.txt" 2>&1 || true
last -n 50 > "$EVIDENCE_DIR/last_logins.txt" 2>&1 || true

# 4. Сетевая конфигурация
echo "[*] Сбор сетевых интерфейсов..."
ip a > "$EVIDENCE_DIR/ip_addr.txt" 2>&1 || true
ip route > "$EVIDENCE_DIR/ip_route.txt" 2>&1 || true

# 5. Хэширование файлов для сохранения Chain of Custody
echo "[*] Вычисление контрольных сумм SHA-256..."
cd "$EVIDENCE_DIR"
sha256sum *.txt > "checksums.sha256"

# 6. Архивация
ARCHIVE="/tmp/evidence_${HOSTNAME}_${TIMESTAMP}.tar.gz"
tar -czf "$ARCHIVE" -C /tmp "ir_evidence_${TIMESTAMP}"
chmod 0600 "$ARCHIVE"
rm -rf "$EVIDENCE_DIR"

echo "[✓] Сбор доказательств завершен: $ARCHIVE"
sha256sum "$ARCHIVE"
```

---

## Задание 3: Эталонный Host Integrity Checker (`host_audit.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Аудит безопасности хоста Linux ==="

# 1. Поиск скрытых учетных записей с UID 0
echo "[*] Проверка пользователей с UID 0:"
awk -F: '($3 == 0) { print "  [!] Найден аккаунт с UID 0:", $1 }' /etc/passwd

# 2. Поиск SUID бинарников
echo "[*] Поиск файлов с битом SUID:"
find / -xdev \( -perm -4000 \) -type f -exec ls -l {} + 2>/dev/null | awk '{print $3, $9}'

# 3. Проверка прав на критические файлы
echo "[*] Проверка прав на /etc/sudoers и /etc/crontab:"
ls -l /etc/sudoers /etc/crontab 2>/dev/null || true
```
