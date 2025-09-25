import socket
import json
import threading
import os
import logging
import time
import sys
from typing import List, Dict, Tuple
from datetime import datetime

# Importaciones del sistema de red seguro
sys.path.append('src/network')
from src.network.peer_conector import PeerConnector
from src.network.transport import ReliableTransport

# Configuración
with open('network_config.json', 'r') as f:
    net_config = json.load(f)

# Configuración
DNS_GENERAL_IP = net_config['dns_general']['connect_ip']
DNS_GENERAL_PORT = net_config['dns_general']['port']

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ServidorDistribuido:
    def __init__(self, server_id: str, host: str, port: int, dns_local_ip: str, dns_local_port: int, folder_path: str = "archivos"):
        self.server_id = server_id
        self.host = host
        self.port = port
        self.dns_local_ip = dns_local_ip
        self.dns_local_port = dns_local_port
        self.folder_path = folder_path
        self.running = True
        
        # Lista local de archivos
        self.local_files = []
        self.local_files_lock = threading.Lock()
        
        # Cache de archivos remotos conocidos
        self.remote_files_cache = {}  # {nombre_archivo: {"server_id": id, "ip": ip, "port": port}}
        
        # Componentes de red seguros
        self.transport = ReliableTransport(host, port)
        self.peer_connector = PeerConnector(
            self.transport, 
            f"{host}:{port}", 
            self._handle_secure_message
        )
        
        # Crear carpeta si no existe
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            
        # Inicializar
        self._scan_local_files()
        self._register_with_dns_general()
        self._start_heartbeat()
        self._start_udp_listener()
        self._start_file_monitor()
        """Inicia el monitor de archivos para detectar cambios locales"""
        def file_monitor():
            last_scan = {}  # {nombre_archivo: timestamp_modificacion}
            
            while self.running:
                try:
                    time.sleep(10)  # Verificar cada 10 segundos
                    if not self.running:
                        break
                    
                    current_files = {}
                    changes_detected = False
                    
                    # Escanear archivos actuales
                    if os.path.exists(self.folder_path):
                        for filename in os.listdir(self.folder_path):
                            if filename.endswith('.temp_checkout'):
                                continue  # Ignorar archivos temporales
                            
                            filepath = os.path.join(self.folder_path, filename)
                            if os.path.isfile(filepath):
                                mtime = os.path.getmtime(filepath)
                                current_files[filename] = mtime
                    
                    # Detectar archivos nuevos
                    nuevos_archivos = set(current_files.keys()) - set(last_scan.keys())
                    if nuevos_archivos:
                        for archivo in nuevos_archivos:
                            self.log(f"Archivo nuevo detectado: {archivo}")
                            self._handle_nuevo_archivo(archivo)
                        changes_detected = True
                    
                    # Detectar archivos eliminados
                    archivos_eliminados = set(last_scan.keys()) - set(current_files.keys())
                    if archivos_eliminados:
                        for archivo in archivos_eliminados:
                            self.log(f"Archivo eliminado detectado: {archivo}")
                            self._handle_archivo_eliminado(archivo)
                        changes_detected = True
                    
                    # Detectar archivos modificados
                    for archivo in current_files:
                        if archivo in last_scan and current_files[archivo] != last_scan[archivo]:
                            self.log(f"Archivo modificado detectado: {archivo}")
                            # Los archivos modificados no requieren acción especial
                            # ya que el contenido se maneja via checkout/checkin
                    
                    # Si hubo cambios, actualizar registro
                    if changes_detected:
                        self._scan_local_files()
                        self._register_with_dns_general()
                    
                    last_scan = current_files.copy()
                    
                except Exception as e:
                    self.log(f"Error en monitor de archivos: {e}")
                    time.sleep(5)  # Esperar más tiempo si hay error
        
        # Iniciar en hilo separado
        thread = threading.Thread(target=file_monitor, daemon=True)
        thread.start()
        self.log("Monitor de archivos iniciado")
    
    def _handle_nuevo_archivo(self, nombre_archivo: str):
        """Maneja la detección de un nuevo archivo local"""
        try:
            # Agregar a lista local si no existe
            with self.local_files_lock:
                existe = any(a["nombre_archivo"] == nombre_archivo for a in self.local_files)
                if not existe:
                    name, ext = os.path.splitext(nombre_archivo)
                    nuevo_archivo = {
                        "nombre_archivo": nombre_archivo,
                        "extension": ext,
                        "publicado": True,
                        "ttl": 3600,
                        "bandera": 0,
                        "ip_origen": self.host
                    }
                    self.local_files.append(nuevo_archivo)
                    self.log(f"Archivo '{nombre_archivo}' agregado a lista local")
        except Exception as e:
            self.log(f"Error manejando nuevo archivo {nombre_archivo}: {e}")
    
    def _handle_archivo_eliminado(self, nombre_archivo: str):
        """Maneja la detección de un archivo eliminado localmente"""
        try:
            # Remover de lista local
            with self.local_files_lock:
                self.local_files = [a for a in self.local_files if a["nombre_archivo"] != nombre_archivo]
                self.log(f"Archivo '{nombre_archivo}' removido de lista local")
            
            # Notificar al DNS General sobre la eliminación
            self._notificar_archivo_eliminado(nombre_archivo)
            
        except Exception as e:
            self.log(f"Error manejando archivo eliminado {nombre_archivo}: {e}")
    
    def _notificar_archivo_eliminado(self, nombre_archivo: str):
        """Notifica al DNS General que un archivo fue eliminado"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            notification = {
                "accion": "archivo_eliminado",
                "nombre_archivo": nombre_archivo,
                "server_id": self.server_id
            }
            
            sock.sendto(json.dumps(notification).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK":
                self.log(f"DNS General notificado sobre eliminación de '{nombre_archivo}'")
                if response.get("nuevo_propietario"):
                    self.log(f"Nuevo propietario asignado: {response.get('nuevo_propietario')}")
                elif response.get("archivo_eliminado_definitivamente"):
                    self.log(f"Archivo '{nombre_archivo}' eliminado definitivamente del sistema")
            
        except Exception as e:
            self.log(f"Error notificando eliminación: {e}")
        finally:
            if 'sock' in locals():
                sock.close()
        
    def _start_udp_listener(self):
        """Inicia un listener UDP para peticiones directas del DNS General"""
        def udp_server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Usar un puerto diferente para UDP (puerto + 1000)
                udp_port = self.port + 1000
                sock.bind((self.host, udp_port))
                self.log(f"Listener UDP iniciado en {self.host}:{udp_port}")
                
                while self.running:
                    try:
                        data, addr = sock.recvfrom(8192)
                        request = json.loads(data.decode('utf-8'))
                        
                        # Procesar petición directa
                        if request.get("via_dns_general"):
                            response = self._process_dns_general_request(request)
                        else:
                            response = {"status": "ERROR", "mensaje": "Petición no reconocida"}
                        
                        # Enviar respuesta
                        sock.sendto(json.dumps(response).encode('utf-8'), addr)
                        
                    except json.JSONDecodeError:
                        error_response = {"status": "ERROR", "mensaje": "JSON inválido"}
                        sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
                    except Exception as e:
                        self.log(f"Error en UDP listener: {e}")
                        error_response = {"status": "ERROR", "mensaje": str(e)}
                        try:
                            sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
                        except:
                            pass
                            
            except Exception as e:
                self.log(f"Error iniciando UDP listener: {e}")
            finally:
                sock.close()
        
        # Iniciar en hilo separado
        thread = threading.Thread(target=udp_server, daemon=True)
        thread.start()
        
    def _process_dns_general_request(self, request: Dict) -> Dict:
        """Procesa peticiones que llegan del DNS General"""
        accion = request.get("accion")
        
        if accion == "leer":
            return self._handle_leer_directo(request)
        elif accion == "escribir":
            return self._handle_escribir_directo(request)
        elif accion == "eliminar_temporal":
            return self._handle_eliminar_temporal(request)
        elif accion == "verificar_existencia":
            return self._handle_verificar_existencia(request)
        else:
            return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada vía UDP"}
    
    def _handle_verificar_existencia(self, request: Dict) -> Dict:
        """Verifica si un archivo existe localmente"""
        nombre_archivo = request.get("nombre_archivo")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        
        exists = os.path.exists(file_path) and not nombre_archivo.endswith('.temp_checkout')
        
        return {
            "status": "ACK",
            "exists": exists,
            "archivo": nombre_archivo,
            "server_id": self.server_id
        }
    
    def _handle_leer_directo(self, request: Dict) -> Dict:
        """Lee archivo local directamente (para peticiones del DNS General)"""
        nombre_archivo = request.get("nombre_archivo")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                return {
                    "status": "EXITO", 
                    "contenido": contenido,
                    "servidor_origen": self.server_id,
                    "procesado_por": self.server_id
                }
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error leyendo archivo: {e}"}
        else:
            return {"status": "ERROR", "mensaje": f"Archivo '{nombre_archivo}' no encontrado"}
    
    def _handle_escribir_directo(self, request: Dict) -> Dict:
        """Escribe archivo local directamente (para peticiones del DNS General)"""
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido", "")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        
        es_nuevo_archivo = not os.path.exists(file_path)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            # Si es un archivo nuevo, actualizar lista local y registro
            if es_nuevo_archivo:
                with self.local_files_lock:
                    name, ext = os.path.splitext(nombre_archivo)
                    nuevo_archivo = {
                        "nombre_archivo": nombre_archivo,
                        "extension": ext,
                        "publicado": True,
                        "ttl": 3600,
                        "bandera": 0,
                        "ip_origen": self.host
                    }
                    self.local_files.append(nuevo_archivo)
                
                # Actualizar registro en DNS General
                self._register_with_dns_general()
                
                tipo_operacion = "creacion"
                mensaje = f"Archivo '{nombre_archivo}' creado"
            else:
                tipo_operacion = "modificacion"
                mensaje = f"Archivo '{nombre_archivo}' modificado"
            
            return {
                "status": "EXITO",
                "mensaje": mensaje,
                "servidor_destino": self.server_id,
                "tipo_operacion": tipo_operacion,
                "procesado_por": self.server_id
            }
            
        except Exception as e:
            return {"status": "ERROR", "mensaje": f"Error escribiendo archivo: {e}"}
        """Inicia un listener UDP para peticiones directas del DNS General"""
        def udp_server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Usar un puerto diferente para UDP (puerto + 1000)
                udp_port = self.port + 1000
                sock.bind((self.host, udp_port))
                self.log(f"Listener UDP iniciado en {self.host}:{udp_port}")
                
                while self.running:
                    try:
                        data, addr = sock.recvfrom(8192)
                        request = json.loads(data.decode('utf-8'))
                        
                        # Procesar petición directa
                        if request.get("via_dns_general"):
                            response = self._process_dns_general_request(request)
                        else:
                            response = {"status": "ERROR", "mensaje": "Petición no reconocida"}
                        
                        # Enviar respuesta
                        sock.sendto(json.dumps(response).encode('utf-8'), addr)
                        
                    except json.JSONDecodeError:
                        error_response = {"status": "ERROR", "mensaje": "JSON inválido"}
                        sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
                    except Exception as e:
                        self.log(f"Error en UDP listener: {e}")
                        error_response = {"status": "ERROR", "mensaje": str(e)}
                        try:
                            sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
                        except:
                            pass
                            
            except Exception as e:
                self.log(f"Error iniciando UDP listener: {e}")
            finally:
                sock.close()
        
    def log(self, message):
        logging.info(f"[{self.server_id}] {message}")
        
    def _scan_local_files(self):
        """Escanea archivos locales"""
        with self.local_files_lock:
            self.local_files = []
            try:
                for filename in os.listdir(self.folder_path):
                    if os.path.isfile(os.path.join(self.folder_path, filename)):
                        name, ext = os.path.splitext(filename)
                        self.local_files.append({
                            "nombre_archivo": filename,
                            "extension": ext,
                            "publicado": True,  # Por defecto publicado
                            "ttl": 3600,
                            "bandera": 0,  # Original
                            "ip_origen": self.host
                        })
                        
                self.log(f"Escaneados {len(self.local_files)} archivos locales")
            except Exception as e:
                self.log(f"Error escaneando archivos locales: {e}")
    
    def _register_with_dns_general(self):
        """Registra el servidor con el DNS General"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            register_request = {
                "accion": "registrar_servidor",
                "server_id": self.server_id,
                "ip": self.host,
                "port": self.port,
                "archivos": self.local_files
            }
            
            sock.sendto(json.dumps(register_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK":
                self.log("Registrado exitosamente en DNS General")
            else:
                self.log(f"Error registrando en DNS General: {response}")
                
        except Exception as e:
            self.log(f"Error conectando con DNS General: {e}")
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _send_heartbeat(self):
        """Envía heartbeat al DNS General"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            
            heartbeat_request = {
                "accion": "heartbeat",
                "server_id": self.server_id
            }
            
            sock.sendto(json.dumps(heartbeat_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(1024)
            
        except Exception as e:
            self.log(f"Error enviando heartbeat: {e}")
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _start_heartbeat(self):
        """Inicia el hilo de heartbeat"""
        def heartbeat_loop():
            while self.running:
                time.sleep(30)  # Cada 30 segundos
                if self.running:
                    self._send_heartbeat()
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()
    
    def _find_file_location(self, nombre_archivo: str) -> Dict:
        """Encuentra dónde está ubicado un archivo"""
        # Primero buscar localmente
        with self.local_files_lock:
            for archivo in self.local_files:
                if archivo["nombre_archivo"] == nombre_archivo:
                    return {
                        "found": True,
                        "local": True,
                        "server_id": self.server_id,
                        "ip": self.host,
                        "port": self.port
                    }
        
        # Si no está local, consultar DNS General
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            query_request = {
                "accion": "consultar",
                "nombre_archivo": nombre_archivo
            }
            
            sock.sendto(json.dumps(query_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK":
                return {
                    "found": True,
                    "local": False,
                    "server_id": response["server_id"],
                    "ip": response["ip"],
                    "port": response["puerto"]
                }
            else:
                return {"found": False}
                
        except Exception as e:
            self.log(f"Error consultando DNS General: {e}")
            return {"found": False, "error": str(e)}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _request_remote_action(self, server_id: str, accion: str, nombre_archivo: str, contenido: str = None) -> Dict:
        """Solicita una acción a un servidor remoto a través del DNS General"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            remote_request = {
                "accion": "solicitar_remoto",
                "server_id": server_id,
                "accion": accion,
                "nombre_archivo": nombre_archivo,
                "origen_server_id": self.server_id
            }
            
            if contenido is not None:
                remote_request["contenido"] = contenido
            
            sock.sendto(json.dumps(remote_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            return response
            
        except Exception as e:
            self.log(f"Error en petición remota: {e}")
            return {"status": "ERROR", "mensaje": str(e)}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _handle_secure_message(self, request: Dict, peer_addr: Tuple[str, int]):
        """Maneja mensajes seguros recibidos de peers"""
        try:
            accion = request.get("accion")
            self.log(f"Mensaje seguro de {peer_addr}: {accion}")
            
            if accion == "consultar":
                response = self._handle_consultar(request)
            elif accion == "listar_archivos":
                response = self._handle_listar_archivos()
            elif accion == "leer":
                response = self._handle_leer(request)
            elif accion == "escribir":
                response = self._handle_escribir(request)
            elif accion == "salir":
                response = {"status": "ACK", "mensaje": "Desconexión confirmada"}
            else:
                response = {"status": "ERROR", "mensaje": f"Acción '{accion}' no reconocida"}
            
            # Enviar respuesta cifrada
            self.peer_connector.send_message(response, peer_addr)
            
        except Exception as e:
            self.log(f"Error procesando mensaje seguro: {e}")
            error_response = {"status": "ERROR", "mensaje": str(e)}
            self.peer_connector.send_message(error_response, peer_addr)
    
    def _handle_consultar(self, request: Dict) -> Dict:
        """Maneja consulta de archivo específico"""
        nombre_archivo = request.get("nombre_archivo")
        if not nombre_archivo:
            return {"status": "ERROR", "mensaje": "Nombre de archivo requerido"}
        
        location_info = self._find_file_location(nombre_archivo)
        
        if location_info["found"]:
            return {
                "status": "ACK",
                "nombre_archivo": nombre_archivo,
                "ip": location_info["ip"],
                "puerto": location_info["port"],
                "local": location_info["local"],
                "server_id": location_info["server_id"],
                "ttl": 3600
            }
        else:
            return {
                "status": "NACK",
                "mensaje": f"Archivo '{nombre_archivo}' no encontrado"
            }
    
    def _handle_listar_archivos(self) -> Dict:
        """Lista todos los archivos disponibles (locales + remotos conocidos)"""
        try:
            # Obtener lista actualizada del DNS General
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            list_request = {"accion": "listar_archivos"}
            sock.sendto(json.dumps(list_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK":
                return response
            else:
                # Fallback a archivos locales
                with self.local_files_lock:
                    return {
                        "status": "ACK",
                        "archivos": self.local_files.copy(),
                        "total": len(self.local_files),
                        "fuente": "local_only"
                    }
                    
        except Exception as e:
            self.log(f"Error listando archivos: {e}")
            # Fallback a archivos locales
            with self.local_files_lock:
                return {
                    "status": "ACK", 
                    "archivos": self.local_files.copy(),
                    "total": len(self.local_files),
                    "fuente": "local_only",
                    "error": str(e)
                }
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _handle_leer(self, request: Dict) -> Dict:
        """Maneja lectura de archivo CON VERIFICACIÓN DE BLOQUEO"""
        nombre_archivo = request.get("nombre_archivo")
        
        # VERIFICAR SI EL ARCHIVO ESTÁ BLOQUEADO ANTES DE LEER
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            bloqueo_request = {
                "accion": "verificar_bloqueo",
                "nombre_archivo": nombre_archivo
            }
            
            sock.sendto(json.dumps(bloqueo_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            # Si está bloqueado, denegar lectura
            if response.get("bloqueado"):
                sock.close()
                return {
                    "status": "ERROR", 
                    "mensaje": f"Archivo '{nombre_archivo}' bloqueado para escritura por {response.get('bloqueado_por')}. No disponible para lectura."
                }
            
            sock.close()
        except Exception as e:
            self.log(f"Error verificando bloqueo: {e}")
        
        # Primero intentar leer localmente
        file_path = os.path.join(self.folder_path, nombre_archivo)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                return {"status": "EXITO", "contenido": contenido, "fuente": "local"}
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error leyendo archivo local: {e}"}
        
        # Si no está local, solicitar al DNS General que maneje la lectura distribuida
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            read_request = {
                "accion": "leer",
                "nombre_archivo": nombre_archivo,
                "requesting_server": self.server_id
            }
            
            sock.sendto(json.dumps(read_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            # Añadir información de que vino del sistema distribuido
            if response.get("status") == "EXITO":
                response["fuente"] = f"distribuido_via_{response.get('servidor_origen', 'remoto')}"
            
            return response
            
        except Exception as e:
            self.log(f"Error solicitando lectura distribuida: {e}")
            return {"status": "ERROR", "mensaje": f"Archivo no encontrado: {e}"}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _handle_escribir(self, request: Dict) -> Dict:
        """Maneja escritura de archivo con sistema de checkout/check-in"""
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido", "")
        
        # Si el archivo existe localmente, escribir directamente
        file_path = os.path.join(self.folder_path, nombre_archivo)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                
                self.log(f"Archivo '{nombre_archivo}' modificado localmente")
                return {
                    "status": "EXITO", 
                    "mensaje": f"Archivo '{nombre_archivo}' guardado localmente",
                    "fuente": "local"
                }
                
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error escribiendo archivo: {e}"}
        
        # Si no existe localmente, iniciar proceso de checkout/check-in
        return self._handle_escritura_remota(nombre_archivo, contenido)
    
    def _handle_escritura_remota(self, nombre_archivo: str, contenido: str) -> Dict:
        """Maneja escritura con sistema de BLOQUEO EXCLUSIVO mejorado"""
        try:
            # Paso 1: SOLICITAR BLOQUEO EXCLUSIVO
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            bloqueo_request = {
                "accion": "solicitar_bloqueo",
                "nombre_archivo": nombre_archivo,
                "requesting_server": self.server_id,
                "client_id": f"{self.server_id}_client_{int(time.time())}"
            }
            
            sock.sendto(json.dumps(bloqueo_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "BLOQUEADO":
                sock.close()
                return {
                    "status": "ERROR",
                    "mensaje": f"Archivo bloqueado para escritura por {response.get('bloqueado_por')}. Intente más tarde."
                }
            elif response.get("status") != "BLOQUEO_CONCEDIDO":
                sock.close()
                return {"status": "ERROR", "mensaje": f"No se pudo obtener bloqueo: {response.get('mensaje')}"}
            
            sock.close()
            self.log(f"BLOQUEO CONCEDIDO para '{nombre_archivo}' por 10 minutos")
            
            # Paso 2: REALIZAR CHECKOUT (obtener copia para edición)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            checkout_request = {
                "accion": "checkout_archivo",
                "nombre_archivo": nombre_archivo,
                "requesting_server": self.server_id
            }
            
            sock.sendto(json.dumps(checkout_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            sock.close()
            
            if response.get("status") not in ["CHECKOUT_EXITOSO", "NUEVO_ARCHIVO"]:
                # Liberar bloqueo si checkout falla
                self._liberar_bloqueo_archivo(nombre_archivo)
                return {"status": "ERROR", "mensaje": f"Error en checkout: {response.get('mensaje')}"}
            
            # Paso 3: CREAR COPIA LOCAL TEMPORAL
            contenido_original = response.get("contenido", "")
            file_path = os.path.join(self.folder_path, nombre_archivo)
            temp_file_path = file_path + ".temp_editing"
            
            try:
                # Crear archivo temporal con contenido editado
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                
                self.log(f"Copia temporal creada: {temp_file_path}")
                
                # Paso 4: REALIZAR CHECK-IN con verificación de archivo original
                checkin_response = self._realizar_checkin_con_bloqueo(nombre_archivo, contenido)
                
                # Paso 5: LIMPIAR y LIBERAR BLOQUEO
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        self.log(f"Archivo temporal eliminado: {temp_file_path}")
                except Exception as e:
                    self.log(f"Error eliminando temporal: {e}")
                
                # Liberar bloqueo
                self._liberar_bloqueo_archivo(nombre_archivo)
                
                return checkin_response
                
            except Exception as e:
                # Limpiar en caso de error
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                except:
                    pass
                self._liberar_bloqueo_archivo(nombre_archivo)
                return {"status": "ERROR", "mensaje": f"Error en edición local: {e}"}
                
        except Exception as e:
            self.log(f"Error en escritura remota con bloqueo: {e}")
            self._liberar_bloqueo_archivo(nombre_archivo)
            return {"status": "ERROR", "mensaje": f"Error en escritura remota: {e}"}
    
    def _realizar_checkin_con_bloqueo(self, nombre_archivo: str, contenido: str) -> Dict:
        """Realiza check-in verificando si el archivo original aún existe"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            checkin_request = {
                "accion": "checkin_archivo",
                "nombre_archivo": nombre_archivo,
                "contenido": contenido,
                "requesting_server": self.server_id
            }
            
            sock.sendto(json.dumps(checkin_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "CHECKIN_EXITOSO":
                return {
                    "status": "EXITO",
                    "mensaje": f"Archivo '{nombre_archivo}' actualizado en servidor original {response.get('servidor_final')}",
                    "fuente": f"remoto_{response.get('servidor_final')}"
                }
            elif response.get("status") == "CHECKIN_NUEVO_PROPIETARIO":
                # CASO ESPECIAL: El archivo original desapareció, este servidor se vuelve propietario
                file_path = os.path.join(self.folder_path, nombre_archivo)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(contenido)
                    
                    # Actualizar lista local
                    with self.local_files_lock:
                        name, ext = os.path.splitext(nombre_archivo)
                        nuevo_archivo = {
                            "nombre_archivo": nombre_archivo,
                            "extension": ext,
                            "publicado": True,
                            "ttl": 3600,
                            "bandera": 0,
                            "ip_origen": self.host
                        }
                        # Verificar si ya existe en la lista
                        existe = any(a["nombre_archivo"] == nombre_archivo for a in self.local_files)
                        if not existe:
                            self.local_files.append(nuevo_archivo)
                    
                    # Re-registrar con DNS General
                    self._register_with_dns_general()
                    
                    self.log(f"NUEVO PROPIETARIO: '{nombre_archivo}' ahora pertenece a {self.server_id}")
                    
                    return {
                        "status": "EXITO",
                        "mensaje": f"Archivo original eliminado. '{nombre_archivo}' ahora es propiedad de este servidor",
                        "fuente": "local_nuevo_propietario"
                    }
                    
                except Exception as e:
                    return {"status": "ERROR", "mensaje": f"Error guardando como nuevo propietario: {e}"}
            
            # AÑADIR ESTE CASO
            elif response.get("status") == "EXITO" and response.get("tipo_operacion") == "creacion":
                self.log(f"Check-in resultó en creación. '{nombre_archivo}' ahora es propiedad de este servidor.")
               # CASO ESPECIAL: El archivo original desapareció, este servidor se vuelve propietario
                file_path = os.path.join(self.folder_path, nombre_archivo)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(contenido)
                    
                    # Actualizar lista local
                    with self.local_files_lock:
                        name, ext = os.path.splitext(nombre_archivo)
                        nuevo_archivo = {
                            "nombre_archivo": nombre_archivo,
                            "extension": ext,
                            "publicado": True,
                            "ttl": 3600,
                            "bandera": 0,
                            "ip_origen": self.host
                        }
                        # Verificar si ya existe en la lista
                        existe = any(a["nombre_archivo"] == nombre_archivo for a in self.local_files)
                        if not existe:
                            self.local_files.append(nuevo_archivo)
                    
                    # Re-registrar con DNS General
                    self._register_with_dns_general()
                    
                    self.log(f"NUEVO PROPIETARIO: '{nombre_archivo}' ahora pertenece a {self.server_id}")
                    return {
                        "status": "EXITO",
                        "mensaje": f"Archivo '{nombre_archivo}' creado y ahora es propiedad de este servidor.",
                        "fuente": "local_nuevo_propietario"
                    }
                except Exception as e:
                    return {"status": "ERROR", "mensaje": f"Error guardando como nuevo propietario: {e}"}
            else:
                # Fallback para otros errores
                return {
                    "status": "ERROR",
                    "mensaje": f"Error en check-in: {response.get('mensaje', 'Error desconocido')}",
                    "debug_response": response
                }
                
        except Exception as e:
            self.log(f"Error en check-in: {e}")
            return {"status": "ERROR", "mensaje": f"Error en check-in: {e}"}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _liberar_bloqueo_archivo(self, nombre_archivo: str):
        """Libera el bloqueo de un archivo"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            liberar_request = {
                "accion": "liberar_bloqueo",
                "nombre_archivo": nombre_archivo,
                "requesting_server": self.server_id
            }
            
            sock.sendto(json.dumps(liberar_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "BLOQUEO_LIBERADO":
                self.log(f"Bloqueo liberado exitosamente para '{nombre_archivo}'")
            else:
                self.log(f"Error liberando bloqueo para '{nombre_archivo}': {response.get('mensaje')}")
                
        except Exception as e:
            self.log(f"Error liberando bloqueo: {e}")
        finally:
            if 'sock' in locals():
                sock.close()# server_distributed.py - Servidor que se conecta al DNS General
    
    def _realizar_checkin(self, nombre_archivo: str, contenido: str) -> Dict:
        """Realiza check-in del archivo editado"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            checkin_request = {
                "accion": "checkin_archivo",
                "nombre_archivo": nombre_archivo,
                "contenido": contenido,
                "requesting_server": self.server_id
            }
            
            sock.sendto(json.dumps(checkin_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "CHECKIN_EXITOSO":
                return {
                    "status": "EXITO",
                    "mensaje": f"Archivo '{nombre_archivo}' actualizado en {response.get('servidor_final')}",
                    "fuente": f"remoto_{response.get('servidor_final')}"
                }
            elif response.get("status") == "CHECKIN_NUEVO_PROPIETARIO":
                # El servidor actual se convirtió en propietario, mantener archivo localmente
                file_path = os.path.join(self.folder_path, nombre_archivo)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(contenido)
                    
                    # Actualizar lista local
                    with self.local_files_lock:
                        name, ext = os.path.splitext(nombre_archivo)
                        nuevo_archivo = {
                            "nombre_archivo": nombre_archivo,
                            "extension": ext,
                            "publicado": True,
                            "ttl": 3600,
                            "bandera": 0,
                            "ip_origen": self.host
                        }
                        # Verificar si ya existe en la lista
                        existe = any(a["nombre_archivo"] == nombre_archivo for a in self.local_files)
                        if not existe:
                            self.local_files.append(nuevo_archivo)
                    
                    # Re-registrar con DNS General
                    self._register_with_dns_general()
                    
                    return {
                        "status": "EXITO",
                        "mensaje": f"Archivo original perdido. '{nombre_archivo}' ahora es propiedad de este servidor",
                        "fuente": "local_nuevo_propietario"
                    }
                    
                except Exception as e:
                    return {"status": "ERROR", "mensaje": f"Error guardando como nuevo propietario: {e}"}
            
            else:
                return {"status": "ERROR", "mensaje": f"Error en check-in: {response.get('mensaje')}"}
                
        except Exception as e:
            self.log(f"Error en check-in: {e}")
            return {"status": "ERROR", "mensaje": f"Error en check-in: {e}"}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _handle_eliminar_temporal(self, request: Dict) -> Dict:
        """Elimina archivo temporal tras check-in exitoso"""
        nombre_archivo = request.get("nombre_archivo")
        temp_file_path = os.path.join(self.folder_path, nombre_archivo + ".temp_checkout")
        
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                self.log(f"Archivo temporal eliminado: {temp_file_path}")
                return {"status": "EXITO", "mensaje": "Archivo temporal eliminado"}
            else:
                return {"status": "ERROR", "mensaje": "Archivo temporal no encontrado"}
        except Exception as e:
            return {"status": "ERROR", "mensaje": f"Error eliminando temporal: {e}"}
        
    def _start_file_monitor(self):
        """Inicia el monitor de archivos para detectar cambios locales (Versión Simplificada)"""
        def file_monitor():
            last_scan = {}  # {nombre_archivo: timestamp_modificacion}
            
            while self.running:
                try:
                    time.sleep(10)  # Verificar cada 10 segundos
                    if not self.running:
                        break
                    
                    current_files = {}
                    changes_detected = False
                    
                    # Escanear archivos físicos actuales en la carpeta
                    if os.path.exists(self.folder_path):
                        for filename in os.listdir(self.folder_path):
                            if filename.endswith(('.temp_checkout', '.temp_editing')):
                                continue  # Ignorar archivos temporales
                            
                            filepath = os.path.join(self.folder_path, filename)
                            if os.path.isfile(filepath):
                                mtime = os.path.getmtime(filepath)
                                current_files[filename] = mtime
                    
                    # Detectar archivos nuevos locales
                    nuevos_archivos = set(current_files.keys()) - set(last_scan.keys())
                    if nuevos_archivos:
                        for archivo in nuevos_archivos:
                            self.log(f"Archivo nuevo detectado localmente: {archivo}")
                            self._handle_nuevo_archivo(archivo)
                        changes_detected = True
                    
                    # Detectar archivos eliminados localmente
                    archivos_eliminados = set(last_scan.keys()) - set(current_files.keys())
                    if archivos_eliminados:
                        for archivo in archivos_eliminados:
                            self.log(f"Archivo eliminado localmente: {archivo}")
                            self._handle_archivo_eliminado(archivo)
                        changes_detected = True
                    
                    # Si hubo cambios, escanear de nuevo y re-registrar en el DNS General
                    if changes_detected:
                        self._scan_local_files()
                        self._register_with_dns_general()
                    
                    last_scan = current_files.copy()
                    
                except Exception as e:
                    self.log(f"Error en monitor de archivos: {e}")
                    time.sleep(10)
        
        # Iniciar en hilo separado
        thread = threading.Thread(target=file_monitor, daemon=True)
        thread.start()
        self.log("Monitor de archivos simplificado iniciado")
    
    def _consultar_archivos_dns_local(self) -> Dict:
        """Consulta los archivos disponibles en el DNS local"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            
            # Construir consulta según el tipo de DNS
            if self.dns_local_ip == "127.0.0.12":  # Christian
                consulta = {"type": "list"}
            elif self.dns_local_ip == "127.0.0.8":  # Marco
                consulta = {"accion": "listar_archivos"}
            elif self.dns_local_ip == "127.0.0.9":  # Dan
                consulta = {"accion": "listar_archivos"}
            elif self.dns_local_ip == "127.0.0.10":  # Gus
                consulta = {"action": "list_all_files"}
            else:  # Original y otros
                consulta = {"accion": "listar_archivos"}
            
            sock.sendto(json.dumps(consulta).encode('utf-8'), (self.dns_local_ip, self.dns_local_port))
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            # Normalizar respuesta según el tipo de DNS
            if self.dns_local_ip == "127.0.0.12":  # Christian
                if response.get("response") == "ACK":
                    archivos = []
                    for file_info in response.get("files", []):
                        archivos.append({
                            "nombre_archivo": f"{file_info['name']}.{file_info['extension']}",
                            "publicado": True,
                            "ttl": 3600
                        })
                    return {"status": "ACK", "archivos": archivos}
            elif self.dns_local_ip == "127.0.0.8":  # Marco
                if response.get("status") == "ACK":
                    archivos = []
                    for file_info in response.get("files", []):
                        archivos.append({
                            "nombre_archivo": f"{file_info['name']}.{file_info['extension']}",
                            "publicado": True,
                            "ttl": file_info.get("ttl", 3600)
                        })
                    return {"status": "ACK", "archivos": archivos}
            elif self.dns_local_ip == "127.0.0.10":  # Gus
                if response.get("status") == "ACK":
                    archivos = []
                    for file_info in response.get("files", []):
                        if file_info.get("can_publish", False):
                            archivos.append({
                                "nombre_archivo": f"{file_info['name']}.{file_info['extension']}",
                                "publicado": True,
                                "ttl": file_info.get("ttl", 3600)
                            })
                    return {"status": "ACK", "archivos": archivos}
            else:  # Original y Dan
                return response
                
            return {"status": "ERROR", "mensaje": "DNS no respondió correctamente"}
            
        except Exception as e:
            self.log(f"Error consultando DNS local: {e}")
            return {"status": "ERROR", "mensaje": str(e)}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _handle_nuevo_archivo(self, nombre_archivo: str):
        """Maneja la detección de un nuevo archivo local"""
        try:
            # Agregar a lista local si no existe
            with self.local_files_lock:
                existe = any(a["nombre_archivo"] == nombre_archivo for a in self.local_files)
                if not existe:
                    name, ext = os.path.splitext(nombre_archivo)
                    nuevo_archivo = {
                        "nombre_archivo": nombre_archivo,
                        "extension": ext,
                        "publicado": True,
                        "ttl": 3600,
                        "bandera": 0,
                        "ip_origen": self.host
                    }
                    self.local_files.append(nuevo_archivo)
                    self.log(f"Archivo '{nombre_archivo}' agregado a lista local")
        except Exception as e:
            self.log(f"Error manejando nuevo archivo {nombre_archivo}: {e}")
    
    def _handle_archivo_eliminado(self, nombre_archivo: str):
        """Maneja la detección de un archivo eliminado localmente"""
        try:
            # Remover de lista local
            with self.local_files_lock:
                self.local_files = [a for a in self.local_files if a["nombre_archivo"] != nombre_archivo]
                self.log(f"Archivo '{nombre_archivo}' removido de lista local")
            
            # Notificar al DNS General sobre la eliminación
            self._notificar_archivo_eliminado(nombre_archivo)
            
        except Exception as e:
            self.log(f"Error manejando archivo eliminado {nombre_archivo}: {e}")
    
    def _notificar_archivo_eliminado(self, nombre_archivo: str):
        """Notifica al DNS General que un archivo fue eliminado"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            notification = {
                "accion": "archivo_eliminado",
                "nombre_archivo": nombre_archivo,
                "server_id": self.server_id
            }
            
            sock.sendto(json.dumps(notification).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK":
                self.log(f"DNS General notificado sobre eliminación de '{nombre_archivo}'")
                if response.get("nuevo_propietario"):
                    self.log(f"Nuevo propietario asignado: {response.get('nuevo_propietario')}")
                elif response.get("archivo_eliminado_definitivamente"):
                    self.log(f"Archivo '{nombre_archivo}' eliminado definitivamente del sistema")
            
        except Exception as e:
            self.log(f"Error notificando eliminación: {e}")
        finally:
            if 'sock' in locals():
                sock.close()
    
    def start(self):
        """Inicia el servidor distribuido"""
        self.log(f"Servidor distribuido iniciado en {self.host}:{self.port}")
        self.log(f"DNS Local: {self.dns_local_ip}:{self.dns_local_port}")
        self.log(f"DNS General: {DNS_GENERAL_IP}:{DNS_GENERAL_PORT}")
        self.log(f"Carpeta local: {os.path.abspath(self.folder_path)}")
        
        try:
            # Bucle principal de escucha segura
            while self.running:
                payload, addr = self.transport.listen()
                if payload and addr:
                    # PeerConnector maneja automáticamente handshakes y descifrado
                    self.peer_connector.handle_incoming_packet(payload, addr)
                    
        except KeyboardInterrupt:
            self.log("Servidor detenido por el usuario")
        except Exception as e:
            self.log(f"Error en el servidor: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el servidor de manera limpia"""
        self.running = False
        if self.peer_connector:
            self.peer_connector.stop()
        self.log("Servidor detenido")

# Función para crear configuraciones de servidores
def crear_servidor(config_name: str):
    """Crea un servidor leyendo la configuración de network_config.json"""
    if config_name not in net_config['peers']:
        print(f"Configuración '{config_name}' no encontrada en network_config.json.")
        return None

    peer_config = net_config['peers'][config_name]

    server_config = {
        "server_id": config_name,
        "host": peer_config['server_ip'],
        "port": peer_config['server_port'],
        "dns_local_ip": peer_config['dns_ip'],
        "dns_local_port": peer_config['dns_port'],
        "folder_path": f"archivos_{config_name.lower()}"
    }
    return ServidorDistribuido(**server_config)

if __name__ == "__main__":
    import sys
    
    print("=== Servidor Distribuido ===")
    print("Conectado al DNS General para comunicación entre servidores")
    print("Comunicación cifrada con clientes")
    print("Ctrl+C para detener\n")
    
    if len(sys.argv) != 2:
        print("Uso: python server_distributed.py <server1|server2|server3>")
        print("Ejemplo: python server_distributed.py server1")
        sys.exit(1)
    
    config_name = sys.argv[1]
    server = crear_servidor(config_name)
    
    if server:
        server.start()
    else:
        sys.exit(1)