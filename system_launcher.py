# system_launcher.py - Lanzador coordinado del sistema distribuido (Refactorizado)
import os
import sys
import time
import subprocess
import threading
from typing import List, Dict

# Nombre del script unificado de DNS Local
DNS_LOCAL_SCRIPT = "dns_local_service.py"

def crear_directorios():
    """Crea los directorios necesarios para el sistema."""
    # IDs tomados de network_config.json para generar carpetas consistentes
    ids_servidores = ["SERVER1", "server_christian", "SERVER_MARCO", "server_dan", "server_gus"]
    
    directorios = [f"archivos_{pid.lower()}" for pid in ids_servidores]
    directorios.append("src/network/dns_translator")
    
    for directorio in directorios:
        if not os.path.exists(directorio):
            os.makedirs(directorio)
            print(f"✅ Directorio verificado/creado: {directorio}")

def mostrar_menu_principal():
    """Muestra el menú principal del sistema"""
    print("\n" + "="*60)
    print("SISTEMA DISTRIBUIDO DE GESTIÓN DE LIBROS (VERSIÓN LIMPIA)")
    print("="*60)
    print("🏗️  INFRAESTRUCTURA:")
    print("  1. 🗂️  Iniciar DNS General (Coordinador)")
    print("  2. 🔗 Iniciar todos los DNS locales (Servicio Unificado)")
    print("  3. 🖥️  Iniciar todos los servidores de Archivos")
    print("  4. 🚀 Iniciar sistema completo (Recomendado)")
    print()
    print("👤 CLIENTES:")
    print("  5. 📱 Iniciar cliente distribuido")
    print()
    print("🔧 UTILIDADES:")
    print("  6. 📊 Estado del sistema")
    print("  7. 📁 Crear directorios base")
    print("  8. 🛑 Detener todos los procesos")
    print("  0. 🚪 Salir")
    print("="*60)

def ejecutar_componente(comando: List[str], nombre: str, delay: float = 0):
    """Ejecuta un componente del sistema de forma no bloqueante"""
    if delay > 0:
        time.sleep(delay)
    
    try:
        print(f"🚀 Iniciando {nombre}...")
        # Creationflags para nueva ventana en Windows (opcional, ayuda a depurar)
        creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        
        proceso = subprocess.Popen(
            comando,
            # stdout=subprocess.PIPE, # Descomentar para ocultar logs en consola principal
            # stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags
        )
        return proceso
    except Exception as e:
        print(f"❌ Error iniciando {nombre}: {e}")
        return None

def iniciar_dns_general():
    return ejecutar_componente([sys.executable, "dns_general.py"], "DNS General")

def iniciar_dns_locales():
    """Inicia instancias del servicio DNS Local unificado"""
    procesos = []
    
    # Mapeo de IDs según network_config.json
    # (ID_CONFIG, NOMBRE_VISUAL, PUERTO_VISUAL)
    peers = [
        ("SERVER1", "DNS Local 1", 50000),
        ("server_christian", "DNS Christian", 50003),
        ("SERVER_MARCO", "DNS Marco", 50001),
        ("server_dan", "DNS Dan", 50004),
        ("server_gus", "DNS Gus", 50002)
    ]
    
    for i, (peer_id, nombre, puerto) in enumerate(peers):
        # Llamamos siempre al MISMO script, pero cambiamos el argumento
        cmd = [sys.executable, DNS_LOCAL_SCRIPT, peer_id]
        proc = ejecutar_componente(cmd, f"{nombre} ({puerto})", delay=0.5 * i)
        if proc:
            procesos.append((nombre, proc))
            
    return procesos

def iniciar_servidores():
    """Inicia los servidores de archivos distribuidos"""
    procesos = []
    
    peers = [
        ("server1", "Servidor 1", 5002),
        ("server2", "Servidor 2", 5003), # Nota: server2 usa config de server_christian en tu lógica original? Revisar mapeo.
        ("server_marco", "Servidor Marco", 5005),
        ("server_dan", "Servidor Dan", 5006),
        ("server_gus", "Servidor Gus", 5007)
    ]
    
    for i, (srv_arg, nombre, puerto) in enumerate(peers):
        cmd = [sys.executable, "server_distributed.py", srv_arg]
        proc = ejecutar_componente(cmd, f"{nombre} ({puerto})", delay=1 + (0.5 * i))
        if proc:
            procesos.append((nombre, proc))
    
    return procesos

def iniciar_cliente():
    return ejecutar_componente([sys.executable, "src/client_distributed.py"], "Cliente CLI")

# --- Gestión de Procesos ---
procesos_activos = []

def detener_todo():
    print("🛑 Deteniendo todos los procesos...")
    for nombre, proc in procesos_activos:
        try:
            proc.terminate()
            if sys.platform != 'win32':
                proc.kill()
        except:
            pass
    procesos_activos.clear()
    print("✅ Todos los procesos detenidos")

def main():
    crear_directorios()
    
    try:
        while True:
            mostrar_menu_principal()
            opcion = input("\nOpción: ").strip()
            
            if opcion == "1":
                p = iniciar_dns_general()
                if p: procesos_activos.append(("DNS General", p))
            
            elif opcion == "2":
                procesos_activos.extend(iniciar_dns_locales())
            
            elif opcion == "3":
                procesos_activos.extend(iniciar_servidores())
            
            elif opcion == "4":
                print("🚀 Iniciando secuencia completa...")
                p_gen = iniciar_dns_general()
                if p_gen: procesos_activos.append(("DNS General", p_gen))
                time.sleep(2)
                
                procesos_activos.extend(iniciar_dns_locales())
                time.sleep(3)
                
                procesos_activos.extend(iniciar_servidores())
                print("\n✅ Sistema completo iniciado.")
                
            elif opcion == "5":
                p = iniciar_cliente()
                if p: p.wait() # El cliente bloquea la terminal hasta que se cierra
                
            elif opcion == "8":
                detener_todo()
                
            elif opcion == "0":
                detener_todo()
                break
                
    except KeyboardInterrupt:
        detener_todo()

if __name__ == "__main__":
    main()