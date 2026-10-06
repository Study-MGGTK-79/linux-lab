# 💡 Решения и критерии проверки: Модуль 09

В данном руководстве представлены эталонные решения, команды системного администрирования и аналитические выводы для лабораторной работы модуля 09.

Все команды предполагаются к выполнению из директории `09-security-and-selinux/`.

---

## Задание 1: Аудит привилегий и системный харденинг (CIS Benchmark & PoLP)

### 1. Анализ векторов повышения привилегий GTFOBins в `sudoers_insecure`

В файле `starter_data/vulnerable_system_config/sudoers_insecure` допущено 5 критических ошибок:

| Пользователь | Уязвимая директива | Команда эксплуатации (Instant Root Shell) |
| :--- | :--- | :--- |
| **`developer`** | `ALL=(ALL) NOPASSWD: /usr/bin/find` | `sudo find . -exec /bin/sh \; -quit`<br>*Утилита find выполняет произвольную команду с правами root через аргумент `-exec`.* |
| **`intern`** | `ALL=(ALL) NOPASSWD: /usr/bin/vim /var/log/nginx/*` | `sudo vim /var/log/nginx/access.log`<br>Внутри редактора нажать `ESC`, ввести `:!/bin/sh` и нажать `Enter`.<br>*Vim открывает полнофункциональный root shell.* |
| **`support`** | `ALL=(ALL) NOPASSWD: /usr/bin/less /var/log/*` | `sudo less /var/log/syslog`<br>Внутри пейджера набрать `!/bin/sh` и нажать `Enter`.<br>*Less поддерживает выполнение шелл-команд.* |
| **`operator`** | `ALL=(ALL) NOPASSWD: /usr/bin/awk` | `sudo awk 'BEGIN {system("/bin/sh")}'`<br>*Язык awk имеет встроенную функцию `system()` для запуска программ.* |
| **`backup_service`** | `ALL=(root) NOPASSWD: /opt/scripts/backup.sh *` | `sudo /opt/scripts/backup.sh ; /bin/bash`<br>или передача параметров внедрения аргументов (Argument Injection), если скрипт использует `eval` или небезопасные переменные. |

#### Опасность символа подстановки `*` (Wildcard) в Sudoers
Когда администратор пишет `/opt/scripts/backup.sh *`, `sudo` проверяет только то, что строка команды **начинается** с `/opt/scripts/backup.sh`. Знак `*` разрешает передачу абсолютно любых флагов и аргументов. Например, если скрипт принимает флаг `--exec` или вызывает внутри себя другую утилиту, злоумышленник внедряет произвольный шелл-код.

---

### 2. Эталонные файлы защищенных конфигураций

#### А. Защищенный `sudoers_hardened`:
```ini
Defaults    env_reset
Defaults    mail_badpass
Defaults    secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

%admin ALL=(ALL) ALL
%sudo  ALL=(ALL:ALL) ALL

# Замена интерактивных утилит на неинтерактивные с жесткими аргументами:
developer ALL=(root) /usr/bin/ls -la /var/log/app/
intern    ALL=(root) /usr/bin/tail -n 100 /var/log/nginx/access.log
support   ALL=(root) /usr/bin/grep -i * /var/log/nginx/error.log
operator  ALL=(root) /usr/local/bin/calc_metrics.sh
backup_service ALL=(root) NOPASSWD: /opt/scripts/backup.sh --daily
```

#### Б. Защищенный `sshd_config_hardened`:
```ini
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
X11Forwarding no
IgnoreRhosts yes
LoginGraceTime 60
```

#### В. Защищенный `sysctl_hardened.conf`:
```ini
net.ipv4.ip_forward = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.tcp_syncookies = 1
fs.suid_dumpable = 0
kernel.randomize_va_space = 2
```

---

### 3. Автоматическая проверка харденинга

```bash
python3 starter_data/verify_hardening.py \
  starter_data/vulnerable_system_config/sudoers_hardened \
  starter_data/vulnerable_system_config/sshd_config_hardened \
  starter_data/vulnerable_system_config/sysctl_hardened.conf
```
**Вывод:**
```text
[✔] Файл sudoers соответствует принципу наименьших привилегий (PoLP)!
[✔] Конфигурация SSHD полностью соответствует CIS Benchmark!
[✔] Параметры ядра sysctl защищены по стандарту CIS!
[🎉] ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ: Система полностью защищена!
```

---

## Задание 2: Расследование и устранение блокировок SELinux (AVC Denials)

### 1. Анализ журнала `audit_selinux_denials.log` через симулятор

Запуск симулятора:
```bash
bash starter_data/simulate_selinux_issue.sh
```

**Разбор событий:**
1. `nginx (pid 1420)` пытался прочитать `/srv/custom_app/public/index.html`. 
   Контекст источника `httpd_t`, контекст цели `default_t`. Отказ ядра: `denied { read }`.
2. `nginx (pid 1418)` пытался открыть слушающий порт 8088. 
   Контекст порта `unreserved_port_t`. Отказ ядра: `denied { name_bind }`.
3. `nginx (pid 1420)` пытался подключиться к TCP-порту 3000 (`ntop_port_t`). 
   Отказ ядра: `denied { name_connect }`.
4. `httpd (pid 1850)` пытался подключиться к TCP-порту 3306 (`mysqld_port_t`). 
   Отказ ядра: `denied { name_connect }`.

---

### 2. Инцидент 1: Ошибка 403 при чтении веб-директории
* **Текущий тип (`tcontext`)**: `default_t` (базовый тип по умолчанию для нестандартных каталогов).
* **Целевой тип**: `httpd_sys_content_t` (стандартный тип статического контента веб-сервера).

