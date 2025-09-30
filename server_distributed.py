import socket
import json
import threading
import os
import logging
import time
import sys
from typing import Dict, Tuple

# Importaciones del sistema de red seguro
sys.path.append('src/network')
from src.network.peer_conector import PeerConnector
from src.network.transport import ReliableTransport
# --- CAMBIO: Importamos el traductor ---
from src.network.dns_translator.translator import DNSTranslatorIntegrated

# --- Configuración ---
with open('network_config.json', 'r') as f:
    net_config = json.load(f)

DNS_GENERAL_IP = net_config['dns_general']['connect_ip']
DNS_GENERAL_PORT = net_config['dns_general']['port']

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ServidorDistribuido:
    # --- CAMBIO: Se añade la información del DNS local al constructor ---
    def __init__(self, server_id: str, host: str, port: int, folder_path: str, dns_local_id: str):
        self.server_id = server_id
        self.host = host
        self.port = port
        self.folder_path = folder_path
        self.running = True
        
        # --- CAMBIO: Guardamos el ID del DNS local asociado ---
        self.dns_local_id = dns_local_id
        
        self.local_files = []
        self.local_files_lock = threading.Lock()
        
        # --- CAMBIO: Instanciamos el traductor ---
        self.translator = DNSTranslatorIntegrated()
        
        # Componentes de red
        self.transport = ReliableTransport(host, port)
        self.peer_connector = PeerConnector(
            self.transport, 
            self.server_id,
            self._handle_secure_message
        )
        
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            
        # Inicialización y arranque de hilos
        # --- CAMBIO: Ya no escaneamos la carpeta, sincronizamos con el DNS local ---
        self._sincronizar_con_dns_local()
        self._register_with_dns_general()
        self._start_heartbeat()
        self._start_udp_listener()
        # --- CAMBIO: El monitor ahora sincroniza, no vigila la carpeta ---
        self._start_sync_monitor()

    def log(self, message):
        logging.info(f"[{self.server_id}] {message}")
        
    def _forward_to_dns_general(self, request: Dict) -> Dict:
        """Reenvía una petición genérica al DNS General y devuelve la respuesta."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                # Añadimos el ID del servidor que origina la petición para el contexto
                request['requesting_server'] = self.server_id
                sock.sendto(json.dumps(request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(4096)
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.log(f"Error reenviando petición a DNS General: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

    # --- CAMBIO: Nuevo método para sincronizar con el DNS local usando el traductor ---
    def _sincronizar_con_dns_local(self):
        """Consulta la lista de archivos publicados desde el DNS local y actualiza el estado interno."""
        self.log(f"Sincronizando con DNS local '{self.dns_local_id}'...")
        request = {"accion": "listar_archivos"}
        response = self.translator._try_resolve(request, self.dns_local_id)
        
        if response and response.get("status") == "ACK":
            archivos_remotos = response.get("archivos", [])
            with self.local_files_lock:
                # Normalizamos la data para que coincida con el formato esperado por el DNS General
                self.local_files = []
                for archivo in archivos_remotos:
                    self.local_files.append({
                        "nombre_archivo": archivo["nombre_archivo"],
                        "extension": os.path.splitext(archivo["nombre_archivo"])[1],
                        "publicado": True, # Si el DNS local lo lista, está publicado
                        "ttl": archivo.get("ttl", 3600),
                        "bandera": 0,
                        "ip_origen": self.host
                    })
            self.log(f"Sincronización exitosa. Obtenidos {len(self.local_files)} archivos publicados.")
        else:
            self.log(f"Fallo al sincronizar con DNS local: {response.get('mensaje', 'Error desconocido')}")

    # --- CAMBIO: El monitor ahora llama a la sincronización periódicamente ---
    def _start_sync_monitor(self):
        """Inicia un hilo para sincronizar periódicamente con el DNS local."""
        def sync_loop():
            while self.running:
                time.sleep(60) # Sincronizar cada 60 segundos
                if self.running:
                    lista_previa = [f["nombre_archivo"] for f in self.local_files]
                    self._sincronizar_con_dns_local()
                    lista_nueva = [f["nombre_archivo"] for f in self.local_files]

                    # Si hubo un cambio en la lista de archivos, notificamos al DNS General
                    if set(lista_previa) != set(lista_nueva):
                        self.log("Cambios detectados en DNS local. Actualizando registro en DNS General...")
                        self._register_with_dns_general()

        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.start()
        self.log("Monitor de sincronización con DNS local iniciado")

    # [ ... El resto del código (_handle_secure_message, _handle_leer, _handle_escribir, etc.) ... ]
    # [ ... no necesita cambios, ya que opera sobre la lista self.local_files que ahora es llenada ... ]
    # [ ... por la sincronización. Lo incluyo abajo por completitud sin comentarios de cambio.    ... ]
    
    def start(self):
        """Inicia el bucle principal del servidor."""
        self.log(f"Servidor distribuido iniciado en {self.host}:{self.port}")
        self.log(f"Carpeta local: {os.path.abspath(self.folder_path)}")
        try:
            while self.running:
                payload, addr = self.transport.listen()
                if payload and addr:
                    self.peer_connector.handle_incoming_packet(payload, addr)
        except KeyboardInterrupt:
            self.log("Servidor detenido por el usuario")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el servidor de manera limpia."""
        self.running = False
        if self.peer_connector:
            self.peer_connector.stop()
        self.log("Servidor detenido")
        
    def _forward_to_dns_general(self, request: Dict) -> Dict:
        """Reenvía una petición genérica al DNS General y devuelve la respuesta."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                # Añadimos el ID del servidor que origina la petición para el contexto
                request['requesting_server'] = self.server_id
                sock.sendto(json.dumps(request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(4096)
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.log(f"Error reenviando petición a DNS General: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

    def _handle_secure_message(self, request: Dict, peer_addr: Tuple[str, int]):
        """Maneja mensajes seguros recibidos de un cliente."""
        try:
            accion = request.get("accion")
            self.log(f"Mensaje seguro de {peer_addr}: {accion}")
            
            if accion == "listar_archivos":
                response = self._handle_listar_archivos()
            elif accion == "leer":
                response = self._handle_leer(request)
            elif accion == "escribir":
                response = self._handle_escribir(request)
            elif accion == "consultar":
                response = self._handle_consultar(request)
            elif accion == "salir":
                response = {"status": "ACK", "mensaje": "Desconexión confirmada"}
            
            # --- NUEVO BLOQUE PARA MANEJAR BLOQUEOS ---
            elif accion in ["solicitar_bloqueo", "liberar_bloqueo", "listar_bloqueos"]:
                # Todas las acciones de bloqueo se reenvían al DNS General
                response = self._forward_to_dns_general(request)
            
            else:
                response = {"status": "ERROR", "mensaje": f"Acción '{accion}' no reconocida"}
            
            self.peer_connector.send_message(response, peer_addr)
            
        except Exception as e:
            self.log(f"Error procesando mensaje seguro: {e}")
            error_response = {"status": "ERROR", "mensaje": str(e)}
            self.peer_connector.send_message(error_response, peer_addr)

    def _handle_listar_archivos(self) -> Dict:
        """Obtiene la lista global de archivos desde el DNS General."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                list_request = {"accion": "listar_archivos"}
                sock.sendto(json.dumps(list_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(8192)
                response = json.loads(data.decode('utf-8'))
                return response if response.get("status") == "ACK" else {"status": "ERROR", "mensaje": "No se pudo listar archivos"}
        except Exception as e:
            self.log(f"Error listando archivos desde DNS General: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

    def _handle_leer(self, request: Dict) -> Dict:
        """Maneja la lectura de un archivo, buscando localmente y luego en la red."""
        nombre_archivo = request.get("nombre_archivo")
        
        # --- LÓGICA DE VERIFICACIÓN DE BLOQUEO ELIMINADA ---
        # Ya no es necesario comprobar el bloqueo para una simple lectura.

        # 1. Intentar leer localmente
        file_path = os.path.join(self.folder_path, nombre_archivo)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return {"status": "EXITO", "contenido": f.read(), "fuente": "local"}
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error leyendo archivo local: {e}"}

        # 2. Si no está local, solicitar lectura distribuida a través del DNS General
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(10)
                read_request = {
                    "accion": "leer", 
                    "nombre_archivo": nombre_archivo, 
                    "requesting_server": self.server_id
                }
                sock.sendto(json.dumps(read_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(8192)
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.log(f"Error solicitando lectura distribuida: {e}")
            return {"status": "ERROR", "mensaje": f"Archivo no encontrado en el sistema: {e}"}

    def _handle_escribir(self, request: Dict) -> Dict:
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido", "")
        
        file_path = os.path.join(self.folder_path, nombre_archivo)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                self.log(f"Archivo '{nombre_archivo}' modificado localmente")
                return {"status": "EXITO", "mensaje": f"Archivo '{nombre_archivo}' guardado localmente", "fuente": "local"}
            except Exception as e:
                return {"status": "ERROR", "mensaje": f"Error escribiendo archivo local: {e}"}
        
        return self._handle_escritura_remota(nombre_archivo, contenido)

    def _handle_consultar(self, request: Dict) -> Dict:
        nombre_archivo = request.get("nombre_archivo")
        if not nombre_archivo:
            return {"status": "ERROR", "mensaje": "Nombre de archivo requerido"}
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                query = {"accion": "consultar", "nombre_archivo": nombre_archivo}
                sock.sendto(json.dumps(query).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(4096)
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.log(f"Error consultando DNS General: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

    def _handle_escritura_remota(self, nombre_archivo: str, contenido: str) -> Dict:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(10)
                bloqueo_req = {"accion": "solicitar_bloqueo", "nombre_archivo": nombre_archivo, "requesting_server": self.server_id}
                sock.sendto(json.dumps(bloqueo_req).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(4096)
                response = json.loads(data.decode('utf-8'))
                if response.get("status") != "BLOQUEO_CONCEDIDO":
                    return {"status": "ERROR", "mensaje": f"No se pudo obtener bloqueo: {response.get('mensaje')}"}
            
            self.log(f"Bloqueo concedido para '{nombre_archivo}'")
            checkin_response = self._realizar_checkin_con_bloqueo(nombre_archivo, contenido)
            return checkin_response

        except Exception as e:
            self.log(f"Error en escritura remota con bloqueo: {e}")
            return {"status": "ERROR", "mensaje": f"Error en escritura remota: {e}"}
        finally:
            self._liberar_bloqueo_archivo(nombre_archivo)

    def _realizar_checkin_con_bloqueo(self, nombre_archivo: str, contenido: str) -> Dict:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(10)
                checkin_req = {"accion": "checkin_archivo", "nombre_archivo": nombre_archivo, "contenido": contenido, "requesting_server": self.server_id}
                sock.sendto(json.dumps(checkin_req).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(8192)
                response = json.loads(data.decode('utf-8'))

                if response.get("status") == "CHECKIN_NUEVO_PROPIETARIO" or (response.get("status") == "EXITO" and response.get("tipo_operacion") == "creacion"):
                    self.log(f"Este servidor ahora es el nuevo propietario de '{nombre_archivo}'")
                    with open(os.path.join(self.folder_path, nombre_archivo), 'w', encoding='utf-8') as f:
                        f.write(contenido)
                    self._sincronizar_con_dns_local() 
                    self._register_with_dns_general()
                    return {"status": "EXITO", "mensaje": f"Archivo '{nombre_archivo}' creado y ahora es propiedad de este servidor."}
                
                elif response.get("status") == "CHECKIN_EXITOSO":
                    return {"status": "EXITO", "mensaje": f"Archivo '{nombre_archivo}' actualizado en servidor {response.get('servidor_final')}"}
                
                else:
                    return {"status": "ERROR", "mensaje": f"Error en check-in: {response.get('mensaje', 'Error desconocido')}"}
        except Exception as e:
            self.log(f"Excepción en _realizar_checkin_con_bloqueo: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

    def _liberar_bloqueo_archivo(self, nombre_archivo: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                liberar_req = {"accion": "liberar_bloqueo", "nombre_archivo": nombre_archivo, "requesting_server": self.server_id}
                sock.sendto(json.dumps(liberar_req).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                sock.recvfrom(4096)
                self.log(f"Bloqueo liberado para '{nombre_archivo}'")
        except Exception as e:
            self.log(f"Error liberando bloqueo para '{nombre_archivo}': {e}")
            
    def _register_with_dns_general(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                register_request = {
                    "accion": "registrar_servidor", "server_id": self.server_id,
                    "ip": self.host, "port": self.port, "archivos": self.local_files
                }
                sock.sendto(json.dumps(register_request).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                data, _ = sock.recvfrom(4096)
                if json.loads(data.decode('utf-8')).get("status") == "ACK":
                    self.log("Registrado exitosamente en DNS General")
        except Exception as e:
            self.log(f"Error registrando en DNS General: {e}")

    def _start_heartbeat(self):
        def heartbeat_loop():
            while self.running:
                time.sleep(30)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                        sock.settimeout(3)
                        sock.sendto(json.dumps({"accion": "heartbeat", "server_id": self.server_id}).encode('utf-8'), (DNS_GENERAL_IP, DNS_GENERAL_PORT))
                        sock.recvfrom(1024)
                except Exception as e:
                    self.log(f"Error enviando heartbeat: {e}")
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()

    def _start_udp_listener(self):
        def udp_server():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                try:
                    udp_port = self.port + 1000
                    sock.bind((self.host, udp_port))
                    self.log(f"Listener UDP para DNS General iniciado en {self.host}:{udp_port}")
                except Exception as e:
                    self.log(f"Error iniciando UDP listener: {e}")
                    return

                while self.running:
                    try:
                        data, addr = sock.recvfrom(8192)
                        request = json.loads(data.decode('utf-8'))
                        if request.get("via_dns_general"):
                            response = self._process_dns_general_request(request)
                            sock.sendto(json.dumps(response).encode('utf-8'), addr)
                    except Exception as e:
                        self.log(f"Error en UDP listener: {e}")
        
        thread = threading.Thread(target=udp_server, daemon=True)
        thread.start()
        
    def _process_dns_general_request(self, request: Dict) -> Dict:
        accion = request.get("accion")
        if accion == "leer":
            return self._handle_leer_directo(request)
        elif accion == "escribir":
            return self._handle_escribir_directo(request)
        elif accion == "verificar_existencia":
            return self._handle_verificar_existencia(request)
        else:
            return {"status": "ERROR", "mensaje": f"Acción '{accion}' no soportada vía UDP"}

    def _handle_leer_directo(self, request: Dict) -> Dict:
        nombre_archivo = request.get("nombre_archivo")
        file_path = os.path.join(self.folder_path, nombre_archivo)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return {"status": "EXITO", "contenido": f.read()}
            except Exception as e:
                return {"status": "ERROR", "mensaje": str(e)}
        return {"status": "ERROR", "mensaje": "Archivo no encontrado"}

    def _handle_escribir_directo(self, request: Dict) -> Dict:
        nombre_archivo = request.get("nombre_archivo")
        contenido = request.get("contenido", "")
        try:
            with open(os.path.join(self.folder_path, nombre_archivo), 'w', encoding='utf-8') as f:
                f.write(contenido)
            return {"status": "EXITO", "mensaje": f"Archivo '{nombre_archivo}' escrito"}
        except Exception as e:
            return {"status": "ERROR", "mensaje": str(e)}
        
    def _handle_verificar_existencia(self, request: Dict) -> Dict:
        nombre_archivo = request.get("nombre_archivo")
        exists = os.path.exists(os.path.join(self.folder_path, nombre_archivo))
        return {"status": "ACK", "exists": exists}

# --- CAMBIO: La función de fábrica ahora pasa el ID del DNS local ---
def crear_servidor(config_name: str):
    if config_name not in net_config['peers']:
        print(f"Configuración '{config_name}' no encontrada.")
        return None
    
    peer_config = net_config['peers'][config_name]
    return ServidorDistribuido(
        server_id=config_name,
        host=peer_config['server_ip'],
        port=peer_config['server_port'],
        folder_path=f"archivos_{config_name.lower()}",
        dns_local_id=peer_config['id_dns_cliente'] # Pasamos el ID del DNS
    )

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python server_distributed.py <server_id>")
        # Muestra las claves exactas que se deben usar
        print(f"IDs disponibles: {', '.join(net_config['peers'].keys())}")
        sys.exit(1)
    
    # --- CAMBIO: Se elimina la línea de normalización defectuosa ---
    # Simplemente usamos el argumento tal como se proporciona.
    config_name = sys.argv[1]

    server = crear_servidor(config_name)
    
    if server:
        server.start()
    else:
        # El mensaje de error 'Configuración no encontrada' ya se imprime en crear_servidor
        sys.exit(1)