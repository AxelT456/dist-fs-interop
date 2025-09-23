# system_launcher.py - Lanzador coordinado del sistema distribuido
import os
import sys
import time
import subprocess
import threading
from typing import List, Dict

def crear_directorios():
    """Crea los directorios necesarios para el sistema expandido"""
    directorios = [
        "archivos_server1",
        "archivos_server2", 
        "archivos_server3",
        "archivos_server_marco",
        "archivos_server_dan", 
        "archivos_server_gus",
        "src/network/dns_translator"
    ]
    
    for directorio in directorios:
        if not os.path.exists(directorio):
            os.makedirs(directorio)
            print(f"✅ Directorio creado: {directorio}")
    
    # Crear archivos de ejemplo en todos los servidores
    archivos_ejemplo = {
        "archivos_server1/libro1.txt": "Contenido del Libro 1 - Una historia fascinante sobre aventuras.",
        "archivos_server1/novela.txt": "Novela épica con personajes memorables y tramas complejas.",
        "archivos_server2/libro2.txt": "Contenido del Libro 2 - Ciencia ficción y tecnología avanzada.",
        "archivos_server2/manual.txt": "Manual técnico con instrucciones detalladas paso a paso.",
        "archivos_server3/libro3.txt": "Contenido del Libro 3 - Romance y drama en la época victoriana.",
        "archivos_server3/guia.txt": "Guía completa para principiantes con ejemplos prácticos.",
        "archivos_server_marco/filosofia.txt": "Reflexiones filosóficas sobre la existencia y el tiempo.",
        "archivos_server_marco/poesia.txt": "Colección de poemas sobre la naturaleza humana.",
        "archivos_server_dan/algoritmos.txt": "Guía completa de algoritmos y estructuras de datos.",
        "archivos_server_dan/programacion.txt": "Manual de buenas prácticas en programación.",
        "archivos_server_gus/historia.txt": "Relatos históricos de civilizaciones antiguas.",
        "archivos_server_gus/biografias.txt": "Biografías de personajes ilustres de la historia."
    }
    
    for archivo, contenido in archivos_ejemplo.items():
        if not os.path.exists(archivo):
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)
            print(f"📄 Archivo creado: {archivo}")

def mostrar_menu_principal():
    """Muestra el menú principal del sistema"""
    print("\n" + "="*60)
    print("SISTEMA DISTRIBUIDO DE GESTIÓN DE LIBROS")
    print("="*60)
    print("🏗️  INFRAESTRUCTURA:")
    print("  1. 🗂️  Iniciar DNS General (Coordinador)")
    print("  2. 🔗 Iniciar todos los DNS locales")
    print("  3. 🖥️  Iniciar todos los servidores")
    print("  4. 🚀 Iniciar sistema completo (DNS + Servidores)")
    print()
    print("👤 CLIENTES:")
    print("  5. 📱 Iniciar cliente distribuido")
    print()
    print("🔧 UTILIDADES:")
    print("  6. 📊 Estado del sistema")
    print("  7. 🧪 Probar conectividad")
    print("  8. 📁 Crear directorios y archivos de ejemplo")
    print("  9. 🛑 Detener todos los procesos")
    print("  0. 🚪 Salir")
    print("="*60)

def ejecutar_componente(comando: List[str], nombre: str, delay: float = 0):
    """Ejecuta un componente del sistema"""
    if delay > 0:
        time.sleep(delay)
    
    try:
        print(f"🚀 Iniciando {nombre}...")
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proceso
    except Exception as e:
        print(f"❌ Error iniciando {nombre}: {e}")
        return None

def iniciar_dns_general():
    """Inicia el DNS General"""
    comando = [sys.executable, "dns_general.py"]
    return ejecutar_componente(comando, "DNS General")

