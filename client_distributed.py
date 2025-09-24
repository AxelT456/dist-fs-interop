# client_distributed.py
import socket
import json
import os
import sys
import time
import random
from prompt_toolkit import prompt

# Importar componentes de red seguros
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.network.peer_conector import PeerConnector
from src.network.transport import ReliableTransport

# Configuración de DNS disponibles (expandida)
DNS_SERVERS = [
    {
        "id": "DNS1",
        "ip": "127.0.0.2",
        "port": 50000,
        "server_ip": "127.0.0.3",
        "server_port": 5002,
        "description": "DNS Servidor Original"
    },
    {
        "id": "DNS2", 
        "ip": "127.0.0.12",
        "port": 50000,
        "server_ip": "127.0.0.4",
        "server_port": 5003,
        "description": "DNS Servidor Christian"
    },
    {
        "id": "DNS_MARCO",
        "ip": "127.0.0.8",
        "port": 50000,
        "server_ip": "127.0.0.8",
        "server_port": 5005,
        "description": "DNS Servidor Marco"
    },
    {
        "id": "DNS_DAN",
        "ip": "127.0.0.9",
        "port": 50000,
        "server_ip": "127.0.0.9",
        "server_port": 5006,
        "description": "DNS Servidor Dan"
    },
    {
        "id": "DNS_GUS",
        "ip": "127.0.0.10",
        "port": 50000,
        "server_ip": "127.0.0.10",
        "server_port": 5007,
        "description": "DNS Servidor Gus"
    }
]