**Эталонные команды исправления:**
```bash
# 1. Добавить постоянную запись в базу данных правил SELinux:
sudo semanage fcontext -a -t httpd_sys_content_t "/srv/custom_app/public(/.*)?"

# 2. Применить правильный контекст рекурсивно ко всем существующим файлам:
sudo restorecon -Rv /srv/custom_app/public
```

#### Почему команда `chcon` неприемлема в продакшене?
Команда `chcon` изменяет только расширенные атрибуты (`xattr`) файлов в текущей файловой системе. Она **не вносит изменений в базу данных политик SELinux**.
При запуске `restorecon`, обновлении RPM-пакетов или автоматической фоновой перемаркировке диска при перезагрузке (`autorelabel`) все метки, установленные через `chcon`, **будут мгновенно сброшены обратно к `default_t`**, и веб-сайт снова упадет с ошибкой 403 Forbidden!

---

### 3. Инцидент 2: Nginx не может открыть порт 8088 (`name_bind`)
* **Текущий тип порта**: `unreserved_port_t`.
* По умолчанию веб-сервер (`httpd_t`) имеет право привязываться (`name_bind`) только к портам с типом `http_port_t` (80, 443, 8008, 8009, 8443).

**Команда исправления:**
```bash
sudo semanage port -a -t http_port_t -p tcp 8088
```
*(Если порт ранее был привязан к другой службе, используется флаг модификации `-m` вместо `-a`)*.

---

### 4. Инциденты 3 и 4: Блокировка сетевых подключений бэкенда (`name_connect`)
По умолчанию SELinux запрещает процессам веб-сервера устанавливать любые исходящие TCP-соединения (во избежание использования скомпрометированного сервера как плацдарма для атак на внутреннюю сеть компании).

Для включения штатных сетевых возможностей используются переключатели (**Booleans**):
```bash
# Разрешить веб-серверу работать в качестве Reverse Proxy (подключаться к локальным бэкендам Node.js, Python, Go):
sudo setsebool -P httpd_can_network_connect on

# Разрешить скриптам веб-сервера подключаться к СУБД (MySQL / PostgreSQL):
sudo setsebool -P httpd_can_network_connect_db on
```
*Флаг `-P` (Persistent) гарантирует сохранение настроек после перезагрузки ОС.*

---

### 5. Экспертное заключение: Почему `audit2allow -M` здесь недопустим?
Если при возникновении этих ошибок выполнить команду `audit2allow -M fix_nginx`, утилита автоматически сгенерирует модуль политики ядра, который разрешит домену `httpd_t` читать любые файлы с типом `default_t` и подключаться к любым портам.
Это **полностью разрушает изоляцию SELinux**: скомпрометированный Nginx сможет читать любые забытые файлы в корне диска с меткой `default_t` (дампы, резервные копии, временные файлы скриптов). 

Правильный путь — всегда использовать штатные типы (`semanage fcontext`), типы портов (`semanage port`) и переключатели (`setsebool -P`).

---

## Задание 3: Профилирование и управление режимами AppArmor

### 1. Анализ профиля
* В первой строке профиля задан режим `flags=(complain)`.
* В режиме **`complain`** подсистема AppArmor не блокирует запрещенные действия, а только генерирует предупреждения в системный журнал аудита.
* **Оценка защищенности**: В режиме complain приложение **НЕ ЗАЩИЩЕНО**. Если злоумышленник скомпрометирует воркер и вызовет чтение `/etc/shadow`, файл будет успешно прочитан и отправлен нарушителю, несмотря на директиву `deny /etc/shadow r,`. В логе появится запись `apparmor="DENIED"`, но системный вызов ядра завершится успешно.

### 2. Команды администрирования
```bash
# 1. Перевод профиля в принудительный строгий режим Enforce:
sudo aa-enforce /etc/apparmor.d/usr.local.bin.payment_worker

# 2. Проверка статуса всех профилей и изолированных процессов:
sudo aa-status

# 3. Интерактивная донастройка профиля по журналу отказов:
sudo aa-logprof
```

---

## Задание 4: Проактивная защита от атак подбора с помощью Fail2ban

### 1. Эталонный конфигурационный файл `/etc/fail2ban/jail.d/ssh-hardened.local`

```ini
[sshd]
enabled  = true
port     = ssh
mode     = aggressive
backend  = systemd

# Окно поиска: 10 минут
findtime = 600

# Лимит неудачных попыток: 3
maxretry = 3

# Время блокировки: 24 часа
bantime  = 86400

# Доверенные IP и подсети (защита от случайного бана администраторов):
ignoreip = 127.0.0.1/8 ::1 10.0.10.0/24

# Использование современного фаервола nftables
banaction = nftables-multiport
```

---

### 2. Тестирование фильтра утилитой `fail2ban-regex`

```bash
fail2ban-regex ../08-logging-auditing-and-monitoring/starter_data/auth.log /etc/fail2ban/filter.d/sshd.conf
```

**Анализ результатов:**
* Фильтр зафиксирует более 350 совпадений по шаблонам `Failed password`.
* Немедленной блокировке подлежат IP:
  * `192.0.2.15` (182 попытки)
  * `203.0.113.88` (168 попыток)
  * `198.51.100.42` (5 попыток — бан наступает на 3-й попытке, что предотвратило бы успешный вход на 6-й попытке!).

---

### 3. Управление через CLI `fail2ban-client`

```bash
# 1. Ручной бан вредоносного IP:
sudo fail2ban-client set sshd banip 198.51.100.42

# 2. Просмотр статистики и списка забаненных IP в джейле sshd:
sudo fail2ban-client status sshd

# 3. Ручной разбан ошибочно заблокированного IP:
sudo fail2ban-client set sshd unbanip 198.51.100.42
```
