# 🎯 Эталонные решения: Модуль 03 — Дисковая подсистема, файловые системы и LVM

Данный документ содержит пошаговые инструкции, объяснение параметров команд и примеры терминального вывода для успешной сдачи всех лабораторных заданий модуля.

---

## 🛠️ Решение Лабораторной работы 1: Разметка диска GPT, ext4/XFS и Swap

### Шаг 1. Инициализация стенда и чтение переменных окружения
```bash
cd /Users/kodoku/Documents/College/Linux/03-storage-and-lvm/starter_data
sudo bash ./setup_disks.sh
source /var/tmp/linux_lab_storage/loop_devices.env

# Проверка назначенных имен устройств:
echo "Диск 1: $LOOP_DISK1"
echo "Диск 2: $LOOP_DISK2"
echo "Диск 3: $LOOP_DISK3"
```

### Шаг 2. Создание таблицы разделов GPT и разметка диска
Для автоматизации и надежности воспользуемся утилитой `parted` (или интерактивным `fdisk`):

```bash
# 1. Создание метки таблицы разделов GPT
sudo parted -s "$LOOP_DISK1" mklabel gpt

# 2. Создание Раздела 1 (400 MiB для WAL-логов)
# Начинаем с 1MiB для правильного выравнивания (Alignment)
sudo parted -s "$LOOP_DISK1" mkpart primary ext4 1MiB 401MiB

# 3. Создание Раздела 2 (400 MiB для XFS аналитики)
sudo parted -s "$LOOP_DISK1" mkpart primary xfs 401MiB 801MiB

# 4. Создание Раздела 3 (оставшееся пространство под Swap)
sudo parted -s "$LOOP_DISK1" mkpart primary linux-swap 801MiB 100%

# 5. Обновление таблицы разделов в ядре
sudo partprobe "$LOOP_DISK1"
```

> **Пояснение**: Для loop-устройств ядро создает подразделы с суффиксом `p` (например, `${LOOP_DISK1}p1`, `${LOOP_DISK1}p2`, `${LOOP_DISK1}p3`). Если разделы не появились в `/dev/`, выполните:
> ```bash
> sudo kpartx -av "$LOOP_DISK1" || sudo partx -u "$LOOP_DISK1"
> ```

Проверка разметки:
```bash
sudo lsblk -o NAME,SIZE,TYPE,PARTTYPE "$LOOP_DISK1"
```
*Ожидаемый вывод:*
```text
NAME      SIZE TYPE PARTTYPE
loop0       1G loop 
├─loop0p1 400M part 0fc63daf-8483-4772-8e79-3d69d8477de4
├─loop0p2 400M part 0fc63daf-8483-4772-8e79-3d69d8477de4
└─loop0p3 223M part 0657fd6d-a4ab-43c4-84e5-0933c84b4f4f
```

---

### Шаг 3. Форматирование файловых систем и тюнинг
```bash
# 1. Форматирование p1 в ext4 с меткой WAL_LOGS
sudo mkfs.ext4 -L "WAL_LOGS" "${LOOP_DISK1}p1"

# 2. Тюнинг ext4: снятие 5% резерва root блоков (освобождает место под данные)
sudo tune2fs -m 0 "${LOOP_DISK1}p1"

# 3. Форматирование p2 в XFS с меткой ANALYTICS
sudo mkfs.xfs -f -L "ANALYTICS" "${LOOP_DISK1}p2"

# 4. Форматирование p3 под область подкачки
sudo mkswap -L "SWAP_DEV" "${LOOP_DISK1}p3"
```

*Проверка параметров ext4 через tune2fs:*
```bash
sudo tune2fs -l "${LOOP_DISK1}p1" | grep "Reserved block count"
# Должно вернуть: Reserved block count: 0
```

---

### Шаг 4. Монтирование и активация Swap
```bash
# Создание точек монтирования
sudo mkdir -p /mnt/wal_logs /mnt/analytics

# Монтирование Раздела 1 с опциями noatime, nodev
sudo mount -o noatime,nodev "${LOOP_DISK1}p1" /mnt/wal_logs

# Монтирование Раздела 2 с опцией nosuid
sudo mount -o nosuid "${LOOP_DISK1}p2" /mnt/analytics

# Активация swap
sudo swapon "${LOOP_DISK1}p3"

# Проверка активного Swap
swapon --show
```
*Ожидаемый вывод `swapon --show`:*
```text
NAME      TYPE      SIZE USED PRIO
/dev/loop0p3 partition 223M   0B   -2
```

---

### Шаг 5. Конфигурирование `/etc/fstab`
Получаем UUID всех разделов:
```bash
sudo blkid "${LOOP_DISK1}p"*
```
*Пример вывода:*
```text
/dev/loop0p1: LABEL="WAL_LOGS" UUID="a1b2c3d4-e5f6-7890-abcd-ef0123456789" BLOCK_SIZE="4096" TYPE="ext4" ...
/dev/loop0p2: LABEL="ANALYTICS" UUID="b2c3d4e5-f6a7-8901-bcde-f01234567890" BLOCK_SIZE="4096" TYPE="xfs" ...
/dev/loop0p3: LABEL="SWAP_DEV" UUID="c3d4e5f6-a7b8-9012-cdef-012345678901" TYPE="swap" ...
```

