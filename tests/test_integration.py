# /tests/test_integration.py

import sys
import os

# Añade la carpeta raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.catalog_manager import CatalogManager
from src.core.file_handler import FileHandler

def test_integration():
    """Test de integración entre CatalogManager y FileHandler."""
    print("Iniciando test de integración...")
    
    # 1. Crear instancias de ambos componentes
    catalog = CatalogManager("server-A")
    file_handler = FileHandler("server-A")
    print("Componentes creados")
    
    # 2. Configurar archivos locales en ambos componentes
    file_handler.add_local_file("documento1.txt", "Contenido del documento 1")
    file_handler.add_local_file("datos.csv", "nombre,edad\nJuan,25")
    
    # Sincronizar con el catálogo
    for filename in file_handler.get_local_files_list():
        catalog.add_local_file(filename)
    
    print("Archivos locales configurados y sincronizados")
    
    # 3. Simular bootstrap del catálogo
    peers = [("192.168.1.100", 8080), ("192.168.1.101", 8080)]
    catalog.set_peer_addresses(peers)
    
    # Simular respuestas de peers
    peer_responses = [
        {
            "type": "CATALOG_INFO_RESPONSE",
            "server_id": "server-B",
            "files": ["reporte.pdf", "presentacion.pptx"]
        },
        {
            "type": "CATALOG_INFO_RESPONSE",
            "server_id": "server-C",
            "files": ["imagen.jpg", "video.mp4"]
        }
    ]
    
    for i, response in enumerate(peer_responses):
        catalog.process_catalog_response(response, peers[i])
    
    print("Catálogo bootstrap completado")
    
    # 4. Construir y distribuir catálogo maestro
    master_catalog = catalog.build_master_catalog()
    distribute_msg = catalog.get_distribute_catalog_message()
    catalog.process_master_catalog_distribution(distribute_msg)
    
    print("Catálogo maestro construido y distribuido")
    
    # 5. Simular operación de archivo: solicitar copia desde otro servidor
    print("\nSimulando operación de archivo...")
    
    # Buscar un archivo que esté en otro servidor
    target_file = "reporte.pdf"
    file_location = catalog.get_file_location(target_file)
    
    if file_location:
        print(f"Archivo {target_file} encontrado en {file_location}")
        
        # Crear solicitud de copia
        copy_request = file_handler.get_file_copy_request_message(target_file)
        print(f"Solicitud de copia creada: {copy_request['type']}")
        
        # Simular que el otro servidor responde con el archivo
        mock_response = {
            "type": "FILE_COPY_RESPONSE",
            "fileName": target_file,
            "content": "VGhpcyBpcyBhIG1vY2sgcmVwb3J0IGNvbnRlbnQ=",  # "This is a mock report content" in base64
            "timestamp": "2025-09-17 19:30:00",
            "serverId": file_location
        }
        
        # Procesar la respuesta
        success = file_handler.process_file_copy_response(mock_response)
        if success:
            print(f"Copia de {target_file} recibida exitosamente")
            
            # Confirmar el archivo temporal
            file_handler.commit_temp_file(target_file)
            catalog.add_local_file(target_file)
            print(f"Archivo {target_file} confirmado y añadido al catálogo")
    
    # 6. Mostrar estado final
    print("\nESTADO FINAL DEL SISTEMA:")
    catalog.print_catalog_summary()
    file_handler.print_file_summary()
    
    # 7. Verificar integridad
    local_files = file_handler.get_local_files_list()
    catalog_files = [f for f in catalog.local_files if catalog.get_file_location(f) == "server-A"]
    
    if set(local_files) == set(catalog_files):
        print("Integridad verificada: archivos locales sincronizados")
    else:
        print("Error de integridad: archivos locales no sincronizados")
    
    print("\nTest de integración completado exitosamente!")

if __name__ == "__main__":
    test_integration()
