# 🎯 Эталонные решения: Модуль 04 — Управление процессами и Systemd

Данный документ содержит пошаговые эталонные решения всех четырех практических заданий модуля 04 с разбором параметров команд, готовыми Unit-файлами и примерами терминального вывода.

---

## 🛠️ Решение Лабораторной работы 1: Анатомия процессов, управление сигналами и Nice

### Шаг 1. Запуск нагрузочных фоновых процессов
```bash
cd /Users/kodoku/Documents/College/Linux/04-processes-and-systemd/starter_data
./load_generator.sh --cpu 2
```
*Вывод терминала:*
```text
Запуск 2 фоновых вычислительных потоков CPU (SHA256 циклы)...
  [+] Поток #1 запущен с PID: 54120
  [+] Поток #2 запущен с PID: 54121
Используйте 'top' или 'htop' для наблюдения. Процессы можно приоритизировать через 'renice'.
```

---

### Шаг 2. Анализ процессов через `ps` и `top`
Вывод подробных метрик планирования для запущенных процессов:
```bash
ps -eo pid,ppid,ni,pri,pcpu,stat,comm | grep -E "sha256sum|bash" | head -5
```
*Пример вывода:*
```text
  PID  PPID  NI PRI %CPU STAT COMMAND
54120 54118   0  19 98.4 R    sha256sum
54121 54119   0  19 98.1 R    sha256sum
```
> **Обратите внимание**: Колонка `STAT` содержит `R` (Running), а `NI` равен `0` (стандартный базовый приоритет).

---

### Шаг 3. Изменение приоритета планировщика (Renice)
```bash
# 1. Понижение приоритета первого процесса до +15 (максимально "вежливый" процесс)
# Обычный пользователь может понижать приоритет без sudo!
renice -n 15 -p 54120

# 2. Повышение приоритета второго процесса до -10 (требует прав root!)
sudo renice -n -10 -p 54121
```
*Вывод команд:*
```text
54120 (process ID) old priority 0, new priority 15
54121 (process ID) old priority 0, new priority -10
```

Повторная проверка через `ps`:
```bash
ps -o pid,ni,pri,pcpu,comm -p 54120,54121
```
*Результат:* процесс `54121` с `NI = -10` получает преимущественную долю тактов процессора по сравнению с процессом `54120`.

---

### Шаг 4. Инспекция виртуальной файловой системы ядра `/proc`
```bash
# Просмотр аргументов запуска (заменяем null-байты на пробелы через tr)
cat /proc/54120/cmdline | tr '\0' ' '; echo ""

# Просмотр системных лимитов процесса (открытые файлы, память, процессы)
cat /proc/54120/limits | grep -E "Max open files|Max processes"

# Список открытых файловых дескрипторов
ls -l /proc/54120/fd/
```
*Ожидаемый вывод `fd`:*
```text
total 0
lr-x------ 1 student student 64 Oct  5 10:00 0 -> 'pipe:[192837]'
l-wx------ 1 student student 64 Oct  5 10:00 1 -> /dev/null
l-wx------ 1 student student 64 Oct  5 10:00 2 -> /dev/pts/1
```

---

### Шаг 5. Остановка процессов (SIGTERM -> SIGKILL)
```bash
# Отправка штатного сигнала завершения SIGTERM (15)
kill -15 54120 54121

# Проверка, завершились ли процессы:
sleep 1
if kill -0 54120 2>/dev/null; then
    echo "Процесс 54120 не завершился по SIGTERM. Принудительно уничтожаем (SIGKILL)..."
    kill -9 54120
fi

# Окончательная очистка через генератор нагрузки
./load_generator.sh --stop
```

---

## 🛠️ Решение Лабораторной работы 2: Разработка и харденинг службы Systemd

### Шаг 1. Подготовка бинарников приложения
```bash
sudo mkdir -p /opt/mock_daemon
sudo cp /Users/kodoku/Documents/College/Linux/04-processes-and-systemd/starter_data/mock_daemon.py /opt/mock_daemon/mock_daemon.py
sudo chmod 755 /opt/mock_daemon/mock_daemon.py
sudo chown -R student:student /opt/mock_daemon
```