def iniciar_dns_locales():
    """Inicia todos los DNS locales expandido"""
    procesos = []
    
    # DNS 1 (Servidor Nombres Original)
    comando1 = [sys.executable, "servidor_nombres.py"]
    proc1 = ejecutar_componente(comando1, "DNS Local 1 (127.0.0.2:50000)", 0)
    if proc1:
        procesos.append(("DNS Local 1", proc1))
    
    # DNS 2 (Christian)  
    comando2 = [sys.executable, "servidor_christian.py"]
    proc2 = ejecutar_componente(comando2, "DNS Local 2 (127.0.0.12:50000)", 1)
    if proc2:
        procesos.append(("DNS Local 2", proc2))
    
    # DNS Marco
    comando_marco = [sys.executable, "servidor_marco.py"]
    proc_marco = ejecutar_componente(comando_marco, "DNS Marco (127.0.0.8:50000)", 2)
    if proc_marco:
        procesos.append(("DNS Marco", proc_marco))
    
    # DNS Dan
    comando_dan = [sys.executable, "servidor_dan.py", "--folder", "archivos_server_dan", "--server-ip", "127.0.0.9", "--server-port", "5006"]
    proc_dan = ejecutar_componente(comando_dan, "DNS Dan (127.0.0.9:50000)", 3)
    if proc_dan:
        procesos.append(("DNS Dan", proc_dan))
    
    # DNS Gus
    comando_gus = [sys.executable, "servidor_gus.py"]
    proc_gus = ejecutar_componente(comando_gus, "DNS Gus (127.0.0.10:50000)", 4)
    if proc_gus:
        procesos.append(("DNS Gus", proc_gus))
    
    # DNS 3 (Alternativo)
    print("⚠️  DNS Local 3 (Alternativo) no configurado - usando otros DNS")
    
    return procesos

def iniciar_servidores():
    """Inicia todos los servidores distribuidos expandido"""
    procesos = []
    
    # Servidor 1
    comando1 = [sys.executable, "server_distributed.py", "server1"]
    proc1 = ejecutar_componente(comando1, "Servidor 1 (127.0.0.3:5002)", 2)
    if proc1:
        procesos.append(("Servidor 1", proc1))
    
    # Servidor 2
    comando2 = [sys.executable, "server_distributed.py", "server2"] 
    proc2 = ejecutar_componente(comando2, "Servidor 2 (127.0.0.4:5003)", 3)
    if proc2:
        procesos.append(("Servidor 2", proc2))
    
    # Servidor 3
    comando3 = [sys.executable, "server_distributed.py", "server3"]
    proc3 = ejecutar_componente(comando3, "Servidor 3 (127.0.0.6:5004)", 4)
    if proc3:
        procesos.append(("Servidor 3", proc3))
    
    # Servidor Marco
    comando_marco = [sys.executable, "server_distributed.py", "server_marco"]
    proc_marco = ejecutar_componente(comando_marco, "Servidor Marco (127.0.0.8:5005)", 5)
    if proc_marco:
        procesos.append(("Servidor Marco", proc_marco))
    
    # Servidor Dan
    comando_dan = [sys.executable, "server_distributed.py", "server_dan"]
    proc_dan = ejecutar_componente(comando_dan, "Servidor Dan (127.0.0.9:5006)", 6)
    if proc_dan:
        procesos.append(("Servidor Dan", proc_dan))
    
    # Servidor Gus
    comando_gus = [sys.executable, "server_distributed.py", "server_gus"]
    proc_gus = ejecutar_componente(comando_gus, "Servidor Gus (127.0.0.10:5007)", 7)
    if proc_gus:
        procesos.append(("Servidor Gus", proc_gus))
    
    return procesos

def iniciar_cliente():
    """Inicia el cliente distribuido"""
    comando = [sys.executable, "client_distributed.py"]
    return ejecutar_componente(comando, "Cliente Distribuido")

def probar_conectividad():
    """Prueba la conectividad del sistema"""
    print("\n🔍 Probando conectividad del sistema...")
    
    try:
        # Importar el traductor para pruebas
        sys.path.append('src/network/dns_translator')
        from translator_integrated import create_translator_for_client
        
        translator = create_translator_for_client()
        results = translator.test_connectivity()
        
        print("\n📊 Resultados de conectividad:")
        for dns_id, status in results.items():
            estado = "🟢" if status["status"] == "connected" else "🔴"
            print(f"  {estado} {dns_id}: {status['status']}")
            
    except Exception as e:
        print(f"❌ Error probando conectividad: {e}")
        print("💡 Asegúrate de que el sistema esté iniciado")

