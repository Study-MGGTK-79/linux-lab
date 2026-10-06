# Решения и эталонные ответы: Лабораторная работа 05

---

## Задание 1: Инспекция системных пакетов

### 1. Поиск владельца файла
- **Debian / Ubuntu**:
  ```bash
  dpkg -S $(which curl)
  # или: dpkg -S /usr/bin/curl
  # Вывод: curl: /usr/bin/curl
  ```
- **RHEL / Rocky Linux**:
  ```bash
  rpm -qf $(which curl)
  # Вывод: curl-7.76.1-26.el9.x86_64
  ```

### 2. Список файлов пакета
- **Debian / Ubuntu**:
  ```bash
  dpkg -L nginx
  ```
- **RHEL / Rocky Linux**:
  ```bash
  rpm -ql nginx
  ```

### 3. Проверка целостности
- **Debian / Ubuntu**:
  ```bash
  dpkg -V coreutils
  ```
  Если контрольные суммы, размеры и права совпадают, команда ничего не выводит (тихий успех).
- **RHEL / Rocky Linux**:
  ```bash
  rpm -V coreutils
  ```

---

## Задание 2: Сборка `sysstat_mini` из исходного кода

```bash
cd starter_data/sample_c_project

# 1. Компиляция
make clean
make

# 2. Установка с кастомным префиксом
sudo make install PREFIX=/opt/sysstat_mini

# 3. Проверка запуска
/opt/sysstat_mini/bin/sysstat_mini
```
Примерный вывод:
```text
==================================================
   SysStat Mini - Enterprise Node Monitor v1.2
==================================================
 Время непрерывной работы (Uptime): 5 ч. 22 мин.
 Всего оперативной памяти (Total RAM): 3918 MB
 Свободно оперативной памяти (Free RAM): 2450 MB
 Количество активных процессов: 142
 Средняя нагрузка (Load Avg 1m): 0.15
```

### 4. Создание глобального симлинка
```bash
sudo ln -sf /opt/sysstat_mini/bin/sysstat_mini /usr/local/bin/sysstat_mini

# Проверка вызова без указания пути:
sysstat_mini
```
*Каталог `/usr/local/bin` входит в стандартный `$PATH` всех пользователей, поэтому утилита теперь доступна глобально.*

---

## Задание 3: Исследование разделяемых библиотек (`ldd`)

```bash
ldd /opt/sysstat_mini/bin/sysstat_mini
```
Пример вывода:
```text
linux-vdso.so.1 (0x00007ffca7fe9000)
libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007fd64b000000)
/lib64/ld-linux-x86-64.so.2 (0x00007fd64b2bf000)
```
**Разбор:**
1. `libc.so.6` — стандартная библиотека языка C (GNU C Library — `glibc`). Содержит базовые функции (`printf`, `sysinfo`, `malloc` и системные вызовы).
2. `ld-linux-x86-64.so.2` — динамический загрузчик (Dynamic Linker). Он запускается ядром первым при старте ELF-программы, загружает все `.so` библиотеки в память процесса и связывает адреса функций.
3. При сборке со статическим линкованием (`gcc -static ...`) все функции из `glibc` упаковываются прямо внутрь исполняемого файла. Размер бинарника вырастает с ~16 КБ до ~850 КБ, но программа становится абсолютно независимой от установленных в системе версий `libc`.

---

## Задание 4: Траблшутинг конфигураций репозиториев

### 1. Ошибки в `broken_apt.list`
- `jammy-supernonexistent`: Такого релиза Ubuntu не существует. При выполнении `apt update` сервер вернет `404 Not Found`, и обновление кэша завершится ошибкой.
- **Исправление**:
  ```text
  deb http://archive.ubuntu.com/ubuntu/ noble main restricted universe
  deb http://archive.ubuntu.com/ubuntu/ noble-updates main restricted universe
  deb http://security.ubuntu.com/ubuntu/ noble-security main restricted universe
  ```

### 2. Ошибки в `broken_dnf.repo`
- **Проблема 1 (URL)**: Домен `repo.invalid-internal-domain.local` недоступен в DNS, dnf выдаст ошибку разрешения имени (`Could not resolve host`).
- **Проблема 2 (GPG)**: Включена проверка подписей `gpgcheck=1`, но строка `gpgkey=` закомментирована/пуста. При установке пакета DNF откажется его устанавливать с ошибкой `Public key for <pkg> is not installed`, так как у системы нет публичного ключа для проверки подписи автора.
- **Исправление**: Указать валидный URL репозитория и валидный путь к открытому ключу:
  ```ini
  [custom-internal-tools]
  name=Internal Enterprise Tools
  baseurl=https://packages.example.com/rpm/x86_64/
  enabled=1
  gpgcheck=1
  gpgkey=https://packages.example.com/RPM-GPG-KEY-corp
  ```


---

## Задание 5: Исследование вектора `LD_PRELOAD` и аудит бинарников

### 1. Компиляция и тестирование хука
```bash
gcc -shared -fPIC -o /tmp/hook.so starter_data/preload_hook.c -ldl
LD_PRELOAD=/tmp/hook.so /opt/sysstat_mini/bin/sysstat_mini
```
Вывод покажет перехват:
```text
[⚠️ AUDIT LD_PRELOAD]: Функция puts() перехвачена инжектированной библиотекой!
==================================================
   SysStat Mini - Enterprise Node Monitor v1.2
==================================================
...
```

### 2. Защита SUID-бинарников: `AT_SECURE`
Когда ядро исполняет программу с установленным битом SUID или SGID, ядро устанавливает бит `AT_SECURE` во вспомогательном векторе ELF (Auxiliary Vector, `getauxval(AT_SECURE)`).

При обнаружении `AT_SECURE != 0` динамический линкер glibc (`ld-linux.so`) **принудительно игнорирует** переменные окружения `LD_PRELOAD`, `LD_LIBRARY_PATH` и связанные директивы, загружая библиотеки только из доверенных системных путей (`/lib`, `/usr/lib`). Если бы этого механизма не существовало, любой пользователь мог бы мгновенно получить root, запустив `LD_PRELOAD=/tmp/evil.so /usr/bin/passwd`.

### 3. Проверка бинарных механизмов защиты:
```bash
# Проверка наличия стековой канарейки (Stack Canary) через символы ELF:
readelf -s /opt/sysstat_mini/bin/sysstat_mini | grep stack_chk

# Проверка флага неисполняемого стека (NX):
readelf -l /opt/sysstat_mini/bin/sysstat_mini | grep GNU_STACK
# Вывод: GNU_STACK ... RW (нет флага E - Execute -> Стек неисполняемый, NX активен!)
```
