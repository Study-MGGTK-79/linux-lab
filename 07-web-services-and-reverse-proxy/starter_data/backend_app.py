#!/usr/bin/env python3
"""
Лабораторный бэкенд-сервис для Модуля 07:
Web Infrastructure Exploitation, Nginx Misconfigurations & SSL Hardening.

Функционал:
- /api/public : общедоступный эндпоинт информации
- /api/login : симуляция формы авторизации для проверки Rate Limiting
- /admin : защищенная панель администратора, проверяющая доверенный IP (127.0.0.1)
"""

import sys
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

SERVER_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8081

class LabSecurityHandler(BaseHTTPRequestHandler):
    server_version = "FintechBackend/1.0"

    def log_message(self, format, *args):
        sys.stderr.write(f"[BACKEND:{SERVER_PORT}] {self.client_address[0]} - {format % args}\n")

    def _send_json(self, data, status=200, extra_headers=None):
        payload = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)

        # 1. Общедоступный эндпоинт
        if parsed.path == "/api/public" or parsed.path == "/api/health":
            self._send_json({
                "status": "UP",
                "service": "Fintech Core Gateway",
                "port": SERVER_PORT,
                "timestamp": time.time()
            })
            return

        # 2. Защищенная панель администратора
        if parsed.path == "/admin":
            # Проверка IP клиента: проверяем заголовок X-Forwarded-For от прокси
            # Если прокси Nginx сконфигурирован ошибочно ($http_x_forwarded_for),
            # атакующий может подделать этот заголовок!
            forwarded_for = self.headers.get("X-Forwarded-For", "").strip()
            real_ip = self.headers.get("X-Real-IP", "").strip()
            direct_socket_ip = self.client_address[0]

            # Определение клиентского IP по логике бэкенда
            # При уязвимом доверии заголовок берется первым
            effective_client_ip = ""
            if forwarded_for:
                # Берем самый первый адрес из цепочки (распространенная уязвимость парсинга)
                effective_client_ip = forwarded_for.split(",")[0].strip()
            elif real_ip:
                effective_client_ip = real_ip
            else:
                effective_client_ip = direct_socket_ip

            # Проверка белого списка (разрешен доступ только локальному администратору)
            trusted_admins = ["127.0.0.1", "::1", "localhost"]
            if effective_client_ip in trusted_admins:
                self._send_json({
                    "status": "AUTHORIZED",
                    "access_level": "ROOT_ADMINISTRATOR",
                    "effective_client_ip": effective_client_ip,
                    "socket_peer_ip": direct_socket_ip,
                    "message": "Добро пожаловать в закрытую панель управления инфраструктурой!",
                    "flag": "FLAG{x_forwarded_for_ip_spoofed_admin_access_granted}",
                    "sensitive_data": {
                        "db_master_host": "10.0.50.12:5432",
                        "db_superuser": "postgres_admin",
                        "db_master_token": "pg_sec_token_98319fbc7412e"
                    }
                }, status=200)
            else:
                self._send_json({
                    "status": "DENIED",
                    "error": "Forbidden: Client IP is not in whitelist",
                    "detected_client_ip": effective_client_ip,
                    "socket_peer_ip": direct_socket_ip,
                    "hint": "Доступ разрешен только доверенному IP 127.0.0.1"
                }, status=403)
            return

        # 404 по умолчанию
        self._send_json({"error": "Endpoint not found", "path": parsed.path}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8', errors='ignore')

        if parsed.path == "/api/login":
            # Эндпоинт логина для тестирования Rate Limiting
            self._send_json({
                "status": "LOGIN_PROCESSED",
                "message": "Запрос на аутентификацию получен бэкендом",
                "timestamp": time.time(),
                "body_len": len(body)
            })
            return

        self._send_json({"error": "Unknown POST route"}, status=404)

def run():
    server = HTTPServer(('127.0.0.1', SERVER_PORT), LabSecurityHandler)
    print(f"[BACKEND-STARTED] Защищенный бэкенд запущен на 127.0.0.1:{SERVER_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка бэкенда...")
        server.server_close()

if __name__ == "__main__":
    run()
