import socket
import json
import os
import sys
import time
import random

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.network.peer_conector import PeerConnector
from src.network.transport import ReliableTransport

# Configuración de DNS disponibles (expandida)
DNS_SERVERS = [
    {
        "id": "DNS1",
        "ip": "127.0.0.2",
        "port": 50000,
        "server_ip": "127.0.0.3",
        "server_port": 5002,
        "description": "DNS Servidor Original"
    },
    {
        "id": "DNS2", 
        "ip": "127.0.0.12",
        "port": 50000,
        "server_ip": "127.0.0.4",
        "server_port": 5003,
        "description": "DNS Servidor Christian"
    },
    {
        "id": "DNS_MARCO",
        "ip": "127.0.0.8",
        "port": 50000,
        "server_ip": "127.0.0.8",
        "server_port": 5005,
        "description": "DNS Servidor Marco"
    },
    {
        "id": "DNS_DAN",
        "ip": "127.0.0.9",
        "port": 50000,
        "server_ip": "127.0.0.9",
        "server_port": 5006,
        "description": "DNS Servidor Dan"
    },
    {
        "id": "DNS_GUS",
        "ip": "127.0.0.10",
        "port": 50000,
        "server_ip": "127.0.0.10",
        "server_port": 5007,
        "description": "DNS Servidor Gus"
    }
]

class ClientLogic:
    def __init__(self):
        self.transport = None
        self.peer_connector = None
        self.server_info = None
        self.dns_info = None
        self.is_connected = False
        self.client_host = "127.0.0.1"
        self.client_port = 0
        self.waiting_for_response = False
        self.last_response = None

    def _handle_secure_response(self, response: dict, peer_addr: tuple):
        """Callback para manejar respuestas asincronas. Solo almacena el resultado"""
        self.last_response = response
        self.waiting_for_response = False

    def connect_randomly(self):
        """
        Orquesta el proceso completo de conexión a un servidor aleatorio.
        Devuelve (True, "Mensaje de éxito") o (False, "Mensaje de error").
        """
        self.disconnect()

        self.dns_info = random.choice(DNS_SERVERS)

        if not self._query_dns_for_server():
            return False, f"No se pudo obtener información del servidor desde DNS {self.dns_info['id']}"
        
        if not self._connect_to_server_securely():
            return False, f"No se pudo conectar de forma segura al servidor {self.server_info['id']}"
        
        success_msg = f"Conectado a {self.server_info[0]}:{self.server_info[1]} a través de DNS {self.dns_info['id']}"
        return True, success_msg
    
    def disconnect(self):
        """Desconecta del servidor de forma segura."""
        if self.peer_connector and self.is_connected:
            try:
                server_addr = (self.server_info[0], self.server_info[1])
                self.peer_connector.send_message({"accion": "salir"}, server_addr)
                time.sleep(0.5)
            except Exception:
                pass # Ignorar errores al desconectar
            finally:
                self.peer_connector.stop()
        
        self.is_connected = False
        self.peer_connector = None
        self.transport = None

    def _send_secure_request(self, request: dict):
        """Lógica interna para enviar una solicitud y esperar la respuesta."""
        if not self.is_connected:
            return {"status": "ERROR", "mensaje": "No conectado al servidor"}
        try:
            server_addr = (self.server_info[0], self.server_info[1])
            self.waiting_for_response = True
            self.last_response = None
            self.peer_connector.send_message(request, server_addr)
            
            start_time = time.time()
            while self.waiting_for_response and time.time() - start_time < 10:
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
                time.sleep(0.1)
            
            return self.last_response or {"status": "ERROR", "mensaje": "Timeout esperando respuesta"}
        except Exception as e:
            return {"status": "ERROR", "mensaje": str(e)}

    def get_file_list(self):
        """Pide la lista de archivos al servidor."""
        request = {"accion": "listar_archivos", "timestamp": time.time()}
        return self._send_secure_request(request)

    def get_file_info(self, filename):
        """Consulta la información de un archivo específico."""
        request = {"accion": "consultar", "nombre_archivo": filename, "timestamp": time.time()}
        return self._send_secure_request(request)
        
    def read_file(self, filename):
        """Lee el contenido de un archivo."""
        request = {"accion": "leer", "nombre_archivo": filename, "timestamp": time.time()}
        return self._send_secure_request(request)

    def write_file(self, filename, content):
        """Escribe contenido en un archivo."""
        request = {
            "accion": "escribir",
            "nombre_archivo": filename,
            "contenido": content,
            "timestamp": time.time()
        }
        return self._send_secure_request(request)