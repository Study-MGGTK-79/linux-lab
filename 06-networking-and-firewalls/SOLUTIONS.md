# Эталонные решения и методические указания: Модуль 06

В данном документе представлены детальные пошаговые решения всех лабораторных сценариев модуля 06 с разбором системных вызовов, объяснением аргументов команд и инструкциями по валидации результатов.

---

## Решение лабораторной работы 6.1: Инвентаризация сетевой подсистемы и DNS

### Шаг 1: Инвентаризация интерфейсов и таблицы маршрутизации (`iproute2`)

1. **Просмотр интерфейсов с канальной статистикой**:
   ```bash
   ip -s link show
   ```
   *Пояснение ключей*:
   - `-s` (`--stats`): выводит счетчики принятых/переданных пакетов и байт (`RX/TX`), а также количество ошибок (`errors`), отброшенных пакетов (`dropped`) и коллизий (`collsns`).

2. **Просмотр IP-адресов в компактном виде**:
   ```bash
   ip -4 -brief addr show
   ```
   *Пояснение*: флаг `-4` фильтрует вывод только по IPv4-адресам; `-brief` выводит результат в виде удобной таблицы: имя интерфейса, статус (UP/DOWN) и CIDR-нотация адреса.

3. **Анализ таблицы маршрутизации**:
   ```bash
   ip route show
   ```
   Чтобы проверить, какой именно маршрут выберет ядро для отправки пакета к конкретному хосту:
   ```bash
   ip route get 1.1.1.1
   ```
   *Ожидаемый вывод*: `1.1.1.1 via <IP_ШЛЮЗА> dev <ИМЯ_ИНТЕРФЕЙСА> src <ВАШ_IP> uid ...`

---

### Шаг 2: Аудит сокетов с помощью утилиты `ss`

1. **Вывод всех слушающих TCP и UDP сокетов с процессами**:
   ```bash
   sudo ss -tulnp
   ```
   *Пояснение флагов*:
   - `-t`: только TCP.
   - `-u`: только UDP.
   - `-l`: только в состоянии `LISTEN` (слушающие сокеты).
   - `-n`: числовой формат (numeric) — не резолвить порт 80 в `http`, порт 22 в `ssh`. Это критично: предотвращает подвисание утилиты на DNS-запросах.
   - `-p`: отобразить PID и имя бинарного файла процесса.

2. **Поиск сокетов с зависшими пакетами в очереди**:
   ```bash
   ss -lnt
   ```
   *Анализ колонок*:
   - `Recv-Q`: количество соединений, ожидающих вызова `accept()` приложением. Если число близко или равно `Send-Q` — приложение не успевает разгребать входящий трафик (CPU bottleneck или deadlock потока).
   - `Send-Q`: максимальный размер очереди бэклога сокета (`listen(fd, backlog)`).

3. **Фильтрация активных сессий (например, к веб-сервисам)**:
   ```bash
   ss -tan '( dport = :80 or dport = :443 )'
   ```

---

### Шаг 3: Диагностика и конфигурация DNS

1. **Запрос записей через `dig`**:
   ```bash
   # Простой запрос A-записи
   dig google.com +short

   # Запрос MX (почтовых) и TXT (SPF/DKIM) записей напрямую у Cloudflare DNS
   dig @1.1.1.1 google.com MX +noall +answer
   dig @1.1.1.1 google.com TXT +noall +answer

   # Трассировка делегирования зоны от корня до авторитетных серверов
   dig google.com +trace
   ```

2. **Настройка отказоустойчивого `/etc/resolv.conf`**:
   Если в системе не запущен `systemd-resolved`, сконфигурируйте `/etc/resolv.conf`:
   ```bash
   sudo tee /etc/resolv.conf << 'EOF'
   nameserver 1.1.1.1
   nameserver 8.8.8.8
   options timeout:2 attempts:2 rotate
   EOF
   ```
   *Пояснение директив*:
   - `options timeout:2`: если сервер не отвечает в течение 2 секунд, опрос прерывается.
   - `options attempts:2`: количество попыток перед переключением на следующий DNS.
   - `options rotate`: балансировка запросов по алгоритму Round Robin между указанными серверами.

   *Если используется `systemd-resolved`*:
   ```bash
   sudo resolvectl dns eth0 1.1.1.1 8.8.8.8
   sudo resolvectl flush-caches
   resolvectl status eth0
   ```

---

## Решение лабораторной работы 6.2: Аудит и харденинг SSH-сервера

