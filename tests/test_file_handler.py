# /tests/test_file_handler.py

import sys
import os

# Añade la carpeta raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.file_handler import FileHandler

def test_file_handler():
    """Test básico del FileHandler."""
    print("Iniciando test del FileHandler...")
    
    # 1. Crear instancia del file handler
    file_handler = FileHandler("server-A")
    print("FileHandler creado")
    
    # 2. Añadir archivos locales
    file_handler.add_local_file("documento1.txt", "Contenido del documento 1")
    file_handler.add_local_file("datos.csv", "nombre,edad\nJuan,25\nMaría,30")
    print("Archivos locales añadidos")
    
    # 3. Crear mensaje de solicitud de copia
    copy_request = file_handler.get_file_copy_request_message("documento1.txt")
    print(f"Mensaje de solicitud de copia: {copy_request['type']}")
    
    # 4. Simular procesamiento de solicitud de copia
    copy_response = file_handler.process_file_copy_request(copy_request)
    if copy_response:
        print(f"Respuesta de copia generada: {copy_response['type']}")
    else:
        print("No se pudo generar respuesta de copia")
    
    # 5. Simular recepción de copia de archivo
    if copy_response:
        success = file_handler.process_file_copy_response(copy_response)
        print(f"Copia de archivo procesada: {success}")
    
    # 6. Crear mensaje de actualización de archivo
    update_msg = file_handler.get_update_file_message("documento1.txt", "Contenido actualizado del documento 1")
    print(f"Mensaje de actualización creado: {update_msg['type']}")
    
    # 7. Simular procesamiento de actualización
    update_response = file_handler.process_update_file_request(update_msg)
    print(f"Actualización procesada: {update_response['status']}")
    
    # 8. Confirmar archivo temporal
    if file_handler.get_temp_files_list():
        temp_file = file_handler.get_temp_files_list()[0]
        success = file_handler.commit_temp_file(temp_file)
        print(f"Archivo temporal confirmado: {success}")
    
    # 9. Mostrar estado de archivos
    status = file_handler.get_file_status()
    print(f"Estado de archivos: {status['local_files_count']} locales, {status['temp_files_count']} temporales")
    
    # 10. Mostrar resumen
    file_handler.print_file_summary()
    
    print("\nTest del FileHandler completado exitosamente!")

if __name__ == "__main__":
    test_file_handler()
