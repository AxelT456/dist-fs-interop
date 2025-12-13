# client_distributed.py (Refactorizado)

import os
import sys
from prompt_toolkit import prompt

# Añadir la raíz del proyecto al path para poder importar la nueva lógica
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.client_logic import ClientLogic, DNS_SERVERS

def main_menu():
    """Maneja la interfaz de usuario en la terminal."""
    client = ClientLogic()
    
    while True:
        print("\n" + "="*60)
        print("SISTEMA DISTRIBUIDO DE GESTIÓN DE LIBROS")
        print("="*60)
        if client.is_connected:
            print(f"🔐 Conectado: {client.server_info[0]}:{client.server_info[1]}")
            print(f"📡 DNS usado: {client.dns_info['description']}")
        else:
            print("🔌 Desconectado")
        print("="*60)
        print("1. 🔗 Conectar aleatoriamente")
        print("2. 📚 Ver libros disponibles")
        print("3. 👁️  Leer libro")
        print("4. ✏️  Escribir/Crear libro")
        print("5. 📋 Consultar ubicación de libro")
        print("6. 🚪 Salir y desconectar")
        print("="*60)
        
        option = input("Selecciona una opción (1-6): ").strip()
        
        if option == "1":
            print("\nConectando a un servidor aleatorio...")
            success, message = client.connect_randomly()
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        
        elif option == "2": # Listar
            if not client.is_connected:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
            
            response = client.get_file_list()
            if response.get("status") == "ACK":
                files = response.get("archivos", [])
                print(f"\n📚 Libros disponibles ({len(files)}):")
                print("-" * 40)
                for file_info in files:
                    print(f"- {file_info.get('nombre_archivo', 'N/A')}")
                print("-" * 40)
            else:
                print(f"❌ {response.get('mensaje', 'Error desconocido')}")

        elif option == "3": # Leer
            if not client.is_connected:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
            
            filename = input("Nombre del libro a leer: ").strip()
            response = client.read_file(filename)
            if response.get("status") == "EXITO":
                print(f"\n📖 Contenido de '{filename}':")
                print("-" * 50)
                print(response.get("contenido", ""))
                print("-" * 50)
            else:
                print(f"❌ {response.get('mensaje', 'No se pudo leer el libro')}")

        elif option == "4": # Escribir
            if not client.is_connected:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
            
            filename = input("Nombre del libro a escribir/crear: ").strip()
            # Opcionalmente, mostrar contenido actual
            current_content_resp = client.read_file(filename)
            current_content = current_content_resp.get("contenido", "")
            
            print(f"\n📝 Editando '{filename}' (Esc+Enter para guardar):")
            new_content = prompt("", default=current_content, multiline=True)
            
            response = client.write_file(filename, new_content.strip())
            if response.get("status") == "EXITO":
                print(f"✅ {response.get('mensaje', 'Libro guardado con éxito')}")
            else:
                print(f"❌ {response.get('mensaje', 'No se pudo guardar el libro')}")

        elif option == "5": # Consultar
            if not client.is_connected:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
            
            filename = input("Nombre del libro a consultar: ").strip()
            response = client.get_file_info(filename)
            if response.get("status") == "ACK":
                print(f"✅ Libro encontrado:")
                print(f"  - Ubicación: {response.get('server_id', 'Local')}")
                print(f"  - IP: {response.get('ip')}:{response.get('puerto')}")
            else:
                print(f"❌ {response.get('mensaje', 'Libro no encontrado')}")

        elif option == "6":
            client.disconnect()
            print("👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    print("=== Cliente del Sistema Distribuido ===")
    print("DNS disponibles:")
    for dns in DNS_SERVERS:
        print(f"  - {dns['description']}")
    print()
    
    main_menu()