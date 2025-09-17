# /tests/test_dns_client.py

import sys
import os
import json
import random
import time
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.peer_conector import PeerConnector
from src.network.dns_translator.translator import DNSTranslator

def mock_driver():
    return {
        "encode": lambda req: {"query": req["name"]},
        "decode": lambda resp: {"ip": resp["ip"], "port": resp["port"]}
    }

class TestDNSClient:
    def __init__(self):
        self.dns = DNSTranslator()
        self.dns.registrar_driver(1, mock_driver())
        self.dns.registrar_driver(2, mock_driver())
        self.connector = PeerConnector("0.0.0.0", 0, self.on_message)
        self.server_addr = None
        self.connected = False

    def on_message(self, message, addr):
        """Maneja mensajes recibidos"""
        # Dejar que PeerConnector maneje los mensajes de handshake primero
        if isinstance(message, dict) and message.get("type") in ["SYN", "SYN-ACK", "ACK", "HANDSHAKE", "HANDSHAKE_RESPONSE", "FIN"]:
            # Estos mensajes son manejados automáticamente por PeerConnector
            return
            
        if isinstance(message, dict) and message.get("type") == "BOOK_RESPONSE":
            print(f"\n📖 RESPUESTA DE {addr}:")
            if message["existe"]:
                print(f"✅ Libro '{message['libro']}' encontrado en {message['servidor']}")
                print(f"📋 Metadata: {message.get('metadata', 'No disponible')}")
            else:
                print(f"❌ Libro '{message['libro']}' no encontrado")
        else:
            print(f"<- Mensaje recibido de {addr}: {message}")

    def consultar_dns(self, dns_config, servidor_name):
        """Consulta el DNS de forma robusta"""
        try:
            cliente_req = {"query": servidor_name}
            print(f"Consultando DNS en {dns_config['ip']}:{dns_config['port']} para: {servidor_name}")

            # Consulta DNS
            sock_dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock_dns.settimeout(3.0)
            
            sock_dns.sendto(json.dumps(cliente_req).encode("utf-8"), (dns_config["ip"], dns_config["port"]))
            
            data, addr = sock_dns.recvfrom(4096)
            resultado_dns = json.loads(data.decode("utf-8"))
            
            sock_dns.close()
            return resultado_dns
            
        except socket.timeout:
            print(f"❌ Timeout consultando DNS {dns_config['nombre']}")
            return None
        except ConnectionResetError:
            print(f"❌ Conexión rechazada por DNS {dns_config['nombre']}")
            return None
        except Exception as e:
            print(f"❌ Error consultando DNS: {e}")
            return None

    def establecer_conexion(self):
        """Establece la conexión con el servidor usando PeerConnector"""
        if self.connected:
            print("✅ Ya hay una conexión establecida")
            return True

        # 1. Consulta DNS para obtener IP y puerto del servidor
        dns_options = [
            {"id": 1, "ip": "127.0.0.1", "port": 8053, "driver": mock_driver(), "nombre": "servidor1"},
            {"id": 2, "ip": "127.0.0.1", "port": 8054, "driver": mock_driver(), "nombre": "servidor2"}
        ]

        # Elegir aleatoriamente QUÉ servidor consultar (servidor1 o servidor2)
        servidor_a_consultar = random.choice(["servidor1", "servidor2"])
        print(f"🔀 Consultando aleatoriamente por: {servidor_a_consultar}")
        
        # Intentar con cada DNS hasta encontrar uno que responda
        resultado_dns = None
        for dns_config in dns_options:
            resultado_dns = self.consultar_dns(dns_config, servidor_a_consultar)
            if resultado_dns and resultado_dns.get("ip") != "0.0.0.0":
                break
            time.sleep(1)
        
        if not resultado_dns or resultado_dns.get("ip") == "0.0.0.0":
            print("❌ No se pudo obtener información válida del DNS")
            return False

        ip_servidor = resultado_dns.get("ip")
        puerto_servidor = resultado_dns.get("port")
        
        self.server_addr = (ip_servidor, puerto_servidor)
        print(f"✅ IP obtenida del DNS: {ip_servidor}, Puerto: {puerto_servidor}")

        # 2. Establecer conexión usando PeerConnector
        try:
            if self.connector.connect(ip_servidor, puerto_servidor):
                self.connected = True
                print("✅ Conexión establecida exitosamente")
                return True
            else:
                print("❌ Error al establecer conexión")
                return False
                
        except Exception as e:
            print(f"❌ Error estableciendo conexión: {e}")
            return False

    def consultar_libro(self, libro_solicitado=None):
        """Consulta un libro al servidor usando PeerConnector"""
        if not self.connected or not self.server_addr:
            print("❌ No hay conexión establecida")
            return False

        try:
            if not libro_solicitado:
                libro_solicitado = random.choice(["LibroA", "LibroB", "LibroC", "LibroD"])
            
            solicitud = {"solicitud": libro_solicitado, "type": "BOOK_QUERY"}
            
            # Enviar solicitud cifrada usando PeerConnector
            if self.connector.send_encrypted(solicitud, self.server_addr):
                print(f"-> Solicitud cifrada enviada: {solicitud}")
                return True
            else:
                print("❌ Error enviando solicitud cifrada")
                return False

        except Exception as e:
            print(f"❌ Error en la consulta: {e}")
            return False

    def cerrar_conexion(self):
        """Cierra la conexión con el servidor usando PeerConnector"""
        if self.server_addr:
            self.connector.disconnect(self.server_addr)
            self.connected = False
            self.server_addr = None
            print("🔌 Conexión cerrada")

    def modo_interactivo(self):
        """Modo interactivo para múltiples consultas"""
        print("\n" + "="*50)
        print("🔍 CLIENTE P2P - MODO INTERACTIVO")
        print("="*50)
        print("Comandos disponibles:")
        print("  connect - Establecer conexión")
        print("  query [libro] - Consultar un libro")
        print("  list - Listar libros disponibles")
        print("  exit - Salir")
        print("="*50)

        while True:
            try:
                comando = input("\n📝 Ingrese comando: ").strip()
                
                if comando == "exit":
                    print("👋 Saliendo...")
                    break
                
                elif comando == "connect":
                    if self.establecer_conexion():
                        print("✅ Conexión establecida exitosamente")
                    else:
                        print("❌ Error al establecer conexión")
                
                elif comando.startswith("query"):
                    partes = comando.split()
                    if len(partes) > 1:
                        libro = partes[1]
                        self.consultar_libro(libro)
                    else:
                        print("❌ Especifique el libro: query [nombre_libro]")
                
                elif comando == "list":
                    print("📚 Libros disponibles para consulta: LibroA, LibroB, LibroC, LibroD")
                
                elif comando == "":
                    continue
                
                else:
                    print("❌ Comando no reconocido. Use: connect, query [libro], list, exit")
            
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

        self.cerrar_conexion()

    def modo_automatico(self):
        """Modo automático con múltiples consultas"""
        if not self.establecer_conexion():
            return

        try:
            # Realizar varias consultas automáticas
            for i in range(5):  # 5 consultas automáticas
                print(f"\n📖 Consulta #{i+1}:")
                resultado = self.consultar_libro()
                if not resultado:
                    print("❌ Error en la consulta, reintentando conexión...")
                    if not self.establecer_conexion():
                        break
                    time.sleep(2)
                time.sleep(3)  # Esperar entre consultas
            
            print("\n✅ Consultas automáticas completadas")
            
        finally:
            self.cerrar_conexion()

if __name__ == "__main__":
    client = TestDNSClient()
    
    # Preguntar al usuario qué modo prefiere
    print("Seleccione modo de operación:")
    print("1. Modo interactivo (puede hacer múltiples consultas)")
    print("2. Modo automático (5 consultas automáticas)")
    
    try:
        opcion = input("Ingrese opción (1/2): ").strip()
        if opcion == "1":
            client.modo_interactivo()
        else:
            client.modo_automatico()
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")
        client.cerrar_conexion()
    finally:
        client.connector.stop()