Эталонные строки для добавления в `/etc/fstab` (замените UUID на фактические значения из `blkid`):
```text
UUID=a1b2c3d4-e5f6-7890-abcd-ef0123456789  /mnt/wal_logs   ext4    noatime,nodev,nofail  0 2
UUID=b2c3d4e5-f6a7-8901-bcde-f01234567890  /mnt/analytics  xfs     nosuid,nofail         0 0
UUID=c3d4e5f6-a7b8-9012-cdef-012345678901  none            swap    sw,nofail             0 0
```

Проверка валидности записей без перезагрузки:
```bash
sudo mount -a
echo $?  # Должен вернуть 0
```

---

## 🛠️ Решение Лабораторной работы 2: LVM, Онлайн-масштабирование и Snapshots

### Шаг 1. Создание Physical Volumes и Volume Group
```bash
# 1. Маркировка дисков как LVM Physical Volumes
sudo pvcreate "$LOOP_DISK2" "$LOOP_DISK3"

# 2. Создание Volume Group vg_db
sudo vgcreate vg_db "$LOOP_DISK2" "$LOOP_DISK3"

# 3. Проверка созданной группы
sudo vgs vg_db
```
*Ожидаемый вывод `vgs`:*
```text
  VG    #PV #LV #SN Attr   VSize VFree
  vg_db   2   0   0 wz--n- 2.99g 2.99g
```

---

### Шаг 2. Создание Logical Volume и перенос данных
```bash
# 1. Создание логического тома lv_mockdb на 1.5 GiB
sudo lvcreate -L 1.5G -n lv_mockdb vg_db

# 2. Создание файловой системы ext4
sudo mkfs.ext4 -L "MOCK_DATABASE" /dev/vg_db/lv_mockdb

# 3. Монтирование тома
sudo mkdir -p /mnt/mock_db
sudo mount /dev/vg_db/lv_mockdb /mnt/mock_db

# 4. Копирование mock-данных базы данных
sudo cp -r /var/tmp/mock_db_source/* /mnt/mock_db/
ls -lh /mnt/mock_db
```

---

### Шаг 3. Горячее онлайн-расширение логического тома (Hot Online Resize)
Представим, что диск базы данных заполняется. Расширим том на **+1 GiB** прямо во время работы:

```bash
# Флаг -r (--resizefs) автоматически увеличивает ext4 или xfs ФС после расширения тома
sudo lvextend -r -L +1G /dev/vg_db/lv_mockdb
```
*Ожидаемый вывод:*
```text
  Size of logical volume vg_db/lv_mockdb changed from 1.50 GiB (384 extents) to 2.50 GiB (640 extents).
  Logical volume vg_db/lv_mockdb successfully resized.
resize2fs 1.47.0 (5-Feb-2023)
Filesystem at /dev/mapper/vg_db-lv_mockdb is mounted on /mnt/mock_db; on-line resizing required
old_desc_blocks = 1, new_desc_blocks = 1
The filesystem on /dev/mapper/vg_db-lv_mockdb is now 655360 (4k) blocks long.
```

Проверка через `df -h`:
```bash
df -h /mnt/mock_db
# Должно отображать около 2.5G объема!
```

---

### Шаг 4. Создание LVM-снимка (Snapshot) и откат после сбоя
```bash
# 1. Создание снимка размером 400 MiB
sudo lvcreate -L 400M -s -n lv_mockdb_snap /dev/vg_db/lv_mockdb

# Проверка наличия снимка
sudo lvs vg_db
```
*Вывод `lvs`:*
```text
  LV             VG    Attr       LSize   Pool Origin    Data%  Meta%  Move Log Cpy%Sync Convert
  lv_mockdb      vg_db owi-aos---   2.50g                                                        
  lv_mockdb_snap vg_db swi-a-s--- 400.00m      lv_mockdb 0.05                                    
```

**2. Симуляция аварии (разрушение данных):**
```bash
# Повреждаем дамп БД и удаляем конфиг:
echo "CORRUPTED DATA BY JUNIOR DEV" | sudo tee /mnt/mock_db/database_dump.sql
sudo rm -f /mnt/mock_db/mockdb.conf

cat /mnt/mock_db/database_dump.sql
```

**3. Процедура отката к снимку (Rollback / Merge):**
```bash
# Отмонтируем рабочий каталог
sudo umount /mnt/mock_db

# Запуск слияния тома со снимком
sudo lvconvert --merge /dev/vg_db/lv_mockdb_snap
```
*Ожидаемый вывод:*
```text
  Merging of volume vg_db/lv_mockdb_snap started.
  vg_db/lv_mockdb: Merged: 100.00%
```

