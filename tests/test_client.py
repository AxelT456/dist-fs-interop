# test_client_integrated.py
import socket
import json
import os
import sys
import time
import base64
from prompt_toolkit import prompt

# Importar componentes de red seguros
# Añadir el directorio raíz del proyecto a la ruta para importar módulos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.network.peer_conector import PeerConnector
from src.network.transport import ReliableTransport

# Configuración del DNS
DNS_IP = "127.0.0.2"
DNS_PORT = 50000

class ClienteSeguro:
    def __init__(self):
        # Componentes de red seguros
        self.transport = None
        self.peer_connector = None
        self.server_info = None
        self.conectado = False
        self.client_host = "127.0.0.1"
        self.client_port = 0  # Puerto aleatorio
        
        # Buffer para respuestas asíncronas
        self.waiting_for_response = False
        self.last_response = None
    
    def _handle_secure_response(self, response: dict, peer_addr: tuple):
        """Maneja respuestas seguras del servidor"""
        print(f"[Respuesta segura] {response}")
        self.last_response = response
        self.waiting_for_response = False
    
    def consultar_dns_para_conexion(self):
        """Consulta al DNS SOLO para obtener la IP del servidor"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # Consulta genérica para obtener información del servidor
            consulta = {
                "accion": "consultar",
                "nombre_archivo": "servidor_info"
            }
            
            sock.sendto(json.dumps(consulta).encode('utf-8'), (DNS_IP, DNS_PORT))
            data, addr = sock.recvfrom(4096)
            respuesta = json.loads(data.decode('utf-8'))
            
            # Guardar información del servidor
            self.server_info = (respuesta.get("ip"), respuesta.get("puerto"))
            return True
                
        except Exception as e:
            print(f"Error consultando DNS: {e}")
            return False
        finally:
            sock.close()

    def conectar_servidor_seguro(self):
        """Conecta al servidor usando PeerConnector para comunicación segura"""
        if not self.server_info:
            if not self.consultar_dns_para_conexion():
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
            while time.time() - start_time < 10:  # 10 segundos timeout
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
                # Enviar mensaje de despedida cifrado
                try:
                    server_addr = (self.server_info[0], self.server_info[1])
                    self.peer_connector.send_message({"accion": "salir"}, server_addr)
                    time.sleep(0.5)  # Dar tiempo para que llegue el mensaje
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
            while self.waiting_for_response and time.time() - start_time < 10:  # 10 segundos timeout
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
                time.sleep(0.1)  # Pequeña pausa
            
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
        
        # Agregar timestamp
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
    cliente = ClienteSeguro()
    
    while True:
        print("\n" + "="*60)
        print("SISTEMA SEGURO DE GESTIÓN DE ARCHIVOS")
        print("="*60)
        if cliente.conectado:
            print(f"🔐 Conectado (seguro): {cliente.server_info[0]}:{cliente.server_info[1]}")
        else:
            print("🔌 Desconectado")
        print("="*60)
        print("1. 🔐 Conectar de manera segura")
        print("2. 📋 Consultar archivo específico")
        print("3. 📁 Listar todos los archivos")
        print("4. 👁️  Leer archivo remoto")
        print("5. ✏️  Escribir archivo remoto")
        print("6. ⬇️  Descargar archivo (seguro)")
        print("7. 🚪 Salir y desconectar")
        print("="*60)
        
        opcion = input("Selecciona una opción (1-7): ").strip()
        
        if opcion == "1":
            if cliente.conectado:
                print("Ya está conectado de manera segura")
                continue
                
            if cliente.consultar_dns_para_conexion():
                if cliente.conectar_servidor_seguro():
                    print("Conexión segura establecida correctamente")
                else:
                    print("No se pudo establecer conexión segura")
            else:
                print("No se pudo obtener información del DNS")
                
        elif opcion == "2":
            if not cliente.conectado:
                print("Primero debe conectarse de manera segura (Opción 1)")
                continue
                
            nombre_archivo = input("Nombre del archivo a consultar: ").strip()
            respuesta = cliente.realizar_accion_segura("consultar", nombre_archivo)
            if respuesta.get("status") == "ACK":
                print(f"✅ Archivo encontrado:")
                print(f"   Servidor: {respuesta.get('ip')}:{respuesta.get('puerto')}")
                print(f"   TTL: {respuesta.get('ttl')}s")
                if 'bandera' in respuesta:
                    bandera = respuesta.get('bandera')
                    if bandera == 0:
                        print(f"   Procedencia: Original")
                    elif bandera == 1:
                        print(f"   Procedencia: Referencia externa")
                    elif bandera == 2:
                        print(f"   Procedencia: Copia local")
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "3":
            if not cliente.conectado:
                print("❌ Primero debe conectarse de manera segura (Opción 1)")
                continue
                
            respuesta = cliente.realizar_accion_segura("listar_archivos")
            if respuesta.get("status") == "ACK":
                archivos = respuesta.get("archivos", [])
                print(f"\n📁 Archivos disponibles ({len(archivos)}):")
                print("-" * 60)
                for i, archivo in enumerate(archivos, 1):
                    estado = "✅" if archivo.get('publicado') else "❌"
                    bandera = archivo.get('bandera', 0)
                    ip_origen = archivo.get('ip_origen', 'Local')
                    
                    if bandera == 0:
                        procedencia = "(Original)"
                    elif bandera == 1:
                        procedencia = f"(Referencia → {ip_origen})"
                    elif bandera == 2:
                        procedencia = f"(Copia ← {ip_origen})"
                    else:
                        procedencia = ""
                    
                    print(f"{i:2d}. {archivo.get('nombre_archivo', 'N/A'):20} {estado} TTL: {archivo.get('ttl', 0)}s {procedencia}")
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "4":
            if not cliente.conectado:
                print("❌ Primero debe conectarse de manera segura (Opción 1)")
                continue
                
            nombre_archivo = input("Nombre del archivo a leer: ").strip()
            respuesta = cliente.realizar_accion_segura("leer", nombre_archivo)
            if respuesta.get("status") == "EXITO":
                print(f"\n📄 Contenido de '{nombre_archivo}':")
                print("-" * 40)
                print(respuesta.get("contenido", ""))
                print("-" * 40)
            else:
                print(f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "5":
            if not cliente.conectado:
                print("❌ Primero debe conectarse de manera segura (Opción 1)")
                continue
                
            nombre_archivo = input("Nombre del archivo a escribir/editar: ").strip()
            
            # Leer contenido actual
            respuesta = cliente.realizar_accion_segura("leer", nombre_archivo)
            if respuesta.get("status") == "EXITO":
                print(f"\n📄 Contenido de '{nombre_archivo}' (Esc+Enter para salir):")
                print("-" * 40)
                nuevo_texto = prompt("", default=respuesta.get("contenido", ""), multiline=True)
                print("-" * 40)
            else:
                print(f"\n📄 Nuevo archivo '{nombre_archivo}' (Esc+Enter para salir):")
                nuevo_texto = prompt("", multiline=True)
            
            # Escribir archivo
            respuesta = cliente.realizar_accion_segura("escribir", nombre_archivo, nuevo_texto.strip())
            print(f"✅ {respuesta.get('mensaje')}" if respuesta.get("status") == "EXITO" else f"❌ {respuesta.get('mensaje')}")
                
        elif opcion == "6":
            if not cliente.conectado:
                print("❌ Primero debe conectarse de manera segura (Opción 1)")
                continue
                
            nombre_archivo = input("Nombre del archivo a descargar: ").strip()
            
            if os.path.exists(nombre_archivo):
                sobrescribir = input(f"⚠️  '{nombre_archivo}' ya existe. ¿Sobrescribir? (s/n): ")
                if sobrescribir.lower() != 's':
                    continue
            
            try:
                respuesta = cliente.realizar_accion_segura("descargar", nombre_archivo)
                
                if respuesta.get("status") == "EXITO":
                    # Decodificar contenido base64
                    contenido_b64 = respuesta.get("contenido", "")
                    contenido_bytes = base64.b64decode(contenido_b64)
                    
                    with open(nombre_archivo, 'wb') as f:
                        f.write(contenido_bytes)
                    
                    size = respuesta.get("size", len(contenido_bytes))
                    print(f"✅ Archivo '{nombre_archivo}' descargado ({size} bytes)")
                else:
                    print(f"❌ {respuesta.get('mensaje')}")
            except Exception as e:
                print(f"❌ Error descargando archivo: {e}")
                
        elif opcion == "7":
            if cliente.conectado:
                cliente.desconectar_servidor()
            print("👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    print("=== Cliente con Comunicación Segura ===")
    print("Handshake Diffie-Hellman automático")
    print("Todos los mensajes cifrados")
    print("Transporte confiable con retransmisión")
    print("Primero conéctese (Opción 1), luego realice operaciones")
    print("NOTA: Todas las comunicaciones son seguras y cifradas\n")
    mostrar_menu()