class ClienteDistribuido:
    def __init__(self):
        # Componentes de red seguros
        self.transport = None
        self.peer_connector = None
        self.server_info = None
        self.dns_info = None
        self.conectado = False
        self.client_host = "127.0.0.1"
        self.client_port = 0
        
        # Buffer para respuestas asíncronas
        self.waiting_for_response = False
        self.last_response = None
    
    def _handle_secure_response(self, response: dict, peer_addr: tuple):
        """Maneja respuestas seguras del servidor"""
        print(f"[Respuesta] {response.get('status', 'UNKNOWN')}: {response.get('mensaje', '')}")
        self.last_response = response
        self.waiting_for_response = False
    
    def seleccionar_dns_aleatorio(self):
        """Selecciona un DNS aleatoriamente de la lista disponible"""
        dns_elegido=DNS_SERVERS[0] #elige el server de axel/christian/marco/dan/gus
        dns_elegido = random.choice(DNS_SERVERS)
        self.dns_info = dns_elegido
        print(f"DNS seleccionado aleatoriamente: {dns_elegido['description']} ({dns_elegido['id']})")
        print(f"  -> DNS: {dns_elegido['ip']}:{dns_elegido['port']}")
        print(f"  -> Servidor asociado: {dns_elegido['server_ip']}:{dns_elegido['server_port']}")
        return True
    
    def consultar_dns_para_servidor(self):
        """Consulta al DNS seleccionado para obtener información del servidor"""
        if not self.dns_info:
            return False
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # Consulta específica según el tipo de DNS
            if self.dns_info['id'] == 'DNS2':  # Servidor Christian
                consulta = {
                    "filename": "servidor",
                    "extension": "info", 
                    "type": "check"
                }
            else:  # DNS Original y otros
                consulta = {
                    "accion": "consultar",
                    "nombre_archivo": "servidor_info"
                }
            
            dns_addr = (self.dns_info['ip'], self.dns_info['port'])
            sock.sendto(json.dumps(consulta).encode('utf-8'), dns_addr)
            data, addr = sock.recvfrom(4096)
            respuesta = json.loads(data.decode('utf-8'))
            
            # Procesar respuesta según el tipo de DNS
            if self.dns_info['id'] == 'DNS2':  # Christian
                if respuesta.get("response") == "ACK":
                    self.server_info = (respuesta.get("ip"), respuesta.get("port"))
                else:
                    # Usar información predeterminada
                    self.server_info = (self.dns_info['server_ip'], self.dns_info['server_port'])
            else:  # DNS Original
                if respuesta.get("status") == "ACK":
                    self.server_info = (respuesta.get("ip"), respuesta.get("puerto"))
                else:
                    # Usar información predeterminada
                    self.server_info = (self.dns_info['server_ip'], self.dns_info['server_port'])
            
            print(f"Servidor obtenido: {self.server_info[0]}:{self.server_info[1]}")
            return True
                
        except Exception as e:
            print(f"Error consultando DNS: {e}")
            print("Usando información predeterminada del servidor")
            self.server_info = (self.dns_info['server_ip'], self.dns_info['server_port'])
            return True
        finally:
            sock.close()

    def conectar_servidor_seguro(self):
        """Conecta al servidor usando PeerConnector para comunicación segura"""
        if not self.server_info:
            return False
        
        try:
            # Encontrar puerto libre para el cliente
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.bind((self.client_host, 0))
            self.client_port = temp_sock.getsockname()[1]
            temp_sock.close()
            
            # Inicializar componentes de red seguros
            self.transport = ReliableTransport(self.client_host, self.client_port)
            self.peer_connector = PeerConnector(
                self.transport, 
                f"{self.client_host}:{self.client_port}",
                self._handle_secure_response
            )
            
            # Iniciar conexión segura con handshake automático
            server_addr = (self.server_info[0], self.server_info[1])
            self.peer_connector.connect_and_secure(server_addr)
            
            # Esperar a que se complete el handshake
            print("Estableciendo conexión segura...")
            start_time = time.time()
            while time.time() - start_time < 10:
                # Procesar mensajes entrantes para completar handshake
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
                
                # Verificar si ya tenemos sesión establecida
                if server_addr in self.peer_connector.sessions:
                    self.conectado = True
                    print(f"Conexión segura establecida con {self.server_info[0]}:{self.server_info[1]}")
                    return True
            
            print("Timeout estableciendo conexión segura")
            return False
            
        except Exception as e:
            print(f"Error conectando de manera segura: {e}")
            self.conectado = False
            return False
    
    def desconectar_servidor(self):
        """Desconecta del servidor"""
        try:
            if self.peer_connector and self.conectado:
                try:
                    server_addr = (self.server_info[0], self.server_info[1])
                    self.peer_connector.send_message({"accion": "salir"}, server_addr)
                    time.sleep(0.5)
                except:
                    pass
                
                self.peer_connector.stop()
                self.peer_connector = None
                self.transport = None
            
            self.conectado = False
            print("Desconectado del servidor de manera segura")
        except Exception as e:
            print(f"Error al desconectar: {e}")
        finally:
            self.conectado = False
    
    def enviar_solicitud_segura(self, solicitud: dict):
        """Envía solicitud de manera segura y espera respuesta"""
        if not self.conectado:
            return {"status": "ERROR", "mensaje": "No conectado al servidor"}
        
        try:
            server_addr = (self.server_info[0], self.server_info[1])
            
            # Enviar mensaje cifrado
            self.waiting_for_response = True
            self.last_response = None
            self.peer_connector.send_message(solicitud, server_addr)
            
            # Esperar respuesta asíncrona
            start_time = time.time()
            while self.waiting_for_response and time.time() - start_time < 10:
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
                time.sleep(0.1)
            
            if self.last_response:
                return self.last_response
            else:
                return {"status": "ERROR", "mensaje": "Timeout esperando respuesta"}
                
        except Exception as e:
            return {"status": "ERROR", "mensaje": str(e)}
    
    def realizar_accion_segura(self, accion, nombre_archivo="", contenido=None):
        """Realiza una acción específica de manera segura"""
        if not self.conectado:
            return {"status": "ERROR", "mensaje": "Primero debe conectarse al servidor"}
        
        solicitud = {
            "accion": accion,
            "nombre_archivo": nombre_archivo
        }
        
        if contenido is not None:
            solicitud["contenido"] = contenido
        
        solicitud["timestamp"] = time.time()
        
        respuesta = self.enviar_solicitud_segura(solicitud)
        
        # Reintento para listar si está vacío
        if accion == "listar_archivos" and respuesta.get("status") == "ACK" and len(respuesta.get("archivos", [])) == 0:
            print("Esperando actualización del servidor...")
            time.sleep(2)
            solicitud["timestamp"] = time.time()
            respuesta = self.enviar_solicitud_segura(solicitud)
        
        return respuesta

