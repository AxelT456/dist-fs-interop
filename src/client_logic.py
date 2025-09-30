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
# 👇 --- 1. IMPORTAMOS EL TRADUCTOR ---
from src.network.dns_translator.translator import DNSTranslatorIntegrated

# La lista global de DNS_SERVERS sigue siendo útil para la selección aleatoria inicial
with open('network_config.json', 'r') as f:
    net_config = json.load(f)

# Construir DNS_SERVERS dinámicamente
DNS_SERVERS = []
for peer_name, peer_data in net_config['peers'].items():
    DNS_SERVERS.append({
        "id": peer_data['id_dns_cliente'],
        "ip": peer_data['dns_ip'],
        "port": peer_data['dns_port'],
        "description": f"DNS para {peer_name}",
        # --- LÍNEA CORREGIDA QUE FALTABA ---
        "server_id": peer_name 
    })

class ClientLogic:
    def __init__(self):
        self.transport = None
        self.peer_connector = None
        self.server_info = None
        self.dns_info = None
        self.is_connected = False
        self.client_host = "0.0.0.0"
        self.client_port = 0
        self.waiting_for_response = False
        self.last_response = None
        # 👇 --- 2. INICIALIZAMOS EL TRADUCTOR ---
        self.translator = DNSTranslatorIntegrated()

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
            return False, f"Fallo al consultar DNS {self.dns_info['id']}. No se pudo obtener la dirección del servidor."
        
        if not self._connect_to_server_securely():
            server_address = f"{self.server_info[0]}:{self.server_info[1]}" if self.server_info else "desconocido"
            return False, f"No se pudo establecer una conexión segura con el servidor en {server_address}"
        
        server_address = f"{self.server_info[0]}:{self.server_info[1]}"
        success_msg = f"Conectado a {server_address} a través de DNS {self.dns_info['id']}"
        return True, success_msg
    
    def get_all_locks(self):
        """Pide al DNS General la lista de todos los archivos bloqueados."""
        request = {"accion": "listar_bloqueos"}
        return self._send_secure_request(request)
    
    def check_lock_status(self, filename):
        """Verifica el estado de un bloqueo."""
        request = {"accion": "verificar_bloqueo", "nombre_archivo": filename}
        return self._send_secure_request(request)
    
    def request_lock(self, filename):
        """Solicita un bloqueo de escritura para un archivo."""
        request = {"accion": "solicitar_bloqueo", "nombre_archivo": filename}
        return self._send_secure_request(request)

    def release_lock(self, filename):
        """Libera el bloqueo de escritura de un archivo."""
        request = {"accion": "liberar_bloqueo", "nombre_archivo": filename}
        return self._send_secure_request(request)
    
    def connect_to_specific_dns(self, dns_id: str):
        """
        Orquesta la conexión a un servidor a través de un DNS específico.
        """
        self.disconnect()

        # Encuentra la info del DNS a partir del ID proporcionado
        dns_info = next((d for d in DNS_SERVERS if d["id"] == dns_id), None)
        if not dns_info:
            return False, f"Error: DNS con ID '{dns_id}' no encontrado en la configuración."
        
        self.dns_info = dns_info

        # El resto del proceso es idéntico
        if not self._query_dns_for_server():
            return False, f"Fallo al consultar DNS {self.dns_info['id']}. No se pudo obtener la dirección del servidor."
        
        if not self._connect_to_server_securely():
            server_address = f"{self.server_info[0]}:{self.server_info[1]}" if self.server_info else "desconocido"
            return False, f"No se pudo establecer una conexión segura con el servidor en {server_address}"
        
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
                pass
            finally:
                self.peer_connector.stop()
        
        self.is_connected = False
        self.peer_connector = None
        self.transport = None
        
    # 👇 --- 3. MÉTODO REFACTORIZADO Y SIMPLIFICADO ---
    def _query_dns_for_server(self):
        """
        Consulta al DNS elegido usando el traductor para obtener la IP/puerto.
        """
        if not self.dns_info:
            print("Error: No se ha seleccionado ningún servidor DNS para consultar.")
            return False
        
        dns_id = self.dns_info['id']
        print(f"Intentando consultar al DNS '{dns_id}' usando el traductor...")

        # Creamos una petición estándar. El traductor se encargará de adaptarla.
        standard_request = {
            "accion": "consultar",
            "nombre_archivo": "servidor_info" 
        }
        
        # Usamos el traductor. ¡Toda la complejidad está ahora dentro de él!
        response = self.translator._try_resolve(standard_request, dns_id)
        print("\n\n\n\n")
        print(response)
        print("\n\n\n\n")

        # Analizamos la respuesta estandarizada que nos devuelve el traductor.
        if response and response.get("status") == "ACK":
            server_ip = response.get("ip")
            server_port = response.get("puerto") or response.get("port")

            if server_ip and server_port:
                self.server_info = (server_ip, int(server_port))
                print(f"¡Éxito! El DNS '{dns_id}' respondió. Servidor de archivos en: {self.server_info[0]}:{self.server_info[1]}")
                return True
        
        # Si llegamos aquí, el traductor no pudo obtener una respuesta válida.
        print(f"Fallo total: No se pudo obtener una respuesta válida del DNS '{dns_id}'.")
        print(f"Respuesta del traductor: {response.get('mensaje', 'Sin detalles')}")
        return False

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

            start_time = time.time()
            while time.time() - start_time < 2.0:
                if server_addr in self.peer_connector.sessions:
                    self.is_connected = True
                    print(f"¡Conexión segura establecida con {server_addr}!")
                    return True
                
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
                
                time.sleep(0.1)
            
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

    # --- El resto de los métodos (get_file_list, read_file, etc.) no necesitan cambios ---
    def get_file_list(self):
        request = {"accion": "listar_archivos", "timestamp": time.time()}
        return self._send_secure_request(request)

    def get_file_info(self, filename):
        request = {"accion": "consultar", "nombre_archivo": filename, "timestamp": time.time()}
        return self._send_secure_request(request)
        
    def read_file(self, filename):
        request = {"accion": "leer", "nombre_archivo": filename, "timestamp": time.time()}
        return self._send_secure_request(request)

    def write_file(self, filename, content):
        request = {
            "accion": "escribir",
            "nombre_archivo": filename,
            "contenido": content,
            "timestamp": time.time()
        }
        return self._send_secure_request(request)