### Шаг 1: Анализ выявленных уязвимостей в `sshd_config_vulnerable`
В ходе аудита стартового конфига зафиксированы следующие критические дефекты:
1. `Port 22` — стандартный порт (мишень для ботнетов).
2. `PermitRootLogin yes` — прямой вход суперпользователя.
3. `PasswordAuthentication yes` — парольный вход уязвим к перебору.
4. `PermitEmptyPasswords yes` — вход без пароля (критический риск!).
5. `MaxAuthTries 10` — позволяет злоумышленнику совершить 10 попыток перебора за одну сессию.
6. `LoginGraceTime 300` — сессия висит открытой 5 минут, блокируя лимиты соединений.
7. `X11Forwarding yes` — риск перехвата GUI-событий и клавиатурных нажатий.
8. `Ciphers 3des-cbc...` — использование устаревших CBC-шифров, уязвимых к атакам класса Plaintext-Recovery (Sweet32).
9. `MACs hmac-md5...` — коллизионно нестойкие алгоритмы контроля целостности.
10. `HostbasedAuthentication yes` — доверие по имени хоста без надежной криптографии.
11. Отсутствие директивы `AllowUsers` / `AllowGroups`.

---

### Шаг 2: Генерация криптографических ключей Ed25519

Выполняется на стороне клиента / администратора:
```bash
# Генерация ключа с усиленной деривацией пароля (100 раундов KDF)
ssh-keygen -t ed25519 -a 100 -C "admin@enterprise-linux" -f ~/.ssh/id_ed25519

# Добавление публичного ключа в authorized_keys пользователя student
mkdir -p /home/student/.ssh
chmod 700 /home/student/.ssh
cat ~/.ssh/id_ed25519.pub >> /home/student/.ssh/authorized_keys
chmod 600 /home/student/.ssh/authorized_keys
chown -R student:student /home/student/.ssh
```

---

### Шаг 3: Формирование безопасного `/etc/ssh/sshd_config`

Создаем эталонный файл конфигурации (или заменяем файл `/etc/ssh/sshd_config.d/99-hardened.conf`):

```bash
sudo tee /etc/ssh/sshd_config << 'EOF'
# ==============================================================================
# HARDENED SSHD CONFIGURATION (CIS BENCHMARK COMPLIANT)
# ==============================================================================

# 1. Сетевые параметры
Port 2222
AddressFamily inet
ListenAddress 0.0.0.0
Protocol 2

# 2. Логирование и аудит
LogLevel VERBOSE
SyslogFacility AUTH

# 3. Аутентификация и ограничение привилегий
PermitRootLogin no
StrictModes yes
MaxAuthTries 3
MaxSessions 4
LoginGraceTime 30
PasswordAuthentication no
PermitEmptyPasswords no
PubkeyAuthentication yes
HostbasedAuthentication no
IgnoreRhosts yes

# 4. Белый список пользователей
AllowUsers student deployer

# 5. Сетевые туннели и пробросы
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no

# 6. Управление таймаутами и сессиями
ClientAliveInterval 300
ClientAliveCountMax 2

# 7. Современный криптографический стек (Quantum & Side-channel Resistant)
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com

# 8. Информационная безопасность
PrintMotd no
PrintLastLog yes
Banner none

Subsystem sftp /usr/lib/openssh/sftp-server
EOF
```

---

### Шаг 4: Тестирование синтаксиса и перезапуск сервиса

```bash
# 1. Валидация синтаксиса (НЕ перезапускать, если есть ошибки!)
sudo sshd -t
echo "Код возврата проверки: $?"  # Должно быть 0

# 2. Перезапуск демона
sudo systemctl restart ssh || sudo service ssh restart

# 3. Проверка прослушивания порта 2222
sudo ss -tlpn | grep 2222

# 4. Валидация подключения
ssh -p 2222 -i ~/.ssh/id_ed25519 student@127.0.0.1
```

---

## Решение лабораторной работы 6.3: Проектирование межсетевого экрана

### Вариант А: Реализация через `iptables`

Скрипт развертывания правил файрвола:
```bash
sudo bash -c '
# 1. Сброс предыдущих правил
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# 2. Политика по умолчанию: сброс всего входящего и пересылаемого трафика
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 3. Разрешение локального интерфейса (loopback)
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# 4. Поддержка установленных соединений (Stateful Inspection)
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -m conntrack --ctstate INVALID -j DROP

# 5. Разрешение входящего ICMP (ping) с ограничением частоты (5 пакетов в секунду)
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 5/sec --limit-burst 10 -j ACCEPT

# 6. Разрешение публичных веб-портов
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 7. Защищенный SSH (порт 2222) с защитой от брутфорса (модуль recent):
# Блокировка хоста, если он делает более 4 новых попыток подключения в минуту
iptables -A INPUT -p tcp --dport 2222 -m conntrack --ctstate NEW -m recent --set --name SSH_RECENT
iptables -A INPUT -p tcp --dport 2222 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSH_RECENT -j DROP
iptables -A INPUT -p tcp --dport 2222 -j ACCEPT

# 8. Настройка NAT: Masquerade для внутренней подсети 10.10.20.0/24
iptables -t nat -A POSTROUTING -s 10.10.20.0/24 -o eth0 -j MASQUERADE

# 9. Port Forwarding (DNAT): перенаправление с внешнего порта 8080 на внутренний сервер
iptables -t nat -A PREROUTING -p tcp -i eth-dmz --dport 8080 -j DNAT --to-destination 10.10.20.5:80
iptables -A FORWARD -p tcp -d 10.10.20.5 --dport 80 -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
'
```

