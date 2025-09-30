import os
import json
import threading
import time
import sys
import socket
from datetime import datetime

CONFIG_FILE = "file_permissions_config.json_chris"
LOG_FILE = "file_server.log"
UPDATE_INTERVAL = 300  # 5 minutos

with open('network_config.json', 'r') as f:
    net_config = json.load(f)

# Obtener la configuración específica para este peer
peer_config = net_config['peers']['server_christian']

# --- CONFIGURACIÓN DE RED ---
DNS_IP = "0.0.0.0" # Siempre escucha en 0.0.0.0
DNS_PORT = peer_config['dns_port']
SERVER_IP = peer_config['server_ip']
SERVER_PORT = peer_config['server_port']

lock = threading.Lock()

class FileEntry:
    def __init__(self, name, extension, ttl, can_publish):
        self.name = name
        self.extension = extension
        self.ttl = ttl
        self.can_publish = can_publish
    
    def to_dict(self):
        return {
            "name": self.name,
            "extension": self.extension,
            "ttl": self.ttl,
            "can_publish": self.can_publish
        }
    
    @staticmethod
    def from_dict(d):
        return FileEntry(d["name"], d["extension"], d["ttl"], d["can_publish"])


class FileServer:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.file_list = {}  # clave: name.ext -> FileEntry
        self.load_config()
        self.running = True
    
    def log(self, message):
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
        print(message)
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                with lock:
                    self.file_list = {
                        key: FileEntry.from_dict(value)
                        for key, value in data.items()
                    }
                self.log(f"Cargada configuración desde {CONFIG_FILE}")
            except Exception as e:
                self.log(f"Error al cargar configuración: {e}")
                self.file_list = {}
        else:
            self.file_list = {}
            self.log(f"No existe archivo de configuración. Se creará uno nuevo.")
    
    def save_config(self):
        with lock:
            data = {key: fe.to_dict() for key, fe in self.file_list.items()}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
        self.log(f"Configuración guardada en {CONFIG_FILE}")
    
    def scan_folder(self):
        """Devuelve set de archivos actuales en carpeta (name.ext)"""
        files = set()
        try:
            for f in os.listdir(self.folder_path):
                full_path = os.path.join(self.folder_path, f)
                if os.path.isfile(full_path):
                    name, ext = os.path.splitext(f)
                    ext = ext.lstrip(".")
                    key = f"{name}.{ext}"
                    files.add(key)
        except Exception as e:
            self.log(f"Error al leer carpeta: {e}")
        return files
    
    def ask_user_for_file(self, filename, extension):
        while True:
            resp = input(f"¿El archivo '{filename}.{extension}' puede publicarse? (s/n): ").strip().lower()
            if resp in ("s", "n"):
                can_publish = resp == "s"
                break
            print("Por favor ingresa 's' o 'n'")
        while True:
            try:
                ttl = int(input(f"Indica TTL (segundos) para '{filename}.{extension}': ").strip())
                if ttl > 0:
                    break
                else:
                    print("TTL debe ser un número positivo")
            except:
                print("TTL debe ser un número entero")
        return can_publish, ttl
    
    def update_files(self):
        """Escanea la carpeta y publica automáticamente los archivos."""
        current_files = self.scan_folder()
        with lock:
            known_files = set(self.file_list.keys())

            # Archivos nuevos: publicarlos automáticamente
            new_files = current_files - known_files
            for f in new_files:
                name, ext = f.rsplit(".", 1)
                self.log(f"Nuevo archivo detectado y auto-publicado: {f}")
                # Asignamos permiso y un TTL por defecto de 1 hora
                can_publish = True
                ttl = 3600
                self.file_list[f] = FileEntry(name, ext, ttl, can_publish)
            
            # Archivos eliminados
            removed_files = known_files - current_files
            for f in removed_files:
                self.log(f"Archivo eliminado detectado: {f}")
                del self.file_list[f]
                self.log(f"Archivo '{f}' removido de la lista")
        
        self.save_config()
    
    def update_loop(self):
        while self.running:
            try:
                self.update_files()
            except Exception as e:
                self.log(f"Error en actualización: {e}")
            time.sleep(UPDATE_INTERVAL)
    
    def udp_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((DNS_IP, DNS_PORT))
        self.log(f"Servidor UDP iniciado en {DNS_IP}:{DNS_PORT}")
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                self.log(f"Paquete UDP recibido de {addr}")
                msg = data.decode("utf-8")
                try:
                    req = json.loads(msg)
                    self.log(f"entrada request: {req}")
                    # 👇 Nuevo caso: consulta de info del servidor
                    if req.get("accion") == "consultar" and req.get("nombre_archivo") == "servidor_info":
                        resp = {
                            "status": "ACK",
                            "ip": SERVER_IP,
                            "puerto": SERVER_PORT
                        }

                    elif req.get("type") == "check":
                        # Solicitud de verificación de archivo individual
                        filename = req.get("filename")
                        extension = req.get("extension")
                        if not filename or not extension:
                            resp = {"response": "NACK", "reason": "Faltan 'filename' o 'extension'"}
                        else:
                            key = f"{filename}.{extension}"
                            with lock:
                                fe = self.file_list.get(key)
                            if fe and fe.can_publish:
                                resp = {"response": "ACK",
                                        "ip": SERVER_IP,
                                        "port": SERVER_PORT}
                            else:
                                resp = {"response": "NACK",
                                        "ip": SERVER_IP,
                                        "port": SERVER_PORT}
                    
                    elif req.get("type") == "list":
                        # Solicitud de lista de archivos disponibles
                        with lock:
                            available_files = [
                                {"name": fe.name, "extension": fe.extension}
                                for fe in self.file_list.values()
                                if fe.can_publish
                            ]
                        resp = {
                            "response": "ACK",
                            "files": available_files,
                            "count": len(available_files),
                            "ip": SERVER_IP,
                            "port": SERVER_PORT
                        }
                    
                    else:
                        resp = {"response": "NACK", "reason": "Solicitud no válida"}
                        
                except json.JSONDecodeError:
                    resp = {"response": "NACK", "reason": "JSON inválido"}
                    
                self.log(f"Salida request: {req}")  
                self.log(f"Respuesta enviada a {addr}: {resp}")  
                resp_bytes = json.dumps(resp).encode("utf-8")
                sock.sendto(resp_bytes, addr)
                
            except Exception as e:
                self.log(f"Error en servidor UDP: {e}")
    
    def start(self):
        self.log("Iniciando servidor de nombres de recursos de archivo.")
        self.update_files()  # actualización inicial
        
        thread_update = threading.Thread(target=self.update_loop, daemon=True)
        thread_udp = threading.Thread(target=self.udp_server, daemon=True)
        
        thread_update.start()
        thread_udp.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("Terminando proceso...")
            self.running = False
            thread_update.join()
            thread_udp.join()


if __name__ == "__main__":
    folder = ""
    # Revisa si se pasó una ruta como argumento
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        folder = sys.argv[1]
    else:
        # Si no, pregunta al usuario como antes
        folder = input("Introduce la ruta absoluta de la carpeta a monitorear: ").strip()

    if not os.path.isdir(folder):
        print("La carpeta no existe o no es válida.")
        exit(1)
        
    server = FileServer(folder)
    server.start()