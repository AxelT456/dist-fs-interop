# /main_server.py
import json
import sys
import os
from typing import Dict, List

# Añade la carpeta src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.catalog_manager import CatalogManager
from src.core.file_handler import FileHandler
from src.network.transport import ReliableTransport
from src.network.security import SecureSession

class DistributedFileServer:
    """
    Servidor principal que integra todos los componentes del sistema distribuido.
    Coordina la comunicación entre la lógica de negocio y la capa de red.
    """
    
    def __init__(self, config_file: str = "config.json"):
        self.config = self.load_config(config_file)
        self.server_id = self.config["server_id"]
        self.host = self.config["host"]
        self.port = self.config["port"]
        
        # Inicializar componentes
        self.catalog_manager = CatalogManager(self.server_id)
        self.file_handler = FileHandler(self.server_id)
        self.transport = ReliableTransport(self.host, self.port)
        self.security_session = SecureSession()
        
        # Configurar peers
        peer_addresses = [(peer["host"], peer["port"]) for peer in self.config["peers"]]
        self.catalog_manager.set_peer_addresses(peer_addresses)
        
        print(f"Servidor {self.server_id} inicializado en {self.host}:{self.port}")
    
    def load_config(self, config_file: str) -> Dict:
        """Carga la configuración del sistema desde archivo JSON."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Archivo de configuración no encontrado: {config_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error en configuración JSON: {e}")
            sys.exit(1)
    
    def bootstrap_system(self):
        """Inicializa el sistema realizando la sincronización inicial de catálogos."""
        print("Iniciando bootstrap del sistema...")
        
        # 1. Solicitar catálogos a todos los peers
        bootstrap_msg = self.catalog_manager.get_bootstrap_message()
        peer_addresses = [(peer["host"], peer["port"]) for peer in self.config["peers"]]
        
        for peer_addr in peer_addresses:
            print(f"Enviando solicitud de catálogo a {peer_addr}")
            # En un sistema real, aquí se enviaría el mensaje a través del transport
            # Por ahora, simulamos la respuesta
            self.simulate_peer_response(peer_addr)
        
        # 2. Construir catálogo maestro
        master_catalog = self.catalog_manager.build_master_catalog()
        
        # 3. Distribuir catálogo maestro
        distribute_msg = self.catalog_manager.get_distribute_catalog_message()
        print(f"Catálogo maestro distribuido: {len(master_catalog)} archivos")
        
        print("Bootstrap del sistema completado")
    
    def simulate_peer_response(self, peer_addr):
        """Simula una respuesta de peer para pruebas de integración."""
        # En un sistema real, esto se haría a través de la red
        mock_response = {
            "type": "CATALOG_INFO_RESPONSE",
            "server_id": f"server-{peer_addr[1]}",
            "files": [f"archivo_{peer_addr[1]}.txt", f"datos_{peer_addr[1]}.csv"]
        }
        self.catalog_manager.process_catalog_response(mock_response, peer_addr)
    
    def process_message(self, message: Dict, client_addr) -> Dict:
        """Procesa mensajes del protocolo y genera respuestas apropiadas."""
        msg_type = message.get("type")
        
        if msg_type == "GET_CATALOG_INFO":
            return self.catalog_manager.get_local_catalog_info()
        
        elif msg_type == "CATALOG_INFO_RESPONSE":
            success = self.catalog_manager.process_catalog_response(message, client_addr)
            return {"type": "ACK", "status": "OK" if success else "ERROR"}
        
        elif msg_type == "DISTRIBUTE_MASTER_CATALOG":
            success = self.catalog_manager.process_master_catalog_distribution(message)
            return {"type": "ACK", "status": "OK" if success else "ERROR"}
        
        elif msg_type == "GET_FILE_COPY":
            return self.file_handler.process_file_copy_request(message)
        
        elif msg_type == "FILE_COPY_RESPONSE":
            success = self.file_handler.process_file_copy_response(message)
            return {"type": "ACK", "status": "OK" if success else "ERROR"}
        
        elif msg_type == "UPDATE_FILE":
            return self.file_handler.process_update_file_request(message)
        
        else:
            return {"type": "ERROR", "message": f"Tipo de mensaje no reconocido: {msg_type}"}
    
    def run(self):
        """Bucle principal de procesamiento de mensajes del servidor."""
        print("Servidor iniciado. Presiona Ctrl+C para detener.")
        
        try:
            while True:
                # Escuchar mensajes
                encrypted_payload, client_addr = self.transport.listen()
                
                if encrypted_payload:
                    print(f"Mensaje recibido de {client_addr}")
                    
                    # En un sistema real, aquí se descifraría el payload
                    # Por ahora, asumimos que ya está descifrado
                    try:
                        message = encrypted_payload if isinstance(encrypted_payload, dict) else json.loads(encrypted_payload)
                        response = self.process_message(message, client_addr)
                        
                        if response:
                            # En un sistema real, aquí se cifraría la respuesta
                            self.transport.send_data(response, client_addr)
                            print(f"Respuesta enviada a {client_addr}")
                    
                    except Exception as e:
                        print(f"Error procesando mensaje: {e}")
                        error_response = {"type": "ERROR", "message": str(e)}
                        self.transport.send_data(error_response, client_addr)
        
        except KeyboardInterrupt:
            print("\nServidor detenido por el usuario")
        except Exception as e:
            print(f"Error en el servidor: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Libera recursos del sistema al cerrar el servidor."""
        print("Limpiando recursos...")
        # Aquí se cerrarían conexiones, se guardarían archivos, etc.
        print("Limpieza completada")

def main():
    """Función principal de entrada del servidor."""
    print("="*60)
    print("SISTEMA DE ARCHIVOS DISTRIBUIDO P2P")
    print("="*60)
    
    # Crear servidor
    server = DistributedFileServer()
    
    # Realizar bootstrap
    server.bootstrap_system()
    
    # Mostrar estado inicial
    server.catalog_manager.print_catalog_summary()
    server.file_handler.print_file_summary()
    
    # Iniciar servidor
    server.run()

if __name__ == "__main__":
    main()
