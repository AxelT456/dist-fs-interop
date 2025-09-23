# /tests/test_catalog_manager.py

import sys
import os

# Añade la carpeta raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.catalog_manager import CatalogManager

def test_catalog_manager():
    """Test básico del CatalogManager."""
    print("Iniciando test del CatalogManager...")
    
    # 1. Crear instancia del catalog manager
    catalog = CatalogManager("server-A")
    print("CatalogManager creado")
    
    # 2. Añadir archivos locales
    catalog.add_local_file("documento1.txt")
    catalog.add_local_file("imagen.jpg")
    catalog.add_local_file("datos.csv")
    print("Archivos locales añadidos")
    
    # 3. Configurar peers
    peers = [("192.168.1.100", 8080), ("192.168.1.101", 8080)]
    catalog.set_peer_addresses(peers)
    print("Peers configurados")
    
    # 4. Crear mensaje de bootstrap
    bootstrap_msg = catalog.get_bootstrap_message()
    print(f"Mensaje de bootstrap: {bootstrap_msg}")
    
    # 5. Simular respuesta de catálogo de otro servidor
    peer_response = {
        "type": "CATALOG_INFO_RESPONSE",
        "server_id": "server-B",
        "files": ["reporte.pdf", "presentacion.pptx"]
    }
    
    success = catalog.process_catalog_response(peer_response, ("192.168.1.100", 8080))
    print(f"Respuesta de peer procesada: {success}")
    
    # 6. Construir catálogo maestro
    master_catalog = catalog.build_master_catalog()
    print(f"Catálogo maestro construido: {len(master_catalog)} archivos")
    
    # 7. Crear mensaje de distribución
    distribute_msg = catalog.get_distribute_catalog_message()
    print(f"Mensaje de distribución creado")
    
    # 8. Simular recepción de catálogo maestro
    catalog.process_master_catalog_distribution(distribute_msg)
    print("Catálogo maestro procesado")
    
    # 9. Buscar ubicación de archivo
    location = catalog.get_file_location("documento1.txt")
    print(f"Ubicación de documento1.txt: {location}")
    
    # 10. Mostrar estado del catálogo
    status = catalog.get_catalog_status()
    print(f"Estado del catálogo: {status['master_catalog_size']} archivos totales")
    
    # 11. Mostrar resumen
    catalog.print_catalog_summary()
    
    print("\nTest del CatalogManager completado exitosamente!")

if __name__ == "__main__":
    test_catalog_manager()
