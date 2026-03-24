import json
import time
import ssl
import socket
import base64
import os
import struct

class ProWebSocket:
    def __init__(self, url, on_message, on_open, on_error):
        self.url = url
        self.on_message = on_message
        self.on_open = on_open
        self.on_error = on_error
        self.socket = None
        self.connected = False
        self.running = True

    def connect(self):
        try:
            host = self.url.replace('wss://', '').split('/')[0]
            path = '/' + '/'.join(self.url.replace('wss://', '').split('/')[1:])
            context = ssl.create_default_context()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            self.socket = context.wrap_socket(sock, server_hostname=host)
            self.socket.connect((host, 443))
            
            key = base64.b64encode(os.urandom(16)).decode()
            handshake = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                         f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
            self.socket.send(handshake.encode())
            
            response = self.socket.recv(1024)
            if b"101" in response:
                self.connected = True
                self.on_open(self)
                self.receive_loop()
            else:
                self.on_error(self, "Handshake failed")
        except Exception as e:
            self.on_error(self, e)

    def receive_loop(self):
        while self.connected and self.running:
            try:
                self.socket.settimeout(1)
                data = self.socket.recv(16384)
                if not data: break
                for msg in self.decode_frames(data):
                    self.on_message(self, msg)
            except socket.timeout:
                continue
            except:
                break
        self.connected = False

    def decode_frames(self, data):
        frames, i = [], 0
        while i < len(data):
            try:
                if len(data) < i + 2: break
                b1, b2 = data[i], data[i+1]
                opcode = b1 & 0x0F
                payload_len = b2 & 0x7F
                i += 2
                
                if payload_len == 126:
                    if len(data) < i + 2: break
                    payload_len = struct.unpack(">H", data[i:i+2])[0]
                    i += 2
                elif payload_len == 127:
                    if len(data) < i + 8: break
                    payload_len = struct.unpack(">Q", data[i:i+8])[0]
                    i += 8
                
                if len(data) < i + payload_len: break
                payload = data[i:i+payload_len]
                i += payload_len
                
                if opcode == 0x1:
                    frames.append(payload.decode('utf-8'))
                elif opcode == 0x8:
                    self.connected = False
            except:
                break
        return frames

    def send(self, msg):
        if not self.connected: return False
        try:
            if isinstance(msg, dict): msg = json.dumps(msg)
            data = msg.encode('utf-8')
            frame = bytearray([0x81])
            length = len(data)
            
            if length <= 125:
                frame.append(length)
            elif length <= 65535:
                frame.append(126)
                frame.extend(struct.pack(">H", length))
            else:
                frame.append(127)
                frame.extend(struct.pack(">Q", length))
            
            frame.extend(data)
            self.socket.send(frame)
            return True
        except:
            return False

    def close(self):
        self.running = False
        self.connected = False
        if self.socket: self.socket.close()