def mostrar_estado_sistema():
    """Muestra el estado actual del sistema distribuido expandido"""
    print("\n📊 Estado del Sistema Distribuido Expandido")
    print("-" * 50)
    
    componentes = [
        ("DNS General", "127.0.0.5", 50005),
        ("DNS Local 1", "127.0.0.2", 50000),
        ("DNS Local 2", "127.0.0.12", 50000),
        ("DNS Marco", "127.0.0.8", 50000),
        ("DNS Dan", "127.0.0.9", 50000),
        ("DNS Gus", "127.0.0.10", 50000),
        ("Servidor 1", "127.0.0.3", 5002),
        ("Servidor 2", "127.0.0.4", 5003),
        ("Servidor 3", "127.0.0.6", 5004),
        ("Servidor Marco", "127.0.0.8", 5005),
        ("Servidor Dan", "127.0.0.9", 5006),
        ("Servidor Gus", "127.0.0.10", 5007),
    ]
    
    import socket
    
    for nombre, ip, puerto in componentes:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.bind(('localhost', 0))
            sock.sendto(b'ping', (ip, puerto))
            sock.settimeout(1)
            data, addr = sock.recvfrom(100)
            estado = "🟢 Activo"
        except:
            estado = "🔴 Inactivo"
        finally:
            sock.close()
        
        print(f"  {estado} {nombre:15} {ip:15}:{puerto}")

# Lista global de procesos activos
procesos_activos = []

def manejar_procesos():
    """Maneja el ciclo de vida de los procesos"""
    global procesos_activos
    
    while True:
        mostrar_menu_principal()
        opcion = input("\nSelecciona una opción (0-9): ").strip()
        
        if opcion == "1":
            proc = iniciar_dns_general()
            if proc:
                procesos_activos.append(("DNS General", proc))
                print("✅ DNS General iniciado")
                time.sleep(2)
        
        elif opcion == "2":
            procs = iniciar_dns_locales()
            procesos_activos.extend(procs)
            print(f"✅ {len(procs)} DNS locales iniciados")
            time.sleep(2)
        
        elif opcion == "3":
            procs = iniciar_servidores()
            procesos_activos.extend(procs)
            print(f"✅ {len(procs)} servidores iniciados")
            time.sleep(3)
        
        elif opcion == "4":
            print("🚀 Iniciando sistema completo...")
            
            # DNS General primero
            proc_dns_general = iniciar_dns_general()
            if proc_dns_general:
                procesos_activos.append(("DNS General", proc_dns_general))
                time.sleep(2)
            
            # DNS locales
            procs_dns = iniciar_dns_locales()
            procesos_activos.extend(procs_dns)
            time.sleep(3)
            
            # Servidores
            procs_servers = iniciar_servidores()
            procesos_activos.extend(procs_servers)
            
            print("✅ Sistema completo iniciado")
            print("⏳ Esperando 5 segundos para estabilización...")
            time.sleep(5)
            
            # Mostrar estado
            mostrar_estado_sistema()
        
        elif opcion == "5":
            if not procesos_activos:
                print("⚠️  Se recomienda iniciar el sistema primero (opción 4)")
                continuar = input("¿Continuar de todos modos? (s/n): ")
                if continuar.lower() != 's':
                    continue
            
            print("🚀 Iniciando cliente...")
            cliente_proc = iniciar_cliente()
            if cliente_proc:
                print("✅ Cliente iniciado")
                # El cliente maneja su propia interacción
                cliente_proc.wait()
        
        elif opcion == "6":
            mostrar_estado_sistema()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == "7":
            probar_conectividad()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == "8":
            crear_directorios()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == "9":
            print("🛑 Deteniendo todos los procesos...")
            for nombre, proc in procesos_activos:
                try:
                    proc.terminate()
                    print(f"  🔴 {nombre} detenido")
                except:
                    pass
            procesos_activos.clear()
            print("✅ Todos los procesos detenidos")
            time.sleep(2)
        
        elif opcion == "0":
            print("🛑 Deteniendo sistema...")
            for nombre, proc in procesos_activos:
                try:
                    proc.terminate()
                except:
                    pass
            print("👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción no válida")
            time.sleep(1)

if __name__ == "__main__":
    print("🎯 Lanzador del Sistema Distribuido de Gestión de Libros")
    print("📋 Este script coordina todos los componentes del sistema")
    print()
    
    # Crear directorios iniciales
    crear_directorios()
    
    try:
        manejar_procesos()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por el usuario")
        print("🛑 Deteniendo procesos...")
        for nombre, proc in procesos_activos:
            try:
                proc.terminate()
            except:
                pass
        print("👋 Sistema detenido")