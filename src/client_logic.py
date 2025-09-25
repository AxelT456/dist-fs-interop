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
        "id": "DNS1", "ip": "127.0.0.2", "port": 50000, # Axel
        "description": "DNS Servidor Nombres (Axel)"
    },
    {
        "id": "DNS_MARCO", "ip": "127.0.0.8", "port": 50001, # Marco
        "description": "DNS Servidor Marco"
    },
    {
        "id": "DNS_GUS", "ip": "127.0.0.10", "port": 50002, # Gus
        "description": "DNS Servidor Gus"
    },
    {
        "id": "DNS2", "ip": "127.0.0.12", "port": 50003, # Christian
        "description": "DNS Servidor Christian"
    },
    {
        "id": "DNS_DAN", "ip": "127.0.0.9", "port": 50004, # Dan
        "description": "DNS Servidor Dan"
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

        # Elegir un DNS al azar para la consulta
        self.dns_info = random.choice(DNS_SERVERS)

        # Paso 1: Intentar obtener la dirección del servidor de archivos desde el DNS
        if not self._query_dns_for_server():
            return False, f"Fallo al consultar DNS {self.dns_info['id']}. No se pudo obtener la dirección del servidor."
        
        # Si la consulta al DNS tuvo éxito, self.server_info tendrá datos.
        # Paso 2: Intentar conectar de forma segura al servidor de archivos.
        if not self._connect_to_server_securely():
            server_address = f"{self.server_info[0]}:{self.server_info[1]}" if self.server_info else "desconocido"
            return False, f"No se pudo establecer una conexión segura con el servidor en {server_address}"
        
        # Si ambos pasos fueron exitosos
        server_address = f"{self.server_info[0]}:{self.server_info[1]}"
        success_msg = f"Conectado a {server_address} a través de DNS {self.dns_info['id']}"
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
        
    def _query_dns_for_server(self):
        """Consulta al DNS local (heterogéneo) para obtener la IP/puerto del servidor de archivos."""
        if not self.dns_info:
            return False
        
        dns_id = self.dns_info['id']
        print(f"Querying DNS {dns_id} at {self.dns_info['ip']}:{self.dns_info['port']}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            
            # --- LÓGICA MEJORADA: Crear la petición correcta para cada DNS ---
            if dns_id in ['DNS1', 'DNS_DAN', 'DNS_MARCO']: # Original, Dan y Marco
                request_payload = {"accion": "consultar", "nombre_archivo": "servidor_info"}
            elif dns_id == 'DNS2': # Christian
                request_payload = {"type": "check", "filename": "servidor_info", "extension": "json"}
            elif dns_id == 'DNS_GUS': # Gus
                request_payload = {"action": "get_server_info"}
            else:
                # Fallback genérico
                request_payload = {"accion": "consultar", "nombre_archivo": "servidor_info"}

            dns_addr = (self.dns_info['ip'], self.dns_info['port'])
            sock.sendto(json.dumps(request_payload).encode('utf-8'), dns_addr)
            
            data, _ = sock.recvfrom(2048)
            response = json.loads(data.decode('utf-8'))
            sock.close()

            server_ip = response.get("ip")
            server_port = response.get("puerto", response.get("port"))

            if server_ip and server_port:
                self.server_info = (server_ip, server_port)
                print(f"DNS response OK. File server is at {server_ip}:{server_port}")
                return True
            else:
                print(f"DNS response from {dns_id} did not contain server IP/port.")
                return False
        except Exception as e:
            print(f"Error querying DNS {dns_id}: {e}")
            return False

# En src/client_logic.py, reemplaza este método
    # En src/client_logic.py, reemplaza este método
    def _connect_to_server_securely(self):
        """Establece la conexión de transporte y la sesión segura."""
        if not self.server_info:
            return False
        
        server_addr = (self.server_info[0], self.server_info[1])
        print(f"Connecting securely to {server_addr}...")
        
        try:
            self.client_port = random.randint(10000, 65000)
            self.transport = ReliableTransport(self.client_host, self.client_port)
            client_id = f"web_client_{int(time.time())}"
            self.peer_connector = PeerConnector(self.transport, client_id, self._handle_secure_response)

            if not self.peer_connector.connect_and_secure(server_addr):
                return False

            # --- BUCLE DE ESCUCHA ACTIVA ---
            # En lugar de dormir, escucha activamente la respuesta durante ~2 segundos.
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if server_addr in self.peer_connector.sessions:
                    self.is_connected = True
                    print(f"¡Conexión segura establecida con {server_addr}!")
                    return True # Éxito, salimos del bucle
                
                # Escucha paquetes y déjalos ser procesados por el PeerConnector
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
                
                time.sleep(0.1) # Pequeña pausa para no saturar la CPU
            
            # Si después de 2 segundos no hay sesión, el handshake falló.
            print("Handshake timeout. No se recibió o procesó la respuesta del servidor.")
            return False
            
        except Exception as e:
            print(f"Error crítico durante conexión segura: {e}")
            return False

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