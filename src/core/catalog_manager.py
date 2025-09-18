# /src/core/catalog_manager.py
import json
import time
from typing import Dict, List, Optional, Tuple

class CatalogManager:
    """
    Gestiona el catálogo maestro de archivos distribuidos.
    Implementa la sincronización de catálogos entre servidores P2P.
    """
    
    def __init__(self, server_id: str):
        self.server_id = server_id
        self.master_catalog = {}  # Mapeo de archivos a servidores
        self.local_files = []     # Archivos almacenados localmente
        self.peer_addresses = []  # Direcciones de otros servidores en la red
        self.catalog_initialized = False
        
    def add_local_file(self, filename: str):
        """Registra un archivo como disponible localmente."""
        if filename not in self.local_files:
            self.local_files.append(filename)
            print(f"[Catalog] Archivo local añadido: {filename}")
    
    def remove_local_file(self, filename: str):
        """Elimina un archivo de la lista de archivos locales."""
        if filename in self.local_files:
            self.local_files.remove(filename)
            print(f"[Catalog] Archivo local removido: {filename}")
    
    def set_peer_addresses(self, addresses: List[Tuple[str, int]]):
        """Configura las direcciones de los servidores peers en la red."""
        self.peer_addresses = addresses
        print(f"[Catalog] Peers configurados: {len(addresses)} servidores")
    
    def get_local_catalog_info(self) -> Dict:
        """
        Genera la respuesta con la lista de archivos locales.
        """
        return {
            "type": "CATALOG_INFO_RESPONSE",
            "server_id": self.server_id,
            "files": self.local_files.copy()
        }
    
    def process_catalog_response(self, response: Dict, peer_address: Tuple[str, int]) -> bool:
        """
        Procesa la información de catálogo recibida de otro servidor.
        Actualiza el catálogo maestro con los archivos del peer.
        """
        try:
            if response.get("type") != "CATALOG_INFO_RESPONSE":
                return False
            
            peer_id = response.get("server_id", f"{peer_address[0]}:{peer_address[1]}")
            files = response.get("files", [])
            
            # Agregar archivos del peer al catálogo maestro
            for filename in files:
                self.master_catalog[filename] = peer_id
            
            print(f"[Catalog] Catálogo actualizado desde {peer_id}: {len(files)} archivos")
            return True
            
        except Exception as e:
            print(f"[Catalog] Error procesando respuesta de catálogo: {e}")
            return False
    
    def build_master_catalog(self) -> Dict:
        """
        Construye el catálogo maestro agregando archivos locales.
        """
        # Registrar archivos locales en el catálogo maestro
        for filename in self.local_files:
            self.master_catalog[filename] = self.server_id
        
        print(f"[Catalog] Catálogo maestro construido: {len(self.master_catalog)} archivos")
        return self.master_catalog.copy()
    
    def get_distribute_catalog_message(self) -> Dict:
        """
        Genera el mensaje para enviar el catálogo maestro a otros servidores.
        """
        return {
            "type": "DISTRIBUTE_MASTER_CATALOG",
            "catalog": self.master_catalog.copy(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def process_master_catalog_distribution(self, message: Dict) -> bool:
        """
        Procesa el catálogo maestro recibido de otro servidor.
        """
        try:
            if message.get("type") != "DISTRIBUTE_MASTER_CATALOG":
                return False
            
            new_catalog = message.get("catalog", {})
            timestamp = message.get("timestamp", "unknown")
            
            # Sincronizar con el catálogo maestro recibido
            self.master_catalog.update(new_catalog)
            self.catalog_initialized = True
            
            print(f"[Catalog] Catálogo maestro recibido ({timestamp}): {len(new_catalog)} archivos")
            return True
            
        except Exception as e:
            print(f"[Catalog] Error procesando distribución de catálogo: {e}")
            return False
    
    def get_file_location(self, filename: str) -> Optional[str]:
        """
        Busca en qué servidor está almacenado un archivo específico.
        """
        return self.master_catalog.get(filename)
    
    def get_catalog_status(self) -> Dict:
        """
        Obtiene el estado actual del catálogo para monitoreo.
        """
        return {
            "server_id": self.server_id,
            "local_files_count": len(self.local_files),
            "master_catalog_size": len(self.master_catalog),
            "peers_count": len(self.peer_addresses),
            "initialized": self.catalog_initialized,
            "local_files": self.local_files.copy(),
            "master_catalog": self.master_catalog.copy()
        }
    
    def get_bootstrap_message(self) -> Dict:
        """
        Genera el mensaje de solicitud de catálogo para otros servidores.
        """
        return {
            "type": "GET_CATALOG_INFO",
            "server_id": self.server_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def is_catalog_ready(self) -> bool:
        """
        Verifica si el catálogo está completamente inicializado.
        """
        return self.catalog_initialized and len(self.master_catalog) > 0
    
    def print_catalog_summary(self):
        """
        Muestra un resumen del estado actual del catálogo.
        """
        print("\n" + "="*50)
        print("RESUMEN DEL CATÁLOGO")
        print("="*50)
        print(f"Servidor: {self.server_id}")
        print(f"Archivos locales: {len(self.local_files)}")
        print(f"Total archivos en red: {len(self.master_catalog)}")
        print(f"Peers conocidos: {len(self.peer_addresses)}")
        print(f"Estado: {'Listo' if self.is_catalog_ready() else 'Inicializando'}")
        
        if self.local_files:
            print(f"\nArchivos locales:")
            for file in self.local_files:
                print(f"  - {file}")
        
        if self.master_catalog:
            print(f"\nDistribución de archivos:")
            for filename, server in self.master_catalog.items():
                print(f"  - {filename} → {server}")
        
        print("="*50)
