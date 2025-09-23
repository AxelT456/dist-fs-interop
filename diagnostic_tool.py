# diagnostic_tool.py - Herramienta de diagnóstico del sistema
import socket
import json
import subprocess
import time
from typing import List, Tuple, Dict

def test_port(host: str, port: int, timeout: int = 3) -> bool:
    """Prueba si un puerto está abierto"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def test_udp_service(host: str, port: int, test_message: dict, timeout: int = 3) -> Tuple[bool, str]:
    """Prueba un servicio UDP enviando un mensaje de prueba"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        message = json.dumps(test_message).encode('utf-8')
        sock.sendto(message, (host, port))
        
        data, addr = sock.recvfrom(4096)
        response = json.loads(data.decode('utf-8'))
        
        sock.close()
        return True, str(response)
    except Exception as e:
        if 'sock' in locals():
            sock.close()
        return False, str(e)

def get_listening_ports() -> List[Tuple[str, int]]:
    """Obtiene lista de puertos que están escuchando"""
    try:
        # En Windows
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        listening_ports = []
        for line in lines:
            if 'LISTENING' in line or 'UDP' in line:
                parts = line.split()
                if len(parts) >= 2:
                    address = parts[1]
                    if ':' in address:
                        try:
                            host, port = address.rsplit(':', 1)
                            listening_ports.append((host, int(port)))
                        except ValueError:
                            continue
        
        return listening_ports
    except Exception as e:
        print(f"Error obteniendo puertos: {e}")
        return []

def diagnose_system():
    """Diagnóstica el estado completo del sistema expandido"""
    print("🔍 DIAGNÓSTICO DEL SISTEMA DISTRIBUIDO EXPANDIDO")
    print("=" * 60)
    
    # Definir componentes esperados expandidos
    components = [
        {
            "name": "DNS General",
            "host": "127.0.0.5",
            "port": 50005,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "DNS Original", 
            "host": "127.0.0.2",
            "port": 50000,
            "type": "UDP",
            "test_message": {"accion": "consultar", "nombre_archivo": "test"}
        },
        {
            "name": "DNS Christian",
            "host": "127.0.0.12",
            "port": 50000, 
            "type": "UDP",
            "test_message": {"type": "list"}
        },
        {
            "name": "DNS Marco",
            "host": "127.0.0.8",
            "port": 50000,
            "type": "UDP",
            "test_message": {"name": "test", "extension": "txt"}
        },
        {
            "name": "DNS Dan",
            "host": "127.0.0.9",
            "port": 50000,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "DNS Gus",
            "host": "127.0.0.10",
            "port": 50000,
            "type": "UDP",
            "test_message": {"action": "list_all_files"}
        },
        {
            "name": "Servidor 1",
            "host": "127.0.0.3",
            "port": 5002,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "Servidor 2",
            "host": "127.0.0.4", 
            "port": 5003,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "Servidor 3",
            "host": "127.0.0.6",
            "port": 5004,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "Servidor Marco",
            "host": "127.0.0.8",
            "port": 5005,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "Servidor Dan",
            "host": "127.0.0.9",
            "port": 5006,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        },
        {
            "name": "Servidor Gus",
            "host": "127.0.0.10",
            "port": 5007,
            "type": "UDP",
            "test_message": {"accion": "listar_archivos"}
        }
    ]
    
    print("\n📊 Estado de Componentes:")
    print("-" * 60)
    
    active_count = 0
    for comp in components:
        if comp["type"] == "UDP":
            is_active, response = test_udp_service(
                comp["host"], 
                comp["port"], 
                comp["test_message"]
            )
        else:
            is_active = test_port(comp["host"], comp["port"])
            response = "Puerto abierto" if is_active else "Puerto cerrado"
        
        status = "🟢 ACTIVO" if is_active else "🔴 INACTIVO"
        print(f"{status:12} {comp['name']:15} {comp['host']}:{comp['port']}")
        
        if is_active:
            active_count += 1
            print(f"             Respuesta: {response[:50]}...")
        else:
            print(f"             Error: {response[:50]}...")
        print()
    
    print(f"📈 Resumen: {active_count}/{len(components)} componentes activos")
    
    # Mostrar puertos activos en el sistema
    print("\n🔌 Puertos activos en localhost:")
    print("-" * 40)
    listening_ports = get_listening_ports()
    localhost_ports = [port for host, port in listening_ports if host.startswith('127.0.0') or host == '0.0.0.0']
    
    expected_ports = [comp['port'] for comp in components]
    
    for port in sorted(set(localhost_ports)):
        if port in expected_ports:
            comp_name = next((comp['name'] for comp in components if comp['port'] == port), 'Desconocido')
            print(f"  ✅ Puerto {port:5} - {comp_name}")
        elif port > 5000:  # Solo mostrar puertos relevantes
            print(f"  ❓ Puerto {port:5} - Servicio desconocido")
    
    # Recomendaciones
    print("\n💡 Recomendaciones:")
    print("-" * 30)
    
    if active_count == 0:
        print("❌ Ningún componente está activo")
        print("   1. Ejecuta: python system_launcher.py")
        print("   2. Selecciona opción 4: 'Iniciar sistema completo'")
        print("   3. Espera a que todos los componentes se inicien")
    elif active_count < len(components):
        print("⚠️  Sistema parcialmente activo")
        print("   • Revisa qué componentes faltan")
        print("   • Verifica que no haya conflictos de puertos")
        print("   • Reinicia los componentes faltantes")
    else:
        print("✅ Todos los componentes están activos")
        print("   • El sistema debería funcionar correctamente")
        print("   • Intenta conectar el cliente nuevamente")
    
    return active_count, len(components)