### Вариант Б: Реализация через `UFW` (Ubuntu / Debian)

```bash
# 1. Сброс и базовые политики
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw default deny forward

# 2. Разрешение веб-трафика
sudo ufw allow 80/tcp comment "HTTP Web Traffic"
sudo ufw allow 443/tcp comment "HTTPS Web Traffic"

# 3. Разрешение SSH с встроенным rate-limiting
sudo ufw limit 2222/tcp comment "SSH Hardened Port with Rate Limit"

# 4. Включение фаервола
sudo ufw --force enable

# 5. Проверка статуса
sudo ufw status verbose
```

---

## Решение лабораторной работы 6.4: Расследование инцидента по сетевому дампу

Файл для анализа: `starter_data/sample_traffic.pcap`.

### Шаг 1: Первичный обзор дампа пакетов
```bash
tcpdump -nn -r starter_data/sample_traffic.pcap | wc -l
```
*Результат*: В дампе зафиксировано 19 пакетов.

---

### Шаг 2: Извлечение незашифрованных учетных данных (HTTP POST)

Выполняем поиск HTTP-запросов с выводом ASCII-содержимого пакетов:
```bash
tcpdump -nn -A -r starter_data/sample_traffic.pcap 'tcp port 80 and (tcp[tcpflags] & tcp-push != 0)'
```
*Пояснение флагов*:
- `-A`: отображать полезную нагрузку пакета в текстовом формате ASCII.
- `tcp[tcpflags] & tcp-push != 0`: фильтрует пакеты с установленным флагом PUSH (передача полезных данных приложения).

**Анализ извлеченных данных**:
- URL запроса: `POST /api/v1/auth/login HTTP/1.1`
- Host: `internal-portal.corp`
- IP клиента: `192.168.1.100` -> IP сервера: `192.168.1.10`
- Учетные данные:
  * **`username`**: `corp_admin`
  * **`password`**: `SuperSecretPassword2026!`
- Выданная сервером сессия (в следующем пакете ответа):
  * `Set-Cookie: auth_session=eyJhbGciOiJIUzI1NiJ9.s3cr3t`

---

### Шаг 3: Обнаружение TCP SYN сканирования портов

Используем BPF-фильтр для изоляции SYN-пакетов (начало установки соединения без флага ACK):
```bash
tcpdump -nn -r starter_data/sample_traffic.pcap 'tcp[tcpflags] & (tcp-syn) != 0 and tcp[tcpflags] & (tcp-ack) == 0'
```
*Вывод команды*:
```text
IP 10.0.0.66.50000 > 192.168.1.10.21: Flags [S]
IP 10.0.0.66.50001 > 192.168.1.10.22: Flags [S]
IP 10.0.0.66.50002 > 192.168.1.10.23: Flags [S]
IP 10.0.0.66.50003 > 192.168.1.10.25: Flags [S]
IP 10.0.0.66.50004 > 192.168.1.10.80: Flags [S]
IP 10.0.0.66.50005 > 192.168.1.10.443: Flags [S]
IP 10.0.0.66.50006 > 192.168.1.10.3306: Flags [S]
IP 10.0.0.66.50007 > 192.168.1.10.8080: Flags [S]
```

**Ответы на контрольные вопросы расследования**:
1. IP-адрес атакующего: **`10.0.0.66`**
2. Просканированные порты: `21 (FTP), 22 (SSH), 23 (Telnet), 25 (SMTP), 80 (HTTP), 443 (HTTPS), 3306 (MySQL), 8080 (HTTP-Alt)`.
3. Анализ ответов сервера (ищем пакеты `Flags [S.]` — SYN-ACK):
   ```bash
   tcpdump -nn -r starter_data/sample_traffic.pcap 'src host 192.168.1.10 and tcp[tcpflags] & (tcp-syn|tcp-ack) == (tcp-syn|tcp-ack)'
   ```
   *Результат*: Единственный открытый порт сервера — **`80`** (на все остальные порты сервер вернул `Flags [R.]` — TCP RST).

---

### Шаг 4: Расследование DNS-эксфильтрации данных

Выводим все UDP DNS-запросы:
```bash
tcpdump -nn -r starter_data/sample_traffic.pcap udp port 53
```
*Вывод команды*:
```text
IP 192.168.1.100.54321 > 1.1.1.1.53: 4919+ A? cGFzc3dvcmRfaGFzaF9lMmQ1YTc.exfil.c2-command.ru. (65)
```

**Криминалистический анализ поддомена**:
- Домен злоумышленника: `exfil.c2-command.ru`
- Переданная полезная нагрузка: `cGFzc3dvcmRfaGFzaF9lMmQ1YTc`
- Декодирование строки Base64:
  ```bash
  echo "cGFzc3dvcmRfaGFzaF9lMmQ1YTc=" | base64 --decode
  ```
- **Результат расшифровки**: `password_hash_e2d5a7`. Произошла утечка хэша пароля через DNS-туннель.
