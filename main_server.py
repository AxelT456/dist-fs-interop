# /main_server.py

import json
import os
import sys
import threading
import time
from typing import Dict

# --- 1. Importaciones ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.transport import ReliableTransport
from src.network.peer_conector import PeerConnector
from src.core.catalog_manager import CatalogManager
from src.core.file_handler import FileHandler
from src.web.controller import start_web_server
from src.network.dns_translator.translator import DNSTranslator # ¡Importación Clave!

# --- 2. Configuración ---
CONFIG_FILE = "config.json"

class MainServer:
    def __init__(self, config: Dict):
        self.config = config
        self.server_id = config["server_id"]
        self.host = config["host"]
        self.port = config["port"]
        print(f"🚀 Iniciando servidor P2P '{self.server_id}' en {self.host}:{self.port}...")

        # --- 3. Instanciación de Componentes ---
        self.transport = ReliableTransport(self.host, self.port)
        self.connector = PeerConnector(self.transport, self.server_id, self._on_decrypted_message)
        self.catalog_manager = CatalogManager(self.server_id)
        self.file_handler = FileHandler(self.server_id)
        
        # ¡NUEVO! Se instancia el DNSTranslator con la configuración.
        self.translator = DNSTranslator(config)
        
        self._populate_local_files()
        print(f"✅ Servidor P2P listo.")

    def _populate_local_files(self):
        """Simula la carga de archivos locales al iniciar."""
        if self.server_id == "server-A":
            self.catalog_manager.add_local_file("LibroA.txt")
            self.catalog_manager.add_local_file("LibroB.pdf")
        elif self.server_id == "server-B":
            self.catalog_manager.add_local_file("DocumentoX.docx")

    def bootstrap_network(self):
        """
        Orquesta el arranque de la red usando el DNSTranslator para descubrir peers.
        """
        print("\n--- Iniciando Bootstrap (Modo Interoperabilidad DNS) ---")
        peers_to_find = self.config.get("peers", [])
        if not peers_to_find:
            self.catalog_manager.build_master_catalog()
            self.catalog_manager.print_catalog_summary()
            return

        # 1. Resolver, conectar y solicitar catálogos
        print(f"-> Descubriendo y solicitando catálogos a {len(peers_to_find)} peers...")
        request = self.catalog_manager.get_bootstrap_message()

        for peer_info in peers_to_find:
            peer_id = peer_info["id"]
            dns_id_for_peer = peer_info["dns_id"]
            
            print(f"   - Resolviendo '{peer_id}' usando el DNS '{dns_id_for_peer}'...")
            
            # ¡AQUÍ ESTÁ LA LÓGICA CLAVE!
            # Se usa el traductor para obtener la dirección del peer.
            peer_addr = self.translator.resolve(peer_id, dns_id_for_peer)
            
            if peer_addr:
                print(f"     ✅ Dirección resuelta: {peer_addr}")
                # Si se encontró la dirección, se conecta y pide el catálogo
                if self.transport.connect(peer_addr):
                    self.connector.connect_and_secure(peer_addr)
                    time.sleep(0.5) # Pausa para el handshake de seguridad
                    self.connector.send_message(request, peer_addr)
            else:
                print(f"     ❌ Falló la resolución de '{peer_id}'.")

        # 2. Esperar respuestas, construir y distribuir el catálogo maestro
        print("\n⏳ Esperando respuestas de los peers (3 segundos)...")
        time.sleep(3)
        self.catalog_manager.build_master_catalog()

        distribute_request = self.catalog_manager.get_distribute_catalog_message()
        print(f"-> Distribuyendo catálogo maestro a los peers resueltos...")
        # Volvemos a resolver para asegurarnos de tener las IPs correctas para la distribución
        for peer_info in peers_to_find:
             peer_addr = self.translator.resolve(peer_info["id"], peer_info["dns_id"])
             if peer_addr:
                self.connector.send_message(distribute_request, peer_addr)

        self.catalog_manager.print_catalog_summary()
        print("--- ✅ Bootstrap Completado ---")

    def _on_decrypted_message(self, request: Dict, addr: tuple):
        """Manejador principal de mensajes que delega a los componentes correctos."""
        response_data = self.process_request(request, addr)
        if response_data:
            self.connector.send_message(response_data, addr)

    def process_request(self, request: Dict, client_addr: tuple) -> Dict:
        """Procesa peticiones P2P usando los manejadores de lógica."""
        msg_type = request.get("type")
        
        if msg_type == "GET_CATALOG_INFO":
            return self.catalog_manager.get_local_catalog_info()
        elif msg_type == "CATALOG_INFO_RESPONSE":
            self.catalog_manager.process_catalog_response(request, client_addr)
            return None
        elif msg_type == "DISTRIBUTE_MASTER_CATALOG":
            self.catalog_manager.process_master_catalog_distribution(request)
            return None
        elif msg_type == "GET_FILE_COPY":
            return self.file_handler.process_file_copy_request(request)
        else:
            return {"type": "ERROR", "message": f"Tipo de mensaje no reconocido: {msg_type}"}

    def run(self):
        """Bucle principal del servidor P2P."""
        try:
            while True:
                payload, addr = self.transport.listen()
                if payload:
                    self.connector.handle_incoming_packet(payload, addr)
        except KeyboardInterrupt:
            print("\n🛑 Servidor detenido.")
        finally:
            self.cleanup()
    
    def cleanup(self):
        print("Limpiando recursos...")
        self.transport.stop()

# --- Punto de Entrada ---
def main():
    print("="*60)
    print("SISTEMA DE ARCHIVOS DISTRIBUIDO v5.0 (con Interoperabilidad DNS)")
    print("="*60)
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error fatal al cargar '{CONFIG_FILE}': {e}")
        sys.exit(1)

    server = MainServer(config)
    
    web_thread = threading.Thread(
        target=start_web_server,
        args=(server.catalog_manager, server.file_handler),
        daemon=True
    )
    web_thread.start()

    print("Servidores iniciándose, esperando 5 segundos antes del bootstrap...")
    time.sleep(5)
    
    bootstrap_thread = threading.Thread(target=server.bootstrap_network, daemon=True)
    bootstrap_thread.start()

    server.run()

if __name__ == "__main__":
    main()