# /tests/test_server2.py (corregido)

import sys
import json
import time
import os
import random
import socket
import threading
import glob

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.peer_conector import PeerConnector

class P2PServer:
    def __init__(self, host, port, server_name):
        self.host = host
        self.port = port
        self.server_name = server_name
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', server_name)
        
        # Inicializar PeerConnector
        self.connector = PeerConnector(host, port, self.on_message)
        
        # Crear directorio de datos si no existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Información de otros servidores
        self.otros_servidores = [
            {"ip": "127.0.0.1", "port": 8080, "nombre": "servidor1"},
            {"ip": "127.0.0.1", "port": 8081, "nombre": "servidor2"}
        ]
        
        # Diccionario para almacenar respuestas de consultas a otros servidores
        self.respuestas_pendientes = {}
        
        print(f"✅ Servidor P2P '{server_name}' escuchando en {host}:{port}")
        print(f"📁 Directorio de datos: {self.data_dir}")
        self.mostrar_libros_disponibles()
    
    def on_message(self, message, addr):
        """Maneja mensajes recibidos"""
        try:
            # Dejar que PeerConnector maneje los mensajes de handshake primero
            if message.get("type") in ["SYN", "SYN-ACK", "ACK", "HANDSHAKE", "HANDSHAKE_RESPONSE", "FIN"]:
                # Estos mensajes son manejados automáticamente por PeerConnector
                return
                
            if message.get("type") == "BOOK_QUERY":
                self.handle_book_query(message, addr)
            elif message.get("type") == "BOOK_RESPONSE":
                self.handle_book_response(message, addr)
            else:
                print(f"<- Mensaje de {addr}: {message}")
        except Exception as e:
            print(f"❌ Error procesando mensaje de {addr}: {e}")
        
    def handle_book_response(self, message, addr):
        """Maneja respuestas de consultas de libros de otros servidores"""
        try:
            libro = message.get("libro")
            existe = message.get("existe", False)
            servidor_origen = message.get("servidor", "desconocido")
            
            print(f"<- Respuesta de {servidor_origen}@{addr}: Libro '{libro}' {'EXISTE' if existe else 'NO existe'}")
            
            # Almacenar la respuesta para procesarla luego
            if libro in self.respuestas_pendientes:
                self.respuestas_pendientes[libro] = message  # Almacenar todo el mensaje, no solo el booleano
                
        except Exception as e:
            print(f"❌ Error procesando respuesta de libro: {e}")
    
    def mostrar_libros_disponibles(self):
        """Muestra los libros disponibles en este servidor"""
        libros = self.obtener_libros_locales()
        print(f"📚 Libros locales ({len(libros)}): {', '.join(libros) if libros else 'Ninguno'}")
    
    def obtener_libros_locales(self):
        """Obtiene la lista de libros disponibles localmente"""
        try:
            # Buscar todos los archivos en el directorio (excluyendo metadata.json)
            archivos = []
            for ext in ['*.txt', '*.pdf', '*.docx', '*.md', '*.json']:
                archivos.extend(glob.glob(os.path.join(self.data_dir, ext)))
            
            # Extraer solo los nombres de archivo sin extensión
            libros = []
            for archivo in archivos:
                nombre_archivo = os.path.basename(archivo)
                if nombre_archivo != 'metadata.json':
                    nombre_libro = os.path.splitext(nombre_archivo)[0]
                    libros.append(nombre_libro)
            
            return sorted(libros)
            
        except Exception as e:
            print(f"❌ Error leyendo directorio: {e}")
            return []
    
    def libro_existe_localmente(self, nombre_libro):
        """Verifica si un libro existe localmente"""
        # Buscar archivos con ese nombre (sin importar extensión)
        patron = os.path.join(self.data_dir, f"{nombre_libro}.*")
        archivos = glob.glob(patron)
        return len(archivos) > 0
    
    def obtener_metadata_libro(self, nombre_libro):
        """Obtiene metadata de un libro si existe"""
        try:
            metadata_path = os.path.join(self.data_dir, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get(nombre_libro, {})
            return {}
        except:
            return {}
            
    def consultar_otro_servidor(self, servidor, libro_buscado):
        """Consulta REAL a otro servidor si tiene el libro usando PeerConnector"""
        try:
            print(f"🔍 Consultando servidor {servidor['nombre']} para libro: {libro_buscado}")
            
            # Crear un connector temporal para consultar al otro servidor
            temp_connector = PeerConnector("0.0.0.0", 0, self.on_temp_message)
            
            # Establecer conexión con el otro servidor
            if temp_connector.connect(servidor["ip"], servidor["port"]):
                # Enviar consulta cifrada
                solicitud = {"solicitud": libro_buscado, "type": "BOOK_QUERY"}
                
                # Usar send_and_wait_response para esperar la respuesta
                respuesta = temp_connector.send_and_wait_response(
                    solicitud, 
                    (servidor["ip"], servidor["port"]), 
                    timeout=5.0
                )
                
                temp_connector.disconnect((servidor["ip"], servidor["port"]))
                temp_connector.stop()
                
                if respuesta and respuesta.get("type") == "BOOK_RESPONSE":
                    return respuesta  # Return the entire response, not just the boolean
                else:
                    print(f"❌ No se recibió respuesta válida de {servidor['nombre']}")
                    return None
            else:
                print(f"❌ No se pudo conectar a {servidor['nombre']}")
                temp_connector.stop()
                return None
                
        except Exception as e:
            print(f"❌ Error consultando servidor {servidor['nombre']}: {e}")
            return None

    def on_temp_message(self, message, addr):
        """Maneja mensajes temporales para consultas a otros servidores"""
        # Dejar que el connector maneje los mensajes de protocolo
        if isinstance(message, dict) and message.get("type") in ["SYN", "SYN-ACK", "ACK", "HANDSHAKE", "HANDSHAKE_RESPONSE", "FIN"]:
            return
            
        if message.get("type") == "BOOK_RESPONSE":
            # Almacenar directamente la respuesta en el diccionario
            libro = message.get("libro")
            if libro:
                self.respuestas_pendientes[libro] = message.get("existe", False)
                print(f"<- Respuesta temporal de {addr}: Libro '{libro}' {'EXISTE' if message.get('existe') else 'NO existe'}")

    def buscar_en_red_p2p(self, libro_buscado):
        """Busca el libro en otros servidores de la red P2P de forma REAL"""
        print(f"🌐 Buscando '{libro_buscado}' en la red P2P...")
        
        for servidor in self.otros_servidores:
            # No consultarnos a nosotros mismos
            if servidor["port"] == self.port:
                continue
                
            try:
                # Usar el método mejorado que espera respuesta
                respuesta = self.consultar_otro_servidor(servidor, libro_buscado)
                if respuesta and respuesta.get("existe", False):  # Check if book exists
                    print(f"✅ Libro '{libro_buscado}' encontrado en {servidor['nombre']}")
                    return respuesta  # Return the complete response
            except Exception as e:
                print(f"❌ Error con servidor {servidor['nombre']}: {e}")
                continue
        
        print(f"❌ Libro '{libro_buscado}' no encontrado en la red P2P")
        return None

    def handle_book_query(self, query, addr):
        """Maneja consultas de libros de forma dinámica"""
        try:
            libro_buscado = query.get("solicitud")
            request_id = query.get("request_id")  # Get the request_id if present
            print(f"<- Consulta de libro recibida: {libro_buscado}")
            
            # Buscar localmente de forma dinámica
            existe_local = self.libro_existe_localmente(libro_buscado)
            
            if existe_local:
                metadata = self.obtener_metadata_libro(libro_buscado)
                respuesta = {
                    "existe": True,
                    "libro": libro_buscado,
                    "fuente": "local",
                    "servidor": self.server_name,
                    "metadata": metadata,
                    "type": "BOOK_RESPONSE"
                }
            else:
                # Buscar en otros servidores de la red P2P
                respuesta_red = self.buscar_en_red_p2p(libro_buscado)
                
                if respuesta_red:
                    # Usar la respuesta del servidor remoto
                    respuesta = respuesta_red
                else:
                    respuesta = {
                        "existe": False,
                        "libro": libro_buscado,
                        "fuente": "no_encontrado",
                        "servidor": "ninguno",
                        "type": "BOOK_RESPONSE"
                    }
            
            # Preservar el request_id si estaba presente en la consulta
            if request_id:
                respuesta["request_id"] = request_id
            
            # Enviar respuesta cifrada
            if self.connector.send_encrypted(respuesta, addr):
                print(f"-> Respuesta enviada a {addr}: {respuesta}")
            
        except Exception as e:
            print(f"❌ Error procesando consulta de libro: {e}")
            # Enviar respuesta de error
            respuesta_error = {
                "existe": False,
                "libro": libro_buscado,
                "error": str(e),
                "type": "BOOK_RESPONSE"
            }
            # Preservar el request_id si estaba presente en la consulta
            if request_id:
                respuesta_error["request_id"] = request_id
            self.connector.send_encrypted(respuesta_error, addr)
    
    def stop(self):
        """Detiene el servidor"""
        self.connector.stop()

def run_server1():
    """Servidor 1"""
    server = P2PServer("0.0.0.0", 8080, "servidor1")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("Servidor 1 detenido.")

def run_server2():
    """Servidor 2"""
    server = P2PServer("0.0.0.0", 8081, "servidor2")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("Servidor 2 detenido.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Ejecutar servidor P2P')
    parser.add_argument('--server', type=int, choices=[1, 2], default=1, help='Número del servidor a ejecutar')
    args = parser.parse_args()
    
    if args.server == 1:
        run_server1()
    else:
        run_server2()