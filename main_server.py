# main_server_integrated.py
import socket
import json
import threading
import os
import logging
import time
from typing import List, Dict, Tuple

# Importaciones del sistema de red seguro
import sys
sys.path.append('src/network')
from src.network.peer_conector import PeerConnector
from src.network.transport import ReliableTransport

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DNS_IP = "127.0.0.2"
DNS_PORT = 50000
SERVER_IP = "127.0.0.3"
SERVER_PORT = 5002
UPDATE_INTERVAL = 30

class ServidorCompletoSeguro:
    def __init__(self, host=SERVER_IP, port=SERVER_PORT, dns_ip=DNS_IP, dns_port=DNS_PORT):
        self.host = host
        self.port = port
        self.dns_ip = dns_ip
        self.dns_port = dns_port
        self.folder_path = "archivos"
        self.archivos = []
        self.ultima_actualizacion = 0
        
        # Componentes de red seguros
        self.transport = ReliableTransport(host, port)
        self.peer_connector = PeerConnector(
            self.transport, 
            f"{host}:{port}", 
            self._handle_secure_message
        )
        
        # Clientes conectados (para broadcast de actualizaciones)
        self.connected_peers = {}
        self.running = True
        
        # Inicializar archivos
        self._actualizar_lista_archivos()
        self._iniciar_actualizador()
        
    def _iniciar_actualizador(self):
        """Inicia el hilo que actualiza periódicamente la lista de archivos"""
        def actualizador_periodico():
            while self.running:
                try:
                    time.sleep(UPDATE_INTERVAL)
                    if self.running:
                        self._actualizar_lista_archivos()
                        logging.info(f"Lista de archivos actualizada. Total: {len(self.archivos)}")
                except Exception as e:
                    logging.error(f"Error en actualizador periódico: {e}")
        
        thread = threading.Thread(target=actualizador_periodico, daemon=True)
        thread.start()
        logging.info("Actualizador periódico iniciado")
        
    def _consultar_dns(self, accion: str, datos: Dict = None) -> Dict:
        """Consulta al DNS para obtener información"""
        try:
            if accion == "listar_archivos" and self.archivos and time.time() - self.ultima_actualizacion < 10:
                return {"status": "ACK", "archivos": self.archivos}
                
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.bind((self.host, 0))
            
            consulta = {"accion": accion}
            if datos:
                consulta.update(datos)
            
            sock.sendto(json.dumps(consulta).encode('utf-8'), (self.dns_ip, self.dns_port))
            data, addr = sock.recvfrom(4096)
            respuesta = json.loads(data.decode('utf-8'))
            
            if accion == "listar_archivos" and respuesta.get("status") == "ACK":
                self.ultima_actualizacion = time.time()
                
            return respuesta
                
        except Exception as e:
            logging.error(f"Error consultando DNS: {e}")
            return {"status": "ERROR", "mensaje": f"Error consulting DNS: {e}"}
        finally:
            if 'sock' in locals():
                sock.close()
        
    def _actualizar_lista_archivos(self):
        """Actualiza la lista de archivos desde el DNS"""
        try:
            respuesta = self._consultar_dns("listar_archivos")
            if respuesta.get("status") == "ACK":
                nuevos_archivos = respuesta.get("archivos", [])
                
                archivos_actualizados = []
                for nuevo_archivo in nuevos_archivos:
                    archivo_existente = next((a for a in self.archivos 
                                            if a['nombre_archivo'] == nuevo_archivo['nombre_archivo']), None)
                    
                    if archivo_existente:
                        nuevo_archivo['bandera'] = archivo_existente['bandera']
                        nuevo_archivo['ip_origen'] = archivo_existente['ip_origen']
                    else:
                        nuevo_archivo['bandera'] = 0
                        nuevo_archivo['ip_origen'] = self.host
                    
                    archivos_actualizados.append(nuevo_archivo)
                
                self.archivos = archivos_actualizados
                logging.info(f"Lista de archivos actualizada. Total: {len(self.archivos)}")
        except Exception as e:
            logging.error(f"Error actualizando lista: {e}")

    def _handle_secure_message(self, request: Dict, peer_addr: Tuple[str, int]):
        """Maneja mensajes seguros recibidos de peers"""
        try:
            accion = request.get("accion")
            logging.info(f"Mensaje seguro de {peer_addr}: {accion}")
            
            if accion == "consultar":
                response = self._manejar_consultar_seguro(request)
            elif accion == "listar_archivos":
                response = self._manejar_listar_seguro()
            elif accion == "leer":
                response = self._manejar_leer_seguro(request)
            elif accion == "escribir":
                response = self._manejar_escribir_seguro(request)
            elif accion == "descargar":
                response = self._manejar_descargar_seguro(request)
            elif accion == "obtener_archivo_desde_otro":
                response = self._manejar_obtener_desde_otro_seguro(request)
            elif accion == "actualizar_lista":
                self._actualizar_lista_archivos()
                response = {"status": "EXITO", "mensaje": "Lista actualizada"}
            else:
                response = {"status": "ERROR", "mensaje": f"Acción '{accion}' no reconocida"}
            
            # Enviar respuesta cifrada
            self.peer_connector.send_message(response, peer_addr)
            
        except Exception as e:
            logging.error(f"Error procesando mensaje seguro: {e}")
            error_response = {"status": "ERROR", "mensaje": str(e)}
            self.peer_connector.send_message(error_response, peer_addr)

    def _manejar_consultar_seguro(self, request: Dict) -> Dict:
        """Versión segura del manejo de consultas"""
        nombre_archivo = request.get("nombre_archivo")
        if not nombre_archivo:
            return {"status": "ERROR", "mensaje": "Nombre de archivo requerido"}
        
        archivo_encontrado = None
        for archivo in self.archivos:
            if archivo['nombre_archivo'] == nombre_archivo and archivo['publicado']:
                archivo_encontrado = archivo
                break
        
        if archivo_encontrado:
            return {
                "status": "ACK",
                "nombre_archivo": archivo_encontrado['nombre_archivo'],
                "ttl": archivo_encontrado['ttl'],
                "ip": archivo_encontrado['ip_origen'],
                "puerto": self.port,
                "bandera": archivo_encontrado['bandera']
            }
        else:
            return {
                "status": "NACK",
                "mensaje": "Archivo no encontrado o no publicado",
                "ip": self.host,
                "puerto": self.port
            }

    def _manejar_listar_seguro(self) -> Dict:
        """Versión segura del listado de archivos"""
        if not self.archivos:
            self._actualizar_lista_archivos()
        
        return {
            "status": "ACK",
            "archivos": self.archivos,
            "total": len(self.archivos)
        }

    def _manejar_leer_seguro(self, request: Dict) -> Dict:
        """Versión segura de lectura de archivos"""
        nombre_archivo = request.get("nombre_archivo")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                return {"status": "EXITO", "contenido": contenido}
            except UnicodeDecodeError:
                return {"status": "ERROR", "mensaje": "Archivo binario, no se puede leer como texto"}
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error leyendo archivo: {e}"}
        else:
            return {"status": "ERROR", "mensaje": "Archivo no encontrado"}

    def _manejar_escribir_seguro(self, request: Dict) -> Dict:
        """Versión segura de escritura de archivos"""
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido", "")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            return {"status": "EXITO", "mensaje": f"Archivo '{nombre_archivo}' guardado"}
        except Exception as e:
            return {"status": "ERROR", "mensaje": f"Error escribiendo archivo: {e}"}

    def _manejar_descargar_seguro(self, request: Dict) -> Dict:
        """Versión segura de descarga - envía contenido en la respuesta"""
        nombre_archivo = request.get("nombre_archivo")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    contenido_bytes = f.read()
                
                # Convertir a base64 para transmisión segura
                import base64
                contenido_b64 = base64.b64encode(contenido_bytes).decode('utf-8')
                
                return {
                    "status": "EXITO",
                    "mensaje": "Archivo listo para descarga",
                    "contenido": contenido_b64,
                    "size": len(contenido_bytes)
                }
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error leyendo archivo: {e}"}
        else:
            return {"status": "ERROR", "mensaje": "Archivo no encontrado"}

    def _manejar_obtener_desde_otro_seguro(self, request: Dict) -> Dict:
        """Versión segura para obtener archivos de otros peers"""
        nombre_archivo = request.get("nombre_archivo")
        ip_origen = request.get("ip_origen")
        puerto_origen = request.get("puerto_origen")
        
        try:
            peer_addr = (ip_origen, puerto_origen)
            
            # Establecer conexión segura con el peer
            self.peer_connector.connect_and_secure(peer_addr)
            
            # Solicitar el archivo de manera segura
            solicitud = {
                "accion": "descargar",
                "nombre_archivo": nombre_archivo
            }
            
            self.peer_connector.send_message(solicitud, peer_addr)
            
            # La respuesta llegará a _handle_secure_message
            # Por ahora retornamos que se inició el proceso
            return {
                "status": "PROCESO_INICIADO",
                "mensaje": f"Solicitando '{nombre_archivo}' de manera segura de {peer_addr}"
            }
            
        except Exception as e:
            return {"status": "ERROR", "mensaje": f"Error obteniendo archivo: {e}"}

    def start(self):
        """Inicia el servidor con comunicación segura"""
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            logging.info(f"Carpeta '{self.folder_path}' creada")
        
        logging.info(f"Servidor seguro escuchando en {self.host}:{self.port}")
        logging.info(f"Conectado al DNS: {self.dns_ip}:{self.dns_port}")
        logging.info(f"Carpeta local: {os.path.abspath(self.folder_path)}")
        logging.info(f"Archivos registrados: {len(self.archivos)}")
        
        try:
            # Bucle principal de escucha segura
            while self.running:
                payload, addr = self.transport.listen()
                if payload and addr:
                    # PeerConnector maneja automáticamente handshakes y descifrado
                    self.peer_connector.handle_incoming_packet(payload, addr)
                    
        except KeyboardInterrupt:
            logging.info("\nServidor detenido por el usuario")
        except Exception as e:
            logging.error(f"Error en el servidor: {e}")
        finally:
            self.stop()

    def stop(self):
        """Detiene el servidor de manera limpia"""
        self.running = False
        if self.peer_connector:
            self.peer_connector.stop()
        logging.info("Servidor detenido")

if __name__ == "__main__":
    print("=== Servidor Completo Seguro ===")
    print("Comunicación cifrada con PeerConnector")
    print("Handshake automático Diffie-Hellman")
    print("Transporte confiable subyacente")
    print("Ctrl+C para detener el servidor\n")
    
    server = ServidorCompletoSeguro()
    server.start()