def mostrar_menu():
    """Menú principal con comunicación segura"""
    cliente = ClienteDistribuido()
    
    while True:
        print("\n" + "="*60)
        print("SISTEMA DISTRIBUIDO DE GESTIÓN DE LIBROS")
        print("="*60)
        if cliente.conectado:
            print(f"🔐 Conectado: {cliente.server_info[0]}:{cliente.server_info[1]}")
            print(f"📡 DNS usado: {cliente.dns_info['description']}")
        else:
            print("🔌 Desconectado")
        print("="*60)
        print("1. 🔗 Conectar aleatoriamente")
        print("2. 📋 Consultar libro específico")
        print("3. 📚 Ver libros disponibles")
        print("4. 👁️  Leer libro")
        print("5. ✏️  Escribir libro")
        print("6. 🚪 Salir y desconectar")
        print("="*60)
        
        opcion = input("Selecciona una opción (1-6): ").strip()
        
        if opcion == "1":
            if cliente.conectado:
                print("Ya está conectado. Desconectando primero...")
                cliente.desconectar_servidor()
            
            print("\nSeleccionando DNS aleatoriamente...")
            if cliente.seleccionar_dns_aleatorio():
                print("Consultando servidor asociado...")
                if cliente.consultar_dns_para_servidor():
                    print("Estableciendo conexión segura...")
                    if cliente.conectar_servidor_seguro():
                        print("✅ Conexión establecida correctamente")
                    else:
                        print("❌ No se pudo establecer conexión segura")
                else:
                    print("❌ No se pudo obtener información del servidor")
            else:
                print("❌ Error seleccionando DNS")
                
        elif opcion == "2":
            if not cliente.conectado:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
                
            nombre_libro = input("Nombre del libro a consultar: ").strip()
            respuesta = cliente.realizar_accion_segura("consultar", nombre_libro)
            if respuesta.get("status") == "ACK":
                print(f"✅ Libro encontrado:")
                print(f"   Ubicación: {respuesta.get('server_id', 'Local')}")
                print(f"   IP: {respuesta.get('ip')}:{respuesta.get('puerto')}")
                if respuesta.get('local'):
                    print(f"   Tipo: Archivo local")
                else:
                    print(f"   Tipo: Archivo remoto")
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "3":
            if not cliente.conectado:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
                
            respuesta = cliente.realizar_accion_segura("listar_archivos")
            if respuesta.get("status") == "ACK":
                archivos = respuesta.get("archivos", [])
                print(f"\n📚 Libros disponibles ({len(archivos)}):")
                print("-" * 70)
                for i, archivo in enumerate(archivos, 1):
                    servidor = archivo.get('servidor_principal', 'Local')
                    replicas = archivo.get('replicas', 1)
                    ubicacion = f"[{servidor}]"
                    if replicas > 1:
                        ubicacion += f" ({replicas} copias)"
                    
                    print(f"{i:2d}. {archivo.get('nombre_archivo', 'N/A'):30} {ubicacion}")
                
                fuente = respuesta.get('fuente', 'distribuido')
                servidores_activos = respuesta.get('servidores_activos', 'N/A')
                print(f"\nFuente: {fuente} | Servidores activos: {servidores_activos}")
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "4":
            if not cliente.conectado:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
                
            nombre_libro = input("Nombre del libro a leer: ").strip()
            respuesta = cliente.realizar_accion_segura("leer", nombre_libro)
            if respuesta.get("status") == "EXITO":
                fuente = respuesta.get("fuente", "desconocida")
                print(f"\n📖 Contenido de '{nombre_libro}' (fuente: {fuente}):")
                print("-" * 50)
                print(respuesta.get("contenido", ""))
                print("-" * 50)
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "5":
            if not cliente.conectado:
                print("❌ Primero debe conectarse (Opción 1)")
                continue
                
            nombre_libro = input("Nombre del libro a escribir/editar: ").strip()
            
            # Intentar leer contenido actual
            respuesta = cliente.realizar_accion_segura("leer", nombre_libro)
            if respuesta.get("status") == "EXITO":
                fuente = respuesta.get("fuente", "desconocida")
                print(f"\n📖 Contenido actual de '{nombre_libro}' (fuente: {fuente}):")
                print("(Esc+Enter para terminar edición)")
                print("-" * 40)
                nuevo_texto = prompt("", default=respuesta.get("contenido", ""), multiline=True)
                print("-" * 40)
            else:
                print(f"\n📝 Nuevo libro '{nombre_libro}' (Esc+Enter para terminar):")
                nuevo_texto = prompt("", multiline=True)
            
            # Escribir libro
            respuesta = cliente.realizar_accion_segura("escribir", nombre_libro, nuevo_texto.strip())
            if respuesta.get("status") == "EXITO":
                fuente = respuesta.get("fuente", "local")
                print(f"✅ {respuesta.get('mensaje')} (guardado en: {fuente})")
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "6":
            if cliente.conectado:
                cliente.desconectar_servidor()
            print("👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    print("=== Cliente Sistema Distribuido ===")
    print("Selección aleatoria de DNS")
    print("Comunicación segura con servidores")
    print("Búsqueda distribuida de libros")
    print("NOTA: Se conectará aleatoriamente a uno de los DNS disponibles\n")
    
    print("DNS disponibles:")
    for dns in DNS_SERVERS:
        print(f"  - {dns['description']}: {dns['ip']}:{dns['port']}")
    print()
    
    mostrar_menu()