# Решения и эталонные ответы: Лабораторная работа 11

---

## Задание 1: Аудит привилегий контейнера

### 1. Вывод команды `capsh --print`
При анализе вывода:
```text
Current: = cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,cap_setgid,cap_setuid...
```
Если в списке обнаружены:
- `cap_sys_admin`: Критический риск. Контейнер может вызывать `mount()`, загружать BPF-программы, манипулировать пространствами имен cgroups и совершить побег на хост.
- `cap_sys_ptrace`: Позволяет контейнеру читать и модифицировать память процессов, работающих в том же PID namespace.

### 2. Защищенный запуск контейнера в Docker:
```bash
# Сброс всех capabilities и добавление только необходимых минимумов:
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE --read-only --security-opt=no-new-privileges:true my-app
```

---

## Задание 2: Обнаружение скрытых процессов

### 1. Принцип работы `hidden_proc_detector.py`
1. Ядро Linux обрабатывает системный вызов `kill(pid, 0)` в функции `kill_something_info()`. Оно проверяет наличие дескриптора задачи `task_struct` в глобальной хэш-таблице процессов `pid_hash`.
2. Если LKM-руткит модифицирует функцию чтения каталога `/proc` (или исключает `task_struct` из двусвязного списка итератора `for_each_process`), вызов `readdir()` для `/proc` не вернет этот PID.
3. Однако при прямом обращении `kill(pid, 0)` ядро находит процесс в хэш-таблице планировщика и возвращает 0 (успех) либо `EPERM` (ошибка доступа). Рассогласование однозначно указывает на сокрытие процесса.

---

## Задание 3: Эталонный файл харденинга ядра (`/etc/sysctl.d/99-security-hardening.conf`)

```ini
# Скрытие указателей ядра от непривилегированных пользователей
kernel.kptr_restrict = 2

# Ограничение доступа к dmesg
kernel.dmesg_restrict = 1

# Отключение непривилегированного eBPF
kernel.unprivileged_bpf_disabled = 2

# Ограничение ptrace (только процессы-потомки или запрет)
kernel.yama.ptrace_scope = 2

# Защита от TCP SYN-Flood
net.ipv4.tcp_syncookies = 1

# Отключение IP Forwarding (если хост не роутер)
net.ipv4.ip_forward = 0

# Игнорирование ICMP Broadcast запросов (защита от Smurf-атак)
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Защита от подмены IP-адресов (Reverse Path Filtering)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
```

Применение:
```bash
sudo sysctl -p /etc/sysctl.d/99-security-hardening.conf
```

---

## Задание 4: Трассировка сетевых вызовов в `strace`

Команда для прикрепления к подозрительному демону и отслеживания всех открываемых сокетов и сетевых адресов:
```bash
sudo strace -f -e trace=socket,connect,bind,accept,sendto,recvfrom -s 1024 -p <PID>
```
- `-f`: отслеживать все дочерние потоки и процессы (fork/clone).
- `-s 1024`: выводить до 1024 байт передаваемых буферов (позволяет увидеть тела запросов и учетные данные).
