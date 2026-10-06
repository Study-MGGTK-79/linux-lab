#!/usr/bin/env python3
"""
Lightweight Mock Webhook Receiver for testing alerting scripts.
Listens on port 9099 and logs incoming JSON alert payloads to stdout and a log file.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import datetime

PORT = 9099
LOG_FILE = "/tmp/linux_lab10/logs/received_alerts.log"

class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{now}] 🔔 ВХОДЯЩИЙ АЛЕРТ ОТ СКРИПТА BASH:")
        
        try:
            parsed = json.loads(body)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            print(formatted)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"--- Alert received at {now} ---\n{formatted}\n\n")
        except json.JSONDecodeError:
            print(f"Raw Body: {body}")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"--- Alert received at {now} (RAW) ---\n{body}\n\n")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "delivered": true}')

    def log_message(self, format, *args):
        # Подавляем стандартный вывод доступа для чистоты консоли
        return

def run():
    server_address = ('127.0.0.1', PORT)
    httpd = HTTPServer(server_address, AlertHandler)
    print(f"📡 Сервер приема алертов запущен на http://127.0.0.1:{PORT}")
    print(f"📝 Лог алертов сохраняется в {LOG_FILE}")
    print("Ожидание вебхуков от backup-скрипта (Нажмите Ctrl+C для остановки)...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер приема алертов остановлен.")

if __name__ == '__main__':
    run()
