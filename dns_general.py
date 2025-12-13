# dns_general.py - DNS General para comunicación entre servidores
import socket
import json
import threading
import time
import logging
import os
from typing import Dict, List, Tuple
from datetime import datetime

# Configuración
# --- Cargar Configuración ---
with open('network_config.json', 'r') as f:
    net_config = json.load(f)

# Configuración
DNS_GENERAL_IP = net_config['dns_general']['listen_ip']
DNS_GENERAL_PORT = net_config['dns_general']['port']
LOG_FILE = "dns_general.log"

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class DNSGeneral:
    def __init__(self, host=DNS_GENERAL_IP, port=DNS_GENERAL_PORT):
        self.host = host
        self.port = port
        self.running = True
        
        # Registro de servidores conectados
        self.registered_servers = {}  # {server_id: {"ip": ip, "port": port, "archivos": [], "last_update": timestamp}}
        
        # Índice global de archivos
        self.global_file_index = {}  # {nombre_archivo: [{"server_id": id, "ip": ip, "port": port, "ttl": ttl}]}
        
        # Sistema de bloqueos de archivos para escritura exclusiva
        self.file_locks = {}  # {nombre_archivo: {"locked_by": server_id, "client_id": client_id, "timestamp": time, "operation": "write"}}
        
        self.lock = threading.Lock()
        
    def solicitar_bloqueo_archivo(self, request: Dict) -> Dict:
        """Solicita bloqueo exclusivo de un archivo para escritura"""
        nombre_archivo = request.get("nombre_archivo")
        server_solicitante = request.get("requesting_server")
        client_id = request.get("client_id", f"{server_solicitante}_client")
        
        with self.lock:
            # Verificar si el archivo ya está bloqueado
            if nombre_archivo in self.file_locks:
                lock_info = self.file_locks[nombre_archivo]
                current_time = time.time()
                
                # Verificar si el bloqueo ha expirado (10 minutos)
                if current_time - lock_info["timestamp"] > 600:
                    self.log(f"Bloqueo expirado para {nombre_archivo}, liberando...")
                    del self.file_locks[nombre_archivo]
                else:
                    # Archivo bloqueado por otro cliente
                    return {
                        "status": "BLOQUEADO",
                        "mensaje": f"Archivo '{nombre_archivo}' bloqueado para escritura",
                        "bloqueado_por": lock_info["locked_by"],
                        "desde": lock_info["timestamp"]
                    }
            
            # Crear bloqueo
            self.file_locks[nombre_archivo] = {
                "locked_by": server_solicitante,
                "client_id": client_id,
                "timestamp": time.time(),
                "operation": "write"
            }
            
            self.log(f"Archivo '{nombre_archivo}' bloqueado para escritura por {server_solicitante}")
            
            return {
                "status": "BLOQUEO_CONCEDIDO",
                "mensaje": f"Archivo '{nombre_archivo}' bloqueado exitosamente",
                "expira_en": 600  # 10 minutos
            }
    
    def liberar_bloqueo_archivo(self, request: Dict) -> Dict:
        """Libera el bloqueo de un archivo"""
        nombre_archivo = request.get("nombre_archivo")
        server_solicitante = request.get("requesting_server")
        
        with self.lock:
            if nombre_archivo in self.file_locks:
                lock_info = self.file_locks[nombre_archivo]
                
                # Verificar que sea el mismo servidor que lo bloqueó
                if lock_info["locked_by"] == server_solicitante:
                    del self.file_locks[nombre_archivo]
                    self.log(f"Bloqueo liberado para '{nombre_archivo}' por {server_solicitante}")
                    
                    return {
                        "status": "BLOQUEO_LIBERADO",
                        "mensaje": f"Archivo '{nombre_archivo}' desbloqueado"
                    }
                else:
                    return {
                        "status": "ERROR",
                        "mensaje": f"Solo {lock_info['locked_by']} puede liberar este bloqueo"
                    }
            else:
                return {
                    "status": "ERROR",
                    "mensaje": f"Archivo '{nombre_archivo}' no está bloqueado"
                }
    
    def verificar_bloqueo_archivo(self, request: Dict) -> Dict:
        """Verifica si un archivo está bloqueado"""
        nombre_archivo = request.get("nombre_archivo")
        
        with self.lock:
            if nombre_archivo in self.file_locks:
                lock_info = self.file_locks[nombre_archivo]
                current_time = time.time()
                
                # Verificar si el bloqueo ha expirado
                if current_time - lock_info["timestamp"] > 600:
                    del self.file_locks[nombre_archivo]
                    return {"status": "LIBRE", "bloqueado": False}
                
                return {
                    "status": "BLOQUEADO",
                    "bloqueado": True,
                    "bloqueado_por": lock_info["locked_by"],
                    "desde": lock_info["timestamp"],
                    "expira_en": 600 - (current_time - lock_info["timestamp"])
                }
            else:
                return {"status": "LIBRE", "bloqueado": False}
        
    def log(self, message):
        logging.info(message)
        
    def register_server(self, server_info: Dict) -> Dict:
        """Registra un servidor en el DNS General y actualiza el conteo total."""
        server_id = server_info.get("server_id")
        ip = server_info.get("ip")
        port = server_info.get("port")
        archivos = server_info.get("archivos", [])
        
        if not all([server_id, ip, port]):
            return {"status": "ERROR", "mensaje": "Información de servidor incompleta"}
        
        with self.lock:
            self.registered_servers[server_id] = {
                "ip": ip,
                "port": port,
                "archivos": archivos,
                "last_update": datetime.now().timestamp()
            }
            
            self._update_global_index(server_id, archivos, ip, port)
            
        self.log(f"Servidor {server_id} registrado con {len(archivos)} archivos.")
        
        # --- CAMBIO: Añadimos un log con el conteo total ---
        self.log(f"Índice actualizado. Total de archivos únicos en el sistema: {len(self.global_file_index)}")
        
        return {"status": "ACK", "mensaje": f"Servidor {server_id} registrado correctamente"}
    
    def _update_global_index(self, server_id: str, archivos: List[Dict], ip: str, port: int):
        """Actualiza el índice global con archivos de un servidor"""
        # Limpiar archivos antiguos de este servidor
        for nombre_archivo in list(self.global_file_index.keys()):
            self.global_file_index[nombre_archivo] = [
                entry for entry in self.global_file_index[nombre_archivo] 
                if entry["server_id"] != server_id
            ]
            if not self.global_file_index[nombre_archivo]:
                del self.global_file_index[nombre_archivo]
        
        # Añadir archivos nuevos
        for archivo in archivos:
            if archivo.get("publicado", False):
                nombre_archivo = archivo["nombre_archivo"]
                if nombre_archivo not in self.global_file_index:
                    self.global_file_index[nombre_archivo] = []
                
                self.global_file_index[nombre_archivo].append({
                    "server_id": server_id,
                    "ip": ip,
                    "port": port,
                    "ttl": archivo.get("ttl", 3600),
                    "bandera": archivo.get("bandera", 0)
                })
    
    def consultar_archivo(self, request: Dict) -> Dict:
        """Consulta dónde se encuentra un archivo específico"""
        nombre_archivo = request.get("nombre_archivo")
        
        with self.lock:
            if nombre_archivo in self.global_file_index:
                # Retornar el primer servidor que tenga el archivo
                archivo_info = self.global_file_index[nombre_archivo][0]
                return {
                    "status": "ACK",
                    "nombre_archivo": nombre_archivo,
                    "ip": archivo_info["ip"],
                    "puerto": archivo_info["port"],
                    "server_id": archivo_info["server_id"],
                    "ttl": archivo_info["ttl"],
                    "bandera": archivo_info["bandera"]
                }
            else:
                return {
                    "status": "NACK",
                    "mensaje": f"Archivo '{nombre_archivo}' no encontrado en ningún servidor"
                }
    
    def listar_archivos_globales(self) -> Dict:
        """Lista todos los archivos disponibles en el sistema"""
        with self.lock:
            archivos_globales = []
            for nombre_archivo, servers in self.global_file_index.items():
                # Tomar información del primer servidor (principal)
                server_info = servers[0]
                archivos_globales.append({
                    "nombre_archivo": nombre_archivo,
                    "servidor_principal": server_info["server_id"],
                    "ip": server_info["ip"],
                    "puerto": server_info["port"],
                    "ttl": server_info["ttl"],
                    "replicas": len(servers),
                    "bandera": server_info["bandera"],
                    "publicado": True
                })
            
            return {
                "status": "ACK",
                "archivos": archivos_globales,
                "total": len(archivos_globales),
                "servidores_activos": len(self.registered_servers)
            }
    
    def solicitar_accion_remota(self, request: Dict) -> Dict:
        """Solicita una acción a un servidor remoto"""
        server_id = request.get("server_id")
        accion = request.get("accion")
        
        if server_id not in self.registered_servers:
            return {"status": "ERROR", "mensaje": f"Servidor {server_id} no registrado"}
        
        server_info = self.registered_servers[server_id]
        
        try:
            # Usar UDP directo al servidor (puerto + 1000)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            # Preparar petición para el servidor remoto
            remote_request = {
                "accion": accion,
                "nombre_archivo": request.get("nombre_archivo"),
                "contenido": request.get("contenido"),
                "via_dns_general": True,
                "origen_request": request.get("origen_server_id", "DNS_GENERAL")
            }
            
            # Conectar al puerto UDP del servidor (puerto original + 1000)
            server_udp_port = server_info["port"] + 1000
            server_addr = (server_info["ip"], server_udp_port)
            
            self.log(f"Enviando petición {accion} a {server_id} via UDP {server_addr}")
            
            sock.sendto(json.dumps(remote_request).encode('utf-8'), server_addr)
            
            # Esperar respuesta
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            self.log(f"Respuesta de {server_id}: {response.get('status', 'UNKNOWN')}")
            return response
            
        except Exception as e:
            self.log(f"Error en solicitud remota a {server_id}: {e}")
            return {"status": "ERROR", "mensaje": f"Error comunicándose con servidor {server_id}: {e}"}
        finally:
            if 'sock' in locals():
                sock.close()
    
    def leer_archivo_distribuido(self, request: Dict) -> Dict:
        """Lee un archivo que puede estar en cualquier servidor del sistema"""
        nombre_archivo = request.get("nombre_archivo")
        
        # Buscar dónde está el archivo
        with self.lock:
            if nombre_archivo in self.global_file_index:
                # Tomar el primer servidor que tenga el archivo
                archivo_info = self.global_file_index[nombre_archivo][0]
                server_id = archivo_info["server_id"]
                
                # Solicitar la lectura al servidor correspondiente
                read_request = {
                    "server_id": server_id,
                    "accion": "leer",
                    "nombre_archivo": nombre_archivo,
                    "origen_server_id": request.get("requesting_server", "DNS_GENERAL")
                }
                
                response = self.solicitar_accion_remota(read_request)
                
                if response.get("status") == "EXITO":
                    # Añadir información sobre dónde se leyó el archivo
                    response["servidor_origen"] = server_id
                    response["via_dns_general"] = True
                
                return response
            else:
                return {
                    "status": "ERROR",
                    "mensaje": f"Archivo '{nombre_archivo}' no encontrado en el sistema"
                }
    
    def escribir_archivo_distribuido(self, request: Dict) -> Dict:
        """Escribe un archivo que puede estar en cualquier servidor del sistema"""
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido", "")
        
        # Buscar si el archivo ya existe
        with self.lock:
            if nombre_archivo in self.global_file_index:
                # El archivo existe, escribir en el servidor que lo tiene
                archivo_info = self.global_file_index[nombre_archivo][0]
                server_id = archivo_info["server_id"]
                
                write_request = {
                    "server_id": server_id,
                    "accion": "escribir", 
                    "nombre_archivo": nombre_archivo,
                    "contenido": contenido,
                    "origen_server_id": request.get("requesting_server", "DNS_GENERAL")
                }
                
                response = self.solicitar_accion_remota(write_request)
                
                if response.get("status") == "EXITO":
                    response["servidor_destino"] = server_id
                    response["via_dns_general"] = True
                    response["tipo_operacion"] = "modificacion"
                
                return response
            else:
                # El archivo no existe, se puede crear en cualquier servidor
                # Por simplicidad, usar el primer servidor disponible
                if self.registered_servers:
                    server_id = list(self.registered_servers.keys())[0]
                    
                    write_request = {
                        "server_id": server_id,
                        "accion": "escribir",
                        "nombre_archivo": nombre_archivo,
                        "contenido": contenido,
                        "origen_server_id": request.get("requesting_server", "DNS_GENERAL")
                    }
                    
                    response = self.solicitar_accion_remota(write_request)
                    
                    if response.get("status") == "EXITO":
                        # Actualizar el índice global con el nuevo archivo
                        server_info = self.registered_servers[server_id]
                        nuevo_archivo = {
                            "nombre_archivo": nombre_archivo,
                            "extension": os.path.splitext(nombre_archivo)[1],
                            "publicado": True,
                            "ttl": 3600,
                            "bandera": 0
                        }
                        
                        if nombre_archivo not in self.global_file_index:
                            self.global_file_index[nombre_archivo] = []
                        
                        self.global_file_index[nombre_archivo].append({
                            "server_id": server_id,
                            "ip": server_info["ip"],
                            "port": server_info["port"],
                            "ttl": 3600,
                            "bandera": 0
                        })
                        
                        response["servidor_destino"] = server_id
                        response["via_dns_general"] = True
                        response["tipo_operacion"] = "creacion"
                        
                        self.log(f"Nuevo archivo '{nombre_archivo}' creado en servidor {server_id}")
                    
                    return response
                else:
                    return {
                        "status": "ERROR",
                        "mensaje": "No hay servidores disponibles para crear el archivo"
                    }

    def solicitar_checkout_archivo(self, request: Dict) -> Dict:
        """Solicita checkout de un archivo para edición (crea copia temporal)"""
        nombre_archivo = request.get("nombre_archivo")
        server_solicitante = request.get("requesting_server")
        
        # Buscar dónde está el archivo original
        with self.lock:
            if nombre_archivo in self.global_file_index:
                archivo_info = self.global_file_index[nombre_archivo][0]
                server_origen = archivo_info["server_id"]
                
                if server_origen == server_solicitante:
                    # El archivo ya está en el servidor solicitante
                    return {
                        "status": "LOCAL",
                        "mensaje": "Archivo ya está en servidor local"
                    }
                
                # Solicitar copia del archivo al servidor origen
                read_request = {
                    "server_id": server_origen,
                    "accion": "leer",
                    "nombre_archivo": nombre_archivo,
                    "origen_server_id": "DNS_GENERAL"
                }
                
                response = self.solicitar_accion_remota(read_request)
                
                if response.get("status") == "EXITO":
                    # Marcar archivo como en checkout
                    checkout_info = {
                        "archivo": nombre_archivo,
                        "server_origen": server_origen,
                        "server_checkout": server_solicitante,
                        "contenido": response.get("contenido"),
                        "timestamp": time.time()
                    }
                    
                    # Almacenar información de checkout
                    if not hasattr(self, 'checkouts_activos'):
                        self.checkouts_activos = {}
                    self.checkouts_activos[f"{server_solicitante}:{nombre_archivo}"] = checkout_info
                    
                    self.log(f"Checkout: {nombre_archivo} de {server_origen} hacia {server_solicitante}")
                    
                    return {
                        "status": "CHECKOUT_EXITOSO",
                        "contenido": response.get("contenido"),
                        "servidor_origen": server_origen,
                        "mensaje": f"Copia temporal creada para edición"
                    }
                else:
                    return {
                        "status": "ERROR",
                        "mensaje": f"No se pudo obtener el archivo: {response.get('mensaje')}"
                    }
            else:
                # El archivo no existe, se puede crear nuevo
                return {
                    "status": "NUEVO_ARCHIVO",
                    "contenido": "",
                    "mensaje": "Archivo no existe, se puede crear nuevo"
                }
    
    # Dentro de la función procesar_checkin_archivo en dns_general.py

    def procesar_checkin_archivo(self, request: Dict) -> Dict:
        """Procesa el check-in de un archivo editado"""
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido")
        server_solicitante = request.get("requesting_server")

        # --- LÓGICA DE CORRECCIÓN ---
        # Primero, verificamos si el archivo existe en el índice global
        archivo_en_indice = False
        server_origen = None
        with self.lock:
            if nombre_archivo in self.global_file_index and self.global_file_index[nombre_archivo]:
                archivo_en_indice = True
                server_origen = self.global_file_index[nombre_archivo][0]["server_id"]

        # Si el archivo ya no existe en el índice o su servidor de origen ya no lo tiene,
        # procedemos directamente a la lógica de "nuevo propietario".
        if not archivo_en_indice or not self._verificar_archivo_existe(server_origen, nombre_archivo):
            self.log(f"Archivo original no encontrado para '{nombre_archivo}'. {server_solicitante} se convierte en el nuevo propietario.")
            
            # Actualizar el índice global para reflejar el nuevo propietario
            with self.lock:
                if server_solicitante in self.registered_servers:
                    server_info = self.registered_servers[server_solicitante]
                    # Eliminar entradas antiguas si existían
                    if nombre_archivo in self.global_file_index:
                        self.global_file_index[nombre_archivo] = [
                            e for e in self.global_file_index[nombre_archivo] if e["server_id"] != server_origen
                        ]
                    else:
                        self.global_file_index[nombre_archivo] = []
                    
                    # Añadir la nueva entrada del propietario
                    self.global_file_index[nombre_archivo].insert(0, {
                        "server_id": server_solicitante,
                        "ip": server_info["ip"],
                        "port": server_info["port"],
                        "ttl": 3600,
                        "bandera": 0
                    })
            
            # Limpiar cualquier checkout activo que pudiera haber quedado
            checkout_key = f"{server_solicitante}:{nombre_archivo}"
            if hasattr(self, 'checkouts_activos') and checkout_key in self.checkouts_activos:
                del self.checkouts_activos[checkout_key]
            
            return {
                "status": "CHECKIN_NUEVO_PROPIETARIO",
                "mensaje": f"Archivo original perdido. {server_solicitante} es ahora el propietario",
                "servidor_final": server_solicitante
            }

        # Si el archivo original SÍ existe, procedemos con la escritura normal
        else:
            write_request = {
                "server_id": server_origen,
                "accion": "escribir",
                "nombre_archivo": nombre_archivo,
                "contenido": contenido,
                "origen_server_id": "DNS_GENERAL"
            }
            
            response = self.solicitar_accion_remota(write_request)
            
            if response.get("status") == "EXITO":
                # Limpiar checkout
                checkout_key = f"{server_solicitante}:{nombre_archivo}"
                if hasattr(self, 'checkouts_activos') and checkout_key in self.checkouts_activos:
                    del self.checkouts_activos[checkout_key]
                
                self.log(f"Check-in exitoso: {nombre_archivo} actualizado en {server_origen}")
                
                return {
                    "status": "CHECKIN_EXITOSO",
                    "mensaje": f"Archivo actualizado en servidor original {server_origen}",
                    "servidor_final": server_origen,
                }
            else:
                return response

    def manejar_archivo_eliminado(self, request: Dict) -> Dict:
        """Maneja la eliminación de un archivo y busca copias en otros servidores"""
        nombre_archivo = request.get("nombre_archivo")
        server_eliminador = request.get("server_id")
        
        with self.lock:
            if nombre_archivo not in self.global_file_index:
                return {
                    "status": "ACK",
                    "mensaje": f"Archivo '{nombre_archivo}' no estaba en índice global"
                }
            
            # Buscar copias en otros servidores
            copias_encontradas = []
            for entry in self.global_file_index[nombre_archivo]:
                if entry["server_id"] != server_eliminador:
                    # Verificar si el archivo realmente existe en ese servidor
                    if self._verificar_archivo_existe(entry["server_id"], nombre_archivo):
                        copias_encontradas.append(entry)
            
            if copias_encontradas:
                # Hay copias en otros servidores, asignar nuevo propietario
                nuevo_propietario = copias_encontradas[0]  # Tomar el primero
                
                # Actualizar índice global
                self.global_file_index[nombre_archivo] = copias_encontradas
                
                self.log(f"Archivo '{nombre_archivo}' eliminado de {server_eliminador}. Nuevo propietario: {nuevo_propietario['server_id']}")
                
                return {
                    "status": "ACK",
                    "mensaje": f"Copia encontrada en {nuevo_propietario['server_id']}",
                    "nuevo_propietario": nuevo_propietario['server_id'],
                    "copias_disponibles": len(copias_encontradas)
                }
            else:
                # No hay copias, eliminar definitivamente
                del self.global_file_index[nombre_archivo]
                
                self.log(f"Archivo '{nombre_archivo}' eliminado definitivamente del sistema")
                
                return {
                    "status": "ACK", 
                    "mensaje": f"Archivo eliminado definitivamente",
                    "archivo_eliminado_definitivamente": True
                }
    
    def _verificar_archivo_existe(self, server_id: str, nombre_archivo: str) -> bool:
        """Verifica si un archivo realmente existe en un servidor específico"""
        if server_id not in self.registered_servers:
            return False
        
        try:
            server_info = self.registered_servers[server_id]
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            
            verify_request = {
                "accion": "verificar_existencia",
                "nombre_archivo": nombre_archivo,
                "via_dns_general": True
            }
            
            server_udp_port = server_info["port"] + 1000
            server_addr = (server_info["ip"], server_udp_port)
            
            sock.sendto(json.dumps(verify_request).encode('utf-8'), server_addr)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            return response.get("exists", False)
            
        except Exception as e:
            self.log(f"Error verificando existencia en {server_id}: {e}")
            return False
        finally:
            if 'sock' in locals():
                sock.close()

    def handle_request(self, request: Dict, addr: Tuple) -> Dict:
        """Maneja peticiones recibidas"""
        accion = request.get("accion")
        
        if accion == "registrar_servidor":
            return self.register_server(request)
        elif accion == "consultar":
            return self.consultar_archivo(request)
        elif accion == "listar_archivos":
            return self.listar_archivos_globales()
        elif accion == "checkout_archivo":
            return self.solicitar_checkout_archivo(request)
        elif accion == "checkin_archivo":
            return self.procesar_checkin_archivo(request)
        elif accion == "archivo_eliminado":
            return self.manejar_archivo_eliminado(request)
        elif accion == "leer":
            return self.leer_archivo_distribuido(request)
        elif accion == "escribir":
            return self.escribir_archivo_distribuido(request)
        elif accion == "solicitar_remoto":
            return self.solicitar_accion_remota(request)
        # AGREGAR ESTAS LÍNEAS PARA MANEJAR BLOQUEOS:
        elif accion == "solicitar_bloqueo":
            return self.solicitar_bloqueo_archivo(request)
        elif accion == "liberar_bloqueo":
            return self.liberar_bloqueo_archivo(request)
        elif accion == "verificar_bloqueo":
            return self.verificar_bloqueo_archivo(request)
        # FIN DE LÍNEAS AGREGADAS
        elif accion == "heartbeat":
            server_id = request.get("server_id")
            if server_id in self.registered_servers:
                self.registered_servers[server_id]["last_update"] = datetime.now().timestamp()
                return {"status": "ACK", "mensaje": "Heartbeat recibido"}
            return {"status": "ERROR", "mensaje": "Servidor no registrado"}
        else:
            return {"status": "ERROR", "mensaje": f"Acción '{accion}' no reconocida"}
    
    def cleanup_inactive_servers(self):
        """Limpia servidores inactivos (más de 5 minutos sin heartbeat)"""
        current_time = datetime.now().timestamp()
        inactive_threshold = 300  # 5 minutos
        
        with self.lock:
            inactive_servers = []
            for server_id, server_info in self.registered_servers.items():
                if current_time - server_info["last_update"] > inactive_threshold:
                    inactive_servers.append(server_id)
            
            for server_id in inactive_servers:
                self.log(f"Eliminando servidor inactivo: {server_id}")
                del self.registered_servers[server_id]
                
                # Limpiar del índice global
                for nombre_archivo in list(self.global_file_index.keys()):
                    self.global_file_index[nombre_archivo] = [
                        entry for entry in self.global_file_index[nombre_archivo]
                        if entry["server_id"] != server_id
                    ]
                    if not self.global_file_index[nombre_archivo]:
                        del self.global_file_index[nombre_archivo]
    
    def cleanup_loop(self):
        """Hilo de limpieza periódica"""
        while self.running:
            try:
                time.sleep(60)  # Cada minuto
                self.cleanup_inactive_servers()
            except Exception as e:
                self.log(f"Error en cleanup: {e}")
    
    def start(self):
        """Inicia el DNS General"""
        # Iniciar hilo de limpieza
        cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        # Crear socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        
        self.log(f"DNS General iniciado en {self.host}:{self.port}")
        self.log("Esperando registros de servidores...")
        
        try:
            while self.running:
                try:
                    data, addr = sock.recvfrom(8192)
                    request = json.loads(data.decode('utf-8'))
                    
                    self.log(f"Petición de {addr}: {request.get('accion', 'UNKNOWN')}")
                    
                    response = self.handle_request(request, addr)
                    
                    sock.sendto(json.dumps(response).encode('utf-8'), addr)
                    
                except json.JSONDecodeError as e:
                    self.log(f"Error decodificando JSON de {addr}: {e}")
                    error_response = {"status": "ERROR", "mensaje": "JSON inválido"}
                    sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
                    
                except Exception as e:
                    self.log(f"Error procesando petición de {addr}: {e}")
                    error_response = {"status": "ERROR", "mensaje": str(e)}
                    sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
                    
        except KeyboardInterrupt:
            self.log("DNS General detenido por el usuario")
        except Exception as e:
            self.log(f"Error en DNS General: {e}")
        finally:
            self.running = False
            sock.close()
            self.log("DNS General detenido")

if __name__ == "__main__":
    print("=== DNS General - Sistema Distribuido ===")
    print("Intermediario para comunicación entre servidores")
    print("Mantiene índice global de archivos")
    print("Ctrl+C para detener\n")
    
    dns_general = DNSGeneral()
    dns_general.start()