**4. Проверка восстановленных данных:**
```bash
sudo mount /dev/vg_db/lv_mockdb /mnt/mock_db

# Проверяем, что конфиг на месте и дамп БД восстановился
ls -l /mnt/mock_db/mockdb.conf
head -n 5 /mnt/mock_db/database_dump.sql
```
*Дамп содержит исходную схему `CREATE TABLE users...`! Данные спасены.*

---

## 🛠️ Решение Лабораторной работы 3: Аварийное восстановление (Disaster Recovery)

### Часть А: Исправление `fstab.broken`
При аудите файла `/tmp/fstab.audit` найдены следующие ошибки:
1. `UUID=deadbeef-... /data/analytics ext4 defaults 0 2` — несуществующий UUID без `nofail` приведет к остановке загрузки в `emergency.target`.  
   *Исправление*: добавить опцию `nofail` либо закомментировать строку, если диск выведен из эксплуатации.
2. `UUID=22222222-... /var/log/audit ext44 defaults,noatime 0 2` — опечатка в имени файловой системы `ext44`.  
   *Исправление*: заменить на `ext4`.
3. `UUID=33333333-... /mnt/shared_storage xfs defaults,nodev,nosuid 0` — пропущено 6-е поле (pass). Строка невалидна синтаксически.  
   *Исправление*: добавить `0 0` в конец.
4. `UUID=44444444-... /nonexistent/backup_repo ext4 defaults 0 2` — директория точки монтирования не создана.  
   *Исправление*: создать директорию `mkdir -p /nonexistent/backup_repo` или добавить опцию `nofail`.
5. `192.168.1.100:/exports/nfs /mnt/nfs_share nfs defaults 0 0` — сетевая файловая система NFS пытается монтироваться до поднятия сети.  
   *Исправление*: добавить опции `_netdev,nofail`.

**Эталонный исправленный файл `/tmp/fstab.audit`:**
```text
# Root filesystem
UUID=11111111-2222-3333-4444-555555555555  /                         ext4            errors=remount-ro                       0       1

# EFI System Partition
UUID=AAAA-BBBB                              /boot/efi                 vfat            umask=0077                              0       2

# ИСПРАВЛЕНО 1: добавлен nofail
UUID=deadbeef-0000-0000-0000-badc0ffee000  /data/analytics           ext4            defaults,nofail                         0       2

# ИСПРАВЛЕНО 2: исправлен тип ФС ext4
UUID=22222222-3333-4444-5555-666666666666  /var/log/audit            ext4            defaults,noatime                        0       2

# ИСПРАВЛЕНО 3: добавлено недостающее 6-е поле
UUID=33333333-4444-5555-6666-777777777777  /mnt/shared_storage       xfs             defaults,nodev,nosuid                   0       0

# ИСПРАВЛЕНО 4: добавлен nofail
UUID=44444444-5555-6666-7777-888888888888  /nonexistent/backup_repo  ext4            defaults,nofail                         0       2

# ИСПРАВЛЕНО 5: добавлены опции _netdev,nofail
192.168.1.100:/exports/nfs                 /mnt/nfs_share            nfs             defaults,_netdev,nofail                 0       0
```

---

### Часть Б: Ликвидация исчерпания Inodes
**1. Создание изолированного тома с ограниченным числом инодов:**
```bash
# Создаем тестовый файл и монтируем в loop
sudo truncate -s 50M /var/tmp/inode_test.img
# Форматируем с малым количеством инодов (например 1024 инода)
sudo mkfs.ext4 -N 2000 /var/tmp/inode_test.img
sudo mkdir -p /mnt/inode_test
sudo mount -o loop /var/tmp/inode_test.img /mnt/inode_test
```

**2. Симуляция инцидента (исчерпание инодов):**
```bash
# Генерируем множество пустых файлов
sudo mkdir -p /mnt/inode_test/bad_cache
sudo bash -c 'for i in $(seq 1 3000); do touch /mnt/inode_test/bad_cache/sess_$i 2>/dev/null || break; done'

# Проверяем симптомы:
df -h /mnt/inode_test
# Вывод: свободно >90% диска!

touch /mnt/inode_test/test.txt
# Вывод: touch: cannot touch '/mnt/inode_test/test.txt': No space left on device!
```

**3. Диагностика и поиск виновника:**
```bash
# Проверяем счетчик инодов:
df -i /mnt/inode_test
# Иноды заняты на 100%!

# Однострочник поиска директории с максимальной концентрацией файлов:
sudo find /mnt/inode_test -xdev -type f | awk -F/ 'BEGIN{OFS="/"}{NF--; print $0}' | sort | uniq -c | sort -nr | head -5
```
*Вывод покажет:*
```text
   1984 /mnt/inode_test/bad_cache
```

**4. Ликвидация последствий:**
```bash
# Удаление скопившихся файлов:
sudo find /mnt/inode_test/bad_cache -type f -delete

# Проверка:
df -i /mnt/inode_test
# Иноды освобождены! Ошибки 'No space left on device' устранены.

# Очистка тестового стенда инцидента:
sudo umount /mnt/inode_test
sudo rm -rf /mnt/inode_test /var/tmp/inode_test.img
```