def quick_start_guide():
    """Muestra guía rápida de inicio para sistema expandido"""
    print("\n🚀 GUÍA RÁPIDA DE INICIO - SISTEMA EXPANDIDO")
    print("=" * 50)
    print("1. Abre una terminal y ejecuta:")
    print("   > python system_launcher.py")
    print()
    print("2. En el menú, selecciona:")
    print("   > 4 (Iniciar sistema completo)")
    print()
    print("3. El sistema iniciará en este orden:")
    print("   📡 DNS General (coordinador)")
    print("   🔗 5 DNS locales (Original, Christian, Marco, Dan, Gus)")
    print("   🖥️  6 Servidores distribuidos")
    print()
    print("4. Espera a ver el mensaje:")
    print("   ✅ Sistema completo iniciado")
    print()
    print("5. Luego selecciona:")
    print("   > 5 (Iniciar cliente distribuido)")
    print()
    print("6. En el cliente, usa:")
    print("   > 1 (Conectar aleatoriamente)")
    print()
    print("📊 SERVIDORES DISPONIBLES:")
    print("   • SERVER1 (127.0.0.3:5002) ← DNS Original")
    print("   • SERVER2 (127.0.0.4:5003) ← DNS Christian") 
    print("   • SERVER3 (127.0.0.6:5004) ← DNS Alternativo")
    print("   • SERVER_MARCO (127.0.0.8:5005) ← DNS Marco")
    print("   • SERVER_DAN (127.0.0.9:5006) ← DNS Dan")
    print("   • SERVER_GUS (127.0.0.10:5007) ← DNS Gus")
    print()
    print("El cliente se conectará aleatoriamente a uno de estos servidores")
    print("pero podrá acceder a archivos de todos los demás de forma transparente.")

