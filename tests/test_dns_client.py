# /tests/test_dns_client.py

import sys
import os
import time
import json
import threading
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.transport import ReliableTransport
from src.network.peer_conector import PeerConnector

# --- Configuración ---
DNS_SERVER_ADDR = ("127.0.0.1", 8053)
SERVER_NAME_TO_FIND = "server-A" # El nombre del servidor que queremos encontrar

class TestClient:
    def __init__(self):
        print("🚀 Iniciando cliente de prueba...")
        self.transport = ReliableTransport("0.0.0.0", 0)
        self.connector = PeerConnector(self.transport, "cliente-final-01", self._on_decrypted_message)
        self.server_addr = None
        self.response_received = None
        self.shutdown_event = threading.Event()

    def _on_decrypted_message(self, response: dict, addr: tuple):
        print(f"\n✅ Respuesta del Servidor {addr}:")
        print(json.dumps(response, indent=2))
        self.response_received = response
        self.shutdown_event.set()

    def resolve_server_address(self):
        """Usa el DNS para encontrar la IP y el puerto del servidor principal."""
        try:
            print(f"📡 Consultando al DNS en {DNS_SERVER_ADDR} por '{SERVER_NAME_TO_FIND}'...")
            sock_dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock_dns.settimeout(2.0)
            
            query = json.dumps({"query": SERVER_NAME_TO_FIND}).encode("utf-8")
            sock_dns.sendto(query, DNS_SERVER_ADDR)
            
            data, _ = sock_dns.recvfrom(4096)
            result = json.loads(data.decode("utf-8"))
            
            if result and result.get("ip") != "0.0.0.0":
                self.server_addr = (result["ip"], result["port"])
                print(f"✅ Dirección obtenida del DNS: {self.server_addr}")
                return True
            else:
                print("❌ El DNS no encontró un registro para el servidor.")
                return False
        except Exception as e:
            print(f"❌ Error consultando DNS: {e}")
            return False

    def run_test(self):
        if not self.resolve_server_address():
            self.shutdown_event.set()
            return
            
        if not self.transport.connect(self.server_addr):
            print("❌ Falló la conexión de transporte. Abortando.")
            self.shutdown_event.set()
            return

        print("\n[Cliente] Conexión de transporte OK. Iniciando handshake de seguridad...")
        self.connector.connect_and_secure(self.server_addr)
        time.sleep(1) 

        if self.server_addr in self.connector.sessions:
            print("\n[Cliente] ✅ Sesión segura establecida. Pidiendo catálogo.")
            request = {"type": "GET_CATALOG_INFO"}
            self.connector.send_message(request, self.server_addr)
        else:
            print("❌ No se pudo establecer la sesión segura.")
            self.shutdown_event.set()

    def listen_for_responses(self):
        print("...cliente escuchando por respuestas...")
        while not self.shutdown_event.is_set():
            payload, addr = self.transport.listen()
            if payload and addr:
                self.connector.handle_incoming_packet(payload, addr)
    
    def stop(self):
        self.connector.stop()

if __name__ == "__main__":
    client = TestClient()
    listener_thread = threading.Thread(target=client.listen_for_responses, daemon=True)
    listener_thread.start()
    client.run_test()
    listener_thread.join(timeout=5)
    print("\nPrueba finalizada.")
    client.stop()