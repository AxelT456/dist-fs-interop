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
        
        # Se instancia tu CatalogManager y FileHandler
        self.catalog_manager = CatalogManager(self.server_id)
        self.file_handler = FileHandler(self.server_id)
        # Poblar el catálogo local con archivos de ejemplo
        self._populate_local_files()

        print(f"✅ Servidor P2P listo.")

    def _populate_local_files(self):
        """Simula la carga de archivos locales al iniciar."""
        # En un sistema real, esto escanearía el directorio de datos.
        # Usamos datos de ejemplo para la prueba.
        if self.server_id == "server-A":
            self.catalog_manager.add_local_file("LibroA.txt")
            self.catalog_manager.add_local_file("LibroB.pdf")

    def bootstrap_network(self):
        """
        Orquesta el proceso de arranque y sincronización de la red.
        """
        print("\n--- Iniciando Bootstrap de la Red ---")
        peers = self.config.get("peers", [])
        if not peers:
            print("⚠️ No hay peers en la configuración. Construyendo catálogo solo con archivos locales.")
            self.catalog_manager.build_master_catalog()
            self.catalog_manager.print_catalog_summary()
            return

        # 1. Solicitar catálogos a todos los peers
        print(f"-> Solicitando catálogos a {len(peers)} peers...")
        request = self.catalog_manager.get_bootstrap_message() #
        for peer in peers:
            peer_addr = (peer["host"], peer["port"])
            # Se establece la conexión de transporte y luego la de seguridad
            if self.transport.connect(peer_addr):
                self.connector.connect_and_secure(peer_addr)
                time.sleep(0.5) # Dar tiempo para que se complete el handshake
                self.connector.send_message(request, peer_addr)

        # 2. Esperar respuestas y construir el catálogo maestro
        print("⏳ Esperando respuestas de los peers (espera de 3 segundos)...")
        time.sleep(3)
        self.catalog_manager.build_master_catalog() #

        # 3. Distribuir el catálogo maestro completo
        print(f"-> Distribuyendo catálogo maestro a {len(peers)} peers...")
        distribute_request = self.catalog_manager.get_distribute_catalog_message() #
        for peer in peers:
            peer_addr = (peer["host"], peer["port"])
            self.connector.send_message(distribute_request, peer_addr)
        
        self.catalog_manager.print_catalog_summary()
        print("--- ✅ Bootstrap Completado ---")

    def _on_decrypted_message(self, request: Dict, addr: tuple):
        """Manejador de mensajes que delega a los componentes correctos."""
        response_data = self.process_request(request, addr)
        if response_data:
            self.connector.send_message(response_data, addr)

    def process_request(self, request: Dict, client_addr: tuple) -> Dict:
        """Procesa peticiones P2P usando los manejadores."""
        msg_type = request.get("type")
        
        # --- Lógica de Bootstrap ---
        if msg_type == "GET_CATALOG_INFO":
            return self.catalog_manager.get_local_catalog_info()
        
        elif msg_type == "CATALOG_INFO_RESPONSE":
            self.catalog_manager.process_catalog_response(request, client_addr)
            return None # No se necesita respuesta para un ACK

        elif msg_type == "DISTRIBUTE_MASTER_CATALOG":
            self.catalog_manager.process_master_catalog_distribution(request)
            return None

        # --- Lógica de Archivos ---
        elif msg_type == "GET_FILE_COPY":
            return self.file_handler.process_file_copy_request(request)
        
        # ... otros tipos de mensajes ...

        else:
            print(f"⚠️ Mensaje con tipo desconocido recibido: {msg_type}")
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
    print("SISTEMA DE ARCHIVOS DISTRIBUIDO P2P - v4.0 (con Bootstrap)")
    print("="*60)
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error fatal al cargar '{CONFIG_FILE}': {e}")
        sys.exit(1)

    server = MainServer(config)
    
    # Iniciar servidor WEB en un hilo
    web_thread = threading.Thread(
        target=start_web_server,
        args=(server.catalog_manager, server.file_handler),
        daemon=True
    )
    web_thread.start()

    # Dar un respiro para que los servidores se inicien antes del bootstrap
    print("Servidores iniciándose, esperando 5 segundos antes del bootstrap...")
    time.sleep(5)
    
    # Iniciar el proceso de Bootstrap en un hilo para no bloquear
    bootstrap_thread = threading.Thread(target=server.bootstrap_network, daemon=True)
    bootstrap_thread.start()

    # El hilo principal se queda en el bucle de escucha P2P
    server.run()

if __name__ == "__main__":
    main()