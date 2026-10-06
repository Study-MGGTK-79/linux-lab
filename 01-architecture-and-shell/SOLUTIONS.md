# Решения и эталонные ответы: Лабораторная работа 01

Все команды предполагаются к выполнению из директории модуля `01-architecture-and-shell/`.

---

## Задание 1: Расследование инцидента безопасности (`server_access.log`)

### 1. Топ-3 атакующих IP-адресов
```bash
awk '{print $1}' starter_data/server_access.log | sort | uniq -c | sort -rn | head -n 3
```
**Разбор команды:**
- `awk '{print $1}'`: извлекает первое поле (IP-адрес клиента).
- `sort`: лексикографически упорядочивает адреса, группируя одинаковые вместе (обязательно перед `uniq`).
- `uniq -c`: подсчитывает количество подряд идущих одинаковых строк.
- `sort -rn`: выполняет обратную числовую (`-n` numeric, `-r` reverse) сортировку по количеству запросов.
- `head -n 3`: выводит первые 3 строки.

### 2. Уникальные целевые URL атак
```bash
awk '{print $7}' starter_data/server_access.log | grep -E '\.(php|env|git)' | sort -u
```
**Разбор команды:**
- В стандартном формате логов Nginx 7-я колонка — это запрашиваемый URI (`/wp-login.php` и т.д.).
- `grep -E '\.(php|env|git)'`: фильтрует строки по расширенному регулярному выражению с альтернативами.
- `sort -u`: сортирует и оставляет только уникальные значения (эквивалентно `sort | uniq`).

### 3. Подсчет количества 500 и 502 ошибок
```bash
awk '$9 == "500" || $9 == "502" { count++ } END { print "Total 50x errors:", count }' starter_data/server_access.log
```
*Альтернатива через grep:*
```bash
grep -E ' HTTP/[0-9.]+" (500|502) ' starter_data/server_access.log | wc -l
```

### 4. Выделение нестандартных User-Agent
```bash
awk -F'"' '{print $6}' starter_data/server_access.log | grep -v -E '(Mozilla|Chrome|Firefox)' | sort -u
```
**Разбор:**
- Параметр `-F'"'` делает двойную кавычку разделителем полей. Шестое поле в формате лога — это значение заголовка `User-Agent`.
- `grep -v -E`: инвертирует поиск (`-v`), отбрасывая браузеры.

---

## Задание 2: Обработка структурированных данных (`employees.csv`)

### 1. Фильтрация DevOps и Security с окладом > 300 000
```bash
awk -F',' '($3 == "DevOps" || $3 == "Security") && $4 > 300000 { print $2, "(" $3 "):", $4, "руб. ->", $6 }' starter_data/employees.csv
```

### 2. Расчет средней зарплаты отдела Engineering
```bash
awk -F',' '$3 == "Engineering" { sum += $4; count++ } END { if (count > 0) print "Avg Engineering Salary:", sum / count; else print "No records" }' starter_data/employees.csv
```

### 3. Извлечение имени пользователя из email
```bash
awk -F',' 'NR > 1 { print $6 }' starter_data/employees.csv | cut -d'@' -f1
```
*Или замена формата через sed:*
```bash
tail -n +2 starter_data/employees.csv | awk -F',' '{print $6}' | sed 's/\([a-z]\)\.\([a-z]*\)@.*/\2_\1/'
```

---

## Задание 3: Продвинутая навигация и очистка в `messy_filesystem/`

### 1. Поиск файлов `.sql` с пробелами в пути
```bash
find starter_data/messy_filesystem -type f -name "*.sql"
```

### 2. Поиск файлов больше 1 МБ с размером
```bash
find starter_data/messy_filesystem -type f -size +1M -exec ls -lh {} +
```
*Вывод покажет размер (например `2.0M`) и полный путь.*

### 3. Поиск скрытого файла и чтение секрета
```bash
find starter_data/messy_filesystem -type f -name ".*" -exec cat {} +
```
Или точечно:
```bash
cat starter_data/messy_filesystem/.hidden_config
```

### 4. Безопасное удаление файлов с расширением `.tmp`
```bash
find starter_data/messy_filesystem -type f -name "*.tmp" -print0 | xargs -0 rm -v
```
**Почему `-print0` и `-0` критически важны:**
По умолчанию `xargs` разделяет аргументы пробелами и переводами строк. Если имя файла содержит пробел (например, `my log.tmp`), без `-print0` команда попытается удалить два отдельных файла: `my` и `log.tmp`. Символ `\0` (null-байт) гарантированно не может встречаться в имени файла в Linux, что делает операцию 100% безопасной.

---

## Задание 4: Перенаправление потоков и логирование

### 1. Разделение stdout и stderr
```bash
ls /root /etc/passwd > found.txt 2> denied.log
```
Проверка содержимого:
```bash
cat found.txt    # Покажет /etc/passwd
cat denied.log   # Покажет Permission denied для /root (если не из-под root)
```

### 2. Конвейер с `tee`
```bash
(echo "=== Audit $(date) ===" && ss -tuln 2>/dev/null || netstat -tuln) | tee -a audit.log
```
- Запись отправляется в терминал и параллельно в конец файла `audit.log`.