---

### Шаг 2. Создание эталонного Unit-файла `/etc/systemd/system/mock_daemon.service`
Создадим production-grade файл юнита со всеми исправлениями и директивами харденинга:

```bash
sudo tee /etc/systemd/system/mock_daemon.service << 'EOF'
[Unit]
Description=Enterprise Mock Application Service (Production Hardened)
After=network.target network-online.target
Wants=network-online.target
Documentation=https://enterprise.internal/docs/mock_daemon

[Service]
Type=simple
User=student
Group=student
WorkingDirectory=/opt/mock_daemon

# ИСПРАВЛЕНИЕ 1: Абсолютные пути к исполняемому файлу и интерпретатору
ExecStart=/usr/bin/python3 /opt/mock_daemon/mock_daemon.py --port 8088

# Перечитывание конфигурации по сигналу SIGHUP без остановки сервиса
ExecReload=/bin/kill -HUP $MAINPID

# ИСПРАВЛЕНИЕ 4: Безопасная политика перезапуска с защитой от CrashLoop
Restart=on-failure
RestartSec=3s
StartLimitIntervalSec=60s
StartLimitBurst=3

# --- ПЕСОЧНИЦА И БЕЗОПАСНОСТЬ (Hardening) ---
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
RuntimeDirectory=mock_daemon
RuntimeDirectoryMode=0750

# --- ОГРАНИЧЕНИЯ РЕСУРСОВ (cgroups v2) ---
CPUQuota=50%
MemoryMax=256M
TasksMax=50

[Install]
# ИСПРАВЛЕНИЕ 5: Корректное имя стандартного таргета
WantedBy=multi-user.target
EOF
```

---

### Шаг 3. Регистрация, запуск и проверка сервиса
```bash
# 1. Обязательная перезагрузка конфигурации Systemd
sudo systemctl daemon-reload

# 2. Включение службы в автозагрузку и немедленный запуск
sudo systemctl enable --now mock_daemon.service

# 3. Проверка статуса
systemctl status mock_daemon.service
```

*Ожидаемый статус:*
```text
● mock_daemon.service - Enterprise Mock Application Service (Production Hardened)
     Loaded: loaded (/etc/systemd/system/mock_daemon.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-10-05 10:05:00 UTC; 4s ago
   Main PID: 61200 (python3)
      Tasks: 2 (limit: 50)
     Memory: 18.4M (peak: 18.9M, max: 256.0M)
        CPU: 120ms
     CGroup: /system.slice/mock_daemon.service
             └─61200 /usr/bin/python3 /opt/mock_daemon/mock_daemon.py --port 8088
```

Проверка доступности HTTP healthcheck:
```bash
curl -s http://localhost:8088/status
```
*Вывод:*
```json
{"status": "UP", "pid": 61200, "config_version": 1, "requests": 1}
```

---

## 🛠️ Решение Лабораторной работы 3: Systemd Timers — Замена Crontab

### Шаг 1. Размещение скрипта бэкапа
```bash
sudo cp /Users/kodoku/Documents/College/Linux/04-processes-and-systemd/starter_data/backup_task.sh /usr/local/bin/backup_task.sh
sudo chmod 755 /usr/local/bin/backup_task.sh
```

---

### Шаг 2. Создание однократного сервиса `/etc/systemd/system/app_backup.service`
```bash
sudo tee /etc/systemd/system/app_backup.service << 'EOF'
[Unit]
Description=Application Backup Task Execution
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/backup_task.sh
StandardOutput=journal
StandardError=journal
EOF
```

---

### Шаг 3. Создание таймера `/etc/systemd/system/app_backup.timer`
```bash
sudo tee /etc/systemd/system/app_backup.timer << 'EOF'
[Unit]
Description=Scheduled Periodic Application Backup Timer
Requires=app_backup.service

[Timer]
# Запуск каждые 10 минут
OnCalendar=*:0/10
# Гарантия запуска после восстановления сервера, если запуск был пропущен
Persistent=true
# Случайная девиация до 30 секунд для предотвращения Thundering Herd
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
EOF
```