def interactive_diagnosis():
    """Diagnóstico interactivo"""
    while True:
        print("\n" + "=" * 60)
        print("🔧 HERRAMIENTA DE DIAGNÓSTICO")
        print("=" * 60)
        print("1. 🔍 Diagnosticar sistema completo")
        print("2. 🧪 Probar componente específico") 
        print("3. 🔌 Ver puertos activos")
        print("4. 🚀 Guía de inicio rápido")
        print("5. 🛠️  Crear archivos de prueba")
        print("0. 🚪 Salir")
        print("=" * 60)
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == "1":
            active, total = diagnose_system()
            input("\nPresiona Enter para continuar...")
            
        elif opcion == "2":
            print("\nComponentes disponibles:")
            components = [
                ("DNS General", "127.0.0.5", 50005),
                ("DNS Original", "127.0.0.2", 50000),
                ("Servidor 1", "127.0.0.3", 5002)
            ]
            
            for i, (name, host, port) in enumerate(components, 1):
                print(f"  {i}. {name} ({host}:{port})")
            
            try:
                idx = int(input("Selecciona componente (número): ")) - 1
                if 0 <= idx < len(components):
                    name, host, port = components[idx]
                    is_active, response = test_udp_service(host, port, {"accion": "test"})
                    status = "ACTIVO" if is_active else "INACTIVO" 
                    print(f"\n{name}: {status}")
                    print(f"Respuesta: {response}")
            except (ValueError, IndexError):
                print("Selección inválida")
            
            input("\nPresiona Enter para continuar...")
            
        elif opcion == "3":
            print("\n🔌 Puertos activos:")
            ports = get_listening_ports()
            for host, port in sorted(set(ports)):
                if host.startswith('127.0.0') or host == '0.0.0.0':
                    print(f"  {host}:{port}")
            input("\nPresiona Enter para continuar...")
            
        elif opcion == "4":
            quick_start_guide()
            input("\nPresiona Enter para continuar...")
            
        elif opcion == "5":
            create_test_files()
            input("\nPresiona Enter para continuar...")
            
        elif opcion == "0":
            print("👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción inválida")

def create_test_files():
    """Crea archivos de prueba en los directorios del sistema expandido"""
    import os
    
    print("\n📁 Creando archivos de prueba para sistema expandido...")
    
    directories = [
        "archivos_server1", "archivos_server2", "archivos_server3",
        "archivos_server_marco", "archivos_server_dan", "archivos_server_gus"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Directorio creado: {directory}")
    
    test_files = {
        # Servidor 1
        "archivos_server1/libro1.txt": "Este es el contenido del Libro 1.\nUna historia fascinante sobre aventuras.",
        "archivos_server1/manual.txt": "Manual de usuario.\nInstrucciones detalladas paso a paso.",
        
        # Servidor 2  
        "archivos_server2/libro2.txt": "Contenido del Libro 2.\nCiencia ficción y tecnología avanzada.", 
        "archivos_server2/guia.txt": "Guía completa.\nEjemplos prácticos para principiantes.",
        
        # Servidor 3
        "archivos_server3/libro3.txt": "El Libro 3 contiene.\nRomance y drama en la época victoriana.",
        "archivos_server3/tutorial.txt": "Tutorial básico.\nConceptos fundamentales explicados.",
        
        # Servidor Marco
        "archivos_server_marco/filosofia.txt": "Reflexiones filosóficas sobre la existencia.\nEl tiempo y el espacio en la mente humana.",
        "archivos_server_marco/poesia.txt": "Colección de poemas.\nSobre la naturaleza y el alma humana.",
        
        # Servidor Dan
        "archivos_server_dan/algoritmos.txt": "Guía completa de algoritmos.\nEstructuras de datos avanzadas y optimización.",
        "archivos_server_dan/programacion.txt": "Manual de programación.\nBuenas prácticas y patrones de diseño.",
        
        # Servidor Gus
        "archivos_server_gus/historia.txt": "Relatos históricos fascinantes.\nCivilizaciones antiguas y sus legados.",
        "archivos_server_gus/biografias.txt": "Biografías de personajes ilustres.\nVidas que cambiaron el curso de la historia."
    }
    
    for filepath, content in test_files.items():
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"📄 Archivo creado: {filepath}")
        except Exception as e:
            print(f"❌ Error creando {filepath}: {e}")
    
    print(f"\n✅ {len(test_files)} archivos de prueba creados en 6 servidores")
    print("Cada servidor tiene 2 archivos únicos para probar la distribución.")

if __name__ == "__main__":
    print("🔧 Herramienta de Diagnóstico del Sistema Distribuido")
    print("Esta herramienta te ayuda a identificar problemas de conectividad")
    print()
    
    interactive_diagnosis()