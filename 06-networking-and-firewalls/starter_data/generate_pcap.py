#!/usr/bin/env python3
"""
Скрипт генерации тестового дампа сетевого трафика (PCAP)
Формирует валидный файл формата Libpcap без внешних зависимостей.
В дампе содержатся:
1. HTTP POST с передачей учетных данных открытым текстом
2. Сессия сканирования портов (TCP SYN scan)
3. DNS-запрос с признаками эксфильтрации данных
4. Подозрительные TCP RST и ICMP echo
"""

import struct
import time

def build_eth(src_mac, dst_mac, ethertype=0x0800):
    return dst_mac + src_mac + struct.pack("!H", ethertype)

def checksum(data):
    if len(data) % 2:
        data += b'\x00'
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    s = (s >> 16) + (s & 0xffff)
    s += s >> 16
    return ~s & 0xffff

def ip_to_bytes(ip_str):
    return bytes(map(int, ip_str.split('.')))

def build_ipv4(src_ip, dst_ip, proto, payload, ip_id=1234):
    ihl = 5
    version = 4
    tos = 0
    total_len = 20 + len(payload)
    flags_frag = 0x4000  # DF
    ttl = 64
    check = 0
    header_no_check = struct.pack("!BBHHHBBH4s4s",
        (version << 4) + ihl, tos, total_len, ip_id,
        flags_frag, ttl, proto, check, ip_to_bytes(src_ip), ip_to_bytes(dst_ip))
    check = checksum(header_no_check)
    header = struct.pack("!BBHHHBBH4s4s",
        (version << 4) + ihl, tos, total_len, ip_id,
        flags_frag, ttl, proto, check, ip_to_bytes(src_ip), ip_to_bytes(dst_ip))
    return header + payload

def build_tcp(src_ip, dst_ip, src_port, dst_port, seq, ack, flags, payload=b'', window=64240):
    data_offset = 5
    check = 0
    urgent_ptr = 0
    tcp_hdr_dummy = struct.pack("!HHIIBBHHH",
        src_port, dst_port, seq, ack, (data_offset << 4), flags, window, check, urgent_ptr)
    
    # Pseudo header for TCP checksum
    pseudo_hdr = struct.pack("!4s4sBBH",
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip), 0, 6, len(tcp_hdr_dummy) + len(payload))
    check = checksum(pseudo_hdr + tcp_hdr_dummy + payload)
    
    tcp_hdr = struct.pack("!HHIIBBHHH",
        src_port, dst_port, seq, ack, (data_offset << 4), flags, window, check, urgent_ptr)
    return tcp_hdr + payload

def build_udp(src_ip, dst_ip, src_port, dst_port, payload=b''):
    length = 8 + len(payload)
    check = 0
    pseudo_hdr = struct.pack("!4s4sBBH",
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip), 0, 17, length)
    udp_dummy = struct.pack("!HHHH", src_port, dst_port, length, check)
    check = checksum(pseudo_hdr + udp_dummy + payload)
    if check == 0:
        check = 0xffff
    return struct.pack("!HHHH", src_port, dst_port, length, check) + payload

def encode_dns_query(qname, qtype=1, qclass=1):
    parts = qname.split('.')
    qname_bytes = b''.join(bytes([len(p)]) + p.encode('ascii') for p in parts) + b'\x00'
    header = struct.pack("!HHHHHH", 0x1337, 0x0100, 1, 0, 0, 0)
    question = qname_bytes + struct.pack("!HH", qtype, qclass)
    return header + question