---

### Шаг 4. Активация таймера и проверка расписания
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now app_backup.timer

# Проверка статуса таймеров в системе:
systemctl list-timers app_backup.timer
```
*Ожидаемый вывод `list-timers`:*
```text
NEXT                        LEFT        LAST                        PASSED     UNIT             ACTIVATES
Sun 2026-10-05 10:20:00 UTC 8min left   n/a                         n/a        app_backup.timer app_backup.service
```

Ручной прогон и проверка созданного архива:
```bash
sudo systemctl start app_backup.service

# Просмотр логов выполнения:
journalctl -u app_backup.service -n 10 --no-pager

# Проверка созданного архива:
ls -lh /var/tmp/lab_backups/
```

---

## 🛠️ Решение Лабораторной работы 4: Траблшутинг инцидента через `journalctl`

### Шаг 1. Симуляция падения службы
```bash
cd /Users/kodoku/Documents/College/Linux/04-processes-and-systemd/starter_data
sudo bash ./load_generator.sh --crash
```
Через 3 секунды демон перехватит файл флага и аварийно завершится.

Проверяем статус:
```bash
systemctl status mock_daemon.service
```
*Вывод покажет переход в статус сбоя:*
```text
● mock_daemon.service - Enterprise Mock Application Service (Production Hardened)
   Loaded: loaded (/etc/systemd/system/mock_daemon.service; enabled; ...)
   Active: failed (Result: exit-code) since Sun 2026-10-05 10:12:00 UTC; 2s ago
```

---

### Шаг 2. Расследование Root Cause через `journalctl`
```bash
# Просмотр только ошибок критического уровня за последние 10 минут:
journalctl -u mock_daemon.service -p err..emerg --since "10 minutes ago" --no-pager
```
*Пример вывода расследования:*
```text
Oct 05 10:12:01 srv01 python3[61200]: [2026-10-05 10:12:01] [CRITICAL] [PID:61200] Обнаружен триггерный файл /tmp/mock_daemon_crash.flag! Аварийное падение приложения!
Oct 05 10:12:01 srv01 python3[61200]: [2026-10-05 10:12:01] [CRITICAL] [PID:61200] Необработанное исключение: Fatal Hardware/OS signal exception: SIGBUS simulation
Oct 05 10:12:01 srv01 systemd[1]: mock_daemon.service: Main process exited, code=exited, status=1/FAILURE
```

> **Диагноз инцидента**: Приложение аварийно завершилось из-за наличия триггерного флага аварии `/tmp/mock_daemon_crash.flag`. Флаг уже удален приложением.

---

### Шаг 3. Снятие блокировки и восстановление сервиса
Если служба падала несколько раз подряд и перешла в статус `start-limit-hit`:
```bash
# 1. Сброс счетчика аварий Systemd
sudo systemctl reset-failed mock_daemon.service

# 2. Перезапуск службы
sudo systemctl restart mock_daemon.service

# 3. Подтверждение статуса active (running)
systemctl is-active mock_daemon.service
# Должно вернуть: active
```

---

### Шаг 4. Тестирование `ExecReload` (сигнал SIGHUP)
Проверим перечитывание конфигурации без даунтайма:
```bash
# Фиксируем PID до релоада
OLD_PID=$(pgrep -f "python3.*mock_daemon.py")
echo "Текущий PID: $OLD_PID"

# Отправляем команду reload через systemctl
sudo systemctl reload mock_daemon.service

# Проверяем PID после релоада
NEW_PID=$(pgrep -f "python3.*mock_daemon.py")
echo "Новый PID: $NEW_PID"

# PID должен остаться в точности тем же (процесс НЕ перезапускался)!
test "$OLD_PID" -eq "$NEW_PID" && echo "✓ PID не изменился: бесшовная перезагрузка подтверждена!"
```

Проверка записи в журнале:
```bash
journalctl -u mock_daemon.service -n 3 --no-pager
```
*Вывод покажет:*
```text
[WARNING] [PID:61200] Получен сигнал SIGHUP (1). Перечитывание конфигурационных файлов... Успешно! (Конфиг ревизии 2)
```