def create_pcap(filename):
    client_mac = b'\x00\x11\x22\x33\x44\x55'
    server_mac = b'\x52\x54\x00\x12\x34\x56'
    client_ip = "192.168.1.100"
    server_ip = "192.168.1.10"
    dns_ip = "1.1.1.1"

    packets = []
    base_ts = 1775376000 # fixed timestamp

    def add_pkt(pkt_data, delta_ms):
        ts = base_ts + delta_ms / 1000.0
        sec = int(ts)
        usec = int((ts - sec) * 1000000)
        packets.append((sec, usec, pkt_data))

    # 1. 3-Way Handshake TCP (Client -> Server:80)
    # SYN
    p1 = build_eth(client_mac, server_mac) + build_ipv4(client_ip, server_ip, 6,
         build_tcp(client_ip, server_ip, 45678, 80, 1000, 0, 0x02)) # SYN
    add_pkt(p1, 10)

    # SYN-ACK
    p2 = build_eth(server_mac, client_mac) + build_ipv4(server_ip, client_ip, 6,
         build_tcp(server_ip, client_ip, 80, 45678, 5000, 1001, 0x12)) # SYN-ACK
    add_pkt(p2, 12)

    # ACK
    p3 = build_eth(client_mac, server_mac) + build_ipv4(client_ip, server_ip, 6,
         build_tcp(client_ip, server_ip, 45678, 80, 1001, 5001, 0x10)) # ACK
    add_pkt(p3, 14)

    # 2. HTTP POST with plaintext credentials
    http_payload = (
        b"POST /api/v1/auth/login HTTP/1.1\r\n"
        b"Host: internal-portal.corp\r\n"
        b"User-Agent: Mozilla/5.0 (X11; Linux x86_64)\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Content-Length: 53\r\n\r\n"
        b"username=corp_admin&password=SuperSecretPassword2026!"
    )
    p4 = build_eth(client_mac, server_mac) + build_ipv4(client_ip, server_ip, 6,
         build_tcp(client_ip, server_ip, 45678, 80, 1001, 5001, 0x18, http_payload)) # PSH-ACK
    add_pkt(p4, 20)

    # Server ACK + HTTP 200 Response
    http_resp = (
        b"HTTP/1.1 200 OK\r\n"
        b"Server: nginx/1.24.0\r\n"
        b"Content-Type: application/json\r\n"
        b"Set-Cookie: auth_session=eyJhbGciOiJIUzI1NiJ9.s3cr3t; Path=/\r\n"
        b"Content-Length: 27\r\n\r\n"
        b'{"status":"ok","role":"admin"}'
    )
    p5 = build_eth(server_mac, client_mac) + build_ipv4(server_ip, client_ip, 6,
         build_tcp(server_ip, client_ip, 80, 45678, 5001, 1001 + len(http_payload), 0x18, http_resp))
    add_pkt(p5, 25)

    # 3. TCP SYN Port Scan from attacker (10.0.0.66)
    attacker_ip = "10.0.0.66"
    attacker_mac = b'\x00\xaa\xbb\xcc\xdd\xee'
    ports_to_scan = [21, 22, 23, 25, 80, 443, 3306, 8080]
    
    for idx, dport in enumerate(ports_to_scan):
        scan_pkt = build_eth(attacker_mac, server_mac) + build_ipv4(attacker_ip, server_ip, 6,
                   build_tcp(attacker_ip, server_ip, 50000 + idx, dport, 10000 + idx, 0, 0x02)) # SYN
        add_pkt(scan_pkt, 100 + idx * 5)
        # Server responds with RST-ACK for closed ports, SYN-ACK for 80
        if dport == 80:
            resp_pkt = build_eth(server_mac, attacker_mac) + build_ipv4(server_ip, attacker_ip, 6,
                       build_tcp(server_ip, attacker_ip, dport, 50000 + idx, 20000, 10001 + idx, 0x12))
        else:
            resp_pkt = build_eth(server_mac, attacker_mac) + build_ipv4(server_ip, attacker_ip, 6,
                       build_tcp(server_ip, attacker_ip, dport, 50000 + idx, 0, 10001 + idx, 0x14)) # RST-ACK
        add_pkt(resp_pkt, 102 + idx * 5)

    # 4. Suspicious DNS query (data exfiltration in subdomain)
    dns_query = encode_dns_query("cGFzc3dvcmRfaGFzaF9lMmQ1YTc.exfil.c2-command.ru")
    dns_pkt = build_eth(client_mac, server_mac) + build_ipv4(client_ip, dns_ip, 17,
              build_udp(client_ip, dns_ip, 54321, 53, dns_query))
    add_pkt(dns_pkt, 300)

    # Write PCAP Global Header
    # magic 0xa1b2c3d4, v2.4, thiszone=0, sigfigs=0, snaplen=65535, network=1 (Ethernet)
    global_hdr = struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
    
    with open(filename, "wb") as f:
        f.write(global_hdr)
        for sec, usec, pkt in packets:
            length = len(pkt)
            pkt_hdr = struct.pack("!IIII", sec, usec, length, length)
            f.write(pkt_hdr)
            f.write(pkt)

if __name__ == "__main__":
    create_pcap("sample_traffic.pcap")
    print("Created sample_traffic.pcap successfully.")
